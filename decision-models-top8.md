# Top 8 decision models: setup and use

The eight most accurate decision models on the Turkish TYT bank (`questions-v2.sqlite`, 2,198 scored
questions): how each one is set up, and how the benchmark and a plain `curl` call it. Facts as of
2026-10-08. Commands run from the benchmark folder, `/home/cbasaran/T7/code/data/eval/benchmarks/Turkce`,
unless they `cd` elsewhere. Keys are named here, never written.

## Overview

| # | Model | Maker | Where it runs | `--provider` | Script | Score | Per 1,000 questions | Per question |
|---|---|---|---|---|---|---:|---:|---:|
| 1 | GLiDE | Fastino | Fastino API | `fastino` | `run_glide.sh` | 67.9% | $0.160 | 2.1 s, 4 in flight |
| 2 | GPT-6 Luna, Decisions API (beta) | OpenAI | OpenAI API | `openai-decisions` | `run_openai_decisions.sh` | 63.6% | $0.040 | 0.19 s, 4 in flight |
| 3 | Decider 27B | Perplexity | Perplexity API | `perplexity` | `run_perplexity.sh` | 60.4% | $0.016 | ≈ 0.21 s |
| 4 | Jev 1.13.0 | TypeSafe | TypeSafe API | `jev` | `run_jev.sh` | 57.5% | $0.029 | ≈ 0.24 s |
| 5 | Clef | Cloudflare | our GPU, port 18091 | `clef` | `run_clef.sh` | 57.3% | GPU time only | 0.20 s |
| 6 | d1 | Liquid AI | Liquid AI API | `liquid` | `run_liquid_d1.sh` | 57.0% | free | ≈ 0.40 s |
| 7 | Open-Jev 27B v1.1 | Zefan Cai | our GPU, port 8791 | `open-jev` | `run_open_jev.sh` | 55.7% | GPU time only | ≈ 0.39 s |
| 8 | Cygnet | blockbrain-ai | our GPU, ports 8892 and 18093 | `cygnet` | `run_cygnet.sh` | 55.7% | GPU time only | 0.04 s |

- **Per question:** the median request time where the run recorded it. "≈" marks a mean worked out from
  questions per minute, one request at a time.
- **Ties:** ranks 7 and 8 have the same number of right answers (1,224). Ranks 4–8 share a tied group on
  the leaderboard, so their order is not reliable. GLiDE is ahead of all the others.
- **Reading and grammar:** all eight do far better on reading (83–88%) than on grammar (44–59%).
- **Self-hosted hardware:** one RTX PRO 6000 Blackwell (96 GB) each, BF16.

## What all eight share

- **One question per request**, in TypeSafe's System One format:
  - `state` holds the question as text;
  - one `choice` question named `answer` maps each letter to its option text in `criteria`.

  OpenAI takes the same parts under other names (section 2). `ask_jev()` in `benchmark_ollama.py` builds
  both forms.
- **The `state`** is the text every model in the benchmark gets (`compose_prompt()`), in this order:
  1. the shared passage under `Ortak metin / bağlam:`, when there is one;
  2. the question;
  3. `Seçenekler:`, then one `A. …` line per option.
- **The score** is the chosen option's probability, `probabilities[choice]`. The services' own
  `confidence` field is not used; most compute it as (p_max − 1/K)/(1 − 1/K) over K options.
- **Text only:** questions that need their image are left out for every System One provider, and
  `--batch-size` stays 1.

Example request, with a made-up question that is not from the bank. Save it as `request.json` for the
`curl` lines below. Change `model` for each service; Open-Jev takes no `model` at all.

```json
{
  "model": "pplx-decider-v1-27b",
  "state": "\"Kitabı masanın üstüne dün bıraktım.\" cümlesinin yüklemi hangisidir?\n\nSeçenekler:\nA. Kitabı\nB. masanın\nC. üstüne\nD. dün\nE. bıraktım",
  "questions": {
    "answer": {
      "type": "choice",
      "instructions": "Which option is the correct answer to this Turkish multiple-choice question?",
      "criteria": {"A": "Kitabı", "B": "masanın", "C": "üstüne", "D": "dün", "E": "bıraktım"}
    }
  }
}
```

