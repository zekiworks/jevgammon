# Participants migration: check

Oct 23, 2026 · v3.db moved to the "participants" storage layout (commit 91b6016 on main). Nothing was played.

## What was done

1. Rebased the `participants` branch onto main (two conflicts, both in notes: `AFTER_MORNING.md` kept main's text, and `freeze/league2-changes.json` kept main's entries plus the Flash Next withdrawal record). `cargo test`: 57 tests pass.
2. Added the error-rate tiebreak and removed the playoffs. A league ranks by points, then games won, then fewer games lost, then the lower error rate over all of a setup's valid matches (all leagues, ladder and Cup). The error rate uses the site's scores: GNUbg 1.08 2-ply equity loss x 500, decisions with two or more legal plays, invalid answers left out (rule B11), read from the site loop's score shards with no rescoring. Every decision of every valid match is already scored.
3. One result per pair: a pair's valid match now counts in every league that holds both setups, whatever league or format it was played in. This is what lets the ladder reuse stored results.
4. Migrated a copy of v3.db first (`/home/cbasaran/code/ladder-test/`, every table except the exchange bodies, which the migration does not touch), then the real file. Backup: `v3.db.bak-20261023T204046-before-participants` (31.8 GB, `quick_check` ok, 499 matches, 129,332 turns).
5. Deployed: swapped the binary (`cargo build --release` on main), restarted the dashboard (league-web, :8095), and ran the site update loop once, then started its timer again.

## Migration (real v3.db)

```
players: 48 (2 from additions log, 1 from matches, 45 from roster)
league #1: 19 current participants, 5 left (GPT-6 Luna (subscription, choice only), Gemma 4 31B (off), Gemma 4 31B (on), Qwen3.8-27B (off), Qwen3.8-27B (on))
league #2: 17 current participants, 2 left (Qwen3.8 Flash Next (off), Qwen3.8 Flash Next (on))
league #3: 11 current participants, 0 left
matches linked: valid: 362          (171 + 136 + 55: every league match)
matches voided (changes log): 51
matches fixture removed (changes log): 70
matches player left: 12
matches replaced attempt: 4
league #1: identical · league #2: identical · league #3: identical
```

All 499 match rows are kept: the 137 voided ones were already outside every table before. Running `jevgammon migrate` a second time prints "already migrated" and compares the tables again, with the same result (identical). No playoff matches were stored: League 1's stored ranking put Liquid d1-ultra above GNUbg weak on games won (67 against 55), not through a playoff.

## Points and games, old layout against new layout

