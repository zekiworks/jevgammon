//! League run guard (Zeki #5385), offline: stub System One servers on 127.0.0.1, scratch
//! ledgers, latch files and databases under the temp dir; no network, no production file.
//! Identity: a mismatched model, a mismatched provider, a missing field, a warm-up reply and
//! one group of a split decision each fail closed and latch (nothing more is sent, the league
//! stops and does not start again). Money: retries, warm-ups, failed attempts, decisions in
//! flight at once and an opponent's spend are all reserved before sending in one shared
//! ledger and never pass its cap.
//!
//! Every guard-specific step goes through `support` (setup under a guard file), so the same
//! tests run against a runner without the guard (the RED run on cb669a0 replaces `support`
//! with a stand-in that builds the setup without it).

use std::collections::HashMap;
use std::io::{BufRead, BufReader, Read, Write};
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::Duration;

use serde_json::{Value, json};

use super::{DecisionRequest, Player, PlayerConfig, Setup};
use crate::board::{Board, Play};
use crate::http::RetryTime;
use crate::players::prompt::PromptVersion;

mod support {
    use super::*;
    /// The players' setup under the guard file at `guard` (as `league --guard`).
    pub fn setup(guard: &Path) -> Setup {
        Setup::new(std::env::temp_dir(), "http://127.0.0.1:9/v1".into())
            .with_guard(crate::guard::Guard::load(guard).expect("guard file"))
    }
}

const MODEL: &str = "google/gemini-decision-1-20261111";
const PROVIDER: &str = "Google AI Studio";

/// One stub reply: HTTP status, body, delay before answering.
struct Reply {
    status: u16,
    body: String,
    delay: Duration,
}

impl Reply {
    fn ok(body: String) -> Self {
        Reply {
            status: 200,
            body,
            delay: Duration::ZERO,
        }
    }
}

/// A System One server: answers request `n` (from 0) with `reply(n, request body)`, one thread
/// per connection; counts the requests it received.
struct Stub {
    url: String,
    count: Arc<AtomicUsize>,
}

impl Stub {
    fn start(reply: impl Fn(usize, &Value) -> Reply + Send + Sync + 'static) -> Self {
        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let url = format!("http://{}", listener.local_addr().unwrap());
        let count = Arc::new(AtomicUsize::new(0));
        let seen = count.clone();
        let reply = Arc::new(reply);
        std::thread::spawn(move || {
            for stream in listener.incoming() {
                let Ok(mut stream) = stream else { continue };
                let n = seen.fetch_add(1, Ordering::SeqCst);
                let reply = reply.clone();
                std::thread::spawn(move || {
                    let mut reader = BufReader::new(stream.try_clone().unwrap());
                    let mut length = 0;
                    loop {
                        let mut line = String::new();
                        if reader.read_line(&mut line).unwrap_or(0) == 0 || line == "\r\n" {
                            break;
                        }
                        if let Some((name, value)) = line.split_once(':')
                            && name.eq_ignore_ascii_case("content-length")
                        {
                            length = value.trim().parse().unwrap();
                        }
                    }
                    let mut body = vec![0; length];
                    reader.read_exact(&mut body).unwrap();
                    let request: Value = serde_json::from_slice(&body).unwrap_or(Value::Null);
                    let r = reply(n, &request);
                    std::thread::sleep(r.delay);
                    let _ = write!(
                        stream,
                        "HTTP/1.1 {} X\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
                        r.status,
                        r.body.len(),
                        r.body
                    );
                });
            }
        });
        Stub { url, count }
    }

    fn requests(&self) -> usize {
        self.count.load(Ordering::SeqCst)
    }
}

/// An answer to `request` picking its first option, with `model`/`provider` when given, 1,000
/// input tokens and the provider-reported `cost`.
fn answer(request: &Value, model: Option<&str>, provider: Option<&str>, cost: f64) -> String {
    let keys: Vec<String> = request
        .pointer("/questions/play/criteria")
        .and_then(Value::as_object)
        .map(|c| c.keys().cloned().collect())
        .unwrap_or_default();
    let p = 1.0 / keys.len().max(1) as f64;
    let probabilities: serde_json::Map<String, Value> =
        keys.iter().map(|k| (k.clone(), p.into())).collect();
    let mut reply = json!({
        "id": "gen-stub",
        "answers": {"play": {"type": "choice", "choice": keys.first(), "probabilities": probabilities}},
        "usage": {"input_tokens": 1000, "output_tokens": 0, "cost": cost}
    });
    if let Some(model) = model {
        reply["model"] = model.into();
    }
    if let Some(provider) = provider {
        reply["provider"] = provider.into();
    }
    reply.to_string()
}

