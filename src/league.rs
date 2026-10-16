//! League: a single round robin between models on a random fixture. A match starts as soon
//! as both its models can take another one (`max_matches` each), in fixture order, so the
//! matchday order holds wherever it can but nobody waits for a whole matchday. A match
//! that fails is deferred and resumed later from its last stored turn; only the failing
//! model backs off, the others play on. Ties in the table are broken by more games won,
//! then fewer games lost; a tie still standing that decides any of the first three places
//! goes to a playoff.

use std::collections::{HashMap, HashSet};
use std::path::PathBuf;
use std::pin::Pin;
use std::sync::Arc;
use std::time::{Duration, Instant};

use anyhow::{Context, Result, bail};
use parking_lot::RwLock;
use serde::Deserialize;
use tokio::sync::mpsc;
use tokio::task::JoinSet;

use crate::db::{Db, FixtureRow};
use crate::dice::{Dice, derive_seed};
use crate::players::prompt::PromptVersion;
use crate::players::{Player, PlayerConfig, Setup};
use crate::runner::{
    Clock, Control, Event, Harness, MAX_SPEED, MatchResult, MatchSettings, PlayerFault, Protocol,
    Runner, describe_clock,
};

/// League points for a match won, drawn, lost.
const WIN_POINTS: u32 = 3;
const DRAW_POINTS: u32 = 1;
/// Places a playoff decides when the table leaves them tied.
const PLAYOFF_PLACES: usize = 3;
/// After a failure no new match of the failing model (or, when no model is to blame, the
/// failed match) starts for `FIRST_BACKOFF`, doubling with every failure in a row up to
/// `MAX_BACKOFF`; the failed match is resumed after it.
const FIRST_BACKOFF: Duration = Duration::from_secs(120);
const MAX_BACKOFF: Duration = Duration::from_secs(3600);
/// League matches a model plays at once unless its `max_matches` says otherwise; local
/// engines (random, safest, gnubg-weak) have no limit.
const DEFAULT_MAX_MATCHES: usize = 4;

pub enum Start {
    New {
        /// Entry order.
        models: Vec<PlayerConfig>,
        seed: u64,
        rounds: u32,
        clock: Option<Clock>,
        max_turns: Option<u32>,
        /// What this league tests; shown in the history.
        note: Option<String>,
        version: PromptVersion,
        order_seed: u64,
        mirror_concurrent: bool,
    },
    Resume(i64),
}

/// A league config file (`jevgammon league --config FILE`): the roster with each player's
/// provider, quantization, reasoning, request fields and price, plus the settings. Fields
/// left out fall back to the command line.
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct LeagueConfig {
    pub players: Vec<PlayerConfig>,
    pub seed: Option<u64>,
    pub order_seed: Option<u64>,
    pub prompt_version: Option<String>,
    pub rounds: Option<u32>,
    /// Bank per player per game in seconds; 0 = no clock.
    pub clock: Option<u64>,
    pub delay: Option<u64>,
    /// 0 = no limit.
    pub max_turns: Option<u32>,
    /// Play the two games of each round at once (default false); both then show the score
    /// at the start of the round.
    pub mirror_concurrent: Option<bool>,
    pub note: Option<String>,
}

impl LeagueConfig {
    pub fn load(path: &std::path::Path) -> Result<Self> {
        let text =
            std::fs::read_to_string(path).with_context(|| format!("reading {}", path.display()))?;
        serde_json::from_str(&text).with_context(|| format!("parsing {}", path.display()))
    }
}

/// Prompt version of a league stored before versions existed: the runner then sent
/// League #13's prompt, which is bg-v2-history.
const LEGACY_VERSION: PromptVersion = PromptVersion::BgV2History;

struct League {
    db_path: PathBuf,
    id: i64,
    seed: u64,
    rounds: u32,
    clock: Option<Clock>,
    max_turns: Option<u32>,
    mirror_concurrent: bool,
    /// Entry order; players added later come last.
    names: RwLock<Vec<String>>,
    players: RwLock<HashMap<String, Entrant>>,
    control: Arc<Control>,
    protocol: Arc<Protocol>,
    /// First and longest backoff after failures.
    backoff: (Duration, Duration),
}

/// A model of the league and how many matches it plays at once.
struct Entrant {
    player: Arc<Player>,
    max_matches: usize,
}

impl Entrant {
    fn new(config: &PlayerConfig, player: Player) -> Self {
        let default = if player.is_engine() {
            usize::MAX
        } else {
            DEFAULT_MAX_MATCHES
        };
        Entrant {
            max_matches: config.max_matches.unwrap_or(default).max(1),
            player: Arc::new(player),
        }
    }
}

/// One model's line in a table.
#[derive(Clone, Debug, Default)]
struct Row {
    name: String,
    played: u32,
    won: u32,
    drawn: u32,
    lost: u32,
    points: u32,
    games_won: u32,
    games_lost: u32,
    /// Backgammon points scored and conceded; shown, not used for ranking.
    scored: u32,
    conceded: u32,
}

impl Row {
    /// Ranking key: league points, then games won, then fewer games lost.
    fn key(&self) -> (u32, u32, std::cmp::Reverse<u32>) {
        (
            self.points,
            self.games_won,
            std::cmp::Reverse(self.games_lost),
        )
    }
}

/// The table for `names` over `results`, best first; equal keys keep `names` order.
fn table(names: &[String], results: &[(String, String, MatchResult)]) -> Vec<Row> {
    let mut rows: Vec<Row> = names
        .iter()
        .map(|name| Row {
            name: name.clone(),
            ..Row::default()
        })
        .collect();
    let index: HashMap<&str, usize> = names
        .iter()
        .enumerate()
        .map(|(i, n)| (n.as_str(), i))
        .collect();
    for (model1, model2, result) in results {
        for (side, name) in [model1, model2].into_iter().enumerate() {
            let row = &mut rows[index[name.as_str()]];
            let other = 1 - side;
            row.played += 1;
            row.games_won += result.games_won[side];
            row.games_lost += result.games_won[other];
            row.scored += result.score[side];
            row.conceded += result.score[other];
            match result.winner {
                None => {
                    row.drawn += 1;
                    row.points += DRAW_POINTS;
                }
                Some(winner) if winner as usize == side + 1 => {
                    row.won += 1;
                    row.points += WIN_POINTS;
                }
                Some(_) => row.lost += 1,
            }
        }
    }
    rows.sort_by(|a, b| b.key().cmp(&a.key()));
    rows
}

/// Runs of equal ranking keys in a sorted table, as index ranges.
fn tie_groups(rows: &[Row]) -> Vec<std::ops::Range<usize>> {
    let mut groups = Vec::new();
    let mut start = 0;
    for i in 1..=rows.len() {
        if i == rows.len() || rows[i].key() != rows[start].key() {
            if i - start > 1 {
                groups.push(start..i);
            }
            start = i;
        }
    }
    groups
}

