# Late entries REAX - status 2026-11-07

Go: Ümit via Zeki (bus #2092, 7 Nov). REAX 1.3 joins the original League 1 table as a late entry, in the same format as the Drex and Base Labs late entries: a hidden late-entry league that plays the 19 original League 1 setups once.

**State: on hold. No REAX server is running, and no match was played or created.** The one server start failed with EPERM under `no-new-privileges` (details below). Zeki (#2099) gave no approval to run without it; that needs Can's explicit decision. Until then nothing is started: no REAX server, and no league against the free opponents. Results 2f496968 and every finished match are untouched. GPT-6 Astra is not involved.

## Setup (from Turkce's `run_reax13.sh` and Turkce, bus #2095)

| | |
|---|---|
| Model | `decisionmodels/REAX-1.3` @ fa4bf7ee3bb56a8bc421dad090631be1c5845c2d (Apache-2.0); two parts in FP8 on one GPU, each option's probability the 50/50 mean of the two parts' |
| Weights | `~/code/reax-engine/reax13/model-repo`, mounted `:ro` |
| Engine | github.com/reaxlabs/reax-engine @ ff8f595f149abdd50ea914455eadc74cf97a277f, reax13 mode; image `reax13-runtime` (built on bariton) |
| Decision Index kit | `~/code/reax-engine/reax13/decision-index` @ 25c6ec7b6b5f44a216c63c3a700de3a9c6d6699d; its `decision_index/` is mounted `:ro` at `/kit/decision_index` |
| Interface | Jev-compatible `POST /v1/systemone`; the model field must be `reax13`; one request at a time (the server serializes requests); client timeout 1,800 s (the runner's HTTP client already uses 1,800 s) |
| GPU | GPU 3, as in Turkce's run (one RTX PRO 6000, 96 GB; about 62 GB when loaded) |

## Server attempt (one try; stopped there)

At 2026-11-07 02:34 UTC, after `nvidia-smi` showed GPU 3 empty (20 MiB, no process), the server was started once:

    docker network create --internal reax13-offline
    docker run -d --name reax13-late --network reax13-offline -p 127.0.0.1:18093:8080 \
      --runtime nvidia --gpus device=3 --read-only --user "$(id -u):$(id -g)" \
      --cap-drop ALL --security-opt no-new-privileges --shm-size 8g --tmpfs /tmp:rw,exec,size=8g \
      -v ~/code/reax-engine/reax13/model-repo:/model:ro \
      -v ~/code/reax-engine/reax13/decision-index/decision_index:/kit/decision_index:ro \
      --entrypoint env reax13-runtime -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/tmp PYTHONPATH=/engine:/kit \
      DUO_ISOLATED=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 \
      HF_HUB_DISABLE_IMPLICIT_TOKEN=1 HF_HOME=/tmp/hf KERNELS_CACHE=/opt/kernels \
      LOCAL_KERNELS=kernels-community/finegrained-fp8=/opt/fp8-kernel D3_STATE_ONCE=0 OMP_NUM_THREADS=4 \
      OPENBLAS_NUM_THREADS=4 PYTORCH_ALLOC_CONF=expandable_segments:True TRITON_CACHE_DIR=/tmp/triton \
      python /engine/serve.py --host 0.0.0.0 --port 8080 --model /model --config /engine/reax13.json

This is the card's sealed-contract HTTP launch: an internal Docker network with no external route, the API published only on host loopback. It differs from the card only in `--runtime nvidia`, because bariton's Docker refuses `--gpus` without it.

- **Security settings:** `no-new-privileges` on; `--cap-drop ALL`; read-only root filesystem; non-root user; weights and kit mounted read-only; no outbound network.
- **Result:** the container exited with code 255 in under a second. Its whole log: `exec /usr/bin/env: operation not permitted`. Docker inspect: SecurityOpt `[no-new-privileges]`, CapDrop `[ALL]`, ReadonlyRootfs `true`, Runtime `nvidia`.
- **Cleanup:** the container was removed. GPU 3 was back at 20 MiB with no process. The empty internal network `reax13-offline` is left in place for a rerun.

### Cause (diagnosed)

The cause is on the host, not in REAX. Kernel audit log, one line per failed exec:

    apparmor="DENIED" operation="exec" class="file" info="no new privs" error=-1
    profile="snap.docker.dockerd" name="/usr/bin/env" comm="runc:[2:INIT]" target="docker-default"

- bariton's Docker daemon is the **snap** (`docker 29.8.0`, `snap.docker.dockerd` active). The apt `docker.service` is installed but inactive.
- Under the snap, runc runs inside the AppArmor profile `snap.docker.dockerd`. With `no_new_privs` set, the kernel refuses runc's switch to the container's profile at exec. So **every** container fails under `no-new-privileges`: `ubuntu:22.04 /bin/true` fails the same way.
- `--security-opt apparmor=unconfined` does not help: the exec is still denied, with target `unconfined`.
- Turkce's failures on 6 Nov (21:55 UTC) show the same audit line: 5 denials of this kind in the kernel log.

How the cause was found: before Zeki's #2099 limit, a few throwaway containers were run without a GPU and with `--network none`. They ran only `env true` or `/bin/true` in `reax13-runtime`, `reax13-base` and `ubuntu:22.04`, under:
- default security;
- `--cap-drop ALL` alone;
- `no-new-privileges`, alone and with `--cap-drop ALL`, `--runtime nvidia` or `apparmor=unconfined`.

All exited at once and were removed (`--rm`). The finding came from reading the kernel log. Since #2099, nothing has been run.

**Options for Can (each needs a decision; sudo for the first):**
1. Serve REAX with the non-snap Docker (`docker.service`, with the NVIDIA runtime configured). Keep `no-new-privileges` and the internal network, as in the card.
2. Approve running without `no-new-privileges`, as Turkce did (approved for Turkce's runs only, bus #2004). Everything else stays as above, including no outbound network.

## Runner (offline work, done)

- **Branch:** `late-reax` (from `late-drex` e58fc6c), worktree `~/code/jevgammon-reax`, commit 3a1bc46.
- **Service:** decision service `reax` (`src/players/decision.rs`).
  - URL `http://127.0.0.1:18106`, `REAX_BASE_URL`, path `/v1/systemone`. No key.
  - Model `reax13`.
  - Sends only `model`, `state` and `questions`, the fields `serve.py` accepts.
  - README provider table and base-URL list updated.
- **Option cap: 255 per request, from the card.**
  - The server accepts 2..255 options per choice question.
  - The engine refuses a request above 32,000 "proxy tokens", where proxy tokens = characters of the compact request JSON / 4; nothing is truncated.
  - The card documents no tokenizer limit, only this proxy. Measured with its formula on stored full-list System One requests in v3.db (Celeris, Liquid, Jev, SubQ), the largest (251 options, Celeris) is 15,424 proxy tokens: 48% of the cap.
  - Longer lists are split into groups and a final by the runner's existing mechanism. In the valid matches stored in v3.db, positions reach 461 legal plays, and 78 turns have more than 255.
- **Unit test:** `reax_sends_only_model_state_and_questions_with_up_to_255_options` checks the body fields, the model, the URL and the reading of `serve.py`'s answer. `cargo test`: 81 passed. `cargo fmt --check`: clean.
- **Smoke test (20 stored League 1 requests: probability sums, latency): not run.** It needs the server. `workspace/drex/drex.py smoke http://127.0.0.1:18106 reax13 --max-options 255` replays them once the server is allowed to start. The network setting (`--network none` or internal) is tested in that smoke: `HF_HUB_OFFLINE=1` is set.

## Paid opponents: pilot estimate (not started)

The eight paid API setups would play one match each against REAX. Method: each opponent's own averages over its valid finished matches in v3.db (league and late-entry stages), input tokens per decision × decisions per match × its list price per million input tokens. Output is not billed by any of them. The same 3 rounds per match apply as in League 1. REAX's own tokens cost nothing (our GPU).

| opponent | matches averaged | decisions / match | input tokens / decision | input tokens / match | $ / M input | est. $ / match | high (worse stage avg) |
|---|---|---|---|---|---|---|---|
| Celeris-1 Decision | 43 | 113.6 | 3,714 | 421,731 | 0.04 | 0.0169 | 0.0177 |
| Fastino GLiDE | 44 | 117.7 | 3,821 | 449,756 | 0.04 (no price in settings; as in the Drex runs) | 0.0180 | 0.0186 |
| GPT-6 Luna (blocked: no credit) | 25 | 107.2 | 3,336 | 357,448 | 0.10 | 0.0357 | 0.0368 |
| Jev 1.13.0 | 29 | 109.0 | 3,928 | 428,069 | 0.042 | 0.0180 | 0.0210 |
| Jev 1.14.0 | 43 | 109.7 | 4,026 | 441,675 | 0.042 | 0.0186 | 0.0210 |
| Liquid d1-ultra | 44 | 117.6 | 3,405 | 400,324 | 0.042 | 0.0168 | 0.0181 |
| Mercury Decide | 29 | 103.9 | 3,577 | 371,503 | 0.02 | 0.0074 | 0.0076 |
| SubQ Snap Preview | 29 | 121.4 | 3,850 | 467,489 | 0.05 | 0.0234 | 0.0240 |

- **All 8:** about 3.34 M input tokens, **≈ $0.155** (high $0.165).
- **Without GPT-6 Luna:** about 2.98 M tokens, **≈ $0.119** (high $0.128).
- The recorded `cost_usd` matches tokens × price for every setup except Fastino GLiDE, which records none.

## GPUs

None of ours hold anything. At 02:40 UTC: GPU 0 41 MiB, GPU 1 20 MiB, GPU 3 20 MiB, none with a process. GPU 2 holds Can's ai-toolkit and was not touched. GPUs 0, 1 and 3 are free.
