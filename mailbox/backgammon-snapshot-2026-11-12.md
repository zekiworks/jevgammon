# Backgammon snapshot, 10-12 Nov 2026 (as of 2026-11-12 ~10:30 UTC)

For Ümit (Zeki #5220, #5232). Read only: v3.db, systemd units, mailbox status files, `improve.py status`, bus reservations, live site + bench-scores.json (09:50Z). JSON twin: `backgammon-snapshot-2026-11-12.json`.

- Late entries play the original League 1 table: 19 pairs = 10 programs + API opponents (first stage, incl. Mercury Decide) + 8 local opponents (local stage) + GPT-6 Luna.
- **GPT-6 Luna and Mercury Decide pairs: not required (Ümit #5220).** Not missing work, never a score; past results kept. So the first stage is n/9, the full entry n/17.
- 'held' = built but not shown on the site until complete (held_setups.json). Site wording for Luna/Mercury: branch `scope-luna-mercury` (not merged).

| Model / setup (exact name) | List | Status | First stage: programs + API (n/N) | Local stage: 8 local opponents | E1 200 positions | Learning lane | Live? | Handoff / next step |
|---|---|---|---|---|---|---|---|---|
| **Ümit #4577: decision-model queue** | | | | | | | | |
| KnowLine 31B Gen1.5 | #4577 | done | 9/9 (L21 #937-#945; #933-#936 voided) | 8/8 (#947-#954) | not asked | n/a (decision model) | live | none |
| KnowLine 4B Gen5.5 | #4577 | queued | 9/9 (L22 #957-#965) | 0/8 queued | n/a | n/a | held | local stage: reload its SGLang server on spark2 (spark2 GPU0 = logic hold r_cf95c9e58f42 (to 13 Nov 14:03Z), servers handed in turn); needs a free bariton card for the 8 local opponents (jevgammon) |
| Sieve 31B v3 | #4577 | queued | not started | not started | n/a | n/a | no | after the tiny batch on spark2 GPU0 = logic hold r_cf95c9e58f42 (to 13 Nov 14:03Z), servers handed in turn; no backgammon route built |
| Turion Jev 31B | #4577 | queued | not started | not started | n/a | n/a | no | after Sieve on spark2 GPU0 = logic hold r_cf95c9e58f42 (to 13 Nov 14:03Z), servers handed in turn |
| StartLux-Decision v1.1 4B | #4577 | queued | not started | not started | n/a | n/a | no | 'if machines are free' (#4577); after Turion |
| Cerno 9B v1.2 | #4577 | queued | not started | not started | n/a | n/a | no | 'if machines are free'; needs a wrapper server (no HTTP server shipped) |
| **Ümit #4578: tiny batch** | | | | | | | | |
| GLiDE 0.4B | #4578 (1) | queued | not started (prepared, late-tiny8 e4ce0e9) | not started | n/a | n/a | held | start after GLiClass (spark2 GPU0 = logic hold r_cf95c9e58f42 (to 13 Nov 14:03Z), servers handed in turn) |
| GLiDE 0.8B | #4578 (1) | queued | not started (prepared) | not started | n/a | n/a | held | in turn |
| GLiDE 2B | #4578 (1) | queued | not started (prepared) | not started | n/a | n/a | held | in turn |
| Liquid d1-2B | #4578 (1) | queued | not started (not prepared for backgammon) | not started | n/a | n/a | no | prepare a late-tiny8 entry (logic ran it locally on Logic & Math) |
| KnowLine-0.8B-Gen1 | #4578 (2) | queued | 9/9 (L25 #983-#991) | 0/8 queued | n/a | n/a | held | needs a free bariton card for the 8 local opponents (jevgammon) |
| StartLux-Decision-v1.1-0.8B-Instant | #4578 (2) | queued | 9/9 (L27 #1000-#1014) | 0/8 queued | n/a | n/a | held | needs a free bariton card for the 8 local opponents (jevgammon) |
| PKU-KCL-Meteor-0.8B | #4578 (2) | queued | not started (not prepared) | not started | n/a | n/a | no | x86 build on a bariton card (#4592), after the local stages |
| OneJev1.6-0.8B | #4578 (2); #4577 said 'skip' | queued | 9/9 (L30 #1041-#1049) | 0/8 queued | n/a | n/a | held | needs a free bariton card for the 8 local opponents (jevgammon); note #4577 'Skip OneJev1.6-0.8B' vs #4578 list: run on Main's 11 Nov go |
| GLiClass v4 Edge | #4578 (2) | blocked | 3/9 (L36 #1141-#1143); #1144 aborted 08:59Z: server failed 3 health checks | not started | n/a | n/a | held | restart gliclass_server on spark2 :19480 (spark2 GPU0 = logic hold r_cf95c9e58f42 (to 13 Nov 14:03Z), servers handed in turn), resume L36 |
| StartLux-Decision v1.1 2B | #4578 (3) | queued | 9/9 (L23 #970-#978) | 0/8 queued | n/a | n/a | held | local stage: spark2 StartLux server again; needs a free bariton card for the 8 local opponents (jevgammon) |
| KnowLine-2B-Gen1 | #4578 (3) | queued | not started (prepared) | not started | n/a | n/a | held | in turn on spark2 |
| Base Labs joey-1 | #4578 (3) | queued | not started (not prepared) | not started | n/a | n/a | no | amd64 image on a bariton card (#4592) |
| **Small chat models (Zeki #5064/#5071; 12 models, each (off)/(on))** | | | | | | | | |
| LFM3-1.7B (off) | #5064 | queued | not started | not started | n/a | not in a lane | held | in turn, one setup at a time on logic's bariton GPU-7a85a208 servers |
| LFM3-1.7B (on) | #5064 | queued | not started | not started | n/a | not in a lane | held | in turn, one setup at a time on logic's bariton GPU-7a85a208 servers |
| LFM2.5-2.6B (off) | #5064 | queued | 9/9 (L35 #1124-#1132) | 0/8 queued | n/a | not in a lane | held | local stage on our card; server: logic's small_models.py (bariton GPU-7a85a208, logic to 13 Nov 01:07Z) |
| LFM2.5-2.6B (on) | #5064 | queued | not started | not started | n/a | not in a lane | held | in turn, one setup at a time on logic's bariton GPU-7a85a208 servers |
| MiniCPM5-2B (off) | #5064 | queued | not started | not started | n/a | not in a lane | held | in turn, one setup at a time on logic's bariton GPU-7a85a208 servers |
| MiniCPM5-2B (on) | #5064 | queued | not started | not started | n/a | not in a lane | held | in turn, one setup at a time on logic's bariton GPU-7a85a208 servers |
| LFM2.5-8B-A1B (off) | #5064 | queued | not started | not started | n/a | not in a lane | held | in turn, one setup at a time on logic's bariton GPU-7a85a208 servers |
| LFM2.5-8B-A1B (on) | #5064 | queued | not started | not started | n/a | not in a lane | held | in turn, one setup at a time on logic's bariton GPU-7a85a208 servers |
| Gemma 4 E4B (off) | #5064 | running | 9/9 (L37 #1145-#1154, since 10:02Z) | 0/8 queued | n/a | not in a lane | held | jevgammon holds bariton GPU-bee4b5d4 (r_980dca7fec68, to 13:58Z); then local stage |
| Gemma 4 E4B (on) | #5064 | queued | not started | not started | n/a | not in a lane | held | in turn, one setup at a time on logic's bariton GPU-7a85a208 servers |
| Qwen3.5-4B (off) | #5064 | queued | not started | not started | n/a | not in a lane | held | in turn, one setup at a time on logic's bariton GPU-7a85a208 servers |
| Qwen3.5-4B (on) | #5064 | queued | not started | not started | n/a | not in a lane | held | in turn, one setup at a time on logic's bariton GPU-7a85a208 servers |
| Qwen3.5-9B (off) | #5064 | queued | not started | not started | n/a | not in a lane | held | in turn, one setup at a time on logic's bariton GPU-7a85a208 servers |
| Qwen3.5-9B (on) | #5064 | queued | not started | not started | n/a | not in a lane | held | in turn, one setup at a time on logic's bariton GPU-7a85a208 servers |
| Spark-X2.6-4B (off) | #5071 | queued | not started | not started | n/a | not in a lane | held | in turn, one setup at a time on logic's bariton GPU-7a85a208 servers |
| Spark-X2.6-4B (on) | #5071 | queued | not started | not started | n/a | not in a lane | held | in turn, one setup at a time on logic's bariton GPU-7a85a208 servers |
| Granite-4.2-3B (off) | #5071 | queued | not started | not started | n/a | not in a lane | held | in turn, one setup at a time on logic's bariton GPU-7a85a208 servers |
| Granite-4.2-3B (on) | #5071 | queued | not started | not started | n/a | not in a lane | held | in turn, one setup at a time on logic's bariton GPU-7a85a208 servers |
| Granite-4.2-8B (off) | #5071 | queued | not started | not started | n/a | not in a lane | held | in turn, one setup at a time on logic's bariton GPU-7a85a208 servers |
| Granite-4.2-8B (on) | #5071 | queued | not started | not started | n/a | not in a lane | held | in turn, one setup at a time on logic's bariton GPU-7a85a208 servers |
| Granite-4.2-30B (off) | #5071 | queued | not started | not started | n/a | not in a lane | held | in turn, one setup at a time on logic's bariton GPU-7a85a208 servers |
| Granite-4.2-30B (on) | #5071 | queued | not started | not started | n/a | not in a lane | held | in turn, one setup at a time on logic's bariton GPU-7a85a208 servers |
| LFM2.5-24B-A2B (on) | #5064 | done (backgammon) | 19/19 league (earlier) | done | not asked | queued: lane 3 after Qwen3.8-27B | live | learning lane: jevgammon bariton GPU-e4f2a538 (r_355c890cc9ab, to 12 Nov 13:09Z: renew) |
| **Other authorized backgammon work** | | | | | | | | |
| Muse Ember (max) | Can #4144 | done | 9/9 | 8/8 (L20, 17/19 total #923-#982) | done: ember-E1-20261112T0237Z, 88/200 best, tier 1 | not in a lane | live | none |
| Gemini Decision 1 | Ümit/Can #4966 | done | 9/9 | 8/8 (L26, 17/19 #993-#1063) | not asked | n/a | live | none |
| Claude Opus 5.5 (high) | same positions | done | n/a | n/a | done 200/200, tier 1 | done 5/5 series | live | none |
| Claude Sonnet 5.5 (high) | same positions | done | n/a | n/a | done 200/200, tier 1 | done 5/5 series | live | none |
| **Repeats (6)** | | | | | | | | |
| Liquid d1-ultra [repeat 1] | repeats #4663/#4838 | done | 16/16 (of 18) (L28, run repeat-2026-11-11-d1-ultra-r1) | incl. | n/a | n/a | live (Experiments, Complete) | none; logic's REAX server r_da26c4c4f4f0 can be released |
| Drex Max 1.1 [repeat 1] | repeats #4663/#4838 | done | 17/17 (of 19) (L29, run repeat-2026-11-11-drex-max-1.1-r1) | incl. | n/a | n/a | live (Experiments, Complete) | none; logic's REAX server r_da26c4c4f4f0 can be released |
| Base Labs Mammoth-1 [repeat 1] | repeats #4663/#4838 | done | 17/17 (of 19) (L31, run repeat-2026-11-11-mammoth-1-r1) | incl. | n/a | n/a | live (Experiments, Complete) | none; logic's REAX server r_da26c4c4f4f0 can be released |
| Drex Max v1 [repeat 1] | repeats #4663/#4838 | done | 17/17 (of 19) (L32, run repeat-2026-11-11-drex-max-v1-r1) | incl. | n/a | n/a | live (Experiments, Complete) | none; logic's REAX server r_da26c4c4f4f0 can be released |
| Fastino GLiDE v1.2 (local) [repeat 1] | repeats #4663/#4838 | done | 16/16 (of 18) (L33, run repeat-2026-11-11-glide-v1.2-r1) | incl. | n/a | n/a | live (Experiments, Complete) | none; logic's REAX server r_da26c4c4f4f0 can be released |
| REAX 1.3 [repeat 1] | repeats #4663 | done | 17/17 (L34, run repeat-2026-11-11-reax-1.3-r1); original 18/19 (Luna never played), 17 matched (#5201) | incl. | n/a | n/a | live (Complete) | close L24 (first try, 0 own matches, still 'running') |
| **Learning lanes ('Did they improve?', 15 chat models; done = Opus/Sonnet above too)** | | | | | | | | |
| Qwen3.8 Flash (off) | learning lanes | done | n/a | n/a | done | 5/5 | live | none |
| GLM-5.3 (low) | learning lanes | done | n/a | n/a | done | 5/5 | live | none |
| Kimi K3.1 Pro (off) | learning lanes | done | n/a | n/a | done | 5/5 | live | none |
| DeepSeek-V4.1-Flash (low) | learning lanes | done | n/a | n/a | done | 5/5 | live | none |
| Gemini 3.8 Flash (high) | learning lanes | done | n/a | n/a | done | 5/5 | live | none |
| Gemini 4 Argon (high) | learning lanes | done | n/a | n/a | done | 5/5 | live | none |
| Claude Fable 5.1 (high) | learning lanes | done | n/a | n/a | done | 5/5 | live | none |
| Gemma 4 31B (on) | learning lanes | done | n/a | n/a | done | 5/5 | live | none |
| Grok 4.7 (high) | learning lanes | running | n/a | n/a | done | 3/5, next S4 | live (interim/status) | lane continues |
| Qwen3.8-27B (low) | learning lanes | running | n/a | n/a | done | 3/5, next S4 | live (interim/status) | lane continues |
| GPT-6.1 Sol (high) | learning lanes | queued | n/a | n/a | not asked (quota) | 0/5 | live (interim/status) | ChatGPT quota reset 13 Nov 11:38Z |
| GPT-6 Astra (high) | learning lanes | queued | n/a | n/a | not asked (quota) | 0/5 | live (interim/status) | ChatGPT quota reset 13 Nov 11:38Z |
| Decision-model lane (improve-decision.service) | learning lanes | blocked | n/a | n/a | SubQ Snap 1.1, Drex Max 1.1 done | SubQ both arms + Drex Max 1.1 notes complete | not yet | Drex Max 1.1 worst: Nace subcap $0.36 < $0.88; others wait D5 / local render check |
| **Prepared, not started** | | | | | | | | |
| Gemini 4 Carbon (high) | Ümit via Zeki #4676 | queued | not started (late-carbon-fable 9ed3182) | not started | n/a | n/a | no | explicit approval id (paid); subscription route down since 23:24Z (#5227) |
| Claude Fable 5.2 (max) | Ümit via Zeki #4676 | blocked | not started | not started | n/a | n/a | no | Ümit's decision: max effort gave no answer within 4 x 32,000 (smoke-0004) |

Resources now: spark2 GPU0 logic r_cf95c9e58f42 (Ümit's queue, to 13 Nov 14:03Z); bariton GPU-bee4b5d4 jevgammon r_980dca7fec68 (Gemma 4 E4B serve, to 13:58Z); GPU-7a85a208 logic r_60f5f0a89a09 (small chat servers, to 13 Nov 01:07Z); GPU-e4f2a538 jevgammon r_355c890cc9ab (learning lane 3, ends 13:09Z today); GPU-1115ade0 logic r_da26c4c4f4f0 (REAX server for the finished repeat, to 16:05Z).
