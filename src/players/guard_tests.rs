//! League run guard (Zeki #5385; ported from 959a8a2 for the small chat first stages, Zeki
//! #10062), offline: stub System One servers on 127.0.0.1, scratch ledgers, latch files and
//! databases under the temp dir; no network, no production file. Money: retries, warm-ups,
//! failed attempts, decisions in flight at once and an opponent's spend are all reserved before
//! sending in one shared ledger and never pass its cap; settled at max(list, usage.cost); one
//! ledger shared by two entries (two leagues) stops the second; a refused reservation latches
//! and the latch blocks a restart; under a guard an unexpected paid participant is refused at
//! admission and by the league; a local-only roster needs no guard.

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

/// The players' setup under the guard file at `guard` (as `league --guard`).
fn guarded(guard: &Path) -> Setup {
    Setup::new(std::env::temp_dir(), "http://127.0.0.1:9/v1".into())
        .with_guard(crate::guard::Guard::load(guard).expect("guard file"))
}

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

/// An answer to `request` picking its first option, with 1,000 input tokens and the
/// provider-reported `cost` (`None`: no cost field, as Jev, Celeris, SubQ and Fastino answer).
fn answer(request: &Value, cost: Option<f64>) -> String {
    let keys: Vec<String> = request
        .pointer("/questions/play/criteria")
        .and_then(Value::as_object)
        .map(|c| c.keys().cloned().collect())
        .unwrap_or_default();
    let p = 1.0 / keys.len().max(1) as f64;
    let probabilities: serde_json::Map<String, Value> =
        keys.iter().map(|k| (k.clone(), p.into())).collect();
    let mut usage = json!({"input_tokens": 1000, "output_tokens": 0});
    if let Some(cost) = cost {
        usage["cost"] = cost.into();
    }
    json!({
        "answers": {"play": {"type": "choice", "choice": keys.first(), "probabilities": probabilities}},
        "usage": usage
    })
    .to_string()
}

fn good(request: &Value) -> String {
    answer(request, Some(0.0))
}

fn scratch(tag: &str) -> PathBuf {
    let dir = std::env::temp_dir().join(format!("jevgammon-guard-{tag}-{}", uuid::Uuid::new_v4()));
    std::fs::create_dir_all(&dir).unwrap();
    dir
}

/// A guard file `name` in `dir` metering `metered` (name, $ per million input tokens) under
/// `cap`, with the ledger `budget.db` and the latch `latch` in `dir`.
fn guard_named(dir: &Path, name: &str, cap: f64, metered: &[(&str, f64)]) -> PathBuf {
    let path = dir.join(name);
    let metered: serde_json::Map<String, Value> = metered
        .iter()
        .map(|(name, price)| {
            (
                (*name).to_owned(),
                json!({"input_per_mtok": price, "cached_input_per_mtok": price, "output_per_mtok": 0.0}),
            )
        })
        .collect();
    std::fs::write(
        &path,
        json!({"ledger": dir.join("budget.db"), "cap_usd": cap, "latch": dir.join("latch"),
               "metered": metered})
        .to_string(),
    )
    .unwrap();
    path
}

