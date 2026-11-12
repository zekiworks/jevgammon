# Sourced by start.sh and locals.sh (URL, PORT and SSH_HOST set there): the model's snapshot, its /v1/models as the
# pinned server answers it (sieve-serve has no /health), and pinned(): the pinned server process on PORT, read over ssh
# (read-only).
SNAPSHOT=/home/cbasaran/decision-models/Sieve-31B-v3@8fcee858f7f20a50bfa3c8f984c22adb3cbb46a2
LABEL=Sieve
REPO=/home/cbasaran/decision-src/Sieve
REPO_COMMIT=1e64657c930f91db7119b5638774c0f11a77e441
ENV=/home/cbasaran/envs/sieve
# sha256 of "sha256sum" over the package's .py files (sorted, LC_ALL=C) as installed in ENV (sieve-decisions 0.5.1,
# a plain install from REPO) and as tracked in REPO at REPO_COMMIT: the same tree.
TREE_SHA=a3a5619727607bc06c73b1874f390931bcd4ec0f143ac045a08d31073c920bf7
HEAD_SHA=75b2073d12876068d15eca8dfc606c0e666979f5bef8e767fe478803a126ae0c
# AnyServer.info of sieve-serve 0.5.1: the --model path and the design read from the release's head.pt.
healthy() {
  curl -fsS -m 10 "$URL/v1/models" | python3 -c 'import json,sys; d=json.load(sys.stdin)
sys.exit(not (d == {"model": sys.argv[1], "design": "letters"}))' "$SNAPSHOT"
}
# Exactly `sieve-serve --model SNAPSHOT --host 0.0.0.0 --port PORT` from ENV (no --base, --no-merge or --graphs), no
# SIEVE_* variable in its environment (SIEVE_MAX_OPTIONS, the letters pack/branch sizes keep their defaults), the
# installed package the same .py tree as REPO at REPO_COMMIT (clean), sieve-decisions 0.5.1, the release's head.pt.
pinned() {
  local procs line="$ENV/bin/python3.12 $ENV/bin/sieve-serve --model $SNAPSHOT --host 0.0.0.0 --port $PORT"
  local sp=$ENV/lib/python3.12/site-packages
  procs=$(timeout 30 ssh -o BatchMode=yes "$SSH_HOST" "ps -eo args; echo @@; pid=\$(pgrep -xf '$line');
    [ -n \"\$pid\" ] && echo \"env \$(tr '\\0' '\\n' < /proc/\$pid/environ | grep -c '^SIEVE_')\";
    git -C $REPO rev-parse HEAD; git -C $REPO status --porcelain --untracked-files=no | wc -l;
    echo \"tree \$(cd $sp && find sieve -name '*.py' | LC_ALL=C sort | xargs sha256sum | sha256sum)\";
    echo \"repo \$(cd $REPO && git ls-files 'sieve/*.py' | LC_ALL=C sort | xargs sha256sum | sha256sum)\";
    grep -x 'Version: 0.5.1' $sp/sieve_decisions-0.5.1.dist-info/METADATA; sha256sum $SNAPSHOT/head.pt" 2>/dev/null) ||
    return 1
  grep -qxF "$line" <<<"$procs" && grep -qxF "env 0" <<<"$procs" &&
  grep -qxF "$REPO_COMMIT" <<<"$procs" && grep -qxF 0 <<<"$procs" &&
  grep -qxF "tree $TREE_SHA  -" <<<"$procs" && grep -qxF "repo $TREE_SHA  -" <<<"$procs" &&
  grep -qxF "Version: 0.5.1" <<<"$procs" && grep -qxF "$HEAD_SHA  $SNAPSHOT/head.pt" <<<"$procs"
}
