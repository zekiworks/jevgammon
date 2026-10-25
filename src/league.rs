//! League: a single round robin between its current participants. The fixture is implicit:
//! every pair of current participants without a valid match is still to play, in a
//! matchday order derived from the participants (founders by a round robin drawn from the
//! league seed, each late joiner on a matchday of its own after it). A pair plays at most
//! once: its valid match from any league, ladder round or Cup counts here too, whatever
//! rules it was played under; new matches are played under the league's rules.
//! A match starts as soon as both its models can take another one (`max_matches` each), in
//! fixture order, so the matchday order holds wherever it can but nobody waits for a whole
//! matchday. A match that fails is deferred and resumed later from its last stored turn;
//! only the failing model backs off, the others play on. The table ranks by points, then
//! more games won, then fewer games lost, then the lower error rate over all of a setup's
//! valid matches (`scores`); there are no playoffs. A league can play only one setup's pairs
//! (an early start of its matches for a coming ladder round) and be hidden from the site,
//! the dashboard and the ladder tools (`Scope`).

use std::collections::{HashMap, HashSet};
use std::path::PathBuf;
use std::sync::Arc;
use std::time::{Duration, Instant};

use anyhow::{Context, Result, bail};
use parking_lot::RwLock;
use serde::Deserialize;
use tokio::sync::mpsc;
use tokio::task::JoinSet;

use crate::db::{Db, MatchRow, NewMatch, Participant, Rules, Scope};
use crate::dice::{Dice, derive_seed};
use crate::players::prompt::PromptVersion;
use crate::players::{Player, PlayerConfig, Setup};
use crate::runner::{
    Control, Event, Harness, MAX_SPEED, MatchResult, MatchSettings, PlayerFault, Protocol, Runner,
    describe_clock,
};
use crate::scores;

/// League points for a match won, drawn, lost.
const WIN_POINTS: u32 = 3;
const DRAW_POINTS: u32 = 1;
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
        rules: Rules,
        /// What this league tests; shown in the history.
        note: Option<String>,
        scope: Scope,
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
    /// Play only this player's pairs (`Scope::only_pairs_of`); every pair when left out.
    pub only_pairs_of: Option<String>,
    /// Leave the league out of the site, the dashboard and the ladder tools (default false).
    pub hidden: Option<bool>,
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
    /// Orders the founders' round robin.
    seed: u64,
    rules: Rules,
    /// Play only this participant's pairs (`Scope::only_pairs_of`).
    only_pairs_of: Option<String>,
    /// Current participants in join order.
    names: RwLock<Vec<String>>,
    /// Player ids of the current participants by name.
    ids: RwLock<HashMap<String, i64>>,
    players: RwLock<HashMap<String, Entrant>>,
    control: Arc<Control>,
    protocol: Arc<Protocol>,
    /// First and longest backoff after failures.
    backoff: (Duration, Duration),
    /// The site's GNUbg score shards, for the error-rate tiebreak (`scores::error_rates`).
    scores: PathBuf,
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

/// A match of the league: one pair of current participants.
#[derive(Clone, Debug)]
struct Fixture {
    /// Position in the derived fixture; earlier fixtures start first.
    order: usize,
    /// `matchday 3: A v B`.
    label: String,
    matchday: u32,
    /// model1 plays white in the first game of every round.
    model1: String,
    model2: String,
    /// Player ids of model1 and model2.
    players: [i64; 2],
    /// Seed of a new match; an existing match keeps its own.
    seed: u64,
    /// The pair's valid match and its status, once created.
    match_id: Option<i64>,
    status: Option<String>,
}

impl Fixture {
    /// The pair, lower player id first.
    fn key(&self) -> (i64, i64) {
        let [a, b] = self.players;
        (a.min(b), a.max(b))
    }

