//! SQLite record of every match, game, roll, move, and model exchange.

use std::path::Path;
use std::time::Duration;

use anyhow::{Context, Result};
use rusqlite::{Connection, OptionalExtension, params};

use crate::board::{Board, Side};
use crate::runner::{Clock, MatchResult};

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
    max_turns       INTEGER
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
    note            TEXT
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
const ADDED_COLUMNS: [(&str, &str, &str); 5] = [
    ("matches", "clock_seconds", "INTEGER"),
    ("turns", "clock_ms", "INTEGER"),
    ("matches", "delay_seconds", "INTEGER"),
    ("matches", "max_turns", "INTEGER"),
    ("leagues", "note", "TEXT"),
];

pub struct Db {
    conn: Connection,
}

pub struct LeagueRow {
    pub seed: u64,
    pub rounds: u32,
    pub clock: Option<Clock>,
    pub max_turns: Option<u32>,
    /// `(name, spec)` in entry order.
    pub models: Vec<(String, String)>,
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
}

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

    pub fn create_match(
        &self,
        model1: &str,
        model2: &str,
        seed: u64,
        rounds: u32,
        clock: Option<Clock>,
        max_turns: Option<u32>,
    ) -> Result<i64> {
        self.conn.execute(
            "INSERT INTO matches (started_at, model1, model2, seed, rounds_planned, status,
                                  clock_seconds, delay_seconds, max_turns)
             VALUES (?1, ?2, ?3, ?4, ?5, 'running', ?6, ?7, ?8)",
            params![
                now(),
                model1,
                model2,
                seed as i64,
                rounds,
                clock.map(|c| c.bank.as_secs() as i64),
                clock.map(|c| c.delay.as_secs() as i64),
                max_turns
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
        let tx = self.conn.transaction()?;
        tx.execute(
            "INSERT INTO turns (game_id, turn_no, side, player, die1, die2, position, legal_count,
                                chosen_index, move, decided_by, latency_ms, input_tokens,
                                output_tokens, created_at, clock_ms)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16)",
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

    pub fn create_league(
        &self,
        seed: u64,
        rounds: u32,
        clock: Option<Clock>,
        max_turns: Option<u32>,
        models: &[(String, String)],
        note: Option<&str>,
    ) -> Result<i64> {
        let models: Vec<_> = models
            .iter()
            .map(|(name, spec)| serde_json::json!({"name": name, "spec": spec}))
            .collect();
        self.conn.execute(
            "INSERT INTO leagues (started_at, seed, rounds, clock_seconds, delay_seconds,
                                  max_turns, models, status, note)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, 'running', ?8)",
            params![
                now(),
                seed as i64,
                rounds,
                clock.map(|c| c.bank.as_secs() as i64),
                clock.map(|c| c.delay.as_secs() as i64),
                max_turns,
                serde_json::Value::from(models).to_string(),
                note
            ],
        )?;
        Ok(self.conn.last_insert_rowid())
    }

    pub fn league(&self, league_id: i64) -> Result<LeagueRow> {
        type Row = (i64, u32, Option<i64>, Option<i64>, Option<u32>, String);
        let (seed, rounds, bank, delay, max_turns, models): Row = self
            .conn
            .query_row(
                "SELECT seed, rounds, clock_seconds, delay_seconds, max_turns, models
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
                    ))
                },
            )
            .with_context(|| format!("league #{league_id}"))?;
        let models: Vec<serde_json::Value> =
            serde_json::from_str(&models).context("leagues.models")?;
        let models = models
            .iter()
            .map(|m| {
                let field = |key: &str| m.get(key).and_then(|v| v.as_str()).map(str::to_owned);
                field("name")
                    .zip(field("spec"))
                    .context("leagues.models entry without name and spec")
            })
            .collect::<Result<_>>()?;
        Ok(LeagueRow {
            seed: seed as u64,
            rounds,
            clock: bank.map(|bank| Clock {
                bank: Duration::from_secs(bank as u64),
                delay: Duration::from_secs(delay.unwrap_or(0) as u64),
            }),
            max_turns,
            models,
        })
    }

    pub fn finish_league(&self, league_id: i64, ranking: &[String]) -> Result<()> {
        self.conn.execute(
            "UPDATE leagues SET status = 'finished', finished_at = ?2, ranking = ?3 WHERE id = ?1",
            params![league_id, now(), serde_json::to_string(ranking)?],
        )?;
        Ok(())
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
