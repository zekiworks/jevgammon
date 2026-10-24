//! Hard spending cap shared by every process that uses one ledger (a SQLite file): each
//! request attempt first reserves its worst-case cost, and is refused when the money already
//! spent plus the open reservations plus the new one would pass the cap. A finished attempt
//! replaces its reservation with its cost; an attempt whose cost is unknown (no response:
//! network error, timeout, a cancelled decision, a crash) keeps its worst case as spent.
//!
//! Costs are at the configured list prices: uncached input, cached input and output
//! (reasoning included) tokens, each counted once. When the provider also reports a cost,
//! the larger of the two is booked.

use std::path::PathBuf;
use std::sync::Arc;

use anyhow::{Context as _, Result, bail};
use parking_lot::Mutex;
use rusqlite::{Connection, OptionalExtension as _, TransactionBehavior, params};
use serde::{Deserialize, Serialize};

/// A player's cap, from its config (`budget`).
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub struct BudgetConfig {
    /// Ledger file; every setup naming the same file shares the cap.
    pub ledger: String,
    /// Dollars, never to be passed by spent + reserved.
    pub cap_usd: f64,
    /// List prices per million tokens.
    pub input_per_mtok: f64,
    pub cached_input_per_mtok: f64,
    pub output_per_mtok: f64,
}

/// Token counts of one answered attempt.
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub struct Usage {
    /// All prompt tokens, cached ones included.
    pub input_tokens: u64,
    pub cached_tokens: u64,
    /// All completion tokens, reasoning included.
    pub output_tokens: u64,
    pub reasoning_tokens: u64,
}

pub struct Ledger {
    config: BudgetConfig,
    setup: String,
    conn: Mutex<Connection>,
}

const SCHEMA: &str = "
CREATE TABLE IF NOT EXISTS budget (
    id      INTEGER PRIMARY KEY CHECK (id = 1),
    cap_usd REAL NOT NULL
);
-- One row per request attempt. status: open (in flight, counted at reserved_usd),
-- settled (answered, counted at cost_usd), lost (no response, counted at reserved_usd).
CREATE TABLE IF NOT EXISTS attempts (
    id                INTEGER PRIMARY KEY,
    setup             TEXT NOT NULL,
    pid               INTEGER NOT NULL,
    started_at        TEXT NOT NULL,
    finished_at       TEXT,
    status            TEXT NOT NULL,
    reserved_usd      REAL NOT NULL,
    cost_usd          REAL,
    list_cost_usd     REAL,
    reported_cost_usd REAL,
    input_tokens      INTEGER,
    cached_tokens     INTEGER,
    output_tokens     INTEGER,
    reasoning_tokens  INTEGER,
    note              TEXT
);
";

fn now() -> String {
    chrono::Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Millis, true)
}

/// Spent (settled + lost) and reserved (open) dollars.
fn totals(conn: &Connection) -> Result<(f64, f64)> {
    Ok(conn.query_row(
        "SELECT COALESCE(SUM(CASE status WHEN 'settled' THEN cost_usd
                                         WHEN 'lost' THEN reserved_usd END), 0),
                COALESCE(SUM(CASE status WHEN 'open' THEN reserved_usd END), 0)
         FROM attempts",
        [],
        |row| Ok((row.get(0)?, row.get(1)?)),
    )?)
}

impl Ledger {
    /// Opens (creating) the ledger. The cap is stored on first use; a config naming a
    /// different cap for the same ledger is refused.
    pub fn open(config: &BudgetConfig, setup: &str) -> Result<Arc<Self>> {
        let path = PathBuf::from(&config.ledger);
        let conn = Connection::open(&path)
            .with_context(|| format!("opening budget ledger {}", path.display()))?;
        conn.busy_timeout(std::time::Duration::from_secs(30))?;
        conn.pragma_update(None, "journal_mode", "WAL")?;
        conn.execute_batch(SCHEMA)?;
        let stored: Option<f64> = conn
            .query_row("SELECT cap_usd FROM budget WHERE id = 1", [], |r| r.get(0))
            .optional()?;
        match stored {
            None => {
                conn.execute(
                    "INSERT INTO budget (id, cap_usd) VALUES (1, ?1)",
                    [config.cap_usd],
                )?;
            }
            Some(cap) if cap != config.cap_usd => bail!(
                "budget ledger {} has cap ${cap}, the config says ${}",
                path.display(),
                config.cap_usd
            ),
            Some(_) => {}
        }
        Ok(Arc::new(Ledger {
            config: config.clone(),
            setup: setup.to_owned(),
            conn: Mutex::new(conn),
        }))
    }

    /// Worst case of one attempt: every byte of the request body an uncached input token
    /// (a token is never shorter than one byte) and the whole output allowance used.
    pub fn worst_case(&self, body_bytes: usize, max_output_tokens: u64) -> f64 {
        (body_bytes as f64 * self.config.input_per_mtok
            + max_output_tokens as f64 * self.config.output_per_mtok)
            / 1e6
    }

    /// List-price cost of an answered attempt; cached tokens are part of `input_tokens`.
    pub fn list_cost(&self, usage: &Usage) -> f64 {
        let cached = usage.cached_tokens.min(usage.input_tokens);
        ((usage.input_tokens - cached) as f64 * self.config.input_per_mtok
            + cached as f64 * self.config.cached_input_per_mtok
            + usage.output_tokens as f64 * self.config.output_per_mtok)
            / 1e6
    }

