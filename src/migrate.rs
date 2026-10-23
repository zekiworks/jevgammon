//! `jevgammon migrate`: from the old league layout (rosters in `leagues.models`, fixtures in
//! `league_matches`) to players, league participants and `matches.valid`.
//!
//! - Every name of a roster, of a fixture, or of the freeze logs becomes a `players` row:
//!   the current roster entry's settings, else the latest `league-add` entry of the
//!   additions log, else `{name, spec}` with the spec its matches were played with.
//! - Each league's current roster becomes current participants in entry order (joined at
//!   the league start, or when the additions log added them); players of its fixtures or
//!   freeze logs no longer on the roster become participants who left (`left_at` and the
//!   reason from the changes log, when recorded).
//! - A match linked by a fixture keeps counting (`valid` 1; a stale playoff's 0) and gets its
//!   players, stage, label and the league's `mirror_concurrent`. A match no fixture links
//!   is found by its seed (`derive_seed(league seed, label)` of a fixture or of a label in
//!   the freeze logs) and voided with why: voided in the changes log, its fixture removed
//!   with a player, or a replaced attempt. A match no fixture explains stays as it is (a
//!   single match outside leagues).
//! - `league_matches` is kept as `legacy_league_matches`, `leagues.models` as
//!   `legacy_league_rosters`.
//!
//! Then every league's table is computed the old way (legacy roster and fixtures) and the
//! new way (`league::standings`) and compared; any difference rolls the migration back.
//! One transaction; `--dry-run` always rolls back. Running it again on a migrated database
//! only compares.

use std::collections::{BTreeMap, HashMap, HashSet};
use std::path::{Path, PathBuf};

use anyhow::{Context, Result, bail};
use clap::Args;
use rusqlite::{Connection, OptionalExtension, params};
use serde_json::Value;

use crate::db::{self, Db};
use crate::dice::derive_seed;
use crate::league::{self, Standing};
use crate::players::PlayerConfig;

#[derive(Args)]
pub struct MigrateArgs {
    /// SQLite database to convert (back it up first).
    #[arg(long)]
    pub db: PathBuf,
    /// Convert inside a transaction, print the comparison, and roll back.
    #[arg(long)]
    pub dry_run: bool,
    /// Freeze logs (league<ID>-additions.json, league<ID>-changes.json): join times,
    /// departures, voided matches. Entries for other database files are ignored.
    #[arg(long, default_value = "freeze")]
    pub freeze: PathBuf,
    /// Database file name the freeze entries name (`"db"`); default: the --db file's name.
    /// For a copy, e.g. `--freeze-db v3.db`.
    #[arg(long)]
    pub freeze_db: Option<String>,
}

pub fn run(args: &MigrateArgs) -> Result<()> {
    let db = Db::open_raw(&args.db)?;
    let conn = db.conn();
    if !db::legacy_layout(conn)? {
        if !table_exists(conn, "legacy_league_matches")? {
            println!(
                "{}: nothing to migrate (no old league layout)",
                args.db.display()
            );
            return Ok(());
        }
        println!(
            "{}: already migrated; comparing the tables again",
            args.db.display()
        );
        let differences = compare(&db)?;
        if differences > 0 {
            bail!("{differences} table lines differ between the old and the new layout");
        }
        return Ok(());
    }
    let file = match &args.freeze_db {
        Some(name) => name.clone(),
        None => args
            .db
            .file_name()
            .map(|f| f.to_string_lossy().into_owned())
            .unwrap_or_default(),
    };
    let history = History::load(&args.freeze, &file)?;
    conn.execute_batch("BEGIN IMMEDIATE")?;
    let outcome = migrate(conn, &history).and_then(|summary| {
        println!("{summary}");
        compare(&db)
    });
    match outcome {
        Ok(0) if !args.dry_run => {
            conn.execute_batch("COMMIT")?;
            println!("migrated {}", args.db.display());
            Ok(())
        }
        Ok(0) => {
            conn.execute_batch("ROLLBACK")?;
            println!("dry run: rolled back, {} unchanged", args.db.display());
            Ok(())
        }
        Ok(differences) => {
            conn.execute_batch("ROLLBACK")?;
            bail!(
                "{differences} table lines differ between the old and the new layout; rolled back"
            )
        }
        Err(error) => {
            conn.execute_batch("ROLLBACK")?;
            Err(error.context("migration failed; rolled back"))
        }
    }
}

fn table_exists(conn: &Connection, name: &str) -> Result<bool> {
    Ok(conn.query_row(
        "SELECT COUNT(*) > 0 FROM sqlite_master WHERE type = 'table' AND name = ?1",
        params![name],
        |row| row.get(0),
    )?)
}

/// A `league-add` entry of the additions log.
struct Joined {
    league: i64,
    at: String,
    name: String,
    entry: Option<PlayerConfig>,
    fixtures: Vec<String>,
}

