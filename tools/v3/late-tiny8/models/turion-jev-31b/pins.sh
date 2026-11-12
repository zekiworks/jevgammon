# Sourced by start.sh and locals.sh (URL, PORT and SSH_HOST set there): the model's snapshot, its /health as the
# pinned server answers it, and pinned(): the pinned server process on PORT, read over ssh (read-only).
SNAPSHOT=/home/cbasaran/decision-models/turion-jev-31b@866c0fc6e040cba23fcc72113a80e5c99d5ebab1
LABEL="Turion Jev"
ENV=/home/cbasaran/envs/turion-jev
# sha256 of "sha256sum" over the package's .py files (sorted, LC_ALL=C) as installed in ENV (turion-jev 0.1.0, a plain
# install of the snapshot's code/) and in the snapshot's code/turion_jev: the same tree.
TREE_SHA=17881787acbd39a1ba77f99b157da3ad4718ca808baf5d6faa7ed49dbd24a279
CALIBRATION_SHA=1825117d4747b226bf2036ebefe2142dfe573b2e680b6f05d7b3eb4d08ee0820
PROMPT_CONFIG_SHA=f1b59802afc6b1842203ef8a12329c9fcb010a5980c4ec08ef2e5619486411e8
# turion_jev.serve's /health: the model_name of the snapshot's calibration.json.
healthy() {
  curl -fsS -m 10 "$URL/health" | python3 -c 'import json,sys; d=json.load(sys.stdin)
sys.exit(not (d == {"ok": True, "model": "turion-jev-31b"}))'
}
# Exactly `python -m turion_jev.serve --model SNAPSHOT --backend vllm --quantization fp8 --no-recheck --host 0.0.0.0
# --port PORT` from ENV (logic's setup: re-scoring off as in the card's run; --max-len and the recheck threshold at
# their defaults, 65,536 and unused), no TURION_JEV_API_KEY in its environment, the installed package the snapshot's
# code, turion-jev 0.1.0 with vLLM 0.32.0, and the snapshot's calibration.json and prompt_config.json.
pinned() {
  local procs args="-m turion_jev.serve --model $SNAPSHOT --backend vllm --quantization fp8 --no-recheck --host 0.0.0.0 --port $PORT"
  local sp=$ENV/lib/python3.12/site-packages
  procs=$(timeout 30 ssh -o BatchMode=yes "$SSH_HOST" "ps -eo pid=,args= | while read -r pid a; do
      case \"\$a\" in '$ENV/bin/python $args'|'$ENV/bin/python3 $args'|'$ENV/bin/python3.12 $args')
        echo \"server \$(tr '\\0' '\\n' < /proc/\$pid/environ | grep -c '^TURION_JEV_API_KEY=')\";; esac; done; echo @@;
    echo \"tree \$(cd $sp && find turion_jev -name '*.py' | LC_ALL=C sort | xargs sha256sum | sha256sum)\";
    echo \"code \$(cd $SNAPSHOT/code && find turion_jev -name '*.py' | LC_ALL=C sort | xargs sha256sum | sha256sum)\";
    ls -d $sp/turion_jev-0.1.0.dist-info $sp/vllm-0.32.0.dist-info; sha256sum $SNAPSHOT/calibration.json $SNAPSHOT/prompt_config.json" \
    2>/dev/null) || return 1
  grep -qxF "server 0" <<<"$procs" &&
  grep -qxF "tree $TREE_SHA  -" <<<"$procs" && grep -qxF "code $TREE_SHA  -" <<<"$procs" &&
  grep -qxF "$sp/turion_jev-0.1.0.dist-info" <<<"$procs" && grep -qxF "$sp/vllm-0.32.0.dist-info" <<<"$procs" &&
  grep -qxF "$CALIBRATION_SHA  $SNAPSHOT/calibration.json" <<<"$procs" &&
  grep -qxF "$PROMPT_CONFIG_SHA  $SNAPSHOT/prompt_config.json" <<<"$procs"
}
