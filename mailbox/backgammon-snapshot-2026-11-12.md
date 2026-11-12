# Backgammon snapshot, 10-12 Nov 2026 (as of 2026-11-12 ~10:10 UTC)

For Ümit (via Zeki #5220). One row per model or setup worked on since 10 Nov 00:00 UTC. Read only: v3.db (read-only), systemd units, mailbox status files, `improve.py status`, live site and bench-scores.json (updated 2026-11-12T09:50Z).
Late entries play the original League 1 table: 19 pairs. **GPT-6 Luna and Mercury Decide pairs are outside the requested scope (Ümit #5220)**: not missing work, never a score; earlier results kept. "n/19" = finished valid matches.

| Model / setup | Status | Evidence | Live? | Next step / blocker |
|---|---|---|---|---|
| **Late entries** |||||
| Muse Ember (max) | done | L20, 17/19 (#923-#982); #932 Mercury aborted | live (says "Provisional 17 of 19") | none; site wording fix on branch scope-luna-mercury |
| KnowLine-31B-Gen1.5 | done | L21, 17/19 (#937-#954; #933-#936 voided); #946 Mercury | live (says "Provisional 17 of 19") | none; wording fix as above |
| Gemini Decision 1 | done | L26, 17/19 (#993-#1063); #1016 Mercury | live (says "Provisional 17 of 19") | none; wording fix as above |
| KnowLine 4B Gen5.5 | queued | L22, 9/19 (#957-#965), API+programs stage; #966 Mercury | not yet (held) | locals stage: 8 GPU setups, spark2 server reload |
| StartLux-Decision v1.1 2B | queued | L23, 9/19 (#970-#978); #979 Mercury | not yet (held) | locals stage |
| KnowLine-0.8B-Gen1 (tiny) | queued | L25, 9/19 (#983-#991); #992 Mercury | not yet (held) | locals stage (bariton card) |
| StartLux 0.8B Instant (tiny) | queued | L27, 9/19 (#1000-#1014); #1015 Mercury | not yet (held) | locals stage |
| OneJev1.6-0.8B (tiny) | queued | L30, 9/19 (#1041-#1049); #1050 Mercury | not yet (held) | locals stage |
| GLiClass v4 Edge (tiny) | blocked | L36, 3/19 (#1141-#1143); #1144 aborted: server failed 3 health checks 08:59Z | not yet (held) | restart GLiClass server (spark2 :19480), resume L36 |
| KnowLine-2B-Gen1 (tiny) | queued | prepared (late-tiny8 e4ce0e9), no league | not yet (held) | start after GLiClass |
| GLiDE 0.4B (tiny) | queued | prepared, no league | not yet (held) | start in turn |
| GLiDE 0.8B (tiny) | queued | prepared, no league | not yet (held) | start in turn |
| GLiDE 2B (tiny) | queued | prepared, no league | not yet (held) | start in turn |
| **Small chat (11 models, (off)/(on))** |||||
| LFM2.5-2.6B (off) | queued | L35, 9/19 (#1124-#1132); #1123 Mercury | not yet (held) | locals stage, then (on) |
| LFM2.5-2.6B (on) | queued | not started | not yet (held) | after (off) |
| LFM3-1.7B (off)/(on) | queued | not started | not yet (held) | start in turn |
| MiniCPM5-2B (off)/(on) | queued | not started | not yet (held) | start in turn |
| LFM2.5-8B-A1B (off)/(on) | queued | not started | not yet (held) | start in turn |
| Gemma 4 E4B (off)/(on) | queued | not started; server unit smallchat-serve-gemma-4-e4b up, no league | not yet (held) | start its league |
| Qwen3.5-4B (off)/(on) | queued | not started | not yet (held) | start in turn |
| Qwen3.5-9B (off)/(on) | queued | not started | not yet (held) | start in turn |
| Spark-X2.6-4B (off)/(on) | queued | not started | not yet (held) | start in turn |
| Granite-4.2-3B (off)/(on) | queued | not started | not yet (held) | start in turn |
| Granite-4.2-8B (off)/(on) | queued | not started | not yet (held) | start in turn |
| Granite-4.2-30B (off)/(on) | queued | not started | not yet (held) | start in turn |
| **Repeats (6)** |||||
| Liquid d1-ultra r1 | done | L28, 16/16 in-scope (of 18); run repeat-2026-11-11-d1-ultra-r1 | live (Experiments, Complete) | none |
| Drex Max 1.1 r1 | done | L29, 17/17 (of 19); run …-drex-max-1.1-r1 | live (Complete) | none |
| Base Labs Mammoth-1 r1 | done | L31, 17/17 (of 19); run …-mammoth-1-r1 | live (Complete) | none |
| Drex Max v1 r1 | done | L32, 17/17 (of 19); run …-drex-max-v1-r1 | live (Complete) | none |
| Fastino GLiDE v1.2 (local) r1 | done | L33, 16/16 (of 18); run …-glide-v1.2-r1 | live (Complete) | none |
| REAX 1.3 r1 | done | L34, 17/17 (of 19); run …-reax-1.3-r1 | live (Complete) | none; L24 (first try, 0 own matches) still 'running' in DB: close it |
| **Same positions (E1, 200 positions)** |||||
| Muse Ember (max) | done | run ember-E1-20261112T0237Z, 88/200 best, 4 invalid, tier 1 | live | none |
| Claude Opus 5.5 | done | 200/200 answered, tier 1 (15-model table, Holm) | live | none |
| Claude Sonnet 5.5 | done | 200/200 answered, tier 1 | live | none |
| **Learning lanes, "Did they improve?" (15 chat models)** |||||
| Qwen3.8 Flash (off), GLM-5.3, Kimi K3.1 Pro, DeepSeek-V4.1-Flash, Gemini 3.8 Flash, Claude Sonnet 5.5, Claude Opus 5.5, Gemini 4 Argon, Claude Fable 5.1, Gemma 4 31B (10) | done | improve.py: all 8 steps, 5/5 series; billed $78.14 of $110 total | live (verdicts) | none |
| Grok 4.7 | running | 3/5 series, next S4 | live (interim, "pending") | lane continues |
| Qwen3.8-27B | running | 3/5 series, next S4 | live (interim) | lane continues |
| LFM2.5-24B-A2B | queued | 0/5, waiting for its lane turn | live (status only) | after Qwen3.8-27B |
| GPT-6.1 Sol (high) | queued | 0/5 | live (status only) | ChatGPT reset 13 Nov 11:38 UTC |
| GPT-6 Astra (high) | queued | 0/5 | live (status only) | ChatGPT reset 13 Nov 11:38 UTC |
| Decision-model lane (improve-decision.service) | blocked | SubQ Snap 1.1 both arms + Drex Max 1.1 notes complete; rest pending | not yet | Drex Max 1.1 worst: Nace subcap ($0.36 left < $0.88); others: D5 decision / local render check |
| **Prepared, not started** |||||
| Gemini 4 Carbon (high) | queued | late-carbon-fable 9ed3182; nothing started | not yet | explicit approval id to start (paid) |
| Claude Fable 5.2 (max) | blocked | smoke-0004: 4 x 32,000 thinking, no answer | not yet | Ümit's decision on max_tokens/effort |
