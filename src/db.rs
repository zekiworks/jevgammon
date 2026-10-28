//! SQLite record of every match, game, roll, move, and model exchange, and of the leagues:
//! players (one row per setup), the leagues' settings and their participants. Two setups
//! play each other at most once: a pair's valid match is its result in every league (and
//! ladder round and Cup) whatever rules it was played under. A league's table is the valid
//! matches between two of its current participants; its fixtures are implicit (every pair
//! of current participants without a valid match is still to play, under the league's
//! rules).

use std::path::Path;
use std::time::Duration;

use anyhow::{Context, Result, bail};
use rusqlite::{Connection, OptionalExtension, params};
use serde_json::Value;

use crate::board::{Board, Side, StartPosition, WinKind};
use crate::dice::derive_seed;
use crate::players::PlayerConfig;
use crate::players::prompt::letter;
use crate::runner::{Clock, MatchResult, Protocol};

/// What a league plays its new matches under. A stored match counts in every league that
/// holds both its players, whatever rules it was played under (one result per pair); the
/// rules choose a new match's format and dice. Raw column values: a league stored before
/// prompt versions keeps `prompt_version` and `order_seed` NULL here, and so do its
/// matches. `start_position` is NULL (standard) for every league and match before it.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Rules {
    pub rounds: u32,
    pub clock_seconds: Option<u64>,
    pub delay_seconds: Option<u64>,
    pub max_turns: Option<u32>,
    pub prompt_version: Option<String>,
    pub order_seed: Option<u64>,
    pub mirror_concurrent: bool,
    /// The position every game starts from.
    pub start_position: StartPosition,
}

impl Rules {
    pub fn new(
        rounds: u32,
        clock: Option<Clock>,
        max_turns: Option<u32>,
        prompt_version: &str,
        order_seed: u64,
        mirror_concurrent: bool,
        start_position: StartPosition,
    ) -> Self {
        Rules {
            rounds,
            clock_seconds: clock.map(|c| c.bank.as_secs()),
            delay_seconds: clock.map(|c| c.delay.as_secs()),
            max_turns,
            prompt_version: Some(prompt_version.to_owned()),
            order_seed: Some(order_seed),
            mirror_concurrent,
            start_position,
        }
    }

    pub fn clock(&self) -> Option<Clock> {
        self.clock_seconds.map(|bank| Clock {
            bank: Duration::from_secs(bank),
            delay: Duration::from_secs(self.delay_seconds.unwrap_or(0)),
        })
    }

    /// The rules as one stable string (`tools/league_web.py` builds the same one). The
    /// standard start adds nothing, so the rules of every league before start positions
    /// keep their string, hash and dice.
    pub fn canonical(&self) -> String {
        fn opt<T: std::fmt::Display>(value: &Option<T>) -> String {
            value.as_ref().map_or("-".to_owned(), |v| v.to_string())
        }
        let mut out = format!(
            "rules-v1 rounds={} clock={} delay={} max_turns={} prompt={} order_seed={} mirror={}",
            self.rounds,
            opt(&self.clock_seconds),
            opt(&self.delay_seconds),
            opt(&self.max_turns),
            opt(&self.prompt_version),
            opt(&self.order_seed),
            u8::from(self.mirror_concurrent)
        );
        if self.start_position != StartPosition::Standard {
            out.push_str(" start=");
            out.push_str(self.start_position.id());
        }
        out
    }

    /// Hash of the rules, the root of every pair's dice seed.
    pub fn hash(&self) -> u64 {
        derive_seed(0, &self.canonical())
    }

    /// Dice seed of a league match between `a` and `b` under these rules: the same pair
    /// gets the same dice in every league with the same rules, whatever the league.
    pub fn pair_seed(&self, a: &str, b: &str) -> u64 {
        let (low, high) = if a <= b { (a, b) } else { (b, a) };
        derive_seed(self.hash(), &format!("pair: {low} v {high}"))
    }

    /// `(model1, model2)` of a new match between `a` and `b`: drawn from the pair seed, so
    /// it does not depend on the order the two are given in.
    pub fn sides<'a>(&self, a: &'a str, b: &'a str) -> (&'a str, &'a str) {
        let (low, high) = if a <= b { (a, b) } else { (b, a) };
        if derive_seed(self.pair_seed(a, b), "side") & 1 == 0 {
            (low, high)
        } else {
            (high, low)
        }
    }

    /// Column values in `RULES_COLUMNS` order.
    fn values(&self) -> [rusqlite::types::Value; 8] {
        use rusqlite::types::Value;
        let int = |v: Option<i64>| v.map_or(Value::Null, Value::Integer);
        [
            Value::Integer(self.rounds as i64),
            int(self.clock_seconds.map(|s| s as i64)),
            int(self.delay_seconds.map(|s| s as i64)),
            int(self.max_turns.map(i64::from)),
            self.prompt_version.clone().map_or(Value::Null, Value::Text),
            int(self.order_seed.map(|s| s as i64)),
            Value::Integer(i64::from(self.mirror_concurrent)),
            start_position_value(self.start_position),
        ]
    }
}

/// `start_position` column value: NULL for the standard start (as before the column).
fn start_position_value(start: StartPosition) -> rusqlite::types::Value {
    match start {
        StartPosition::Standard => rusqlite::types::Value::Null,
        other => rusqlite::types::Value::Text(other.id().to_owned()),
    }
}

/// A `start_position` column: NULL is the standard start.
impl rusqlite::types::FromSql for StartPosition {
    fn column_result(value: rusqlite::types::ValueRef<'_>) -> rusqlite::types::FromSqlResult<Self> {
        match value {
            rusqlite::types::ValueRef::Null => Ok(StartPosition::Standard),
            _ => StartPosition::parse(value.as_str()?)
                .map_err(|error| rusqlite::types::FromSqlError::Other(error.into())),
        }
    }
}

/// Rule columns of `matches`, in `Rules::values` order (`leagues` names the first `rounds`).
const RULES_COLUMNS: [&str; 8] = [
    "rounds_planned",
    "clock_seconds",
    "delay_seconds",
    "max_turns",
    "prompt_version",
    "order_seed",
    "mirror_concurrent",
    "start_position",
];

/// The matches that are a pair's result (`m` aliases `matches`): valid, of any stage but the
/// legacy playoffs (a second match of a pair, played before the error-rate tiebreak).
pub const PAIR_RESULT: &str = "m.valid = 1 AND m.stage IS NOT NULL AND m.stage <> 'playoff'";

/// How the dice seed of a new league match is chosen (`leagues.seed_rule`): from the two
/// player names and the rules hash (`Rules::pair_seed`), or the stored seed of an earlier
/// voided match of the pair (a voided pair replays with the same dice).
pub const SEED_RULE: &str = "pair-v1";

/// Opens `path` for concurrent use (WAL, one connection per league match).
pub fn connect(path: &Path) -> Result<Connection> {
    let conn = Connection::open(path).with_context(|| format!("opening {}", path.display()))?;
    conn.busy_timeout(Duration::from_secs(60))?;
    conn.execute_batch("PRAGMA journal_mode = WAL; PRAGMA foreign_keys = ON;")?;
    Ok(conn)
}

fn has_column(conn: &Connection, table: &str, column: &str) -> Result<bool> {
    Ok(conn.query_row(
        "SELECT COUNT(*) > 0 FROM pragma_table_info(?1) WHERE name = ?2",
        params![table, column],
        |row| row.get(0),
    )?)
}

/// Whether the database still keeps rosters in `leagues.models` (before `jevgammon migrate`).
pub fn legacy_layout(conn: &Connection) -> Result<bool> {
    has_column(conn, "leagues", "models")
}

