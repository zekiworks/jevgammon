//! Stored positions (the shared sets, the smoke test): `jevgammon render` prints what a
//! model is sent for each, and `jevgammon ask` sends them to the setups of a league config
//! through the same players as the leagues and stores every answer with the per-decision
//! fields of `turns`.

use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::sync::atomic::{AtomicU64, AtomicUsize, Ordering};
use std::time::{Duration, Instant};

use anyhow::{Context, Result, bail};
use parking_lot::Mutex;
use rusqlite::{Connection, params};
use serde_json::{Value, json};
use tokio::sync::Semaphore;
use tokio::task::JoinSet;

use crate::board::{Board, Play, Side};
use crate::db::{Exchange, parse_position};
use crate::dice::derive_seed;
use crate::http::RetryTime;
use crate::league::LeagueConfig;
use crate::players::order::{option_order, position_key};
use crate::players::prompt::{self, PromptVersion, letter};
use crate::players::{DecisionRequest, PastMove, Player, Setup};
use crate::runner::{Clock, Harness};

/// The match context shown with a stored position when its row does not give one.
#[derive(Clone, Copy, Debug)]
pub struct MatchContext {
    pub rounds: u32,
    pub max_turns: Option<u32>,
    /// Shown with full banks; stored positions are answered without a clock.
    pub clock: Option<Clock>,
}

/// One stored position, parsed: a JSON line with `position` (the runner's white-view
/// JSON, as in `turns.position`), `dice` (legal plays are generated in that order), and
/// optional `id`, `set`, `prompt` (version), `option_order` (checked), `my_score`,
/// `opp_score`, `round`, `rounds`, `leg`, `turn`/`turn_no`, `max_turns` (null = no limit),
/// `clock` {bank, delay, my_left, opp_left} in seconds (null = no clock), `history`
/// [{turn_no, player, dice, notation}], `player`.
pub struct Position {
    pub id: String,
    pub set: Option<String>,
    pub version: Option<PromptVersion>,
    board: Board,
    dice: (u8, u8),
    pub key: String,
    stored_order: Option<Vec<usize>>,
    plays: Vec<Play>,
    notations: Vec<String>,
    history: Vec<PastMove>,
    my_score: u32,
    opp_score: u32,
    round: u32,
    rounds: u32,
    leg: u8,
    clock: Option<Clock>,
    my_clock: Option<Duration>,
    opp_clock: Option<Duration>,
    turn_no: u32,
    max_turns: Option<u32>,
    player: u8,
}

impl Position {
    pub fn parse(row: &Value, defaults: MatchContext, number: usize) -> Result<Self> {
        let position = match &row["position"] {
            Value::String(text) => serde_json::from_str(text).context("position")?,
            other => other.clone(),
        };
        let (board, side): (Board, Side) = parse_position(&position)?;
        let die = |i: usize| -> Result<u8> {
            row["dice"][i]
                .as_u64()
                .filter(|d| (1..=6).contains(d))
                .map(|d| d as u8)
                .context("dice must be two numbers 1-6")
        };
        let dice = (die(0)?, die(1)?);
        let number_of = |key: &str| row[key].as_u64();
        let seconds = |key: &str| row["clock"][key].as_u64().map(Duration::from_secs);
        let clock = match row.get("clock") {
            Some(Value::Null) => None,
            Some(_) => seconds("bank").map(|bank| Clock {
                bank,
                delay: seconds("delay").unwrap_or_default(),
            }),
            None => defaults.clock,
        };
        let history = row["history"]
            .as_array()
            .map(|moves| {
                moves
                    .iter()
                    .map(|m| PastMove {
                        turn_no: m["turn_no"].as_u64().unwrap_or(0) as u32,
                        player: m["player"].as_u64().unwrap_or(0) as u8,
                        dice: (
                            m["dice"][0].as_u64().unwrap_or(0) as u8,
                            m["dice"][1].as_u64().unwrap_or(0) as u8,
                        ),
                        notation: m["notation"].as_str().unwrap_or_default().to_owned(),
                    })
                    .collect()
            })
            .unwrap_or_default();
        let plays = board.legal_plays(dice.0, dice.1);
        let notations: Vec<String> = plays.iter().map(|p| p.notation()).collect();
        if let Some(stored) = row["legal_plays"].as_array() {
            let stored: Vec<&str> = stored.iter().filter_map(Value::as_str).collect();
            if stored != notations {
                bail!("legal_plays differ from the runner's");
            }
        }
        let stored_order = row["option_order"].as_array().map(|order| {
            order
                .iter()
                .filter_map(Value::as_u64)
                .map(|i| i as usize)
                .collect()
        });
        Ok(Position {
            id: row["id"]
                .as_str()
                .map_or_else(|| format!("line-{number}"), str::to_owned),
            set: row["set"].as_str().map(str::to_owned),
            version: row["prompt"]
                .as_str()
                .map(PromptVersion::parse)
                .transpose()?,
            key: position_key(&board, dice, side),
            board,
            dice,
            stored_order,
            plays,
            notations,
            history,
            my_score: number_of("my_score").unwrap_or(0) as u32,
            opp_score: number_of("opp_score").unwrap_or(0) as u32,
            round: number_of("round").unwrap_or(1) as u32,
            rounds: number_of("rounds").map_or(defaults.rounds, |r| r as u32),
            leg: number_of("leg").unwrap_or(1) as u8,
            my_clock: clock.map(|c| seconds("my_left").unwrap_or(c.bank)),
            opp_clock: clock.map(|c| seconds("opp_left").unwrap_or(c.bank)),
            clock,
            turn_no: number_of("turn_no")
                .or_else(|| number_of("turn"))
                .unwrap_or(1) as u32,
            max_turns: match row.get("max_turns") {
                Some(Value::Null) => None,
                Some(value) => value.as_u64().map(|t| t as u32).or(defaults.max_turns),
                None => defaults.max_turns,
            },
            player: number_of("player").unwrap_or(1) as u8,
        })
    }

