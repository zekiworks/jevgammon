# Nackgammon paired test: late entries, estimate (2026-11-07)

**Total cost for Ümit, 8 setups × at most 1,000 positions: billed $0.36 (at most $0.54); list price $1.16 (at most $1.71).**

Ümit's ask (bus #2627/#2631): add the late entries to the Nackgammon paired test. They take the same paired standard/Nackgammon test and are shown in a separate "Late entries / exploratory" section (Zeki, #2641). **The completed 28 setups' results do not change.** **Estimate only.** No model or API was called, no GPU was used and nothing was spent. The databases were opened read-only (`smoke/nack-paired.db`, `positions/nack-paired/*.jsonl`, `results-2026-10-28/results.json`).

## Who is in

- **In (8):** SubQ Snap 1.1, Base Labs Elephant-1, Base Labs Mammoth-1, Drex Max 1.1, Drex 2.0, Drex Max v1, Drex 2.0 (local), REAX 1.3.
- **Out: GPT-6 Astra (high).** Paid Astra spend is on hold (Zeki). It can get its own estimate later. It is not in any total below.

## Status: exploratory additions (Method §10.14(g), (h))

- They are added after the test's results were computed and read (2026-10-27/28). They are not Cup-roster additions under §10.14(b)/(g), so, as with Gemini 4 Argon (on)/(low) under (g)/(h), they **belong to no group**:
  - they enter no primary comparison;
  - M stays 5;
  - the frozen results (`results/`) and the 2026-10-28 additions results (`results-2026-10-28/`) stay unchanged.
