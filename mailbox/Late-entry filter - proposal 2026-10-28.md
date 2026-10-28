# Late-entry filter: proposal (2026-10-28)

For Can, through Main. **Nothing here is committed to `tools/site`, and nothing is deployed.** The site update timer (`bg-site-preview.timer`) has been **stopped since 15:44 UTC** and stays off until you confirm. The live site still shows the 15:35 UTC data, which has no late-entry decision in it.

## Rule (Can, 2026-10-28)

The late entries play every original League 3 setup once. GPT-6 Astra (high) is the only one now, because the Terra entries are cancelled. Their games stay **out of the standings and out of every other setup's published numbers**. The matches are marked explicitly, and the filter tests that mark. It does not rely on the league being hidden.

## 1. Marking (done in v3.db, no code)

- Matches #758, #759 and #760 (Astra (high) v GNUbg weak, Astra (off) and Astra (on), hidden league #9) have `matches.stage = 'late-entry'`. The runner counts any stage other than NULL or `'playoff'` as a pair's result (`src/db.rs` `PAIR_RESULT`). Pair bookkeeping is therefore unchanged: a late-entry pair is played once and never again.
- Future late-entry matches are marked by a trigger in v3.db. The runner always inserts `stage = 'league'`, so without the trigger they would not be marked:

```sql
CREATE TRIGGER late_entry_stage AFTER INSERT ON matches
WHEN EXISTS (SELECT 1 FROM players p WHERE p.id IN (NEW.player1, NEW.player2)
             AND p.name IN ('GPT-6 Astra (high)', 'GPT-6.1 Terra (low)', 'GPT-6.1 Terra (high)'))
BEGIN
  UPDATE matches SET stage = 'late-entry' WHERE id = NEW.id;
END;
```

  The trigger still lists the cancelled Terra names. That does no harm, because no Terra match will be played.

## 2. Where the late-entry games leaked (audit of every query path)

Today exactly one path leaks: the **global error rate**. It is computed in two places, `tools/league_web.py error_rates` (Python) and `src/scores.rs error_rates` (Rust). Both count every valid match. That rate feeds:
- the standings tiebreak on the site, on the dashboard, in the ladder tools and in the runner;
- the dashboard's error-rate column.

Every other site number comes through `league_match_view` for shown leagues. Hidden league #9 is not in that view. The rest is latent: it would leak only if Astra (high) became a participant of a shown league. `score_plays.py` scores late-entry turns (shard rows with `league_id` NULL). Those rows have no effect once the turns queries leave them out.

## 3. The filter (diff, from a separate worktree; not committed)

Two chokepoints, plus the internal tools and the docs:
- **Error rate:** `tools/league_web.py error_rates` and `src/scores.rs error_rates` get `AND m.stage <> 'late-entry'`. This covers the site tiebreak, the dashboard, the ladder and the runner. The Rust side takes effect only in a rebuilt runner binary.
- **Site views (`tools/site/snapshot.py`):** in `snap.db`, `league_match_view` is rebuilt as `league_match_view_all` minus `stage = 'late-entry'`. Every view-based number on the site (tables, per-setup quality, risk, confidence, cost and time, decision pages) then drops late-entry matches, even if the entrant ever joined a shown league. The matches stay in the snapshot and are still scored, so the entrant's own numbers can be reported separately.
- **Internal tools, same predicate:** `tools/ladder.py` (`setup_stats`, `concurrent_factor`) and `tools/original_league.py` (`counted_matches`, `paired_estimate`).
- **Docs:** every docstring or README line that said "over all valid matches" now names the exception.