    pub fn legal_count(&self) -> usize {
        self.plays.len()
    }

    /// The seeded option order; an error when the row stores a different one.
    pub fn order(&self, seed: u64) -> Result<Vec<usize>> {
        let order = option_order(seed, &self.key, self.plays.len());
        match &self.stored_order {
            Some(stored) if *stored != order => {
                bail!(
                    "{}: stored option_order differs from the order for seed {seed}",
                    self.id
                )
            }
            _ => Ok(order),
        }
    }

    pub fn request<'a>(
        &'a self,
        order: &'a [usize],
        version: PromptVersion,
        seed: u64,
        retry: &'a RetryTime,
    ) -> DecisionRequest<'a> {
        DecisionRequest {
            board: &self.board,
            dice: self.dice,
            plays: &self.plays,
            notations: &self.notations,
            my_score: self.my_score,
            opp_score: self.opp_score,
            round: self.round,
            rounds: self.rounds,
            leg: self.leg,
            clock: self.clock,
            my_clock: self.my_clock,
            opp_clock: self.opp_clock,
            turn_no: self.turn_no,
            max_turns: self.max_turns,
            player: self.player,
            history: &self.history,
            order,
            seed,
            version,
            retry,
        }
    }
}

/// Reads a JSON-lines file of positions (`-` = stdin).
pub fn read_positions(path: &Path, defaults: MatchContext) -> Result<Vec<Position>> {
    let text = if path.as_os_str() == "-" {
        std::io::read_to_string(std::io::stdin())?
    } else {
        std::fs::read_to_string(path).with_context(|| format!("reading {}", path.display()))?
    };
    text.lines()
        .enumerate()
        .filter(|(_, line)| !line.trim().is_empty())
        .map(|(i, line)| {
            let row: Value =
                serde_json::from_str(line).with_context(|| format!("line {}", i + 1))?;
            Position::parse(&row, defaults, i + 1).with_context(|| format!("line {}", i + 1))
        })
        .collect()
}

/// `jevgammon render`: the prompt of every position, one JSON line each.
pub fn render(path: &Path, version: Option<PromptVersion>, order_seed: u64) -> Result<()> {
    use std::io::Write as _;
    let defaults = MatchContext {
        rounds: 3,
        max_turns: Some(300),
        clock: None,
    };
    let mut out = std::io::stdout().lock();
    for position in read_positions(path, defaults)? {
        let order = option_order(order_seed, &position.key, position.legal_count());
        let retry = RetryTime::default();
        let version = version.or(position.version).unwrap_or(PromptVersion::BgV2);
        let req = position.request(&order, version, 0, &retry);
        let mut rendered = prompt::render(&req);
        rendered["id"] = json!(position.id);
        rendered["position_key"] = json!(position.key);
        rendered["order_seed"] = json!(order_seed);
        writeln!(out, "{rendered}")?;
    }
    Ok(())
}

