//! League: a single round robin between models on a random fixture. A match starts as soon
//! as both its models are free, in fixture order, so a model never plays two matches at
//! once but never waits for a whole matchday to finish either. Ties in the table are
//! broken by more games won, then fewer games lost; a tie still standing that decides any
//! of the first three places goes to a playoff.

use std::collections::{HashMap, HashSet};
use std::path::PathBuf;
use std::pin::Pin;
use std::sync::Arc;
use std::time::Duration;

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
    Clock, Control, Event, Harness, MAX_SPEED, MatchResult, MatchSettings, Protocol, Runner,
    describe_clock,
};

/// League points for a match won, drawn, lost.
const WIN_POINTS: u32 = 3;
const DRAW_POINTS: u32 = 1;
/// Places a playoff decides when the table leaves them tied.
const PLAYOFF_PLACES: usize = 3;
/// Attempts per match: a failed match (e.g. a provider outage outlasting the HTTP
/// retries) is replayed from the start with the same seed after `RETRY_PAUSE`.
const MATCH_ATTEMPTS: u32 = 3;
const RETRY_PAUSE: Duration = Duration::from_secs(120);

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
    /// Entry order; players added later come last.
    names: RwLock<Vec<String>>,
    players: RwLock<HashMap<String, Arc<Player>>>,
    control: Arc<Control>,
    protocol: Arc<Protocol>,
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