/// An entry of the changes log.
struct Change {
    league: i64,
    at: String,
    what: String,
    /// `(name, reason)`.
    removed: Vec<(String, String)>,
    removed_fixtures: Vec<String>,
    /// `(match id, fixture label, voided for)`.
    voided: Vec<(i64, String, String)>,
}

/// The freeze logs of one database.
#[derive(Default)]
struct History {
    joined: Vec<Joined>,
    changes: Vec<Change>,
}

impl History {
    /// Every `league*-additions.json` and `league*-changes.json` in `dir` whose entries name
    /// the database file `file` (entries without `db` are taken too).
    fn load(dir: &Path, file: &str) -> Result<Self> {
        let mut history = History::default();
        let Ok(entries) = std::fs::read_dir(dir) else {
            println!(
                "no freeze logs in {} (join times and reasons unknown)",
                dir.display()
            );
            return Ok(history);
        };
        let file = Some(file.to_owned());
        let mut paths: Vec<PathBuf> = entries.filter_map(|e| Some(e.ok()?.path())).collect();
        paths.sort();
        for path in paths {
            let name = path.file_name().unwrap_or_default().to_string_lossy();
            let kind = if name.ends_with("-additions.json") {
                "additions"
            } else if name.ends_with("-changes.json") {
                "changes"
            } else {
                continue;
            };
            let text = std::fs::read_to_string(&path)?;
            let items: Vec<Value> = serde_json::from_str(&text)
                .with_context(|| format!("parsing {}", path.display()))?;
            for item in items {
                let same_db = item["db"].as_str().is_none_or(|d| {
                    Path::new(d)
                        .file_name()
                        .map(|f| f.to_string_lossy().into_owned())
                        == file
                });
                let Some(league) = item["league"].as_i64() else {
                    continue;
                };
                if !same_db {
                    continue;
                }
                let strings = |key: &str| -> Vec<String> {
                    item[key]
                        .as_array()
                        .into_iter()
                        .flatten()
                        .filter_map(|v| v.as_str().map(str::to_owned))
                        .collect()
                };
                if kind == "additions" {
                    history.joined.push(Joined {
                        league,
                        at: item["added_at"].as_str().unwrap_or_default().to_owned(),
                        name: item["name"].as_str().unwrap_or_default().to_owned(),
                        entry: serde_json::from_value(item["entry"].clone()).ok(),
                        fixtures: strings("fixtures"),
                    });
                } else {
                    let pairs = |key: &str, a: &str, b: &str| -> Vec<(String, String)> {
                        item[key]
                            .as_array()
                            .into_iter()
                            .flatten()
                            .map(|v| {
                                (
                                    v[a].as_str().unwrap_or_default().to_owned(),
                                    v[b].as_str().unwrap_or_default().to_owned(),
                                )
                            })
                            .collect()
                    };
                    history.changes.push(Change {
                        league,
                        at: item["changed_at"].as_str().unwrap_or_default().to_owned(),
                        what: item["change"].as_str().unwrap_or_default().to_owned(),
                        removed: pairs("removed", "name", "reason"),
                        removed_fixtures: strings("removed_fixtures"),
                        voided: item["voided"]
                            .as_array()
                            .into_iter()
                            .flatten()
                            .filter_map(|v| {
                                Some((
                                    v["match_id"].as_i64()?,
                                    v["fixture"].as_str().unwrap_or_default().to_owned(),
                                    v["voided_for"].as_str().unwrap_or_default().to_owned(),
                                ))
                            })
                            .collect(),
                    });
                }
            }
        }
        Ok(history)
    }
}

struct LegacyLeague {
    id: i64,
    started_at: String,
    seed: u64,
    mirror: bool,
    roster: Vec<PlayerConfig>,
}

struct LegacyFixture {
    league: i64,
    stage: String,
    label: String,
    model1: String,
    model2: String,
    seed: u64,
    match_id: Option<i64>,
    error: Option<String>,
    failed_at: Option<String>,
}

/// What a match belongs to: league, stage, label and the two names.
#[derive(Clone)]
struct Origin {
    league: i64,
    stage: String,
    label: String,
    model1: String,
    model2: String,
}

/// `matchday N: A v B` (or any `prefix: A v B`) with both names known.
fn parse_label(label: &str, known: &HashSet<String>) -> Option<(String, String)> {
    let (_, pair) = label.split_once(": ")?;
    pair.match_indices(" v ").find_map(|(at, _)| {
        let (a, b) = (&pair[..at], &pair[at + 3..]);
        (known.contains(a) && known.contains(b)).then(|| (a.to_owned(), b.to_owned()))
    })
}