    /// The same match with the sides the other way round.
    fn swap(&mut self) {
        std::mem::swap(&mut self.model1, &mut self.model2);
        self.players.swap(0, 1);
        self.label = format!(
            "matchday {}: {} v {}",
            self.matchday, self.model1, self.model2
        );
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
    /// Error rate over all of the setup's valid matches; `None` when none is scored.
    error_rate: Option<f64>,
}

impl Row {
    /// Ranking order, better first: league points, then games won, then fewer games lost,
    /// then the lower error rate (a row without one after a row with one).
    fn rank(&self, other: &Row) -> std::cmp::Ordering {
        other
            .points
            .cmp(&self.points)
            .then(other.games_won.cmp(&self.games_won))
            .then(self.games_lost.cmp(&other.games_lost))
            .then(match (self.error_rate, other.error_rate) {
                (Some(a), Some(b)) => a.total_cmp(&b),
                (Some(_), None) => std::cmp::Ordering::Less,
                (None, Some(_)) => std::cmp::Ordering::Greater,
                (None, None) => std::cmp::Ordering::Equal,
            })
    }
}

/// The table for `names` over `results`, best first (`Row::rank`, with each name's error
/// rate from `rates`); rows equal on everything keep `names` order. Results of players
/// outside `names` (they left the league) are left out.
fn table(
    names: &[String],
    results: &[(String, String, MatchResult)],
    rates: &HashMap<String, f64>,
) -> Vec<Row> {
    let mut rows: Vec<Row> = names
        .iter()
        .map(|name| Row {
            name: name.clone(),
            error_rate: rates.get(name).copied(),
            ..Row::default()
        })
        .collect();
    let index: HashMap<&str, usize> = names
        .iter()
        .enumerate()
        .map(|(i, n)| (n.as_str(), i))
        .collect();
    for (model1, model2, result) in results {
        let (Some(&one), Some(&two)) = (index.get(model1.as_str()), index.get(model2.as_str()))
        else {
            continue;
        };
        for (side, at) in [one, two].into_iter().enumerate() {
            let row = &mut rows[at];
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
    rows.sort_by(Row::rank);
    rows
}

/// Places of a sorted table, from 1: rows equal on everything share the first one's place.
fn places(rows: &[Row]) -> Vec<usize> {
    let mut out: Vec<usize> = Vec::with_capacity(rows.len());
    for i in 0..rows.len() {
        let shared = i > 0 && rows[i - 1].rank(&rows[i]).is_eq();
        out.push(if shared { out[i - 1] } else { i + 1 });
    }
    out
}

/// The final ranking as stored in `leagues.ranking`: `"place. name"`, best first.
fn ranking(rows: &[Row]) -> Vec<String> {
    rows.iter()
        .zip(places(rows))
        .map(|(row, place)| format!("{place}. {}", row.name))
        .collect()
}

fn print_table(title: &str, rows: &[Row]) {
    let width = rows.iter().map(|r| r.name.len()).max().unwrap_or(5).max(5);
    println!("\n{title}");
    println!(
        "  #  {:width$}   P   W   D   L  Pts   GW   GL    PF    PA    Err",
        "Model"
    );
    for (place, row) in places(rows).into_iter().zip(rows) {
        println!(
            " {:>2}  {:width$} {:>3} {:>3} {:>3} {:>3} {:>4} {:>4} {:>4} {:>5} {:>5} {:>6}",
            place,
            row.name,
            row.played,
            row.won,
            row.drawn,
            row.lost,
            row.points,
            row.games_won,
            row.games_lost,
            row.scored,
            row.conceded,
            row.error_rate.map_or("-".to_owned(), |e| format!("{e:.1}"))
        );
    }
}

/// Removes from `pending`, in order, every fixture whose two models are below their match
/// limit (`limit`, against the matches counted in `running`) and not held back by
/// `waiting`, and counts it in `running`. Earlier fixtures go first, so the matchday order
/// holds wherever it can.
fn take_startable(
    pending: &mut Vec<Fixture>,
    running: &mut HashMap<String, usize>,
    limit: impl Fn(&str) -> usize,
    waiting: impl Fn(&Fixture) -> bool,
) -> Vec<Fixture> {
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

/// Running backoffs by model name and by pair.
#[derive(Default)]
struct Backoffs {
    players: HashMap<String, Backoff>,
    fixtures: HashMap<(i64, i64), Backoff>,
}

impl Backoffs {
    /// The running backoff that keeps `fixture` from starting at `now`, with what backs off
    /// (a model's name, or "the match").
    fn holding<'a>(&'a self, fixture: &'a Fixture, now: Instant) -> Option<(&'a str, &'a Backoff)> {
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
                    .get(&fixture.key())
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
        fixture: &Fixture,
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
                let key = fixture.key();
                let backoff = Backoff::after(self.fixtures.get(&key), message, now, limits);
                let text = format!("the match is retried {}", backoff.describe(now));
                self.fixtures.insert(key, backoff);
                text
            }
        }
    }

    /// A match of `fixture` finished: its models and the match work again.
    fn clear(&mut self, fixture: &Fixture) {
        self.players.remove(&fixture.model1);
        self.players.remove(&fixture.model2);
        self.fixtures.remove(&fixture.key());
    }
}

/// The model of `fixture` whose decision or warm-up caused `error`, if one did.
fn blamed<'a>(fixture: &'a Fixture, error: &anyhow::Error) -> Option<&'a str> {
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
fn results_of(played: &[(Fixture, MatchResult)]) -> Vec<(String, String, MatchResult)> {
    let mut sorted: Vec<_> = played.iter().collect();
    sorted.sort_by_key(|(fixture, _)| fixture.order);
    sorted
        .into_iter()
        .map(|(f, result)| (f.model1.clone(), f.model2.clone(), *result))
        .collect()
}