fn print_table(title: &str, rows: &[Row]) {
    let width = rows.iter().map(|r| r.name.len()).max().unwrap_or(5).max(5);
    println!("\n{title}");
    println!(
        "  #  {:width$}   P   W   D   L  Pts   GW   GL    PF    PA",
        "Model"
    );
    for (place, row) in rows.iter().enumerate() {
        println!(
            " {:>2}  {:width$} {:>3} {:>3} {:>3} {:>3} {:>4} {:>4} {:>4} {:>5} {:>5}",
            place + 1,
            row.name,
            row.played,
            row.won,
            row.drawn,
            row.lost,
            row.points,
            row.games_won,
            row.games_lost,
            row.scored,
            row.conceded
        );
    }
}

/// Removes from `pending`, in order, every fixture whose two models are below their match
/// limit (`limit`, against the matches counted in `running`) and not held back by
/// `waiting`, and counts it in `running`. Earlier fixtures go first, so the matchday order
/// holds wherever it can.
fn take_startable(
    pending: &mut Vec<FixtureRow>,
    running: &mut HashMap<String, usize>,
    limit: impl Fn(&str) -> usize,
    waiting: impl Fn(&FixtureRow) -> bool,
) -> Vec<FixtureRow> {
    let mut started = Vec::new();
    let mut i = 0;
    while i < pending.len() {
        let fixture = &pending[i];
        let free = |name: &str| running.get(name).copied().unwrap_or(0) < limit(name);
        if !free(&fixture.model1) || !free(&fixture.model2) || waiting(fixture) {
            i += 1;
            continue;
        }
        let fixture = pending.remove(i);
        *running.entry(fixture.model1.clone()).or_default() += 1;
        *running.entry(fixture.model2.clone()).or_default() += 1;
        started.push(fixture);
    }
    started
}

/// The wait after failures of one model (its decisions or warm-up failed) or of one match
/// (a failure no model is to blame for): nothing of it starts before `until`.
#[derive(Clone, Debug)]
struct Backoff {
    until: Instant,
    delay: Duration,
    /// Failures in a row.
    failures: u32,
    error: String,
}

impl Backoff {
    /// The backoff after another failure at `now`: `first`, then twice the last delay up to
    /// `max`. A failure while the last backoff still runs (another match failing for the
    /// same cause) keeps that backoff.
    fn after(
        previous: Option<&Backoff>,
        error: String,
        now: Instant,
        (first, max): (Duration, Duration),
    ) -> Backoff {
        match previous {
            Some(last) if last.until > now => Backoff {
                error,
                ..last.clone()
            },
            Some(last) => {
                let delay = (last.delay * 2).min(max);
                Backoff {
                    until: now + delay,
                    delay,
                    failures: last.failures + 1,
                    error,
                }
            }
            None => Backoff {
                until: now + first,
                delay: first,
                failures: 1,
                error,
            },
        }
    }

    /// E.g. "until 08:15:02 UTC (2 min; 3 failures in a row)".
    fn describe(&self, now: Instant) -> String {
        let left = self.until.saturating_duration_since(now);
        let at = chrono::Utc::now() + chrono::Duration::from_std(left).unwrap_or_default();
        format!(
            "until {} ({}; {} failure{} in a row)",
            at.format("%H:%M:%S UTC"),
            span(self.delay),
            self.failures,
            if self.failures == 1 { "" } else { "s" }
        )
    }
}

/// `"45 s"`, `"4 min"`, `"1 h"`.
fn span(duration: Duration) -> String {
    let seconds = duration.as_secs();
    if seconds < 120 {
        format!("{seconds} s")
    } else if seconds < 7200 {
        format!("{} min", seconds / 60)
    } else {
        format!("{} h", seconds / 3600)
    }
}

/// Running backoffs by model name and by fixture id.
#[derive(Default)]
struct Backoffs {
    players: HashMap<String, Backoff>,
    fixtures: HashMap<i64, Backoff>,
}

impl Backoffs {
    /// The running backoff that keeps `fixture` from starting at `now`, with what backs off
    /// (a model's name, or "the match").
    fn holding<'a>(
        &'a self,
        fixture: &'a FixtureRow,
        now: Instant,
    ) -> Option<(&'a str, &'a Backoff)> {
        [&fixture.model1, &fixture.model2]
            .into_iter()
            .find_map(|name| {
                self.players
                    .get(name)
                    .filter(|b| b.until > now)
                    .map(|b| (name.as_str(), b))
            })
            .or_else(|| {
                self.fixtures
                    .get(&fixture.id)
                    .filter(|b| b.until > now)
                    .map(|b| ("the match", b))
            })
    }

    /// When the next running backoff ends.
    fn next_end(&self, now: Instant) -> Option<Instant> {
        self.players
            .values()
            .chain(self.fixtures.values())
            .map(|b| b.until)
            .filter(|&until| until > now)
            .min()
    }

    /// Records a failure of `fixture`'s match: a backoff for the model to blame, or for
    /// the match when none is. Returns what backs off and until when.
    fn fail(
        &mut self,
        fixture: &FixtureRow,
        error: &anyhow::Error,
        now: Instant,
        limits: (Duration, Duration),
    ) -> String {
        let message = format!("{error:#}");
        match blamed(fixture, error) {
            Some(name) => {
                let backoff = Backoff::after(self.players.get(name), message, now, limits);
                let text = format!(
                    "{name} backs off: none of its matches starts {}",
                    backoff.describe(now)
                );
                self.players.insert(name.to_owned(), backoff);
                text
            }
            None => {
                let backoff = Backoff::after(self.fixtures.get(&fixture.id), message, now, limits);
                let text = format!("the match is retried {}", backoff.describe(now));
                self.fixtures.insert(fixture.id, backoff);
                text
            }
        }
    }

    /// A match of `fixture` finished: its models and the match work again.
    fn clear(&mut self, fixture: &FixtureRow) {
        self.players.remove(&fixture.model1);
        self.players.remove(&fixture.model2);
        self.fixtures.remove(&fixture.id);
    }
}

/// The model of `fixture` whose decision or warm-up caused `error`, if one did.
fn blamed<'a>(fixture: &'a FixtureRow, error: &anyhow::Error) -> Option<&'a str> {
    error
        .downcast_ref::<PlayerFault>()
        .map(|&PlayerFault(player)| {
            if player == 1 {
                fixture.model1.as_str()
            } else {
                fixture.model2.as_str()
            }
        })
}

/// Played matches as table input, in fixture order whatever order they finished in.
fn results_of(played: &[(FixtureRow, MatchResult)]) -> Vec<(String, String, MatchResult)> {
    let mut sorted: Vec<_> = played.iter().collect();
    sorted.sort_by_key(|(fixture, _)| fixture.id);
    sorted
        .into_iter()
        .map(|(f, result)| (f.model1.clone(), f.model2.clone(), *result))
        .collect()
}

/// Single round robin by the circle method on a shuffled entry list; `(matchday, model1,
/// model2)` with model1 (white in each round's first game) drawn per match.
fn draw_fixture(names: &[String], seed: u64) -> Vec<(u32, String, String)> {
    let mut rng = Dice::new(derive_seed(seed, "fixture"));
    let mut teams: Vec<Option<&String>> = names.iter().map(Some).collect();
    for i in (1..teams.len()).rev() {
        teams.swap(i, rng.below(i + 1));
    }
    if teams.len() % 2 == 1 {
        teams.push(None); // bye
    }
    let n = teams.len();
    let mut fixture = Vec::new();
    for day in 1..n as u32 {
        for i in 0..n / 2 {
            if let (Some(a), Some(b)) = (teams[i], teams[n - 1 - i]) {
                let (model1, model2) = if rng.below(2) == 0 { (a, b) } else { (b, a) };
                fixture.push((day, model1.clone(), model2.clone()));
            }
        }
        teams[1..].rotate_right(1);
    }
    fixture
}

