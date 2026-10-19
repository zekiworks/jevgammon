#!/usr/bin/env bash
# Qwen3.8 Flash Next for League 2 on DGX Spark spark3 (192.168.1.139, GB10, 121 GB unified),
# run from this machine over ssh; bariton's GPUs stay free.
#   tools/v3/servers/spark3-flashnext.sh start|stop|status|probe
# Served with the MiaAI-Lab single-Spark recipe (github MiaAI-Lab/Qwen3.8-Flash-Next-Single-DGX-Spark,
# ~/code/Qwen3.8-Flash-Next-Single-DGX-Spark, its .env as on spark2), image
# vllm/vllm-openai:qwen38-flash-next and checkpoint Mia-AiLab/Qwen3.8-Flash-Next-NVFP4, all copied
# from spark2 (docker save | docker load, tar of the hub cache; blob checksums equal). The recipe
# keeps the n-gram (PLE) table off the GPU in a memory-mapped file and caps the GPU budget from
# the host side; MTP speculation (3 tokens) stays on. Overrides of its .env, for the league:
# port 8896, 32k context (the v1 bariton server's), 8 sequences (League 2 asks up to 8 at a time
# per setup) and top-20 logprobs for the letter probabilities.
source "$(dirname "$(readlink -f "$0")")/_lib.sh"

HOST=spark3
ADDR=192.168.1.139
PORT=8896
REPO=code/Qwen3.8-Flash-Next-Single-DGX-Spark
ENV="PORT=$PORT MAX_MODEL_LEN=32768 MAX_NUM_SEQS=8 EXTRA_VLLM_ARGS='--max-logprobs 20'"

remote() { ssh -o BatchMode=yes "$HOST" "cd ~/$REPO && $*"; }

case ${1:-} in
  start) remote "$ENV ./start.sh" ;;
  stop) remote "./stop.sh" ;;
  status)
    remote "docker ps -a --filter name=vllm-fn-tp1 --format '{{.Names}} {{.Status}}'"
    curl -s -o /dev/null -w "http %{http_code}\n" "http://$ADDR:$PORT/health" || true
    ;;
  probe) python3 "$(dirname "$(readlink -f "$0")")/probe_chat.py" "http://$ADDR:$PORT/v1" qwen3.8-flash-next ;;
  *) die "usage: $0 start|stop|status|probe" ;;
esac
