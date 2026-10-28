# Late entries on the site: proposal (2026-10-28)

For Can, through Main. **Proposal only. Nothing is committed under `tools/site`, nothing is deployed.** The code is in a detached worktree, `/tmp/late-site` (HEAD `d0200a6`, uncommitted edits). The builds are in `/tmp`. **Deploy only after Can's go, together with the relabel or after it.**

## What it shows and where

**1. Leagues page: a card "Late entries (not in standings)"** (`leagues/#late-entries`). It sits after the three league cards and before "About these tables". It is its own card with its own table, outside every league card, so the late entry is never shown under a standings table.

- Each row is one late entry, with these columns: setup (links to its page, with the badge "Provisional: late entry still playing"), entry date (start of its first late-entry match), league field played ("League 3 (original table)", 12 setups), matches played / total, error rate (PR) with its 95% interval, risk judgement at margin 0.001 with its interval, ability d′ and caution c with their intervals and counts, invalid answers, answers cut off at the output limit, and route and effort sent.
- A short note explains what a late entry is, and a method line says how each number is computed.
- The table's rows carry their own dataset id, `late-entry`. The site's no-mixing check therefore keeps them out of any league's table.

**2. A page for the setup, `models/late-entry/<slug>/`, with a "Late entry, not in standings" note.** The setup has no page today. The page has:
- a header card ("Late entry, not in standings · League 3 field", provisional badge);
- a card titled "Late entry, not in standings" with the same numbers as the Leagues row, plus decisions (scored) and the method line;
- its late-entry matches (opponent, status, score with its own score first);
- links to the Leagues card and to its JSON.

**3. Data:**
- `data/v3/late-entries.json`: every late entry, risk without phases, like a league file.
- `data/v3/late-entries/<slug>.json`: everything, including phases, tags, both margins and the matches.

Both files are in the manifest and on the Data page. `results.json`, `summary.json`, `setups.json` and the league files are unchanged.

**Why there, and not on the models index.** The standings live on the Leagues page. A reader who looks for the late entry next to the League 3 table finds it there, clearly labelled as not in the standings. The models index lists the B7 fields from `content/setups.json`. The late entry has no row there, and adding one would change an existing data file (`data/setups.json`) instead of only adding new ones. Route and effort come from the run itself instead (player settings and the requests sent).

Screenshots (built site served locally from `/tmp/late-site-out`, headless Chromium):
- `/tmp/late-site-shots/leagues-late-entries.png`: the card at 1440 px (the table scrolls sideways, as the other league tables do).
- `/tmp/late-site-shots/leagues-late-entries-right.png`: the same card scrolled to the right-hand columns.
- `/tmp/late-site-shots/leagues-late-entries-full.png`: the whole table in one image (screenshot-only widening, not a site change).
- `/tmp/late-site-shots/leagues-late-entries-light.png`: the card in the light theme.
- `/tmp/late-site-shots/leagues-context.png`: the end of the League 3 card with the late-entry card below it.
- `/tmp/late-site-shots/model-page-late-entry.png`: the setup's page with the note and its matches.

## How it is computed (no new formula)

- **What counts as a late entry:** every setup whose matches carry `matches.stage = 'late-entry'`, read from `league_match_view_all` in `snap.db`. No names are hard-coded.
  - **Entrant of a match:** the setup its league plays only the pairs of (`leagues.only_pairs_of`). Failing that, the side that is in no original-league table.
  - **Field:** the original-league table that holds all of its opponents. Original tables are built with `league_web.league_origins` over the shown leagues, the same rule as `tools/original_league.py`. A tie, for example after its GNUbg weak match only, is broken by the late-entry league's seed, which is the dice of that table.
  - **Total:** the field size without the entrant.
  - **Entry date:** the start of its first late-entry match.
  - A match with no single entrant, or a field that cannot be resolved, stops the build loudly.
- **Numbers:** `analysis.dataset_summary("late-entry", decisions, [name])` is the same per-setup computation a league setup gets: `quality`, `risk` (judgement and SDT d′/c with their bootstrap intervals), `confidence`, and the breakdowns. Its input is the entrant's own decisions in its late-entry matches only. The decision row builder is shared with the league loader (`analysis.decision`, moved out of `load_leagues` unchanged), so both read decisions identically. The bootstrap seeds use the key `late-entry/<name>`, so no other setup's interval moves. Decisions of the running match are included, as in a running league ("Provisional").
- **Cut off at the output limit:** the rule of `tools/v3/nack_paired_score.py` §10.14(h), whose regexes are imported, not copied (`ANY_LIMIT`, `CUT_MARK`, `LETTER_READOUT`, `OUTPUT_LIMIT`).
  - `snapshot.py` reads the exchanges of every late-entry decision in its existing read transaction into a new `snap.db` table, `late_entry_exchanges(turn_id, exchanges, limit_sent, cut_off, efforts)`.
  - An answer is **cut off** when an answering exchange (the one-token letter readout left out) has a stop at the limit in its stored response **or stored error**. The error matters on the Codex route: the runner stores only the parsed answer as the response, and a `response.incomplete` event (reason `max_output_tokens`) ends up in `exchanges.error`.
  - Also counted: decisions that sent an output limit, and answers over 32,768 output tokens from requests that sent none (`turns.output_tokens`; flag only).
  - The rule fires on real data. In these same matches it finds 10 MAX_TOKENS stops by Gemini 4 Argon (on), the opponent. That count is not published, because only the entrant's turns are shown.
- **Route and effort sent:**
  - Route: `players.settings` provider and spec.
  - Effort: the `reasoning.effort` (or `reasoning_effort`) value the request bodies actually carried, counted over the entrant's decisions.
- **Checks (`checks.py`, part of the build):**
  - The late entry's decisions match the snapshot count.
  - Its risk, phase and option cells add up (the same checks a league setup gets).
  - It is in no league's setups or standings; if it ever were, the deploy stops.

## Numbers for GPT-6 Astra (high), as of the build

**Data as of 2026-10-28 17:57 UTC.** The v3.db copy was read at 17:57:32Z and the last stored turn is from 17:53:02Z. **8 of 12 matches had finished, and 1 was running** (v Gemini 4 Argon (on), 0–0 at the copy). The numbers are Provisional.

