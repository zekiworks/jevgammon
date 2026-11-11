//! `jevgammon admit`: offline client admission before a league writes anything. Every
//! player of a league config and every opponent its `pinned_pairs` names (with its
//! `players.settings`, as `league-add --entry` adds it) gets its client built by
//! `Player::from_config`, the call a league makes for each participant; no request is sent
//! and the database is opened read-only.

use std::path::Path;

use anyhow::{Context, Result, bail};
use rusqlite::{Connection, OpenFlags, OptionalExtension};

use crate::budget::BudgetConfig;
use crate::league::LeagueConfig;
use crate::players::{Player, PlayerConfig, Setup};

/// One player's admission: its name, spec, where its settings came from, and why its client
/// was refused (`None`: built).
#[derive(Debug)]
pub struct Admission {
    pub name: String,
    pub spec: String,
    pub source: String,
    pub refused: Option<String>,
}

/// Prints one line per player and fails when any client was refused.
pub async fn run(db: &Path, config: &Path, setup: &Setup) -> Result<()> {
    let admissions = admit(db, config, setup).await?;
    for a in &admissions {
        match &a.refused {
            None => println!(
                "ok       {} ({}; {}): client built",
                a.name, a.spec, a.source
            ),
            Some(why) => println!("REFUSED  {} ({}; {}): {why}", a.name, a.spec, a.source),
        }
    }
    let refused = admissions.iter().filter(|a| a.refused.is_some()).count();
    if refused > 0 {
        bail!(
            "{refused} of {} clients refused; nothing may be written for {}",
            admissions.len(),
            config.display()
        );
    }
    println!(
        "admitted: all {} clients of {} built (players: league config; pinned opponents: {} players.settings, read-only)",
        admissions.len(),
        config.display(),
        db.display()
    );
    Ok(())
}

/// The config's players first, then each pinned opponent the config does not hold.
pub async fn admit(db: &Path, config: &Path, setup: &Setup) -> Result<Vec<Admission>> {
    let league = LeagueConfig::load(config)?;
    let conn = Connection::open_with_flags(db, OpenFlags::SQLITE_OPEN_READ_ONLY)
        .with_context(|| format!("opening {} read-only", db.display()))?;
    let mut entries: Vec<(Result<PlayerConfig>, String, String)> = league
        .players
        .iter()
        .map(|p| (Ok(p.clone()), p.name.clone(), "league config".to_owned()))
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
                name.clone(),
                format!("players #{id}"),
            ),
            None => (
                Err(anyhow::anyhow!("pinned opponent without a players row")),
                name.clone(),
                "players: none".to_owned(),
            ),
        });
    }
    let mut admissions = Vec::new();
    for (config, name, source) in entries {
        let spec = config.as_ref().map_or(String::new(), |c| c.spec.clone());
        let refused = match config {
            Err(error) => Some(format!("{error:#}")),
            Ok(config) => build(&config, setup).await.err().map(|e| format!("{e:#}")),
        };
        admissions.push(Admission {
            name,
            spec,
            source,
            refused,
        });
    }
    Ok(admissions)
}

async fn build(config: &PlayerConfig, setup: &Setup) -> Result<()> {
    if let Some(budget) = &config.budget {
        ledger_opens_unchanged(budget)?;
    }
    Player::from_config(config, setup).await.map(drop)
}