/// Creates missing tables and adds missing columns.
pub fn ensure_schema(conn: &Connection) -> Result<()> {
    conn.execute_batch(SCHEMA).context("creating schema")?;
    for (table, column, kind) in ADDED_COLUMNS {
        if !has_column(conn, table, column)? {
            conn.execute_batch(&format!("ALTER TABLE {table} ADD COLUMN {column} {kind}"))
                .with_context(|| format!("adding {table}.{column}"))?;
        }
    }
    Ok(())
}

/// Indexes and the league view (needs the columns of `ensure_schema`). The view is replaced
/// when its stored definition differs from `LEAGUE_MATCH_VIEW` (a database from an earlier
/// definition), and left alone otherwise.
pub fn ensure_derived_schema(conn: &Connection) -> Result<()> {
    conn.execute_batch(DERIVED_SCHEMA)
        .context("creating indexes")?;
    let stored: Option<String> = conn
        .query_row(
            "SELECT sql FROM sqlite_master WHERE type = 'view' AND name = 'league_match_view'",
            [],
            |row| row.get(0),
        )
        .optional()?;
    if stored.as_deref() != Some(LEAGUE_MATCH_VIEW.trim()) {
        conn.execute_batch(&format!(
            "DROP VIEW IF EXISTS league_match_view; {}",
            LEAGUE_MATCH_VIEW.trim()
        ))
        .context("creating league_match_view")?;
    }
    Ok(())
}

const SCHEMA: &str = r#"
CREATE TABLE IF NOT EXISTS matches (
    id              INTEGER PRIMARY KEY,
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    model1          TEXT NOT NULL,
    model2          TEXT NOT NULL,
    seed            INTEGER NOT NULL,
    rounds_planned  INTEGER NOT NULL,
    rounds_played   INTEGER NOT NULL DEFAULT 0,
    score1          INTEGER NOT NULL DEFAULT 0,
    score2          INTEGER NOT NULL DEFAULT 0,
    -- 1 or 2; NULL while running, when aborted, or when drawn.
    winner          INTEGER,
    -- running | finished | aborted (stopped by an error or a stop; a league resumes it
    -- from its last stored turn, back to running). `error`: the last such stop.
    status          TEXT NOT NULL,
    error           TEXT,
    -- Simple Delay clock: bank per player per game and free delay per decision, in
    -- seconds; NULL = no clock.
    clock_seconds   INTEGER,
    delay_seconds   INTEGER,
    -- Turns after which a game is decided on pip count; NULL = no limit.
    max_turns       INTEGER,
    -- Prompt version (bg-v2, bg-v2-notation, bg-v2-history, nack-v2) and option-order
    -- seed; NULL for matches before versions existed.
    prompt_version  TEXT,
    order_seed      INTEGER,
    -- `git rev-parse HEAD` of the runner at startup, and whether its tree had changes.
    harness_commit  TEXT,
    harness_dirty   INTEGER,
    -- League matches: the players (model1/model2 above are the specs played), `league`
    -- (`playoff`: a legacy second match of a pair; NULL for a single match), and the label
    -- it was created under.
    player1         INTEGER REFERENCES players(id),
    player2         INTEGER REFERENCES players(id),
    stage           TEXT,
    label           TEXT,
    -- Rule column next to the ones above (see `Rules`).
    mirror_concurrent INTEGER,
    -- 0: voided (`void_reason`, `voided_at`); no table counts it and the pair is played
    -- again. Earlier attempts replaced by a later match are voided too.
    valid           INTEGER NOT NULL DEFAULT 1,
    void_reason     TEXT,
    voided_at       TEXT,
    -- Last failure that deferred the match (the error is in `error`); kept once finished.
    failed_at       TEXT,
    -- Rule column (see `Rules`): the position every game starts from; NULL = standard,
    -- `nackgammon` = the Nackgammon start.
    start_position  TEXT
);

CREATE TABLE IF NOT EXISTS games (
    id              INTEGER PRIMARY KEY,
    match_id        INTEGER NOT NULL REFERENCES matches(id),
    round_no        INTEGER NOT NULL,
    -- 1: model1 plays white; 2: seats swapped, same dice.
    leg             INTEGER NOT NULL,
    white_player    INTEGER NOT NULL,
    dice_seed       INTEGER NOT NULL,
    opening_white   INTEGER NOT NULL,
    opening_black   INTEGER NOT NULL,
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    winner_player   INTEGER,
    -- single | gammon | backgammon | timeout | turn_limit
    result          TEXT,
    points          INTEGER,
    turns           INTEGER NOT NULL DEFAULT 0,
    UNIQUE (match_id, round_no, leg)
);

CREATE TABLE IF NOT EXISTS turns (
    id              INTEGER PRIMARY KEY,
    game_id         INTEGER NOT NULL REFERENCES games(id),
    turn_no         INTEGER NOT NULL,
    side            TEXT NOT NULL,
    player          INTEGER NOT NULL,
    die1            INTEGER NOT NULL,
    die2            INTEGER NOT NULL,
    -- Board before the move, white's perspective (JSON).
    position        TEXT NOT NULL,
    legal_count     INTEGER NOT NULL,
    -- Index into the legal play list (0-based); NULL when no play was possible.
    chosen_index    INTEGER,
    -- Mover's numbering; empty when no play was possible.
    move            TEXT NOT NULL,
    -- no_move | forced | model | fallback | timeout (bank ran out; the game is lost)
    decided_by      TEXT NOT NULL,
    latency_ms      INTEGER NOT NULL,
    input_tokens    INTEGER NOT NULL,
    output_tokens   INTEGER NOT NULL,
    created_at      TEXT NOT NULL,
    -- Mover's bank left in this game after the turn; NULL = no clock.
    clock_ms        INTEGER,
    -- Per decision (NULL for forced and impossible moves, and before these existed):
    prompt_version  TEXT,
    harness_commit  TEXT,
    harness_dirty   INTEGER,
    provider        TEXT,
    quantization    TEXT,
    -- JSON array: option_order[k] = chosen_index-style index of the play shown k-th.
    option_order    TEXT,
    -- Letter (A, B, ...) and 0-based position of the chosen play in option_order.
    letter          TEXT,
    chosen_position INTEGER,
    -- JSON array aligned with option_order; null entries for options outside the deciding
    -- request (group splits). NULL when the player gives no probabilities.
    probabilities   TEXT,
    -- logprobs | decision | choice_only (one letter, probability 1) | NULL
    probability_source TEXT,
    -- Decision time without retries, and the time spent on retries (not charged to the
    -- clock), in milliseconds.
    request_ms      INTEGER,
    retry_ms        INTEGER,
    -- Tokens at the player's configured list price; NULL without a price.
    cost_usd        REAL,
    -- 1: the answer named no option and a random legal play was made.
    invalid         INTEGER,
    -- Options per request when the list was split into groups; NULL for one request.
    group_size      INTEGER,
    -- Reasoning tokens of the decision, when the provider reports them.
    reasoning_tokens INTEGER,
    UNIQUE (game_id, turn_no)
);

