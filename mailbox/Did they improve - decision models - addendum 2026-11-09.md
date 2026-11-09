# Did they improve? Decision models (Part 3): addendum to the pre-registration (2026-11-09)

**This is the pre-registration of Part 3.** It adds to the live plan (`mailbox/Did they improve - plan 2026-11-08.md`, sha256 85a970d09cf1ae40d5567a7540ec0f607133314589119391bd71584b5ef78542) and changes nothing in it for the chat models. It is committed before the first call of Part 3, and the page shows its rule, writer, arms and cohort before that call. The harness (`workspace/improve/decision.py`, branch `improve-decision`) refuses to run an arm unless this file has the sha256 it is bound to. Each arm stores that hash before its first call, and a resume with a different file is refused.

**Results will be published whichever way they go.**

Sources:
- the plan draft, revision 3 (`mailbox/Did they improve - decision-model notes - plan draft 2026-11-09.md`, d7c030e, sha256 da57fb8f…3147), whose decided parts (D3, D4, D7, D9, D10) are carried over here unchanged;
- Zeki #3725 (context guard), #3753 (relaying Ümit's D6 approval) and #3638/#3662/#3664/#3665/#3678/#3685;
- Ümit:
  - #3632 and #3660 (the part and its second arm);
  - #3744 (the cohort), #3746 (Elephant-1 added) and #3758 (native message 1569386902715506699, SubQ Snap 1.1 added: ten models);
  - native message 1569386890212147201 (D6 approved).

Where they differ, the later decision wins. Nothing was called to write this file.

## 1. Question

For each decision model of the cohort (§3), at its leaderboard setting: does it take risks better on the pilot's 200-position test after 10 games against GNUbg weak (GNU Backgammon 1.08 Beginner), with a block of text about its own earlier games in its prompt, than with no block?

There are two arms, each judged on its own:
- **Arm N, helper-written notes → decision player.** After each game a fixed helper model (the writer, §4) reads the decision model's graded game record and writes notes with the pilot's lesson prompt and limits. The page says: *helper-written notes, not self-written learning*.
- **Arm W, worst mistakes (no writer).** After each game a fixed script puts the 5 costliest decisions of this series so far (GNUbg grades) into the prompt as solved examples (§5).

Each arm has **its own games**: same dice schedules, never the other arm's games, decisions or trajectories. Notes and examples reset at the start of every series. Games count nowhere (no league, no leaderboard).

Verdicts are reported **per arm**, under the same rule. Neither arm is picked as "the" result.

## 2. The rule (verbatim from the live plan §2; decided by Ümit, #3060 and #3065)

**Improved** = both of these hold:

