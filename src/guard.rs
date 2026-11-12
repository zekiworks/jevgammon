//! A league's run guard (`league --guard FILE`, `admit --guard FILE`; Zeki #5385): the
//! guarantees a repeat claims, bound to the setups it names and kept by the runner itself.
//!
//! - Money: one budget ledger (`budget.rs`) and one cap shared by every `metered` setup (the
//!   entrant and the paid opponents). Each request attempt of theirs (warm-ups, retries and
//!   failed attempts included) first reserves its worst case and is refused before it is sent
//!   when spent + reserved in flight + that would pass the cap; an answered attempt is settled
//!   at max(list price, the provider's reported `usage.cost`), any other keeps its worst case.
//! - Identity: every reply of an `expect_route` setup (warm-ups and each group of a split
//!   decision included) must name exactly the listed model and provider. A missing or other
//!   identity fails closed: the client sends nothing more, the league stops.
//! - Latch: either stop (an identity failure, or a refused reservation) writes the `latch`
//!   file. While it exists, no guarded league starts or resumes, no guarded client sends and
//!   admission refuses: there is no automatic re-entry; only a person removes it.
//!
//! The players' stored settings are not changed: the guard names setups by player name.

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};

use anyhow::{Context as _, Result, bail};
use serde::{Deserialize, Serialize};

use crate::budget::BudgetConfig;
use crate::players::llm::ExpectRoute;

/// List prices of a metered setup, per million tokens (worst cases and list-price settlement).
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Prices {
    pub input_per_mtok: f64,
    pub cached_input_per_mtok: f64,
    pub output_per_mtok: f64,
}

/// The guard file.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct GuardConfig {
    /// Free text: what the guard is for.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub note: Option<String>,
    /// Budget ledger shared by every metered setup.
    pub ledger: String,
    /// Dollars never to be passed by spent + reserved over all metered setups.
    pub cap_usd: f64,
    /// Stop latch file: written on a guard stop; while it exists nothing guarded runs.
    pub latch: PathBuf,
    /// Setups whose every request attempt is metered, by player name.
    pub metered: BTreeMap<String, Prices>,
    /// The identity every reply of these setups must carry, by player name.
    #[serde(default)]
    pub expect_route: BTreeMap<String, ExpectRoute>,
}

pub struct Guard {
    pub config: GuardConfig,
    /// SHA-256 of the guard file's bytes (admission's record).
    pub sha256: String,
    pub path: PathBuf,
    stopped: AtomicBool,
}

/// A guard stop: an identity failure, or the latch already set. Matched by type, so a
/// league can tell it from an ordinary match failure.
#[derive(Debug)]
pub struct GuardStop(pub String);

impl std::fmt::Display for GuardStop {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.0)
    }
}

impl std::error::Error for GuardStop {}

/// Whether `error` is a guard stop or a refused reservation (`budget::BudgetCap`).
pub fn is_stop(error: &anyhow::Error) -> bool {
    error
        .chain()
        .any(|e| e.is::<GuardStop>() || e.is::<crate::budget::BudgetCap>())
}

impl Guard {
    /// Reads and checks the guard file: a positive cap, and every `expect_route` setup metered.
    pub fn load(path: &Path) -> Result<Arc<Self>> {
        let bytes =
            std::fs::read(path).with_context(|| format!("reading guard {}", path.display()))?;
        let config: GuardConfig = serde_json::from_slice(&bytes)
            .with_context(|| format!("parsing guard {}", path.display()))?;
        if !(config.cap_usd.is_finite() && config.cap_usd > 0.0) {
            bail!(
                "guard {}: cap_usd must be a positive number",
                path.display()
            );
        }
        if let Some(name) = config
            .expect_route
            .keys()
            .find(|n| !config.metered.contains_key(*n))
        {
            bail!(
                "guard {}: {name} has an expect_route but is not metered",
                path.display()
            );
        }
        use sha2::Digest as _;
        Ok(Arc::new(Guard {
            config,
            sha256: hex::encode(sha2::Sha256::digest(&bytes)),
            path: path.to_path_buf(),
            stopped: AtomicBool::new(false),
        }))
    }

    pub fn meters(&self, name: &str) -> bool {
        self.config.metered.contains_key(name)
    }

    /// The budget of a metered setup: the shared ledger and cap at its list prices.
    pub fn budget_for(&self, name: &str) -> Option<BudgetConfig> {
        self.config.metered.get(name).map(|p| BudgetConfig {
            ledger: self.config.ledger.clone(),
            cap_usd: self.config.cap_usd,
            input_per_mtok: p.input_per_mtok,
            cached_input_per_mtok: p.cached_input_per_mtok,
            output_per_mtok: p.output_per_mtok,
        })
    }

    pub fn route_for(&self, name: &str) -> Option<ExpectRoute> {
        self.config.expect_route.get(name).cloned()
    }

    /// The latch's text when it is set (in this process, or by the file).
    pub fn latched(&self) -> Option<String> {
        match std::fs::read_to_string(&self.config.latch) {
            Ok(text) => Some(text.trim().to_owned()),
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => self
                .stopped
                .load(Ordering::SeqCst)
                .then(|| "stopped in this process (latch file missing)".to_owned()),
            Err(error) => Some(format!(
                "latch {} unreadable: {error}",
                self.config.latch.display()
            )),
        }
    }

    /// Fails with a `GuardStop` while the latch is set: nothing may be sent or started.
    pub fn check(&self) -> Result<()> {
        match self.latched() {
            None => Ok(()),
            Some(why) => Err(anyhow::Error::new(GuardStop(format!(
                "GUARD LATCHED ({}): {why}; nothing is sent and no guarded league starts until a person removes it",
                self.config.latch.display()
            )))),
        }
    }

    /// Sets the latch: in this process at once, and in the latch file (one line appended per
    /// stop), which keeps every later run from starting.
    pub fn latch(&self, reason: &str) {
        self.stopped.store(true, Ordering::SeqCst);
        let line = format!(
            "{} {reason}\n",
            chrono::Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Millis, true)
        );
        use std::io::Write as _;
        let written = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.config.latch)
            .and_then(|mut f| f.write_all(line.as_bytes()));
        if let Err(error) = written {
            eprintln!(
                "guard: latch {} not written: {error} (latched in this process)",
                self.config.latch.display()
            );
        }
    }
}
