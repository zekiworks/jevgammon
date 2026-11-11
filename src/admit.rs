//! `jevgammon admit`: offline client admission before a league writes anything. Every
//! player of a league config and every opponent its `pinned_pairs` names (with its
//! `players.settings`, as `league-add --entry` adds it) gets its client built by
//! `Player::for_admission`: the construction `Player::from_config` (the call a league makes
//! for each participant) does, restricted to decision services and the local engines (any
//! other client type, e.g. a subscription login that could refresh a token, is refused
//! before anything is constructed) and with every budget ledger opened read-only and
//! immutable. No request is sent and the database is read the same way: no database,
//! ledger or credential file is written, created or locked (gnubg-weak, as in a league,
//! starts gnubg from a temporary directory it removes).
//!
//! Read immutably, the database is its main file only: a change still in the write-ahead
//! log (a new row, or an UPDATE of an existing opponent's row) is not seen, while the
//! league later reads the current rows. So a successful admission ends with one line,
//! `admitted-settings {json}`, naming exactly what was admitted: the SHA-256 of the config
//! file read (the config players' settings) and, for each pinned opponent, its players row
//! and the SHA-256 of the settings text its client was built from. The launcher compares
//! that record with an ordinary read-only (write-ahead-log-aware) read before it prepares
//! or starts anything and refuses any difference.

use std::path::Path;

use anyhow::{Context, Result, bail};
use rusqlite::OptionalExtension;

use crate::league::LeagueConfig;
use crate::players::{Player, PlayerConfig, Setup};

/// One player's admission: its name, spec, where its settings came from (for a pinned
/// opponent its players row and the SHA-256 of the settings text read), and why its client
/// was refused (`None`: built).
#[derive(Debug)]
pub struct Admission {
    pub name: String,
    pub spec: String,
    pub source: String,
    /// The pinned opponent's `players.id` (`None`: a config player, or no row).
    pub player_id: Option<i64>,
    /// SHA-256 of the `players.settings` text the pinned opponent's client was built from
    /// (`None`: a config player, bound by the config file's SHA-256, or no row).
    pub settings_sha256: Option<String>,
    pub refused: Option<String>,
}

impl Admission {
    fn new(name: &str, source: String) -> Self {
        Self {
            name: name.to_owned(),
            spec: String::new(),
            source,
            player_id: None,
            settings_sha256: None,
            refused: None,
        }
    }
}

/// One admission run: the SHA-256 of the config file read and every client's admission.
#[derive(Debug)]
pub struct Admitted {
    pub config_sha256: String,
    pub clients: Vec<Admission>,
}

/// Prints one line per player and fails when any client was refused; else ends with the
/// `admitted-settings` record.
pub async fn run(db: &Path, config: &Path, setup: &Setup) -> Result<()> {
    let admitted = admit(db, config, setup).await?;
    for a in &admitted.clients {
        match &a.refused {
            None => println!(
                "ok       {} ({}; {}): client built",
                a.name, a.spec, a.source
            ),
            Some(why) => println!("REFUSED  {} ({}; {}): {why}", a.name, a.spec, a.source),
        }
    }
    let refused = admitted
        .clients
        .iter()
        .filter(|a| a.refused.is_some())
        .count();
    if refused > 0 {
        bail!(
            "{refused} of {} clients refused; nothing may be written for {}",
            admitted.clients.len(),
            config.display()
        );
    }
    println!(
        "admitted: all {} clients of {} built (players: league config; pinned opponents: {} players.settings, read immutably)",
        admitted.clients.len(),
        config.display(),
        db.display()
    );
    println!("admitted-settings {}", record(config, &admitted));
    Ok(())
}

/// The `admitted-settings` record (one line of JSON): the config file and its SHA-256, then
/// every client in admission order with its source, players row and settings SHA-256.
fn record(config: &Path, admitted: &Admitted) -> serde_json::Value {
    let clients: Vec<_> = admitted
        .clients
        .iter()
        .map(|a| {
            serde_json::json!({"name": a.name, "source": a.source, "player_id": a.player_id,
                               "settings_sha256": a.settings_sha256})
        })
        .collect();
    serde_json::json!({"config": config.display().to_string(),
                       "config_sha256": admitted.config_sha256, "clients": clients})
}

fn sha256(bytes: &[u8]) -> String {
    use sha2::Digest as _;
    hex::encode(sha2::Sha256::digest(bytes))
}