1. risks found with lessons (the mean of the 5 tests after game 10) minus risks found with no memory (the mean of the 3 empty runs) is **more than max(range of the model's own 3 empty runs, 5 points)**;
2. right safety with lessons minus right safety with no memory is **≥ −5 points** (right safety drops by no more than 5 points).

- Range = max − min of risks found over the model's 3 empty runs, in percentage points.
- The 5-point floor = 5 of the 100 positions where the risk pays. The Gemma pilot showed about 3 points of drift from re-asking alone.
- **This is an operational threshold, not a statistical test and not statistical evidence.** The page says so.
- Error rate (PR) is shown before and after; it is not part of the rule.

For Part 3, "with lessons" means "with the arm's block" (notes in Arm N, worst mistakes in Arm W). "With no memory" means that arm's own empty runs (§6).

## 3. Cohort (Ümit #3744, #3746 and #3758)

Each row is one model at its leaderboard setup, frozen from `v3.db` `players.settings`: setup name, route, model id sent, request parameters and option cap. The only changes are `name`, `parallel` (never above the league's), the block file, this experiment's budget ledger (never the league's), the route check and the context gate.

The allowed response ids are the ids observed in the league's own replies. There is no successor, alias or substitute (D7). A reply naming another id stops the arm: "not tested: model id not served as on the leaderboard". There is no hosted/local swap.

| Setup (v3.db) | Chosen by | Route | Response id | Delivery evidence | Status before preflight |
|---|---|---|---|---|---|
| REAX 1.3 | Ümit #3744 | local `reax13/serve.py` (reax-engine @ ff8f595) | `reax13` | pending Lr | needs D5 (read-twice → read-once switch); local render check; a GPU |
| Fastino GLiDE v1.2 (local) | Ümit #3744 | local `glide/server.py` | `glide-v1.2` | pending Lr | local render check; a GPU |
| Liquid d1-ultra | Ümit #3744 | `api.liquid.ai/decisions/v1/systemone`, `d1-ultra` | `d1-ultra` | **delivery unverified (our evidence gap)** | selected and shown; **not tested: native context limit unverified** (Zeki #3761; §6.1, §6.2) |
| Drex Max 1.1 | Ümit #3744 | Nace `console.nace.ai/v1/systemone`, `drex-max-v1.1`, 25 options | `drex-max-v1.1` | Hc | P1, then runs; Nace subcap (§7) |
| vLLM-SR d3-ultra | Ümit #3744 | — | — | — | **not started**: added 9 Nov, no league record, no backgammon route yet |
| Base Labs Mammoth-1 | Ümit #3744 | local `baselabs_server.py` (`baselabs-serve:81ce62f`), 120 options | `baselabs/mammoth-1` | pending Lr | needs D5 (both arms past the trained 16,384 tokens); local render check; a GPU |
| Base Labs Elephant-1 | Ümit #3746 | local, as Mammoth-1 | `baselabs/elephant-1` | pending Lr | needs D5 for Arm N (past the trained 16,384 tokens); local render check; a GPU |
| Decider v1.2 27B | Ümit #3744 | local `pplx_decider_server.py` (`decider-v1.2.sh 27b`), 25 options | `pplx-decider-v1.2` | pending Lr | local render check; a GPU |
| Jev 1.14.0 | Ümit #3744 | `api.typesafe.ai/v1/systemone`, `jev-1.14.0` | `jev-1.14.0` | Hc | **not tested: conservative context guard** (§6.2: the guard refuses 1.3% of its league requests even without a block) |
| SubQ Snap 1.1 | Ümit #3758 | `api.subq.ai/v1/systemone`, `subq-snap-1.1` | `subq-snap-1.1` | Hc | P1, then runs |

Every decision model of the leaderboard outside this list is out of scope for Part 3. Its row stays as the live plan states it.

Page notes:
- Base Labs: "runs past the checkpoint's trained 16,384 tokens (the engine refuses above 32,768)".
- REAX: "reads requests of at most 3,000 tokens twice; with a block every request is longer and is read once".

## 4. The writer (Arm N only)

**Qwen3.8 Flash (off) via OpenRouter, pinned once for the whole cohort, no swap mid-cohort.** It is the live plan's Qwen3.8 Flash (off) lesson call, unchanged (improve.py `player_config` of that setup):
- spec `openai-compatible/qwen/qwen3.8-flash`, `https://openrouter.ai/api/v1`;
- request `provider: {order: ["alibaba"], allow_fallbacks: false, require_parameters: true}`, `usage: {include: true}`, `reasoning: {enabled: false}`;
- the runner's output allowance of 32,768 tokens;
- `parallel` 1;
- route check: response `model` ∈ {`qwen/qwen3.8-flash`, `qwen/qwen3.8-flash-20260826`} and provider `Alibaba`; anything else stops the arm.

**Prompt:** the pilot's `lessons_system.txt` + `lessons_user.txt`, byte-identical (sha256 d755001513b60546cbcc4159db0965dbeda09a65d65377d874b22e247f74550e).

**Cut rule (the pilot's):** lines starting `- ` are lessons; at most 5 lessons and 150 words are kept; cuts are counted and shown. The writer's raw reply, the kept notes and the exact block delivered (by sha256) are stored privately. After the cut rule nothing in a block is ever shortened.

**What the writer reads:** the live plan's lesson record (`improve.py` `record_line`, `game_header`, `eligible`) of that model's game in Arm N, scored by GNUbg 1.08 2-ply. Left out:
- forced and impossible moves;
- invalid answers;
- unscored decisions;
- GNUbg's moves;
- the model's probabilities;
- any decision whose `board_key` is among the frozen 200 test positions (test-set sha256 6c92e7416745125ca3ea09c9e41e450a52716f8ad018772278b07f992f7318e6), removed before the record is built, counted and shown.

**The block (Arm N), at the start of `state` (OpenAI: `input`), then a blank line, then the league state unchanged:**

```
=== NOTES FROM YOUR EARLIER GAMES IN THIS SERIES ===
Notes a helper wrote from your earlier games in this series, oldest first:

After game 1:
<kept notes>

…
=== END OF NOTES ===
```

Writer calls are booked in the same ledgers as the players.

## 5. Arm W: the worst-mistakes block (exact)

After game g of a series, a script (no model) builds the block for game g + 1 and, after game 10, for T10.

1. **Eligible decisions:** this arm's own games 1…g of the current series only, model-decided (not forced, not invalid), scored by GNUbg 2-ply. Any decision whose `board_key` is among the 200 frozen test positions is removed **before** selection and counted.
2. **Selection:** largest equity loss first, at full precision. Tie-break: earlier game, then lower turn number, then lower turn id. Losses that print as 0.000 at 3 decimals are not eligible. The first 5 are taken; with fewer than 5 eligible, those; with none, no block (the league request).
3. **Serialization:** board, chosen play, best play and loss only, at the start of `state` (OpenAI: `input`), then a blank line, then the league state unchanged:

```
=== WORST MISTAKES FROM YOUR EARLIER GAMES IN THIS SERIES ===
Your costliest decisions so far in this series, by GNU Backgammon's 2-ply equity loss, largest first:

Example 1 (game 3, turn 17):
<the league prompt's position block for that decision, verbatim: "Position (your numbering; you move 24 -> 1):" … "Dice: a-b">
You played: <play>. GNUbg's best play: <play>. Equity lost: 0.352.

Example 2 (…)
…

=== END OF WORST MISTAKES ===
```

   Plays are in the league option notation. The position block is the runner's own rendering (`jevgammon render`, prompt bg-v2).
4. **Reset** at the start of every series.
5. **Private record:** the selected turn ids per game, their `board_key`s, the scoring file and its sha256, GNUbg 1.08 2-ply. Only aggregates are published.

## 6. Delivery, context and identity

### 6.1 Delivery evidence

- **Local routes (Lr):** a CPU-only render, with the server's own code at its pinned commit, of the final inference input. It is checked on stored league requests with and without a block, including the largest stored request. It passes only if:
  - the block is present in full after the route's declared transformations;
  - the original state, instructions and every option are present in full;
  - no cut path is taken under the server's limits.

  A route whose final input cannot be rendered this way is "delivery unverified" and is not run. No local arm runs before its check passes.
- **Hosted routes, API contract + accounting (Hc):** the maker's docs say the state is what the model reads **and** that oversize input is refused, not cut. The page labels this "delivery: API contract + accounting, not verified end to end". Met for:
  - Jev 1.14.0 (TypeSafe, `400 max_tokens_exceeded`);
  - Drex Max 1.1 (Nace: passed "as is"; "A longer request is refused", `422`);
  - SubQ Snap 1.1 (SubQ: "`state`: the text, object, or array to evaluate"; "A request over the limit, or close to it, fails with `400`", docs.subq.ai/endpoints/decisions-api).
- **Liquid d1-ultra** is selected by Ümit (#3744) and stays visible with **"delivery unverified (our evidence gap)"**. Liquid publishes no limit and no oversize behaviour, so under the per-request guard it cannot pass: **"not tested: native context limit unverified"** (Zeki #3761). There is no route switch and no shortened block. Even OpenRouter's documented 32,768 tokens would not help: the guard would refuse its 61 kB league requests. If Liquid ever ran (a documented limit recorded in the cohort file), its result rows and the method note would carry the delivery flag visibly, P1 would still apply, and nothing on the page would claim delivery.
- **P1 (accounting probe, every hosted row run):** one stored 2-option League request of the setup is sent without and with the largest notes block, and the reported input tokens must rise. It costs under $0.001 per route and is booked. It is accounting evidence only: billing can precede a cut. No arm of a hosted row runs before its P1 passes. No canary.

### 6.2 Context: the conservative guard on every request (Zeki #3725)

- **Hosted routes:** before sending, the runner refuses a request whose upper bound (request body bytes counted as tokens + the documented wrapper allowance, 4,096 tokens where undocumented + the output allowance, 0 here) exceeds the documented limit. With no documented limit it refuses (fails closed). This guard is a heuristic policy, not proof that the whole input is read. It cannot clear a "delivery unverified" route. The service's own documented refusal is the second gate.
- **Local routes:** the server's own pre-inference gate (400/422 before the model runs).
- **Before any paid dispatch:** the guard is run locally on the setup's retained league requests, without a block and with the largest permitted block of each arm:
  - Arm N: 10 games × 5 lessons × 30 words of 12 bytes;
  - Arm W: the 5 largest rendered League position blocks with the longest play notation.

  A setup the guard refuses in that preflight is **"not tested: conservative context guard"** for that arm, or for both arms when it refuses requests with no block.
- **Mid-run:** a guard refusal, or the service's refusal (400/413/422), stops that arm as **"incomplete: conservative context guard"** or **"incomplete: context limit reached"**. Its partial records stay. There is no subset score, no truncation, no shortened block, no dropped option and no other group size. It is never worded as "the model can't".

**Expected feasibility (guard preflight, `decision.py preflight-guard`, v3.db exchanges of each setup's valid league matches):**

| Setup | Retained league requests | Largest (bytes) | Documented limit (tokens) | Refused: no block | Refused: largest notes block (+19,977 bytes) | Refused: largest worst-mistakes block (+2,733 bytes) | Result |
|---|---:|---:|---:|---:|---:|---:|---|
| SubQ Snap 1.1 | 2,330 | 48,274 | 393,216 | 0 (0%) | 0 (0%) | 0 (0%) | both arms run |
| Drex Max 1.1 | 2,734 | 13,823 | 262,144 | 0 (0%) | 0 (0%) | 0 (0%) | both arms run (money: §7) |
| Jev 1.14.0 | 4,888 | 59,869 | 32,000 | 65 (1.3%) | 4,888 (100%) | 81 (1.7%) | **not tested: conservative context guard** (both arms) |
| Liquid d1-ultra | 5,301 | 61,393 | none documented | 5,301 (100%) | 5,301 (100%) | 5,301 (100%) | **not tested: native context limit unverified** (the guard fails closed) |

Block hashes: notes sha256 fd3a5e56a0542247298130e72c51355dfe191420bb39cecd0471d2e8a2e7e0a4, worst mistakes sha256 d77b3076be90076befbfcdb44bd8fc2a17d8ce6f1b53590ed16609bd75d9095e. The worst-mistakes block uses the 5 largest rendered blocks among the 2,000 League positions with the longest checker lists. Local routes are gated by their own servers and checked by the render checks (§6.1).

### 6.3 Identity

The response `model` must be in the frozen list (§3). The writer's `model` and `provider` must be as in §4. Any mismatch stops the arm and is logged with the raw reply.

## 7. Money

- **The $110 total cap and the $5 OpenRouter reserve stay** (live plan §9). Every decision-model ledger counts against the $110: players, writer, P1 probes, retries, and every open reservation at its worst case (request bytes as input tokens + 4,096 tokens on decision routes at list price; the writer's 32,768-token output allowance). A request with no response is booked at its worst case. Billed = max(provider-reported cost, tokens × list price).
- **Rule (a) per arm:** after E1 and S1, a projected cost above 1.5 × the arm's estimate stops that arm.
- **D6 approved** (Ümit, native message 1569386890212147201, relayed by Zeki #3753): hosted spending outside OpenRouter counts within the existing $110 total cap. The $5 OpenRouter reserve and the 1.5× per-model rule are unchanged. The cohort file sets the hosted allowance of TypeSafe, Liquid, Nace and SubQ to "within the $110". A $0 there would refuse every billed call of that provider, P1 included.
- **Nace subcap: $2.50** (raised from $1.25 by the same approval). The league's shared Nace ledger (`workspace/drex/state/nace-budget.db`, $0.7856 settled) still counts, so $1.71 is left. Drex Max 1.1's two arms book about $0.89 + $0.88 at the $0.06 list price; Nace bills its $0.03 launch price. The second arm may therefore stop at the cap, shown as "incomplete".
- **Estimates (booked, separate empty runs, both arms; method of the draft §7):**
  - SubQ Snap 1.1 $0.99;
  - Drex Max 1.1 $1.74;
  - Jev 1.14.0 $1.08 and Liquid d1-ultra $0.94 if they ever run (not tested now: $0);
  - writer: Arm N of each running model ≈ $0.03 each (about $0.21 for the 7 that can run: SubQ, Drex Max 1.1 and the 5 local models);
  - P1 < $0.01 per hosted route.

## 8. Schedule and empty runs

Same as the chat models: 5 series × 10 games against GNUbg weak, the pilot's dice s01–s05 (mirrored pairs), the same 200 test positions, T10 after each series, 3 empty runs, order E1, S1, (cost check), S2, E2, S3, S4, E3, S5. Hosted arms run one at a time. A local model runs only on a card its owner releases, one model per GPU.

## 9. Decisions

- **Decided (from the draft):**
  - D3 placement: start of `state` / `input`;
  - D4 wording: the pilot prompt byte-identical, the intro line above;
  - D7 identity: no successor ids;
  - D9 Arm W content: board, chosen play, best play, loss;
  - D10 delivery evidence classes.
- **Decided by Ümit:** the cohort (#3744, #3746, #3758), including running Liquid d1-ultra with its flag; D6 (native message 1569386890212147201).
- **Proposals pending Ümit (the harness reads them from `workspace/improve/decision_cohort.json`, so an answer changes that file, not the code):**
  - **D1 empty runs:** separate per arm (the proposed default, used unless Ümit changes it; the page says "proposed default, Ümit may change") or shared;
  - **D5 edge settings:** Base Labs past the trained length, REAX's read-once switch; until decided these arms are pending.

**Results will be published whichever way they go.**