Perplexity's response to it, rounded here to four decimals:

```json
{"model": "pplx-decider-v1-27b",
 "answers": {"answer": {"type": "choice", "choice": "E", "confidence": 0.9996,
                        "probabilities": {"A": 0.0001, "B": 0.0001, "C": 0.0001, "D": 0.0001, "E": 0.9997}}},
 "usage": {"input_tokens": 169, "output_tokens": 1}}
```

## Running the benchmark

```bash
./run_glide.sh        # each script runs the whole bank
./benchmark_ollama.py <model> --provider <provider> --data questions-v2.sqlite --timeout <seconds> [--concurrency N]
```

- **Where results go:** answers to `benchmark-results.sqlite` (`--database`), the report to
  `benchmark-results.md` (`--output`).
- **Resume:** running the same command again resumes an interrupted run. `--restart` deletes that run's
  stored answers and starts over; don't use it on the real database by accident.
- **Trial run that touches neither file:**

  ```bash
  ./benchmark_ollama.py d1:free --provider liquid --data questions-v2.sqlite --limit 3 --timeout 30 \
    --database /tmp/try.sqlite --output /tmp/try.md
  ```

  `--sample 100 --seed 0` takes a fixed sample spread over the bank instead of the first questions.
- **Other base URL:** `--jev-url URL` sends any of these providers to another host or port.
- **Parallel requests:** `--concurrency N` keeps N requests in flight (default 1).
- **Retries:** HTTP 408, 425, 429 and 5xx answers and network failures are retried up to five times,
  after 1, 2, 4, 8 and 16 s, never sooner than `Retry-After` asks. Any other error stops the run;
  starting it again resumes.
- **Stored per answer:** the full response and, where the service sends one, its request ID.

## 1. GLiDE (Fastino)

- **What it is:** Fastino's hosted decision model. Fastino says it reasons further on uncertain decisions
  before it returns the probabilities. No published size or base model.
- **Setup:**
  - Key: a Fastino API key in `FASTINO_API_KEY`; a copy is in `~/.config/fastino/key`.
  - Docs: <https://docs.fastino.ai/inference/systemone>.
  - Price: $0.15 per 1M input tokens, output free.
- **Call it:** `POST https://api.fastino.ai/v1/systemone`, model `fastino/GLiDE`, with
  `Authorization: Bearer <key>`.

  ```bash
  ./run_glide.sh
  # = ./benchmark_ollama.py fastino/GLiDE --provider fastino --data questions-v2.sqlite --timeout 300 --concurrency 4
  curl -s https://api.fastino.ai/v1/systemone -H "Authorization: Bearer $FASTINO_API_KEY" \
    -H 'Content-Type: application/json' --data-binary @request.json
  ```

- **Response:** System One.
  - `model` comes back as `glide`, and there is an extra top-level `token_usage`.
  - `usage.output_tokens` counts its reasoning: 1 on easy questions, hundreds on uncertain ones, 254 per
    question on average here.
  - No request ID is stored.
- **On our bank (run 129):** 67.9% (reading 87.8%, grammar 59.4%), AUROC 0.810, ECE 0.045, 121 of 121
  right at ≥ 0.99. Whole bank: 14 minutes, $0.35.
- **Watch out:** about 2 s per request, so keep `--concurrency 4` and a long `--timeout`. HTTP 425 means
  the model is still warming up; the benchmark retries it.
- **Last check (2026-10-08):** answered the example (E, 0.999) in 1.2 s.

## 2. GPT-6 Luna through OpenAI's Decisions API (beta)

- **What it is:** OpenAI's Decisions API, in public beta; `gpt-6-luna` is its only model. It returns a
  probability for every option and does no reasoning (0 output tokens).
