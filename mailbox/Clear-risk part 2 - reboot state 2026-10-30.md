# Clear-risk Part 2: state before the bariton reboot (2026-10-30, about 12:10 UTC)

## Live on the site

- **Page:** https://zekiworks.github.io/analysis/backgammon/clear-risk/, labelled Preliminary.
- **Sections:**
  - scan
  - per-setup tables
  - checks 2–4
  - rollout check
  - Part 2
- **Scan as of:** the scan sections are frozen at results 1082e024.
- **Which deploy:** see the last section ("Deploy at …"). It was appended when it happened.

## Answers collected (smoke/clearrisk-q.db; untracked, it survives the reboot)

| model | answer rows | state |
|---|---:|---|
| Celeris-1 Decision, Jev 1.14.0, Liquid d1-ultra | 1,782 each | complete |
| Claude Sonnet 5.5 (high) | 816 | complete |
| Kimi K3.1 Pro (off) | 816 | complete ($1.39 provider-reported) |
| Claude Opus 5.5 (high) (league setup "Claude Opus 5.5 (on)") | 816 | complete ($19.26 API-equivalent) |
| GLM-5.3 (low) (league setup "GLM-5.3 (on)") | 558 of 816 | **stopped by its $3.00 cap** ($3.04 recorded, so the cap was overshot by the requests already running). Not published: pending. Finishing it needs about $1.40 more and a new go (budget). |
| GPT-6.1 Sol (high) | see the last section | it was running on the ChatGPT subscription when this file was written |

## How to resume after the reboot

All commands run from `~/code/jevgammon`. The scratch files are in `/tmp/clearrisk`. **`/tmp` may be wiped by the reboot**,
so check first.

**Files the steps below need**
- `items_chat.jsonl` and `items_decision.jsonl`
- `meta.json`
- `p2rep.py`
- `p2rep_062550.md`, the frozen report
- `all3.json`, the render outputs and `build.py`

**If `/tmp/clearrisk` was wiped**, rebuild the items:
1. Recreate the files with the git-tracked mailbox report and the sample (`mailbox/... sample.csv`).
2. The confirmed ids: rerun `rollrep.py` on `roll_res.jsonl`.
3. Restore the scoring script `p2rep.py` from this commit's copy (`mailbox/clear-risk-part2-tools/`, if it is present).

**Resume a model**, asking only what is missing (the binary is in `target/clearrisk`, built from the uncommitted runner
changes in `src/`):

    set -a; . ~/.keys; set +a
    target/clearrisk/release/jevgammon quiz --config smoke/clearrisk-config.json --items /tmp/clearrisk/items_chat.jsonl \
      --out smoke/clearrisk-q.db --setup "GPT-6.1 Sol (high)" --time-limit 900

- **Sol:** ChatGPT subscription. Check that nothing else uses it first.
- **GLM:** add `--max-cost <new cap>`. The stored cost counts towards the cap.

**Publish**
1. Score the answers:

       cd /tmp/clearrisk && python3 p2rep.py

2. Build the data file:

       cd ~/code/jevgammon && python3 tools/site/clear_risk_publish.py /tmp/clearrisk/p2rep_062550.md \
         --new /tmp/clearrisk/p2rep.md --added "<model>" ...

3. Build the base and candidate sites, then run the invariance check (`/tmp/cr-pub/invariance.py`; it was used for the
   first deploy).
4. Commit `tools/site` only and push.
5. Run `systemctl --user start bg-site-preview.service`.
6. Read the page back with curl.

**Still to write:** the final Part 2 report, `mailbox/Clear-risk follow-up - part 2 2026-10-30.md`.

**Units that stop with the reboot and are not restarted:**
- `clearrisk-part2` (Sol)
- `clearrisk-orwatch`

`season2-resume` waits for the line "Sol ended" in `/tmp/clearrisk/part2.log`. If Sol does not finish, that queue
stays blocked until someone writes the line or restarts Sol.
