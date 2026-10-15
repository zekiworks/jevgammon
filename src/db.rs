//! SQLite record of every match, game, roll, move, and model exchange.

use std::path::Path;
use std::time::Duration;

use anyhow::{Context, Result, bail};
use rusqlite::{Connection, OptionalExtension, params};
use serde_json::Value;

use crate::board::{Board, Side};
use crate::players::PlayerConfig;
use crate::players::prompt::letter;
use crate::runner::{Clock, MatchResult, Protocol};

const SCHEMA: &str = r#"
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

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
    -- running | finished | aborted
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
    harness_dirty   INTEGER
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
    seed            INTEGER NOT NULL,
    rounds          INTEGER NOT NULL,
    -- As in matches.
    clock_seconds   INTEGER,
    delay_seconds   INTEGER,
    max_turns       INTEGER,
    -- JSON array of {"name", "spec"} in entry order.
    models          TEXT NOT NULL,
    -- running | finished
    status          TEXT NOT NULL,
    -- Final ranking (JSON array of names, first place first), playoffs applied.
    ranking         TEXT,
    -- What the league tests (`--note`), shown in the web history.
    note            TEXT,
    prompt_version  TEXT,
    order_seed      INTEGER,
    -- Last sign of life of a runner that picks up added players (every 30 s).
    heartbeat_at    TEXT
);

CREATE TABLE IF NOT EXISTS league_matches (
    id              INTEGER PRIMARY KEY,
    league_id       INTEGER NOT NULL REFERENCES leagues(id),
    -- league | playoff
    stage           TEXT NOT NULL,
    -- Unique within the league, e.g. `matchday 3 match 2` or `playoff 2-3: A v B`.
    label           TEXT NOT NULL,
    -- League stage: 1-based matchday; NULL for playoffs.
    matchday        INTEGER,
    -- Model names (leagues.models); model1 plays white in the first game of every round.
    model1          TEXT NOT NULL,
    model2          TEXT NOT NULL,
    seed            INTEGER NOT NULL,
    -- Latest attempt; an aborted attempt is replaced by a fresh match with the same seed.
    match_id        INTEGER REFERENCES matches(id),
    UNIQUE (league_id, label)
);
"#;

/// Columns added after the first release, for databases created before them.
const ADDED_COLUMNS: [(&str, &str, &str); 28] = [
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
];

pub struct Db {
    conn: Connection,
}

pub struct LeagueRow {
    pub seed: u64,
    pub rounds: u32,
    pub clock: Option<Clock>,
    pub max_turns: Option<u32>,
    /// Entry order.
    pub models: Vec<PlayerConfig>,
    /// `None` for leagues before prompt versions.
    pub prompt_version: Option<String>,
    pub order_seed: Option<u64>,
}

#[derive(Clone, Debug)]
pub struct FixtureRow {
    pub id: i64,
    pub label: String,
    pub matchday: Option<u32>,
    pub model1: String,
    pub model2: String,
    pub seed: u64,
    pub match_id: Option<i64>,
}

fn fixture_row(row: &rusqlite::Row<'_>) -> rusqlite::Result<FixtureRow> {
    Ok(FixtureRow {
        id: row.get(0)?,
        label: row.get(1)?,
        matchday: row.get(2)?,
        model1: row.get(3)?,
        model2: row.get(4)?,
        seed: row.get::<_, i64>(5)? as u64,
        match_id: row.get(6)?,
    })
}