pub async fn run(db_path: PathBuf, setup: &Setup, start: Start, harness: Harness) -> Result<()> {
    let mut league_id = None;
    let result = run_inner(&db_path, setup, start, harness, &mut league_id).await;
    if let Some(id) = league_id {
        // Lets `--resume` and `league-add` see at once that no runner holds the league.
        let _ = Db::open(&db_path).and_then(|db| db.clear_heartbeat(id));
    }
    result
}

/// `"12 s ago"`, or `"none"`.
pub fn ago(secs: Option<f64>) -> String {
    secs.map_or("none".to_owned(), |s| format!("{s:.0} s ago"))
}

async fn run_inner(
    db_path: &std::path::Path,
    setup: &Setup,
    start: Start,
    harness: Harness,
    league_id: &mut Option<i64>,
) -> Result<()> {
    let db_path = db_path.to_path_buf();
    let db = Db::open(&db_path)?;
    let id = match start {
        Start::New {
            models,
            seed,
            rounds,
            clock,
            max_turns,
            note,
            version,
            order_seed,
            mirror_concurrent,
        } => {
            let id = db.create_league(
                seed,
                rounds,
                clock,
                max_turns,
                &models,
                note.as_deref(),
                version.id(),
                order_seed,
                mirror_concurrent,
            )?;
            let names: Vec<String> = models.into_iter().map(|m| m.name).collect();
            add_fixtures(&db, id, &names, seed)?;
            id
        }
        Start::Resume(id) => {
            let activity = db.league_activity(id)?;
            if activity.playing() {
                bail!(
                    "league #{id} is being played by another process (heartbeat {}, last turn \
                     of a running match {}); a current runner picks up added players by itself, \
                     otherwise resume after it stops",
                    ago(activity.heartbeat_secs),
                    ago(activity.running_turn_secs)
                );
            }
            id
        }
    };
    *league_id = Some(id);
    let row = db.league(id)?;
    let version = match &row.prompt_version {
        Some(id) => PromptVersion::parse(id)?,
        None => LEGACY_VERSION,
    };
    let protocol = Arc::new(Protocol {
        version,
        order_seed: row
            .order_seed
            .unwrap_or_else(|| derive_seed(row.seed, "option order")),
        harness,
    });
    let control = Arc::new(Control::new(MAX_SPEED));
    let interrupt = control.clone();
    tokio::spawn(async move {
        let Ok(mut terminate) =
            tokio::signal::unix::signal(tokio::signal::unix::SignalKind::terminate())
        else {
            return;
        };
        let signal = tokio::select! {
            Ok(()) = tokio::signal::ctrl_c() => "Ctrl-C",
            Some(()) = terminate.recv() => "SIGTERM",
            else => return,
        };
        println!(
            "{signal}: stopping; matches in progress keep their stored turns and resume from \
             there with --resume"
        );
        interrupt.cancel();
    });
    let league = Arc::new(League {
        db_path: db_path.clone(),
        id,
        seed: row.seed,
        rounds: row.rounds,
        clock: row.clock,
        max_turns: row.max_turns,
        mirror_concurrent: row.mirror_concurrent,
        names: RwLock::new(row.models.iter().map(|m| m.name.clone()).collect()),
        players: RwLock::new(HashMap::new()),
        control,
        protocol: protocol.clone(),
        backoff: (FIRST_BACKOFF, MAX_BACKOFF),
    });
    println!(
        "league #{id}: {} models · {} rounds per match · games of a round {} · clock {} · turn \
         limit {} · seed {} · prompt {} · option-order seed {} · harness {}{} · db {}",
        league.names.read().len(),
        league.rounds,
        if league.mirror_concurrent {
            "at once (both show the round-start score)"
        } else {
            "one after the other"
        },
        describe_clock(league.clock),
        league.max_turns.map_or("off".to_owned(), |t| t.to_string()),
        league.seed,
        protocol.version.id(),
        protocol.order_seed,
        protocol.harness.commit.as_deref().unwrap_or("unknown"),
        if protocol.harness.dirty {
            " (dirty)"
        } else {
            ""
        },
        db_path.display()
    );
    let mut state = State::default();
    state.sync(&db, &league, setup).await?;
    for config in &row.models {
        println!(
            "  {}: {}{}",
            config.name,
            config.spec,
            league.players.read().get(&config.name).map_or(
                " (not ready, see above)".to_owned(),
                |entrant| format!(
                    " · {} at once · {} decisions in flight",
                    match entrant.max_matches {
                        usize::MAX => "any number of matches".to_owned(),
                        1 => "1 match".to_owned(),
                        n => format!("{n} matches"),
                    },
                    config
                        .parallel
                        .map_or("any number of".to_owned(), |n| format!("up to {n}"))
                )
            )
        );
    }
    println!("\nFixture");
    for fixture in state.played.iter().map(|(f, _)| f).chain(&state.pending) {
        println!("  {}", fixture.label);
    }
    if !state.played.is_empty() {
        print_table(
            &format!(
                "Table so far ({} of {} matches played)",
                state.played.len(),
                state.known.len()
            ),
            &table(&league.names.read(), &results_of(&state.played)),
        );
    }
    play_league(league, &db, setup, state).await
}

/// The round robin's fixtures (`draw_fixture`), each match seeded from the league seed and
/// its label.
fn add_fixtures(db: &Db, id: i64, names: &[String], seed: u64) -> Result<()> {
    for (day, model1, model2) in draw_fixture(names, seed) {
        let label = format!("matchday {day}: {model1} v {model2}");
        let seed = derive_seed(seed, &label);
        db.add_fixture(id, "league", &label, Some(day), &model1, &model2, seed)?;
    }
    Ok(())
}