    /// Reserves `amount` for one attempt, or refuses it (an error naming the cap) when
    /// spent + reserved + amount would pass the cap.
    pub fn reserve(self: &Arc<Self>, amount: f64) -> Result<Hold> {
        let mut conn = self.conn.lock();
        let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
        let (spent, reserved) = totals(&tx)?;
        let cap = self.config.cap_usd;
        if spent + reserved + amount > cap {
            bail!(
                "BUDGET CAP: ${spent:.4} spent + ${reserved:.4} reserved in flight + \
                 ${amount:.4} for this request would pass the ${cap:.2} hard cap \
                 (ledger {}); stopped before the call",
                self.config.ledger
            );
        }
        tx.execute(
            "INSERT INTO attempts (setup, pid, started_at, status, reserved_usd)
             VALUES (?1, ?2, ?3, 'open', ?4)",
            params![self.setup, std::process::id(), now(), amount],
        )?;
        let id = tx.last_insert_rowid();
        tx.commit()?;
        Ok(Hold {
            ledger: Arc::clone(self),
            id,
            done: false,
        })
    }

    fn finish(
        &self,
        id: i64,
        status: &str,
        cost: Option<(f64, f64, Option<f64>, Usage)>,
        note: &str,
    ) {
        let conn = self.conn.lock();
        let result = match cost {
            Some((cost, list, reported, usage)) => conn.execute(
                "UPDATE attempts SET status = ?2, finished_at = ?3, cost_usd = ?4,
                     list_cost_usd = ?5, reported_cost_usd = ?6, input_tokens = ?7,
                     cached_tokens = ?8, output_tokens = ?9, reasoning_tokens = ?10, note = ?11
                 WHERE id = ?1",
                params![
                    id,
                    status,
                    now(),
                    cost,
                    list,
                    reported,
                    usage.input_tokens as i64,
                    usage.cached_tokens as i64,
                    usage.output_tokens as i64,
                    usage.reasoning_tokens as i64,
                    note
                ],
            ),
            None => conn.execute(
                "UPDATE attempts SET status = ?2, finished_at = ?3, cost_usd = ?4, note = ?5
                 WHERE id = ?1",
                params![
                    id,
                    status,
                    now(),
                    if status == "settled" { Some(0.0) } else { None },
                    note
                ],
            ),
        };
        if let Err(error) = result {
            // The row stays open, so it keeps counting at its worst case.
            eprintln!("budget ledger: attempt {id} not updated: {error:#}");
        }
    }
}

/// One attempt's reservation. Dropped without `settle`/`refused`, it is booked at its
/// worst case (`lost`).
pub struct Hold {
    ledger: Arc<Ledger>,
    id: i64,
    done: bool,
}

impl std::fmt::Debug for Hold {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "Hold({})", self.id)
    }
}

impl Hold {
    /// Books an answered attempt at max(list-price cost, provider-reported cost).
    pub fn settle(mut self, usage: Usage, reported: Option<f64>) -> f64 {
        let list = self.ledger.list_cost(&usage);
        let cost = reported.map_or(list, |r| r.max(list));
        self.ledger
            .finish(self.id, "settled", Some((cost, list, reported, usage)), "");
        self.done = true;
        cost
    }

    /// The provider answered with an error status (nothing generated, nothing billed).
    pub fn refused(mut self, note: &str) {
        self.ledger.finish(self.id, "settled", None, note);
        self.done = true;
    }
}

impl Drop for Hold {
    fn drop(&mut self) {
        if !self.done {
            self.ledger.finish(
                self.id,
                "lost",
                None,
                "no response: booked at the worst case",
            );
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::Path;

    fn config(path: &Path, cap: f64) -> BudgetConfig {
        BudgetConfig {
            ledger: path.to_string_lossy().into_owned(),
            cap_usd: cap,
            input_per_mtok: 2.0,
            cached_input_per_mtok: 0.2,
            output_per_mtok: 10.0,
        }
    }

    #[test]
    fn reservations_settlements_and_losses_respect_the_cap() {
        let dir = std::env::temp_dir().join(format!("budget-{}", uuid::Uuid::new_v4()));
        std::fs::create_dir_all(&dir).unwrap();
        let path = dir.join("ledger.db");
        let ledger = Ledger::open(&config(&path, 1.0), "a").unwrap();
        let one = ledger.reserve(0.6).unwrap();
        // 0.6 in flight: another 0.6 would pass the cap.
        assert!(ledger.reserve(0.6).is_err());
        // Answered: 1,000 input (400 cached), 1,000 output = 0.0012 + 0.00008 + 0.01.
        let usage = Usage {
            input_tokens: 1000,
            cached_tokens: 400,
            output_tokens: 1000,
            reasoning_tokens: 900,
        };
        let cost = one.settle(usage, Some(0.005));
        assert!((cost - 0.01128).abs() < 1e-9);
        // A second process sees the same ledger.
        let other = Ledger::open(&config(&path, 1.0), "b").unwrap();
        let lost = other.reserve(0.5).unwrap();
        drop(lost); // no response: booked at 0.5
        let refused = other.reserve(0.4).unwrap();
        refused.refused("429");
        let (spent, reserved) = totals(&other.conn.lock()).unwrap();
        assert!((spent - 0.51128).abs() < 1e-9 && reserved == 0.0);
        assert!(other.reserve(0.49).is_err());
        assert!(other.reserve(0.48).is_ok());
        // Another cap for the same ledger is refused.
        assert!(Ledger::open(&config(&path, 2.0), "c").is_err());
    }
}
