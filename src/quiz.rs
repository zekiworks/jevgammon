//! `jevgammon quiz` (Clear-risk follow-up, Part 2): sends prebuilt questions to the players of
//! a league config and stores every answer. The questions are built outside the runner from
//! `jevgammon render` (the league prompt code); each JSON line holds both forms of one
//! question: the decision-service form (`name`, `state`, `instructions`, `options` as
//! `[value, text]` pairs) and the chat form (`system`, `user`, an answer `schema` named
//! `schema_name`). Decision services return a choice and probabilities; chat models' answer
//! text is stored unparsed. A rerun asks only what is missing or failed.

use std::path::PathBuf;
use std::sync::Arc;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{Duration, Instant};

use anyhow::{Context, Result, anyhow};
use parking_lot::Mutex;
use rusqlite::{Connection, params};
use serde::Deserialize;
use serde_json::Value;
use tokio::sync::Semaphore;
use tokio::task::JoinSet;

use crate::http::RetryTime;
use crate::league::LeagueConfig;
use crate::players::{Decision, Player, QuizQuestion, QuizReply, Setup};
use crate::runner::Harness;

const SCHEMA: &str = r#"
PRAGMA journal_mode = WAL;
CREATE TABLE IF NOT EXISTS quiz_answers (
    id                 INTEGER PRIMARY KEY,
    -- Player name in the league config, its spec and settings.
    setup              TEXT NOT NULL,
    spec               TEXT NOT NULL,
    provider           TEXT,
    reasoning          TEXT,
    item_id            TEXT NOT NULL,
    harness_commit     TEXT,
    harness_dirty      INTEGER,
    -- Decision services: the chosen option value (NULL = invalid answer) and the
    -- probabilities as a JSON object by value.
    choice             TEXT,
    probabilities      TEXT,
    -- Chat models: the answer text, unparsed.
    text               TEXT,
    request_ms         INTEGER,
    retry_ms           INTEGER,
    input_tokens       INTEGER,
    output_tokens      INTEGER,
    reasoning_tokens   INTEGER,
    cost_usd           REAL,
    -- The request failed after its retries (or timed out); asked again on the next run.
    error              TEXT,
    created_at         TEXT NOT NULL,
    UNIQUE (setup, item_id)
);
CREATE TABLE IF NOT EXISTS quiz_exchanges (
    id          INTEGER PRIMARY KEY,
    answer_id   INTEGER NOT NULL REFERENCES quiz_answers(id),
    attempt     INTEGER NOT NULL,
    request     TEXT NOT NULL,
    response    TEXT,
    error       TEXT,
    latency_ms  INTEGER NOT NULL
);
"#;

/// One question (a line of the items file).
#[derive(Deserialize)]
struct Item {
    id: String,
    name: String,
    state: String,
    instructions: String,
    options: Vec<(String, String)>,
    system: String,
    user: String,
    schema: Value,
    schema_name: String,
}

pub struct QuizArgs {
    pub config: PathBuf,
    pub items: PathBuf,
    pub out: PathBuf,
    /// Player names; empty = every player of the config.
    pub setups: Vec<String>,
    /// No new question is sent once the chosen setups' stored and new answers together cost
    /// more than this many dollars.
    pub max_cost: Option<f64>,
    pub time_limit: Option<Duration>,
}

struct Stored {
    setup: String,
    item: usize,
    outcome: Result<(Decision, QuizReply)>,
    request_ms: u64,
    retry_ms: u64,
}

