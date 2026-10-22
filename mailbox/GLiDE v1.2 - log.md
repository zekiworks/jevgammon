# Fastino GLiDE v1.2 (local): log

Oct 22, 2026 · new League 1 player "Fastino GLiDE v1.2 (local)". The existing "Fastino GLiDE" (Fastino's API) is unchanged.

**Status: League 1 is paused (Can, 17:22 UTC). The new player has played 1 of its 18 matches.** The resume steps are in `AFTER_MORNING.md`, section "Resume League 1".

## Licence

From the `LICENSE` file of `fastino/GLiDE` ("Fastino Community License", © 2026 Fastino Inc.):

> Permission is hereby granted, free of charge, to any person obtaining a copy of the GLiDE model, including its weights and associated software and documentation (the "Software"), to deal in the Software, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or provide copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions: […]

> 6b. "Production" means any deployment of the Software or a Derivative Work that serves end users, customers, or employees, or supports business operations, […] **Production does not include evaluation, testing, benchmarking, or research**, or a pilot lasting no more than ninety (90) days that does not serve paying customers.

What the conditions mean for us:
- Section 2 (a commercial agreement for revenue over $10M) applies only to Production with Commercial Use. Benchmarking is excluded from Production by 6b.
- Section 4 ("Built with Fastino GLiDE") applies to Commercial Use; ours is not.
- Section 1 (keep the notices) applies to copies we distribute; we don't redistribute the weights.
- **So benchmarking it and publishing the results are allowed.**

One caveat: the model card's overview says "Internal use only." The licence grants the rights above and does not say that. I went by the licence; Can may want to know about the sentence.

The Qwen3.8-27B parts stay under Apache 2.0 (copy in `licenses/`).

## Access and setup

- **Access:** our Hugging Face token (user perreal, read role) downloads it. The API reports the repo as not gated and not private. Revision `main` = **`a7e45896be7c96ba3354891da790c5ec99c30b6c`** (last modified 2026-10-22 16:23 UTC).
- **Weights:** 52.2 GB (49 GiB), downloaded in 55 s to `~/.cache/huggingface/hub/models--fastino--GLiDE`. The card's banner was skipped.
- **Code review:** I read `glide/server.py`, `model.py`, `prompt.py` and `images.py` in full. They contain no subprocess, eval/exec, pickle or telemetry. Hub access happens only when the model path is not a local directory; ours is local, and the unit runs with `HF_HUB_OFFLINE=1`. Request contents are not logged.
- **Environment:** `~/code/glide/.venv`, built from the snapshot's `requirements.txt` on uv's Python 3.12.13: torch 2.14.0+cu130, transformers 5.17.0, flash-linear-attention 0.5.2, fastapi 0.142.2, uvicorn 0.54.0.
- **Server:** `tools/v3/servers/glide-v12.sh download|setup|start|stop|status|probe` (`GLIDE_GPU` required).
  - Unit `v3-glide-v12`, `127.0.0.1:18101`, served name `glide-v1.2`.
  - `GLIDE_MAX_BATCH=1`, so an answer never depends on other traffic.
  - `TRITON_CACHE_DIR=~/code/glide/triton-cache` (persistent).
  - Loaded in 20 s on bariton GPU 0 and used 53.6 GiB.
- **Check against the card:** its curl example gives the card's numbers exactly: resend 0.3044, refund 0.0095, investigate 0.6861; urgent 0.9917.

## Version question: what does Fastino's API serve?

- **Today:** one request to `POST https://api.fastino.ai/v1/systemone` with model `fastino/GLiDE` (22 Oct 16:51 UTC) answered `"model": "glide_v2"` (header `x-fastino-served-model: fastino/GLiDE`). That is not the `glide-v1.2` that the local weights report.
- **League 1's "Fastino GLiDE":** every stored exchange of its 17 matches names the model `glide_v2`. That is 1,992 exchanges, 0 without a response (read-only query on `v3.db`). The 16 matches of 20 Oct 05:02–05:16 UTC and the one of 20:36–20:41 UTC all say the same. So one label played them all, the same label the API returns today.
- **How close the two are:**
  - On the 50 smoke positions the same day, the API and the local v1.2 chose the same play 48/50 times, with a largest probability gap of 0.022.
  - On the card's example, the API gives 0.283 / 0.009 / 0.708 against the weights' 0.304 / 0.009 / 0.686.
  - That is close, but not bit-identical. `glide_v2` may be the same model on other hardware or batching, or a nearby version. [INFERENCE] Fastino publishes no mapping between the two names.
- The two League 1 players are therefore kept apart: "Fastino GLiDE" (API, `glide_v2`) and "Fastino GLiDE v1.2 (local)" (released weights at `a7e45896`, our GPU). Version, revision and hardware are in the new player's roster `note` and `device`. The site metadata now shows `glide_v2` for the API player (`tools/site/content/setups.json`, `tools/v3/page_v3.py`).

## Smoke test (50 positions)

Command: `jevgammon ask --config leagues/smoke-glide-v12.json --positions positions/smoke.jsonl --out smoke/glide-v12.db --time-limit 600`. No earlier GLiDE smoke answers existed in `smoke/l1-new.db` or `part-a.db`, so the API answered the same positions too. Rows were added to `mailbox/Part A smoke tests - results.md` (table and item 8).

| Setup | Answers / failed / timed out | Invalid | p50 / p90 s | Error rate [95% CI] | Δ vs Gemini 3.8 Flash (low) today | Δ vs Oct 14 | Δ vs Fastino API |
|---|---|---|---|---|---|---|---|
| Fastino GLiDE v1.2 (local) | 50 / 0 / 0 | 0% | 2.7 / 9.1 (fresh process, Triton compiling) | 22.5 [10.6, 37.5] | +9.0 [−5.1, +24.6] | +14.0 [+4.1, +27.9] | **+2.5 [−0.2, +7.9]** |
| Fastino GLiDE (API, `glide_v2`) | 50 / 0 / 0 | 0% | 0.7 / 0.8 | 20.0 [8.9, 34.0] | +6.4 [−6.8, +21.2] | +11.5 [+2.9, +24.5] | reference |

Same play on 48 of 50 positions. Probability gap: max 0.022, median 0.007 (largest gap within each position).

## League 1

- **GPUs:** compactor released bariton GPUs 0, 1 and 3 at 17:12 UTC.
  - GPU 0: GLiDE v1.2.
  - GPU 3: Open-Jev 27B v1.1.
  - GPU 1: Decider v1.2 27B, Decider Flash v1.2 and Winnow-12B (73.5 GiB).
- **Sparks:** Clef and Cygnet on spark, Decider v1.1 on spark3. Same scripts as before, without spark3's Gemma, which League 1 no longer needs. All probes answered.
- **Joining:** `league-add` at 17:16 UTC gave 18 fixtures on matchday 24, logged in `freeze/league1-additions.json`, with the entry also in `leagues/league1.json`. The league resumed at 17:16:32 under unit `league1` (`run_league1.sh`).
- **Paused at 17:22 UTC** on Can's request (Main sent SIGINT).
  - Finished: Fastino GLiDE v1.2 (local) v SubQ Snap Preview, **2–4** (SubQ wins).
  - Started, resume from the last stored turn:
    - v Open-Jev 27B v1.1: 4–1 for GLiDE v1.2
    - v Decider v1.1 27B: 3–0
    - v Clef: 0–1
    - v Cygnet: 0–0
  - Not started: 13.
  - Stored decisions: 322, all answered by `glide-v1.2`, none failed, mean 2.1 s per decision (cold kernel cache, 4 matches at once).
- **Servers:** stopped at 17:22 UTC (bariton). Release posted on the bus at 17:23 UTC. The Spark servers are left running for the resume.
- **Final standings:** not yet; League 1 finishes with 19 entrants (16 models + 3 programs) and 189 matches once the 17 remaining matches are played.

## Timeline (UTC, 22 Oct)

- ~16:49: licence and model card read; access check passed; download done (55 s).
- 16:51: Fastino API version check (`glide_v2`); claim posted to compactor for GPUs 0, 1, 3.
- ~16:55: venv built. API smoke answers: 50/50 in 8 s.
- ~17:00–17:07: Spark servers started (Cygnet, Clef, Decider v1.1; 6.5 min).
- 17:12: compactor's release.
- 17:13: GLiDE v1.2 up on GPU 0 (20 s); card example reproduced.
- 17:14–17:15: local smoke 50/50 in 52 s. Open-Jev, Decider v1.2 27B/Flash and Winnow up.
- 17:16: `league-add`, League 1 resumed.
- 17:22: League 1 paused (Can). Bariton servers stopped; release posted at 17:23.
- 17:24: pages refreshed (`v3-page-refresh.service`); the public page (https://zekiworks.github.io/analysis/backgammon/) lists the new player and its matches.

## Files

- `tools/v3/servers/glide-v12.sh` (+ README rows)
- `leagues/smoke-glide-v12.json`
- `leagues/league1.json` (new entry)
- `freeze/league1-additions.json`
- `tools/site/content/setups.json` and `tools/v3/page_v3.py` (new player; API player labelled `glide_v2`)
- `AFTER_MORNING.md` (resume steps)
- Answers: `smoke/glide-v12.db`, `smoke/glide-v12.json` (git-ignored)
