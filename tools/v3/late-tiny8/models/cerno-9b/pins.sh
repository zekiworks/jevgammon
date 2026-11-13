# Sourced by start.sh and locals.sh (URL, PORT and SSH_HOST set there): the model's snapshot, its /health as the
# pinned server answers it, and pinned(): the pinned server process on PORT, read over ssh (read-only).
SNAPSHOT=/home/cbasaran/decision-models/cerno-9b-v1.2@f02a632fbe3a4698cd1ff5c0b929ea240e2b8eda
LABEL=Cerno
ENV=/home/cbasaran/envs/cerno
# logic's thin server around the card's CernoEngine (benchmark/decision/servers/cerno_server.py, request/response
# mapping only), copied to spark2; and the sha256 of "sha256sum" over the snapshot's inference .py files under evals/ and
# third_party/ (CernoEngine, the vendored decider 1c15a48; sorted, LC_ALL=C), and of its decider_config.json.
SERVER=/home/cbasaran/decision-src/cerno_server.py
SERVER_SHA=17749f72b80c967bab353404d87551e3937457b5545d02a6af8ec3a9f5bc6fed
TREE_SHA=442cfa6696fcc8792d5548f7a9899acd59bb463b8ffaa8aa2214fc38b76ea835
CONFIG_SHA=84d36f81c2adee800468078ecbfd369a897b165c57996d2017db6319391bd7ea
# cerno_server.py's /health: the name, then CernoEngine's provenance (decider_config.json: block attention, read twice
# up to 3,000 tokens, temperature 1.256), for this snapshot.
healthy() {
  curl -fsS -m 10 "$URL/health" | python3 -c 'import json,sys; d=json.load(sys.stdin)
sys.exit(not (d["status"] == "ok" and d["model"] == "apertixai/cerno-9b-v1.2" and d["kind"] == "local-weights"
              and d["attention"] == "block" and d["read_twice_tokens"] == 3000 and d["temperature"] == 1.256
              and d["model_path"] == "/home/cbasaran/decision-models/cerno-9b-v1.2@f02a632fbe3a4698cd1ff5c0b929ea240e2b8eda"))'
}
# Exactly `PYTHONPATH=SNAPSHOT/inference HF_HUB_OFFLINE=1 ENV/bin/python SERVER --model SNAPSHOT --name
# apertixai/cerno-9b-v1.2 --host 0.0.0.0 --port PORT` (logic's setup cerno-9b: the engine's defaults, i.e.
# max_state_tokens 32,768), with ENV exactly the card's inference/requirements-v1.2.txt (torch 2.14.1+cu130,
# transformers 5.17.0, fla 0.5.2, decision-index 0.3 at 9eb2dbe).
pinned() {
  local procs args="$SERVER --model $SNAPSHOT --name apertixai/cerno-9b-v1.2 --host 0.0.0.0 --port $PORT"
  local sp=$ENV/lib/python3.12/site-packages
  procs=$(timeout 30 ssh -o BatchMode=yes "$SSH_HOST" "ps -eo pid=,args= | while read -r pid a; do
      case \"\$a\" in '$ENV/bin/python $args'|'$ENV/bin/python3 $args'|'$ENV/bin/python3.12 $args')
        e=\$(tr '\\0' '\\n' < /proc/\$pid/environ 2>/dev/null | grep -E '^(PYTHONPATH|HF_HUB_OFFLINE)=' | LC_ALL=C sort | tr '\\n' ' ')
        echo \"server \$e\";; esac; done; echo @@;
    sha256sum $SERVER $SNAPSHOT/decider_config.json;
    echo \"tree \$(cd $SNAPSHOT/inference && find evals third_party -name '*.py' | LC_ALL=C sort | xargs sha256sum | sha256sum)\";
    ls -d $sp/torch-2.14.1+cu130.dist-info $sp/transformers-5.17.0.dist-info $sp/flash_linear_attention-0.5.2.dist-info \
      $sp/decision_index-0.3.dist-info" 2>/dev/null) || return 1
  grep -qxF "server HF_HUB_OFFLINE=1 PYTHONPATH=$SNAPSHOT/inference " <<<"$procs" &&
  [[ $(grep -c '^server ' <<<"$procs") == 1 ]] &&
  grep -qxF "$SERVER_SHA  $SERVER" <<<"$procs" && grep -qxF "$CONFIG_SHA  $SNAPSHOT/decider_config.json" <<<"$procs" &&
  grep -qxF "tree $TREE_SHA  -" <<<"$procs" &&
  grep -qxF "$sp/torch-2.14.1+cu130.dist-info" <<<"$procs" && grep -qxF "$sp/transformers-5.17.0.dist-info" <<<"$procs" &&
  grep -qxF "$sp/flash_linear_attention-0.5.2.dist-info" <<<"$procs" && grep -qxF "$sp/decision_index-0.3.dist-info" <<<"$procs"
}
