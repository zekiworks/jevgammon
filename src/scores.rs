//! Error rates for the league tiebreak, from the site's GNUbg scores.
//!
//! The site update loop (`tools/site/update.sh`) scores every legal play of every league
//! decision at 2-ply with GNUbg 1.08 (`tools/site/score_plays.py`) into 32 shard databases,
//! `<state>/bg-site/plays/s{0..31}.db`, table `plays (turn_id, loss, ...)`. The error rate of a
//! setup is the site's (brief B11): 500 × the mean equity loss of its decisions with two or
//! more legal plays, invalid answers (`decided_by = 'fallback'`) left out, over all of its
//! valid matches (every league, ladder round and Cup, legacy playoffs included). Decisions
//! not scored yet are counted, so a caller can tell a complete error rate from a partial one.

use std::collections::HashMap;
use std::path::{Path, PathBuf};

use anyhow::{Context, Result};
use rusqlite::{Connection, OpenFlags};

use crate::db::Db;

/// Error rate = `SCALE` × mean equity loss (site thresholds `equity_scale`).
pub const SCALE: f64 = 500.0;

/// One setup's error rate over all of its valid matches.
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub struct ErrorRate {
    /// Sum of the equity losses of the scored decisions.
    pub loss: f64,
    /// Scored decisions.
    pub scored: u64,
    /// Decisions GNUbg could not score (`skipped`, e.g. a stored move it cannot replay).
    pub skipped: u64,
    /// Decisions not scored yet.
    pub pending: u64,
}

impl ErrorRate {
    /// `SCALE` × mean loss; `None` without scored decisions.
    pub fn rate(&self) -> Option<f64> {
        (self.scored > 0).then(|| SCALE * self.loss / self.scored as f64)
    }
}

/// The site update loop's shard directory: `$XDG_STATE_HOME/bg-site/plays`, else
/// `~/.local/state/bg-site/plays`.
pub fn default_dir() -> PathBuf {
    dirs::state_dir()
        .unwrap_or_else(|| dirs::home_dir().unwrap_or_default().join(".local/state"))
        .join("bg-site/plays")
}

/// Every player's error rate by name, from the shards in `dir`.
pub fn error_rates(db: &Db, dir: &Path) -> Result<HashMap<String, ErrorRate>> {
    let mut loss: HashMap<i64, f64> = HashMap::new();
    let mut skipped: std::collections::HashSet<i64> = std::collections::HashSet::new();
    let mut shards = 0;
    for entry in std::fs::read_dir(dir).with_context(|| format!("reading {}", dir.display()))? {
        let path = entry?.path();
        let name = path.file_name().and_then(|n| n.to_str()).unwrap_or("");
        if !(name.starts_with('s') && name.ends_with(".db")) {
            continue;
        }
        let shard = Connection::open_with_flags(&path, OpenFlags::SQLITE_OPEN_READ_ONLY)
            .with_context(|| format!("opening {}", path.display()))?;
        shards += 1;
        let mut statement = shard.prepare("SELECT turn_id, loss FROM plays")?;
        for row in statement.query_map([], |r| Ok((r.get(0)?, r.get(1)?)))? {
            let (turn, value): (i64, f64) = row?;
            loss.insert(turn, value);
        }
        let mut statement = shard.prepare("SELECT turn_id FROM skipped")?;
        for turn in statement.query_map([], |r| r.get(0))? {
            skipped.insert(turn?);
        }
    }
    anyhow::ensure!(shards > 0, "no score shards (s*.db) in {}", dir.display());
    let mut statement = db.conn().prepare(
        "SELECT t.id, p.name FROM turns t
         JOIN games g ON g.id = t.game_id
         JOIN matches m ON m.id = g.match_id
         JOIN players p ON p.id = CASE t.player WHEN 1 THEN m.player1 ELSE m.player2 END
         WHERE m.valid = 1 AND m.stage IS NOT NULL
           AND t.decided_by = 'model' AND t.legal_count >= 2",
    )?;
    let mut rates: HashMap<String, ErrorRate> = HashMap::new();
    for row in statement.query_map([], |r| Ok((r.get::<_, i64>(0)?, r.get::<_, String>(1)?)))? {
        let (turn, name) = row?;
        let rate = rates.entry(name).or_default();
        match loss.get(&turn) {
            Some(value) => {
                rate.loss += value;
                rate.scored += 1;
            }
            None if skipped.contains(&turn) => rate.skipped += 1,
            None => rate.pending += 1,
        }
    }
    Ok(rates)
}