/// Plays the league stage, then the playoffs, and stores the final ranking. A failing match
/// is deferred and its failing model backs off while the other matches go on; when only
/// deferred matches are left, the league waits for the backoffs and retries rather than
/// stopping. Returns early only on a stop request (Ctrl-C, SIGTERM).
async fn play_league(league: Arc<League>, db: &Db, setup: &Setup, mut state: State) -> Result<()> {
    let id = league.id;
    let stopped = || {
        anyhow::anyhow!(
            "league #{id} stopped on request; finished matches are kept and unfinished ones \
             resume from their last stored turn: `jevgammon league --resume {id} --db {}`",
            league.db_path.display()
        )
    };
    let mut running: HashMap<String, usize> = HashMap::new();
    let mut backoffs = Backoffs::default();
    let mut set = JoinSet::new();
    // Whether the current wait with nothing to play was explained in the log.
    let mut waiting_told = false;
    // League stage, then playoffs; again when players were added meanwhile.
    loop {
        let mut tick = tokio::time::interval(RELOAD);
        loop {
            if !league.control.is_cancelled() {
                let now = Instant::now();
                let limits: HashMap<String, usize> = league
                    .players
                    .read()
                    .iter()
                    .map(|(name, entrant)| (name.clone(), entrant.max_matches))
                    .collect();
                let started = take_startable(
                    &mut state.pending,
                    &mut running,
                    |name| limits.get(name).copied().unwrap_or(0),
                    |fixture| backoffs.holding(fixture, now).is_some(),
                );
                for fixture in started {
                    waiting_told = false;
                    let league = league.clone();
                    set.spawn(async move {
                        let result = league.play(&fixture, false).await;
                        (fixture, result)
                    });
                }
            }
            if set.is_empty() {
                if league.control.is_cancelled() {
                    return Err(stopped());
                }
                if state.pending.is_empty() && state.skipped == 0 {
                    break;
                }
                if !waiting_told {
                    waiting_told = true;
                    let now = Instant::now();
                    println!(
                        "waiting: no match can start now; {} unfinished, each tried again when \
                         its backoff ends:",
                        state.pending.len() + state.skipped
                    );
                    for fixture in &state.pending {
                        let why = backoffs
                            .holding(fixture, now)
                            .map_or("starts next".to_owned(), |(who, b)| {
                                format!("{who} backs off {}: {}", b.describe(now), b.error)
                            });
                        println!("  {}: {why}", fixture.label);
                    }
                    if state.skipped > 0 {
                        println!(
                            "  {} more of models whose client is not ready (tried every 30 s): {}",
                            state.skipped,
                            state
                                .unbuilt
                                .iter()
                                .map(|(name, error)| format!("{name}: {error}"))
                                .collect::<Vec<_>>()
                                .join("; ")
                        );
                    }
                }
            }
            let wake = backoffs.next_end(Instant::now());
            tokio::select! {
                joined = set.join_next(), if !set.is_empty() => {
                    let (fixture, result) = joined.expect("not empty")?;
                    for name in [&fixture.model1, &fixture.model2] {
                        if let Some(count) = running.get_mut(name) {
                            *count -= 1;
                        }
                    }
                    match result {
                        Ok(result) => {
                            backoffs.clear(&fixture);
                            let day = fixture.matchday;
                            state.played.push((fixture, result));
                            if let Some(day) = day {
                                let remaining =
                                    state.left.get_mut(&day).expect("counted on sync");
                                *remaining -= 1;
                                if *remaining == 0 {
                                    print_table(
                                        &format!(
                                            "Table after matchday {day} ({} of {} matches played)",
                                            state.played.len(),
                                            state.known.len()
                                        ),
                                        &table(&league.names.read(), &results_of(&state.played)),
                                    );
                                }
                            }
                        }
                        // Stopped on request: the match resumes with the next run.
                        Err(_) if league.control.is_cancelled() => {}
                        Err(error) => {
                            let backoff =
                                backoffs.fail(&fixture, &error, Instant::now(), league.backoff);
                            league.defer(&fixture, &error, &backoff);
                            state.requeue(fixture);
                        }
                    }
                }
                _ = tick.tick() => {
                    if let Err(error) = state.sync(db, &league, setup).await {
                        println!("league #{id}: reading the league failed, retried in 30 s: {error:#}");
                    }
                }
                _ = tokio::time::sleep_until(wake.unwrap_or_else(Instant::now).into()),
                    if wake.is_some() => {}
                _ = league.control.cancelled(), if !league.control.is_cancelled() => {}
            }
        }
        // Playoffs wait until every fixture, added ones included, is done.
        if state.sync(db, &league, setup).await? > 0 {
            continue;
        }
        let names = league.names.read().clone();
        let rows = table(&names, &results_of(&state.played));
        let mut ranking: Vec<String> = rows.iter().map(|r| r.name.clone()).collect();
        // Places of unresolved ties outside the playoff places: (start, end) shares one place.
        let mut shared = Vec::new();
        for group in tie_groups(&rows) {
            let members: Vec<String> = ranking[group.clone()].to_vec();
            if group.start >= PLAYOFF_PLACES {
                shared.push(group);
                continue;
            }
            let key = format!("playoff for places {}-{}", group.start + 1, group.end);
            println!(
                "\n{key}: {} are level on points, games won, and games lost",
                members.join(", ")
            );
            let ordered = league.order(members, key).await?;
            ranking.splice(group, ordered);
        }
        // A player added during the playoffs makes them stale: play the new matches, then
        // rank and play off again.
        if state.sync(db, &league, setup).await? > 0 {
            let stale = db.mark_playoffs_stale(id)?;
            println!(
                "players were added during the playoffs: {stale} playoff fixtures marked stale"
            );
            continue;
        }
        let places: Vec<usize> = (0..ranking.len())
            .map(|i| {
                shared
                    .iter()
                    .find(|g| g.contains(&i))
                    .map_or(i + 1, |g| g.start + 1)
            })
            .collect();
        print_table("Final table (league stage)", &rows);
        println!("\nFinal ranking");
        for (name, place) in ranking.iter().zip(&places) {
            let tied = places.iter().filter(|p| *p == place).count() > 1;
            println!("  {place}{} {name}", if tied { "=" } else { "." });
        }
        let stored: Vec<String> = ranking
            .iter()
            .zip(&places)
            .map(|(name, place)| format!("{place}. {name}"))
            .collect();
        db.finish_league(id, &stored)?;
        return Ok(());
    }
}

/// How often a running league checks for added players and signs its heartbeat.
const RELOAD: Duration = Duration::from_secs(30);

/// The fixtures a league run knows about.
#[derive(Default)]
struct State {
    /// Fixture ids already played or scheduled.
    known: HashSet<i64>,
    played: Vec<(FixtureRow, MatchResult)>,
    /// Unfinished fixtures in fixture order, deferred ones included.
    pending: Vec<FixtureRow>,
    /// Unfinished fixtures per matchday, for the table after each matchday.
    left: HashMap<u32, usize>,
    /// Models whose client could not be built yet, with the error.
    unbuilt: HashMap<String, String>,
    /// Unfinished fixtures of those models, left for a later sync: the league stage does
    /// not end before them.
    skipped: usize,
    /// Whether the first sync is done.
    synced: bool,
}

impl State {
    /// Signs the heartbeat, builds the roster's players not built yet (all of them on the
    /// first call, then players added since), and takes up league fixtures not seen yet.
    /// Returns how many unfinished fixtures it added. A player whose client cannot be
    /// built is tried again on the next call; its unfinished fixtures wait until then.
    async fn sync(&mut self, db: &Db, league: &League, setup: &Setup) -> Result<usize> {
        db.heartbeat(league.id)?;
        let row = db.league(league.id)?;
        for config in &row.models {
            if league.players.read().contains_key(&config.name) {
                continue;
            }
            if !league.names.read().contains(&config.name) {
                league.names.write().push(config.name.clone());
            }
            match Player::from_config(config, setup).await {
                Ok(player) => {
                    if self.synced {
                        println!("player ready: {} ({})", config.name, config.spec);
                    }
                    self.unbuilt.remove(&config.name);
                    league
                        .players
                        .write()
                        .insert(config.name.clone(), Entrant::new(config, player));
                }
                Err(error) => {
                    let error = format!("{error:#}");
                    if self.unbuilt.get(&config.name) != Some(&error) {
                        println!(
                            "{} ({}) is not ready, its matches wait (tried again every 30 s): \
                             {error}",
                            config.name, config.spec
                        );
                    }
                    self.unbuilt.insert(config.name.clone(), error);
                }
            }
        }
        let mut added = 0;
        self.skipped = 0;
        for fixture in db.fixtures(league.id, "league")? {
            if self.known.contains(&fixture.id) {
                continue;
            }
            let stored = match fixture.match_id {
                Some(match_id) => db.match_result(match_id)?,
                None => None,
            };
            if let Some(result) = stored {
                self.known.insert(fixture.id);
                self.played.push((fixture, result));
                continue;
            }
            {
                let players = league.players.read();
                if !players.contains_key(&fixture.model1) || !players.contains_key(&fixture.model2)
                {
                    self.skipped += 1;
                    continue;
                }
            }
            self.known.insert(fixture.id);
            if self.synced {
                println!("fixture picked up: {}", fixture.label);
            }
            if let Some(day) = fixture.matchday {
                *self.left.entry(day).or_default() += 1;
            }
            self.pending.push(fixture);
            added += 1;
        }
        self.synced = true;
        Ok(added)
    }