CREATE TABLE IF NOT EXISTS exchanges (
    id              INTEGER PRIMARY KEY,
    turn_id         INTEGER NOT NULL REFERENCES turns(id),
    attempt         INTEGER NOT NULL,
    request         TEXT NOT NULL,
    response        TEXT,
    error           TEXT,
    latency_ms      INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS leagues (
    id              INTEGER PRIMARY KEY,
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    -- Orders the round robin of the founding participants (not the dice).
    seed            INTEGER NOT NULL,
    -- Rules, compared with the same columns of `matches` (see `Rules`).
    rounds          INTEGER NOT NULL,
    clock_seconds   INTEGER,
    delay_seconds   INTEGER,
    max_turns       INTEGER,
    -- running | finished
    status          TEXT NOT NULL,
    -- Final ranking (JSON array of "place. name", first place first): points, games won,
    -- fewer games lost, then the lower error rate over all of a setup's valid matches
    -- (late-entry matches left out).
    ranking         TEXT,
    -- What the league tests (`--note`) and what changed since, shown in the web history.
    note            TEXT,
    prompt_version  TEXT,
    order_seed      INTEGER,
    -- Last sign of life of the league's runner (every 30 s).
    heartbeat_at    TEXT,
    -- 1: the two games of a round play at once, both showing the round-start score;
    -- 0: game 2 starts after game 1 and shows the score after it.
    mirror_concurrent INTEGER,
    -- How a new match's dice seed is chosen (`SEED_RULE`).
    seed_rule       TEXT,
    -- 1: left out of the site, the dashboard and the ladder tools (`Scope::hidden`).
    hidden          INTEGER,
    -- Only this participant's pairs are played (`Scope::only_pairs_of`); NULL: every pair.
    only_pairs_of   TEXT,
    -- The position every game starts from (as `matches.start_position`); NULL = standard.
    start_position  TEXT
);

-- One row per setup: the name is the identity a league table shows.
CREATE TABLE IF NOT EXISTS players (
    id              INTEGER PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    -- Copies of `settings` fields, for queries.
    spec            TEXT NOT NULL,
    provider        TEXT,
    quantization    TEXT,
    device          TEXT,
    -- JSON {"input_per_mtok", "output_per_mtok"}.
    price           TEXT,
    -- The full player config (JSON `{name, spec, ...}`, as in a league config file).
    settings        TEXT NOT NULL,
    created_at      TEXT NOT NULL
);

-- Participation of a player in a league; `left_at` NULL = a current participant.
CREATE TABLE IF NOT EXISTS league_players (
    id              INTEGER PRIMARY KEY,
    league_id       INTEGER NOT NULL REFERENCES leagues(id),
    player_id       INTEGER NOT NULL REFERENCES players(id),
    joined_at       TEXT NOT NULL,
    left_at         TEXT,
    -- Why the player joined late or left.
    note            TEXT
);
"#;

/// Indexes over columns that older databases gain in `ADDED_COLUMNS`.
const DERIVED_SCHEMA: &str = r#"
CREATE UNIQUE INDEX IF NOT EXISTS league_players_current
    ON league_players (league_id, player_id) WHERE left_at IS NULL;
CREATE INDEX IF NOT EXISTS matches_pair ON matches (player1, player2);
"#;

/// Every valid match between two current participants of a league, whatever rules it was
/// played under (one result per pair; legacy playoffs included): the matches its table and
/// pages count. A match can belong to several leagues.
const LEAGUE_MATCH_VIEW: &str = "
CREATE VIEW league_match_view AS
SELECT l.id AS league_id, m.id AS match_id, m.stage, m.label, p1.name AS model1,
       p2.name AS model2, m.player1, m.player2, m.seed, m.status
FROM leagues l
JOIN matches m ON m.valid = 1 AND m.stage IS NOT NULL
JOIN league_players a ON a.league_id = l.id AND a.player_id = m.player1 AND a.left_at IS NULL
JOIN league_players b ON b.league_id = l.id AND b.player_id = m.player2 AND b.left_at IS NULL
JOIN players p1 ON p1.id = m.player1
JOIN players p2 ON p2.id = m.player2
";

/// Columns added after the first release, for databases created before them.
const ADDED_COLUMNS: [(&str, &str, &str); 43] = [
    ("matches", "clock_seconds", "INTEGER"),
    ("turns", "clock_ms", "INTEGER"),
    ("matches", "delay_seconds", "INTEGER"),
    ("matches", "max_turns", "INTEGER"),
    ("leagues", "note", "TEXT"),
    ("matches", "prompt_version", "TEXT"),
    ("matches", "order_seed", "INTEGER"),
    ("matches", "harness_commit", "TEXT"),
    ("matches", "harness_dirty", "INTEGER"),
    ("leagues", "prompt_version", "TEXT"),
    ("leagues", "order_seed", "INTEGER"),
    ("turns", "prompt_version", "TEXT"),
    ("turns", "harness_commit", "TEXT"),
    ("turns", "harness_dirty", "INTEGER"),
    ("turns", "provider", "TEXT"),
    ("turns", "quantization", "TEXT"),
    ("turns", "option_order", "TEXT"),
    ("turns", "letter", "TEXT"),
    ("turns", "chosen_position", "INTEGER"),
    ("turns", "probabilities", "TEXT"),
    ("turns", "probability_source", "TEXT"),
    ("turns", "request_ms", "INTEGER"),
    ("turns", "retry_ms", "INTEGER"),
    ("turns", "cost_usd", "REAL"),
    ("turns", "invalid", "INTEGER"),
    ("turns", "group_size", "INTEGER"),
    ("turns", "reasoning_tokens", "INTEGER"),
    ("leagues", "heartbeat_at", "TEXT"),
    ("leagues", "mirror_concurrent", "INTEGER"),
    ("matches", "player1", "INTEGER REFERENCES players(id)"),
    ("matches", "player2", "INTEGER REFERENCES players(id)"),
    ("matches", "stage", "TEXT"),
    ("matches", "label", "TEXT"),
    ("matches", "mirror_concurrent", "INTEGER"),
    ("matches", "valid", "INTEGER NOT NULL DEFAULT 1"),
    ("matches", "void_reason", "TEXT"),
    ("matches", "voided_at", "TEXT"),
    ("matches", "failed_at", "TEXT"),
    ("leagues", "seed_rule", "TEXT"),
    ("leagues", "hidden", "INTEGER"),
    ("leagues", "only_pairs_of", "TEXT"),
    ("matches", "start_position", "TEXT"),
    ("leagues", "start_position", "TEXT"),
];

pub struct Db {
    conn: Connection,
}

pub struct LeagueRow {
    /// Orders the founding participants' round robin.
    pub seed: u64,
    pub rules: Rules,
    pub scope: Scope,
}

/// Which pairs a league plays and who sees it. The default is a normal league: every pair,
/// shown everywhere.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct Scope {
    /// Play only this participant's pairs (an early start of a setup's matches for a coming
    /// ladder round); the other pairs of the league are neither played nor waited for.
    pub only_pairs_of: Option<String>,
    /// Left out of the site, the dashboard and the ladder tools: its matches still count
    /// wherever both players meet, as every match does.
    pub hidden: bool,
}

/// A current participant of a league.
#[derive(Clone, Debug)]
pub struct Participant {
    pub player_id: i64,
    pub config: PlayerConfig,
    pub joined_at: String,
}

/// A stored match of one stage between two players.
#[derive(Clone, Debug)]
pub struct MatchRow {
    pub id: i64,
    pub player1: i64,
    pub player2: i64,
    pub seed: u64,
    pub status: String,
    pub valid: bool,
}

impl MatchRow {
    /// The pair, lower player id first.
    pub fn pair(&self) -> (i64, i64) {
        (
            self.player1.min(self.player2),
            self.player1.max(self.player2),
        )
    }
}

/// A league match about to be created.
pub struct NewMatch<'a> {
    pub rules: &'a Rules,
    pub label: &'a str,
    pub players: [i64; 2],
    /// Specs as the match plays them, for `matches.model1` and `model2`.
    pub specs: [&'a str; 2],
    pub seed: u64,
    pub protocol: &'a Protocol,
}

pub struct TurnRecord<'a> {
    pub game_id: i64,
    pub turn_no: u32,
    pub side: Side,
    pub player: u8,
    pub dice: (u8, u8),
    pub position: &'a Board,
    pub legal_count: usize,
    pub chosen_index: Option<usize>,
    pub notation: &'a str,
    pub decided_by: &'a str,
    pub latency_ms: u64,
    pub input_tokens: u64,
    pub output_tokens: u64,
    pub clock_ms: Option<u64>,
    /// `None` for forced and impossible moves.
    pub decision: Option<DecisionLog<'a>>,
}