| | |
|---|---|
| Entry date | 2026-10-28, first match 15:35 UTC (`matches.started_at` 15:35:34Z) |
| League field played | League 3, original table, 12 setups |
| Matches played | 8 / 12 (1 running) |
| Decisions | 1,068, all scored |
| Error rate (PR) | **9.2** (95% interval 7.5 to 11.0), 48 games |
| Risk judgement, margin 0.001 | **73.8** (70.4 to 77.3); at the 0.02 margin 75.2 (71.7 to 78.9), in the data file |
| Ability d′ | **1.82** (1.58 to 2.06); risks taken 194 / 336 Risk pays, needless 23 / 446 Safety pays |
| Caution c | **+0.71** (+0.59 to +0.85), cautious |
| Invalid answers | 0 of 1,068 |
| Cut off at the output limit | **0**. No request sent an output limit (0 of 1,068), and no answer went past 32,768 output tokens. |
| Route and effort sent | `chatgpt-subscription` (Codex backend), `openai/gpt-6-astra`; effort **high** in 1,068 of 1,068 decisions (`"reasoning":{"effort":"high"}`) |

Its matches, its score first:

| Opponent | Score |
|---|---|
| GNUbg weak | 5–0 |
| GPT-6 Astra (off) | 5–2 |
| GPT-6 Astra (on) | 4–3 |
| Gemini 4 Argon (off) | 6–3 |
| Claude Fable 5.1 (off) | 5–1 |
| Claude Fable 5.1 (on) | 0–7 |
| Claude Opus 5.5 (off) | 4–3 |
| Claude Opus 5.5 (on) | 5–5 |
| Gemini 4 Argon (on) | running |

## Kept out of standings, original-league tables, the Cup and other setups (filter unchanged)

- **The filter from 3bf23ba is not touched.**
  - `snapshot.py` still rebuilds `league_match_view` without `stage = 'late-entry'`. Every league table, standings, per-setup number and decision page still reads that view.
  - `league_web.error_rates`, `src/scores.rs`, `ladder.py` and `original_league.py` are not in this diff.
- The late-entry numbers are read from `league_match_view_all` only. They go to their own dataset (`late-entry`), their own data files and their own pages.
- **Original-league tables and Cup:** `tools/original_league.py tables` and `cup` were run from both worktrees on the same v3.db copy, each with its own state's score shards. The outputs are byte-identical (103 and 83 lines). The Cup output still lists "Not eligible: GPT-6 Astra (high) … not in any original-league table yet". Files: `/tmp/late-site-state/ol-{base,new}-{tables,cup}.txt`.

## Verifier result: only additive

Script: `/tmp/late-site-state/verify.py`. Full output: `/tmp/late-site-verify.txt`. It compares `/tmp/late-site-out` (this change) with `/tmp/late-site-base` (HEAD code). The inputs were identical: the same v3.db copy and the same state copy; each build was seeded with the deployed tree (analysis `581c33cd8`) and given the same `snap.db` time.

- **Every data JSON leaf and every decision file was compared:**
  - 2,384 JSON files leaf by leaf (89 under `data/`, 2,294 decision files), 20,154,701 leaves.
  - **No leaf differs except in `data/manifest.json`:** `/results` (`a12573f2` → `1dcadcd1`) and the file list, which gains the two new files. The other 186 differing leaves are the list positions shifted by those two insertions; every existing entry (path, bytes, sha256) is unchanged.
  - **Decision data files: 0 differ.** In `decisions/`, only `decisions/index.html` changed, by the results hash in its version line.
- **Added files:**
  - `data/v3/late-entries.json`
  - `data/v3/late-entries/gpt-6-astra-high.json`
  - `models/late-entry/gpt-6-astra-high/index.html`
  - one redirect for that page in the old preview path
- **Removed files:** none, apart from the three renamed risk cards below.
- **Pages:** 96 pages differ only in the results hash of the version line. Three pages differ in one more way each:
  - `leagues/index.html`: plus the "Late entries" card. After removing that card and the hash, it is identical.
  - `data/index.html`: plus the two file rows.
  - `index.html`: plus the risk-card file names.
- **Risk-call cards:** the three `share/risk-card-league-*.png` files are renamed. Their name hashes the card HTML, whose footer prints the results hash. A pixel diff of each old/new pair is confined to the box (110, 635)–(974, 650): the footer line, nothing else.
- **Why the results hash moves:** it is the sha256 over every data file, so adding the late-entry data files changes it. No other setup's number, standings table, original-league table or Cup input changed.
- The name "GPT-6 Astra (high)" appears in no file of the HEAD build. In this build it appears only in the two new data files, the new page and the new Leagues card.
- **checks.py** (part of the build): **passed** in both builds (exit 0, no `site-check-failures.json`). The only stderr line is the existing `offline.py:213` numpy RuntimeWarning, in both. Build output: base `{"results": "a12573f2", "data_as_of": "2026-10-28T17:57Z", "decision_files": 2298, "scored": {"league-1": 36995, "league-2": 39538, "league-3": 16355}}`; new is the same except `"results": "1dcadcd1"`.

Side effects to know:
- `snapshot.py` now reads the exchanges of the late-entry decisions in every run: 2,896 rows today, both sides. The snapshot took 0.4 s instead of 0.2 s on the copy.
- The numbers check also accepts numbers from the new data files, because the allowed set is the union over `data/`.

## How the builds were made

- **Worktrees** (detached at HEAD `d0200a6`, left in place):
  - `/tmp/late-site`: this change, uncommitted.
  - `/tmp/late-site-basewt`: HEAD, unchanged.
  - Untracked data (top-level entries, `tools/*`, `positions/games`, `positions/nack-paired/{candidates,games}`) is symlinked from the main checkout, as in `/tmp/le-after`. `tools/__pycache__` is not linked.
- **v3.db:** `/tmp/late-site-state/v3.db`, read-only, made by `/tmp/late-site-state/copy_v3.py`. One read transaction (17:57:32Z) copies every table, index, view and trigger. `exchanges` keeps rows from the first late-entry turn (202349) on: 2,896 rows, all the snapshot reads. It has 204,957 turns.
- **State:** `/tmp/late-site-state/{base,new}`, an rsync of `~/.local/state/bg-site` without `analysis/` and `src/`.
- **Steps, per side, with `/usr/bin/python3` (as the timer):**
  1. `snapshot.py` (exit 0; fingerprint `t204957/204957 l1:finished:171/171 l2:finished:171/171 l3:finished:66/66`);
  2. `score.sh` (exit 0; 3 decisions newly scored on each side);
  3. `snap.db` time set to the copy time, 17:57:32Z, so both builds carry the same as-of;
  4. `build.py --state … --out /tmp/late-site-{out,base} --preview-redirects /tmp/late-site-{out,base}-preview`, with the out dirs seeded with the deployed `backgammon/` and `backgammon-preview/`.