const SCHEMA: &str = r#"
PRAGMA journal_mode = WAL;
CREATE TABLE IF NOT EXISTS answers (
    id                 INTEGER PRIMARY KEY,
    -- Player name in the league config, its spec and settings.
    setup              TEXT NOT NULL,
    spec               TEXT NOT NULL,
    provider           TEXT,
    quantization       TEXT,
    reasoning          TEXT,
    position_id        TEXT NOT NULL,
    position_set       TEXT,
    -- 1-based repetition (consistency runs ask a position several times).
    repeat             INTEGER NOT NULL,
    prompt_version     TEXT NOT NULL,
    order_seed         INTEGER NOT NULL,
    harness_commit     TEXT,
    harness_dirty      INTEGER,
    legal_count        INTEGER NOT NULL,
    -- As in turns: option_order[k] = index of the play shown k-th.
    option_order       TEXT NOT NULL,
    chosen_index       INTEGER,
    move               TEXT,
    letter             TEXT,
    chosen_position    INTEGER,
    probabilities      TEXT,
    probability_source TEXT,
    invalid            INTEGER,
    group_size         INTEGER,
    request_ms         INTEGER,
    retry_ms           INTEGER,
    input_tokens       INTEGER,
    output_tokens      INTEGER,
    reasoning_tokens   INTEGER,
    cost_usd           REAL,
    -- The request failed after its retries; asked again on the next run.
    error              TEXT,
    created_at         TEXT NOT NULL,
    UNIQUE (setup, position_id, repeat, prompt_version)
);
CREATE TABLE IF NOT EXISTS answer_exchanges (
    id          INTEGER PRIMARY KEY,
    answer_id   INTEGER NOT NULL REFERENCES answers(id),
    attempt     INTEGER NOT NULL,
    request     TEXT NOT NULL,
    response    TEXT,
    error       TEXT,
    latency_ms  INTEGER NOT NULL
);
"#;

pub struct AskArgs {
    pub config: PathBuf,
    pub positions: PathBuf,
    pub out: PathBuf,
    /// Player names; empty = every player of the config.
    pub setups: Vec<String>,
    pub limit: Option<usize>,
    pub repeats: u32,
    pub version: Option<PromptVersion>,
    /// A setup stops taking new positions once its answers cost more than this.
    pub max_cost: Option<f64>,
}

/// One stored answer.
struct Answer {
    setup: String,
    position: usize,
    repeat: u32,
    version: PromptVersion,
    order: Vec<usize>,
    outcome: Result<crate::players::Decision>,
    request_ms: u64,
    retry_ms: u64,
}