fn guard_file(dir: &Path, cap: f64, metered: &[(&str, f64)]) -> PathBuf {
    guard_named(dir, "guard.json", cap, metered)
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
fn config(name: &str, url: &str) -> PlayerConfig {
    PlayerConfig {
        base_url: Some(url.to_owned()),
        ..PlayerConfig::new(name, "cygnet")
    }
}

async fn player(name: &str, url: &str, parallel: usize, setup: &Setup) -> anyhow::Result<Player> {
    let config = PlayerConfig {
        parallel: Some(parallel),
        ..config(name, url)
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

/// The worst case one decision request of `position` reserves at `price` per million input
/// tokens: (request body bytes + the 4,096-token template margin) at that price, the body
/// measured as the stub received it (and equal to the ledger's reservation).
async fn worst_case(position: &Position, price: f64) -> f64 {
    let bytes = Arc::new(AtomicUsize::new(0));
    let seen = bytes.clone();
    let stub = Stub::start(move |_, r| {
        seen.store(r.to_string().len(), Ordering::SeqCst);
        Reply::ok(good(r))
    });
    let dir = scratch("calibrate");
    let setup = guarded(&guard_file(&dir, 1000.0, &[("G", price)]));
    let g = player("G", &stub.url, 1, &setup).await.unwrap();
    g.decide(&position.request()).await.unwrap();
    let worst = (bytes.load(Ordering::SeqCst) + 4096) as f64 * price / 1e6;
    let rows = ledger(&dir);
    assert_eq!(rows.len(), 1, "{rows:?}");
    assert!((rows[0].1 - worst).abs() < 1e-12, "{} {worst}", rows[0].1);
    worst
}

/// A league of `models` (1 round, 60 turns, no clock) in `db` under `setup`.
async fn league(
    db: &Path,
    setup: &Setup,
    models: Vec<PlayerConfig>,
    dir: &Path,
) -> anyhow::Result<()> {
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
        db.to_path_buf(),
        setup,
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
    tokio::time::timeout(Duration::from_secs(120), run)
        .await
        .expect("the league ends")
}

async fn resume(db: &Path, setup: &Setup, id: i64, dir: &Path) -> anyhow::Result<()> {
    crate::league::run(
        db.to_path_buf(),
        setup,
        crate::league::Start::Resume(id),
        crate::runner::Harness::default(),
        dir.join("no-scores"),
    )
    .await
}

/// A league config file in `dir` holding `players`.
fn league_config(dir: &Path, players: &[PlayerConfig]) -> PathBuf {
    let path = dir.join("league.json");
    std::fs::write(&path, json!({"players": players}).to_string()).unwrap();
    path
}

/// The entrant of a small chat first stage: a chat server on a loopback address, unmetered.
fn entrant() -> PlayerConfig {
    PlayerConfig {
        base_url: Some("http://127.0.0.1:18614/v1".into()),
        ..PlayerConfig::new("Entrant (on)", "openai-compatible/minicpm5-2b")
    }
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
        _ => Reply::ok(answer(r, Some(0.5))),
    });
    let dir = scratch("retries");
    let setup = guarded(&guard_file(&dir, 5.0, &[("G", 1.0)]));
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

/// Settlement is max(list price, usage.cost): a reported cost above the list price is booked
/// as reported, one below it (or none, as most of the paid services answer) at the list price.
#[tokio::test(flavor = "multi_thread")]
async fn money_settles_at_the_larger_of_list_price_and_reported_cost() {
    // 1,000 input tokens at $100/M: list price $0.1.
    for (reported, booked) in [(Some(0.5), 0.5), (Some(0.01), 0.1), (None, 0.1)] {
        let stub = Stub::start(move |_, r| Reply::ok(answer(r, reported)));
        let dir = scratch("settle");
        let setup = guarded(&guard_file(&dir, 50.0, &[("G", 100.0)]));
        let g = player("G", &stub.url, 1, &setup).await.unwrap();
        g.decide(&Position::with(3).request()).await.unwrap();
        let rows = ledger(&dir);
        assert_eq!(rows.len(), 1, "{rows:?}");
        assert_eq!(rows[0].0, "settled", "{rows:?}");
        let cost = rows[0].2.unwrap();
        assert!(
            (cost - booked).abs() < 1e-12,
            "reported {reported:?}: booked {cost}, expected {booked}"
        );
    }
}

#[tokio::test(flavor = "multi_thread")]
async fn money_warm_ups_are_reserved_and_settled() {
    let stub = Stub::start(|_, r| Reply::ok(answer(r, Some(0.25))));
    let dir = scratch("warm-up-money");
    let setup = guarded(&guard_file(&dir, 5.0, &[("G", 1.0)]));
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
    let setup = guarded(&guard_file(&dir, 5.0, &[("G", 1.0)]));
    let g = player("G", &stub.url, 1, &setup).await.unwrap();
    let position = Position::with(3);
    assert!(g.decide(&position.request()).await.is_err());
    g.decide(&position.request()).await.unwrap();
    let rows = ledger(&dir);
    assert_eq!(rows.len(), 2, "{rows:?}");
    assert!(rows.iter().all(|r| r.0 == "lost" && r.1 > 0.0), "{rows:?}");
    assert!((committed(&rows) - 2.0 * rows[0].1).abs() < 1e-9);
}

/// A cap below one request's worst case: the reservation is refused and nothing reaches the
/// stub, the decision and the warm-up alike.
#[tokio::test(flavor = "multi_thread")]
async fn money_reservation_past_the_cap_is_refused_before_sending() {
    let position = Position::with(3);
    let worst = worst_case(&position, 1.0).await;
    let stub = Stub::start(|_, r| Reply::ok(good(r)));
    let dir = scratch("at-cap");
    let setup = guarded(&guard_file(&dir, worst * 0.99, &[("G", 1.0)]));
    let g = player("G", &stub.url, 1, &setup).await.unwrap();
    let error = format!("{:#}", g.decide(&position.request()).await.unwrap_err());
    assert!(error.contains("BUDGET CAP"), "{error}");
    let tiny = scratch("at-cap-warm-up");
    let setup = guarded(&guard_file(&tiny, 1e-6, &[("G", 1.0)]));
    let g = player("G", &stub.url, 1, &setup).await.unwrap();
    let error = format!("{:#}", g.warm_up().await.unwrap_err());
    assert!(error.contains("BUDGET CAP"), "{error}");
    assert_eq!(stub.requests(), 0, "a request reached the stub");
    assert!(ledger(&dir).is_empty() && ledger(&tiny).is_empty());
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
    let setup = guarded(&guard_file(&dir, cap, &[("G", 1.0)]));
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
async fn money_one_opponents_spend_stops_another_before_sending() {
    let position = Position::with(3);
    let worst = worst_case(&position, 1.0).await;
    let cap = 1.0;
    // One paid opponent's answer reports what leaves less than one worst case for the other.
    let reported = cap - worst / 2.0;
    let first_stub = Stub::start(move |_, r| Reply::ok(answer(r, Some(reported))));
    let second_stub = Stub::start(|_, r| Reply::ok(good(r)));
    let dir = scratch("opponent");
    let setup = guarded(&guard_file(&dir, cap, &[("A", 1.0), ("B", 1.0)]));
    let a = player("A", &first_stub.url, 1, &setup).await.unwrap();
    let b = player("B", &second_stub.url, 1, &setup).await.unwrap();
    a.decide(&position.request()).await.unwrap();
    let error = format!("{:#}", b.decide(&position.request()).await.unwrap_err());
    assert!(error.contains("BUDGET CAP"), "{error}");
    assert_eq!(second_stub.requests(), 0, "refused before sending");
    assert!(committed(&ledger(&dir)) <= cap + 1e-12);
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
    let setup = guarded(&guard_file(&dir, 5.0, &[("G", 1.0)]));
    let g = player("G", &stub.url, 1, &setup).await.unwrap();
    let position = Position::with(3);
    let request = position.request();
    let latch_while_waiting = async {
        while stub.requests() == 0 {
            tokio::time::sleep(Duration::from_millis(20)).await;
        }
        // The first attempt failed (503); its retry waits 2 s. Set the latch meanwhile, as
        // another entry's refused reservation would.
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
        "a retry was sent after the latch: {error}"
    );
    assert!(error.contains("GUARD LATCHED"), "{error}");
    let rows = ledger(&dir);
    assert_eq!(rows.len(), 1, "the retry was reserved: {rows:?}");
    assert!(rows[0].0 == "lost" && rows[0].1 > 0.0, "{rows:?}");
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
    let setup = guarded(&guard_file(&dir, cap, &[("G", 1.0)]));
    let g = player("G", &stub.url, 1, &setup).await.unwrap();
    g.decide(&position.request()).await.unwrap();
    assert!((committed(&ledger(&dir)) - charge).abs() < 1e-12);
    let error = format!("{:#}", g.decide(&position.request()).await.unwrap_err());
    assert!(error.contains("BUDGET CAP"), "{error}");
    assert_eq!(stub.requests(), 1, "the next request was sent");
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
    let setup = guarded(&guard_file(&dir, cap, &[("G", 1.0)]));
    let g = player("G", &stub.url, 1, &setup).await.unwrap();
    assert!(g.decide(&position.request()).await.is_err());
    assert!((committed(&ledger(&dir)) - charge).abs() < 1e-12);
    let error = format!("{:#}", g.decide(&position.request()).await.unwrap_err());
    assert!(error.contains("BUDGET CAP"), "{error}");
    assert_eq!(stub.requests(), 1, "the next request was sent");
}

/// A whole league (a local entrant, played by `random`, v a paid opponent O whose warm-up's
/// worst case passes the cap): no request reaches O's stub, the league stops by its guard and
/// latches; the latch then blocks a restart (resume, a new process's client, admission and
/// the ledger command), and nothing is sent.
#[tokio::test(flavor = "multi_thread")]
async fn league_refused_reservation_latches_and_the_latch_blocks_a_restart() {
    let stub = Stub::start(|_, r| Reply::ok(good(r)));
    let dir = scratch("league-cap");
    let guard = guard_file(&dir, 1e-4, &[("O", 1.0)]);
    let setup = guarded(&guard);
    let db = dir.join("league.db");
    let models = vec![PlayerConfig::new("E", "random"), config("O", &stub.url)];
    let error = format!(
        "{:#}",
        league(&db, &setup, models.clone(), &dir)
            .await
            .expect_err("the league played past its cap")
    );
    assert!(error.contains("stopped by its run guard"), "{error}");
    assert!(error.contains("BUDGET CAP"), "{error}");
    assert_eq!(stub.requests(), 0, "a request reached the paid opponent");
    assert!(latched(&dir));
    assert!(ledger(&dir).is_empty(), "nothing reserved");
    // A restart, as a new process: the guard file read again.
    let again = guarded(&guard);
    let error = format!("{:#}", resume(&db, &again, 1, &dir).await.unwrap_err());
    assert!(error.contains("GUARD LATCHED"), "{error}");
    let fresh_db = dir.join("fresh.db");
    let error = format!(
        "{:#}",
        league(&fresh_db, &again, models.clone(), &dir)
            .await
            .unwrap_err()
    );
    assert!(error.contains("GUARD LATCHED"), "{error}");
    assert!(
        !fresh_db.exists(),
        "the database was opened under the latch"
    );
    let o = player("O", &stub.url, 1, &again).await.unwrap();
    assert!(o.warm_up().await.is_err());
    assert!(o.decide(&Position::with(3).request()).await.is_err());
    let config = league_config(&dir, &models);
    let error = format!(
        "{:#}",
        crate::admit::run(&config, &again).await.unwrap_err()
    );
    assert!(error.contains("GUARD LATCHED"), "{error}");
    let error = format!(
        "{:#}",
        again.guard.as_ref().unwrap().open_ledger().unwrap_err()
    );
    assert!(error.contains("GUARD LATCHED"), "{error}");
    assert_eq!(stub.requests(), 0, "a request was sent after the latch");
}

/// Two entries of one batch (two leagues, each a local entrant v a paid opponent), one guard
/// ledger: the first plays to the end and spends most of the cap; the second's paid opponent
/// is refused before its first request (its warm-up) by what the first spent, and its league
/// stops by its guard. Control: on a fresh ledger with the same cap the second's warm-up is sent.
#[tokio::test(flavor = "multi_thread")]
async fn shared_ledger_across_two_entries_stops_the_second() {
    // O's first answer reports $1, every later one nothing (booked at list: 1,000 tokens at
    // $1/M = $0.001); O2 at $100/M reserves about $0.43 for a warm-up.
    let first = Stub::start(|n, r| Reply::ok(answer(r, Some(if n == 0 { 1.0 } else { 0.0 }))));
    let second = Stub::start(|_, r| Reply::ok(good(r)));
    let dir = scratch("two-entries");
    let cap = 1.2;
    let guard = guard_file(&dir, cap, &[("O", 1.0), ("O2", 100.0)]);
    let db = dir.join("league.db");
    league(
        &db,
        &guarded(&guard),
        vec![PlayerConfig::new("E1", "random"), config("O", &first.url)],
        &dir,
    )
    .await
    .expect("the first entry plays to the end");
    let spent = committed(&ledger(&dir));
    assert!(
        first.requests() > 1 && spent >= 1.0 && spent <= cap,
        "{spent}"
    );
    assert!(!latched(&dir), "the first entry latched");
    // The second entry: a new process, the same guard file, the same database.
    let error = format!(
        "{:#}",
        league(
            &db,
            &guarded(&guard),
            vec![PlayerConfig::new("E2", "random"), config("O2", &second.url)],
            &dir,
        )
        .await
        .expect_err("the second entry played past the shared cap")
    );
    assert!(error.contains("stopped by its run guard"), "{error}");
    assert!(error.contains("BUDGET CAP"), "{error}");
    assert_eq!(
        second.requests(),
        0,
        "the second entry's opponent was sent a request"
    );
    assert!(latched(&dir));
    assert!(committed(&ledger(&dir)) <= cap + 1e-12);
    // Control: the same cap on a fresh ledger lets O2's warm-up through.
    let fresh = scratch("two-entries-control");
    let setup = guarded(&guard_file(&fresh, cap, &[("O", 1.0), ("O2", 100.0)]));
    player("O2", &second.url, 1, &setup)
        .await
        .unwrap()
        .warm_up()
        .await
        .unwrap();
    assert_eq!(second.requests(), 1);
}

/// Under a guard, a participant that is neither metered nor local (here Jev 1.14.0 at
/// TypeSafe's API, and a remote chat server) is refused at admission and by the league's own
/// client construction; the metered opponent, the engines and the loopback entrant are admitted.
#[tokio::test(flavor = "multi_thread")]
async fn unexpected_paid_participant_is_refused_at_admission() {
    let dir = scratch("unexpected");
    let guard = guard_file(&dir, 2.0, &[("O", 1.0)]);
    let setup = guarded(&guard);
    setup.guard.as_ref().unwrap().open_ledger().unwrap();
    let jev = PlayerConfig::new("Jev 1.14.0", "jev/jev-1.14.0");
    let remote_chat = PlayerConfig {
        base_url: Some("https://api.example.com/v1".into()),
        ..PlayerConfig::new("Remote chat", "openai-compatible/some-model")
    };
    let admitted = vec![
        entrant(),
        PlayerConfig::new("Random", "random"),
        PlayerConfig::new("Safest", "safest"),
        config("O", "http://127.0.0.1:9"),
    ];
    let mut players = admitted.clone();
    players.extend([jev.clone(), remote_chat]);
    let config_path = league_config(&dir, &players);
    let result = crate::admit::admit(&config_path, &setup).await.unwrap();
    let refused: Vec<(&str, &str)> = result
        .clients
        .iter()
        .filter_map(|a| a.refused.as_deref().map(|why| (a.name.as_str(), why)))
        .collect();
    assert_eq!(refused.len(), 2, "{refused:?}");
    assert_eq!(refused[0].0, "Jev 1.14.0");
    assert!(
        refused[0].1.contains("unexpected paid participant"),
        "{refused:?}"
    );
    assert_eq!(refused[1].0, "Remote chat");
    assert!(crate::admit::run(&config_path, &setup).await.is_err());
    let error = format!(
        "{:#}",
        Player::from_config(&jev, &setup).await.err().unwrap()
    );
    assert!(error.contains("unexpected paid participant"), "{error}");
    // Without the unexpected players, admission passes.
    let ok = league_config(&scratch("expected"), &admitted);
    crate::admit::run(&ok, &setup).await.unwrap();
}

/// A local-only roster (loopback entrant, engines, a decision server on 127.0.0.1) needs no
/// guard: admitted without one, every client local; a remote chat server is still refused at
/// admission without a guard.
#[tokio::test(flavor = "multi_thread")]
async fn local_only_roster_is_admitted_without_a_guard() {
    let dir = scratch("local-only");
    let setup = Setup::new(PathBuf::new(), String::new());
    let players = vec![
        entrant(),
        PlayerConfig::new("Random", "random"),
        PlayerConfig::new("Safest", "safest"),
        config("Local decider", "http://127.0.0.1:9"),
    ];
    let config_path = league_config(&dir, &players);
    let admitted = crate::admit::admit(&config_path, &setup).await.unwrap();
    assert!(
        admitted.clients.iter().all(|a| a.refused.is_none()),
        "{:?}",
        admitted.clients
    );
    assert!(players.iter().all(|p| super::runs_locally(p, &setup)));
    crate::admit::run(&config_path, &setup).await.unwrap();
    let remote = vec![PlayerConfig {
        base_url: Some("https://api.example.com/v1".into()),
        ..PlayerConfig::new("Remote chat", "openai-compatible/some-model")
    }];
    let refused = crate::admit::admit(&league_config(&scratch("remote"), &remote), &setup)
        .await
        .unwrap();
    assert!(refused.clients[0].refused.is_some());
    assert!(!dir.join("budget.db").exists(), "a ledger was created");
}