/// What the protocol logs per decision besides the move itself.
pub struct DecisionLog<'a> {
    pub protocol: &'a Protocol,
    pub provider: &'a str,
    pub quantization: Option<&'a str>,
    /// `option_order[k]` = index into the legal plays of the play shown k-th.
    pub option_order: &'a [usize],
    /// Probability per shown option (aligned with `option_order`); `None` without any.
    pub probabilities: Option<Vec<Option<f64>>>,
    pub probability_source: Option<&'a str>,
    pub request_ms: u64,
    pub retry_ms: u64,
    pub cost_usd: Option<f64>,
    pub invalid: bool,
    pub group_size: Option<usize>,
    pub reasoning_tokens: Option<u64>,
}

#[derive(Clone, Debug)]
pub struct Exchange {
    pub request: String,
    pub response: Option<String>,
    pub error: Option<String>,
    pub latency_ms: u64,
}

/// A game of a match as stored, for resuming the match.
#[derive(Debug)]
pub struct StoredGame {
    pub id: i64,
    pub round: u32,
    pub leg: u8,
    pub white_player: u8,
    pub dice_seed: u64,
    pub opening: (u8, u8),
    /// Winner (1 or 2) and how, once the game is over.
    pub result: Option<(u8, WinKind)>,
    /// Every turn so far, in order; empty for finished games.
    pub turns: Vec<StoredTurn>,
}

/// A stored turn of an unfinished game.
#[derive(Debug)]
pub struct StoredTurn {
    pub turn_no: u32,
    pub side: Side,
    pub player: u8,
    pub dice: (u8, u8),
    /// Board before the move, mover's perspective.
    pub board: Board,
    pub chosen_index: Option<usize>,
    pub notation: String,
    pub decided_by: String,
    pub clock_ms: Option<u64>,
}

fn now() -> String {
    chrono::Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Millis, true)
}

/// Board JSON in white's perspective: `points[i]` is white's point `i + 1`,
/// positive for white checkers and negative for black.
pub fn position_json(white_view: &Board, to_move: Side) -> String {
    serde_json::json!({
        "points": white_view.pts,
        "bar": {"white": white_view.bar[0], "black": white_view.bar[1]},
        "off": {"white": white_view.off[0], "black": white_view.off[1]},
        "to_move": to_move.name(),
    })
    .to_string()
}

/// The inverse of `position_json`: the board from the mover's side, and the mover.
pub fn parse_position(json: &Value) -> Result<(Board, Side)> {
    let side = match json["to_move"].as_str() {
        Some("white") => Side::White,
        Some("black") => Side::Black,
        other => bail!("position.to_move must be white or black, not {other:?}"),
    };
    let points = json["points"]
        .as_array()
        .filter(|p| p.len() == 24)
        .context("position.points must list 24 points")?;
    let mut white = Board {
        pts: [0; 24],
        bar: [0; 2],
        off: [0; 2],
    };
    for (slot, value) in white.pts.iter_mut().zip(points) {
        *slot = value.as_i64().context("position.points: integers")? as i8;
    }
    for (i, colour) in ["white", "black"].into_iter().enumerate() {
        white.bar[i] = json["bar"][colour].as_u64().context("position.bar")? as u8;
        white.off[i] = json["off"][colour].as_u64().context("position.off")? as u8;
    }
    let mover = match side {
        Side::White => white,
        Side::Black => white.flip(),
    };
    Ok((mover, side))
}

impl Db {
    pub fn open(path: &Path) -> Result<Self> {
        let conn = connect(path)?;
        if legacy_layout(&conn)? {
            bail!(
                "{} still has the old league layout (leagues.models, league_matches): run \
                 `jevgammon migrate --db {}` first (back the file up before)",
                path.display(),
                path.display()
            );
        }
        ensure_schema(&conn)?;
        ensure_derived_schema(&conn)?;
        Ok(Db { conn })
    }

    /// Opens without the layout check or schema changes, for `jevgammon migrate`.
    pub fn open_raw(path: &Path) -> Result<Self> {
        Ok(Db {
            conn: connect(path)?,
        })
    }

    pub fn conn(&self) -> &Connection {
        &self.conn
    }