fn migrate(conn: &Connection, history: &History) -> Result<String> {
    db::ensure_schema(conn)?;
    // A database from before fixtures were stored has none to migrate.
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS league_matches (id INTEGER PRIMARY KEY,
             league_id INTEGER NOT NULL, stage TEXT NOT NULL, label TEXT NOT NULL,
             matchday INTEGER, model1 TEXT NOT NULL, model2 TEXT NOT NULL,
             seed INTEGER NOT NULL, match_id INTEGER)",
    )?;
    let leagues: Vec<LegacyLeague> = {
        let mut statement = conn.prepare(
            "SELECT id, started_at, seed, mirror_concurrent, models FROM leagues ORDER BY id",
        )?;
        let rows = statement
            .query_map([], |row| {
                Ok((
                    row.get::<_, i64>(0)?,
                    row.get::<_, String>(1)?,
                    row.get::<_, i64>(2)?,
                    row.get::<_, Option<bool>>(3)?,
                    row.get::<_, String>(4)?,
                ))
            })?
            .collect::<rusqlite::Result<Vec<_>>>()?;
        rows.into_iter()
            .map(|(id, started_at, seed, mirror, models)| {
                Ok(LegacyLeague {
                    id,
                    started_at,
                    seed: seed as u64,
                    mirror: mirror.unwrap_or(false),
                    roster: serde_json::from_str(&models)
                        .with_context(|| format!("league #{id}: models"))?,
                })
            })
            .collect::<Result<_>>()?
    };
    let fixtures: Vec<LegacyFixture> = if table_exists(conn, "league_matches")? {
        let deferred = if has_column(conn, "league_matches", "error")? {
            "error, failed_at"
        } else {
            "NULL, NULL"
        };
        let mut statement = conn.prepare(&format!(
            "SELECT league_id, stage, label, model1, model2, seed, match_id, {deferred}
             FROM league_matches ORDER BY id"
        ))?;
        statement
            .query_map([], |row| {
                Ok(LegacyFixture {
                    league: row.get(0)?,
                    stage: row.get(1)?,
                    label: row.get(2)?,
                    model1: row.get(3)?,
                    model2: row.get(4)?,
                    seed: row.get::<_, i64>(5)? as u64,
                    match_id: row.get(6)?,
                    error: row.get(7)?,
                    failed_at: row.get(8)?,
                })
            })?
            .collect::<rusqlite::Result<_>>()?
    } else {
        Vec::new()
    };
    let league_of: HashMap<i64, &LegacyLeague> = leagues.iter().map(|l| (l.id, l)).collect();

    // Every name the records know.
    let mut known: HashSet<String> = HashSet::new();
    for league in &leagues {
        known.extend(league.roster.iter().map(|c| c.name.clone()));
    }
    for fixture in &fixtures {
        known.insert(fixture.model1.clone());
        known.insert(fixture.model2.clone());
    }
    for joined in &history.joined {
        known.insert(joined.name.clone());
    }
    for change in &history.changes {
        known.extend(change.removed.iter().map(|(name, _)| name.clone()));
    }
    known.remove("");

    // What each match belongs to: its fixture, else a fixture or a freeze label with its
    // seed.
    let mut linked: HashMap<i64, &LegacyFixture> = HashMap::new();
    for fixture in &fixtures {
        if let Some(id) = fixture.match_id
            && let Some(other) = linked.insert(id, fixture)
        {
            bail!(
                "match #{id} is linked by two fixtures: `{}` (league #{}) and `{}` (league #{})",
                other.label,
                other.league,
                fixture.label,
                fixture.league
            );
        }
    }
    let mut by_seed: HashMap<u64, Origin> = HashMap::new();
    for fixture in &fixtures {
        by_seed.entry(fixture.seed).or_insert_with(|| Origin {
            league: fixture.league,
            stage: fixture.stage.clone(),
            label: fixture.label.clone(),
            model1: fixture.model1.clone(),
            model2: fixture.model2.clone(),
        });
    }
    let freeze_labels = history
        .joined
        .iter()
        .flat_map(|j| j.fixtures.iter().map(move |label| (j.league, label)))
        .chain(history.changes.iter().flat_map(|c| {
            c.removed_fixtures
                .iter()
                .chain(c.voided.iter().map(|v| &v.1))
                .map(move |label| (c.league, label))
        }));
    for (league, label) in freeze_labels {
        let (Some(row), Some((model1, model2))) =
            (league_of.get(&league), parse_label(label, &known))
        else {
            continue;
        };
        by_seed
            .entry(derive_seed(row.seed, label))
            .or_insert_with(|| Origin {
                league,
                stage: "league".into(),
                label: label.clone(),
                model1,
                model2,
            });
    }
    type MatchLine = (i64, u64, String, String, String);
    let matches: Vec<MatchLine> = {
        let mut statement =
            conn.prepare("SELECT id, seed, model1, model2, started_at FROM matches ORDER BY id")?;
        statement
            .query_map([], |row| {
                Ok((
                    row.get(0)?,
                    row.get::<_, i64>(1)? as u64,
                    row.get(2)?,
                    row.get(3)?,
                    row.get(4)?,
                ))
            })?
            .collect::<rusqlite::Result<_>>()?
    };
    let origin_of = |id: i64, seed: u64| -> Option<Origin> {
        match linked.get(&id) {
            Some(f) => Some(Origin {
                league: f.league,
                stage: f.stage.clone(),
                label: f.label.clone(),
                model1: f.model1.clone(),
                model2: f.model2.clone(),
            }),
            None => by_seed.get(&seed).cloned(),
        }
    };

    // Players: current roster entries, else the latest additions entry, else the spec of
    // their matches.
    let mut settings: BTreeMap<String, (PlayerConfig, &'static str)> = BTreeMap::new();
    for league in &leagues {
        for config in &league.roster {
            if let Some((other, _)) = settings.get(&config.name)
                && other != config
            {
                bail!(
                    "`{}` is on two rosters with different settings; rename one before migrating",
                    config.name
                );
            }
            settings.insert(config.name.clone(), (config.clone(), "roster"));
        }
    }
    let mut joined_sorted: Vec<&Joined> = history.joined.iter().collect();
    joined_sorted.sort_by(|a, b| a.at.cmp(&b.at));
    for joined in &joined_sorted {
        if let Some(entry) = &joined.entry
            && entry.name == joined.name
            && settings.get(&joined.name).is_none_or(|s| s.1 != "roster")
        {
            settings.insert(joined.name.clone(), (entry.clone(), "additions log"));
        }
    }
    let mut first_seen: HashMap<String, String> = HashMap::new();
    for (id, seed, spec1, spec2, started_at) in &matches {
        if let Some(origin) = origin_of(*id, *seed) {
            for (name, spec) in [(&origin.model1, spec1), (&origin.model2, spec2)] {
                first_seen
                    .entry(name.clone())
                    .or_insert_with(|| started_at.clone());
                settings.entry(name.clone()).or_insert_with(|| {
                    let mut config = PlayerConfig::new(name, spec);
                    config.note = Some(
                        "settings not recorded; spec from its matches (jevgammon migrate)".into(),
                    );
                    (config, "matches")
                });
            }
        }
    }
    let mut ids: HashMap<String, i64> = HashMap::new();
    let mut counts: BTreeMap<&str, usize> = BTreeMap::new();
    for name in &known {
        let Some((config, source)) = settings.get(name) else {
            bail!("no settings and no match for `{name}`; add it to a freeze log or roster");
        };
        let created = first_seen
            .get(name)
            .cloned()
            .or_else(|| leagues.first().map(|l| l.started_at.clone()))
            .unwrap_or_default();
        ids.insert(name.clone(), db::insert_player(conn, config, &created)?);
        *counts.entry(source).or_default() += 1;
    }
    let mut summary = format!(
        "players: {} ({})",
        ids.len(),
        counts
            .iter()
            .map(|(source, n)| format!("{n} from {source}"))
            .collect::<Vec<_>>()
            .join(", ")
    );

    // Participants: the roster, then those who left.
    let mut departed: HashMap<(i64, String), String> = HashMap::new();
    for league in &leagues {
        let joined_at = |name: &str, before: Option<&str>| -> String {
            joined_sorted
                .iter()
                .rev()
                .find(|j| {
                    j.league == league.id
                        && j.name == name
                        && before.is_none_or(|b| j.at.as_str() <= b)
                })
                .map_or(league.started_at.clone(), |j| j.at.clone())
        };
        let roster: HashSet<&str> = league.roster.iter().map(|c| c.name.as_str()).collect();
        for config in &league.roster {
            conn.execute(
                "INSERT INTO league_players (league_id, player_id, joined_at) VALUES (?1, ?2, ?3)",
                params![league.id, ids[&config.name], joined_at(&config.name, None)],
            )?;
        }
        let mut gone: Vec<String> = Vec::new();
        let mut note_gone = |name: &String| {
            if !roster.contains(name.as_str()) && !gone.contains(name) {
                gone.push(name.clone());
            }
        };
        for fixture in fixtures.iter().filter(|f| f.league == league.id) {
            note_gone(&fixture.model1);
            note_gone(&fixture.model2);
        }
        for joined in history.joined.iter().filter(|j| j.league == league.id) {
            note_gone(&joined.name);
        }
        for change in history.changes.iter().filter(|c| c.league == league.id) {
            for (name, _) in &change.removed {
                note_gone(name);
            }
        }
        for (id, seed, ..) in &matches {
            if let Some(origin) = origin_of(*id, *seed).filter(|o| o.league == league.id) {
                note_gone(&origin.model1);
                note_gone(&origin.model2);
            }
        }
        for name in &gone {
            let record = history
                .changes
                .iter()
                .filter(|c| c.league == league.id)
                .find_map(|c| {
                    c.removed
                        .iter()
                        .find(|(n, _)| n == name)
                        .map(|(_, reason)| (c.at.clone(), format!("{reason} ({})", c.what)))
                });
            let (left_at, reason) = match record {
                Some(record) => record,
                None => {
                    // No record: the start of its last match in the league.
                    let last = matches
                        .iter()
                        .filter(|(id, seed, ..)| {
                            origin_of(*id, *seed).is_some_and(|o| {
                                o.league == league.id && (o.model1 == *name || o.model2 == *name)
                            })
                        })
                        .map(|m| m.4.clone())
                        .max()
                        .unwrap_or_else(|| league.started_at.clone());
                    (
                        last,
                        "left the league (no record of when or why; left_at = start of its \
                         last match)"
                            .to_owned(),
                    )
                }
            };
            conn.execute(
                "INSERT INTO league_players (league_id, player_id, joined_at, left_at, note)
                 VALUES (?1, ?2, ?3, ?4, ?5)",
                params![
                    league.id,
                    ids[name],
                    joined_at(name, Some(&left_at)),
                    left_at,
                    reason
                ],
            )?;
            departed.insert((league.id, name.clone()), reason);
        }
        summary += &format!(
            "\nleague #{}: {} current participants, {} left{}",
            league.id,
            league.roster.len(),
            gone.len(),
            if gone.is_empty() {
                String::new()
            } else {
                format!(" ({})", gone.join(", "))
            }
        );
    }
    conn.execute(
        "UPDATE leagues SET mirror_concurrent = COALESCE(mirror_concurrent, 0), seed_rule = ?1",
        params![db::SEED_RULE],
    )?;

    // Matches.
    let voided_by: HashMap<i64, (&Change, &(i64, String, String))> = history
        .changes
        .iter()
        .flat_map(|c| c.voided.iter().map(move |v| (v.0, (c, v))))
        .collect();
    let mut outcome: BTreeMap<String, usize> = BTreeMap::new();
    for (id, seed, ..) in &matches {
        let Some(origin) = origin_of(*id, *seed) else {
            *outcome
                .entry("unattributed: kept as single matches".into())
                .or_default() += 1;
            continue;
        };
        let league = league_of[&origin.league];
        let fixture = linked.get(id);
        let stale = origin.stage == "playoff-stale";
        let (valid, reason, kind) = if fixture.is_some() && !stale {
            (true, None, "linked: valid")
        } else if stale {
            (
                false,
                Some("stale playoff: players joined after it".to_owned()),
                "stale playoff: void",
            )
        } else if let Some((change, (_, _, why))) = voided_by.get(id) {
            (
                false,
                Some(format!(
                    "voided on {}: {}; voided for {why}",
                    change.at, change.what
                )),
                "voided (changes log): void",
            )
        } else if let Some(change) = history
            .changes
            .iter()
            .find(|c| c.league == origin.league && c.removed_fixtures.contains(&origin.label))
        {
            (
                false,
                Some(format!("fixture removed on {}: {}", change.at, change.what)),
                "fixture removed (changes log): void",
            )
        } else if let Some((name, why)) =
            [&origin.model1, &origin.model2].into_iter().find_map(|n| {
                departed
                    .get(&(origin.league, n.clone()))
                    .map(|why| (n, why))
            })
        {
            (
                false,
                Some(format!("{name} left league #{}: {why}", origin.league)),
                "player left: void",
            )
        } else {
            (
                false,
                Some(format!(
                    "replaced attempt: a later match of `{}` counts",
                    origin.label
                )),
                "replaced attempt: void",
            )
        };
        *outcome.entry(kind.into()).or_default() += 1;
        conn.execute(
            "UPDATE matches SET player1 = ?2, player2 = ?3, stage = ?4, label = ?5,
                 mirror_concurrent = ?6, valid = ?7, void_reason = ?8,
                 voided_at = CASE WHEN ?7 THEN NULL ELSE COALESCE(finished_at, started_at) END
             WHERE id = ?1",
            params![
                id,
                ids[&origin.model1],
                ids[&origin.model2],
                if stale {
                    "playoff"
                } else {
                    origin.stage.as_str()
                },
                origin.label,
                league.mirror,
                valid,
                reason
            ],
        )?;
        if let Some(fixture) = fixture
            && let Some(error) = &fixture.error
        {
            conn.execute(
                "UPDATE matches SET error = ?2, failed_at = ?3 WHERE id = ?1",
                params![id, error, fixture.failed_at],
            )?;
        }
    }
    for (kind, n) in &outcome {
        summary += &format!("\nmatches {kind}: {n}");
    }
    // One result per pair: a pair's valid match counts in every league, whatever its rules.
    let duplicates: Vec<(i64, i64, i64)> = {
        let mut statement = conn.prepare(&format!(
            "SELECT MIN(m.id), MAX(m.id), COUNT(*) FROM matches m WHERE {}
             GROUP BY MIN(m.player1, m.player2), MAX(m.player1, m.player2)
             HAVING COUNT(*) > 1",
            db::PAIR_RESULT
        ))?;
        statement
            .query_map([], |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)))?
            .collect::<rusqlite::Result<_>>()?
    };
    if !duplicates.is_empty() {
        bail!(
            "pairs with several valid matches (one result per pair; first id, last id, count): \
             {duplicates:?}"
        );
    }
    conn.execute_batch(
        "ALTER TABLE league_matches RENAME TO legacy_league_matches;
         CREATE TABLE legacy_league_rosters AS SELECT id AS league_id, models FROM leagues;
         ALTER TABLE leagues DROP COLUMN models;",
    )?;
    db::ensure_derived_schema(conn)?;
    Ok(summary)
}