```diff
diff --git a/README.md b/README.md
index 5f2288b..aecb910 100644
--- a/README.md
+++ b/README.md
@@ -446,8 +446,9 @@ existed resumes with `bg-v2-history`, the prompt the runner then sent).
   same way; the round's score is stored when both games have finished.
 - **Table:** a win is 3 league points, a draw (still tied after the extra round) 1. Ties
   are broken by more games won, then fewer games lost, then the **lower error rate** over
-  all of the setup's valid matches (every league, ladder round and Cup): 500 × the mean
-  GNUbg 1.08 2-ply equity loss of its decisions with two or more legal plays, invalid
+  all of the setup's valid matches (every league, ladder round and Cup; late-entry matches,
+  `matches.stage = 'late-entry'`, left out: they count in no other setup's numbers): 500 ×
+  the mean GNUbg 1.08 2-ply equity loss of its decisions with two or more legal plays, invalid
   answers left out, as on the site (rule B11). The runner reads the site update loop's
   scores (`--scores`, default `$XDG_STATE_HOME/bg-site/plays/s*.db`, written by
   `tools/site/score.sh`; `src/scores.rs`); a setup without scored decisions ranks after
diff --git a/src/db.rs b/src/db.rs
index b326fee..06e8d21 100644
--- a/src/db.rs
+++ b/src/db.rs
@@ -376,7 +376,8 @@ CREATE TABLE IF NOT EXISTS leagues (
     -- running | finished
     status          TEXT NOT NULL,
     -- Final ranking (JSON array of "place. name", first place first): points, games won,
-    -- fewer games lost, then the lower error rate over all of a setup's valid matches.
+    -- fewer games lost, then the lower error rate over all of a setup's valid matches
+    -- (late-entry matches left out).
     ranking         TEXT,
     -- What the league tests (`--note`) and what changed since, shown in the web history.
     note            TEXT,
diff --git a/src/league.rs b/src/league.rs
index 12f6ac3..19947b2 100644
--- a/src/league.rs
+++ b/src/league.rs
@@ -9,9 +9,9 @@
 //! matchday. A match that fails is deferred and resumed later from its last stored turn;
 //! only the failing model backs off, the others play on. The table ranks by points, then
 //! more games won, then fewer games lost, then the lower error rate over all of a setup's
-//! valid matches (`scores`); there are no playoffs. A league can play only one setup's pairs
-//! (an early start of its matches for a coming ladder round) and be hidden from the site,
-//! the dashboard and the ladder tools (`Scope`).
+//! valid matches, late-entry matches left out (`scores`); there are no playoffs. A league can
+//! play only one setup's pairs (an early start of its matches for a coming ladder round) and
+//! be hidden from the site, the dashboard and the ladder tools (`Scope`).
 
 use std::collections::{HashMap, HashSet};
 use std::path::PathBuf;
diff --git a/src/scores.rs b/src/scores.rs
index 2d74fce..d0e6fa9 100644
--- a/src/scores.rs
+++ b/src/scores.rs
@@ -5,8 +5,10 @@
 //! `<state>/bg-site/plays/s{0..31}.db`, table `plays (turn_id, loss, ...)`. The error rate of a
 //! setup is the site's (brief B11): 500 × the mean equity loss of its decisions with two or
 //! more legal plays, invalid answers (`decided_by = 'fallback'`) left out, over all of its
-//! valid matches (every league, ladder round and Cup, legacy playoffs included). Decisions
-//! not scored yet are counted, so a caller can tell a complete error rate from a partial one.
+//! valid matches (every league, ladder round and Cup, legacy playoffs included; late-entry
+//! matches, `matches.stage = 'late-entry'`, left out: they count in no other setup's numbers).
+//! Decisions not scored yet are counted, so a caller can tell a complete error rate from a
+//! partial one.
 
 use std::collections::HashMap;
 use std::path::{Path, PathBuf};
@@ -19,7 +21,7 @@ use crate::db::Db;
 /// Error rate = `SCALE` × mean equity loss (site thresholds `equity_scale`).
 pub const SCALE: f64 = 500.0;
 
-/// One setup's error rate over all of its valid matches.
+/// One setup's error rate over all of its valid matches (late-entry matches left out).
 #[derive(Clone, Copy, Debug, Default, PartialEq)]
 pub struct ErrorRate {
     /// Sum of the equity losses of the scored decisions.
@@ -77,7 +79,7 @@ pub fn error_rates(db: &Db, dir: &Path) -> Result<HashMap<String, ErrorRate>> {
          JOIN games g ON g.id = t.game_id
          JOIN matches m ON m.id = g.match_id
          JOIN players p ON p.id = CASE t.player WHEN 1 THEN m.player1 ELSE m.player2 END
-         WHERE m.valid = 1 AND m.stage IS NOT NULL
+         WHERE m.valid = 1 AND m.stage IS NOT NULL AND m.stage <> 'late-entry'
            AND t.decided_by = 'model' AND t.legal_count >= 2",
     )?;
     let mut rates: HashMap<String, ErrorRate> = HashMap::new();
diff --git a/tools/ladder.py b/tools/ladder.py
index 765ed7a..18cc570 100755
--- a/tools/ladder.py
+++ b/tools/ladder.py
@@ -12,9 +12,9 @@ Rules (setups move, not models; one result per pair):
   league's winner swaps with the upper league's last. Programs (GNU Backgammon, Random, Safest) never
   move: when a rule picks a program, the next setup in the table is taken.
 - Tables: points, games won, fewer games lost, then the lower error rate over all of a setup's valid
-  matches (`league_web.error_rates`, the site's GNUbg scores). A pair's valid match counts in every
-  league whatever league or rules it was played in, so a mover plays only the pairs it never played;
-  every other pair of its new league is reused (order ignored).
+  matches, late-entry matches left out (`league_web.error_rates`, the site's GNUbg scores). A pair's
+  valid match counts in every league whatever league or rules it was played in, so a mover plays only
+  the pairs it never played; every other pair of its new league is reused (order ignored).
 - No lock (Can, 2026-10-26; the earlier lock rule is gone): setups move by these rules every round,
   as often as the tables say.
 - End: the ladder ends at the first round whose moves would create no new pairing (every pair they
@@ -212,12 +212,14 @@ def compute_round(conn, scores: Path) -> dict:
 
 def concurrent_factor(conn) -> float:
     """Median wall time of a match with both games of a round at once, over the summed decision time of
-    both sides (pauses over league_web.PAUSE_GAP left out): measured on the stored valid matches."""
+    both sides (pauses over league_web.PAUSE_GAP left out): measured on the stored valid matches, late-entry
+    matches left out."""
     ratios = []
     rows = conn.execute(
         """SELECT m.id, t.created_at, t.latency_ms, t.decided_by FROM turns t JOIN games g ON g.id = t.game_id
            JOIN matches m ON m.id = g.match_id
-           WHERE m.valid = 1 AND m.stage IS NOT NULL AND m.mirror_concurrent = 1 ORDER BY m.id, t.created_at""")
+           WHERE m.valid = 1 AND m.stage IS NOT NULL AND m.stage <> 'late-entry' AND m.mirror_concurrent = 1
+           ORDER BY m.id, t.created_at""")
     by = defaultdict(list)
     for r in rows:
         by[r["id"]].append(r)
@@ -231,15 +233,16 @@ def concurrent_factor(conn) -> float:
 
 
 def setup_stats(conn) -> dict[str, dict]:
-    """Per setup over its valid matches: decisions per match (its own side), seconds per decision, and
-    the cost per decision at its configured price (NULL prices count as unknown)."""
+    """Per setup over its valid matches (late-entry matches left out): decisions per match (its own side),
+    seconds per decision, and the cost per decision at its configured price (NULL prices count as unknown)."""
     out = {}
     for r in conn.execute(
             """SELECT p.name, COUNT(DISTINCT m.id) AS matches, COUNT(*) AS decisions,
                       AVG(t.latency_ms) / 1000.0 AS seconds, SUM(t.cost_usd) AS cost, COUNT(t.cost_usd) AS priced
                FROM turns t JOIN games g ON g.id = t.game_id JOIN matches m ON m.id = g.match_id
                JOIN players p ON p.id = CASE t.player WHEN 1 THEN m.player1 ELSE m.player2 END
-               WHERE m.valid = 1 AND m.stage IS NOT NULL AND t.decided_by IN ('model', 'fallback')
+               WHERE m.valid = 1 AND m.stage IS NOT NULL AND m.stage <> 'late-entry'
+                 AND t.decided_by IN ('model', 'fallback')
                GROUP BY p.name"""):
         out[r["name"]] = dict(per_match=r["decisions"] / r["matches"], seconds=r["seconds"],
                               cost=(r["cost"] / r["priced"]) if r["priced"] else None)
@@ -412,9 +415,9 @@ def request(conn, plan: dict, db: Path) -> str:
                 "the first round whose moves would create no new pairing).", ""]
     out += ["## Tables used", "",
             "Ranking: points, then games won, then fewer games lost, then the lower error rate over all of a "
-            "setup's valid matches (every league, ladder round and Cup; GNUbg 1.08 2-ply, 500 x mean equity loss, "
-            "decisions with two or more legal plays, invalid answers left out, as on the site). Programs never "
-            "move.", ""]
+            "setup's valid matches (every league, ladder round and Cup; late-entry matches left out; GNUbg 1.08 "
+            "2-ply, 500 x mean equity loss, decisions with two or more legal plays, invalid answers left out, as "
+            "on the site). Programs never move.", ""]
     for lid in LADDER:
         rows = plan["before"][lid]["table"]
         top = [r for r in rows if not is_program(people[r["name"]])]
@@ -436,8 +439,8 @@ def request(conn, plan: dict, db: Path) -> str:
             for m in plan["history"]]
     out += ["", "## Error-rate flag", "",
             "A swap is flagged when the promoted setup's error rate is worse (higher) than the error rate of the "
-            "setup it replaces. Error rates over all valid matches, 95% intervals by resampling games (site "
-            "method, 2,000 resamples).", "",
+            "setup it replaces. Error rates over all valid matches but late-entry ones, 95% intervals by resampling "
+            "games (site method, 2,000 resamples).", "",
             "| Boundary | Promoted | Error rate | Replaced | Error rate | Flag |", "| --- | --- | --- | --- | --- | --- |"]
     for s in plan["swaps"]:
         a, b = rates[s["promoted"]]["rate"], rates[s["replaced"]]["rate"]
diff --git a/tools/league_web.py b/tools/league_web.py
index e90232b..b993296 100755
--- a/tools/league_web.py
+++ b/tools/league_web.py
@@ -8,9 +8,9 @@ league in progress. The page shows the latest league (or ?league=N), the history
 league in the database with what each one tested (`leagues.note`), and links to the working
 copy of the published report (`--report`, served at /report/). The table follows `src/league.rs`: 3 points for a win, 1 for
 a draw, ties broken by more games won, then fewer games lost, then the lower error rate over all of a
-setup's valid matches (the site's GNUbg scores, `--scores`); only finished matches count: the valid
-match of every pair of current participants, whatever league or rules it was played under (one result
-per pair). The fixture is derived from the participants as the runner derives it (`pair_order`,
+setup's valid matches, late-entry matches left out (the site's GNUbg scores, `--scores`); only finished
+matches count: the valid match of every pair of current participants, whatever league or rules it was
+played under (one result per pair). The fixture is derived from the participants as the runner derives it (`pair_order`,
 `new_pair`).
 
 --control SCRIPT adds a Pause / Resume button: GET /api/control runs `SCRIPT status` (one JSON
@@ -348,7 +348,8 @@ def default_scores() -> Path:
 
 
 def error_rates(conn: sqlite3.Connection, plays_dir: Path) -> dict[str, dict]:
-    """Every setup's error rate over all of its valid matches (every league, ladder round and Cup), as
+    """Every setup's error rate over all of its valid matches (every league, ladder round and Cup; late-entry
+    matches, `matches.stage = 'late-entry'`, left out: they count in no other setup's numbers), as
     `src/scores.rs` computes it for the tiebreak: 500 x mean 2-ply equity loss of its decisions with two
     or more legal plays, invalid answers left out (site rule B11), from the site's score shards
     `plays_dir/s*.db`. Per name: rate (None without a scored decision), scored, skipped, pending (not
@@ -367,7 +368,8 @@ def error_rates(conn: sqlite3.Connection, plays_dir: Path) -> dict[str, dict]:
             """SELECT t.id, t.game_id, p.name FROM turns t JOIN games g ON g.id = t.game_id
                JOIN matches m ON m.id = g.match_id
                JOIN players p ON p.id = CASE t.player WHEN 1 THEN m.player1 ELSE m.player2 END
-               WHERE m.valid = 1 AND m.stage IS NOT NULL AND t.decided_by = 'model' AND t.legal_count >= 2"""):
+               WHERE m.valid = 1 AND m.stage IS NOT NULL AND m.stage <> 'late-entry'
+                 AND t.decided_by = 'model' AND t.legal_count >= 2"""):
         r = out.setdefault(name, dict(loss=0.0, scored=0, skipped=0, pending=0, games=defaultdict(lambda: [0.0, 0])))
         if turn in loss:
             r["loss"] += loss[turn]
diff --git a/tools/original_league.py b/tools/original_league.py
index 738e0ad..732bcb3 100755
--- a/tools/original_league.py
+++ b/tools/original_league.py
@@ -61,13 +61,14 @@ def members(conn) -> dict[int, list[str]]:
 
 
 def counted_matches(conn, names: list[str]) -> tuple[dict[frozenset, dict], list[dict]]:
-    """The finished valid matches between the setups `names`, by pair, and the unfinished ones."""
+    """The finished valid matches between the setups `names`, by pair, and the unfinished ones (late-entry
+    matches left out: they count in no other setup's numbers)."""
     wanted = set(names)
     done, running = {}, []
     for r in conn.execute(
             """SELECT m.id, m.status, m.score1, m.score2, p1.name AS a, p2.name AS b
                FROM matches m JOIN players p1 ON p1.id = m.player1 JOIN players p2 ON p2.id = m.player2
-               WHERE m.valid = 1 AND m.stage IS NOT NULL AND m.stage <> 'playoff' ORDER BY m.id"""):
+               WHERE m.valid = 1 AND m.stage IS NOT NULL AND m.stage NOT IN ('playoff', 'late-entry') ORDER BY m.id"""):
         if r["a"] not in wanted or r["b"] not in wanted:
             continue
         key = frozenset((r["a"], r["b"]))
@@ -408,12 +409,14 @@ def paired_estimate(conn, paired: Path, names: list[str]) -> list[dict]:
             """SELECT COUNT(*), AVG(t.input_tokens), AVG(t.output_tokens), AVG(t.request_ms)
                FROM turns t JOIN games g ON g.id = t.game_id JOIN matches m ON m.id = g.match_id
                JOIN players p ON p.id = CASE t.player WHEN 1 THEN m.player1 ELSE m.player2 END
-               WHERE p.name = ? AND m.valid = 1 AND m.stage IS NOT NULL AND t.decided_by = 'model'
+               WHERE p.name = ? AND m.valid = 1 AND m.stage IS NOT NULL AND m.stage <> 'late-entry'
+                 AND t.decided_by = 'model'
                  AND t.legal_count BETWEEN 2 AND 25 AND t.group_size IS NULL""", (name,)).fetchone()
         times = sorted(r[0] for r in conn.execute(
             """SELECT t.request_ms FROM turns t JOIN games g ON g.id = t.game_id JOIN matches m ON m.id = g.match_id
                JOIN players p ON p.id = CASE t.player WHEN 1 THEN m.player1 ELSE m.player2 END
-               WHERE p.name = ? AND m.valid = 1 AND m.stage IS NOT NULL AND t.decided_by = 'model'
+               WHERE p.name = ? AND m.valid = 1 AND m.stage IS NOT NULL AND m.stage <> 'late-entry'
+                 AND t.decided_by = 'model'
                  AND t.legal_count BETWEEN 2 AND 25 AND t.group_size IS NULL AND t.request_ms IS NOT NULL""",
             (name,)))
         n, inp, outp, mean_ms = stats
diff --git a/tools/site/score_plays.py b/tools/site/score_plays.py
index 826d44a..1986ae3 100644
--- a/tools/site/score_plays.py
+++ b/tools/site/score_plays.py
@@ -13,8 +13,10 @@ A league decision is a `turns` row with decided_by 'model' or 'fallback' in a va
 leagues keeps its matches scored); plays.league_id is the match's shown league in `league_match_view`
 (NULL when it is in no shown league, e.g. a match held only by a hidden league, `leagues.hidden`, an
 early start for the next ladder round: it is a valid match, so it is scored and counts in every error
-rate over all valid matches, as Method says). This shard takes those with turn_id % SHARDS == SHARD
-that are not yet in plays
+rate over all valid matches, as Method says). Late-entry matches (`matches.stage = 'late-entry'`) are
+scored too (league_id NULL), but they are in no view (tools/site/snapshot.py leaves them out of
+`league_match_view`) and in no error rate: they count in no other setup's numbers. This shard takes
+those with turn_id % SHARDS == SHARD that are not yet in plays
 or skipped (incremental). For each one the legal plays are generated by tools/v3/rules.py (the
 runner's order and notation); their count must equal turns.legal_count and the stored move must
 lead to the play at turns.chosen_index, else the decision is skipped with the reason. Every legal
diff --git a/tools/site/snapshot.py b/tools/site/snapshot.py
index 258d2fc..b5ba108 100755
--- a/tools/site/snapshot.py
+++ b/tools/site/snapshot.py
@@ -337,7 +337,17 @@ def run(v3, state):
                              " AND tbl_name != 'exchanges'").fetchall():
         db.execute(sql)
     # Views (league_match_view) after the tables they read: their names resolve to main's copies.
-    for (sql,) in db.execute("SELECT sql FROM src.sqlite_master WHERE type = 'view' ORDER BY rowid").fetchall():
+    # Late-entry matches (matches.stage 'late-entry') are in no league's view on the site: league_match_view is
+    # v3.db's view with them left out (the full one stays as league_match_view_all). They stay in the snapshot,
+    # so they are still scored (plays.league_id NULL), but count in no other setup's numbers.
+    views = db.execute("SELECT name, sql FROM src.sqlite_master WHERE type = 'view' ORDER BY rowid").fetchall()
+    for name, sql in views:
+        if name == "league_match_view":
+            head = "CREATE VIEW league_match_view AS"
+            if not sql.startswith(head):
+                raise RuntimeError(f"league_match_view: unexpected definition in {v3}: {sql[:80]!r}")
+            db.execute("CREATE VIEW league_match_view_all AS" + sql[len(head):])
+            sql = "CREATE VIEW league_match_view AS SELECT * FROM league_match_view_all WHERE stage <> 'late-entry'"
         db.execute(sql)
     engines = engine_setups(db, "main.")
     targets = {}
```