/// The config's players first, then each pinned opponent the config does not hold.
pub async fn admit(db: &Path, config: &Path, setup: &Setup) -> Result<Admitted> {
    // Parsed from the bytes whose SHA-256 is recorded (as `LeagueConfig::load` parses them).
    let text =
        std::fs::read_to_string(config).with_context(|| format!("reading {}", config.display()))?;
    let league: LeagueConfig =
        serde_json::from_str(&text).with_context(|| format!("parsing {}", config.display()))?;
    // Read-only and immutable: nothing written, locked or created, whatever else runs.
    let conn = crate::db::open_immutable(db)?;
    let mut entries: Vec<(Result<PlayerConfig>, Admission)> = league
        .players
        .iter()
        .map(|p| {
            (
                Ok(p.clone()),
                Admission::new(&p.name, "league config".to_owned()),
            )
        })
        .collect();
    for name in league.pinned_pairs.iter().flat_map(|pins| pins.keys()) {
        if league.players.iter().any(|p| &p.name == name) {
            continue;
        }
        let row: Option<(i64, String)> = conn
            .query_row(
                "SELECT id, settings FROM players WHERE name = ?1",
                [name],
                |r| Ok((r.get(0)?, r.get(1)?)),
            )
            .optional()?;
        entries.push(match row {
            Some((id, settings)) => (
                serde_json::from_str(&settings).with_context(|| format!("players #{id}: settings")),
                Admission {
                    player_id: Some(id),
                    settings_sha256: Some(sha256(settings.as_bytes())),
                    ..Admission::new(name, format!("players #{id}"))
                },
            ),
            None => (
                Err(anyhow::anyhow!(
                    "pinned opponent without a players row in the database file (read immutably: a row still only in its write-ahead log is not seen)"
                )),
                Admission::new(name, "players: none".to_owned()),
            ),
        });
    }
    let mut clients = Vec::new();
    for (config, mut admission) in entries {
        admission.spec = config.as_ref().map_or(String::new(), |c| c.spec.clone());
        admission.refused = match config {
            Err(error) => Some(format!("{error:#}")),
            Ok(config) => build(&config, setup).await.err().map(|e| format!("{e:#}")),
        };
        clients.push(admission);
    }
    Ok(Admitted {
        config_sha256: sha256(text.as_bytes()),
        clients,
    })
}

