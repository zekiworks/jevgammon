#!/usr/bin/env bash
# Overnight 2026-10-19: once Qwen3.8-27B's League 2 matches are played, give its GPU (bariton
# GPU 1) to Decider v1.2 27B and add Decider to League 1 (it passed the 10-position smoke test on
# 2026-10-19; it did not fit next to LFM2.5 bf16, Qwen or Gemma tonight). Run it detached:
#   systemd-run --user --unit=v3-swap-qwen-decider --working-directory=$PWD tools/v3/swap_qwen_decider.sh
# Every 5 minutes it checks League 2: when no Qwen3.8-27B (off)/(on) fixture is left to play
# except against players whose provider matches SKIP_PROVIDER (default openrouter%: OpenRouter
# was out of credit from 2026-10-19 22:26 UTC, so DeepSeek V4.1 Flash (off, on), GLM-5.3 (on) and
# Qwen3.8 Flash (off) cannot play), it stops Qwen's server, starts Decider v1.2 27B on GPU 1,
# checks it answers, backs up v3.db and runs league-add for the "Decider v1.2 27B" entry of
# leagues/league1.json. The running league1 runner picks the matches up within 30 s. Qwen's
# skipped fixtures then wait (backing off) until qwen38-27b.sh runs again. Log: journalctl
# --user -u v3-swap-qwen-decider.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")/../.."
SKIP_PROVIDER=${SKIP_PROVIDER:-openrouter%}

left() {
  sqlite3 -readonly -cmd '.timeout 60000' v3.db "
    SELECT count(*) FROM league_matches lm LEFT JOIN matches m ON m.id = lm.match_id
    WHERE lm.league_id = 2
      AND (lm.model1 LIKE 'Qwen3.8-27B (%' OR lm.model2 LIKE 'Qwen3.8-27B (%')
      AND (m.status IS NULL OR m.status <> 'finished')
      AND NOT EXISTS (
        SELECT 1 FROM leagues l, json_each(l.models) j
        WHERE l.id = 2 AND json_extract(j.value, '$.name') IN (lm.model1, lm.model2)
          AND json_extract(j.value, '$.provider') LIKE '$SKIP_PROVIDER')"
}

# A failed query (empty or non-numeric) counts as fixtures left: only a clean 0 swaps.
while n=$(left 2>&1) || true; [[ $n != 0 ]]; do
  echo "$(date -u +%FT%TZ) Qwen3.8-27B fixtures left to play: $n"
  sleep 300
done
echo "$(date -u +%FT%TZ) Qwen3.8-27B's playable League 2 fixtures are finished; swapping GPU 1"
tools/v3/servers/qwen38-27b.sh stop
DECIDER_V12_GPU=1 tools/v3/servers/decider-v1.2.sh 27b start
tools/v3/servers/decider-v1.2.sh 27b probe
sqlite3 v3.db ".backup v3.db.bak-$(date -u +%Y%m%dT%H%M%S)-before-decider-v12-27b"
./target/release/jevgammon league-add --db v3.db --league 1 --config leagues/league1.json \
  --name "Decider v1.2 27B"
echo "$(date -u +%FT%TZ) Decider v1.2 27B added to League 1 (bariton GPU 1)"