/// Removes from `pending`, in order, every fixture whose two models are both free, and
/// marks them busy. Earlier fixtures go first, so the matchday order holds wherever it can.
fn take_startable(pending: &mut Vec<FixtureRow>, busy: &mut HashSet<String>) -> Vec<FixtureRow> {
    let mut started = Vec::new();
    let mut i = 0;
    while i < pending.len() {
        let fixture = &pending[i];
        if busy.contains(&fixture.model1) || busy.contains(&fixture.model2) {
            i += 1;
            continue;
        }
        busy.insert(fixture.model1.clone());
        busy.insert(fixture.model2.clone());
        started.push(pending.remove(i));
    }
    started
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
            )?;
            let names: Vec<String> = models.into_iter().map(|m| m.name).collect();
            for (day, model1, model2) in draw_fixture(&names, seed) {
                let label = format!("matchday {day}: {model1} v {model2}");
                let seed = derive_seed(seed, &label);
                db.add_fixture(id, "league", &label, Some(day), &model1, &model2, seed)?;
            }
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
    let mut players = HashMap::new();
    for config in &row.models {
        let player = Player::from_config(config, setup)
            .await
            .with_context(|| format!("{} ({})", config.name, config.spec))?;
        players.insert(config.name.clone(), Arc::new(player));
    }
    let control = Arc::new(Control::new(MAX_SPEED));
    let interrupt = control.clone();
    tokio::spawn(async move {
        if tokio::signal::ctrl_c().await.is_ok() {
            interrupt.cancel();
        }
    });
    let league = Arc::new(League {
        db_path: db_path.clone(),
        id,
        seed: row.seed,
        rounds: row.rounds,
        clock: row.clock,
        max_turns: row.max_turns,
        names: RwLock::new(row.models.iter().map(|m| m.name.clone()).collect()),
        players: RwLock::new(players),
        control,
        protocol: protocol.clone(),
    });
    println!(
        "league #{id}: {} models · {} rounds per match · clock {} · turn limit {} · seed {} · \
         prompt {} · option-order seed {} · harness {}{} · db {}",
        league.names.read().len(),
        league.rounds,
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
    for config in &row.models {
        println!("  {}: {}", config.name, config.spec);
    }
    let mut state = State::default();
    state.sync(&db, &league, setup, true).await?;
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
    let mut busy = HashSet::new();
    let mut set = JoinSet::new();
    let mut failures: Vec<String> = Vec::new();
    // League stage, then playoffs; again when players were added meanwhile.
    loop {
        let mut tick = tokio::time::interval(RELOAD);
        loop {
            // After a failure no new match starts; the running ones finish first.
            if failures.is_empty() {
                for fixture in take_startable(&mut state.pending, &mut busy) {
                    let league = league.clone();
                    set.spawn(async move {
                        let result = league.play_retrying(&fixture, false).await;
                        (fixture, result)
                    });
                }
            }
            if set.is_empty() && (state.pending.is_empty() || !failures.is_empty()) {
                break;
            }
            tokio::select! {
                joined = set.join_next(), if !set.is_empty() => {
                    let (fixture, result) = joined.expect("not empty")?;
                    busy.remove(&fixture.model1);
                    busy.remove(&fixture.model2);
                    let day = fixture.matchday;
                    match result {
                        Ok(result) => state.played.push((fixture, result)),
                        Err(error) => failures.push(format!("{}: {error:#}", fixture.label)),
                    }
                    if let Some(day) = day {
                        let remaining = state.left.get_mut(&day).expect("counted on sync");
                        *remaining -= 1;
                        if *remaining == 0 && failures.is_empty() {
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
                _ = tick.tick() => {
                    if let Err(error) = state.sync(&db, &league, setup, false).await {
                        failures.push(format!("picking up added players: {error:#}"));
                    }
                }
            }
        }
        if !failures.is_empty() {
            bail!(
                "league #{id} stopped:\n  {}\nfinished matches are kept; resume with \
                 `jevgammon league --resume {id} --db {}`",
                failures.join("\n  "),
                db_path.display()
            );
        }
        // Playoffs wait until every fixture, added ones included, is done.
        if state.sync(&db, &league, setup, false).await? > 0 {
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
        if state.sync(&db, &league, setup, false).await? > 0 {
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
    pending: Vec<FixtureRow>,
    /// Unfinished fixtures per matchday, for the table after each matchday.
    left: HashMap<u32, usize>,
}

impl State {
    /// Signs the heartbeat, builds players added to the roster since, and takes up league
    /// fixtures not seen yet (all of them on the first call). Returns how many unplayed
    /// fixtures it added. Fixtures of a player whose client cannot be built yet are left
    /// for a later call.
    async fn sync(
        &mut self,
        db: &Db,
        league: &League,
        setup: &Setup,
        first: bool,
    ) -> Result<usize> {
        db.heartbeat(league.id)?;
        if !first {
            let row = db.league(league.id)?;
            for config in &row.models {
                if league.players.read().contains_key(&config.name) {
                    continue;
                }
                let player = Player::from_config(config, setup)
                    .await
                    .with_context(|| format!("added player {} ({})", config.name, config.spec))?;
                println!("added player picked up: {} ({})", config.name, config.spec);
                league
                    .players
                    .write()
                    .insert(config.name.clone(), Arc::new(player));
                league.names.write().push(config.name.clone());
            }
        }
        let mut added = 0;
        for fixture in db.fixtures(league.id, "league")? {
            if self.known.contains(&fixture.id) {
                continue;
            }
            {
                let players = league.players.read();
                if !players.contains_key(&fixture.model1) || !players.contains_key(&fixture.model2)
                {
                    continue;
                }
            }
            self.known.insert(fixture.id);
            let stored = match fixture.match_id {
                Some(match_id) => db.match_result(match_id)?,
                None => None,
            };
            match stored {
                Some(result) => self.played.push((fixture, result)),
                None => {
                    if !first {
                        println!("added fixture picked up: {}", fixture.label);
                    }
                    if let Some(day) = fixture.matchday {
                        *self.left.entry(day).or_default() += 1;
                    }
                    self.pending.push(fixture);
                    added += 1;
                }
            }
        }
        Ok(added)
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
    /// `play`, replaying a failed match up to `MATCH_ATTEMPTS` times in all.
    async fn play_retrying(&self, fixture: &FixtureRow, decisive: bool) -> Result<MatchResult> {
        let mut attempt = 1;
        loop {
            match self.play(fixture, decisive).await {
                Ok(result) => return Ok(result),
                Err(error) if attempt < MATCH_ATTEMPTS && !self.control.is_cancelled() => {
                    println!(
                        "[{}] attempt {attempt} of {MATCH_ATTEMPTS} failed: {error:#}; replaying \
                         from the start in {} s",
                        fixture.label,
                        RETRY_PAUSE.as_secs()
                    );
                    tokio::select! {
                        _ = tokio::time::sleep(RETRY_PAUSE) => {}
                        _ = self.control.cancelled() => bail!("cancelled"),
                    }
                    attempt += 1;
                }
                Err(error) => return Err(error),
            }
        }
    }

    /// The result of `fixture`: stored when it already finished, otherwise played now
    /// (an earlier aborted attempt is replayed from the start with the same seed).
    async fn play(&self, fixture: &FixtureRow, decisive: bool) -> Result<MatchResult> {
        let db = Db::open(&self.db_path)?;
        if let Some(match_id) = fixture.match_id
            && let Some(result) = db.match_result(match_id)?
        {
            return Ok(result);
        }
        let names = [fixture.model1.clone(), fixture.model2.clone()];
        let players = {
            let players = self.players.read();
            [players[&names[0]].clone(), players[&names[1]].clone()]
        };
        let tag = &fixture.label;
        for (name, player) in names.iter().zip(&players) {
            let took = player
                .warm_up()
                .await
                .with_context(|| format!("{tag}: warming up {name}"))?;
            if took > Duration::from_secs(5) {
                println!("[{tag}] {name} warmed up in {} s", took.as_secs());
            }
        }
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
        let (events, mut receiver) = mpsc::unbounded_channel();
        let runner = Runner {
            db,
            players,
            settings: MatchSettings {
                match_id,
                seed: fixture.seed,
                rounds: self.rounds,
                clock: self.clock,
                max_turns: self.max_turns,
                decisive,
                protocol: self.protocol.clone(),
            },
            events,
            control: self.control.clone(),
        };
        let report = async {
            while let Some(event) = receiver.recv().await {
                match event {
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
                    Event::Failed(message) => println!("[{tag}] aborted: {message}"),
                    _ => {}
                }
            }
        };
        let (result, ()) = tokio::join!(runner.run(), report);
        result
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
                    let result = self.play_retrying(&fixture, true).await?;
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
    fn a_match_starts_when_both_models_are_free_not_when_the_matchday_ends() {
        let mut pending = vec![
            fixture(1, 1, "A", "B"),
            fixture(2, 1, "C", "D"),
            fixture(3, 2, "C", "E"),
            fixture(4, 2, "A", "D"),
        ];
        let mut busy = HashSet::new();
        let ids = |started: Vec<FixtureRow>| started.iter().map(|f| f.id).collect::<Vec<_>>();
        // C v E waits for C, even though E has a bye.
        assert_eq!(ids(take_startable(&mut pending, &mut busy)), [1, 2]);
        // C v D ends while A v B still runs: C v E starts; A v D still waits for A.
        busy.remove("C");
        busy.remove("D");
        assert_eq!(ids(take_startable(&mut pending, &mut busy)), [3]);
        busy.remove("A");
        busy.remove("B");
        assert_eq!(ids(take_startable(&mut pending, &mut busy)), [4]);
        assert!(pending.is_empty());
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
            .create_league(7, 1, None, None, &models, Some("test."), "bg-v2", 9)
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
}