- **Not touched:** nothing is committed, pushed or deployed. `update.sh` was not run, the timer was not touched, and `~/.local/state/bg-site` was only copied from. No model calls.

## Files touched (all under `tools/site`, in `/tmp/late-site` only)

- `tools/site/snapshot.py`: new `late_entry_exchanges` table filled in the existing read transaction (`sent_effort`, `late_entry_exchanges`); docstring step 4.
- `tools/site/analysis.py`: `decision()` and `DECISION_COLUMNS` moved out of `load_leagues` unchanged; `original_fields`, `late_entries`; `load_leagues` returns `late_entries`.
- `tools/site/build.py`: late entries through `dataset_summary`; `data/v3/late-entries.json` and per-entrant files; docstring.
- `tools/site/pages.py`: the Leagues card (`late_entries_section`), the setup page (`late_entry_page`), shared cells (`late_cells`), written by `write_all`.
- `tools/site/checks.py`: late-entry counts and "in no league" in `check_counts`; docstring.
- `tools/site/common.py`: `LATE_ENTRY`, `LATE_ENTRY_LABEL`, `LATE_ENTRY_NOTE`.

## Deploy

**Deploy only after Can's go, together with the relabel or after it.** Deploying means committing these six files on main; the timer then builds from the committed tree. On the first run the snapshot adds the `late_entry_exchanges` table. The live site then gets the new card, the new page, the two data files and a new results hash. Nothing else changes.

## Full diff (`git -C /tmp/late-site diff`)