/// `jevgammon ask`.
pub async fn ask(args: AskArgs, setup: &Setup) -> Result<()> {
    let config = LeagueConfig::load(&args.config)?;
    let order_seed = config
        .order_seed
        .context("the league config needs order_seed to ask stored positions")?;
    let config_version = match &config.prompt_version {
        Some(id) => PromptVersion::parse(id)?,
        None => PromptVersion::BgV2,
    };
    let bank = config.clock.unwrap_or(300);
    let defaults = MatchContext {
        rounds: config.rounds.unwrap_or(3),
        max_turns: match config.max_turns.unwrap_or(300) {
            0 => None,
            t => Some(t),
        },
        clock: (bank > 0).then(|| Clock {
            bank: Duration::from_secs(bank),
            delay: Duration::from_secs(config.delay.unwrap_or(30)),
        }),
    };
    let mut positions = read_positions(&args.positions, defaults)?;
    positions.retain(|p| p.legal_count() > 1);
    if let Some(limit) = args.limit {
        positions.truncate(limit);
    }
    let positions = Arc::new(positions);
    let chosen: Vec<_> = config
        .players
        .iter()
        .filter(|p| args.setups.is_empty() || args.setups.contains(&p.name))
        .cloned()
        .collect();
    for name in &args.setups {
        if !chosen.iter().any(|p| &p.name == name) {
            bail!("no player `{name}` in {}", args.config.display());
        }
    }
    let harness = Harness::detect();
    let conn =
        Connection::open(&args.out).with_context(|| format!("opening {}", args.out.display()))?;
    conn.busy_timeout(Duration::from_secs(60))?;
    conn.execute_batch(SCHEMA)?;
    let conn = Arc::new(Mutex::new(conn));
    println!(
        "asking {} positions × {} repeat(s) of {} · {} setup(s) · option-order seed {order_seed} · \
         harness {}{} · out {}",
        positions.len(),
        args.repeats,
        args.positions.display(),
        chosen.len(),
        harness.commit.as_deref().unwrap_or("unknown"),
        if harness.dirty { " (dirty)" } else { "" },
        args.out.display()
    );
    let mut setups = JoinSet::new();
    for config in chosen {
        let player = match Player::from_config(&config, setup).await {
            Ok(player) => Arc::new(player),
            Err(error) => {
                println!("[{}] blocked: {error:#}", config.name);
                continue;
            }
        };
        if let Err(error) = player.warm_up().await {
            println!("[{}] blocked at warm-up: {error:#}", config.name);
            continue;
        }
        let done: std::collections::HashSet<(String, u32, String)> = {
            let conn = conn.lock();
            let mut statement = conn.prepare(
                "SELECT position_id, repeat, prompt_version FROM answers
                 WHERE setup = ?1 AND error IS NULL",
            )?;
            let rows = statement.query_map(params![config.name], |row| {
                Ok((row.get(0)?, row.get(1)?, row.get(2)?))
            })?;
            rows.collect::<rusqlite::Result<_>>()?
        };
        let positions = positions.clone();
        let conn = conn.clone();
        let harness = harness.clone();
        let max_cost = args.max_cost;
        let repeats = args.repeats;
        let version_override = args.version;
        setups.spawn(async move {
            let name = config.name.clone();
            let parallel = Semaphore::new(config.parallel.unwrap_or(4).max(1));
            let parallel = Arc::new(parallel);
            let spent = Arc::new(AtomicU64::new(0));
            let answered = Arc::new(AtomicUsize::new(0));
            let failed = Arc::new(AtomicUsize::new(0));
            let mut jobs = JoinSet::new();
            let started = Instant::now();
            let mut stopped = None;
            'outer: for repeat in 1..=repeats {
                for index in 0..positions.len() {
                    let position = &positions[index];
                    let version = version_override
                        .or(position.version)
                        .unwrap_or(config_version);
                    if done.contains(&(position.id.clone(), repeat, version.id().to_owned())) {
                        continue;
                    }
                    let permit = parallel.clone().acquire_owned().await.expect("open");
                    let cost = spent.load(Ordering::Relaxed) as f64 / 1e9;
                    if max_cost.is_some_and(|limit| cost > limit) {
                        stopped = Some(cost);
                        break 'outer;
                    }
                    let (asker, rows, spent, answered, failed, name) = (
                        player.clone(),
                        positions.clone(),
                        spent.clone(),
                        answered.clone(),
                        failed.clone(),
                        name.clone(),
                    );
                    jobs.spawn(async move {
                        let _permit = permit;
                        let position = &rows[index];
                        let order = match position.order(order_seed) {
                            Ok(order) => order,
                            Err(error) => {
                                return Answer {
                                    setup: name,
                                    position: index,
                                    repeat,
                                    version,
                                    order: Vec::new(),
                                    outcome: Err(error),
                                    request_ms: 0,
                                    retry_ms: 0,
                                };
                            }
                        };
                        let retry = RetryTime::default();
                        let seed = derive_seed(
                            order_seed,
                            &format!("ask:{}:{repeat}:{}", position.id, version.id()),
                        );
                        let started = Instant::now();
                        let outcome = asker
                            .decide(&position.request(&order, version, seed, &retry))
                            .await;
                        let elapsed = started.elapsed();
                        let retry_spent = retry.get().min(elapsed);
                        match &outcome {
                            Ok(decision) => {
                                if let Some(cost) = asker.cost(decision) {
                                    spent.fetch_add((cost * 1e9) as u64, Ordering::Relaxed);
                                }
                                answered.fetch_add(1, Ordering::Relaxed);
                            }
                            Err(_) => {
                                failed.fetch_add(1, Ordering::Relaxed);
                            }
                        }
                        Answer {
                            setup: name,
                            position: index,
                            repeat,
                            version,
                            order,
                            outcome,
                            request_ms: (elapsed - retry_spent).as_millis() as u64,
                            retry_ms: retry_spent.as_millis() as u64,
                        }
                    });
                    while let Some(joined) = jobs.try_join_next() {
                        store(&conn, &positions, &player, &harness, order_seed, joined?)?;
                    }
                }
            }
            while let Some(joined) = jobs.join_next().await {
                store(&conn, &positions, &player, &harness, order_seed, joined?)?;
            }
            let cost = spent.load(Ordering::Relaxed) as f64 / 1e9;
            println!(
                "[{name}] {} answered, {} failed in {:.0} s · ${cost:.4}{}",
                answered.load(Ordering::Relaxed),
                failed.load(Ordering::Relaxed),
                started.elapsed().as_secs_f64(),
                stopped.map_or(String::new(), |c| format!(
                    " · stopped: cost ${c:.4} over the limit"
                ))
            );
            anyhow::Ok(())
        });
    }
    while let Some(joined) = setups.join_next().await {
        if let Err(error) = joined? {
            println!("setup failed: {error:#}");
        }
    }
    Ok(())
}