- **Same rules and scoring as every setup:**
  - the frozen pairs, prompts (`bg-v3-std-notable` / `bg-v3-nack`) and option-order seed;
  - each setup's stored settings;
  - the invalid-answer rule (scores the position's Random error) and the output-limit rule of (h);
  - the stopping rule of §10.8(b): the 400 main positions first, then the 600 reserve when the first look calls for it.
- **Reported per setup:** first look, final look, label and sensitivity checks, as in the additions table. Each row is labelled "exploratory, added after results" and carries the timing caveat. A dated section goes in `mailbox/Nackgammon paired test - results.md`, and the output goes to a new results directory. Nothing is published without a go.

## Positions and requests

- **Positions per setup:**
  - start: 400 (200 main pairs: 200 standard + 200 Nackgammon);
  - if extended: +600 reserve (300 pairs), so 1,000 in total (500 standard + 500 Nackgammon).
- **Expect extension.** In the 2026-10-28 results, 29 of 30 setups were extended, including every decision model (for example SubQ Snap Preview's first-look interval was [−18.09, +11.88]). So the budget below uses 1,000 per setup, with the 400-only figure shown.
- **Option caps cost nothing extra here.** The paired positions have at most **25 legal plays** (main and reserve, measured). So no list is split at any cap (25 Drex, 120 Base Labs, 255 SubQ/REAX). **Requests = positions: 1,000 per setup at most**, and 400 if a setup is not extended.
- **Total:** 8 setups × 1,000 = **8,000 requests** (3,200 if none is extended).

## Cost per setup

- **Tokens.** Central: 2,800 input tokens per request, measured on this test's prompts. The decision models in `smoke/nack-paired.db` averaged 2,512–2,809 (SubQ Snap Preview 2,798, Celeris 2,809). Output is not billed by any of these.
- **Upper bound:** each setup's own league $ per 1,000 decisions (`mailbox/Late entries - report 2026-11-06.md`). League lists are longer, so this is a ceiling.
- **Prices:** from the same report (source and date there). REAX has no price (our GPU, no hosted list).

| Setup | Route | Price ($/M input) | List, 400 / 1,000 central | List, 1,000 upper | Billed, 1,000 central / upper |
|---|---|---|---|---|---|
| SubQ Snap 1.1 | SubQ API | $0.04 (billed) | $0.045 / $0.112 | $0.150 | $0.112 / $0.150 |
| Base Labs Elephant-1 | local GPU | $0.035 (Baseten list, not billed) | $0.039 / $0.098 | $0.133 | $0 |
| Base Labs Mammoth-1 | local GPU | $0.10 (Baseten list, not billed) | $0.112 / $0.280 | $0.387 | $0 |
| Drex Max 1.1 | Nace API | list $0.06; billed $0.03 (launch price) | $0.067 / $0.168 | $0.265 | $0.084 / $0.132 |
| Drex 2.0 | Nace API | $0.06 (list = billed) | $0.067 / $0.168 | $0.258 | $0.168 / $0.258 |
| Drex Max v1 | local GPU | $0.06 (hosted list, not billed) | $0.067 / $0.168 | $0.271 | $0 |
| Drex 2.0 (local) | local GPU | $0.06 (hosted list, not billed) | $0.067 / $0.168 | $0.250 | $0 |
| REAX 1.3 | local GPU | none | — | — | $0 |
| **Total** | | | **$0.46 / $1.16** | **$1.71** | **$0.36 / $0.54** |

- **Billed money** goes only to SubQ ($0.11–0.15) and Nace (Drex Max 1.1 + Drex 2.0: $0.25–0.39).
- The Nace pre-send guard and soft stop work as in the Drex late entries. A cap of $0.50 on the Nace requests covers the upper bound.
- No OpenAI, OpenRouter or Antigravity credit is used.

## Time

- **Hosted, request time:** about 0.23 s per request for SubQ and 0.42–0.44 s for Drex (median s per decision in the late entries). 1,000 requests take about 4 min (SubQ) and about 7 min each (Drex Max 1.1, Drex 2.0).
- **Local GPUs: one setup at a time on one 96 GB RTX PRO 6000.** Each fits alone. None fits beside REAX's 62 GB on the same card.
  - **Which card:** arranged through the current GPU owners, with the card named by UUID.
  - **Never index 3 (GPU-e4f2a538, the faulty card)**, even when it looks empty.

  | Setup | VRAM | s per request (late entries) | 1,000 requests | With load (about 2 min) |
  |---|---|---|---|---|
  | Base Labs Elephant-1 | about 26 GB (22.3 GB measured) | 0.26 | about 4 min | about 6 min |
  | Base Labs Mammoth-1 | about 60 GB (57–59 GB measured) | 0.72 | about 12 min | about 14 min |
  | Drex Max v1 | 53 GB | 0.68 | about 11 min | about 13 min |
  | Drex 2.0 (local) | 66 GB | 0.40 | about 7 min | about 9 min |
  | REAX 1.3 | about 62 GB | 2.1 (mean; at most 25 options here, so likely less) | about 35 min | about 37 min |
  | **Total GPU time** | | | | **about 80 min, call it 1.5 h** |

- **REAX:** it runs in its own container with the security exception recorded for its league run (Can, #2199). That exception says it is not to be reused, so REAX's paired run needs Can's OK for the exception again.
- **Wall time:** about 1.5 h on one GPU, with the hosted setups running alongside, plus the scorer below.

## Scorer runs (GNUbg on CPU, no GPU)

- **2-ply scoring: no new GNUbg evaluation.** All 1,000 positions are already scored (`positions/nack-paired/scores-2ply.jsonl`). Each answer is scored by looking it up.
- **Report:** one run of `tools/v3/nack_paired_score.py report`, written to a new results directory. It does per-setup first look → extension decision → final look, and the secondary analyses. CPU, minutes.
- **Engine check (§10.12):** the plays the new setups choose on the 40 frozen pairs and that have no rollout yet are rolled out with the §10.12 settings (GNUbg 1.08.003, 1,296 trials, cubeless, variance reduction, quasi-random dice, 1-ply chequer play, seed 1, 8 threads, nice 19). They are added to a copy of `smoke/nack-engine-check-g.db`, which holds 442 plays.
  - The 2026-10-28 additions needed 6 new plays for 5 setups. So expect roughly 5–15 plays here [INFERENCE].
  - CPU only. The rollouts must not run while another CPU-heavy job is running.
- **Group results are unchanged by construction.** The report also reproduces the frozen results and the 2026-10-28 additions results exactly as a check.

## Totals

- **8 setups:** at most **8,000 requests** (each at most 500 standard + 500 Nackgammon), and 3,200 if none is extended. No list split at any cap.
- **Money billed:** about **$0.36** central and **$0.54** at most (SubQ + Nace).
- **List-price equivalent:** $1.16 central, $1.71 upper (REAX has no price).
- **GPU:** about **1.5 h** on one 96 GB GPU, one setup at a time (largest 66 GB).
- **CPU:** a few rollouts plus one report run.
- **Astra (high):** out (spend on hold).
- **Before any run:**
  - a go from Ümit/Can;
  - a dated §10.14 entry committed before any call;
  - a GPU by UUID from its current owner (never GPU-e4f2a538);
  - Can's OK to reuse the REAX exception.