fn good(request: &Value) -> String {
    answer(request, Some(MODEL), Some(PROVIDER), 0.0)
}

fn scratch(tag: &str) -> PathBuf {
    let dir = std::env::temp_dir().join(format!("jevgammon-guard-{tag}-{}", uuid::Uuid::new_v4()));
    std::fs::create_dir_all(&dir).unwrap();
    dir
}

/// A guard file in `dir` metering `metered` (name, $ per million input tokens) under `cap`,
/// expecting the frozen identity of `expect`'s replies.
fn guard_file(dir: &Path, cap: f64, metered: &[(&str, f64)], expect: &[&str]) -> PathBuf {
    let path = dir.join("guard.json");
    let metered: serde_json::Map<String, Value> = metered
        .iter()
        .map(|(name, price)| {
            (
                (*name).to_owned(),
                json!({"input_per_mtok": price, "cached_input_per_mtok": price, "output_per_mtok": 0.0}),
            )
        })
        .collect();
    let expect: serde_json::Map<String, Value> = expect
        .iter()
        .map(|name| {
            (
                (*name).to_owned(),
                json!({"models": [MODEL], "provider": PROVIDER}),
            )
        })
        .collect();
    std::fs::write(
        &path,
        json!({"ledger": dir.join("budget.db"), "cap_usd": cap, "latch": dir.join("latch"),
               "metered": metered, "expect_route": expect})
        .to_string(),
    )
    .unwrap();
    path
}

fn latched(dir: &Path) -> bool {
    dir.join("latch").exists()
}

/// Ledger rows `(status, reserved_usd, cost_usd)` in order; empty when there is no ledger.
fn ledger(dir: &Path) -> Vec<(String, f64, Option<f64>)> {
    let path = dir.join("budget.db");
    if !path.exists() {
        return Vec::new();
    }
    let conn = rusqlite::Connection::open(&path).unwrap();
    let mut statement = conn
        .prepare("SELECT status, reserved_usd, cost_usd FROM attempts ORDER BY id")
        .unwrap();
    statement
        .query_map([], |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)))
        .unwrap()
        .collect::<rusqlite::Result<_>>()
        .unwrap()
}

/// Spent (settled + lost) plus reserved (open): what the cap bounds.
fn committed(rows: &[(String, f64, Option<f64>)]) -> f64 {
    rows.iter()
        .map(|(status, reserved, cost)| match status.as_str() {
            "settled" => cost.unwrap_or(0.0),
            _ => *reserved,
        })
        .sum()
}

/// A decision service player (System One, `cygnet`: at most 26 options per request) at `url`.
async fn player(name: &str, url: &str, parallel: usize, setup: &Setup) -> anyhow::Result<Player> {
    let config = PlayerConfig {
        base_url: Some(url.to_owned()),
        parallel: Some(parallel),
        ..PlayerConfig::new(name, "cygnet")
    };
    Player::from_config(&config, setup).await
}

struct Position {
    board: Board,
    plays: Vec<Play>,
    notations: Vec<String>,
    order: Vec<usize>,
    retry: RetryTime,
}

impl Position {
    /// A position with at least `min` legal plays.
    fn with(min: usize) -> Self {
        let mut board = Board::start();
        board.pts[12] = 3;
        board.pts[7] = 5;
        let (plays, _) = [(2, 1), (1, 1), (2, 2), (3, 1), (4, 2), (3, 3)]
            .iter()
            .map(|&(a, b)| (board.legal_plays(a, b), (a, b)))
            .find(|(p, _)| p.len() >= min)
            .expect("a position with enough plays");
        let notations = plays.iter().map(|p| p.notation()).collect();
        let order = (0..plays.len()).rev().collect();
        Position {
            board,
            plays,
            notations,
            order,
            retry: RetryTime::default(),
        }
    }