    /// Puts a deferred fixture back in fixture order.
    fn requeue(&mut self, fixture: FixtureRow) {
        let key = |f: &FixtureRow| (f.matchday, f.id);
        let at = self.pending.partition_point(|f| key(f) < key(&fixture));
        self.pending.insert(at, fixture);
    }
}

/// What `add_player` did.
pub struct Addition {
    pub fixtures: Vec<String>,
    pub stale_playoffs: usize,
    pub note: String,
}

/// The fixtures of a player joining a league: one match against every current player, all
/// on one new matchday after the last. Which side is `model1` is drawn from the league seed
/// and the pairing; each match seed is `derive_seed(league seed, label)`, the rule of the
/// original fixture.
fn added_fixtures(
    seed: u64,
    matchday: u32,
    new: &str,
    others: &[String],
) -> Vec<(u32, String, String, String, u64)> {
    others
        .iter()
        .map(|other| {
            let side = derive_seed(seed, &format!("added: {new} v {other}"));
            let (model1, model2) = if side & 1 == 0 {
                (new, other.as_str())
            } else {
                (other.as_str(), new)
            };
            let label = format!("matchday {matchday}: {model1} v {model2}");
            let match_seed = derive_seed(seed, &label);
            (
                matchday,
                label,
                model1.to_owned(),
                model2.to_owned(),
                match_seed,
            )
        })
        .collect()
}

/// Adds `config` to league `id`: roster entry, its fixtures against every current player,
/// and the note; earlier playoffs are marked stale. Playing the matches is left to a
/// running league process (it picks them up within `RELOAD`) or to `--resume`.
pub fn add_player(db: &mut Db, id: i64, config: &PlayerConfig, date: &str) -> Result<Addition> {
    let row = db.league(id)?;
    if config.name.is_empty() || row.models.iter().any(|m| m.name == config.name) {
        bail!(
            "the added player needs a name not yet in league #{id}: `{}`",
            config.name
        );
    }
    let others: Vec<String> = row.models.iter().map(|m| m.name.clone()).collect();
    let matchday = db.max_matchday(id)? + 1;
    let fixtures = added_fixtures(row.seed, matchday, &config.name, &others);
    let note = format!("{} added on {date}.", config.name);
    let stale_playoffs = db.add_league_player(id, config, &fixtures, &note)?;
    Ok(Addition {
        fixtures: fixtures.into_iter().map(|f| f.1).collect(),
        stale_playoffs,
        note,
    })
}

impl League {
    /// The result of `fixture`: stored when it already finished, otherwise played now. A
    /// match started before (cut off by a failure, a stop, or the process dying) resumes
    /// from its last stored turn under its match id.
    async fn play(&self, fixture: &FixtureRow, decisive: bool) -> Result<MatchResult> {
        let db = Db::open(&self.db_path)?;
        let existing = db.fixture_match(fixture.id)?;
        if let Some(match_id) = existing
            && let Some(result) = db.match_result(match_id)?
        {
            return Ok(result);
        }
        let names = [fixture.model1.clone(), fixture.model2.clone()];
        let players = {
            let players = self.players.read();
            let player = |name: &String| {
                players
                    .get(name)
                    .map(|entrant| entrant.player.clone())
                    .with_context(|| format!("{name} is not ready"))
            };
            [player(&names[0])?, player(&names[1])?]
        };
        let tag = &fixture.label;
        for (index, (name, player)) in names.iter().zip(&players).enumerate() {
            let took = player
                .warm_up()
                .await
                .with_context(|| format!("warming up {name}"))
                .context(PlayerFault(index as u8 + 1))?;
            if took > Duration::from_secs(5) {
                println!("[{tag}] {name} warmed up in {} s", took.as_secs());
            }
        }
        let match_id = match existing {
            Some(match_id) => {
                db.resume_match(match_id)?;
                println!("[{tag}] match #{match_id} resumes");
                match_id
            }
            None => {
                let match_id = db.create_match(
                    &players[0].spec,
                    &players[1].spec,
                    fixture.seed,
                    self.rounds,
                    self.clock,
                    self.max_turns,
                    &self.protocol,
                )?;
                db.set_fixture_match(fixture.id, match_id)?;
                println!("[{tag}] match #{match_id} starts");
                match_id
            }
        };
        let (events, mut receiver) = mpsc::unbounded_channel();
        let runner = Runner {
            db: parking_lot::Mutex::new(db),
            players,
            settings: MatchSettings {
                match_id,
                seed: fixture.seed,
                rounds: self.rounds,
                clock: self.clock,
                max_turns: self.max_turns,
                decisive,
                concurrent_mirror: self.mirror_concurrent,
                protocol: self.protocol.clone(),
            },
            events,
            control: self.control.clone(),
        };
        let report = async {
            while let Some(event) = receiver.recv().await {
                match event {
                    Event::Resumed {
                        round,
                        leg,
                        turn_no,
                        score,
                        ..
                    } => println!(
                        "[{tag}] round {round} game {leg} resumes at turn {turn_no} · {} {} - {} {}",
                        names[0], score[0], score[1], names[1]
                    ),
                    Event::GameOver {
                        round,
                        leg,
                        winner,
                        kind,
                        score,
                    } => println!(
                        "[{tag}] round {round} game {leg}: {} wins {} (+{}) · {} {} - {} {}",
                        names[winner as usize - 1],
                        kind.describe(),
                        kind.points(),
                        names[0],
                        score[0],
                        score[1],
                        names[1]
                    ),
                    Event::MatchOver {
                        score,
                        winner,
                        rounds,
                    } => println!(
                        "[{tag}] final after {rounds} rounds: {} {} - {} {} · {}",
                        names[0],
                        score[0],
                        score[1],
                        names[1],
                        winner.map_or("draw".to_owned(), |w| format!(
                            "{} wins",
                            names[w as usize - 1]
                        ))
                    ),
                    Event::Failed(message) => println!("[{tag}] stopped: {message}"),
                    _ => {}
                }
            }
        };
        let (result, ()) = tokio::join!(runner.run(), report);
        result
    }