## 4. Before / after / baseline (local builds in /tmp; nothing deployed)

## Setup
- Worktrees (detached at `ae55aeb`, left in place): BEFORE = `/tmp/le-before-wt` (HEAD code); AFTER = `/tmp/le-after` (filter edits, uncommitted). Untracked data (`replay.db`, `smoke/`, `positions/games`, `positions/nack-paired/{candidates,games}`, other top-level entries) is symlinked from the main checkout. The main checkout is unchanged: `git status` shows only the user's earlier changes.
- Diff: `/tmp/le-filter.diff` (9 files, +59/−35). It covers the five requested changes plus doc lines that said "over all valid matches": `README.md:449`, `src/db.rs:379`, `src/league.rs:11-14`, the `scores.rs` header/struct docs, the `league_web.py` module docstring, and the `ladder.py` docstrings plus two strings it writes into its plan output (`:417-420`, `:443-444`). `counted_matches` uses `stage NOT IN ('playoff', 'late-entry')`.
- Input: one read-only, consistent copy of v3.db, `/tmp/le-v3.db`, taken at 15:54:42Z. It has every table, index, view and trigger. `exchanges` holds only rows with turn_id > 202348 (395 rows), because only new decisions read it. Max turn is 202722; matches 758–760 are `late-entry` and `running`. Both snapshots read this file instead of the live path, so BEFORE and AFTER saw identical data.
- State: `/tmp/le-{before,after}/state` = rsync of `~/.local/state/bg-site` without `analysis` and `src`. Out dirs were seeded with the baseline tree, as `update.sh` builds on top of the clone: `/tmp/le-{before,after}/site` and `/tmp/le-{before,after}/preview` (`--preview-redirects`).
- Baseline: `git archive` of analysis commit `330055dd2` ("backgammon: data as of 2026-10-28T15:35Z a12573f2") into `/tmp/le-baseline/{backgammon,backgammon-preview}`.
- Python version: the timer runs `/usr/bin/python3` (3.14.4), while the shell's pyenv `python3` is 3.12.13. A first build pair under 3.12 had identical content, but every `.json.gz` differed in the gzip OS byte (0x03 vs 0xff), which gave results hash `6b52ca52`. The final builds use `/usr/bin/python3`.