    fn request(&self) -> DecisionRequest<'_> {
        DecisionRequest {
            board: &self.board,
            dice: (2, 1),
            plays: &self.plays,
            notations: &self.notations,
            my_score: 0,
            opp_score: 0,
            round: 1,
            rounds: 3,
            leg: 1,
            clock: None,
            my_clock: None,
            opp_clock: None,
            turn_no: 1,
            max_turns: None,
            player: 1,
            history: &[],
            order: &self.order,
            seed: 1,
            version: PromptVersion::BgV2,
            retry: &self.retry,
        }
    }
}

/// One decision against a stub replying `reply`; returns the outcome, the stub, the scratch dir.
async fn decide_once(
    tag: &str,
    reply: impl Fn(usize, &Value) -> Reply + Send + Sync + 'static,
) -> (
    anyhow::Result<super::Decision>,
    Stub,
    PathBuf,
    Player,
    Position,
) {
    let stub = Stub::start(reply);
    let dir = scratch(tag);
    let setup = support::setup(&guard_file(&dir, 5.0, &[("G", 0.1)], &["G"]));
    let g = player("G", &stub.url, 1, &setup).await.unwrap();
    let position = Position::with(3);
    let outcome = g.decide(&position.request()).await;
    (outcome, stub, dir, g, position)
}