    /// Logs a failed match and stores the failure with its fixture; `backoff` says who
    /// waits for how long.
    fn defer(&self, fixture: &FixtureRow, error: &anyhow::Error, backoff: &str) {
        let message = format!("{error:#}");
        println!(
            "[{}] deferred: {message}\n[{}] {backoff}; the match resumes from its last stored \
             turn then, other matches go on",
            fixture.label, fixture.label
        );
        if let Err(error) =
            Db::open(&self.db_path).and_then(|db| db.defer_fixture(fixture.id, &message))
        {
            println!("[{}] storing the failure failed: {error:#}", fixture.label);
        }
    }

    /// `play` until the match finishes (playoffs, played one at a time): after a failure
    /// the match waits out a doubling backoff and resumes. Only a stop request ends it.
    async fn play_until_done(&self, fixture: &FixtureRow, decisive: bool) -> Result<MatchResult> {
        let mut backoff: Option<Backoff> = None;
        loop {
            let error = match self.play(fixture, decisive).await {
                Ok(result) => return Ok(result),
                Err(error) if self.control.is_cancelled() => return Err(error),
                Err(error) => error,
            };
            let now = Instant::now();
            let next = Backoff::after(backoff.as_ref(), format!("{error:#}"), now, self.backoff);
            let who = blamed(fixture, &error).unwrap_or("the match");
            self.defer(
                fixture,
                &error,
                &format!("{who} backs off {}", next.describe(now)),
            );
            tokio::select! {
                _ = tokio::time::sleep(next.delay) => {}
                _ = self.control.cancelled() => bail!("cancelled"),
            }
            backoff = Some(next);
        }
    }