    #[allow(clippy::too_many_arguments)]
    pub fn create_match(
        &self,
        model1: &str,
        model2: &str,
        seed: u64,
        rounds: u32,
        clock: Option<Clock>,
        max_turns: Option<u32>,
        start_position: StartPosition,
        protocol: &Protocol,
    ) -> Result<i64> {
        self.conn.execute(
            "INSERT INTO matches (started_at, model1, model2, seed, rounds_planned, status,
                                  clock_seconds, delay_seconds, max_turns, prompt_version,
                                  order_seed, harness_commit, harness_dirty, start_position)
             VALUES (?1, ?2, ?3, ?4, ?5, 'running', ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13)",
            params![
                now(),
                model1,
                model2,
                seed as i64,
                rounds,
                clock.map(|c| c.bank.as_secs() as i64),
                clock.map(|c| c.delay.as_secs() as i64),
                max_turns,
                protocol.version.id(),
                protocol.order_seed as i64,
                protocol.harness.commit,
                protocol.harness.dirty,
                start_position_value(start_position)
            ],
        )?;
        Ok(self.conn.last_insert_rowid())
    }

    pub fn update_match_score(
        &self,
        match_id: i64,
        rounds_played: u32,
        score: [u32; 2],
    ) -> Result<()> {
        self.conn.execute(
            "UPDATE matches SET rounds_played = ?2, score1 = ?3, score2 = ?4 WHERE id = ?1",
            params![match_id, rounds_played, score[0], score[1]],
        )?;
        Ok(())
    }

    pub fn finish_match(&self, match_id: i64, winner: Option<u8>) -> Result<()> {
        self.conn.execute(
            "UPDATE matches SET status = 'finished', finished_at = ?2, winner = ?3 WHERE id = ?1",
            params![match_id, now(), winner],
        )?;
        Ok(())
    }

    pub fn abort_match(&self, match_id: i64, error: &str) -> Result<()> {
        self.conn.execute(
            "UPDATE matches SET status = 'aborted', finished_at = ?2, error = ?3
             WHERE id = ?1 AND status = 'running'",
            params![match_id, now(), error],
        )?;
        Ok(())
    }

    /// Marks an unfinished match running again before it resumes; its `error` stays as the
    /// record of the last stop.
    pub fn resume_match(&self, match_id: i64) -> Result<()> {
        self.conn.execute(
            "UPDATE matches SET status = 'running', finished_at = NULL
             WHERE id = ?1 AND status != 'finished'",
            params![match_id],
        )?;
        Ok(())
    }

    /// The games of a match in round and leg order, with every turn of the unfinished ones.
    pub fn stored_games(&self, match_id: i64) -> Result<Vec<StoredGame>> {
        let mut statement = self.conn.prepare(
            "SELECT id, round_no, leg, white_player, dice_seed, opening_white, opening_black,
                    winner_player, result
             FROM games WHERE match_id = ?1 ORDER BY round_no, leg",
        )?;
        type Row = (i64, u32, u8, u8, i64, u8, u8, Option<u8>, Option<String>);
        let rows = statement
            .query_map(params![match_id], |row| {
                Ok((
                    row.get(0)?,
                    row.get(1)?,
                    row.get(2)?,
                    row.get(3)?,
                    row.get(4)?,
                    row.get(5)?,
                    row.get(6)?,
                    row.get(7)?,
                    row.get(8)?,
                ))
            })?
            .collect::<rusqlite::Result<Vec<Row>>>()?;
        let mut games = Vec::with_capacity(rows.len());
        for (id, round, leg, white_player, dice_seed, white, black, winner, result) in rows {
            let result = match (winner, result) {
                (Some(winner), Some(name)) => Some((
                    winner,
                    WinKind::parse(&name)
                        .with_context(|| format!("game #{id}: unknown result `{name}`"))?,
                )),
                _ => None,
            };
            let turns = if result.is_some() {
                Vec::new()
            } else {
                self.stored_turns(id)?
            };
            games.push(StoredGame {
                id,
                round,
                leg,
                white_player,
                dice_seed: dice_seed as u64,
                opening: (white, black),
                result,
                turns,
            });
        }
        Ok(games)
    }

    fn stored_turns(&self, game_id: i64) -> Result<Vec<StoredTurn>> {
        let mut statement = self.conn.prepare(
            "SELECT turn_no, side, player, die1, die2, position, chosen_index, move, decided_by,
                    clock_ms
             FROM turns WHERE game_id = ?1 ORDER BY turn_no",
        )?;
        type Row = (
            u32,
            String,
            u8,
            u8,
            u8,
            String,
            Option<i64>,
            String,
            String,
            Option<i64>,
        );
        let rows = statement
            .query_map(params![game_id], |row| {
                Ok((
                    row.get(0)?,
                    row.get(1)?,
                    row.get(2)?,
                    row.get(3)?,
                    row.get(4)?,
                    row.get(5)?,
                    row.get(6)?,
                    row.get(7)?,
                    row.get(8)?,
                    row.get(9)?,
                ))
            })?
            .collect::<rusqlite::Result<Vec<Row>>>()?;
        rows.into_iter()
            .map(
                |(
                    turn_no,
                    side,
                    player,
                    die1,
                    die2,
                    position,
                    chosen,
                    notation,
                    decided_by,
                    clock,
                )| {
                    let context = || format!("game #{game_id} turn {turn_no}");
                    let json: Value = serde_json::from_str(&position).with_context(context)?;
                    let (board, to_move) = parse_position(&json).with_context(context)?;
                    if to_move.name() != side {
                        bail!(
                            "{}: side {side} but the position has {} to move",
                            context(),
                            to_move.name()
                        );
                    }
                    Ok(StoredTurn {
                        turn_no,
                        side: to_move,
                        player,
                        dice: (die1, die2),
                        board,
                        chosen_index: chosen.map(|i| i as usize),
                        notation,
                        decided_by,
                        clock_ms: clock.map(|ms| ms as u64),
                    })
                },
            )
            .collect()
    }

    #[allow(clippy::too_many_arguments)]
    pub fn create_game(
        &self,
        match_id: i64,
        round: u32,
        leg: u8,
        white_player: u8,
        dice_seed: u64,
        opening: (u8, u8),
    ) -> Result<i64> {
        self.conn.execute(
            "INSERT INTO games (match_id, round_no, leg, white_player, dice_seed,
                                opening_white, opening_black, started_at)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
            params![
                match_id,
                round,
                leg,
                white_player,
                dice_seed as i64,
                opening.0,
                opening.1,
                now()
            ],
        )?;
        Ok(self.conn.last_insert_rowid())
    }

    pub fn finish_game(
        &self,
        game_id: i64,
        winner: u8,
        result: &str,
        points: u32,
        turns: u32,
    ) -> Result<()> {
        self.conn.execute(
            "UPDATE games SET finished_at = ?2, winner_player = ?3, result = ?4, points = ?5, turns = ?6
             WHERE id = ?1",
            params![game_id, now(), winner, result, points, turns],
        )?;
        Ok(())
    }

    pub fn record_turn(&mut self, turn: &TurnRecord<'_>, exchanges: &[Exchange]) -> Result<()> {
        let log = turn.decision.as_ref();
        let position = log.and_then(|log| {
            let chosen = turn.chosen_index?;
            log.option_order.iter().position(|&i| i == chosen)
        });
        let tx = self.conn.transaction()?;
        tx.execute(
            "INSERT INTO turns (game_id, turn_no, side, player, die1, die2, position, legal_count,
                                chosen_index, move, decided_by, latency_ms, input_tokens,
                                output_tokens, created_at, clock_ms, prompt_version,
                                harness_commit, harness_dirty, provider, quantization,
                                option_order, letter, chosen_position, probabilities,
                                probability_source, request_ms, retry_ms, cost_usd, invalid,
                                group_size, reasoning_tokens)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16, ?17,
                     ?18, ?19, ?20, ?21, ?22, ?23, ?24, ?25, ?26, ?27, ?28, ?29, ?30, ?31, ?32)",
            params![
                turn.game_id,
                turn.turn_no,
                turn.side.name(),
                turn.player,
                turn.dice.0,
                turn.dice.1,
                position_json(turn.position, turn.side),
                turn.legal_count as i64,
                turn.chosen_index.map(|i| i as i64),
                turn.notation,
                turn.decided_by,
                turn.latency_ms as i64,
                turn.input_tokens as i64,
                turn.output_tokens as i64,
                now(),
                turn.clock_ms.map(|ms| ms as i64),
                log.map(|l| l.protocol.version.id()),
                log.and_then(|l| l.protocol.harness.commit.as_deref()),
                log.map(|l| l.protocol.harness.dirty),
                log.map(|l| l.provider),
                log.and_then(|l| l.quantization),
                log.map(|l| serde_json::to_string(l.option_order).expect("serializes")),
                position.filter(|&p| p < 26).map(|p| letter(p).to_string()),
                position.map(|p| p as i64),
                log.and_then(|l| l.probabilities.as_ref())
                    .map(|p| serde_json::to_string(p).expect("serializes")),
                log.and_then(|l| l.probability_source),
                log.map(|l| l.request_ms as i64),
                log.map(|l| l.retry_ms as i64),
                log.and_then(|l| l.cost_usd),
                log.map(|l| l.invalid),
                log.and_then(|l| l.group_size).map(|g| g as i64),
                log.and_then(|l| l.reasoning_tokens).map(|r| r as i64),
            ],
        )?;
        let turn_id = tx.last_insert_rowid();
        for (attempt, exchange) in exchanges.iter().enumerate() {
            tx.execute(
                "INSERT INTO exchanges (turn_id, attempt, request, response, error, latency_ms)
                 VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
                params![
                    turn_id,
                    (attempt + 1) as i64,
                    exchange.request,
                    exchange.response,
                    exchange.error,
                    exchange.latency_ms as i64
                ],
            )?;
        }
        tx.commit()?;
        Ok(())
    }

    /// A new league with `players` as its founding participants (in entry order); one
    /// transaction. `scope.only_pairs_of` must be one of them.
    pub fn create_league(
        &mut self,
        seed: u64,
        rules: &Rules,
        players: &[PlayerConfig],
        note: Option<&str>,
        scope: &Scope,
    ) -> Result<i64> {
        if let Some(name) = &scope.only_pairs_of
            && !players.iter().any(|p| &p.name == name)
        {
            bail!("only_pairs_of: `{name}` is not a player of the league");
        }
        let tx = self.conn.transaction()?;
        let started_at = now();
        let mut values: Vec<rusqlite::types::Value> = vec![
            started_at.clone().into(),
            (seed as i64).into(),
            note.map(str::to_owned).into(),
            SEED_RULE.to_owned().into(),
            i64::from(scope.hidden).into(),
            scope.only_pairs_of.clone().into(),
        ];
        values.extend(rules.values());
        tx.execute(
            "INSERT INTO leagues (started_at, seed, note, seed_rule, hidden, only_pairs_of, status,
                                  rounds, clock_seconds, delay_seconds, max_turns,
                                  prompt_version, order_seed, mirror_concurrent, start_position)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, 'running', ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14)",
            rusqlite::params_from_iter(values),
        )?;
        let id = tx.last_insert_rowid();
        for config in players {
            let player_id = upsert_player(&tx, config)?;
            tx.execute(
                "INSERT INTO league_players (league_id, player_id, joined_at) VALUES (?1, ?2, ?3)",
                params![id, player_id, started_at],
            )?;
        }
        tx.commit()?;
        Ok(id)
    }

    pub fn league(&self, league_id: i64) -> Result<LeagueRow> {
        self.conn
            .query_row(
                "SELECT seed, rounds, clock_seconds, delay_seconds, max_turns, prompt_version,
                        order_seed, mirror_concurrent, hidden, only_pairs_of, start_position
                 FROM leagues WHERE id = ?1",
                params![league_id],
                |row| {
                    Ok(LeagueRow {
                        seed: row.get::<_, i64>(0)? as u64,
                        rules: Rules {
                            rounds: row.get(1)?,
                            clock_seconds: row.get::<_, Option<i64>>(2)?.map(|s| s as u64),
                            delay_seconds: row.get::<_, Option<i64>>(3)?.map(|s| s as u64),
                            max_turns: row.get(4)?,
                            prompt_version: row.get(5)?,
                            order_seed: row.get::<_, Option<i64>>(6)?.map(|s| s as u64),
                            mirror_concurrent: row.get::<_, Option<bool>>(7)?.unwrap_or(false),
                            start_position: row.get(10)?,
                        },
                        scope: Scope {
                            hidden: row.get::<_, Option<bool>>(8)?.unwrap_or(false),
                            only_pairs_of: row.get(9)?,
                        },
                    })
                },
            )
            .with_context(|| format!("league #{league_id}"))
    }

    /// The rules match `match_id` was played under.
    pub fn match_rules(&self, match_id: i64) -> Result<Rules> {
        self.conn
            .query_row(
                "SELECT rounds_planned, clock_seconds, delay_seconds, max_turns, prompt_version,
                        order_seed, mirror_concurrent, start_position
                 FROM matches WHERE id = ?1",
                params![match_id],
                |row| {
                    Ok(Rules {
                        rounds: row.get(0)?,
                        clock_seconds: row.get::<_, Option<i64>>(1)?.map(|s| s as u64),
                        delay_seconds: row.get::<_, Option<i64>>(2)?.map(|s| s as u64),
                        max_turns: row.get(3)?,
                        prompt_version: row.get(4)?,
                        order_seed: row.get::<_, Option<i64>>(5)?.map(|s| s as u64),
                        mirror_concurrent: row.get::<_, Option<bool>>(6)?.unwrap_or(false),
                        start_position: row.get(7)?,
                    })
                },
            )
            .with_context(|| format!("match #{match_id}"))
    }

    /// Replaces a finished league's stored ranking (`jevgammon rank`); its finish time stays.
    pub fn store_ranking(&self, league_id: i64, ranking: &[String]) -> Result<()> {
        self.conn.execute(
            "UPDATE leagues SET ranking = ?2 WHERE id = ?1 AND status = 'finished'",
            params![league_id, serde_json::to_string(ranking)?],
        )?;
        Ok(())
    }

    pub fn finish_league(&self, league_id: i64, ranking: &[String]) -> Result<()> {
        self.conn.execute(
            "UPDATE leagues SET status = 'finished', finished_at = ?2, ranking = ?3 WHERE id = ?1",
            params![league_id, now(), serde_json::to_string(ranking)?],
        )?;
        Ok(())
    }

    /// Marks the runner's process as alive for this league (`leagues.heartbeat_at`).
    pub fn heartbeat(&self, league_id: i64) -> Result<()> {
        self.conn.execute(
            "UPDATE leagues SET heartbeat_at = ?2 WHERE id = ?1",
            params![league_id, now()],
        )?;
        Ok(())
    }

    pub fn clear_heartbeat(&self, league_id: i64) -> Result<()> {
        self.conn.execute(
            "UPDATE leagues SET heartbeat_at = NULL WHERE id = ?1",
            params![league_id],
        )?;
        Ok(())
    }

    /// Whether a process is playing this league: seconds since its runner's last heartbeat
    /// (runners that pick up added players) and since the last turn of a match still marked
    /// running (any runner).
    pub fn league_activity(&self, league_id: i64) -> Result<Activity> {
        let age = |sql: &str| -> Result<Option<f64>> {
            Ok(self
                .conn
                .query_row(sql, params![league_id], |row| row.get::<_, Option<f64>>(0))?)
        };
        Ok(Activity {
            heartbeat_secs: age(
                "SELECT (julianday('now') - julianday(heartbeat_at)) * 86400 FROM leagues
                 WHERE id = ?1",
            )?,
            running_turn_secs: age(
                "SELECT (julianday('now') - julianday(MAX(t.created_at))) * 86400
                 FROM league_match_view v JOIN games g ON g.match_id = v.match_id
                 JOIN turns t ON t.game_id = g.id
                 WHERE v.league_id = ?1 AND v.status = 'running'",
            )?,
        })
    }

    /// The current participants of `league_id`, in the order they joined (founders in
    /// their entry order).
    pub fn participants(&self, league_id: i64) -> Result<Vec<Participant>> {
        let mut statement = self.conn.prepare(
            "SELECT p.id, p.settings, lp.joined_at FROM league_players lp
             JOIN players p ON p.id = lp.player_id
             WHERE lp.league_id = ?1 AND lp.left_at IS NULL ORDER BY lp.id",
        )?;
        let rows = statement
            .query_map(params![league_id], |row| {
                Ok((row.get::<_, i64>(0)?, row.get::<_, String>(1)?, row.get(2)?))
            })?
            .collect::<rusqlite::Result<Vec<_>>>()?;
        rows.into_iter()
            .map(|(player_id, settings, joined_at)| {
                Ok(Participant {
                    player_id,
                    config: serde_json::from_str(&settings)
                        .with_context(|| format!("players #{player_id}: settings"))?,
                    joined_at,
                })
            })
            .collect()
    }

    /// Adds `config` to the league as a current participant now, appends `note` to the
    /// league note and reopens a finished league (the table changes); one transaction.
    pub fn add_participant(
        &mut self,
        league_id: i64,
        config: &PlayerConfig,
        note: &str,
    ) -> Result<()> {
        let tx = self.conn.transaction()?;
        let player_id = upsert_player(&tx, config)?;
        let current: bool = tx.query_row(
            "SELECT COUNT(*) > 0 FROM league_players
             WHERE league_id = ?1 AND player_id = ?2 AND left_at IS NULL",
            params![league_id, player_id],
            |row| row.get(0),
        )?;
        if current {
            bail!("`{}` already plays in league #{league_id}", config.name);
        }
        tx.execute(
            "INSERT INTO league_players (league_id, player_id, joined_at, note)
             VALUES (?1, ?2, ?3, ?4)",
            params![league_id, player_id, now(), note],
        )?;
        league_changed(&tx, league_id, note)?;
        tx.commit()?;
        Ok(())
    }

    /// Ends `name`'s participation now with `reason`: its matches stay valid (a pair's
    /// result in any league it meets again) but leave this league's table, and its unplayed
    /// pairs drop out of the fixture.
    pub fn remove_participant(&mut self, league_id: i64, name: &str, reason: &str) -> Result<()> {
        let tx = self.conn.transaction()?;
        let date = now();
        let note = format!("{name} left on {}: {reason}.", &date[..10]);
        league_changed(&tx, league_id, &note)?;
        let changed = tx.execute(
            "UPDATE league_players SET left_at = ?3, note = TRIM(COALESCE(note, '') || ' ' || ?4)
             WHERE league_id = ?1 AND left_at IS NULL
               AND player_id = (SELECT id FROM players WHERE name = ?2)",
            params![league_id, name, date, reason],
        )?;
        if changed == 0 {
            bail!("`{name}` is not a current participant of league #{league_id}");
        }
        tx.commit()?;
        Ok(())
    }

    /// Voids a valid match: no table counts it any more and its pair is played again (with
    /// the same seed). Every league whose table counted it reopens. Returns those leagues.
    pub fn void_match(&mut self, match_id: i64, reason: &str) -> Result<Vec<i64>> {
        let tx = self.conn.transaction()?;
        let leagues: Vec<i64> = {
            let mut statement =
                tx.prepare("SELECT league_id FROM league_match_view WHERE match_id = ?1")?;
            statement
                .query_map(params![match_id], |row| row.get(0))?
                .collect::<rusqlite::Result<_>>()?
        };
        let changed = tx.execute(
            "UPDATE matches SET valid = 0, void_reason = ?2, voided_at = ?3
             WHERE id = ?1 AND valid = 1",
            params![match_id, reason, now()],
        )?;
        if changed == 0 {
            bail!("match #{match_id} does not exist or is already void");
        }
        for &league_id in &leagues {
            let note = format!("Match #{match_id} voided on {}: {reason}.", &now()[..10]);
            league_changed(&tx, league_id, &note)?;
        }
        tx.commit()?;
        Ok(leagues)
    }

    /// Every match (valid or void) of a pair of `players`, of any stage but the legacy
    /// playoffs, under any rules, in id order: with a league's current participants, the
    /// matches of its table and fixture (and the seeds of voided pairs).
    pub fn matches_between(&self, players: &[i64]) -> Result<Vec<MatchRow>> {
        let ids = serde_json::to_string(players)?;
        let mut statement = self.conn.prepare(
            "SELECT m.id, m.player1, m.player2, m.seed, m.status, m.valid
             FROM matches m
             WHERE m.stage IS NOT NULL AND m.stage <> 'playoff'
               AND m.player1 IN (SELECT value FROM json_each(?1))
               AND m.player2 IN (SELECT value FROM json_each(?1))
             ORDER BY m.id",
        )?;
        let rows = statement.query_map(params![ids], |row| {
            Ok(MatchRow {
                id: row.get(0)?,
                player1: row.get(1)?,
                player2: row.get(2)?,
                seed: row.get::<_, i64>(3)? as u64,
                status: row.get(4)?,
                valid: row.get(5)?,
            })
        })?;
        Ok(rows.collect::<rusqlite::Result<_>>()?)
    }

    /// The pair's result: its valid match (`PAIR_RESULT`, either side first, any rules).
    pub fn current_match(&self, players: [i64; 2]) -> Result<Option<CurrentMatch>> {
        current_match(&self.conn, players)
    }

    /// The pair's valid match, or a new league match created now under `new.rules`; one
    /// transaction, so two runners never create the same match.
    pub fn ensure_league_match(&self, new: &NewMatch<'_>) -> Result<i64> {
        let tx = rusqlite::Transaction::new_unchecked(
            &self.conn,
            rusqlite::TransactionBehavior::Immediate,
        )?;
        if let Some(current) = current_match(&tx, new.players)? {
            return Ok(current.id);
        }
        let mut values: Vec<rusqlite::types::Value> = vec![
            now().into(),
            new.specs[0].to_owned().into(),
            new.specs[1].to_owned().into(),
            (new.seed as i64).into(),
            new.protocol.harness.commit.clone().into(),
            i64::from(new.protocol.harness.dirty).into(),
            new.players[0].into(),
            new.players[1].into(),
            String::from("league").into(),
            new.label.to_owned().into(),
        ];
        values.extend(new.rules.values());
        tx.execute(
            &format!(
                "INSERT INTO matches (started_at, status, model1, model2, seed, harness_commit,
                                      harness_dirty, player1, player2, stage, label, {})
                 VALUES (?1, 'running', ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, {})",
                RULES_COLUMNS.join(", "),
                (11..11 + RULES_COLUMNS.len())
                    .map(|i| format!("?{i}"))
                    .collect::<Vec<_>>()
                    .join(", ")
            ),
            rusqlite::params_from_iter(values),
        )?;
        let id = tx.last_insert_rowid();
        tx.commit()?;
        Ok(id)
    }

    /// Records that the match failed now with `error` and was deferred.
    pub fn defer_match(&self, match_id: i64, error: &str) -> Result<()> {
        self.conn.execute(
            "UPDATE matches SET error = ?2, failed_at = ?3,
                 finished_at = CASE status WHEN 'running' THEN ?3 ELSE finished_at END,
                 status = CASE status WHEN 'running' THEN 'aborted' ELSE status END
             WHERE id = ?1",
            params![match_id, error, now()],
        )?;
        Ok(())
    }

    /// The result of a finished match; `None` while running or when aborted.
    pub fn match_result(&self, match_id: i64) -> Result<Option<MatchResult>> {
        let row: Option<(u32, u32, Option<u8>)> = self
            .conn
            .query_row(
                "SELECT score1, score2, winner FROM matches WHERE id = ?1 AND status = 'finished'",
                params![match_id],
                |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)),
            )
            .optional()?;
        let Some((score1, score2, winner)) = row else {
            return Ok(None);
        };
        let mut games_won = [0u32; 2];
        let mut statement = self.conn.prepare(
            "SELECT winner_player, COUNT(*) FROM games
             WHERE match_id = ?1 AND winner_player IS NOT NULL GROUP BY winner_player",
        )?;
        let mut rows = statement.query(params![match_id])?;
        while let Some(row) = rows.next()? {
            let player: u8 = row.get(0)?;
            games_won[player as usize - 1] = row.get(1)?;
        }
        Ok(Some(MatchResult {
            score: [score1, score2],
            games_won,
            winner,
        }))
    }
}