/// The identity check failed closed: an error naming the route check, the latch file written,
/// and the client sends nothing more.
async fn assert_fails_closed(
    what: &str,
    outcome: anyhow::Result<super::Decision>,
    stub: &Stub,
    dir: &Path,
    g: &Player,
    position: &Position,
) {
    let error = match outcome {
        Ok(decision) => panic!(
            "{what}: the reply was used (index {}): not checked",
            decision.index
        ),
        Err(error) => format!("{error:#}"),
    };
    assert!(error.contains("ROUTE CHECK"), "{what}: {error}");
    assert!(latched(dir), "{what}: no latch file");
    let sent = stub.requests();
    assert!(
        g.decide(&position.request()).await.is_err(),
        "{what}: decided after the latch"
    );
    assert_eq!(
        stub.requests(),
        sent,
        "{what}: a request was sent after the latch"
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn identity_mismatched_model_fails_closed_and_latches() {
    let (outcome, stub, dir, g, position) = decide_once("model", |_, r| {
        Reply::ok(answer(
            r,
            Some("google/gemini-decision-1-20261205"),
            Some(PROVIDER),
            0.0,
        ))
    })
    .await;
    assert_fails_closed("mismatched model", outcome, &stub, &dir, &g, &position).await;
}

#[tokio::test(flavor = "multi_thread")]
async fn identity_mismatched_provider_fails_closed_and_latches() {
    let (outcome, stub, dir, g, position) = decide_once("provider", |_, r| {
        Reply::ok(answer(r, Some(MODEL), Some("Google Vertex"), 0.0))
    })
    .await;
    assert_fails_closed("mismatched provider", outcome, &stub, &dir, &g, &position).await;
}

#[tokio::test(flavor = "multi_thread")]
async fn identity_missing_field_fails_closed_and_latches() {
    let (outcome, stub, dir, g, position) = decide_once("no-provider", |_, r| {
        Reply::ok(answer(r, Some(MODEL), None, 0.0))
    })
    .await;
    assert_fails_closed("missing provider", outcome, &stub, &dir, &g, &position).await;
    let (outcome, stub, dir, g, position) = decide_once("no-model", |_, r| {
        Reply::ok(answer(r, None, Some(PROVIDER), 0.0))
    })
    .await;
    assert_fails_closed("missing model", outcome, &stub, &dir, &g, &position).await;
    // The control: the frozen identity passes, nothing is latched.
    let (outcome, _stub, dir, _g, _position) =
        decide_once("control", |_, r| Reply::ok(good(r))).await;
    assert!(outcome.is_ok(), "{:#}", outcome.unwrap_err());
    assert!(!latched(&dir));
}

#[tokio::test(flavor = "multi_thread")]
async fn identity_warm_up_mismatch_fails_closed_at_once() {
    let stub = Stub::start(|_, r| {
        Reply::ok(answer(
            r,
            Some("google/gemini-decision-2"),
            Some(PROVIDER),
            0.0,
        ))
    });
    let dir = scratch("warm-up");
    let setup = support::setup(&guard_file(&dir, 5.0, &[("G", 0.1)], &["G"]));
    let g = player("G", &stub.url, 1, &setup).await.unwrap();
    let warmed = tokio::time::timeout(Duration::from_secs(30), g.warm_up())
        .await
        .expect("the warm-up ends at once, not after retrying");
    let error = format!(
        "{:#}",
        warmed.expect_err("a warm-up reply with another model passed")
    );
    assert!(error.contains("ROUTE CHECK"), "{error}");
    assert!(latched(&dir));
    assert_eq!(stub.requests(), 1, "one warm-up request, then nothing");
}

#[tokio::test(flavor = "multi_thread")]
async fn identity_split_group_mismatch_fails_closed() {
    // More than 26 options: split into groups (cygnet takes 26 per request); the second
    // group's reply names another provider.
    let stub = Stub::start(|n, r| {
        Reply::ok(answer(
            r,
            Some(MODEL),
            Some(if n == 1 { "Google Vertex" } else { PROVIDER }),
            0.0,
        ))
    });
    let dir = scratch("split");
    let setup = support::setup(&guard_file(&dir, 5.0, &[("G", 0.1)], &["G"]));
    let g = player("G", &stub.url, 1, &setup).await.unwrap();
    let position = Position::with(60);
    assert!(
        position.plays.len().div_ceil(26) >= 3,
        "{} plays",
        position.plays.len()
    );
    let outcome = g.decide(&position.request()).await;
    let error = format!(
        "{:#}",
        outcome.expect_err("a split group's reply with another provider was used")
    );
    assert!(error.contains("ROUTE CHECK"), "{error}");
    assert_eq!(
        stub.requests(),
        2,
        "the groups after the failing one are not sent"
    );
    assert!(latched(&dir));
}

#[tokio::test(flavor = "multi_thread")]
async fn identity_latch_survives_a_restart_and_no_league_starts() {
    let (outcome, stub, dir, _g, position) = decide_once("restart", |_, r| {
        Reply::ok(answer(r, Some(MODEL), Some("Google Vertex"), 0.0))
    })
    .await;
    assert!(outcome.is_err());
    // A new process: the guard file read again, the client built again.
    let setup = support::setup(&dir.join("guard.json"));
    let again = player("G", &stub.url, 1, &setup).await.unwrap();
    assert!(again.decide(&position.request()).await.is_err());
    assert!(again.warm_up().await.is_err());
    assert_eq!(stub.requests(), 1, "nothing sent after the restart");
    let db = dir.join("league.db");
    let started = crate::league::run(
        db.clone(),
        &setup,
        crate::league::Start::Resume(1),
        crate::runner::Harness::default(),
        dir.join("no-scores"),
    )
    .await;
    let error = format!(
        "{:#}",
        started.expect_err("a league started under a latched guard")
    );
    assert!(error.contains("GUARD LATCHED"), "{error}");
    assert!(!db.exists(), "the database was opened");
}

/// A whole league (G v Random): G's replies name another model; the league stops with the
/// guard instead of deferring and retrying, and does not resume.
#[tokio::test(flavor = "multi_thread")]
async fn identity_mismatch_stops_the_league_without_re_entry() {
    let stub = Stub::start(|_, r| {
        Reply::ok(answer(
            r,
            Some("google/gemini-decision-1-20261205"),
            Some(PROVIDER),
            0.0,
        ))
    });
    let dir = scratch("league");
    let setup = support::setup(&guard_file(&dir, 5.0, &[("G", 0.1)], &["G"]));
    let db = dir.join("league.db");
    let models = vec![
        PlayerConfig {
            base_url: Some(stub.url.clone()),
            ..PlayerConfig::new("G", "cygnet")
        },
        PlayerConfig::new("R", "random"),
    ];
    let rules = crate::db::Rules::new(
        1,
        None,
        Some(60),
        "bg-v2",
        9,
        false,
        crate::board::StartPosition::Standard,
    );
    let run = crate::league::run(
        db.clone(),
        &setup,
        crate::league::Start::New {
            models,
            seed: 5,
            rules,
            note: None,
            scope: crate::db::Scope::default(),
        },
        crate::runner::Harness::default(),
        dir.join("no-scores"),
    );
    let ended = tokio::time::timeout(Duration::from_secs(60), run)
        .await
        .expect("the league stops, not retries");
    let error = format!(
        "{:#}",
        ended.expect_err("the league finished on replies naming another model")
    );
    assert!(error.contains("stopped by its run guard"), "{error}");
    assert!(latched(&dir));
    let sent = stub.requests();
    assert_eq!(sent, 1, "only the warm-up reply was received");
    let resumed = crate::league::run(
        db,
        &setup,
        crate::league::Start::Resume(1),
        crate::runner::Harness::default(),
        dir.join("no-scores"),
    )
    .await;
    assert!(format!("{:#}", resumed.expect_err("resumed")).contains("GUARD LATCHED"));
    assert_eq!(stub.requests(), sent);
}

/// The worst case one decision request of `position` reserves at `price` per million input
/// tokens: (request body bytes + the 4,096-token template margin) at that price, the body
/// measured as the stub received it (and, where a ledger meters it, equal to its reservation).
async fn worst_case(position: &Position, price: f64) -> f64 {
    let bytes = Arc::new(AtomicUsize::new(0));
    let seen = bytes.clone();
    let stub = Stub::start(move |_, r| {
        seen.store(r.to_string().len(), Ordering::SeqCst);
        Reply::ok(good(r))
    });
    let dir = scratch("calibrate");
    let setup = support::setup(&guard_file(&dir, 1000.0, &[("G", price)], &[]));
    let g = player("G", &stub.url, 1, &setup).await.unwrap();
    g.decide(&position.request()).await.unwrap();
    let worst = (bytes.load(Ordering::SeqCst) + 4096) as f64 * price / 1e6;
    if let [(_, reserved, _)] = ledger(&dir)[..] {
        assert!((reserved - worst).abs() < 1e-12, "{reserved} {worst}");
    }
    worst
}

#[tokio::test(flavor = "multi_thread")]
async fn money_retries_are_each_reserved_and_settled_from_the_reported_cost() {
    // Two 503s, then an answer reporting $0.5 (its list price: 1,000 tokens x $1/M = $0.001).
    let stub = Stub::start(|n, r| match n {
        0 | 1 => Reply {
            status: 503,
            body: "{}".into(),
            delay: Duration::ZERO,
        },
        _ => Reply::ok(answer(r, Some(MODEL), Some(PROVIDER), 0.5)),
    });
    let dir = scratch("retries");
    let setup = support::setup(&guard_file(&dir, 5.0, &[("G", 1.0)], &["G"]));
    let g = player("G", &stub.url, 1, &setup).await.unwrap();
    let position = Position::with(3);
    g.decide(&position.request()).await.unwrap();
    assert_eq!(stub.requests(), 3);
    let rows = ledger(&dir);
    let statuses: Vec<&str> = rows.iter().map(|r| r.0.as_str()).collect();
    assert_eq!(
        statuses,
        ["lost", "lost", "settled"],
        "every attempt booked: {rows:?}"
    );
    let worst = rows[0].1;
    assert!(worst > 0.001, "{worst}");
    assert_eq!(rows[2].2, Some(0.5), "settled at the reported cost");
    assert!((committed(&rows) - (2.0 * worst + 0.5)).abs() < 1e-9);
}

#[tokio::test(flavor = "multi_thread")]
async fn money_warm_ups_are_reserved_and_settled() {
    let stub = Stub::start(|_, r| Reply::ok(answer(r, Some(MODEL), Some(PROVIDER), 0.25)));
    let dir = scratch("warm-up-money");
    let setup = support::setup(&guard_file(&dir, 5.0, &[("G", 1.0)], &["G"]));
    let g = player("G", &stub.url, 1, &setup).await.unwrap();
    g.warm_up().await.unwrap();
    let rows = ledger(&dir);
    assert_eq!(rows.len(), 1, "the warm-up is metered: {rows:?}");
    assert_eq!((rows[0].0.as_str(), rows[0].2), ("settled", Some(0.25)));
}

#[tokio::test(flavor = "multi_thread")]
async fn money_failed_attempts_keep_their_worst_case() {
    // A 400 (refused, not retried) and a 200 without usage: both kept at the worst case.
    let stub = Stub::start(|n, r| match n {
        0 => Reply {
            status: 400,
            body: r#"{"error":"bad"}"#.into(),
            delay: Duration::ZERO,
        },
        _ => {
            let mut v: Value = serde_json::from_str(&good(r)).unwrap();
            v.as_object_mut().unwrap().remove("usage");
            Reply::ok(v.to_string())
        }
    });
    let dir = scratch("failed");
    let setup = support::setup(&guard_file(&dir, 5.0, &[("G", 1.0)], &["G"]));
    let g = player("G", &stub.url, 1, &setup).await.unwrap();
    let position = Position::with(3);
    assert!(g.decide(&position.request()).await.is_err());
    g.decide(&position.request()).await.unwrap();
    let rows = ledger(&dir);
    assert_eq!(rows.len(), 2, "{rows:?}");
    assert!(rows.iter().all(|r| r.0 == "lost" && r.1 > 0.0), "{rows:?}");
    assert!((committed(&rows) - 2.0 * rows[0].1).abs() < 1e-9);
}

#[tokio::test(flavor = "multi_thread")]
async fn money_in_flight_reservations_bound_concurrent_requests() {
    let position = Position::with(3);
    let worst = worst_case(&position, 1.0).await;
    // Room for one request in flight, not two: the second is refused before it is sent.
    let stub = Stub::start(|_, r| Reply {
        delay: Duration::from_secs(2),
        ..Reply::ok(good(r))
    });
    let dir = scratch("in-flight");
    let cap = 1.5 * worst;
    let setup = support::setup(&guard_file(&dir, cap, &[("G", 1.0)], &["G"]));
    let g = player("G", &stub.url, 2, &setup).await.unwrap();
    let (first, second) = (position.request(), position.request());
    let (a, b) = tokio::join!(g.decide(&first), g.decide(&second));
    assert_eq!(
        stub.requests(),
        1,
        "the second request was sent while the first was in flight"
    );
    let refused = [&a, &b].into_iter().filter(|o| o.is_err()).count();
    assert_eq!(refused, 1);
    let error = format!("{:#}", [a, b].into_iter().find_map(Result::err).unwrap());
    assert!(error.contains("BUDGET CAP"), "{error}");
    assert!(committed(&ledger(&dir)) <= cap + 1e-12);
}

#[tokio::test(flavor = "multi_thread")]
async fn money_opponent_spend_crossing_the_cap_stops_the_entrant_before_sending() {
    let position = Position::with(3);
    let worst = worst_case(&position, 1.0).await;
    let cap = 1.0;
    // The paid opponent's answer reports what leaves less than one worst case for the entrant.
    let reported = cap - worst / 2.0;
    let opponent_stub =
        Stub::start(move |_, r| Reply::ok(answer(r, Some("o"), Some("o"), reported)));
    let entrant_stub = Stub::start(|_, r| Reply::ok(good(r)));
    let dir = scratch("opponent");
    let setup = support::setup(&guard_file(&dir, cap, &[("G", 1.0), ("O", 1.0)], &["G"]));
    let o = player("O", &opponent_stub.url, 1, &setup).await.unwrap();
    let g = player("G", &entrant_stub.url, 1, &setup).await.unwrap();
    o.decide(&position.request()).await.unwrap();
    let refused = g.decide(&position.request()).await;
    let error = format!(
        "{:#}",
        refused.expect_err("the entrant sent past the shared cap")
    );
    assert!(error.contains("BUDGET CAP"), "{error}");
    assert_eq!(entrant_stub.requests(), 0, "refused before sending");
    let rows = ledger(&dir);
    assert!(committed(&rows) <= cap + 1e-12, "{rows:?}");
    let by_setup: HashMap<String, i64> = {
        let conn = rusqlite::Connection::open(dir.join("budget.db")).unwrap();
        let mut s = conn
            .prepare("SELECT setup, count(*) FROM attempts GROUP BY setup")
            .unwrap();
        s.query_map([], |r| Ok((r.get(0)?, r.get(1)?)))
            .unwrap()
            .collect::<rusqlite::Result<_>>()
            .unwrap()
    };
    assert_eq!(by_setup.get("O"), Some(&1), "{by_setup:?}");
    assert_eq!(by_setup.get("G"), None, "{by_setup:?}");
}

/// Zeki #5396 G01: the latch set while a retry waits out its backoff: the retry is neither
/// reserved nor sent; the attempt already sent keeps its accounting.
#[tokio::test(flavor = "multi_thread")]
async fn latch_set_during_backoff_stops_the_retry() {
    let stub = Stub::start(|_, _| Reply {
        status: 503,
        body: "{}".into(),
        delay: Duration::ZERO,
    });
    let dir = scratch("backoff-latch");
    let setup = support::setup(&guard_file(&dir, 5.0, &[("G", 1.0)], &["G"]));
    let g = player("G", &stub.url, 1, &setup).await.unwrap();
    let position = Position::with(3);
    let request = position.request();
    let latch_while_waiting = async {
        while stub.requests() == 0 {
            tokio::time::sleep(Duration::from_millis(20)).await;
        }
        // The first attempt failed (503); its retry waits 2 s. Set the latch meanwhile, as
        // another match's identity failure would.
        tokio::time::sleep(Duration::from_millis(300)).await;
        std::fs::write(dir.join("latch"), "test: latched during the backoff\n").unwrap();
    };
    let (outcome, ()) = tokio::time::timeout(Duration::from_secs(60), async {
        tokio::join!(g.decide(&request), latch_while_waiting)
    })
    .await
    .expect("the decision ends");
    let error = format!(
        "{:#}",
        outcome.expect_err("a retry was answered after the latch")
    );
    assert_eq!(
        stub.requests(),
        1,
        "a retry was sent after the latch was set: {error}"
    );
    assert!(error.contains("GUARD LATCHED"), "{error}");
    let rows = ledger(&dir);
    assert_eq!(
        rows.len(),
        1,
        "only the sent attempt is booked, the retry not reserved: {rows:?}"
    );
    assert!(
        rows[0].0 == "lost" && rows[0].1 > 0.0,
        "the 503 keeps its worst case: {rows:?}"
    );
}

/// Zeki #5396 G02 (cost only): a 200 whose usage reports only its charge is booked at
/// max(worst case, charge), and the next request's reservation is checked against it.
#[tokio::test(flavor = "multi_thread")]
async fn cost_only_usage_is_booked_and_bounds_the_next_send() {
    let position = Position::with(3);
    let worst = worst_case(&position, 1.0).await;
    let charge = 2.0 * worst;
    let stub = Stub::start(move |_, r| {
        let mut v: Value = serde_json::from_str(&good(r)).unwrap();
        v["usage"] = json!({"cost": charge});
        Reply::ok(v.to_string())
    });
    let dir = scratch("cost-only");
    let cap = 2.5 * worst;
    let setup = support::setup(&guard_file(&dir, cap, &[("G", 1.0)], &["G"]));
    let g = player("G", &stub.url, 1, &setup).await.unwrap();
    g.decide(&position.request()).await.unwrap();
    let rows = ledger(&dir);
    assert!(
        (committed(&rows) - charge).abs() < 1e-12,
        "the reported charge is booked: {rows:?}"
    );
    let next = g.decide(&position.request()).await;
    let error = format!(
        "{:#}",
        next.expect_err("sent although the known charge leaves no room")
    );
    assert!(error.contains("BUDGET CAP"), "{error}");
    assert_eq!(stub.requests(), 1, "the next request was sent");
    assert!(committed(&ledger(&dir)) <= cap + 1e-12);
}

/// Zeki #5396 G02 (charged error): an error status whose body reports a charge is booked at
/// max(worst case, charge), never erased, and bounds the next request's reservation.
#[tokio::test(flavor = "multi_thread")]
async fn charged_error_is_booked_and_bounds_the_next_send() {
    let position = Position::with(3);
    let worst = worst_case(&position, 1.0).await;
    let charge = 2.0 * worst;
    let stub = Stub::start(move |n, r| match n {
        0 => Reply {
            status: 400,
            body: json!({"error": {"message": "bad request"}, "usage": {"cost": charge}})
                .to_string(),
            delay: Duration::ZERO,
        },
        _ => Reply::ok(good(r)),
    });
    let dir = scratch("charged-error");
    let cap = 2.5 * worst;
    let setup = support::setup(&guard_file(&dir, cap, &[("G", 1.0)], &["G"]));
    let g = player("G", &stub.url, 1, &setup).await.unwrap();
    assert!(
        g.decide(&position.request()).await.is_err(),
        "the 400 is an error"
    );
    let rows = ledger(&dir);
    assert!(
        (committed(&rows) - charge).abs() < 1e-12,
        "the error's charge is booked: {rows:?}"
    );
    let next = g.decide(&position.request()).await;
    let error = format!(
        "{:#}",
        next.expect_err("sent although the known charge leaves no room")
    );
    assert!(error.contains("BUDGET CAP"), "{error}");
    assert_eq!(stub.requests(), 1, "the next request was sent");
    assert!(committed(&ledger(&dir)) <= cap + 1e-12);
}