fn has_column(conn: &Connection, table: &str, column: &str) -> Result<bool> {
    Ok(conn.query_row(
        "SELECT COUNT(*) > 0 FROM pragma_table_info(?1) WHERE name = ?2",
        params![table, column],
        |row| row.get(0),
    )?)
}

/// The league stage's table computed the old way: the legacy roster's names, and every
/// league-stage fixture whose linked match finished.
fn old_standings(db: &Db, id: i64) -> Result<Vec<Standing>> {
    let conn = db.conn();
    let models: Option<String> = conn
        .query_row(
            "SELECT models FROM legacy_league_rosters WHERE league_id = ?1",
            params![id],
            |row| row.get(0),
        )
        .optional()?;
    let Some(models) = models else {
        return Ok(Vec::new());
    };
    let roster: Vec<PlayerConfig> = serde_json::from_str(&models)?;
    let names: Vec<String> = roster.into_iter().map(|c| c.name).collect();
    let fixtures: Vec<(String, String, Option<i64>)> = {
        let mut statement = conn.prepare(
            "SELECT model1, model2, match_id FROM legacy_league_matches
             WHERE league_id = ?1 AND stage = 'league' ORDER BY id",
        )?;
        statement
            .query_map(params![id], |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)))?
            .collect::<rusqlite::Result<_>>()?
    };
    let mut results = Vec::new();
    for (model1, model2, match_id) in fixtures {
        if let Some(match_id) = match_id
            && let Some(result) = db.match_result(match_id)?
        {
            results.push((model1, model2, result));
        }
    }
    Ok(league::rank(&names, &results))
}