Every setup in every league has the same matches played, wins, draws, losses, points, games won and lost, and points for and against under both layouts (the migration's own comparison, `jevgammon migrate`). Rows are in the old table's order.

### League 1 (19 setups): identical

| # | Setup | P | W | D | L | Pts old = new | Games won-lost old = new | Points for-against |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Liquid d1-ultra | 18 | 16 | 0 | 2 | 48 = 48 | 67-35 = 67-35 | 90-43 |
| 2 | GNUbg weak | 18 | 16 | 0 | 2 | 48 = 48 | 55-27 = 55-27 | 101-36 |
| 3 | Fastino GLiDE | 18 | 12 | 1 | 5 | 37 = 37 | 57-41 = 57-41 | 77-49 |
| 4 | Decider v1.2 27B | 18 | 12 | 0 | 6 | 36 = 36 | 60-30 = 60-30 | 84-46 |
| 5 | Jev 1.14.0 | 18 | 12 | 0 | 6 | 36 = 36 | 56-38 = 56-38 | 77-52 |
| 6 | Jev 1.13.0 | 18 | 12 | 0 | 6 | 36 = 36 | 53-37 = 53-37 | 81-47 |
| 7 | Cygnet (Gemma 4 12B) | 18 | 11 | 1 | 6 | 34 = 34 | 56-44 = 56-44 | 75-59 |
| 8 | Clef | 18 | 10 | 2 | 6 | 32 = 32 | 46-44 = 46-44 | 69-53 |
| 9 | Celeris-1 Decision | 18 | 9 | 3 | 6 | 30 = 30 | 58-48 = 58-48 | 74-63 |
| 10 | Fastino GLiDE v1.2 (local) | 18 | 10 | 0 | 8 | 30 = 30 | 55-41 = 55-41 | 69-55 |
| 11 | SubQ Snap Preview | 18 | 9 | 1 | 8 | 28 = 28 | 58-44 = 58-44 | 76-58 |
| 12 | GPT-6 Luna | 18 | 9 | 0 | 9 | 27 = 27 | 49-51 = 49-51 | 62-65 |
| 13 | Decider v1.1 27B | 18 | 9 | 0 | 9 | 27 = 27 | 48-50 = 48-50 | 69-60 |
| 14 | Mercury Decide | 18 | 6 | 1 | 11 | 19 = 19 | 39-55 = 39-55 | 51-78 |
| 15 | Winnow-12B | 18 | 4 | 0 | 14 | 12 = 12 | 42-56 = 42-56 | 51-77 |
| 16 | Safest | 18 | 3 | 3 | 12 | 12 = 12 | 40-70 = 40-70 | 50-83 |
| 17 | Open-Jev 27B v1.1 | 18 | 2 | 2 | 14 | 8 = 8 | 31-71 = 31-71 | 38-96 |
| 18 | Decider Flash v1.2 | 18 | 2 | 0 | 16 | 6 = 6 | 28-64 = 28-64 | 36-97 |
| 19 | Random | 18 | 0 | 0 | 18 | 0 = 0 | 6-58 = 6-58 | 6-119 |

### League 2 (17 setups): identical

| # | Setup | P | W | D | L | Pts old = new | Games won-lost old = new | Points for-against |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | GPT-6.1 Sol (low) | 16 | 15 | 0 | 1 | 45 = 45 | 61-27 = 61-27 | 83-31 |
| 2 | Gemma 4 31B (on) | 16 | 12 | 0 | 4 | 36 = 36 | 58-34 = 58-34 | 73-44 |
| 3 | GPT-6.1 Sol (high) | 16 | 12 | 0 | 4 | 36 = 36 | 52-30 = 52-30 | 68-38 |
| 4 | Gemini 3.8 Flash (low) | 16 | 11 | 1 | 4 | 34 = 34 | 50-34 = 50-34 | 74-39 |
| 5 | Claude Sonnet 5.5 (high) | 16 | 11 | 0 | 5 | 33 = 33 | 60-36 = 60-36 | 71-44 |
| 6 | Gemini 3.8 Flash (high) | 16 | 11 | 0 | 5 | 33 = 33 | 55-39 = 55-39 | 68-43 |
| 7 | DeepSeek V4.1 Flash (on) | 16 | 11 | 0 | 5 | 33 = 33 | 53-37 = 53-37 | 73-45 |
| 8 | Claude Sonnet 5.5 (low) | 16 | 10 | 1 | 5 | 31 = 31 | 55-33 = 55-33 | 70-41 |
| 9 | GNUbg weak | 16 | 8 | 0 | 8 | 24 = 24 | 37-37 = 37-37 | 60-53 |
| 10 | Qwen3.8-27B (on) | 16 | 8 | 0 | 8 | 24 = 24 | 36-46 = 36-46 | 50-55 |
| 11 | Gemma 4 31B (off) | 16 | 6 | 1 | 9 | 19 = 19 | 40-42 = 40-42 | 54-55 |
| 12 | GLM-5.3 (on) | 16 | 6 | 0 | 10 | 18 = 18 | 33-51 = 33-51 | 47-67 |
| 13 | Qwen3.8 Flash (off) | 16 | 5 | 0 | 11 | 15 = 15 | 36-54 = 36-54 | 47-75 |
| 14 | DeepSeek V4.1 Flash (off) | 16 | 3 | 1 | 12 | 10 = 10 | 38-56 = 38-56 | 49-75 |
| 15 | Qwen3.8-27B (off) | 16 | 3 | 0 | 13 | 9 = 9 | 29-59 = 29-59 | 32-82 |
| 16 | LFM2.5-24B-A2B (on) | 16 | 2 | 0 | 14 | 6 = 6 | 23-59 = 23-59 | 33-88 |
| 17 | LFM2.5-24B-A2B (off) | 16 | 0 | 0 | 16 | 0 = 0 | 10-52 = 10-52 | 12-89 |

### League 3 (11 setups): identical

| # | Setup | P | W | D | L | Pts old = new | Games won-lost old = new | Points for-against |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | GPT-6 Astra (on) | 10 | 8 | 0 | 2 | 24 = 24 | 33-23 = 33-23 | 43-28 |
| 2 | Claude Fable 5.1 (on) | 10 | 7 | 0 | 3 | 21 = 21 | 33-23 = 33-23 | 46-30 |
| 3 | Claude Opus 5.5 (on) | 10 | 6 | 0 | 4 | 18 = 18 | 37-27 = 37-27 | 45-33 |
| 4 | Gemini 4 Argon (on) | 10 | 5 | 1 | 4 | 16 = 16 | 30-32 = 30-32 | 35-36 |
| 5 | Grok 4.7 (on) | 10 | 5 | 1 | 4 | 16 = 16 | 30-32 = 30-32 | 34-38 |
| 6 | Gemini 4 Argon (off) | 10 | 5 | 1 | 4 | 16 = 16 | 29-37 = 29-37 | 36-40 |
| 7 | GPT-6 Astra (off) | 10 | 4 | 2 | 4 | 14 = 14 | 33-27 = 33-27 | 39-31 |
| 8 | Claude Opus 5.5 (off) | 10 | 4 | 0 | 6 | 12 = 12 | 30-30 = 30-30 | 33-38 |
| 9 | Grok 4.7 (off) | 10 | 3 | 0 | 7 | 9 = 9 | 26-34 = 26-34 | 28-40 |
| 10 | GNUbg weak | 10 | 2 | 2 | 6 | 8 = 8 | 25-37 = 25-37 | 32-48 |
| 11 | Claude Fable 5.1 (off) | 10 | 2 | 1 | 7 | 7 = 7 | 32-36 = 32-36 | 36-45 |

## Order changes caused by the new tiebreak

Only one pair of setups in the three leagues is level on points, games won and games lost, so the error rate decides one place:

| League | Setups level on points and games | Before | After | Error rate (all valid matches) |
| --- | --- | --- | --- | --- |
| League 3 | Gemini 4 Argon (on), Grok 4.7 (on): 16 pts, games 30-32 | shared 4th place ("4. Gemini 4 Argon (on)", "4. Grok 4.7 (on)") | 4. Gemini 4 Argon (on), 5. Grok 4.7 (on) | 12.6 against 15.1 |

- **League 1's top two (48 points each) are not a tiebreak case.** Liquid d1-ultra won 67 games and lost 35, while GNUbg weak won 55 and lost 27, so games won already put Liquid d1-ultra first, as the stored ranking did. Our reply (`backgammon-ladder-cup - response.md`) was wrong to say they were level on games and that GNUbg weak ranks first. The outcome does not change: Liquid d1-ultra is League 1's winner and mover. GNUbg weak would not move anyway, because programs never move.
- The stored rankings were recomputed with `jevgammon rank`. Leagues 1 and 2 are unchanged. League 3's 4th and 5th places changed as shown in the table above, and that is the only change.
- The dashboard table and the site table show the same order as before. Their rows were already listed Gemini 4 Argon (on) above Grok 4.7 (on), because a tie kept the roster order, and the site numbered the places row by row. The dashboard now numbers places from the ranking and shows the error rate in an **Err** column.

## Dashboard and site

- **Dashboard (league-web, :8095):** restarted on the new code. `/` returns 200. `/api/history` lists all three leagues with 171/171, 136/136 and 55/55 matches, and `/api/state` returns each league's full fixture with minutes and s/move per match.
- **Site (update loop, `tools/site/update.sh`):** the loop now reads the new tables. Its snapshot fingerprint did not change (`t129332/129332 l1:finished:171/171 l2:finished:136/136 l3:finished:55/55`), no decision needed scoring, and the build and pre-deploy checks passed. It deployed to the live site (data as of 2026-10-23T20:42Z). Against the previous deploy, only 4 data files differ, and every number is the same:
  - `data/setups.json`: the source note "leagues.models (snapshot of v3.db)" now reads "players.settings (snapshot of v3.db)".
  - `data/v3/league-1.json`: the same 171 matches with the same matchday, scores, games and links. 16 rows are listed in a different order inside their matchday, because League 1's fixture is now derived from its participants instead of read from the old fixture table.
  - `data/manifest.json` and `data/index.html`: the time, the results hash, and the sizes and checksums of the two files above.
- The same comparison was made before deploying, on a copy: the old code on the old layout against the new code on the migrated copy. Both builds passed the checks, with the same differences as above.

## Changed behaviour to know

- **Stored results are reused.** A setup that leaves a league keeps its matches. Its matches stay valid and count wherever the same pair meets again, so a ladder mover plays only the pairs it has never played. The 12 League 1 matches of setups that left before today stay void, as they were before.
- **No playoffs.** The runner's decisive mode is gone. A final ranking waits until every pair has been played, and it uses the error rates that are scored at that moment; the runner says when some decisions are still unscored. `jevgammon rank` ranks a finished league again once they are scored.
- **Hype Cup tie rule** (`tools/ladder.py cup-winner`, README): a level Cup match, stored or new, goes to the setup with the lower error rate in that match. No extra rounds are played. This replaces the "decisive mode" sentence in our reply. Example: stored match #38, Safest against Cygnet (Gemma 4 12B), ended 4-4 and goes to Cygnet (Gemma 4 12B), with an error rate of 37.4 in that match against Safest's 39.9.