    /// Orders a tied group by playoff: one decisive match for two models; for more, a
    /// decisive round robin ranked like the league, with its own ties played off again.
    fn order(
        &self,
        mut group: Vec<String>,
        key: String,
    ) -> Pin<Box<dyn Future<Output = Result<Vec<String>>> + Send + '_>> {
        Box::pin(async move {
            group.sort();
            let db = Db::open(&self.db_path)?;
            let mut results = Vec::new();
            for i in 0..group.len() {
                for j in i + 1..group.len() {
                    let (a, b) = (&group[i], &group[j]);
                    let label = format!("{key}: {a} v {b}");
                    let seed = derive_seed(self.seed, &label);
                    let (model1, model2) = if seed & 1 == 0 { (a, b) } else { (b, a) };
                    let fixture =
                        db.add_fixture(self.id, "playoff", &label, None, model1, model2, seed)?;
                    let result = self.play_until_done(&fixture, true).await?;
                    results.push((fixture.model1, fixture.model2, result));
                }
            }
            let rows = table(&group, &results);
            let mut ordered: Vec<String> = rows.iter().map(|r| r.name.clone()).collect();
            if group.len() > 2 {
                print_table(&key, &rows);
            }
            for tie in tie_groups(&rows) {
                let sub_key = format!("{key} > places {}-{}", tie.start + 1, tie.end);
                let sub = self.order(ordered[tie.clone()].to_vec(), sub_key).await?;
                ordered.splice(tie, sub);
            }
            Ok(ordered)
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn names(n: usize) -> Vec<String> {
        (0..n).map(|i| format!("m{i}")).collect()
    }

    fn fixture(id: i64, day: u32, model1: &str, model2: &str) -> FixtureRow {
        FixtureRow {
            id,
            label: format!("matchday {day}: {model1} v {model2}"),
            matchday: Some(day),
            model1: model1.into(),
            model2: model2.into(),
            seed: 0,
            match_id: None,
        }
    }

    #[test]
    fn a_match_starts_while_both_models_are_below_their_limit_in_fixture_order() {
        let mut pending = vec![
            fixture(1, 1, "A", "B"),
            fixture(2, 1, "C", "D"),
            fixture(3, 2, "A", "C"),
            fixture(4, 2, "B", "D"),
            fixture(5, 3, "A", "D"),
            fixture(6, 3, "B", "C"),
        ];
        // A plays two matches at once, R (a local engine) any number, the others one.
        let limit = |name: &str| match name {
            "A" => 2,
            "R" => usize::MAX,
            _ => 1,
        };
        let free = |_: &FixtureRow| false;
        let mut running: HashMap<String, usize> = HashMap::new();
        let ids = |started: Vec<FixtureRow>| started.iter().map(|f| f.id).collect::<Vec<_>>();
        let end = |running: &mut HashMap<String, usize>, a: &str, b: &str| {
            *running.get_mut(a).unwrap() -= 1;
            *running.get_mut(b).unwrap() -= 1;
        };
        assert_eq!(
            ids(take_startable(&mut pending, &mut running, limit, free)),
            [1, 2]
        );
        // C v D ends while A v B still runs: A v C starts as A's second match; B v D still
        // waits for B, A v D for A.
        end(&mut running, "C", "D");
        assert_eq!(
            ids(take_startable(&mut pending, &mut running, limit, free)),
            [3]
        );
        assert_eq!(running["A"], 2);
        // A v B ends: B v D goes first; A v D now waits for D, B v C for B and C.
        end(&mut running, "A", "B");
        assert_eq!(
            ids(take_startable(&mut pending, &mut running, limit, free)),
            [4]
        );
        end(&mut running, "A", "C");
        end(&mut running, "B", "D");
        // C backs off: its match waits, the next one starts.
        let c_backs_off = |f: &FixtureRow| f.model1 == "C" || f.model2 == "C";
        assert_eq!(
            ids(take_startable(
                &mut pending,
                &mut running,
                limit,
                c_backs_off
            )),
            [5]
        );
        assert_eq!(
            ids(take_startable(&mut pending, &mut running, limit, free)),
            [6]
        );
        assert!(pending.is_empty());
        // An engine without a limit plays all its matches at once.
        let mut pending = vec![
            fixture(7, 4, "R", "E"),
            fixture(8, 5, "F", "R"),
            fixture(9, 6, "R", "G"),
        ];
        assert_eq!(
            ids(take_startable(&mut pending, &mut running, limit, free)),
            [7, 8, 9]
        );
        assert_eq!(running["R"], 3);
    }

    #[test]
    fn backoff_doubles_up_to_the_longest_and_blames_the_failing_player() {
        let limits = (Duration::from_secs(120), Duration::from_secs(600));
        let now = Instant::now();
        let first = Backoff::after(None, "402".into(), now, limits);
        assert_eq!((first.delay, first.failures), (limits.0, 1));
        // Another failure while it runs (a second match of the player) keeps it.
        let same = Backoff::after(Some(&first), "402 again".into(), now, limits);
        assert_eq!((same.until, same.failures), (first.until, 1));
        let mut last = first;
        for delay in [240, 480, 600, 600] {
            let at = last.until;
            last = Backoff::after(Some(&last), "402".into(), at, limits);
            assert_eq!(last.delay, Duration::from_secs(delay));
            assert_eq!(last.until, at + last.delay);
        }
        assert_eq!(last.failures, 5);

        let f = fixture(1, 1, "A", "B");
        let failed = anyhow::anyhow!("402 Payment Required")
            .context(PlayerFault(2))
            .context("round 1");
        assert_eq!(blamed(&f, &failed), Some("B"));
        assert_eq!(blamed(&f, &anyhow::anyhow!("database is locked")), None);
        let mut backoffs = Backoffs::default();
        backoffs.fail(&f, &failed, now, limits);
        let other = fixture(2, 2, "A", "C");
        let (who, backoff) = backoffs.holding(&f, now).unwrap();
        assert_eq!(
            (who, backoff.error.as_str()),
            ("B", "round 1: player 2: 402 Payment Required")
        );
        assert!(backoffs.holding(&other, now).is_none());
        assert!(backoffs.holding(&f, now + limits.0).is_none());
        assert_eq!(backoffs.next_end(now), Some(now + limits.0));
        // A failure no player is to blame for holds the match only.
        backoffs.fail(&other, &anyhow::anyhow!("disk full"), now, limits);
        assert_eq!(backoffs.holding(&other, now).unwrap().0, "the match");
        assert!(backoffs.holding(&fixture(3, 3, "A", "D"), now).is_none());
        backoffs.clear(&f);
        assert!(backoffs.holding(&f, now).is_none());
    }

    #[test]
    fn fixture_is_a_round_robin_with_one_match_per_model_per_matchday() {
        for n in [7, 8] {
            let names = names(n);
            let fixture = draw_fixture(&names, 11);
            let mut pairs: Vec<(String, String)> = fixture
                .iter()
                .map(|(_, a, b)| {
                    if a < b {
                        (a.clone(), b.clone())
                    } else {
                        (b.clone(), a.clone())
                    }
                })
                .collect();
            pairs.sort();
            pairs.dedup();
            assert_eq!(pairs.len(), n * (n - 1) / 2);
            assert_eq!(fixture.len(), pairs.len());
            let days = if n % 2 == 0 { n - 1 } else { n };
            for day in 1..=days as u32 {
                let mut seen: Vec<&String> = fixture
                    .iter()
                    .filter(|f| f.0 == day)
                    .flat_map(|(_, a, b)| [a, b])
                    .collect();
                let count = seen.len();
                seen.sort();
                seen.dedup();
                assert_eq!(seen.len(), count, "a model plays twice on matchday {day}");
                assert_eq!(count, n / 2 * 2);
            }
        }
        assert_ne!(draw_fixture(&names(8), 1), draw_fixture(&names(8), 2));
    }

    fn result(score: [u32; 2], games_won: [u32; 2]) -> MatchResult {
        let winner = match score[0].cmp(&score[1]) {
            std::cmp::Ordering::Greater => Some(1),
            std::cmp::Ordering::Less => Some(2),
            std::cmp::Ordering::Equal => None,
        };
        MatchResult {
            score,
            games_won,
            winner,
        }
    }

    #[test]
    fn table_ranks_by_points_then_games_won_then_fewer_games_lost() {
        let names = names(4);
        let r = |a: usize, b: usize, score, games| {
            (names[a].clone(), names[b].clone(), result(score, games))
        };
        let order = |rows: &[Row]| rows.iter().map(|r| r.name.clone()).collect::<Vec<_>>();

        // Equal points: more games won ranks higher (m1 over m0, m2 over m3).
        let rows = table(&names, &[r(0, 2, [7, 5], [6, 4]), r(1, 3, [9, 3], [7, 3])]);
        assert_eq!(order(&rows), ["m1", "m0", "m2", "m3"]);

        // Equal points and games won: fewer games lost ranks higher. m1 beat m2 in ten
        // games, m0 needed an extra round.
        let rows = table(
            &names[..3],
            &[r(0, 2, [7, 5], [6, 5]), r(1, 2, [7, 5], [6, 4])],
        );
        assert_eq!(order(&rows), ["m1", "m0", "m2"]);
        assert!(tie_groups(&rows).is_empty());

        // A draw is worth DRAW_POINTS; a win by fewer games still outranks it.
        let rows = table(&names, &[r(0, 1, [6, 6], [6, 6]), r(2, 3, [4, 3], [2, 1])]);
        assert_eq!(order(&rows)[0], "m2");
        assert_eq!(rows[1].points, DRAW_POINTS);
        // m0 and m1 are level on everything.
        assert_eq!(tie_groups(&rows), vec![1..3]);
    }

    /// Adding a player to a league with a finished playoff: one match against every
    /// current player on a new matchday, seeds from the league seed and the label, the
    /// roster and note updated, the playoff kept but marked stale.
    #[test]
    fn added_player_gets_one_match_against_each_player() {
        let path = std::env::temp_dir().join(format!("jevgammon-add-{}.db", std::process::id()));
        let _ = std::fs::remove_file(&path);
        let mut db = Db::open(&path).unwrap();
        let models: Vec<PlayerConfig> = ["A", "B", "C"]
            .iter()
            .map(|n| PlayerConfig::new(n, "random"))
            .collect();
        let id = db
            .create_league(7, 1, None, None, &models, Some("test."), "bg-v2", 9, false)
            .unwrap();
        let names: Vec<String> = models.iter().map(|m| m.name.clone()).collect();
        for (day, m1, m2) in draw_fixture(&names, 7) {
            let label = format!("matchday {day}: {m1} v {m2}");
            db.add_fixture(
                id,
                "league",
                &label,
                Some(day),
                &m1,
                &m2,
                derive_seed(7, &label),
            )
            .unwrap();
        }
        db.add_fixture(
            id,
            "playoff",
            "playoff for places 1-2: A v B",
            None,
            "A",
            "B",
            1,
        )
        .unwrap();
        db.finish_league(id, &["1. A".into()]).unwrap();
        let before = db.fixtures(id, "league").unwrap();
        let last_day = db.max_matchday(id).unwrap();

        let addition =
            add_player(&mut db, id, &PlayerConfig::new("D", "safest"), "2026-10-15").unwrap();
        assert_eq!(addition.fixtures.len(), 3);
        assert_eq!(addition.stale_playoffs, 1);
        let after = db.fixtures(id, "league").unwrap();
        assert_eq!(after.len(), before.len() + 3);
        for fixture in &after[before.len()..] {
            assert_eq!(fixture.matchday, Some(last_day + 1));
            assert!(fixture.model1 == "D" || fixture.model2 == "D");
            assert_eq!(fixture.seed, derive_seed(7, &fixture.label));
            assert!(fixture.match_id.is_none());
        }
        let mut opponents: Vec<&str> = after[before.len()..]
            .iter()
            .map(|f| {
                if f.model1 == "D" {
                    f.model2.as_str()
                } else {
                    f.model1.as_str()
                }
            })
            .collect();
        opponents.sort_unstable();
        assert_eq!(opponents, ["A", "B", "C"]);
        // Same league seed and names, same fixtures.
        assert_eq!(
            added_fixtures(7, last_day + 1, "D", &names),
            after[before.len()..]
                .iter()
                .map(|f| (
                    last_day + 1,
                    f.label.clone(),
                    f.model1.clone(),
                    f.model2.clone(),
                    f.seed
                ))
                .collect::<Vec<_>>()
        );
        let row = db.league(id).unwrap();
        assert_eq!(row.models.last().unwrap().name, "D");
        assert!(db.fixtures(id, "playoff").unwrap().is_empty());
        assert_eq!(db.fixtures(id, "playoff-stale").unwrap().len(), 1);
        // The note and the running status.
        let activity = db.league_activity(id).unwrap();
        assert!(!activity.playing());
        assert!(add_player(&mut db, id, &PlayerConfig::new("D", "random"), "x").is_err());
        drop(db);
        let conn = rusqlite::Connection::open(&path).unwrap();
        let (note, status): (String, String) = conn
            .query_row(
                "SELECT note, status FROM leagues WHERE id = ?1",
                [id],
                |r| Ok((r.get(0)?, r.get(1)?)),
            )
            .unwrap();
        assert_eq!(note, "test. D added on 2026-10-15.");
        assert_eq!(status, "running");
        let _ = std::fs::remove_file(&path);
    }

    /// Plays like `random` while `fail` is false; otherwise every decision fails like a
    /// provider out of credit.
    struct Flaky {
        fail: Arc<std::sync::atomic::AtomicBool>,
    }

    impl crate::players::Engine for Flaky {
        fn decide(
            &self,
            req: &crate::players::DecisionRequest<'_>,
        ) -> Result<crate::players::Decision> {
            if self.fail.load(std::sync::atomic::Ordering::Relaxed) {
                bail!("402 Payment Required: insufficient credits");
            }
            crate::players::baseline::Baseline::Random.decide(req)
        }
    }

    /// `(model1, model2, match id, match status, fixture error)`.
    type StageRow = (String, String, Option<i64>, Option<String>, Option<String>);

    /// The league stage's fixtures.
    fn league_stage(path: &std::path::Path, id: i64) -> Vec<StageRow> {
        let conn = rusqlite::Connection::open(path).unwrap();
        let mut statement = conn
            .prepare(
                "SELECT lm.model1, lm.model2, lm.match_id, m.status, lm.error
                 FROM league_matches lm LEFT JOIN matches m ON m.id = lm.match_id
                 WHERE lm.league_id = ?1 AND lm.stage = 'league' ORDER BY lm.id",
            )
            .unwrap();
        statement
            .query_map([id], |r| {
                Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?, r.get(4)?))
            })
            .unwrap()
            .collect::<rusqlite::Result<_>>()
            .unwrap()
    }