/// Prints every league's table the old and the new way; returns how many lines differ.
fn compare(db: &Db) -> Result<usize> {
    let leagues: Vec<(i64, String)> = {
        let mut statement = db
            .conn()
            .prepare("SELECT id, status FROM leagues ORDER BY id")?;
        statement
            .query_map([], |r| Ok((r.get(0)?, r.get(1)?)))?
            .collect::<rusqlite::Result<_>>()?
    };
    let mut differences = 0;
    for (id, status) in leagues {
        let old = old_standings(db, id)?;
        let new = league::standings(db, id)?;
        let width = old
            .iter()
            .chain(&new)
            .map(|r| r.name.len())
            .max()
            .unwrap_or(5)
            .max(5);
        println!(
            "\nleague #{id} ({status}): old layout | new layout\n  #  {:width$}   P   W   D   L  Pts   GW   GL    PF    PA | {:width$}   P   W   D   L  Pts   GW   GL    PF    PA",
            "Model", "Model"
        );
        let line = |row: Option<&Standing>| match row {
            Some(row) => {
                let c = row.counts;
                format!(
                    "{:width$} {:>3} {:>3} {:>3} {:>3} {:>4} {:>4} {:>4} {:>5} {:>5}",
                    row.name, c[0], c[1], c[2], c[3], c[4], c[5], c[6], c[7], c[8]
                )
            }
            None => format!("{:width$}", "-"),
        };
        let mut league_differences = 0;
        for i in 0..old.len().max(new.len()) {
            let (a, b) = (old.get(i), new.get(i));
            let same = a == b;
            if !same {
                league_differences += 1;
            }
            println!(
                " {:>2}  {} | {}{}",
                i + 1,
                line(a),
                line(b),
                if same { "" } else { "   <-- differs" }
            );
        }
        println!(
            "league #{id}: {}",
            if league_differences == 0 {
                "identical".to_owned()
            } else {
                format!("{league_differences} lines differ")
            }
        );
        differences += league_differences;
    }
    Ok(differences)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::players::PlayerConfig;

    /// Builds an old-layout database: two leagues sharing a player, fixtures with finished,
    /// running and replaced matches, a removed player with a fixture deleted from the league,
    /// a stale playoff, and a single match outside leagues.
    fn old_database(path: &Path) {
        let conn = Connection::open(path).unwrap();
        conn.execute_batch(
            "CREATE TABLE leagues (id INTEGER PRIMARY KEY, started_at TEXT NOT NULL,
                 finished_at TEXT, seed INTEGER NOT NULL, rounds INTEGER NOT NULL,
                 clock_seconds INTEGER, delay_seconds INTEGER, max_turns INTEGER,
                 models TEXT NOT NULL, status TEXT NOT NULL, ranking TEXT, note TEXT,
                 prompt_version TEXT, order_seed INTEGER, heartbeat_at TEXT,
                 mirror_concurrent INTEGER);
             CREATE TABLE league_matches (id INTEGER PRIMARY KEY, league_id INTEGER NOT NULL,
                 stage TEXT NOT NULL, label TEXT NOT NULL, matchday INTEGER,
                 model1 TEXT NOT NULL, model2 TEXT NOT NULL, seed INTEGER NOT NULL,
                 match_id INTEGER, error TEXT, failed_at TEXT, UNIQUE (league_id, label));",
        )
        .unwrap();
        let roster = |names: &[&str]| {
            serde_json::to_string(
                &names
                    .iter()
                    .map(|n| PlayerConfig::new(n, &n.to_lowercase()))
                    .collect::<Vec<_>>(),
            )
            .unwrap()
        };
        conn.execute(
            "INSERT INTO leagues (id, started_at, seed, rounds, max_turns, models, status,
                                  prompt_version, order_seed, mirror_concurrent)
             VALUES (1, '2026-10-15T10:00:00Z', 11, 3, 300, ?1, 'finished', 'bg-v2', 9, NULL),
                    (2, '2026-10-19T10:00:00Z', 22, 3, 300, ?2, 'running', 'bg-v2', 9, 1)",
            params![roster(&["A", "B", "C", "D"]), roster(&["D", "E", "F"])],
        )
        .unwrap();
        drop(conn);
        // The matches table and its games come from the current schema.
        let db = Db::open_raw(path).unwrap();
        db::ensure_schema(db.conn()).unwrap();
        let conn = db.conn();
        let protocol = crate::runner::Protocol {
            version: crate::players::prompt::PromptVersion::BgV2,
            order_seed: 9,
            harness: crate::runner::Harness::default(),
        };
        let mut next_game = 0;
        // (league, label, model1, model2, games won by 1, by 2, finished?, linked?)
        let mut add = |league: i64,
                       stage: &str,
                       label: &str,
                       models: (&str, &str),
                       games: (u32, u32),
                       finished: bool,
                       linked: bool| {
            let league_seed: i64 = conn
                .query_row("SELECT seed FROM leagues WHERE id = ?1", [league], |r| {
                    r.get(0)
                })
                .unwrap();
            let seed = derive_seed(league_seed as u64, label);
            let id = db
                .create_match(
                    &models.0.to_lowercase(),
                    &models.1.to_lowercase(),
                    seed,
                    3,
                    None,
                    Some(300),
                    &protocol,
                )
                .unwrap();
            for (player, n) in [(1u8, games.0), (2u8, games.1)] {
                for _ in 0..n {
                    next_game += 1;
                    db.create_game(id, next_game, 1, 1, 0, (1, 2)).unwrap();
                    conn.execute(
                        "UPDATE games SET winner_player = ?2, result = 'single', points = 1
                         WHERE id = ?1",
                        params![conn.last_insert_rowid(), player],
                    )
                    .unwrap();
                }
            }
            db.update_match_score(id, 3, [games.0, games.1]).unwrap();
            if finished {
                let winner = match games.0.cmp(&games.1) {
                    std::cmp::Ordering::Greater => Some(1),
                    std::cmp::Ordering::Less => Some(2),
                    std::cmp::Ordering::Equal => None,
                };
                db.finish_match(id, winner).unwrap();
            }
            if linked {
                conn.execute(
                    "INSERT INTO league_matches (league_id, stage, label, model1, model2, seed,
                                                 match_id)
                     VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)
                     ON CONFLICT (league_id, label) DO UPDATE SET match_id = excluded.match_id",
                    params![league, stage, label, models.0, models.1, seed as i64, id],
                )
                .unwrap();
            }
            id
        };
        // League 1: A, B, C, D (X removed; its fixture deleted, its match kept).
        let replaced = add(
            1,
            "league",
            "matchday 1: A v B",
            ("A", "B"),
            (1, 0),
            false,
            true,
        );
        add(
            1,
            "league",
            "matchday 1: A v B",
            ("A", "B"),
            (4, 2),
            true,
            true,
        );
        add(
            1,
            "league",
            "matchday 1: C v D",
            ("C", "D"),
            (3, 3),
            true,
            true,
        );
        add(
            1,
            "league",
            "matchday 2: A v C",
            ("A", "C"),
            (1, 4),
            true,
            true,
        );
        add(
            1,
            "league",
            "matchday 2: D v B",
            ("D", "B"),
            (4, 1),
            true,
            true,
        );
        add(
            1,
            "league",
            "matchday 3: A v D",
            ("A", "D"),
            (2, 4),
            true,
            true,
        );
        add(
            1,
            "league",
            "matchday 3: B v C",
            ("B", "C"),
            (4, 3),
            true,
            true,
        );
        add(
            1,
            "league",
            "matchday 4: X v A",
            ("X", "A"),
            (4, 0),
            true,
            false,
        );
        add(
            1,
            "playoff-stale",
            "playoff for places 1-2: A v D [stale]",
            ("A", "D"),
            (1, 0),
            true,
            true,
        );
        // League 2: D, E, F; one finished, one running, one not started.
        add(
            2,
            "league",
            "matchday 1: D v E",
            ("D", "E"),
            (0, 4),
            true,
            true,
        );
        add(
            2,
            "league",
            "matchday 1: E v F",
            ("E", "F"),
            (1, 1),
            false,
            true,
        );
        conn.execute(
            "INSERT INTO league_matches (league_id, stage, label, model1, model2, seed)
             VALUES (2, 'league', 'matchday 2: F v D', 'F', 'D', 5)",
            [],
        )
        .unwrap();
        // A single match outside leagues.
        db.create_match("random", "safest", 99, 3, None, Some(300), &protocol)
            .unwrap();
        assert_eq!(replaced, 1);
    }

    fn freeze_dir(dir: &Path) {
        std::fs::create_dir_all(dir).unwrap();
        std::fs::write(
            dir.join("league1-changes.json"),
            serde_json::json!([{
                "changed_at": "2026-10-16T10:00:00Z", "league": 1, "db": "old.db",
                "change": "X removed",
                "removed": [{"name": "X", "reason": "testing removal"}],
                "removed_fixtures": ["matchday 4: X v A"]
            }])
            .to_string(),
        )
        .unwrap();
        std::fs::write(
            dir.join("league2-additions.json"),
            serde_json::json!([{
                "added_at": "2026-10-19T12:00:00Z", "league": 2, "db": "old.db", "name": "F",
                "entry": {"name": "F", "spec": "f"}, "fixtures": []
            }])
            .to_string(),
        )
        .unwrap();
    }

    /// The old and the new tables agree, every match row is kept, links become valid
    /// matches, the rest void with a reason, and a second run only compares.
    #[test]
    fn standings_equal_old_and_new_on_a_fixture_database() {
        let dir = std::env::temp_dir().join(format!("jevgammon-migrate-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        let path = dir.join("old.db");
        old_database(&path);
        freeze_dir(&dir.join("freeze"));
        assert!(
            Db::open(&path).is_err(),
            "the new layout needs the migration"
        );
        let args = MigrateArgs {
            db: path.clone(),
            dry_run: true,
            freeze: dir.join("freeze"),
            freeze_db: None,
        };
        run(&args).unwrap();
        assert!(db::legacy_layout(Db::open_raw(&path).unwrap().conn()).unwrap());
        run(&MigrateArgs {
            dry_run: false,
            ..args
        })
        .unwrap();
        let db = Db::open(&path).unwrap();
        for id in [1, 2] {
            assert_eq!(
                old_standings(&db, id).unwrap(),
                league::standings(&db, id).unwrap()
            );
        }
        let table = league::standings(&db, 1).unwrap();
        assert_eq!(table[0].name, "D");
        assert_eq!(table.iter().map(|r| r.counts[0]).sum::<u32>(), 12);
        let conn = db.conn();
        let count = |sql: &str| -> i64 { conn.query_row(sql, [], |r| r.get(0)).unwrap() };
        assert_eq!(count("SELECT COUNT(*) FROM matches"), 12);
        assert_eq!(
            count("SELECT COUNT(*) FROM matches WHERE valid = 1 AND stage IS NOT NULL"),
            8
        );
        assert_eq!(
            count("SELECT COUNT(*) FROM matches WHERE stage IS NULL AND valid = 1"),
            1
        );
        let reason = |id: i64| -> String {
            conn.query_row("SELECT void_reason FROM matches WHERE id = ?1", [id], |r| {
                r.get(0)
            })
            .unwrap()
        };
        assert!(reason(1).starts_with("replaced attempt"), "{}", reason(1));
        assert!(reason(8).starts_with("fixture removed"), "{}", reason(8));
        assert!(reason(9).starts_with("stale playoff"), "{}", reason(9));
        let (left_at, note): (String, String) = conn
            .query_row(
                "SELECT left_at, lp.note FROM league_players lp JOIN players p ON p.id = lp.player_id
                 WHERE p.name = 'X'",
                [],
                |r| Ok((r.get(0)?, r.get(1)?)),
            )
            .unwrap();
        assert_eq!(left_at, "2026-10-16T10:00:00Z");
        assert!(note.starts_with("testing removal"));
        let f_joined: String = conn
            .query_row(
                "SELECT joined_at FROM league_players lp JOIN players p ON p.id = lp.player_id
                 WHERE p.name = 'F'",
                [],
                |r| r.get(0),
            )
            .unwrap();
        assert_eq!(f_joined, "2026-10-19T12:00:00Z");
        // D plays in both leagues: one player row.
        assert_eq!(count("SELECT COUNT(*) FROM players WHERE name = 'D'"), 1);
        // League 2's running match resumes as the pair's match; F v D is still to play.
        let participants = db.participants(2).unwrap();
        let ids: Vec<i64> = participants.iter().map(|p| p.player_id).collect();
        let matches = db.matches_between(&ids).unwrap();
        assert_eq!(matches.len(), 2);
        drop(db);
        // Idempotent: a second run only compares.
        run(&MigrateArgs {
            db: path.clone(),
            dry_run: false,
            freeze: dir.join("freeze"),
            freeze_db: None,
        })
        .unwrap();
        let _ = std::fs::remove_dir_all(&dir);
    }
}