/// Seconds since the league's runner heartbeat and its last running turn.
#[derive(Clone, Copy, Debug)]
pub struct Activity {
    pub heartbeat_secs: Option<f64>,
    pub running_turn_secs: Option<f64>,
}

impl Activity {
    /// A runner that picks up added players beat within the last 90 s.
    pub fn pickup_runner(&self) -> bool {
        self.heartbeat_secs.is_some_and(|s| s < 90.0)
    }

    /// Some runner (old or new) moved in a running match in the last 5 minutes.
    pub fn playing(&self) -> bool {
        self.pickup_runner() || self.running_turn_secs.is_some_and(|s| s < 300.0)
    }
}

/// A pair's valid match: its id, which player is `player1`, and its seed.
#[derive(Clone, Copy, Debug)]
pub struct CurrentMatch {
    pub id: i64,
    pub player1: i64,
    pub seed: u64,
}

/// The pair's result: its valid match of any stage but the legacy playoffs, under any rules
/// (the newest, should there be two).
fn current_match(conn: &Connection, [a, b]: [i64; 2]) -> Result<Option<CurrentMatch>> {
    Ok(conn
        .query_row(
            &format!(
                "SELECT id, player1, seed FROM matches m
                 WHERE {PAIR_RESULT}
                   AND ((m.player1 = ?1 AND m.player2 = ?2) OR (m.player1 = ?2 AND m.player2 = ?1))
                 ORDER BY m.id DESC LIMIT 1"
            ),
            params![a, b],
            |row| {
                Ok(CurrentMatch {
                    id: row.get(0)?,
                    player1: row.get(1)?,
                    seed: row.get::<_, i64>(2)? as u64,
                })
            },
        )
        .optional()?)
}

