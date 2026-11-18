# Sourced by start.sh and locals.sh (URL and PORT set there): the model's snapshot, its /healthz as the pinned server
# answers it, and pinned(): the pinned server process on PORT. The server runs on this host (bariton), on compactor's
# card (runs/gpu0-serve-15nov.sh serve karpo-decision-31b), not on spark2: pinned() reads the local process table and
# files, so SSH_HOST only names the host in messages (TINY_SSH unused).
SSH_HOST="bariton (local)"
SNAPSHOT=/home/cbasaran/.cache/huggingface/hub/models--MachinePulseAI--karpo-decision-31B/snapshots/d69cdd57eab23271cbe65236ca8a00d80d7bb8c7
LABEL="Karpo Decision 31B"
ENV=/home/cbasaran/code/compactor/exp-grpo/.venv-karpo
# sha256 of "sha256sum" over the package's .py files (sorted, LC_ALL=C) as installed in ENV: karpo-decision 0.1.0 from
# github.com/machinepulse-ai/karpo-decision @ ac40d399a748d13820c5fba701e4bee1f21fd45a (its direct_url.json, pinned).
TREE_SHA=d61b0e3f292e41a74af85c4284776db91ed297e26e45abb22306af1bed609889
DIRECT_URL_SHA=82177c3eb9b6527d6b1119b704d3d4788f55927da5abef8c6ad3919049abe60f
# The snapshot as released: its decision config (codes, template karpo-blocks-v1, temperatures), backbone config, chat
# template and tokenizer files, and the 12 weight shards plus readout.safetensors by their blob names (Hugging Face
# names an LFS blob by its sha256): sha256 of "<file> <blob>" lines in that order.
DECISION_CONFIG_SHA=9a4502700d4aca2d277d177d45d886c5e7525c71e5c483bba77f115b4a7f13af
CONFIG_SHA=df331a6adf48a0c9af910d155be20a4143aeeb22e4a739da2d6b9190a6dc77fd
TEMPLATE_SHA=ae53464bf3be25802b3a5b37def7fd89667067d7577049b3b2d74c4d8de4c6d4
TOKENIZER_CONFIG_SHA=b8045a4576903e86903291d5cbdd4adfc8859e9ce3c98621bdbd957f73ed394b
TOKENIZER_SHA=cc8d3a0ce36466ccc1278bf987df5f71db1719b9ca6b4118264f45cb627bfe0f
WEIGHTS_SHA=3459260b1b05ce3ee514568a86dea85e2c0751dc4dc9219551bbc483a7905f38
# karpo_decision.serve.server's /healthz as compactor serves it: its default name, one rank, the plain path (no FP8, no
# graphs, no Triton attention kernel), bidirectional attention, --max-length 32,768; any GPU name.
healthy() {
  curl -fsS -m 10 "$URL/healthz" | python3 -c 'import json,sys; d=json.load(sys.stdin)
sys.exit(not (isinstance(d.pop("gpu", None), str) and d == {"ok": True, "model": "karpo-decision", "ranks": 1,
              "attention": "bidirectional", "path": "plain", "kernels": [], "max_length": 32768}))'
}
# The pinned server: the worker torchrun starts for exactly `torchrun --standalone --nproc_per_node 1 -m
# karpo_decision.serve.server --checkpoint SNAPSHOT --host 127.0.0.1 --port PORT` from ENV (sys.executable -u -m ...;
# no other option: default name, max length, plain path), offline (HF_HUB_OFFLINE=1 in its environment); the installed
# package as pinned with torch 2.15.0 and transformers 5.23.0; the snapshot's files as released.
SERVE="$ENV/bin/python3 -u -m karpo_decision.serve.server --checkpoint $SNAPSHOT --host 127.0.0.1 --port $PORT"
pinned() {
  local procs sp=$ENV/lib/python3.12/site-packages rest="-u -m karpo_decision.serve.server --checkpoint $SNAPSHOT --host 127.0.0.1 --port $PORT"
  procs=$( { ps -eo pid=,args= | while read -r pid a; do
      case $a in "$ENV/bin/python $rest"|"$ENV/bin/python3 $rest"|"$ENV/bin/python3.12 $rest")
        echo "server $(tr '\0' '\n' < /proc/$pid/environ | grep -cx 'HF_HUB_OFFLINE=1')";; esac; done
    echo "tree $(cd "$sp" && find karpo_decision -name '*.py' | LC_ALL=C sort | xargs sha256sum | sha256sum)"
    sha256sum "$sp/karpo_decision-0.1.0.dist-info/direct_url.json"
    ls -d "$sp/torch-2.15.0.dist-info" "$sp/transformers-5.23.0.dist-info"
    (cd "$SNAPSHOT" && sha256sum decision_config.json config.json chat_template.jinja tokenizer_config.json tokenizer.json)
    echo "weights $(cd "$SNAPSHOT" && for f in model-*.safetensors readout.safetensors; do
      echo "$f $(basename "$(readlink "$f")")"; done | sha256sum)"; } 2>/dev/null)
  grep -qx "server 1" <<<"$procs" && grep -qxF "tree $TREE_SHA  -" <<<"$procs" &&
  grep -qxF "$DIRECT_URL_SHA  $sp/karpo_decision-0.1.0.dist-info/direct_url.json" <<<"$procs" &&
  grep -qxF "$sp/torch-2.15.0.dist-info" <<<"$procs" && grep -qxF "$sp/transformers-5.23.0.dist-info" <<<"$procs" &&
  grep -qxF "$DECISION_CONFIG_SHA  decision_config.json" <<<"$procs" && grep -qxF "$CONFIG_SHA  config.json" <<<"$procs" &&
  grep -qxF "$TEMPLATE_SHA  chat_template.jinja" <<<"$procs" &&
  grep -qxF "$TOKENIZER_CONFIG_SHA  tokenizer_config.json" <<<"$procs" &&
  grep -qxF "$TOKENIZER_SHA  tokenizer.json" <<<"$procs" && grep -qxF "weights $WEIGHTS_SHA  -" <<<"$procs"
}
