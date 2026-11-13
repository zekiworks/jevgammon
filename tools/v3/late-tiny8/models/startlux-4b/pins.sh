# Sourced by start.sh and locals.sh (URL, PORT and SSH_HOST set there): the model's snapshot, its /health as the
# pinned server answers it, and pinned(): the pinned server process on PORT, read over ssh (read-only).
SNAPSHOT=/home/cbasaran/decision-models/StartLux-Decision-v1.1-4B-Instant@416088f77cfce09633906a3675c7cd2e5dabcf10
LABEL=StartLux
REPO=/home/cbasaran/decision-src/StartLux-Decision
REPO_COMMIT=a99977d9332decc9fb27a2488b4a83b533b6cd5f
PLUGIN_SHA=d80d120266b915f0d7ef1de09483b09eaf4ef79641f8847f6c696f9d8ac20a66
# As the 2B's (tools/v3/late-startlux2b): the snapshot's Instant server, vLLM 0.31.0, bidirectional, 131,072, no thinking.
healthy() {
  curl -fsS -m 10 "$URL/health" | python3 -c 'import json,sys; d=json.load(sys.stdin); e=d["engine"]
sys.exit(not (d["status"] == "ok" and d["model"] == "StartLux-Decision-v1.1-4B-Instant@416088f77cfce09633906a3675c7cd2e5dabcf10"
              and d["kind"] == "instant" and d["prompt_attention"] == "bidirectional" and e["name"] == "vllm"
              and e["vllm_versions"] == ["0.31.0"] and d["context_length"] == 131072
              and d["defaults"]["think_mode"] == "never"))'
}
pinned() {
  local procs
  procs=$(timeout 30 ssh -o BatchMode=yes "$SSH_HOST" "ps -eo args; echo @@; git -C $REPO rev-parse HEAD;
    git -C $REPO status --porcelain --untracked-files=no | wc -l; sha256sum $REPO/startlux_decide/vllm_plugin.py;
    cat ~/envs/startlux/lib/python3.12/site-packages/startlux_decide-1.1.0.dist-info/direct_url.json" 2>/dev/null) ||
    return 1
  grep -qxF "$REPO_COMMIT" <<<"$procs" && grep -qxF 0 <<<"$procs" &&
  grep -qF "$PLUGIN_SHA  $REPO/startlux_decide/vllm_plugin.py" <<<"$procs" &&
  grep -qF "\"url\": \"file://$REPO\"" <<<"$procs" &&
  grep -F "startlux-decide serve --model $SNAPSHOT --launch-vllm " <<<"$procs" | grep -F -- "--port $PORT" |
    grep -vF -- "--allow-none" | grep -qvF -- "--no-none-check" &&
  grep -F "vllm.entrypoints.openai.api_server --model $SNAPSHOT " <<<"$procs" | grep -F -- "--max-model-len 131072" |
    grep -vqF -- "--quantization"
}