async fn build(config: &PlayerConfig, setup: &Setup) -> Result<()> {
    Player::for_admission(config, setup).await.map(drop)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::budget::Ledger;
    use rusqlite::Connection;
    use std::path::PathBuf;
    use std::sync::Arc;
    use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};

    /// A fresh scratch directory under the temp dir (TMPDIR).
    fn scratch(tag: &str) -> PathBuf {
        let dir =
            std::env::temp_dir().join(format!("jevgammon-admit-{tag}-{}", uuid::Uuid::new_v4()));
        std::fs::create_dir_all(&dir).unwrap();
        dir
    }

    /// Name, SHA-256 and modification time of a file and of its `-wal` and `-shm` (`None`:
    /// absent).
    type Snapshot = Vec<(String, Option<(String, std::time::SystemTime)>)>;

    fn snapshot(paths: &[&Path]) -> Snapshot {
        use sha2::Digest as _;
        paths
            .iter()
            .flat_map(|p| ["", "-wal", "-shm"].map(|s| format!("{}{s}", p.display())))
            .map(|p| {
                let state = std::fs::read(&p).ok().map(|bytes| {
                    (
                        hex::encode(sha2::Sha256::digest(&bytes)),
                        std::fs::metadata(&p).unwrap().modified().unwrap(),
                    )
                });
                (p, state)
            })
            .collect()
    }

    fn budget(path: &Path, cap: f64) -> serde_json::Value {
        serde_json::json!({"ledger": path, "cap_usd": cap, "input_per_mtok": 0.03,
                           "cached_input_per_mtok": 0.03, "output_per_mtok": 0.0})
    }

    /// A ledger as `Ledger::open` leaves it, closed: WAL mode, no `-wal`/`-shm` left.
    fn ledger(path: &Path, cap: f64) {
        drop(Ledger::open(&serde_json::from_value(budget(path, cap)).unwrap(), "x").unwrap());
        assert!(!Path::new(&format!("{}-wal", path.display())).exists());
    }

    /// A connection that never checkpoints, holding committed pages in the write-ahead log.
    fn holder(path: &Path) -> Connection {
        let conn = Connection::open(path).unwrap();
        conn.pragma_update(None, "wal_autocheckpoint", 0).unwrap();
        conn
    }

    fn book(conn: &Connection) {
        conn.execute(
            "INSERT INTO attempts (setup, pid, started_at, status, reserved_usd) VALUES ('w', 1, 't', 'lost', 0)",
            [],
        )
        .unwrap();
    }

    fn wal_len(path: &Path) -> u64 {
        std::fs::metadata(format!("{}-wal", path.display())).map_or(0, |m| m.len())
    }

    /// Players rows, checkpointed into the database file (the connection closes last).
    fn players(db: &Path, rows: &[(&str, serde_json::Value)]) {
        let conn = Connection::open(db).unwrap();
        for (name, settings) in rows {
            let spec = settings["spec"].as_str().unwrap();
            conn.execute(
                "INSERT INTO players (name, spec, settings, created_at) VALUES (?1, ?2, ?3, '2026-11-11T00:00:00Z')",
                rusqlite::params![name, spec, settings.to_string()],
            )
            .unwrap();
        }
        drop(conn);
        assert_eq!(wal_len(db), 0);
    }

    #[tokio::test]
    async fn every_config_player_and_pinned_opponent_is_built_or_refused_read_only() {
        let dir = scratch("roster");
        let db = dir.join("v3.db");
        drop(crate::db::Db::open(&db).unwrap());
        players(
            &db,
            &[
                (
                    "Opp reax",
                    serde_json::json!({"name": "Opp reax", "spec": "reax/reax13"}),
                ),
                (
                    "Opp unknown",
                    serde_json::json!({"name": "Opp unknown", "spec": "nosuch/model"}),
                ),
                (
                    "Opp openai",
                    serde_json::json!({"name": "Opp openai", "spec": "openai/gpt-5.6"}),
                ),
                (
                    "Random",
                    serde_json::json!({"name": "Random", "spec": "random"}),
                ),
            ],
        );
        // A database another connection is writing to: a row committed but only in the
        // write-ahead log (not read: the file is read immutably), the log and the shared
        // memory index present.
        let db_holder = holder(&db);
        db_holder
            .execute(
                "INSERT INTO players (name, spec, settings, created_at) VALUES ('Opp in log', 'random', '{\"name\":\"Opp in log\",\"spec\":\"random\"}', 't')",
                [],
            )
            .unwrap();
        assert!(wal_len(&db) > 0);
        let clean = dir.join("clean-ledger.db");
        ledger(&clean, 1.25);
        let pending = dir.join("pending-ledger.db");
        ledger(&pending, 1.25);
        let pending_holder = holder(&pending);
        book(&pending_holder);
        assert!(wal_len(&pending) > 0);
        let other_cap = dir.join("other-cap-ledger.db");
        ledger(&other_cap, 2.0);
        let missing = dir.join("missing-ledger.db");
        let compat_missing = dir.join("compat-ledger.db");
        let qfork = dir.join("qfork-root");
        let config = dir.join("config.json");
        let pin = serde_json::json!({"seed": 1, "seat_first": true});
        std::fs::write(
            &config,
            serde_json::json!({
                "players": [
                    {"name": "Entrant", "spec": "drex-max/drex-max-v1"},
                    {"name": "Budgeted", "spec": "drex-max/drex-max-v1", "budget": budget(&clean, 1.25)},
                    {"name": "No ledger", "spec": "drex-max/drex-max-v1", "budget": budget(&missing, 1.25)},
                    {"name": "Random", "spec": "random"},
                    {"name": "Pending log", "spec": "drex-max/drex-max-v1", "budget": budget(&pending, 1.25)},
                    {"name": "Other cap", "spec": "drex-max/drex-max-v1", "budget": budget(&other_cap, 1.25)},
                    {"name": "Sub openai", "spec": "openai/gpt-5.6"},
                    {"name": "Sub anthropic", "spec": "anthropic/claude-x"},
                    {"name": "Sub antigravity", "spec": "antigravity/gemini-x"},
                    {"name": "Sub xai", "spec": "xai/grok-x"},
                    {"name": "Gemini", "spec": "gemini/gemini-x"},
                    {"name": "Ollama", "spec": "ollama/m"},
                    {"name": "Local", "spec": "local/m"},
                    {"name": "Compat", "spec": "openai-compatible/m", "base_url": "http://127.0.0.1:9/v1",
                     "budget": budget(&compat_missing, 1.0)}
                ],
                "only_pairs_of": "Entrant",
                "pinned_pairs": {"Opp in log": pin, "Opp reax": pin, "Opp unknown": pin, "Opp openai": pin,
                                 "Opp missing": pin, "Random": pin}
            })
            .to_string(),
        )
        .unwrap();
        let files: [&Path; 4] = [&db, &clean, &pending, &other_cap];
        let before = snapshot(&files);
        let setup = Setup::new(qfork.clone(), "http://127.0.0.1:9/v1".into());
        let admissions = admit(&db, &config, &setup).await.unwrap().clients;
        let outcome: Vec<(&str, &str, Option<&str>)> = admissions
            .iter()
            .map(|a| (a.name.as_str(), a.source.as_str(), a.refused.as_deref()))
            .collect();
        assert_eq!(outcome.len(), 19, "{outcome:?}");
        let refused = |i: usize, why: &str| {
            assert!(
                outcome[i].2.is_some_and(|r| r.contains(why)),
                "{i}: {outcome:?}"
            );
        };
        assert_eq!(outcome[0], ("Entrant", "league config", None));
        assert_eq!(outcome[1], ("Budgeted", "league config", None));
        refused(2, "does not exist");
        assert_eq!(outcome[3], ("Random", "league config", None));
        // Committed pages still in the ledger's write-ahead log: read as the main file has
        // them, nothing checkpointed.
        assert_eq!(outcome[4], ("Pending log", "league config", None));
        refused(5, "has cap $2, the config says $1.25");
        // Every client type outside the roster, refused before its constructor runs: the
        // constructors would ask for a login (openai, anthropic, antigravity, xai), a Gemini
        // key (qfork root), a key variable, or open (create) the budget ledger.
        for i in 6..=13 {
            refused(i, "outside the admission roster");
            refused(i, "refused before its client is constructed");
        }
        // Pinned opponents in name order; Random is the config's, not read again.
        assert_eq!(outcome[14].0, "Opp in log");
        refused(14, "a row still only in its write-ahead log is not seen");
        assert_eq!(outcome[15].0, "Opp missing");
        refused(15, "pinned opponent without a players row");
        assert_eq!(outcome[16].0, "Opp openai");
        assert!(outcome[16].1.starts_with("players #"));
        refused(
            16,
            "provider `openai` of `openai/gpt-5.6` is outside the admission roster",
        );
        assert_eq!(outcome[17].0, "Opp reax");
        assert!(outcome[17].1.starts_with("players #") && outcome[17].2.is_none());
        assert_eq!(outcome[18].0, "Opp unknown");
        refused(18, "provider `nosuch`");
        assert_eq!(snapshot(&files), before, "a file changed");
        assert!(!missing.exists() && !compat_missing.exists() && !qfork.exists());
        for ledger in [&clean, &other_cap] {
            for side in ["-wal", "-shm"] {
                assert!(!Path::new(&format!("{}{side}", ledger.display())).exists());
            }
        }
        assert!(run(&db, &config, &setup).await.is_err());
        assert_eq!(snapshot(&files), before, "a file changed");
        drop((pending_holder, db_holder));
    }

    /// Zeki #4928 S1: an existing pinned opponent's row replaced by an UPDATE still only in
    /// the write-ahead log (Clef: `clef` checkpointed, `openai/review-placeholder` committed in
    /// the log). Admission reads the main file and admits the checkpointed `clef`; its record
    /// says so (the row and the SHA-256 of exactly that text, and the config file's SHA-256),
    /// so the write-ahead-log-aware read the league makes (here an ordinary read-only
    /// connection) gives another SHA-256 and the launcher refuses. Nothing is written.
    #[tokio::test]
    async fn the_admitted_settings_record_names_the_text_read() {
        let dir = scratch("record");
        let db = dir.join("v3.db");
        drop(crate::db::Db::open(&db).unwrap());
        let checkpointed = serde_json::json!({"name": "Clef", "spec": "clef"});
        players(&db, &[("Clef", checkpointed.clone())]);
        let writer = holder(&db);
        let replaced = serde_json::json!({"name": "Clef", "spec": "openai/review-placeholder"});
        writer
            .execute(
                "UPDATE players SET spec = 'openai/review-placeholder', settings = ?1 WHERE name = 'Clef'",
                [replaced.to_string()],
            )
            .unwrap();
        assert!(wal_len(&db) > 0);
        let clef_id: i64 = writer
            .query_row("SELECT id FROM players WHERE name = 'Clef'", [], |r| {
                r.get(0)
            })
            .unwrap();
        let config = dir.join("config.json");
        let text = serde_json::json!({"players": [{"name": "Entrant", "spec": "random"}],
                                      "only_pairs_of": "Entrant",
                                      "pinned_pairs": {"Clef": {"seed": 1, "seat_first": true}}})
        .to_string();
        std::fs::write(&config, &text).unwrap();
        let before = snapshot(&[&db]);
        let setup = Setup::new(dir.join("qfork-root"), "http://127.0.0.1:9/v1".into());
        let admitted = admit(&db, &config, &setup).await.unwrap();
        assert_eq!(snapshot(&[&db]), before, "a file changed");
        assert_eq!(admitted.config_sha256, sha256(text.as_bytes()));
        let entrant = &admitted.clients[0];
        assert_eq!(
            (
                entrant.name.as_str(),
                entrant.source.as_str(),
                entrant.player_id,
                &entrant.settings_sha256,
                &entrant.refused
            ),
            ("Entrant", "league config", None, &None, &None)
        );
        let clef = &admitted.clients[1];
        assert_eq!(admitted.clients.len(), 2);
        assert_eq!(
            (
                clef.name.as_str(),
                clef.spec.as_str(),
                clef.player_id,
                &clef.refused
            ),
            ("Clef", "clef", Some(clef_id), &None)
        );
        assert_eq!(
            clef.settings_sha256.as_deref(),
            Some(sha256(checkpointed.to_string().as_bytes()).as_str())
        );
        let record = record(&config, &admitted);
        assert_eq!(
            record,
            serde_json::json!({"config": config.display().to_string(),
                               "config_sha256": sha256(text.as_bytes()),
                               "clients": [
                {"name": "Entrant", "source": "league config", "player_id": null, "settings_sha256": null},
                {"name": "Clef", "source": format!("players #{clef_id}"), "player_id": clef_id,
                 "settings_sha256": sha256(checkpointed.to_string().as_bytes())}]})
        );
        // What the league reads (write-ahead-log-aware): the replacement, another SHA-256.
        let current: String = Connection::open_with_flags(
            &db,
            rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY | rusqlite::OpenFlags::SQLITE_OPEN_NO_MUTEX,
        )
        .unwrap()
        .query_row(
            "SELECT settings FROM players WHERE id = ?1",
            [clef_id],
            |r| r.get(0),
        )
        .unwrap();
        assert_eq!(current, replaced.to_string());
        assert_ne!(
            clef.settings_sha256.as_deref(),
            Some(sha256(current.as_bytes()).as_str())
        );
        drop(writer);
    }

    /// A writer that keeps committing to the shared ledger (never checkpointing, so only
    /// admission could change the main file) while admission runs over and over, and a writer
    /// holding an open write transaction: every admission admits and leaves the ledger as
    /// the writers have it.
    #[tokio::test(flavor = "multi_thread", worker_threads = 2)]
    async fn ledger_admission_is_unchanged_under_a_concurrent_writer() {
        let dir = scratch("writer");
        let db = dir.join("v3.db");
        drop(crate::db::Db::open(&db).unwrap());
        players(
            &db,
            &[(
                "Safest",
                serde_json::json!({"name": "Safest", "spec": "safest"}),
            )],
        );
        let shared = dir.join("nace-budget.db");
        ledger(&shared, 1.25);
        let config = dir.join("config.json");
        std::fs::write(
            &config,
            serde_json::json!({"players": [
                {"name": "Drex Max 1.1", "spec": "drex-max/drex-max-v1", "budget": budget(&shared, 1.25)},
                {"name": "Random", "spec": "random"}
            ], "only_pairs_of": "Drex Max 1.1", "pinned_pairs": {"Safest": {"seed": 1, "seat_first": true}}})
            .to_string(),
        )
        .unwrap();
        let main_file = std::fs::read(&shared).unwrap();
        let stop = Arc::new(AtomicBool::new(false));
        let commits = Arc::new(AtomicU64::new(0));
        let writer = {
            let (shared, stop, commits) = (shared.clone(), stop.clone(), commits.clone());
            std::thread::spawn(move || {
                let conn = holder(&shared);
                while !stop.load(Ordering::Relaxed) {
                    book(&conn);
                    commits.fetch_add(1, Ordering::Relaxed);
                }
                conn
            })
        };
        let setup = Setup::new(dir.join("qfork-root"), "http://127.0.0.1:9/v1".into());
        while commits.load(Ordering::Relaxed) == 0 {
            std::thread::yield_now();
        }
        // At least 50 admissions, and until the writer has committed 200 times.
        let mut admitted = 0;
        while admitted < 50 || commits.load(Ordering::Relaxed) < 200 {
            let admissions = admit(&db, &config, &setup).await.unwrap().clients;
            assert!(
                admissions.len() == 3 && admissions.iter().all(|a| a.refused.is_none()),
                "{admissions:?}"
            );
            admitted += 1;
        }
        stop.store(true, Ordering::Relaxed);
        let conn = writer.join().unwrap();
        let during = commits.load(Ordering::Relaxed);
        assert!(during >= 200, "the writer committed {during} times");
        assert!(wal_len(&shared) > 0);
        assert_eq!(
            std::fs::read(&shared).unwrap(),
            main_file,
            "the ledger's main file changed"
        );
        // A writer in the middle of a write transaction (holding the write lock): admitted,
        // and the ledger, its log and its shared memory are byte-identical.
        conn.execute_batch("BEGIN IMMEDIATE").unwrap();
        book(&conn);
        let before = snapshot(&[&shared, &db]);
        let admissions = admit(&db, &config, &setup).await.unwrap().clients;
        assert!(
            admissions.iter().all(|a| a.refused.is_none()),
            "{admissions:?}"
        );
        assert_eq!(snapshot(&[&shared, &db]), before, "a file changed");
        conn.execute_batch("COMMIT").unwrap();
        // The database, closed by its last writer, gained no `-wal` or `-shm`.
        for side in ["-wal", "-shm"] {
            assert!(!Path::new(&format!("{}{side}", db.display())).exists());
        }
        let rows: i64 = conn
            .query_row("SELECT COUNT(*) FROM attempts", [], |r| r.get(0))
            .unwrap();
        assert_eq!(rows as u64, during + 1);
    }

    /// Admission needs no write access: a ledger in a directory nobody may write to, the
    /// file itself read-only, is admitted and nothing is created next to it.
    #[tokio::test]
    async fn ledger_admission_needs_no_write_access() {
        use std::os::unix::fs::PermissionsExt as _;
        let dir = scratch("ro");
        let db = dir.join("v3.db");
        drop(crate::db::Db::open(&db).unwrap());
        let ro = dir.join("ledgers");
        std::fs::create_dir(&ro).unwrap();
        let path = ro.join("budget.db");
        ledger(&path, 1.25);
        let config = dir.join("config.json");
        std::fs::write(
            &config,
            serde_json::json!({"players": [
                {"name": "Budgeted", "spec": "drex-max/drex-max-v1", "budget": budget(&path, 1.25)}
            ]})
            .to_string(),
        )
        .unwrap();
        std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o444)).unwrap();
        std::fs::set_permissions(&ro, std::fs::Permissions::from_mode(0o555)).unwrap();
        // Root writes anyway: then the check means nothing.
        let enforced = std::fs::write(ro.join("probe"), b"").is_err();
        let before = snapshot(&[&path]);
        let setup = Setup::new(dir.join("qfork-root"), "http://127.0.0.1:9/v1".into());
        let admissions = admit(&db, &config, &setup).await.unwrap().clients;
        assert!(
            admissions.iter().all(|a| a.refused.is_none()),
            "{admissions:?}"
        );
        assert_eq!(snapshot(&[&path]), before);
        let entries: Vec<_> = std::fs::read_dir(&ro)
            .unwrap()
            .map(|e| e.unwrap().file_name())
            .collect();
        std::fs::set_permissions(&ro, std::fs::Permissions::from_mode(0o755)).unwrap();
        std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o644)).unwrap();
        assert!(enforced, "running as root: write protection not enforced");
        assert_eq!(entries, vec![std::ffi::OsString::from("budget.db")]);
    }
}