- **Setup:**
  - Key: an OpenAI API key with billing in `OPENAI_API_KEY`. The ChatGPT subscription behind the Codex
    runs does not cover this endpoint.
  - Guide: <https://developers.openai.com/api/docs/guides/decisions>.
  - Price: $0.10 per 1M input tokens; output and cache free.
  - Our limits: 5,000 requests and 2M tokens per minute.
- **Call it:** `POST https://api.openai.com/v1/decisions`. The request differs from System One: `input`
  instead of `state`, `questions` as a list with a `name`, and `choices` as `{value, description}` pairs
  instead of `criteria`. Save this as `request-openai.json`:

  ```json
  {
    "model": "gpt-6-luna",
    "input": "\"Kitabı masanın üstüne dün bıraktım.\" cümlesinin yüklemi hangisidir?\n\nSeçenekler:\nA. Kitabı\nB. masanın\nC. üstüne\nD. dün\nE. bıraktım",
    "questions": [
      {
        "type": "choice",
        "name": "answer",
        "instructions": "Which option is the correct answer to this Turkish multiple-choice question?",
        "choices": [
          {"value": "A", "description": "Kitabı"},
          {"value": "B", "description": "masanın"},
          {"value": "C", "description": "üstüne"},
          {"value": "D", "description": "dün"},
          {"value": "E", "description": "bıraktım"}
        ]
      }
    ]
  }
  ```

  ```bash
  ./run_openai_decisions.sh
  # = ./benchmark_ollama.py gpt-6-luna --provider openai-decisions --data questions-v2.sqlite --timeout 60 --concurrency 4
  curl -s https://api.openai.com/v1/decisions -H "Authorization: Bearer $OPENAI_API_KEY" \
    -H 'Content-Type: application/json' --data-binary @request-openai.json
  ```

- **Response:**
  - `answers` is a list. Each option's probability comes as `{"value": "A", "probability": 0.16}`,
    rounded to two decimals. `confidence` is there but not used.
  - `usage` has `input_tokens`, `output_tokens: 0` and `reasoning_tokens: 0`.
  - The `x-request-id` header is stored. `system_one_answer()` turns the response into the System One shape.
  - A refusal comes back as `{"type": "refusal", "name": "answer"}` with no choice; the benchmark counts
    it wrong.
- **On our bank (run 143):** 63.6% (reading 85.5%, grammar 54.3%), AUROC 0.820, ECE 0.024, 365 of 368
  right at ≥ 0.99. Whole bank: under 2 minutes, $0.09. Four refusals, no reason given: questions 292,
  4062, 4091 and 4203.
- **Watch out:**
  - Two-decimal probabilities give only 80 distinct scores (276 answers at exactly 1.0), so thresholds
    tie.
  - The same model through Codex scores 4.7 points higher (68.3%), but its stated confidence is much
    worse (AUROC 0.69, ECE 0.26).
- **Last check (2026-10-08):** E, 1.0, in 1.1 s.

## 3. Perplexity Decider 27B

- **What it is:** Perplexity's decision model `pplx-decider-v1-27b`, 26.1B parameters (its published
  index), built on Qwen3.8-27B. It is the only model, and it has no versioned ID.