```diff
diff --git a/tools/site/analysis.py b/tools/site/analysis.py
index 3e99ab3..5f80b90 100644
--- a/tools/site/analysis.py
+++ b/tools/site/analysis.py
@@ -34,8 +34,11 @@ from common import EARLIER, PROVISIONAL, PUBLISHED, ROOT, SPEC, THRESHOLDS as T,
 from decisions_export import PAGE_SIZE as DECISION_PAGE
 
 sys.path.insert(0, str(ROOT / "tools"))
-from league_web import (error_rates, last_activity, league_fixtures, league_state, league_table,  # noqa: E402
-                        participants, shown, tiebreak_rates)
+from league_web import (error_rates, last_activity, league_fixtures, league_origins, league_state,  # noqa: E402
+                        league_table, participants, shown, tiebreak_rates)
+
+sys.path.append(str(ROOT / "tools" / "v3"))
+from nack_paired_score import OUTPUT_LIMIT  # noqa: E402
 
 SCALE = T["equity_scale"]
 PHASES = ["opening", "contact", "holding", "race", "bear-off"]
@@ -83,6 +86,38 @@ def decision_from_plays(p: dict) -> dict:
                 gap=(top[0] - top[1]) if len(top) > 1 else None)
 
 
+DECISION_COLUMNS = """t.id, g.id AS game_id, g.match_id, g.round_no, t.decided_by, t.legal_count, t.probability_source,
+    t.probabilities, t.chosen_position, t.option_order, t.request_ms, t.latency_ms, t.retry_ms, t.cost_usd, t.group_size,
+    t.created_at, t.input_tokens, t.output_tokens, t.reasoning_tokens"""
+
+
+def decision(r, plays: dict) -> dict:
+    """One decision (a turns row with DECISION_COLUMNS and `name`) as every measure reads it."""
+    p = plays.get(r["id"])
+    prob = pvec = rank = None
+    if r["probability_source"] in REAL_PROBS and r["probabilities"] and r["chosen_position"] is not None:
+        probs = json.loads(r["probabilities"])
+        if r["chosen_position"] < len(probs):
+            prob = probs[r["chosen_position"]]
+        # The whole vector in legal order, and each legal play's place in the shown order (offline.py).
+        order = json.loads(r["option_order"]) if r["option_order"] else list(range(len(probs)))
+        if not r["group_size"] and len(order) == len(probs) == r["legal_count"]:
+            pvec, rank = [None] * len(order), [0] * len(order)
+            for k, li in enumerate(order):
+                pvec[li], rank[li] = probs[k], k
+    # Block: the two games of a round (seats swapped, same dice) stay together in every resample and split.
+    d = dict(id=r["id"], setup=r["name"], cluster=r["game_id"], match=r["match_id"], invalid=r["decided_by"] == "fallback",
+             block=f'{r["match_id"]}/{r["round_no"]}', pvec=pvec, rank=rank,
+             scored=p is not None, n=r["legal_count"], source=r["probability_source"], p=prob,
+             req_s=(r["request_ms"] if r["request_ms"] is not None else r["latency_ms"]) / 1000,
+             retry_s=(r["retry_ms"] or 0) / 1000, cost=r["cost_usd"], group=r["group_size"],
+             at=r["created_at"], tin=r["input_tokens"], tout=r["output_tokens"], treason=r["reasoning_tokens"])
+    if p is not None:
+        d.update(loss=p["loss"], phase=p["phase"], tag=p["tag"], **decision_from_plays(p))
+        d["chosen"] = p["chosen"]
+    return d
+
+
 def load_leagues(snap: Path, plays_dir: Path) -> dict:
     conn = sqlite3.connect(f"file:{snap}?mode=ro", uri=True)
     conn.row_factory = sqlite3.Row
@@ -109,38 +144,11 @@ def load_leagues(snap: Path, plays_dir: Path) -> dict:
             if f["status"] != "finished":
                 left[f["model1"]] += 1
                 left[f["model2"]] += 1
-        decisions = []
-        for r in conn.execute(
-            """SELECT t.id, g.id AS game_id, g.match_id, g.round_no, CASE t.player WHEN 1 THEN lm.model1 ELSE lm.model2 END AS name,
-                      t.decided_by, t.legal_count, t.probability_source, t.probabilities, t.chosen_position, t.option_order,
-                      t.request_ms, t.latency_ms, t.retry_ms, t.cost_usd, t.group_size, t.created_at,
-                      t.input_tokens, t.output_tokens, t.reasoning_tokens
+        decisions = [decision(r, plays) for r in conn.execute(
+            f"""SELECT {DECISION_COLUMNS}, CASE t.player WHEN 1 THEN lm.model1 ELSE lm.model2 END AS name
                FROM turns t JOIN games g ON g.id = t.game_id JOIN league_match_view lm ON lm.match_id = g.match_id
                WHERE lm.league_id = ? AND t.decided_by IN ('model', 'fallback')
-               ORDER BY lm.label, g.id, t.turn_no""", (lid,)):
-            p = plays.get(r["id"])
-            prob = pvec = rank = None
-            if r["probability_source"] in REAL_PROBS and r["probabilities"] and r["chosen_position"] is not None:
-                probs = json.loads(r["probabilities"])
-                if r["chosen_position"] < len(probs):
-                    prob = probs[r["chosen_position"]]
-                # The whole vector in legal order, and each legal play's place in the shown order (offline.py).
-                order = json.loads(r["option_order"]) if r["option_order"] else list(range(len(probs)))
-                if not r["group_size"] and len(order) == len(probs) == r["legal_count"]:
-                    pvec, rank = [None] * len(order), [0] * len(order)
-                    for k, li in enumerate(order):
-                        pvec[li], rank[li] = probs[k], k
-            # Block: the two games of a round (seats swapped, same dice) stay together in every resample and split.
-            d = dict(id=r["id"], setup=r["name"], cluster=r["game_id"], match=r["match_id"], invalid=r["decided_by"] == "fallback",
-                     block=f'{r["match_id"]}/{r["round_no"]}', pvec=pvec, rank=rank,
-                     scored=p is not None, n=r["legal_count"], source=r["probability_source"], p=prob,
-                     req_s=(r["request_ms"] if r["request_ms"] is not None else r["latency_ms"]) / 1000,
-                     retry_s=(r["retry_ms"] or 0) / 1000, cost=r["cost_usd"], group=r["group_size"],
-                     at=r["created_at"], tin=r["input_tokens"], tout=r["output_tokens"], treason=r["reasoning_tokens"])
-            if p is not None:
-                d.update(loss=p["loss"], phase=p["phase"], tag=p["tag"], **decision_from_plays(p))
-                d["chosen"] = p["chosen"]
-            decisions.append(d)
+               ORDER BY lm.label, g.id, t.turn_no""", (lid,))]
         # Where each match's decisions sit in Every decision: per setup, scored decisions in turn order, 50 a page.
         order = defaultdict(list)
         for d in decisions:
@@ -181,8 +189,90 @@ def load_leagues(snap: Path, plays_dir: Path) -> dict:
             decisions=decisions))
     turns_total = conn.execute("SELECT COUNT(*) FROM turns").fetchone()[0]
     last = conn.execute("SELECT MAX(created_at) FROM turns").fetchone()[0]
+    late = late_entries(conn, plays)
     conn.close()
-    return dict(leagues=leagues, plays=len(plays), turns_total=turns_total, last_move=last)
+    return dict(leagues=leagues, plays=len(plays), turns_total=turns_total, last_move=last, late_entries=late)
+
+
+def original_fields(conn) -> dict[int, set[str]]:
+    """Every shown league's original table: each current member of a shown league counted in the league it played in
+    before any ladder move (league_web.league_origins; a setup in several shown leagues, the anchor, is in each)."""
+    fields = defaultdict(set)
+    for (lid,) in conn.execute(f"SELECT id FROM leagues WHERE {shown(conn)} ORDER BY id").fetchall():
+        for name, origin in league_origins(conn, lid).items():
+            fields[origin].add(name)
+    return dict(fields)
+
+
+def late_entries(conn, plays: dict) -> list[dict]:
+    """Setups that joined an original league table late: every one of their matches carries matches.stage
+    'late-entry' (league_match_view_all; league_match_view leaves them out), each pairs it with one setup of that
+    table, and none counts in any standings table or any other setup's numbers. Per entrant: the setup its late-entry
+    league plays only the pairs of (leagues.only_pairs_of), else the side outside every original table; its field: the
+    original table holding all its opponents (ties broken by the league's seed, the dice of that table); entry: the
+    start of its first late-entry match; its decisions: its own, in its late-entry matches only."""
+    rows = conn.execute(
+        """SELECT DISTINCT lm.match_id, lm.model1, lm.model2, lm.player1, lm.player2, m.status, m.score1, m.score2,
+                  m.started_at, m.finished_at, l.only_pairs_of, l.seed
+           FROM league_match_view_all lm JOIN matches m ON m.id = lm.match_id JOIN leagues l ON l.id = lm.league_id
+           WHERE lm.stage = 'late-entry' ORDER BY m.started_at, lm.match_id""").fetchall()
+    if not rows:
+        return []
+    fields = original_fields(conn)
+    seeds = dict(conn.execute(f"SELECT id, seed FROM leagues WHERE {shown(conn)}").fetchall())
+    in_field = set().union(*fields.values())
+    by = defaultdict(list)
+    for r in rows:
+        if r["only_pairs_of"] in (r["model1"], r["model2"]):
+            name = r["only_pairs_of"]
+        else:
+            outside = [n for n in (r["model1"], r["model2"]) if n not in in_field]
+            if len(outside) != 1:
+                raise RuntimeError(f"late-entry match {r['match_id']}: no single entrant ({r['model1']} v {r['model2']})")
+            name = outside[0]
+        by[name].append(r)
+    out = []
+    for name, ms in by.items():
+        seat = {r["match_id"]: 1 if r["model1"] == name else 2 for r in ms}
+        opponents = {r["model2"] if seat[r["match_id"]] == 1 else r["model1"] for r in ms}
+        cands = [lid for lid, f in sorted(fields.items()) if opponents <= f]
+        if len(cands) > 1:
+            cands = [lid for lid in cands if seeds.get(lid) == ms[0]["seed"]]
+        if len(cands) != 1:
+            raise RuntimeError(f"late entry {name}: no single original table holds its opponents {sorted(opponents)}")
+        field = sorted(fields[cands[0]] - {name})
+        player = ms[0]["player1"] if seat[ms[0]["match_id"]] == 1 else ms[0]["player2"]
+        settings = json.loads(conn.execute("SELECT settings FROM players WHERE id = ?", (player,)).fetchone()[0] or "{}")
+        decisions, flags = [], {}
+        for r in ms:
+            for t in conn.execute(
+                    f"""SELECT {DECISION_COLUMNS}, ? AS name, x.exchanges, x.limit_sent, x.cut_off, x.efforts
+                        FROM turns t JOIN games g ON g.id = t.game_id
+                        LEFT JOIN late_entry_exchanges x ON x.turn_id = t.id
+                        WHERE g.match_id = ? AND t.player = ? AND t.decided_by IN ('model', 'fallback')
+                        ORDER BY g.id, t.turn_no""", (name, r["match_id"], seat[r["match_id"]])):
+                decisions.append(decision(t, plays))
+                flags[t["id"]] = t
+        sent = [x for x in flags.values() if x["exchanges"]]
+        efforts = Counter(e for x in sent for e in json.loads(x["efforts"] or "[]"))
+        out.append(dict(
+            name=name, slug=slug(name), field_league=cands[0], field=field,
+            total=len(field), entry=ms[0]["started_at"],
+            played=sum(r["status"] == "finished" for r in ms), running=sum(r["status"] == "running" for r in ms),
+            matches=[dict(opponent=r["model2"] if seat[r["match_id"]] == 1 else r["model1"], status=r["status"],
+                          score_for=r["score1"] if seat[r["match_id"]] == 1 else r["score2"],
+                          score_against=r["score2"] if seat[r["match_id"]] == 1 else r["score1"],
+                          started=r["started_at"], finished=r["finished_at"]) for r in ms],
+            route=dict(provider=settings.get("provider"), spec=settings.get("spec"), reasoning=settings.get("reasoning")),
+            # Output limit (rule of tools/v3/nack_paired_score.py §10.14(h)): answers stopped at a limit that was sent
+            # (cut off), and answers past OUTPUT_LIMIT tokens from requests that sent no limit (flag only).
+            exchanges=dict(decisions=len(flags), with_exchanges=len(sent), limit_sent=sum(x["limit_sent"] for x in sent),
+                           cut_off=sum(x["cut_off"] for x in sent), output_limit=OUTPUT_LIMIT,
+                           past_limit_no_limit_sent=sum(1 for x in sent if not x["limit_sent"]
+                                                        and (x["output_tokens"] or 0) > OUTPUT_LIMIT),
+                           efforts=dict(sorted(efforts.items()))),
+            decisions=decisions))
+    return out
 
 
 def load_v1(replay_db: Path, v1_positions: Path) -> dict:
diff --git a/tools/site/build.py b/tools/site/build.py
index 4a61f64..17dd7db 100755
--- a/tools/site/build.py
+++ b/tools/site/build.py
@@ -10,10 +10,11 @@ replay.db + positions/v1.jsonl (earlier-version v1 set), positions/*.jsonl + pos
 metadata, human scale, analysis status, method experiments) and the archived sections of the earlier
 page (tools/site/content/archive/).
 
-Output OUT: every page, the data files under data/ (split per version, league and model), the decision
-files under decisions/ and the link preview image under share/. Every number on a page comes from the
-dicts that are also written to data/; tools/site/checks.py then checks the build (numbers trace to
-data files, counts add up, no mixing of leagues or versions, no banned strings, links resolve).
+Output OUT: every page, the data files under data/ (split per version, league and model; late entries, which are
+in no league's tables, in data/v3/late-entries*), the decision files under decisions/ and the link preview image
+under share/. Every number on a page comes from the dicts that are also written to data/; tools/site/checks.py
+then checks the build (numbers trace to data files, counts add up, no mixing of leagues or versions, no banned
+strings, links resolve).
 Exit status 0 = built and checked; 2 = a check failed (details in OUT/../site-check-failures.json).
 """
 
@@ -34,7 +35,7 @@ import checks  # noqa: E402
 import close_choices as CC  # noqa: E402
 import offline as O  # noqa: E402
 import pages  # noqa: E402
-from common import CONTENT, EARLIER, PENDING, PROVISIONAL, PUBLISHED, ROOT, SITE, THRESHOLDS, slug  # noqa: E402
+from common import CONTENT, EARLIER, LATE_ENTRY, PENDING, PROVISIONAL, PUBLISHED, ROOT, SITE, THRESHOLDS, slug  # noqa: E402
 
 BASE = "https://zekiworks.github.io/analysis/backgammon/"
 
@@ -124,6 +125,13 @@ def compute(args) -> dict:
         lg["reasoning"] = league_reasoning(lg, setups, programs)
         # League winners · match results (B4): the league's first place once it finished; never a ranking.
         lg["winner"] = lg["standings"][0]["name"] if lg["state"] == "finished" and lg["standings"] else None
+    # Late entries (analysis.late_entries): the same per-setup computation as a league's, fed with the entrant's own
+    # late-entry decisions only; in no standings table, league table, Cup input or other setup's numbers.
+    late = []
+    for e in L["late_entries"]:
+        decs = e.pop("decisions")
+        late.append(dict(e, status=PUBLISHED if e["played"] == e["total"] else PROVISIONAL,
+                         **A.dataset_summary(LATE_ENTRY, decs, [e["name"]])[e["name"]]))
     return dict(
         as_of=snapshot_time(snap), last_move=L["last_move"], leagues=leagues, setups_meta=setups,
         v1=dict(dataset="v1-set", version="v1", status=EARLIER, positions=len(v1["positions"]),
@@ -132,7 +140,7 @@ def compute(args) -> dict:
                 play_order=dict(setup="Gemini 4 Argon", diff=play_order["diff"], lo=play_order["lo"],
                                 hi=play_order["hi"], positions=play_order["positions"]),
                 disagreements=A.disagreements(v1)),
-        smoke=smoke, shared=shared, thresholds=THRESHOLDS, counts=counts, hypothesis=hypothesis,
+        smoke=smoke, shared=shared, thresholds=THRESHOLDS, counts=counts, hypothesis=hypothesis, late_entries=late,
         close_spec=dict(fixed_on=CC.CC["fixed_on"], definition=CC.DEFINITION, label=CC.LABEL), _close=close_records,
         close_b=json.loads((CONTENT / "close_choices_b_results.json").read_text()),
         status=json.loads((CONTENT / "analysis_status.json").read_text()),
@@ -201,6 +209,14 @@ def write_data(S: dict, out: Path) -> None:
         for n, r in lg["references"].items():
             write_json(out, f"data/v3/{lg['dataset']}/{r['slug']}.json",
                        dict(dataset=lg["dataset"], version="v3", status=lg["metric_status"], **r))
+    # Late entries: one file for all (risk without phases, as in a league file), one per entrant with everything.
+    write_json(out, "data/v3/late-entries.json", dict(
+        version="v3", note="Late entries: not in any standings table, league table or other setup's numbers; each "
+                           "entrant's own late-entry games only.",
+        entries=[dict({k: v for k, v in e.items() if k not in ("risk", "phases", "tags", "options", "gaps",
+                                                                 "quality_phases")}, **brief(e)) for e in S["late_entries"]]))
+    for e in S["late_entries"]:
+        write_json(out, f"data/v3/late-entries/{e['slug']}.json", dict(dataset=LATE_ENTRY, version="v3", **e))
     v1 = S["v1"]
     write_json(out, "data/v1/v1-set.json", dict(
         {k: v for k, v in v1.items() if k not in ("setups", "pairs", "disagreements")},
diff --git a/tools/site/checks.py b/tools/site/checks.py
index 3250c22..0346aa7 100644
--- a/tools/site/checks.py
+++ b/tools/site/checks.py
@@ -7,7 +7,8 @@
 2. Counts add up: per league, setup decisions sum to the league's decisions and match the snapshot; invalid +
    valid = decisions; risk cells and phase cells sum to the scored decisions; standings played = 2 x matches
    finished; the v1 set is setups x positions; exported decisions match the engine-scored decisions; the B6 marks
-   on Every decision match the 2x2 counts.
+   on Every decision match the 2x2 counts; a late entry's decisions match the snapshot, its risk and phase cells
+   add up, and it is in no league's setups or standings.
 3. No mixing: no table holds rows of two datasets; v1 rows only inside an Earlier-version block; every block
    of a league that has not finished says "Provisional: league still running".
 4. No private addresses or credentials (B7): hostnames, IPs, ports, server paths, keys, tokens, request headers,
@@ -24,7 +25,7 @@ from html.parser import HTMLParser
 from pathlib import Path
 
 import findings
-from common import BANNED, CONTENT, PROVISIONAL, PROVISIONAL_NOTE
+from common import BANNED, CONTENT, LATE_ENTRY, PROVISIONAL, PROVISIONAL_NOTE
 
 NUM = re.compile(r"(?<![\w.\u2212+-])([\u2212+-]?)(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?")
 DATE = re.compile(r"\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?Z?)?|\b\d{1,2}:\d{2}\b|"
@@ -171,8 +172,22 @@ def check_counts(S: dict) -> list[str]:
         played = sum(t["played"] for t in lg["standings"])
         if played != 2 * lg["matches_done"]:
             bad.append(f"league {lg['id']}: standings played {played} != 2 x {lg['matches_done']} finished matches")
+    # Late entries: their own decisions add up, and they are in no league's standings or setups.
+    for e in S["late_entries"]:
+        n = snap.execute("""SELECT COUNT(*) FROM turns t JOIN games g ON g.id = t.game_id JOIN matches m ON m.id = g.match_id
+                            JOIN players p ON p.id = CASE t.player WHEN 1 THEN m.player1 ELSE m.player2 END
+                            WHERE m.valid = 1 AND m.stage = 'late-entry' AND p.name = ?
+                              AND t.decided_by IN ('model', 'fallback')""", (e["name"],)).fetchone()[0]
+        if n != e["quality"]["decisions"]:
+            bad.append(f"late entry {e['name']}: snapshot {n}, setup {e['quality']['decisions']} decisions")
+        if e["played"] + e["running"] > e["total"]:
+            bad.append(f"late entry {e['name']}: {e['played'] + e['running']} matches for a field of {e['total']}")
+        for lg in S["leagues"]:
+            if e["name"] in lg["setups"] or any(t["name"] == e["name"] for t in lg["standings"]):
+                bad.append(f"late entry {e['name']} is in league {lg['id']}")
     snap.close()
-    sets = [(lg["dataset"], lg["setups"]) for lg in S["leagues"]] + [("v1-set", S["v1"]["setups"])]
+    sets = ([(lg["dataset"], lg["setups"]) for lg in S["leagues"]] + [(LATE_ENTRY, {e["name"]: e for e in S["late_entries"]})]
+            + [("v1-set", S["v1"]["setups"])])
     for ds, setups in sets:
         for name, s in setups.items():
             q = s["quality"]
diff --git a/tools/site/common.py b/tools/site/common.py
index cf56196..2871299 100644
--- a/tools/site/common.py
+++ b/tools/site/common.py
@@ -18,6 +18,10 @@ PUBLISHED, PROVISIONAL, EARLIER, PENDING, NOT_MEASURED, NA = (
     "Published", "Provisional", "Earlier version", "Analysis pending", "Not measured", "N/A")
 TOO_FEW = "Too few decisions"
 PROVISIONAL_NOTE = "Provisional: league still running"
+# Late entries (matches.stage 'late-entry'): their own dataset id, label and status note; never in a standings table.
+LATE_ENTRY = "late-entry"
+LATE_ENTRY_LABEL = "Late entry, not in standings"
+LATE_ENTRY_NOTE = "Provisional: late entry still playing"
 # Close choices, stage B: scope note (Ümit, 2026-10-25; Method spec 2026-10-24 §9.13 addendum of 16:05 UTC), verbatim on
 # the home page and the Method page.
 CLOSE_B_SCOPE_NOTE = ("Gemma 4 31B (on) was started but not completed: two reboots and a GPU fault interrupted it, and it "
diff --git a/tools/site/pages.py b/tools/site/pages.py
index 0a81da1..1fe991e 100644
--- a/tools/site/pages.py
+++ b/tools/site/pages.py
@@ -5,8 +5,8 @@ import json
 from pathlib import Path
 
 import analysis as A
-from common import (EARLIER, EARLIER_NOTE, NA, NOT_MEASURED, PENDING, PROVISIONAL, PROVISIONAL_NOTE, PUBLISHED,
-                    TOO_FEW, count, esc, fmt, nm, pct, slug, status_badge)
+from common import (EARLIER, EARLIER_NOTE, LATE_ENTRY, LATE_ENTRY_LABEL, LATE_ENTRY_NOTE, NA, NOT_MEASURED, PENDING,
+                    PROVISIONAL, PROVISIONAL_NOTE, PUBLISHED, TOO_FEW, count, esc, fmt, nm, pct, slug, status_badge)
 
 # B4: the nav of decision-models' form; model pages open from the table rows, New models is linked from Data.
 NAV = [("decisions/", "Every decision"), ("disagreements/", "Where models disagree"), ("phases/", "Phases"),
@@ -464,13 +464,111 @@ def leagues_page(S, archive_v1: str) -> str:
                   "merged into one overall score. A running league's numbers are Provisional and change as matches finish. "
                   "Click a row to open the setup, or a match to open its decisions.</p>", "About these tables")
     return (page_head(S, "Leagues", "Leagues")
-            + "".join(blocks) + intro
+            + "".join(blocks) + late_entries_section(S, rel) + intro
             + f'<section class="card" id="earlier"><details class="more"><summary>Earlier version: v1 leagues and teams '
               f'{status_badge(EARLIER)}</summary><p class="note">{esc(play_order_note(S))}</p>{archive_v1}</details>'
               f'<p class="table-note" id="pre-switch">The page as it was before this site went live, with its final league '
               f'data: <a href="../archive/2026-10-23/">archive, 23 October 2026</a>.</p></section>')
 
 
+# --- Late entries -------------------------------------------------------------------------------------------
+
+LATE_ABOUT = ("A late entry joins an original league table after it was played and plays every setup of that table "
+              "once, in matches of its own. Its games count in no standings table, no league table, no Hype Cup input "
+              "and no other setup's numbers. The numbers here come from its own late-entry games only, computed as for "
+              "a setup in a league.")
+LATE_METHOD = ("Error rate and risk judgement: 95% intervals, whole games resampled. Ability d\u2032 and caution c at "
+               "the 0.001 margin: rates corrected by adding 0.5 to the counts and 1 to the totals; 95% intervals, blocks "
+               "of two seat-swapped games resampled. Cut off: answers that stopped at an output limit the request sent "
+               "(finish reason length, stop reason max_tokens, finishReason MAX_TOKENS, incomplete max_output_tokens), "
+               "in the stored response or error. Effort: the reasoning effort the requests sent.")
+
+
+def late_href(rel, e) -> str:
+    return f"{rel}models/{LATE_ENTRY}/{e['slug']}/"
+
+
+def late_status(e) -> str:
+    return status_badge(LATE_ENTRY_NOTE if e["status"] == PROVISIONAL else PUBLISHED)
+
+
+def late_cells(e) -> dict:
+    """The late-entry numbers as cell contents, shared by the Leagues table and the setup's page."""
+    import home
+    q, r, x, route = e["quality"], e["risk"]["main"], e["exchanges"], e["route"]
+    td = lambda cell: cell[16:-5]  # the contents of a <td class="num"> cell
+    effort = "; ".join(f"{esc(k)} in {count(v)} of {count(x['with_exchanges'])} decisions" for k, v in x["efforts"].items())
+    return dict(
+        entry=f'{esc(e["entry"][:10])}<span class="small">first match {esc(e["entry"][11:16])} UTC</span>',
+        field=f'League {e["field_league"]} (original table)<span class="small">{count(e["total"])} setups</span>',
+        played=(f'{count(e["played"])} / {count(e["total"])}<span class="small">'
+                f'{count(e["running"])} running</span>'),
+        error=td(er_cell(q)), judgement=td(home.judgement_td(r)), ability=td(home.ability_td(r)),
+        caution=td(home.caution_td(r)),
+        invalid=f'{count(q["invalid"])}<span class="small">of {count(q["decisions"])} decisions</span>',
+        cut=(f'{count(x["cut_off"])}<span class="small">{count(x["limit_sent"])} of {count(x["with_exchanges"])} '
+             f'decisions sent an output limit; {count(x["past_limit_no_limit_sent"])} over '
+             f'{count(x["output_limit"])} output tokens without one</span>'),
+        route=(f'{esc(route["provider"] or NOT_MEASURED)}<span class="small">{esc(route["spec"] or "")} · effort '
+               f'{effort or nm("not in the requests")}</span>'))
+
+
+LATE_HEAD = ["Setup", "Entry date", "League field played", "Matches played", "Error rate (PR), 95% interval",
+             "Risk judgement, margin 0.001", "Ability d\u2032", "Caution c (+ cautious, \u2212 bold)", "Invalid answers",
+             "Cut off at the output limit", "Route and effort sent"]
+
+
+def late_entries_section(S, rel) -> str:
+    """Leagues page: every late entry in its own table, after the league tables and outside them."""
+    if not S["late_entries"]:
+        return ""
+    rows = []
+    for e in S["late_entries"]:
+        c = late_cells(e)
+        rows.append(f'<tr data-dataset="{LATE_ENTRY}"><td class="model"><a class="model-name" href="{late_href(rel, e)}">'
+                    f'{esc(e["name"])}</a><span class="small">{late_status(e)}</span></td><td>{c["entry"]}</td>'
+                    f'<td>{c["field"]}</td>'
+                    + "".join(f'<td class="num">{c[k]}</td>' for k in ("played", "error", "judgement", "ability", "caution",
+                                                                       "invalid", "cut"))
+                    + f'<td>{c["route"]}</td></tr>')
+    return (f'<section class="card" id="late-entries" data-dataset="{LATE_ENTRY}"><div class="section-head">'
+            f'<h2>Late entries (not in standings)</h2></div><p class="note">{esc(LATE_ABOUT)}</p>'
+            + SWIPE + table(LATE_HEAD, rows, "Late entries: each one's own late-entry games; never ranked",
+                            attrs=f' data-dataset="{LATE_ENTRY}"')
+            + f'<p class="table-note">{esc(LATE_METHOD)}</p></section>')
+
+
+def late_entry_page(S, e) -> str:
+    """The page of a late entry: what it is, the same numbers as its Leagues row, and its matches."""
+    rel = "../../../"
+    c = late_cells(e)
+    q = e["quality"]
+    facts = [("Late entry", f'{esc(LATE_ENTRY_LABEL)}: its games count in no standings table, no league table, no Hype '
+                            f'Cup input and no other setup\'s numbers'),
+             ("Entry date", c["entry"]), ("League field played", c["field"]), ("Matches played", c["played"]),
+             ("Error rate (PR), 95% interval", c["error"]),
+             ("Decisions", f'{count(q["decisions"])} ({count(q["scored"])} scored)'),
+             ("Risk judgement, margin 0.001", c["judgement"]), ("Ability d\u2032", c["ability"]),
+             ("Caution c (+ cautious, \u2212 bold)", c["caution"]), ("Invalid answers", c["invalid"]),
+             ("Cut off at the output limit", c["cut"]), ("Route and effort sent", c["route"])]
+    rows = "".join(f'<tr data-dataset="{LATE_ENTRY}"><td class="model"><span class="model-name">{esc(m["opponent"])}</span></td>'
+                   f'<td>{esc(MATCH_STATE.get(m["status"], m["status"]))}</td>'
+                   f'<td class="num">{m["score_for"]}\u2013{m["score_against"]}</td></tr>' for m in e["matches"])
+    return (f'<section class="card"><p class="eyebrow">{esc(LATE_ENTRY_LABEL)} · League {e["field_league"]} field</p>'
+            f'<h1>{esc(e["name"])}</h1><p class="subtitle">{late_status(e)}</p><p class="version">{esc(version_line(S))}</p></section>'
+            f'<section class="card" id="late-entry" data-dataset="{LATE_ENTRY}"><h2>{esc(LATE_ENTRY_LABEL)}</h2>'
+            f'<p class="note">{esc(LATE_ABOUT)}</p><dl class="facts">'
+            + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in facts)
+            + f'</dl><p class="table-note">{esc(LATE_METHOD)}</p>'
+            f'<p><a href="{rel}leagues/#late-entries">Late entries on the Leagues page</a> · '
+            f'<a href="{rel}data/v3/late-entries/{e["slug"]}.json">JSON</a></p></section>'
+            f'<section class="card" id="late-entry-matches"><h2>Matches</h2>' + SWIPE
+            + table(["Opponent", "Status", "Score"], rows,
+                    f"Late-entry matches of {esc(e['name'])}, its score first; none counts in a standings table",
+                    attrs=f' data-dataset="{LATE_ENTRY}"')
+            + "</section>")
+
+
 # --- Phases -------------------------------------------------------------------------------------------------
 
 def phases_page(S) -> str:
@@ -988,6 +1086,8 @@ def write_all(S, out: Path, base: str) -> None:
             put(f"models/{lg['dataset']}/{meta(S, lg['dataset'], n)['slug']}/", n, model_page(S, lg["dataset"], n, e, None))
     for n, e in S["v1"]["setups"].items():
         put(f"models/v1-set/{meta(S, 'v1-set', n)['slug']}/", f"{n} (v1)", model_page(S, "v1-set", n, e, None))
+    for e in S["late_entries"]:
+        put(late_href("", e), f"{e['name']} (late entry)", late_entry_page(S, e))
     for r in S["smoke"]:
         put(f"models/smoke-part-a/{meta(S, 'smoke-part-a', r['setup'])['slug']}/", r["setup"],
             model_page(S, "smoke-part-a", r["setup"], None, r))
diff --git a/tools/site/snapshot.py b/tools/site/snapshot.py
index b5ba108..e890146 100755
--- a/tools/site/snapshot.py
+++ b/tools/site/snapshot.py
@@ -17,7 +17,11 @@
    once in `contexts`, the turn part in `seen.requests`, and context + separator + text must give
    the original string back exactly. Identical requests of a decision (retries, the steps of a
    two-step reasoning flow) are kept once; group splits keep every distinct request in send order.
-4. Prints one line of JSON: decisions extracted, skipped by reason, contexts, and a fingerprint
+4. Late-entry decisions (matches.stage 'late-entry'): in the same read transaction, the
+   table `late_entry_exchanges` of snap.db gets one row per decision with what its answering
+   exchanges sent and how they ended (output-limit rule of tools/v3/nack_paired_score.py
+   §10.14(h)); the site shows these per late entry, outside every standings table.
+5. Prints one line of JSON: decisions extracted, skipped by reason, contexts, and a fingerprint
    that changes whenever the league data changes.
 
 Schema of prompts.db: see the site contract (local://site-contract.md). Anthropic requests send
@@ -59,6 +63,12 @@ FROM {p}turns t JOIN {p}games g ON g.id = t.game_id JOIN {p}league_match_view lm
 JOIN {p}leagues l ON l.id = lm.league_id
 WHERE t.decided_by IN ('model', 'fallback') AND {shown}
 """
+# Per late-entry decision: answering exchanges (the one-token letter readout left out), whether any sent an output
+# limit, whether any stopped at it, and the reasoning efforts its requests sent.
+LATE_ENTRY_EXCHANGES = """
+CREATE TABLE late_entry_exchanges(turn_id INTEGER PRIMARY KEY, exchanges INTEGER NOT NULL, limit_sent INTEGER NOT NULL,
+    cut_off INTEGER NOT NULL, efforts TEXT)
+"""
 
 
 def shown_leagues(db, prefix=""):
@@ -310,6 +320,49 @@ def batches(listed):
         yield batch
 
 
+def sent_effort(request):
+    """The reasoning effort a request body sent (OpenAI Responses `reasoning.effort`, Chat Completions
+    `reasoning_effort`), or None."""
+    try:
+        body = json.loads(request)
+    except ValueError:
+        return None
+    if not isinstance(body, dict):
+        return None
+    reasoning = body.get("reasoning")
+    return (reasoning.get("effort") if isinstance(reasoning, dict) else None) or body.get("reasoning_effort")
+
+
+def late_entry_exchanges(db):
+    """Fills main.late_entry_exchanges from src.exchanges for every decision of a late-entry match (both sides; the
+    site picks the entrant's). Cut off: a response or stored error with a stop at the output limit (CUT_MARK)."""
+    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "v3"))
+    from nack_paired_score import ANY_LIMIT, CUT_MARK, LETTER_READOUT
+
+    db.execute(LATE_ENTRY_EXCHANGES)
+    turns = """SELECT t.id FROM main.turns t JOIN main.games g ON g.id = t.game_id JOIN main.matches m ON m.id = g.match_id
+               WHERE m.stage = 'late-entry' AND t.decided_by IN ('model', 'fallback')"""
+    first = db.execute(f"SELECT MIN(id) FROM ({turns})").fetchone()[0]
+    if first is None:
+        return
+    rows = {}
+    for turn_id, request, response, error in db.execute(
+            f"SELECT turn_id, request, response, error FROM src.exchanges WHERE turn_id >= ? AND turn_id IN ({turns})"
+            " ORDER BY id", (first,)):
+        if LETTER_READOUT.search(request):
+            continue
+        r = rows.setdefault(turn_id, [0, 0, 0, set()])
+        r[0] += 1
+        r[1] |= bool(ANY_LIMIT.search(request))
+        r[2] |= bool(CUT_MARK.search((response or "") + "\n" + (error or "")))
+        effort = sent_effort(request)
+        if effort:
+            r[3].add(str(effort))
+    db.executemany("INSERT INTO main.late_entry_exchanges VALUES (?, ?, ?, ?, ?)",
+                   [(t, n, limit, cut, json.dumps(sorted(eff)) if eff else None)
+                    for t, (n, limit, cut, eff) in sorted(rows.items())])
+
+
 def run(v3, state):
     started = time.monotonic()
     os.makedirs(state, exist_ok=True)
@@ -349,6 +402,7 @@ def run(v3, state):
             db.execute("CREATE VIEW league_match_view_all AS" + sql[len(head):])
             sql = "CREATE VIEW league_match_view AS SELECT * FROM league_match_view_all WHERE stage <> 'late-entry'"
         db.execute(sql)
+    late_entry_exchanges(db)
     engines = engine_setups(db, "main.")
     targets = {}
     for turn_id, league_id, setup in db.execute(LEAGUE_DECISIONS.format(p="main.", shown=shown_leagues(db, "main."))):
```