const FIXTURE_COLUMNS: &str = "id, label, matchday, model1, model2, seed, match_id";

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
        let conn = Connection::open(path).with_context(|| format!("opening {}", path.display()))?;
        // League matches write concurrently, one connection each.
        conn.busy_timeout(Duration::from_secs(60))?;
        conn.execute_batch(SCHEMA).context("creating schema")?;
        for (table, column, kind) in ADDED_COLUMNS {
            let exists: bool = conn.query_row(
                "SELECT COUNT(*) > 0 FROM pragma_table_info(?1) WHERE name = ?2",
                params![table, column],
                |row| row.get(0),
            )?;
            if !exists {
                conn.execute_batch(&format!("ALTER TABLE {table} ADD COLUMN {column} {kind}"))
                    .with_context(|| format!("adding {table}.{column}"))?;
            }
        }
        Ok(Db { conn })
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
        protocol: &Protocol,
    ) -> Result<i64> {
        self.conn.execute(
            "INSERT INTO matches (started_at, model1, model2, seed, rounds_planned, status,
                                  clock_seconds, delay_seconds, max_turns, prompt_version,
                                  order_seed, harness_commit, harness_dirty)
             VALUES (?1, ?2, ?3, ?4, ?5, 'running', ?6, ?7, ?8, ?9, ?10, ?11, ?12)",
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
                protocol.harness.dirty
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

    #[allow(clippy::too_many_arguments)]
    pub fn create_league(
        &self,
        seed: u64,
        rounds: u32,
        clock: Option<Clock>,
        max_turns: Option<u32>,
        models: &[PlayerConfig],
        note: Option<&str>,
        prompt_version: &str,
        order_seed: u64,
    ) -> Result<i64> {
        self.conn.execute(
            "INSERT INTO leagues (started_at, seed, rounds, clock_seconds, delay_seconds,
                                  max_turns, models, status, note, prompt_version, order_seed)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, 'running', ?8, ?9, ?10)",
            params![
                now(),
                seed as i64,
                rounds,
                clock.map(|c| c.bank.as_secs() as i64),
                clock.map(|c| c.delay.as_secs() as i64),
                max_turns,
                serde_json::to_string(models)?,
                note,
                prompt_version,
                order_seed as i64
            ],
        )?;
        Ok(self.conn.last_insert_rowid())
    }

    pub fn league(&self, league_id: i64) -> Result<LeagueRow> {
        type Row = (
            i64,
            u32,
            Option<i64>,
            Option<i64>,
            Option<u32>,
            String,
            Option<String>,
            Option<i64>,
        );
        let (seed, rounds, bank, delay, max_turns, models, prompt_version, order_seed): Row = self
            .conn
            .query_row(
                "SELECT seed, rounds, clock_seconds, delay_seconds, max_turns, models,
                        prompt_version, order_seed
                 FROM leagues WHERE id = ?1",
                params![league_id],
                |row| {
                    Ok((
                        row.get(0)?,
                        row.get(1)?,
                        row.get(2)?,
                        row.get(3)?,
                        row.get(4)?,
                        row.get(5)?,
                        row.get(6)?,
                        row.get(7)?,
                    ))
                },
            )
            .with_context(|| format!("league #{league_id}"))?;
        let models: Vec<PlayerConfig> =
            serde_json::from_str(&models).context("leagues.models (entries need name and spec)")?;
        Ok(LeagueRow {
            seed: seed as u64,
            rounds,
            clock: bank.map(|bank| Clock {
                bank: Duration::from_secs(bank as u64),
                delay: Duration::from_secs(delay.unwrap_or(0) as u64),
            }),
            max_turns,
            models,
            prompt_version,
            order_seed: order_seed.map(|s| s as u64),
        })
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
                 FROM league_matches lm JOIN matches m ON m.id = lm.match_id
                 JOIN games g ON g.match_id = m.id JOIN turns t ON t.game_id = g.id
                 WHERE lm.league_id = ?1 AND m.status = 'running'",
            )?,
        })
    }

    /// The highest matchday of the league stage (0 when none).
    pub fn max_matchday(&self, league_id: i64) -> Result<u32> {
        Ok(self.conn.query_row(
            "SELECT COALESCE(MAX(matchday), 0) FROM league_matches WHERE league_id = ?1",
            params![league_id],
            |row| row.get(0),
        )?)
    }

    /// Appends `config` to the roster with its fixtures (`(matchday, label, model1, model2,
    /// seed)`), appends `note` to the league note, and marks earlier playoffs stale; one
    /// transaction. Returns how many playoff fixtures were marked stale.
    pub fn add_league_player(
        &mut self,
        league_id: i64,
        config: &PlayerConfig,
        fixtures: &[(u32, String, String, String, u64)],
        note: &str,
    ) -> Result<usize> {
        let tx = self.conn.transaction()?;
        let models: String = tx.query_row(
            "SELECT models FROM leagues WHERE id = ?1",
            params![league_id],
            |row| row.get(0),
        )?;
        let mut models: Vec<PlayerConfig> = serde_json::from_str(&models)?;
        if models.iter().any(|m| m.name == config.name) {
            bail!(
                "league #{league_id} already has a player named `{}`",
                config.name
            );
        }
        models.push(config.clone());
        tx.execute(
            "UPDATE leagues SET models = ?2, status = 'running', finished_at = NULL,
                 note = TRIM(COALESCE(note, '') || ' ' || ?3)
             WHERE id = ?1",
            params![league_id, serde_json::to_string(&models)?, note],
        )?;
        for (matchday, label, model1, model2, seed) in fixtures {
            tx.execute(
                "INSERT INTO league_matches (league_id, stage, label, matchday, model1, model2, seed)
                 VALUES (?1, 'league', ?2, ?3, ?4, ?5, ?6)",
                params![league_id, label, matchday, model1, model2, *seed as i64],
            )?;
        }
        let stale = stale_playoffs(&tx, league_id)?;
        tx.commit()?;
        Ok(stale)
    }

    /// Marks this league's playoffs stale (kept, renamed): the table changed after them.
    pub fn mark_playoffs_stale(&self, league_id: i64) -> Result<usize> {
        stale_playoffs(&self.conn, league_id)
    }

    /// Adds a fixture unless the label already exists; returns the stored row.
    #[allow(clippy::too_many_arguments)]
    pub fn add_fixture(
        &self,
        league_id: i64,
        stage: &str,
        label: &str,
        matchday: Option<u32>,
        model1: &str,
        model2: &str,
        seed: u64,
    ) -> Result<FixtureRow> {
        self.conn.execute(
            "INSERT INTO league_matches (league_id, stage, label, matchday, model1, model2, seed)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7) ON CONFLICT (league_id, label) DO NOTHING",
            params![
                league_id,
                stage,
                label,
                matchday,
                model1,
                model2,
                seed as i64
            ],
        )?;
        Ok(self.conn.query_row(
            &format!(
                "SELECT {FIXTURE_COLUMNS} FROM league_matches WHERE league_id = ?1 AND label = ?2"
            ),
            params![league_id, label],
            fixture_row,
        )?)
    }

    /// Fixtures of one stage, in matchday and creation order.
    pub fn fixtures(&self, league_id: i64, stage: &str) -> Result<Vec<FixtureRow>> {
        let mut statement = self.conn.prepare(&format!(
            "SELECT {FIXTURE_COLUMNS} FROM league_matches WHERE league_id = ?1 AND stage = ?2
             ORDER BY matchday, id"
        ))?;
        let rows = statement.query_map(params![league_id, stage], fixture_row)?;
        Ok(rows.collect::<rusqlite::Result<_>>()?)
    }

    pub fn set_fixture_match(&self, fixture_id: i64, match_id: i64) -> Result<()> {
        self.conn.execute(
            "UPDATE league_matches SET match_id = ?2 WHERE id = ?1",
            params![fixture_id, match_id],
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

/// Playoff fixtures move to stage `playoff-stale` with a dated label, so their matches stay
/// and a playoff of the same pairing is played afresh.
fn stale_playoffs(conn: &Connection, league_id: i64) -> Result<usize> {
    Ok(conn.execute(
        "UPDATE league_matches SET stage = 'playoff-stale', label = label || ' [stale ' || ?2 || ']'
         WHERE league_id = ?1 AND stage = 'playoff'",
        params![league_id, now()],
    )?)
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A database from before prompt versions opens, gains the new columns, and its
    /// leagues still read.
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
        let db = Db::open(&path).unwrap();
        let league = db.league(1).unwrap();
        assert_eq!(league.models, vec![PlayerConfig::new("Cygnet", "cygnet")]);
        assert_eq!(league.prompt_version, None);
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
}