## Build status
| Step | BEFORE | AFTER |
|---|---|---|
| snapshot.py | exit 0, new 0, skipped {}, fingerprint `t202722/202722 l1:finished:171/171 l2:finished:171/171 l3:finished:66/66` | same |
| snap `league_match_view` | 779 rows, max match 760 (league 9: 758–760) | 776 rows, max 757; `league_match_view_all` keeps the 3 late-entry rows |
| score.sh | exit 0, 323 decisions newly scored | exit 0, 323 (all late-entry; shard rows `league_id` NULL) |
| build.py (+ checks.py) | exit 0, checks passed (no `site-check-failures.json`), results `a12573f2`, 2298 decision files, scored l1 36995 / l2 39538 / l3 16355 | identical |

The only stderr output was the existing `offline.py:213` numpy RuntimeWarning, in both builds.

## BEFORE vs AFTER (published output)
**There are no differing leaves.** All 2515 files in `site/` are byte-identical, as are all files in `preview/`.

The leak does not reach the published bytes today because the global rate enters the site only as the standings tiebreak (`place`). In no shown league is any row level on points, games won and games lost, so places do not move. The table rows' `error_rate` field is not published; the identical builds prove this.

The leak does show in the internal table rows (`league_table`):

| League | Setup | Place | error_rate BEFORE | error_rate AFTER |
|---|---|---|---|---|
| 1 | GNUbg weak | 1 | 25.4089 | 25.4689 |
| 2 | GNUbg weak | 12 | 25.4089 | 25.4689 |
| 3 | GPT-6 Astra (on) | 2 | 11.6933 | 11.4978 |
| 3 | GPT-6 Astra (off) | 7 | 11.1961 | 11.2812 |
| 3 | GNUbg weak | 12 | 25.4089 | 25.4689 |