    /// F fails like a provider out of credit: its matches are deferred with the error
    /// stored and only F backs off, so every other match (F's opponents' included)
    /// finishes while F still fails, and the league neither stops nor starts its playoffs.
    /// A stop request ends the run cleanly; once F works again, the next run resumes F's
    /// matches under their match ids and finishes the league.
    #[tokio::test(flavor = "multi_thread", worker_threads = 4)]
    async fn a_failing_model_backs_off_while_the_others_play_on_and_its_matches_resume() {
        use crate::players::baseline::Baseline;
        let path = std::env::temp_dir().join(format!("jevgammon-flaky-{}.db", std::process::id()));
        let _ = std::fs::remove_file(&path);
        let db = Db::open(&path).unwrap();
        let names: Vec<String> = ["A", "B", "C", "F"].map(String::from).to_vec();
        let models: Vec<PlayerConfig> = names
            .iter()
            .map(|n| PlayerConfig::new(n, "random"))
            .collect();
        let id = db
            .create_league(5, 1, None, Some(300), &models, None, "bg-v2", 9, true)
            .unwrap();
        add_fixtures(&db, id, &names, 5).unwrap();
        let fail = Arc::new(std::sync::atomic::AtomicBool::new(true));
        let setup = Setup::new(std::env::temp_dir(), "http://127.0.0.1:9/v1".into());
        let league = || {
            let players = models
                .iter()
                .map(|config| {
                    let player = if config.name == "F" {
                        Player::engine("flaky", Box::new(Flaky { fail: fail.clone() }))
                    } else {
                        Player::engine("random", Box::new(Baseline::Random))
                    };
                    (config.name.clone(), Entrant::new(config, player))
                })
                .collect();
            Arc::new(League {
                db_path: path.clone(),
                id,
                seed: 5,
                rounds: 1,
                clock: None,
                max_turns: Some(300),
                mirror_concurrent: true,
                names: RwLock::new(names.clone()),
                players: RwLock::new(players),
                control: Arc::new(Control::new(MAX_SPEED)),
                protocol: Arc::new(Protocol {
                    version: PromptVersion::BgV2,
                    order_seed: 9,
                    harness: Harness::default(),
                }),
                // Long enough that F is not tried again during the first run.
                backoff: (Duration::from_secs(3600), Duration::from_secs(3600)),
            })
        };
        let with_f = |row: &StageRow| row.0 == "F" || row.1 == "F";
        let finished = |row: &StageRow| row.3.as_deref() == Some("finished");

        let first = league();
        let mut state = State::default();
        state.sync(&db, &first, &setup).await.unwrap();
        let watch = async {
            loop {
                let stage = league_stage(&path, id);
                if stage.iter().filter(|r| !with_f(r)).all(finished) {
                    break;
                }
                tokio::time::sleep(Duration::from_millis(50)).await;
            }
            first.control.cancel();
        };
        let (stopped, ()) = tokio::time::timeout(Duration::from_secs(120), async {
            tokio::join!(play_league(first.clone(), &db, &setup, state), watch)
        })
        .await
        .expect("the matches without F finish while F fails");
        assert!(
            format!("{:#}", stopped.unwrap_err()).contains("stopped on request"),
            "only the stop request ends the run"
        );
        let stage = league_stage(&path, id);
        let deferred: Vec<_> = stage.iter().filter(|r| with_f(r)).collect();
        assert_eq!(deferred.len(), 3);
        for row in &deferred {
            assert!(!finished(row), "{row:?}");
            let error = row
                .4
                .as_deref()
                .expect("the failure is stored with the fixture");
            assert!(error.contains("402 Payment Required"), "{error}");
            assert!(error.starts_with("player "), "{error}");
        }
        let match_ids: Vec<Option<i64>> = deferred.iter().map(|r| r.2).collect();
        assert!(match_ids.iter().all(Option::is_some));
        let (status,): (String,) = rusqlite::Connection::open(&path)
            .unwrap()
            .query_row("SELECT status FROM leagues WHERE id = ?1", [id], |r| {
                Ok((r.get(0)?,))
            })
            .unwrap();
        assert_eq!(
            status, "running",
            "no playoffs or final ranking without F's matches"
        );

        fail.store(false, std::sync::atomic::Ordering::Relaxed);
        let second = league();
        let mut state = State::default();
        state.sync(&db, &second, &setup).await.unwrap();
        assert_eq!(state.pending.len(), 3);
        tokio::time::timeout(
            Duration::from_secs(120),
            play_league(second, &db, &setup, state),
        )
        .await
        .expect("the league finishes")
        .unwrap();
        let stage = league_stage(&path, id);
        assert!(stage.iter().all(finished), "{stage:?}");
        let resumed: Vec<Option<i64>> = stage.iter().filter(|r| with_f(r)).map(|r| r.2).collect();
        assert_eq!(
            resumed, match_ids,
            "F's matches resumed under their match ids"
        );
        let (status, ranking): (String, String) = rusqlite::Connection::open(&path)
            .unwrap()
            .query_row(
                "SELECT status, ranking FROM leagues WHERE id = ?1",
                [id],
                |r| Ok((r.get(0)?, r.get(1)?)),
            )
            .unwrap();
        assert_eq!(status, "finished");
        assert!(ranking.contains('F'));
        drop(db);
        let _ = std::fs::remove_file(&path);
    }
}