/// Single round robin by the circle method on `items` shuffled with the league seed:
/// `(matchday, a, b)` from 1.
fn round_robin(items: &[usize], seed: u64) -> Vec<(u32, usize, usize)> {
    let mut rng = Dice::new(derive_seed(seed, "fixture"));
    let mut teams: Vec<Option<usize>> = items.iter().copied().map(Some).collect();
    for i in (1..teams.len()).rev() {
        teams.swap(i, rng.below(i + 1));
    }
    if teams.len() % 2 == 1 {
        teams.push(None); // bye
    }
    let n = teams.len();
    let mut pairs = Vec::new();
    for day in 1..n as u32 {
        for i in 0..n / 2 {
            if let (Some(a), Some(b)) = (teams[i], teams[n - 1 - i]) {
                pairs.push((day, a, b));
            }
        }
        teams[1..].rotate_right(1);
    }
    pairs
}

/// Every pair of `participants` (indices) in fixture order, with its matchday: the
/// founders (those who joined first, together) by `round_robin`, then each later joiner in
/// join order on a matchday of its own against everyone who joined before it.
/// `tools/league_web.py` derives the same order.
fn pair_order(participants: &[Participant], seed: u64) -> Vec<(u32, usize, usize)> {
    let mut join: Vec<usize> = (0..participants.len()).collect();
    join.sort_by_key(|&i| (&participants[i].joined_at, i));
    let Some(&first) = join.first() else {
        return Vec::new();
    };
    let founded = &participants[first].joined_at;
    let founders = join
        .iter()
        .take_while(|&&i| participants[i].joined_at == *founded)
        .count();
    let mut pairs = round_robin(&join[..founders], seed);
    let last = pairs.last().map_or(0, |p| p.0);
    for (day, k) in (last + 1..).zip(founders..join.len()) {
        pairs.extend(join[..k].iter().map(|&earlier| (day, earlier, join[k])));
    }
    pairs
}

