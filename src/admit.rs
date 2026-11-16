//! `jevgammon admit`: offline client admission before a league writes anything (ported from
//! 959a8a2 without its pinned_pairs opponents, which this tree has not). Every player of a
//! league config gets its client built by `Player::for_admission`: the construction
//! `Player::from_config` (the call a league makes for each participant) does, restricted to
//! decision services, the local engines and chat servers on a loopback address (any other
//! client type, e.g. a subscription login that could refresh a token, is refused before
//! anything is constructed) and with every budget ledger opened read-only and immutable. No
//! request is sent: no database, ledger or credential file is written, created or locked
//! (gnubg-weak, as in a league, starts gnubg from a temporary directory it removes).
//!
//! Under a guard (`--guard`) its latch must not be set, its metered setups are built with its
//! ledger and every other player must run locally (`Player::build`): an unexpected paid
//! participant is refused. A successful admission ends with one line, `admitted-settings
//! {json}`: the SHA-256 of the config file read and, under a guard, of the guard file.

use std::path::Path;

use anyhow::{Context, Result, bail};

use crate::league::LeagueConfig;
use crate::players::{Player, Setup};

/// One player's admission: its name, spec, and why its client was refused (`None`: built).
#[derive(Debug)]
pub struct Admission {
    pub name: String,
    pub spec: String,
    pub refused: Option<String>,
}

/// One admission run: the SHA-256 of the config file read and every client's admission.
#[derive(Debug)]
pub struct Admitted {
    pub config_sha256: String,
    pub clients: Vec<Admission>,
}

/// Prints one line per player and fails when any client was refused; else ends with the
/// `admitted-settings` record.
pub async fn run(config: &Path, setup: &Setup) -> Result<()> {
    if let Some(guard) = &setup.guard {
        guard.check()?;
    }
    let admitted = admit(config, setup).await?;
    for a in &admitted.clients {
        match &a.refused {
            None => println!("ok       {} ({}): client built", a.name, a.spec),
            Some(why) => println!("REFUSED  {} ({}): {why}", a.name, a.spec),
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
        "admitted: all {} clients of {} built",
        admitted.clients.len(),
        config.display()
    );
    println!(
        "admitted-settings {}",
        record(config, &admitted, setup.guard.as_deref())
    );
    Ok(())
}

/// The `admitted-settings` record (one line of JSON): the config file and its SHA-256, the
/// clients in admission order and, under a guard, the guard file and its SHA-256.
fn record(
    config: &Path,
    admitted: &Admitted,
    guard: Option<&crate::guard::Guard>,
) -> serde_json::Value {
    let clients: Vec<_> = admitted.clients.iter().map(|a| a.name.clone()).collect();
    let mut record = serde_json::json!({"config": config.display().to_string(),
                                        "config_sha256": admitted.config_sha256, "clients": clients});
    if let Some(guard) = guard {
        record["guard"] =
            serde_json::json!({"path": guard.path.display().to_string(), "sha256": guard.sha256});
    }
    record
}

/// Every player of the config, in its order.
pub async fn admit(config: &Path, setup: &Setup) -> Result<Admitted> {
    // Parsed from the bytes whose SHA-256 is recorded (as `LeagueConfig::load` parses them).
    let text =
        std::fs::read_to_string(config).with_context(|| format!("reading {}", config.display()))?;
    let league: LeagueConfig =
        serde_json::from_str(&text).with_context(|| format!("parsing {}", config.display()))?;
    let mut clients = Vec::new();
    for player in &league.players {
        clients.push(Admission {
            name: player.name.clone(),
            spec: player.spec.clone(),
            refused: Player::for_admission(player, setup)
                .await
                .err()
                .map(|e| format!("{e:#}")),
        });
    }
    use sha2::Digest as _;
    Ok(Admitted {
        config_sha256: hex::encode(sha2::Sha256::digest(text.as_bytes())),
        clients,
    })
}