/// The `players` row of `config.name`: created with these settings, or the existing one
/// when its settings are the same. Different settings under a known name are refused: a
/// name is one setup (edit `players.settings` to record a change of the same setup).
pub fn upsert_player(conn: &Connection, config: &PlayerConfig) -> Result<i64> {
    if config.name.is_empty() {
        bail!("a player needs a name");
    }
    let existing: Option<(i64, String)> = conn
        .query_row(
            "SELECT id, settings FROM players WHERE name = ?1",
            params![config.name],
            |row| Ok((row.get(0)?, row.get(1)?)),
        )
        .optional()?;
    if let Some((id, settings)) = existing {
        let stored: PlayerConfig =
            serde_json::from_str(&settings).with_context(|| format!("players #{id}: settings"))?;
        if &stored != config {
            bail!(
                "player `{}` is already recorded (players #{id}) with other settings: use the \
                 same settings, another name, or update players.settings if it is the same \
                 setup\n  stored: {settings}\n  given:  {}",
                config.name,
                serde_json::to_string(config)?
            );
        }
        return Ok(id);
    }
    insert_player(conn, config, &now())
}

/// Inserts a `players` row (the name must be new).
pub fn insert_player(conn: &Connection, config: &PlayerConfig, created_at: &str) -> Result<i64> {
    conn.execute(
        "INSERT INTO players (name, spec, provider, quantization, device, price, settings,
                              created_at)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
        params![
            config.name,
            config.spec,
            config.provider,
            config.quantization,
            config.device,
            config
                .price
                .map(|p| serde_json::to_string(&p))
                .transpose()?,
            serde_json::to_string(config)?,
            created_at
        ],
    )?;
    Ok(conn.last_insert_rowid())
}