/// The league stage: every pair of current participants in `pair_order`, each with its
/// valid match from `matches` (stored side and seed) or, without one, the side and seed of
/// its last voided match (so a voided pair replays the same dice), else from the pair's
/// names and the rules (`Rules::sides`, `Rules::pair_seed`).
fn derive_fixture(
    seed: u64,
    rules: &Rules,
    participants: &[Participant],
    matches: &[MatchRow],
) -> Vec<Fixture> {
    /// The pair's valid match and its last voided one.
    type Known<'a> = (Option<&'a MatchRow>, Option<&'a MatchRow>);
    let mut by_pair: HashMap<(i64, i64), Known> = HashMap::new();
    for row in matches {
        let entry = by_pair.entry(row.pair()).or_default();
        if row.valid {
            entry.0.get_or_insert(row);
        } else {
            entry.1 = Some(row);
        }
    }
    pair_order(participants, seed)
        .into_iter()
        .enumerate()
        .map(|(order, (day, i, j))| {
            let (a, b) = (&participants[i], &participants[j]);
            let key = (a.player_id.min(b.player_id), a.player_id.max(b.player_id));
            let (valid, void) = by_pair.get(&key).copied().unwrap_or_default();
            let (first, seed) = match valid.or(void) {
                Some(row) => (row.player1, row.seed),
                None => {
                    let (model1, _) = rules.sides(&a.config.name, &b.config.name);
                    let first = if model1 == a.config.name { a } else { b };
                    (
                        first.player_id,
                        rules.pair_seed(&a.config.name, &b.config.name),
                    )
                }
            };
            let (one, two) = if first == a.player_id { (a, b) } else { (b, a) };
            Fixture {
                order,
                label: format!("matchday {day}: {} v {}", one.config.name, two.config.name),
                matchday: day,
                model1: one.config.name.clone(),
                model2: two.config.name.clone(),
                players: [one.player_id, two.player_id],
                seed,
                match_id: valid.map(|row| row.id),
                status: valid.map(|row| row.status.clone()),
            }
        })
        .collect()
}

/// The pairs a league plays: every derived pair, or only those of `only_pairs_of`.
fn in_scope(fixtures: Vec<Fixture>, only_pairs_of: Option<&str>) -> Vec<Fixture> {
    match only_pairs_of {
        None => fixtures,
        Some(name) => fixtures
            .into_iter()
            .filter(|f| f.model1 == name || f.model2 == name)
            .collect(),
    }
}