Order and places are identical in all three leagues (19, 19 and 12 rows).

## AFTER vs BASELINE (15:35Z live site)
- **Data JSON:** all 89 `data/**/*.json` files are byte-identical except `data/manifest.json`, which differs in one leaf: `/data_as_of` `2026-10-28T15:35Z` → `2026-10-28T15:56Z`. `results` is `a12573f2` in both.
- **Decision files:** all 2299 under `decisions/` are byte-identical.
- **HTML:** 99 pages differ only in the version line ("updated 28 October 2026, 15:35 UTC" → "15:56 UTC"). On `index.html` the risk-card image names differ too. No other text differs.
- **Share images:** the 3 `share/risk-card-league-{1,2,3}-*.png` files are renamed (`6c52c1d2`/`6a1316c9`/`8aa9ec2f` → `8ab9adaf`/`fe81031a`/`ef8bca0c`). The name hashes the card's HTML, and the card footer prints the as-of time (`home.py:1330`), so this is also a timestamp effect.
- **Preview redirects:** identical.

So AFTER == BASELINE for every setup's numbers (GNUbg weak, GPT-6 Astra (on), GPT-6 Astra (off) and all others), and the league tables and standings order are identical. BEFORE equals BASELINE in the same way (same three classes of timestamp differences).

## Where GPT-6 Astra (high) appears
- **Site output:** nowhere. A search for "Astra (high)", "astra-high" and "late-entry" over all files, gz decompressed, found 0 hits in BASELINE, BEFORE and AFTER (site and preview).
- **AFTER state:** `snap.db` has the 3 matches in `league_match_view_all` and 0 in `league_match_view`. The shards hold 323 scored rows with turn_id ≥ 202349, all with `league_id` NULL. `prompts.db` has 0 late-entry turns.

