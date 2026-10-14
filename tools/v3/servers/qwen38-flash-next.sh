#!/usr/bin/env bash
# Qwen3.8-Flash-Next-FP8, plain OpenAI-compatible vLLM, TP4 over GPUs 0-3 (wave A).
#   tools/v3/servers/qwen38-flash-next.sh start|stop|status
# Same image, checkpoint and model flags as the v1 run (container qwen38-flash-next); the
# memory flags are smaller so that Gemma 4 31B fits on GPU 3 and ComfyUI keeps room on GPU 0.
source "$(dirname "$(readlink -f "$0")")/_lib.sh"

NAME=v3-qwen38-flash-next
PORT=8896
URL=http://127.0.0.1:$PORT/v1/models

case ${1:-} in
  start)
    # NCCL_P2P_DISABLE: direct GPU-to-GPU copies on this machine arrive corrupted although the
    # driver reports peer access (see ~/code/pplx-decider/server.py), so NCCL goes through host
    # memory. vLLM disables its custom all-reduce on more than two PCIe GPUs by itself.
    # The named volume keeps vLLM's torch.compile cache between starts.
    # VLLM_USE_STANDALONE_COMPILE=0 (and the AOT switches it requires off): standalone compile
    # forces inductor to autotune at compile time on random copies of the inputs, including
    # this rank's 12 GiB n-gram embedding table, which does not fit on GPU 0 next to ComfyUI.
    # The classic inductor adaptor tunes kernels on their first real call instead; with it the
    # profiled peak activation is 0.3 GiB (35 GiB in the v1 run).
    docker_up "$NAME" "$PORT" --runtime nvidia --gpus '"device=0,1,2,3"' --ipc host \
      -p "127.0.0.1:$PORT:8000" \
      -v /home/cbasaran/.cache/huggingface:/root/.cache/huggingface \
      -v v3-qwen38-vllm-cache:/root/.cache/vllm \
      -e HF_HUB_OFFLINE=1 -e NCCL_P2P_DISABLE=1 \
      -e VLLM_USE_STANDALONE_COMPILE=0 -e VLLM_USE_AOT_COMPILE=0 -e VLLM_USE_MEGA_AOT_ARTIFACT=0 \
      vllm/vllm-openai:qwen38-flash-next \
      Qwen/Qwen3.8-Flash-Next-FP8 \
      --revision 236dfdf285828023ca3bcd3f37366c58a3469b13 \
      --served-model-name qwen3.8-flash-next \
      --tensor-parallel-size 4 \
      --disable-custom-all-reduce \
      --gpu-memory-utilization 0.50 \
      --max-model-len 32768 \
      --max-num-seqs 16 \
      --max-num-batched-tokens 2048 \
      --limit-mm-per-prompt '{"image":0,"video":0}' \
      --enable-prefix-caching \
      --no-enable-flashinfer-autotune \
      --attention-config.indexer_kv_dtype fp8 \
      --reasoning-parser qwen3 \
      --max-logprobs 20
    docker_wait "$NAME" "$URL" 1200
    ;;
  stop) docker_down "$NAME" ;;
  status) docker_status "$NAME" "$URL" ;;
  *) die "usage: $0 start|stop|status" ;;
esac