fn store(
    conn: &Mutex<Connection>,
    positions: &[Position],
    player: &Player,
    harness: &Harness,
    order_seed: u64,
    answer: Answer,
) -> Result<()> {
    let position = &positions[answer.position];
    let mut conn = conn.lock();
    let tx = conn.transaction()?;
    let (decision, error) = match &answer.outcome {
        Ok(decision) => (Some(decision), None),
        Err(error) => {
            println!("[{}] {}: {error:#}", answer.setup, position.id);
            (None, Some(format!("{error:#}")))
        }
    };
    let chosen = decision.map(|d| d.index);
    let shown = chosen.and_then(|c| answer.order.iter().position(|&i| i == c));
    let probabilities = decision.filter(|d| !d.probabilities.is_empty()).map(|d| {
        let aligned: Vec<Option<f64>> = answer
            .order
            .iter()
            .map(|i| {
                d.probabilities
                    .iter()
                    .find(|(j, _)| j == i)
                    .map(|&(_, p)| p)
            })
            .collect();
        serde_json::to_string(&aligned).expect("serializes")
    });
    tx.execute(
        "DELETE FROM answer_exchanges WHERE answer_id IN (SELECT id FROM answers
         WHERE setup = ?1 AND position_id = ?2 AND repeat = ?3 AND prompt_version = ?4)",
        params![
            answer.setup,
            position.id,
            answer.repeat,
            answer.version.id()
        ],
    )?;
    tx.execute(
        "DELETE FROM answers WHERE setup = ?1 AND position_id = ?2 AND repeat = ?3
         AND prompt_version = ?4",
        params![
            answer.setup,
            position.id,
            answer.repeat,
            answer.version.id()
        ],
    )?;
    tx.execute(
        "INSERT INTO answers (setup, spec, provider, quantization, reasoning, position_id,
             position_set, repeat, prompt_version, order_seed, harness_commit, harness_dirty,
             legal_count, option_order, chosen_index, move, letter, chosen_position,
             probabilities, probability_source, invalid, group_size, request_ms, retry_ms,
             input_tokens, output_tokens, reasoning_tokens, cost_usd, error, created_at)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16, ?17,
                 ?18, ?19, ?20, ?21, ?22, ?23, ?24, ?25, ?26, ?27, ?28, ?29, ?30)",
        params![
            answer.setup,
            player.spec,
            player.provider,
            player.quantization,
            player.reasoning,
            position.id,
            position.set,
            answer.repeat,
            answer.version.id(),
            order_seed as i64,
            harness.commit,
            harness.dirty,
            position.legal_count() as i64,
            serde_json::to_string(&answer.order).expect("serializes"),
            chosen.map(|c| c as i64),
            chosen.map(|c| position.notations[c].clone()),
            shown.filter(|&p| p < 26).map(|p| letter(p).to_string()),
            shown.map(|p| p as i64),
            probabilities,
            decision.and_then(|d| d.probability_source),
            decision.map(|d| d.invalid),
            decision.and_then(|d| d.group_size).map(|g| g as i64),
            answer.request_ms as i64,
            answer.retry_ms as i64,
            decision.map(|d| d.input_tokens as i64),
            decision.map(|d| d.output_tokens as i64),
            decision.and_then(|d| d.reasoning_tokens).map(|r| r as i64),
            decision.and_then(|d| player.cost(d)),
            error,
            chrono::Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Millis, true),
        ],
    )?;
    let id = tx.last_insert_rowid();
    let exchanges: &[Exchange] = decision.map_or(&[], |d| &d.exchanges);
    for (attempt, exchange) in exchanges.iter().enumerate() {
        tx.execute(
            "INSERT INTO answer_exchanges (answer_id, attempt, request, response, error,
                                           latency_ms)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
            params![
                id,
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
