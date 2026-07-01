#!/bin/bash
# Bare-metal SGLang launcher for the local ProofBench eval.
# Usage: serve.sh <gpus> <tp> <port> <served-name> <model-path> <log> [extra sglang args...]
#   gpus: CUDA_VISIBLE_DEVICES value, e.g. "0" or "0,1"
# Examples:
#   serve.sh 0 1 30000 stage1-v2-7b outputs/stage1-v2-7b-deploy LOG --reasoning-parser deepseek-r1
#   serve.sh 0 1 30001 native-7b ${OLMO3_7B:-/models/Olmo-3-7B-Think} LOG
set -u
GPUS=$1; TP=$2; PORT=$3; SERVED=$4; MODEL=$5; LOG=$6; shift 6
VENV="${SGLANG_VENV:-.venv-sglang}"
CTX="${CTX:-65536}"
MEMFRAC="${MEMFRAC:-0.90}"
MAXREQ="${MAXREQ:-32}"
CHUNK="${CHUNK:-8192}"
# ninja lives in $VENV/bin; flashinfer fa3 JIT needs it on PATH. JIT cache -> local /tmp (fast FS).
export PATH="$VENV/bin:$PATH"
JITDIR=/tmp/$USER/sglang_jit; mkdir -p "$JITDIR"
export FLASHINFER_WORKSPACE_BASE="$JITDIR" TVM_FFI_CACHE_DIR="$JITDIR" \
       DG_JIT_CACHE_DIR="$JITDIR" TORCHINDUCTOR_CACHE_DIR="$JITDIR/inductor"
echo "[serve] gpus=$GPUS tp=$TP port=$PORT served=$SERVED ctx=$CTX mem=$MEMFRAC model=$MODEL extra=$* -> $LOG"
CUDA_VISIBLE_DEVICES=$GPUS \
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
exec "$VENV/bin/python" -m sglang.launch_server \
  --model-path "$MODEL" \
  --served-model-name "$SERVED" \
  --tp "$TP" \
  --host 127.0.0.1 --port "$PORT" \
  --attention-backend fa3 \
  --mem-fraction-static "$MEMFRAC" \
  --context-length "$CTX" \
  --max-running-requests "$MAXREQ" \
  --chunked-prefill-size "$CHUNK" \
  "$@" > "$LOG" 2>&1