/// `Ledger::open` (part of building a client with a budget) changes a ledger that is
/// missing, not in WAL mode, lacks a table or the cap row, and closing it checkpoints a
/// pending write-ahead log into it; admission refuses those, so building leaves the ledger
/// as it is. A different cap is refused by `Ledger::open` itself.
fn ledger_opens_unchanged(budget: &BudgetConfig) -> Result<()> {
    let path = Path::new(&budget.ledger);
    if !path.is_file() {
        bail!(
            "budget ledger {} does not exist (opening it would create it)",
            path.display()
        );
    }
    let wal = format!("{}-wal", path.display());
    if let Ok(meta) = std::fs::metadata(&wal)
        && meta.len() > 0
    {
        bail!(
            "budget ledger {} has a write-ahead log of {} bytes (closing it would checkpoint the log into the ledger)",
            path.display(),
            meta.len()
        );
    }
    let conn = Connection::open_with_flags(path, OpenFlags::SQLITE_OPEN_READ_ONLY)
        .with_context(|| format!("opening budget ledger {} read-only", path.display()))?;
    let mode: String = conn.query_row("PRAGMA journal_mode", [], |r| r.get(0))?;
    if !mode.eq_ignore_ascii_case("wal") {
        bail!(
            "budget ledger {} is in {mode} mode (opening it would switch it to WAL)",
            path.display()
        );
    }
    for table in ["budget", "attempts"] {
        let found: Option<i64> = conn
            .query_row(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?1",
                [table],
                |r| r.get(0),
            )
            .optional()?;
        if found.is_none() {
            bail!(
                "budget ledger {} has no table {table} (opening it would add it)",
                path.display()
            );
        }
    }
    let cap: Option<f64> = conn
        .query_row("SELECT cap_usd FROM budget WHERE id = 1", [], |r| r.get(0))
        .optional()?;
    if cap.is_none() {
        bail!(
            "budget ledger {} has no cap (opening it would store ${})",
            path.display(),
            budget.cap_usd
        );
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::budget::Ledger;
    use std::path::PathBuf;

    fn temp(tag: &str, ext: &str) -> PathBuf {
        let path = std::env::temp_dir().join(format!(
            "jevgammon-admit-{tag}-{}.{ext}",
            std::process::id()
        ));
        for suffix in ["", "-wal", "-shm"] {
            let _ = std::fs::remove_file(format!("{}{suffix}", path.display()));
        }
        path
    }

    fn sha(path: &Path) -> Vec<u8> {
        use sha2::Digest as _;
        sha2::Sha256::digest(std::fs::read(path).unwrap()).to_vec()
    }

    #[tokio::test]
    async fn every_config_player_and_pinned_opponent_is_built_or_refused_read_only() {
        let db = temp("db", "db");
        drop(crate::db::Db::open(&db).unwrap());
        let conn = Connection::open(&db).unwrap();
        for (name, spec) in [
            ("Opp reax", "reax/reax13"),
            ("Opp unknown", "nosuch/model"),
            ("Random", "random"),
        ] {
            let settings = serde_json::to_string(&PlayerConfig::new(name, spec)).unwrap();
            conn.execute(
                "INSERT INTO players (name, spec, settings, created_at) VALUES (?1, ?2, ?3, '2026-11-11T00:00:00Z')",
                rusqlite::params![name, spec, settings],
            )
            .unwrap();
        }
        drop(conn);
        let ledger = temp("ledger", "db");
        let budget = |path: &Path| {
            serde_json::json!({"ledger": path, "cap_usd": 1.25, "input_per_mtok": 0.03,
                               "cached_input_per_mtok": 0.03, "output_per_mtok": 0.0})
        };
        let missing = temp("ledger-missing", "db");
        let pending = temp("ledger-pending", "db");
        let config = temp("config", "json");
        let pin = serde_json::json!({"seed": 1, "seat_first": true});
        std::fs::write(
            &config,
            serde_json::json!({
                "players": [
                    {"name": "Entrant", "spec": "drex-max/drex-max-v1"},
                    {"name": "Budgeted", "spec": "drex-max/drex-max-v1", "budget": budget(&ledger)},
                    {"name": "No ledger", "spec": "drex-max/drex-max-v1", "budget": budget(&missing)},
                    {"name": "Random", "spec": "random"},
                    {"name": "Pending log", "spec": "drex-max/drex-max-v1", "budget": budget(&pending)}
                ],
                "only_pairs_of": "Entrant",
                "pinned_pairs": {"Opp reax": pin, "Opp unknown": pin, "Opp missing": pin, "Random": pin}
            })
            .to_string(),
        )
        .unwrap();
        // An existing ledger as `Ledger::open` leaves it: admitted, and left byte-identical.
        drop(Ledger::open(&serde_json::from_value(budget(&ledger)).unwrap(), "x").unwrap());
        // A ledger with committed pages still in its write-ahead log (a connection holds it).
        drop(Ledger::open(&serde_json::from_value(budget(&pending)).unwrap(), "x").unwrap());
        let holder = Connection::open(&pending).unwrap();
        holder.pragma_update(None, "wal_autocheckpoint", 0).unwrap();
        holder
            .execute(
                "INSERT INTO attempts (setup, pid, started_at, status, reserved_usd) VALUES ('x', 1, 't', 'lost', 0)",
                [],
            )
            .unwrap();
        assert!(
            std::fs::metadata(format!("{}-wal", pending.display()))
                .unwrap()
                .len()
                > 0
        );
        let before = (sha(&db), sha(&ledger), sha(&pending));
        let setup = Setup::new(std::env::temp_dir(), "http://127.0.0.1:9/v1".into());
        let admissions = admit(&db, &config, &setup).await.unwrap();
        let outcome: Vec<(&str, &str, Option<&str>)> = admissions
            .iter()
            .map(|a| (a.name.as_str(), a.source.as_str(), a.refused.as_deref()))
            .collect();
        assert_eq!(outcome.len(), 8, "{outcome:?}");
        assert_eq!(outcome[0], ("Entrant", "league config", None));
        assert_eq!(outcome[1], ("Budgeted", "league config", None));
        assert!(
            outcome[2].2.unwrap().contains("does not exist"),
            "{outcome:?}"
        );
        assert!(!missing.exists());
        assert_eq!(outcome[3], ("Random", "league config", None));
        assert!(
            outcome[4].2.unwrap().contains("write-ahead log"),
            "{outcome:?}"
        );
        // Pinned opponents in name order; Random is the config's, not read again.
        assert_eq!(outcome[5].0, "Opp missing");
        assert_eq!(outcome[5].2, Some("pinned opponent without a players row"));
        assert_eq!(outcome[6].0, "Opp reax");
        assert!(outcome[6].1.starts_with("players #") && outcome[6].2.is_none());
        assert_eq!(outcome[7].0, "Opp unknown");
        assert!(outcome[7].2.unwrap().contains("unknown provider `nosuch`"));
        assert_eq!((sha(&db), sha(&ledger), sha(&pending)), before);
        drop(holder);
        assert!(run(&db, &config, &setup).await.is_err());
    }
}