pub async fn run(
    db_path: PathBuf,
    setup: &Setup,
    start: Start,
    harness: Harness,
    scores: PathBuf,
) -> Result<()> {
    let mut league_id = None;
    let result = run_inner(&db_path, setup, start, harness, scores, &mut league_id).await;
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
    scores: PathBuf,
    league_id: &mut Option<i64>,
) -> Result<()> {
    let db_path = db_path.to_path_buf();
    let mut db = Db::open(&db_path)?;
    let id = match start {
        Start::New {
            models,
            seed,
            rules,
            note,
            scope,
        } => db.create_league(seed, &rules, &models, note.as_deref(), &scope)?,
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
    let version = match &row.rules.prompt_version {
        Some(id) => PromptVersion::parse(id)?,
        None => LEGACY_VERSION,
    };
    let protocol = Arc::new(Protocol {
        version,
        order_seed: row
            .rules
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
        rules: row.rules.clone(),
        only_pairs_of: row.scope.only_pairs_of.clone(),
        names: RwLock::new(Vec::new()),
        ids: RwLock::new(HashMap::new()),
        players: RwLock::new(HashMap::new()),
        control,
        protocol: protocol.clone(),
        backoff: (FIRST_BACKOFF, MAX_BACKOFF),
        scores,
    });
    let mut state = State::default();
    state.sync(&db, &league, setup).await?;
    println!(
        "league #{id}: {} models · {} rounds per match · games of a round {} · clock {} · turn \
         limit {} · seed {} · prompt {} · option-order seed {} · harness {}{} · db {}",
        league.names.read().len(),
        league.rules.rounds,
        if league.rules.mirror_concurrent {
            "at once (both show the round-start score)"
        } else {
            "one after the other"
        },
        describe_clock(league.rules.clock()),
        league
            .rules
            .max_turns
            .map_or("off".to_owned(), |t| t.to_string()),
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
    if let Some(name) = &league.only_pairs_of {
        println!("only the pairs of {name} are played");
    }
    if row.scope.hidden {
        println!("hidden: left out of the site, the dashboard and the ladder tools");
    }
    for participant in db.participants(id)? {
        let config = &participant.config;
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
    for fixture in &state.fixtures {
        println!("  {}", fixture.label);
    }
    if !state.played.is_empty() {
        print_table(
            &format!(
                "Table so far ({} of {} matches played)",
                state.played.len(),
                state.fixtures.len()
            ),
            &table(
                &league.names.read(),
                &results_of(&state.played),
                &league.rates(&db, false),
            ),
        );
    }
    play_league(league, &db, setup, state).await
}

/// Plays the league stage and stores the final ranking (`ranking`, no playoffs). A failing
/// match is deferred and its failing model backs off while the other matches go on; when
/// only deferred matches are left, the league waits for the backoffs and retries rather
/// than stopping. Returns early only on a stop request (Ctrl-C, SIGTERM).
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
    // League stage; again when players joined meanwhile.
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
                    state.running.insert(fixture.key());
                    let league = league.clone();
                    set.spawn(async move { league.play(fixture).await });
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
                    state.running.remove(&fixture.key());
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
                            if state.matchday_done(day) {
                                print_table(
                                    &format!(
                                        "Table after matchday {day} ({} of {} matches played)",
                                        state.played.len(),
                                        state.fixtures.len()
                                    ),
                                    &table(
                                        &league.names.read(),
                                        &results_of(&state.played),
                                        &league.rates(db, false),
                                    ),
                                );
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
        // The final ranking waits until every pair, joiners' included, is played.
        state.sync(db, &league, setup).await?;
        if !state.pending.is_empty() || state.skipped > 0 {
            continue;
        }
        let names = league.names.read().clone();
        let rows = table(&names, &results_of(&state.played), &league.rates(db, true));
        print_table("Final table", &rows);
        let stored = ranking(&rows);
        println!("\nFinal ranking");
        for line in &stored {
            println!("  {line}");
        }
        db.finish_league(id, &stored)?;
        return Ok(());
    }
}

/// How often a running league checks for joined and departed players and signs its
/// heartbeat.
const RELOAD: Duration = Duration::from_secs(30);

/// The league stage as a run sees it, rebuilt from the database on every sync.
#[derive(Default)]
struct State {
    /// Every pair of current participants, in fixture order.
    fixtures: Vec<Fixture>,
    played: Vec<(Fixture, MatchResult)>,
    /// Unfinished pairs in fixture order, deferred ones included, not running.
    pending: Vec<Fixture>,
    /// Pairs this run is playing now.
    running: HashSet<(i64, i64)>,
    /// Unfinished pairs seen so far, to log the ones picked up.
    seen: HashSet<(i64, i64)>,
    /// Models whose client could not be built yet, with the error.
    unbuilt: HashMap<String, String>,
    /// Unfinished pairs of those models, left for a later sync: the league stage does not
    /// end before them.
    skipped: usize,
    /// Whether the first sync is done.
    synced: bool,
}

impl State {
    /// Signs the heartbeat, reads the current participants (building the players not built
    /// yet and dropping those who left), and derives the fixture: played pairs, and pending
    /// ones not running. Returns how many unfinished pairs it saw for the first time. A
    /// player whose client cannot be built is tried again on the next call; its pairs wait
    /// until then.
    async fn sync(&mut self, db: &Db, league: &League, setup: &Setup) -> Result<usize> {
        db.heartbeat(league.id)?;
        let participants = db.participants(league.id)?;
        let current: HashSet<&str> = participants
            .iter()
            .map(|p| p.config.name.as_str())
            .collect();
        league
            .players
            .write()
            .retain(|name, _| current.contains(name.as_str()));
        self.unbuilt
            .retain(|name, _| current.contains(name.as_str()));
        *league.names.write() = participants.iter().map(|p| p.config.name.clone()).collect();
        *league.ids.write() = participants
            .iter()
            .map(|p| (p.config.name.clone(), p.player_id))
            .collect();
        for participant in &participants {
            let config = &participant.config;
            if league.players.read().contains_key(&config.name) {
                continue;
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
        let ids: Vec<i64> = participants.iter().map(|p| p.player_id).collect();
        let matches = db.matches_between(&ids)?;
        let fixtures = in_scope(
            derive_fixture(league.seed, &league.rules, &participants, &matches),
            league.only_pairs_of.as_deref(),
        );
        self.played.clear();
        self.pending.clear();
        self.skipped = 0;
        let mut added = 0;
        for fixture in &fixtures {
            if fixture.status.as_deref() == Some("finished")
                && let Some(match_id) = fixture.match_id
                && let Some(result) = db.match_result(match_id)?
            {
                self.played.push((fixture.clone(), result));
                continue;
            }
            if self.running.contains(&fixture.key()) {
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
            if self.seen.insert(fixture.key()) {
                added += 1;
                if self.synced {
                    println!("fixture picked up: {}", fixture.label);
                }
            }
            self.pending.push(fixture.clone());
        }
        self.fixtures = fixtures;
        self.synced = true;
        Ok(added)
    }

    /// Puts a deferred fixture back in fixture order.
    fn requeue(&mut self, fixture: Fixture) {
        let at = self.pending.partition_point(|f| f.order < fixture.order);
        self.pending.insert(at, fixture);
    }

    /// Whether every pair of matchday `day` is played.
    fn matchday_done(&self, day: u32) -> bool {
        let played: HashSet<(i64, i64)> = self.played.iter().map(|(f, _)| f.key()).collect();
        self.fixtures
            .iter()
            .filter(|f| f.matchday == day)
            .all(|f| played.contains(&f.key()))
    }
}

/// The unplayed league pairs of `name` in league `id` (within the league's scope), as labels
/// in fixture order.
fn open_pairs(db: &Db, id: i64, name: &str) -> Result<Vec<String>> {
    let row = db.league(id)?;
    let participants = db.participants(id)?;
    let ids: Vec<i64> = participants.iter().map(|p| p.player_id).collect();
    let matches = db.matches_between(&ids)?;
    Ok(in_scope(
        derive_fixture(row.seed, &row.rules, &participants, &matches),
        row.scope.only_pairs_of.as_deref(),
    )
    .into_iter()
    .filter(|f| (f.model1 == name || f.model2 == name) && f.status.as_deref() != Some("finished"))
    .map(|f| f.label)
    .collect())
}

/// What `add_player` did.
pub struct Addition {
    /// The joiner's unplayed pairs (pairs it already played elsewhere count as played).
    pub fixtures: Vec<String>,
    pub note: String,
}

/// Adds `config` to league `id` as a participant (its `players` row is created, or reused
/// when the name is known with the same settings) with a note. Its pairs with every current
/// participant that it has not played anywhere become pending: a running league process
/// picks them up within `RELOAD`, otherwise `--resume` plays them.
pub fn add_player(db: &mut Db, id: i64, config: &PlayerConfig, date: &str) -> Result<Addition> {
    let note = format!("{} added on {date}.", config.name);
    db.add_participant(id, config, &note)?;
    Ok(Addition {
        fixtures: open_pairs(db, id, &config.name)?,
        note,
    })
}

/// Ends `name`'s participation in league `id`: its matches stay valid (and count wherever it
/// meets the same opponent again) but leave the table, its unplayed pairs leave the
/// fixture. Returns how many pairs it had left to play.
pub fn remove_player(db: &mut Db, id: i64, name: &str, reason: &str) -> Result<usize> {
    let open = open_pairs(db, id, name)?.len();
    db.remove_participant(id, name, reason)?;
    Ok(open)
}

impl League {
    fn player(&self, name: &str) -> Result<Arc<Player>> {
        self.players
            .read()
            .get(name)
            .map(|entrant| entrant.player.clone())
            .with_context(|| format!("{name} is not ready"))
    }

    /// Error rates by name for the tiebreak (`scores::error_rates`). Without readable
    /// scores the map is empty and ties stay shared. `warn`: say which current
    /// participants have decisions not scored yet (their error rate is partial).
    fn rates(&self, db: &Db, warn: bool) -> HashMap<String, f64> {
        match scores::error_rates(db, &self.scores) {
            Ok(all) => {
                if warn {
                    let names = self.names.read();
                    let partial: Vec<String> = names
                        .iter()
                        .filter_map(|n| {
                            all.get(n)
                                .filter(|r| r.pending > 0)
                                .map(|r| format!("{n} ({})", r.pending))
                        })
                        .collect();
                    if !partial.is_empty() {
                        println!(
                            "error rates: decisions not scored yet: {}; once the site update \
                             has scored them, `jevgammon rank --league {}` ranks again",
                            partial.join(", "),
                            self.id
                        );
                    }
                }
                tiebreak_rates(&all)
            }
            Err(error) => {
                println!("error rates unavailable, ties stay shared: {error:#}");
                HashMap::new()
            }
        }
    }

    /// The result of `fixture`'s match: stored when it already finished (in this league or
    /// anywhere else), otherwise played now. A match started before (cut off by a failure,
    /// a stop, or the process dying) resumes from its last stored turn under its match id.
    /// Returns the fixture with the sides of its match.
    async fn play(&self, mut fixture: Fixture) -> (Fixture, Result<MatchResult>) {
        let result = self.play_match(&mut fixture).await;
        (fixture, result)
    }

    async fn play_match(&self, fixture: &mut Fixture) -> Result<MatchResult> {
        let db = Db::open(&self.db_path)?;
        let existing = db.current_match(fixture.players)?;
        let current = match existing {
            Some(current) => current,
            None => {
                let specs = [
                    self.player(&fixture.model1)?.spec.clone(),
                    self.player(&fixture.model2)?.spec.clone(),
                ];
                db.ensure_league_match(&NewMatch {
                    rules: &self.rules,
                    label: &fixture.label,
                    players: fixture.players,
                    specs: [&specs[0], &specs[1]],
                    seed: fixture.seed,
                    protocol: &self.protocol,
                })?;
                db.current_match(fixture.players)?
                    .context("the created match is not found")?
            }
        };
        if let Some(result) = db.match_result(current.id)? {
            if current.player1 != fixture.players[0] {
                fixture.swap();
            }
            fixture.match_id = Some(current.id);
            return Ok(result);
        }
        let rules = db.match_rules(current.id)?;
        if rules != self.rules {
            bail!(
                "the pair's unfinished match #{} was started under other rules ({}); finish it \
                 where it started or void it (`jevgammon void`)",
                current.id,
                rules.canonical()
            );
        }
        if current.player1 != fixture.players[0] {
            fixture.swap();
        }
        fixture.match_id = Some(current.id);
        fixture.seed = current.seed;
        let names = [fixture.model1.clone(), fixture.model2.clone()];
        let players = [self.player(&names[0])?, self.player(&names[1])?];
        let tag = fixture.label.clone();
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
        let match_id = current.id;
        if existing.is_some() {
            db.resume_match(match_id)?;
            println!("[{tag}] match #{match_id} resumes");
        } else {
            println!("[{tag}] match #{match_id} starts");
        }
        let (events, mut receiver) = mpsc::unbounded_channel();
        let runner = Runner {
            db: parking_lot::Mutex::new(db),
            players,
            settings: MatchSettings {
                match_id,
                seed: current.seed,
                rounds: self.rules.rounds,
                clock: self.rules.clock(),
                max_turns: self.rules.max_turns,
                concurrent_mirror: self.rules.mirror_concurrent,
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

    /// Logs a failed match and stores the failure with its match; `backoff` says who waits
    /// for how long.
    fn defer(&self, fixture: &Fixture, error: &anyhow::Error, backoff: &str) {
        let message = format!("{error:#}");
        println!(
            "[{}] deferred: {message}\n[{}] {backoff}; the match resumes from its last stored \
             turn then, other matches go on",
            fixture.label, fixture.label
        );
        let stored =
            Db::open(&self.db_path).and_then(|db| match db.current_match(fixture.players)? {
                Some(current) => db.defer_match(current.id, &message),
                None => Ok(()),
            });
        if let Err(error) = stored {
            println!("[{}] storing the failure failed: {error:#}", fixture.label);
        }
    }
}

/// Converts the error rates of `scores::error_rates` to the tiebreak's map (setups with a
/// scored decision).
pub fn tiebreak_rates(all: &HashMap<String, scores::ErrorRate>) -> HashMap<String, f64> {
    all.iter()
        .filter_map(|(name, rate)| rate.rate().map(|r| (name.clone(), r)))
        .collect()
}

/// League `id`'s table rows as the runner ranks them, from the valid finished matches between
/// its current participants (from any league) within the league's scope, with `rates` for the
/// tiebreak.
fn league_rows(db: &Db, id: i64, rates: &HashMap<String, f64>) -> Result<Vec<Row>> {
    let row = db.league(id)?;
    let participants = db.participants(id)?;
    let ids: Vec<i64> = participants.iter().map(|p| p.player_id).collect();
    let matches = db.matches_between(&ids)?;
    let fixtures = in_scope(
        derive_fixture(row.seed, &row.rules, &participants, &matches),
        row.scope.only_pairs_of.as_deref(),
    );
    let mut played = Vec::new();
    for fixture in fixtures {
        if let Some(match_id) = fixture.match_id
            && let Some(result) = db.match_result(match_id)?
        {
            played.push((fixture, result));
        }
    }
    let names: Vec<String> = participants.iter().map(|p| p.config.name.clone()).collect();
    Ok(table(&names, &results_of(&played), rates))
}

/// The league stage's table of league `id` as `(name, P, W, D, L, Pts, GW, GL, PF, PA)`
/// lines, best first, without the error-rate tiebreak (rows level on points and games keep
/// the participants' order): what `jevgammon migrate` compares with the old layout.
pub fn standings(db: &Db, id: i64) -> Result<Vec<Standing>> {
    Ok(league_rows(db, id, &HashMap::new())?
        .into_iter()
        .map(Standing::from)
        .collect())
}

/// What `rank_league` found.
pub struct Ranked {
    /// `"place. name"`, best first, as `leagues.ranking` stores it.
    pub ranking: Vec<String>,
    /// Current participants with decisions not scored yet, and how many.
    pub unscored: Vec<(String, u64)>,
}

/// Prints league `id`'s final table with the error-rate tiebreak (error rates from the
/// score shards in `scores`) and returns its ranking (`jevgammon rank`).
pub fn rank_league(db: &Db, id: i64, scores: &std::path::Path) -> Result<Ranked> {
    let all = scores::error_rates(db, scores)?;
    let rows = league_rows(db, id, &tiebreak_rates(&all))?;
    print_table(&format!("League #{id}"), &rows);
    Ok(Ranked {
        ranking: ranking(&rows),
        unscored: rows
            .iter()
            .filter_map(|r| {
                all.get(&r.name)
                    .filter(|e| e.pending > 0)
                    .map(|e| (r.name.clone(), e.pending))
            })
            .collect(),
    })
}

/// One line of `standings`.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Standing {
    pub name: String,
    /// played, won, drawn, lost, points, games won, games lost, points for, points against
    pub counts: [u32; 9],
}

impl From<Row> for Standing {
    fn from(row: Row) -> Self {
        Standing {
            counts: [
                row.played,
                row.won,
                row.drawn,
                row.lost,
                row.points,
                row.games_won,
                row.games_lost,
                row.scored,
                row.conceded,
            ],
            name: row.name,
        }
    }
}

/// Ranks `(model1, model2, result)` lines for `names` like the league table does, without
/// the error-rate tiebreak.
pub fn rank(names: &[String], results: &[(String, String, MatchResult)]) -> Vec<Standing> {
    table(names, results, &HashMap::new())
        .into_iter()
        .map(Standing::from)
        .collect()
}

#[cfg(test)]
mod tests;