## Dashboard error rates (`league_web.error_rates`)
Read-only, one read transaction each, plays = `/tmp/le-after/state/plays`. Columns are rate (scored / skipped / pending).

| Setup | BEFORE (HEAD), frozen copy | AFTER, frozen copy | id < 758 only | BEFORE, live v3.db | AFTER, live v3.db |
|---|---|---|---|---|---|
| GNUbg weak | 25.4089 (5427/0/0) | 25.4689 (5359/0/0) | 25.4689 (5359/0/0) | 25.4089 (5427/0/12) | 25.4689 (5359/0/0) |
| GPT-6 Astra (on) | 11.6933 (1778/0/0) | 11.4978 (1718/0/0) | 11.4978 (1718/0/0) | 11.6933 (1778/0/14) | 11.4978 (1718/0/0) |
| GPT-6 Astra (off) | 11.1961 (1723/0/0) | 11.2812 (1694/0/0) | 11.2812 (1694/0/0) | 11.1961 (1723/0/7) | 11.2812 (1694/0/0) |
| GPT-6 Astra (high) | 16.1485 (166/0/0) | absent | absent | 16.1485 (166/0/36) | absent |

- **Sanity check:** AFTER equals the rates over valid staged matches with id < 758 (`original_league.error_rates`) for all 48 setups. Rate, scored, skipped and pending all match.
- **Changed setups:** only those four change between BEFORE and AFTER.
- **Pending:** on live v3.db, the late-entry turns played after the frozen copy show up as pending in BEFORE only; AFTER has none.
- **Baseline:** the 15:35 site already used exactly these AFTER values, because its snapshot stopped at turn 202348.