/// The league's participants or results changed: append `note` to the league note and reopen
/// it if finished (its final ranking is computed again when it finishes).
fn league_changed(conn: &Connection, league_id: i64, note: &str) -> Result<()> {
    let changed = conn.execute(
        "UPDATE leagues SET status = 'running', finished_at = NULL,
             note = TRIM(COALESCE(note, '') || ' ' || ?2)
         WHERE id = ?1",
        params![league_id, note],
    )?;
    if changed == 0 {
        bail!("no league #{league_id}");
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A database from before prompt versions is refused until migrated; then it has every
    /// column, and its league reads with its roster as participants.
    #[test]
    fn old_databases_are_migrated_and_readable() {
        let path = std::env::temp_dir().join(format!("jevgammon-old-{}.db", std::process::id()));
        let _ = std::fs::remove_file(&path);
        {
            let conn = Connection::open(&path).unwrap();
            conn.execute_batch(
                "CREATE TABLE leagues (id INTEGER PRIMARY KEY, started_at TEXT NOT NULL,
                     finished_at TEXT, seed INTEGER NOT NULL, rounds INTEGER NOT NULL,
                     clock_seconds INTEGER, delay_seconds INTEGER, max_turns INTEGER,
                     models TEXT NOT NULL, status TEXT NOT NULL, ranking TEXT);
                 INSERT INTO leagues (started_at, seed, rounds, models, status)
                 VALUES ('2026-10-09', 8, 3, '[{\"name\":\"Cygnet\",\"spec\":\"cygnet\"}]', 'finished');
                 CREATE TABLE turns (id INTEGER PRIMARY KEY, game_id INTEGER NOT NULL,
                     turn_no INTEGER NOT NULL, side TEXT NOT NULL, player INTEGER NOT NULL,
                     die1 INTEGER NOT NULL, die2 INTEGER NOT NULL, position TEXT NOT NULL,
                     legal_count INTEGER NOT NULL, chosen_index INTEGER, move TEXT NOT NULL,
                     decided_by TEXT NOT NULL, latency_ms INTEGER NOT NULL,
                     input_tokens INTEGER NOT NULL, output_tokens INTEGER NOT NULL,
                     created_at TEXT NOT NULL, UNIQUE (game_id, turn_no));",
            )
            .unwrap();
        }
        assert!(Db::open(&path).is_err());
        crate::migrate::run(&crate::migrate::MigrateArgs {
            db: path.clone(),
            dry_run: false,
            freeze: std::env::temp_dir().join("jevgammon-no-freeze"),
            freeze_db: None,
        })
        .unwrap();
        let db = Db::open(&path).unwrap();
        let league = db.league(1).unwrap();
        let participants = db.participants(1).unwrap();
        assert_eq!(participants.len(), 1);
        assert_eq!(
            participants[0].config,
            PlayerConfig::new("Cygnet", "cygnet")
        );
        assert_eq!(participants[0].joined_at, "2026-10-09");
        assert_eq!(league.rules.prompt_version, None);
        assert_eq!(league.rules.start_position, StartPosition::Standard);
        for (table, column, _) in ADDED_COLUMNS {
            let exists: bool = db
                .conn
                .query_row(
                    "SELECT COUNT(*) > 0 FROM pragma_table_info(?1) WHERE name = ?2",
                    params![table, column],
                    |row| row.get(0),
                )
                .unwrap();
            assert!(exists, "{table}.{column}");
        }
        drop(db);
        let _ = std::fs::remove_file(&path);
    }

    #[test]
    fn positions_round_trip() {
        let mut board = Board::start();
        board.bar = [1, 0];
        board.off = [0, 2];
        for side in [Side::White, Side::Black] {
            let white = if side == Side::White {
                board
            } else {
                board.flip()
            };
            let json: Value = serde_json::from_str(&position_json(&white, side)).unwrap();
            assert_eq!(parse_position(&json).unwrap(), (board, side));
        }
    }

    /// The standard start leaves the rules string (and so every pair's dice) and the stored
    /// rows as they were; the Nackgammon start is part of the rules and stored by name.
    #[test]
    fn start_position_is_a_rule_and_standard_changes_nothing() {
        let clock = Some(Clock {
            bank: Duration::from_secs(300),
            delay: Duration::from_secs(30),
        });
        let standard = Rules::new(
            3,
            clock,
            Some(300),
            "bg-v2",
            9,
            true,
            StartPosition::Standard,
        );
        assert_eq!(
            standard.canonical(),
            "rules-v1 rounds=3 clock=300 delay=30 max_turns=300 prompt=bg-v2 order_seed=9 mirror=1"
        );
        let nack = Rules::new(
            3,
            clock,
            Some(300),
            "bg-v3-nack",
            9,
            true,
            StartPosition::Nackgammon,
        );
        assert_eq!(
            nack.canonical(),
            "rules-v1 rounds=3 clock=300 delay=30 max_turns=300 prompt=bg-v3-nack order_seed=9 \
             mirror=1 start=nackgammon"
        );
        let only_start = Rules {
            start_position: StartPosition::Nackgammon,
            ..standard.clone()
        };
        assert_ne!(only_start, standard);
        assert_ne!(only_start.hash(), standard.hash());
        // `tools/league_web.py`'s `rules_hash` of the same rules.
        assert_eq!(standard.hash(), 9116972043994848190);
        assert_eq!(nack.hash(), 762005135011512391);

        let path = std::env::temp_dir().join(format!("jevgammon-start-{}.db", std::process::id()));
        let _ = std::fs::remove_file(&path);
        let mut db = Db::open(&path).unwrap();
        let protocol = Protocol {
            version: crate::players::prompt::PromptVersion::BgV3Nack,
            order_seed: 9,
            harness: crate::runner::Harness::default(),
        };
        for (rules, stored) in [(&standard, None), (&nack, Some("nackgammon"))] {
            let id = db
                .create_league(1, rules, &[], None, &Scope::default())
                .unwrap();
            assert_eq!(&db.league(id).unwrap().rules, rules);
            let column: Option<String> = db
                .conn
                .query_row(
                    "SELECT start_position FROM leagues WHERE id = ?1",
                    [id],
                    |r| r.get(0),
                )
                .unwrap();
            assert_eq!(column.as_deref(), stored);
            let match_id = db
                .create_match("a", "b", 1, 3, None, None, rules.start_position, &protocol)
                .unwrap();
            assert_eq!(
                db.match_rules(match_id).unwrap().start_position,
                rules.start_position
            );
        }
        drop(db);
        let _ = std::fs::remove_file(&path);
    }
}
