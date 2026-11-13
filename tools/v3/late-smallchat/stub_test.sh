#!/usr/bin/env bash
# Dry run of test.sh KEY against stub_chat.py instead of the real server (no GPU, no model, nothing on v3.db but
# smallchat.py's read-only config read): the stub listens on 127.0.0.1:STUB_PORT (default 28600 + n), test.sh gets it
# through SMALLCHAT_URL, and pins.sh's pinned() sees the stub as the pinned server: for llama.cpp setups the stub's
# command line carries llama-server's pinned arguments (pgrep), for vLLM setups a docker shim first on PATH reports
# a container with the pinned arguments and models.json's image (the real docker is never called). The runner is
# test.sh's (SMALLCHAT_BIN). KEY: expected to pass (test.sh exit 0, nothing refused); KEY=refused: expected to fail
# with a request refused by the chat template or for a wrong read-out prompt (regressions with a runner that ignores
# reasoning_prefill / reasoning_field: MiniCPM5-2B (on) gets vLLM's 400, LFM3-1.7B (on) an extra <think></think>).
# Exit 0 when every KEY behaved as expected.
#   tools/v3/late-smallchat/stub_test.sh KEY[=refused]...
# STUB_PYTHON: a python with transformers 5.22.2 (the vLLM be47189f3 image's), default ~/.cache/smallchat/venv-tf5222
# (python3 -m venv ~/.cache/smallchat/venv-tf5222 && ~/.cache/smallchat/venv-tf5222/bin/pip install
# transformers==5.22.2 tokenizers jinja2).
set -uo pipefail
T=$(dirname "$(readlink -f "$0")")
PY=${STUB_PYTHON:-$HOME/.cache/smallchat/venv-tf5222/bin/python}
HUB=$HOME/.cache/huggingface/hub
WORK=$HOME/.cache/smallchat/stub-test
mkdir -p "$WORK/bin"
fail=0 n=0
for ARG in "$@"; do
  KEY=${ARG%=refused}; EXPECT=pass; [[ $ARG == *=refused ]] && EXPECT=refused
  n=$((n + 1)); PORT=$((28600 + n)); LOG=$WORK/$KEY.jsonl; : >"$LOG"
  MODEL=${KEY%-on}; MODEL=${MODEL%-off}
  eval "$(python3 - "$T/models.json" "$MODEL" <<'EOF'
import json, shlex, sys
m = json.load(open(sys.argv[1]))[sys.argv[2]]
g = m["own"].get("gguf") or ["", "", ""]
print(f"REPO={shlex.quote(m['repo'])} REV={m['rev']} SERVER={m['own']['server']} GREPO={shlex.quote(g[0])} GREV={g[1]} GFILE={shlex.quote(g[2])}")
print(f"IMAGE={shlex.quote(m.get('image', 'vllm/vllm-openai:v0.30.0'))}")
EOF
)"
  SNAP=$HUB/models--${REPO//\//--}/snapshots/$REV
  if [[ $SERVER == llama.cpp ]]; then
    ARGS=(llama-server -m "$HUB/models--${GREPO//\//--}/snapshots/$GREV/$GFILE" --port "$PORT" -c 2228224
          --chat-template-file "$SNAP/chat_template.jinja" --stub)
    printf '#!/bin/sh\nexit 0\n' >"$WORK/bin/docker"
  else
    ARGS=()
    printf '#!/bin/sh\ncase $1 in ps) echo stub;; inspect) case "$3" in *Config.Image*) echo "%s sha256:0";; *) echo "serve %s --revision %s --port %s --dtype bfloat16 --max-model-len 69632";; esac;; esac\n' \
      "$IMAGE" "$REPO" "$REV" "$PORT" >"$WORK/bin/docker"
  fi
  chmod +x "$WORK/bin/docker"
  "$PY" "$T/stub_chat.py" "$KEY" "$PORT" "$LOG" "${ARGS[@]}" >"$WORK/$KEY.stub.log" 2>&1 &
  STUB=$!
  for _ in $(seq 120); do curl -fsS -m 2 "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1 && break; sleep 1; done
  rm -rf "$HOME/.cache/smallchat/test/$KEY"
  PATH=$WORK/bin:$PATH SMALLCHAT_URL=http://127.0.0.1:$PORT/v1 "$T/test.sh" "$KEY"
  rc=$?
  kill "$STUB" 2>/dev/null; wait "$STUB" 2>/dev/null
  refused=$(python3 -c 'import json,sys; print(sum(1 for l in open(sys.argv[1]) if json.loads(l)["refused"]))' "$LOG")
  python3 -c 'import json,sys
for l in open(sys.argv[1]):
    r = json.loads(l); print("  request: readout=%(readout)s prompt_tokens=%(prompt_tokens)s max_tokens=%(max_tokens)s refused=%(refused)s" % r)' "$LOG"
  if [[ $EXPECT == pass ]] && (( rc == 0 && refused == 0 )); then echo "$KEY: STUB TEST PASSED"
  elif [[ $EXPECT == refused ]] && (( rc != 0 )) &&
       python3 -c 'import json,sys; sys.exit(not any((json.loads(l)["refused"] or "").startswith(("chat template:", "read-out prompt")) for l in open(sys.argv[1])))' "$LOG"
  then echo "$KEY: STUB TEST PASSED (refused as expected: chat template or wrong read-out prompt)"
  else echo "$KEY: STUB TEST FAILED (expected $EXPECT; test.sh $rc, refused $refused)"; fail=1; fi
done
exit $fail