## original_league.py
`tables` and `cup` were run read-only (`--db /tmp/le-v3.db --scores /tmp/le-after/state/plays`) from each worktree. All four runs exited 0. The outputs are identical BEFORE vs AFTER: `tables` 103 lines, `cup` 83 lines, `diff` empty. Files: `/tmp/le-ol-{before-wt,after}-{tables,cup}.txt`.

## Rust
`cargo test` was run in `/tmp/le-after` with `CARGO_TARGET_DIR=/tmp/le-target`. `cargo test scores` matches no test (0 run). `cargo test league` passed 15 of 15, including `error_rates_come_from_the_score_shards_of_valid_matches`. No binary was installed.

## Untouched
- The timer and `update.sh` were not started.
- Nothing was committed or pushed.
- `~/.local/state/bg-site` was only read and copied.
- v3.db was only opened read-only.

## 5. Summary of the check

- **Published site:** AFTER is identical to the 15:35 live BASELINE for every setup's numbers and for every league table and standings order. Only the timestamps differ, and the share images are renamed because they print the time.
- **BEFORE also equals BASELINE today**, but only by luck. In BEFORE the leak changes the internal tiebreak rates (table above: GNUbg weak 25.41 against 25.47 without the late-entry games; GPT-6 Astra (on) 11.69 against 11.50; GPT-6 Astra (off) 11.20 against 11.28). No shown table currently has rows level on points, games won and games lost, so no place moved. With the filter, those rates equal the rates over matches before #758, and the late entry has no rate on the dashboard.
- **Original-league tables and Cup roster inputs:** `tools/original_league.py tables` and `cup` produce identical output before and after.

## 6. Where the late entry appears

**Nowhere on the site**, before or after. A search for "Astra (high)", "astra-high" and "late-entry" over every built file (gzip files decompressed) found nothing. **Proposal:** keep it off the site unless you ask for it. Its own results (match scores against each of the 12 setups, entry date 2026-10-28, its error rate over its own 12 matches only) go in a separate "late entries" section of the original-league report in `mailbox/`, computed by `tools/original_league.py` from the late-entry matches only. That section is not added to any other setup's row.

## 7. To apply after your confirmation

1. Commit the diff (`tools/league_web.py`, `tools/site/snapshot.py`, `tools/site/score_plays.py` docstring, `src/scores.rs`, `tools/ladder.py`, `tools/original_league.py`, docs).
2. Rebuild the runner binaries that compute error rates. Do it between jobs; the running hidden league uses `target/knockout`.
3. Start the timer again (`systemctl --user start bg-site-preview.timer`).
4. After the first deploy, compare the live data with this AFTER build.