/// `jevgammon quiz`.
pub async fn quiz(args: QuizArgs, setup: &Setup) -> Result<()> {
    let config = LeagueConfig::load(&args.config)?;
    let text = std::fs::read_to_string(&args.items)
        .with_context(|| format!("reading {}", args.items.display()))?;
    let items: Vec<Item> = text
        .lines()
        .filter(|l| !l.trim().is_empty())
        .enumerate()
        .map(|(n, line)| serde_json::from_str(line).with_context(|| format!("item line {}", n + 1)))
        .collect::<Result<_>>()?;
    let items = Arc::new(items);
    let chosen = crate::ask::chosen_players(&config, &args.config, &args.setups)?;
    let harness = Harness::detect();
    let conn = Connection::open(&args.out).with_context(|| format!("opening {}", args.out.display()))?;
    conn.busy_timeout(Duration::from_secs(60))?;
    conn.execute_batch(SCHEMA)?;
    let names: Vec<String> = chosen.iter().map(|c| c.name.clone()).collect();
    let stored_cost: f64 = {
        let mut total = 0.0;
        for name in &names {
            total += conn.query_row(
                "SELECT COALESCE(SUM(cost_usd), 0) FROM quiz_answers WHERE setup = ?1",
                params![name],
                |row| row.get::<_, f64>(0),
            )?;
        }
        total
    };
    let conn = Arc::new(Mutex::new(conn));
    let spent = Arc::new(AtomicU64::new((stored_cost * 1e9) as u64));
    println!(
        "quiz: {} items of {} · {} setup(s) · stored cost ${stored_cost:.4} · harness {}{} · out {}",
        items.len(),
        args.items.display(),
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
        let done: std::collections::HashSet<String> = {
            let conn = conn.lock();
            let mut statement =
                conn.prepare("SELECT item_id FROM quiz_answers WHERE setup = ?1 AND error IS NULL")?;
            let rows = statement.query_map(params![config.name], |row| row.get(0))?;
            rows.collect::<rusqlite::Result<_>>()?
        };
        let (items, conn, harness, spent) = (items.clone(), conn.clone(), harness.clone(), spent.clone());
        let (max_cost, time_limit) = (args.max_cost, args.time_limit);
        setups.spawn(async move {
            let name = config.name.clone();
            let parallel = Arc::new(Semaphore::new(config.parallel.unwrap_or(4).max(1)));
            let mut jobs = JoinSet::new();
            let started = Instant::now();
            let (mut asked, mut failed, mut stopped) = (0usize, 0usize, None);
            for index in 0..items.len() {
                if done.contains(&items[index].id) {
                    continue;
                }
                let permit = parallel.clone().acquire_owned().await.expect("open");
                let cost = spent.load(Ordering::Relaxed) as f64 / 1e9;
                if max_cost.is_some_and(|limit| cost > limit) {
                    stopped = Some(cost);
                    break;
                }
                let (asker, rows, spent, name) = (player.clone(), items.clone(), spent.clone(), name.clone());
                jobs.spawn(async move {
                    let _permit = permit;
                    let item = &rows[index];
                    let question = QuizQuestion {
                        name: &item.name,
                        state: &item.state,
                        instructions: &item.instructions,
                        options: &item.options,
                        system: &item.system,
                        user: &item.user,
                        schema: &item.schema,
                        schema_name: &item.schema_name,
                    };
                    let retry = RetryTime::default();
                    let started = Instant::now();
                    let ask = asker.quiz(&question, &retry);
                    let outcome = match time_limit {
                        Some(limit) => tokio::time::timeout(limit, ask)
                            .await
                            .unwrap_or_else(|_| Err(anyhow!("timed out: no answer within {} s", limit.as_secs()))),
                        None => ask.await,
                    };
                    if let Ok((decision, _)) = &outcome
                        && let Some(cost) = asker.cost(decision)
                    {
                        spent.fetch_add((cost * 1e9) as u64, Ordering::Relaxed);
                    }
                    let elapsed = started.elapsed();
                    let retry_spent = retry.get().min(elapsed);
                    Stored {
                        setup: name,
                        item: index,
                        outcome,
                        request_ms: (elapsed - retry_spent).as_millis() as u64,
                        retry_ms: retry_spent.as_millis() as u64,
                    }
                });
                while let Some(joined) = jobs.try_join_next() {
                    let stored = joined?;
                    asked += 1;
                    failed += stored.outcome.is_err() as usize;
                    store(&conn, &items, &player, &harness, stored)?;
                }
            }
            while let Some(joined) = jobs.join_next().await {
                let stored = joined?;
                asked += 1;
                failed += stored.outcome.is_err() as usize;
                store(&conn, &items, &player, &harness, stored)?;
            }
            println!(
                "[{name}] {asked} asked, {failed} failed in {:.0} s · total ${:.4}{}",
                started.elapsed().as_secs_f64(),
                spent.load(Ordering::Relaxed) as f64 / 1e9,
                stopped.map_or(String::new(), |c| format!(" · stopped: cost ${c:.4} over the limit"))
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

fn store(conn: &Mutex<Connection>, items: &[Item], player: &Player, harness: &Harness, stored: Stored) -> Result<()> {
    let item = &items[stored.item];
    let mut conn = conn.lock();
    let tx = conn.transaction()?;
    let (decision, reply, error) = match &stored.outcome {
        Ok((decision, reply)) => (Some(decision), Some(reply), None),
        Err(error) => {
            println!("[{}] {}: {error:#}", stored.setup, item.id);
            (None, None, Some(format!("{error:#}")))
        }
    };
    let (choice, probabilities, text) = match reply {
        Some(QuizReply::Choice { value, probabilities }) => {
            let map: serde_json::Map<String, Value> =
                probabilities.iter().map(|(v, p)| (v.clone(), Value::from(*p))).collect();
            (value.clone(), Some(Value::Object(map).to_string()), None)
        }
        Some(QuizReply::Text(text)) => (None, None, Some(text.clone())),
        None => (None, None, None),
    };
    tx.execute(
        "DELETE FROM quiz_exchanges WHERE answer_id IN
         (SELECT id FROM quiz_answers WHERE setup = ?1 AND item_id = ?2)",
        params![stored.setup, item.id],
    )?;
    tx.execute(
        "DELETE FROM quiz_answers WHERE setup = ?1 AND item_id = ?2",
        params![stored.setup, item.id],
    )?;
    tx.execute(
        "INSERT INTO quiz_answers (setup, spec, provider, reasoning, item_id, harness_commit,
             harness_dirty, choice, probabilities, text, request_ms, retry_ms, input_tokens,
             output_tokens, reasoning_tokens, cost_usd, error, created_at)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16, ?17, ?18)",
        params![
            stored.setup,
            player.spec,
            player.provider,
            player.reasoning,
            item.id,
            harness.commit,
            harness.dirty,
            choice,
            probabilities,
            text,
            stored.request_ms as i64,
            stored.retry_ms as i64,
            decision.map(|d| d.input_tokens as i64),
            decision.map(|d| d.output_tokens as i64),
            decision.and_then(|d| d.reasoning_tokens).map(|r| r as i64),
            decision.and_then(|d| player.cost(d)),
            error,
            chrono::Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Millis, true),
        ],
    )?;
    let id = tx.last_insert_rowid();
    for (attempt, exchange) in decision.map_or(&[][..], |d| &d.exchanges).iter().enumerate() {
        tx.execute(
            "INSERT INTO quiz_exchanges (answer_id, attempt, request, response, error, latency_ms)
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