- **Setup:**
  - Key: any Perplexity API key (<https://console.perplexity.ai/project/keys>) in `PERPLEXITY_API_KEY`.
  - Docs: <https://docs.perplexity.ai/docs/decisions/quickstart>.
  - Price: $0.04 per 1M input tokens, output free.
  - Limit: 10 requests per second per organization; beyond that HTTP 429, which the benchmark retries.
- **Call it:** `POST https://api.perplexity.ai/v1/decisions`, with the System One request unchanged.

  ```bash
  ./run_perplexity.sh
  # = ./benchmark_ollama.py pplx-decider-v1-27b --provider perplexity --data questions-v2.sqlite --timeout 30
  curl -s https://api.perplexity.ai/v1/decisions -H "Authorization: Bearer $PERPLEXITY_API_KEY" \
    -H 'Content-Type: application/json' --data-binary @request.json
  ```

- **Response:** System One. `usage.output_tokens` is always 1. The `x-request-id` header is stored.
- **On our bank (run 44):** 60.4% (reading 86.0%, grammar 49.5%), AUROC 0.827 (the best ranking of the
  eight), ECE 0.050. Rarely sure: only 21 answers at ≥ 0.99, all right. Whole bank: 8 minutes.
- **Watch out:**
  - Perplexity documents that identical requests can differ in the second decimal; our repeat of 100
    questions matched exactly.
  - The API also reads images in `state`; the benchmark sends text only.
- **Last check (2026-10-08):** E, 0.9997, in 0.6 s.

## 4. Jev 1.13.0 (TypeSafe)

- **What it is:** TypeSafe's System One decision model; its request format is the one the others copy.
  No published size or base model.
- **Setup:**
  - Key: a TypeSafe key (<https://docs.typesafe.ai/>). The benchmark reads `JEV_API_KEY`, then
    `TYPESAFE_API_KEY`; `run_jev.sh` takes it from `~/code/jev/key`.
  - Price: $0.042 per 1M input tokens, output free.
- **Call it:** `POST https://api.typesafe.ai/v1/systemone`. Pin `jev-1.13.0`, because `jev-latest` can
  change between resumed requests. `GET /v1/models` lists the models.

  ```bash
  ./run_jev.sh
  # = JEV_API_KEY="$(cat ~/code/jev/key)" ./benchmark_ollama.py jev-1.13.0 --provider jev --data questions-v2.sqlite --timeout 30
  curl -s https://api.typesafe.ai/v1/systemone -H "Authorization: Bearer $(cat ~/code/jev/key)" \
    -H 'Content-Type: application/json' --data-binary @request.json
  ```

- **Response:** System One. `usage.output_tokens` is always 52, a usage convention: no text is generated.
  The `x-typesafe-request-id` header is stored.
- **On our bank (run 49):** 57.5% (reading 83.7%, grammar 46.4%), AUROC 0.807, ECE 0.051, 311 of 312
  right at ≥ 0.99. Whole bank: 9 minutes.
- **Watch out:**
  - The probabilities are coarse, mostly two decimals: only 95 distinct scores over 2,210 answers.
  - Keep `--timeout 30` (the TypeSafe SDK's default), so a stalled request is retried instead of waiting
    the general 300 s.
- **Last check (2026-10-08): slow and unstable.**
  - `jev-1.13.0` gave HTTP 503 (`model_unavailable`), then a 504 after 30 s, then answered in 5.4 s.
  - `jev-latest` answered in 26 s, as `jev-1.13.0`.
  - Normal is about 0.25 s.
  - `/v1/models` now lists only `jev-latest` and `jev-preview`, but the pinned name still works.

## 5. Clef (Cloudflare), self-hosted

- **What it is:** Cloudflare's 27B multimodal decision model (27.5B parameters, Apache-2.0),
  post-trained from Qwen3.8-27B. A joint schema head scores all options in one forward pass.
- **Files:**
  - Release code and weights: `~/code/clef/model` (52 GB of BF16 safetensors, Hugging Face commit
    `2f3de3d`).
  - Our HTTP wrapper: `~/code/clef/server.py`. It hands each request to the release's `systemone()`
    in `model/joint_schema_model.py`.
  - `~/code/clef/run_clef.py`: a sample script for calling the model directly from Python.
- **Environment:** `~/code/clef/.venv` with Python 3.12, torch 2.11.0, transformers 5.10.2 and
  accelerate 1.15.0, from `requirements.txt` (`torch==2.11.*`, `transformers==5.10.2`, torchvision,
  accelerate, safetensors, huggingface_hub, pillow).
- **Hardware:** about 55 GB of GPU memory in BF16; it ran on GPU 1.
- **Start:**

  ```bash
  cd ~/code/clef && HF_HUB_OFFLINE=1 .venv/bin/python server.py --device cuda:1
  # defaults: --device cuda:0 --host 127.0.0.1 --port 18091
  ```

  Once the model is loaded it prints `{"url": "http://127.0.0.1:18091", "model": "clef", "device": "cuda:1"}`.
  There is no health endpoint: the server handles only `POST /v1/systemone`, one request at a time.
- **Call it:**

  ```bash
  ./run_clef.sh
  # = ./benchmark_ollama.py clef --provider clef --data questions-v2.sqlite --timeout 120
  curl -s http://127.0.0.1:18091/v1/systemone -H 'Content-Type: application/json' --data-binary @request.json
  ```

  The request must include `model`: Clef echoes it back, and returns HTTP 400 without it.
- **Response:** System One; probabilities rounded to four decimals; `output_tokens` 0; no request ID.
- **On our bank (run 125):** 57.3% (reading 85.1%, grammar 45.5%), AUROC 0.785, ECE 0.107. It never
  reaches 0.99. Whole bank: 8 minutes.
- **Stop:** Ctrl-C in its terminal.
- **Clef-flash** (45.7%, `Cloudflare/clef-flash` at `fde727a`) runs the same way from `~/code/clef-flash`,
  in Clef's environment: `HF_HUB_OFFLINE=1 ../clef/.venv/bin/python server.py --device cuda:2` (port 18095,
  about 19 GB), then `run_clef_flash.sh`.

## 6. Liquid d1

- **What it is:** Liquid AI's decision model, served free as `d1:free`. No published size or base model.
- **Setup:**
  - Key: create one at <https://console.liquid.ai> (Dashboard > API Keys) and put it in `LIQUID_API_KEY`.
  - Docs: <https://docs.liquid.ai/lfm/models/decision-models>.
  - Price: free; Liquid publishes no d1 price.
- **Call it:** `POST https://api.liquid.ai/decisions/v1/systemone`, with the System One request.

  ```bash
  ./run_liquid_d1.sh
  # = ./benchmark_ollama.py d1:free --provider liquid --data questions-v2.sqlite --timeout 30
  curl -s https://api.liquid.ai/decisions/v1/systemone -H "Authorization: Bearer $LIQUID_API_KEY" \
    -H 'Content-Type: application/json' --data-binary @request.json
  ```

- **Response:** System One; `output_tokens` 0; no request ID (Liquid sends none).
- **On our bank (run 52):** 57.0% (reading 82.8%, grammar 46.0%), AUROC 0.792, ECE 0.102, 273 of 274
  right at ≥ 0.99. Whole bank: 15 minutes.
- **Watch out:**
  - Liquid limits the model's total request rate: bursts get HTTP 429 with `Retry-After: 1`, which the
    benchmark retries.
  - `d1:free` has no versioned ID, so a run can't pin a release.
  - Identical requests can return different probabilities, and on uncertain questions a different option.
- **Last check (2026-10-08):** E, 0.9996, in 0.24 s. A 3-question trial run hit one 429 and finished
  after the retry.

## 7. Open-Jev 27B v1.1, self-hosted

- **What it is:** Zefan Cai's open reimplementation of Jev's API: a LoRA adapter (rank 8), a scalar
  decision head and a saved temperature (2.534) on Qwen3.8-27B. Each option is scored as its own sequence
  that repeats the question.
  - Model: <https://huggingface.co/ZefanCai/Open-Jev-27B-v1.1>.
  - Code: <https://github.com/Zefan-Cai/Open-Jev>.
- **Files:**
  - Code: `~/code/Open-Jev` at commit `3308a15`.
  - Checkpoint package: `~/code/Open-Jev/checkpoints/open-jev-27b-v1.1/package/checkpoint` (adapter,
    `head.pt`, `model.json`, `temperature.json`; 60 MB).
  - Base weights: `Qwen/Qwen3.8-27B` at revision `1d4bf0f` (pinned in `model.json`), 52 GB in
    `~/.cache/huggingface/hub`.
- **Environment:** `~/code/Open-Jev/.venv` with torch 2.14.0, transformers 5.10.2, peft 0.19.1 and
  accelerate 1.13.0.
- **Hardware:** about 53 GB on one GPU, BF16.
- **Start:** a systemd user unit, `~/.config/systemd/user/open-jev.service`. It is disabled, so it doesn't
  start at boot.

  ```bash
  systemctl --user start open-jev.service
  journalctl --user -u open-jev.service -f        # watch it load
  ```

  The unit runs:

  ```bash
  cd ~/code/Open-Jev && HF_HUB_OFFLINE=1 .venv/bin/python -m jev.server \
    --checkpoint checkpoints/open-jev-27b-v1.1/package/checkpoint \
    --device cuda:0 --max-length 4096 --batch-size 8 --no-prefix-cache --host 0.0.0.0 --port 8791
  ```

  The port opens only after the model has loaded.
- **Check it is up:** `curl -s http://127.0.0.1:8791/health` returns `{"status": "ready", ...}`.
- **Call it:** the benchmark's default URL, `http://192.168.1.126:8791`, is this machine's LAN address.

  ```bash
  ./run_open_jev.sh
  # = ./benchmark_ollama.py open-jev-27b-v1.1 --provider open-jev --data questions-v2.sqlite --timeout 30
  curl -s http://127.0.0.1:8791/v1/systemone -H 'Content-Type: application/json' --data-binary @request.json
  ```

  It takes no `model` field; the benchmark's model name is only the report label.
- **Response:** System One, with `model: "Qwen/Qwen3.8-27B"` and a `metadata` block. The block records
  the temperature, the candidate count, `inference_seconds`, the checkpoint SHA-256 (`c4999456…`), the
  base revision, the maximum length and the code commit.
- **On our bank (run 45):** 55.7% (reading 82.9%, grammar 44.1%), AUROC 0.823, ECE 0.245. Whole bank:
  14 minutes.
  - Strongly underconfident: it never gives the chosen option 0.7 or more, yet all 144 answers between
    0.5 and 0.6 are right.
  - On version 1 of the bank, refitting the temperature to 0.68 lowered ECE from 0.228 to 0.030, with
    accuracy unchanged. Our results use the released 2.53.
  - About 1,380 input tokens per question, roughly twice the others, because every option repeats the
    question.
- **Watch out:**
  - Keep `--device cuda:0`. With `cuda:1` and up, this stack loads but returns wrong probabilities. To
    use another GPU, set `CUDA_VISIBLE_DEVICES` instead: run `systemctl --user edit open-jev.service`
    and add `Environment=CUDA_VISIBLE_DEVICES=1` under `[Service]`.
  - On 2026-10-08, GPU 0 is full (Gemma vLLM and another user's ComfyUI), so the unit as written won't
    fit there.
  - The unit has `Conflicts=deepseek-v41.service`: starting one stops the other.
  - It listens on all interfaces with no authentication.
  - `--batch-size 8` scores up to 8 options per GPU pass: 1.9× faster than 1, with the same answers.
  - The repo's `docker-compose.yml` serves Open-Jev 2B, not this model.
- **Stop:** `systemctl --user stop open-jev.service`.

## 8. Cygnet, self-hosted

- **What it is:** blockbrain-ai's `cygnet-recipe` (MIT): `google/gemma-4-12B-it`, unchanged (11.96B
  parameters, BF16), on stock vLLM 0.30.0, read out by option letter. For each question the decision
  server:
  1. shows the options as letters;
  2. lets vLLM write one token, restricted to those letters;
  3. sums each letter's probability from the top 20 logprobs;
  4. applies a calibration temperature of 3.4 (p^(1/T), renormalized).
- **Files:**
  - Code: `~/code/cygnet` (<https://github.com/blockbrain-ai/cygnet-recipe> at `3cf591c`). The server
    is `shim/decision_server.py`, which imports `shim/cygnet_shim.py`. Both use only the standard
    library, so the system `python3` runs them; there is no venv.
  - Weights: `google/gemma-4-12B-it` at revision `707f0a3b8a3c7ad586ed01e27eafbad8a27dd0f7`, 23 GB in
    `~/.cache/huggingface/hub`.
  - Image: `vllm/vllm-openai:v0.30.0` (digest `sha256:8a69ffad…`, the one the recipe names).
- **Hardware:** it ran on GPU 2.
  - The weights need about 24 GB.
  - `--gpu-memory-utilization 0.90` makes vLLM reserve 90% of the card; lower it to share a GPU.
- **Start**, as two processes:

  ```bash
  # 1. vLLM on port 8892 (the recipe's 8890 belongs to hilde-searxng here)
  docker run -d --name cygnet-vllm --network host --ipc host --runtime nvidia --gpus device=2 \
    -e HF_HUB_OFFLINE=1 -v ~/.cache/huggingface/hub:/root/.cache/huggingface/hub:ro \
    --entrypoint vllm vllm/vllm-openai:v0.30.0 serve google/gemma-4-12B-it \
    --revision 707f0a3b8a3c7ad586ed01e27eafbad8a27dd0f7 --served-model-name cygnet \
    --host 127.0.0.1 --port 8892 --max-model-len 16384 --gpu-memory-utilization 0.90
  # 2. the decision server on port 18093, once vLLM answers
  cd ~/code/cygnet && SHIM_VLLM=http://127.0.0.1:8892/v1/chat/completions SHIM_MODEL=cygnet \
    SHIM_TEMPERATURE=3.4 CYGNET_PORT=18093 python3 shim/decision_server.py
  ```

- **Check it is up:** first `curl -s http://127.0.0.1:8892/v1/models` (vLLM), then
  `curl -s http://127.0.0.1:18093/v1/models` (the decision server; it lists `cygnet`).
- **Call it:**

  ```bash
  ./run_cygnet.sh
  # = ./benchmark_ollama.py cygnet --provider cygnet --data questions-v2.sqlite --timeout 180
  curl -s http://127.0.0.1:18093/v1/systemone -H 'Content-Type: application/json' --data-binary @request.json
  ```

- **Response:** System One; `output_tokens` 1 (the one letter); full-precision probabilities.
- **On our bank (run 127):** 55.7% (reading 82.8%, grammar 44.2%), AUROC 0.802, ECE 0.138; only 2
  answers at ≥ 0.99. The fastest of the eight: 0.04 s per question, the whole bank in 1.4 minutes.
- **Identity check:** JevBench's 48 public easy items gave the authors' answers on all 48, with
  probabilities within 0.002.
- **Watch out:**
  - Set all four variables. Without them the server uses port 8010 (taken by the `gemma4-31b` container
    now), vLLM port 8890, and temperature 1.0, which turns the calibration off.
  - Other settings and their defaults:
    - `CYGNET_HOST`: 127.0.0.1;
    - `CYGNET_API_KEY`: unset; when set, requests need it as a Bearer key;
    - `CYGNET_MAX_PARALLEL`: 8 vLLM requests in flight;
    - `SHIM_TIMEOUT`: 180 s;
    - `SHIM_MIN_CONTEXT`: 4096.
  - It refuses to listen beyond localhost without `CYGNET_API_KEY`, unless `CYGNET_ALLOW_NO_KEY=1`.
  - The `cygnet-vllm` container was removed after the run; the `docker run` above creates it again. If
    the name is taken, `docker rm cygnet-vllm` first.
  - Ollaya's `cygnet` package runs the same prompt on a Q8_0 GGUF under llama.cpp. That is a different
    setup from the one measured here.
- **Stop:** Ctrl-C the decision server, then `docker stop cygnet-vllm && docker rm cygnet-vllm`.

## Which one for what (from these runs)

- **Accuracy:** GLiDE, 4.3 points ahead of the next.
- **Calibration** (does 0.8 mean right 80% of the time?): the OpenAI Decisions API (ECE 0.024), then
  GLiDE (0.045).
- **Ranking right answers above wrong ones:** Perplexity (AUROC 0.827), Open-Jev (0.823), OpenAI (0.820).
- **Cost:** d1 is free. Perplexity is the cheapest paid service ($0.016 per 1,000 questions). The
  self-hosted three cost only GPU time.
- **Speed:** Cygnet locally (0.04 s per question); the OpenAI Decisions API among the hosted ones (0.19 s).
