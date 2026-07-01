#!/usr/bin/env bash
# Bring up the DFlash server (target + sink draft) and run the client, then
# ALWAYS tear down. Bounded readiness wait + guaranteed cleanup (no hangs).
#
# Usage: IMG=<sif> TARGET=<dir> [DRAFT=<dir>] GPU=0 PORT=30010 [RUN_AB=1] bash serve_and_test_dflash.sh
set -euo pipefail

ROOT=${PP_ROOT:-$PWD}
HERE=$ROOT/deploy/dflash
IMG=${IMG:-${SGLANG_SIF:-/images/sglang.sif}}
GPU=${GPU:-0}
PORT=${PORT:-30010}
TARGET=${TARGET:-$ROOT/outputs/stage1-v2-7b-deploy}
DRAFT=${DRAFT:-$ROOT/outputs/dflash-canonical-sink-sglang-draft}
READY_TIMEOUT=${READY_TIMEOUT:-600}
RUN_AB=${RUN_AB:-0}
AB_PROMPTS=${AB_PROMPTS:-$HERE/ab_prompts.json}
AB_MAX_NEW_TOKENS=${AB_MAX_NEW_TOKENS:-400}
PYTHON=${PYTHON:-$ROOT/quantization/.venv/bin/python}
if [[ ! -x "$PYTHON" ]]; then
  PYTHON=python3
fi
NAME=$(basename "$TARGET")__$(basename "$DRAFT")
IMG_NAME=$(basename "$IMG" .sif)
LOG=$HERE/server_dflash_${IMG_NAME}_${NAME}.log

echo "=== dflash serve+test: image=$IMG_NAME target=$NAME on GPU$GPU port $PORT ==="
: > "$LOG"
IMG=$IMG GPU=$GPU PORT=$PORT TARGET=$TARGET DRAFT=$DRAFT bash "$HERE/run_dflash_server.sh" >>"$LOG" 2>&1 &
SRV_PID=$!

cleanup() {
  echo "--- tearing down dflash server (pid $SRV_PID) ---"
  pkill -P "$SRV_PID" 2>/dev/null || true
  kill "$SRV_PID" 2>/dev/null || true
  pkill -f "launch_server --model-path $TARGET" 2>/dev/null || true
  sleep 3
  pkill -9 -f "launch_server --model-path $TARGET" 2>/dev/null || true
}
trap cleanup EXIT

ready=0
for ((i=0; i<READY_TIMEOUT; i+=3)); do
  if grep -q "The server is fired up and ready to roll" "$LOG" 2>/dev/null; then ready=1; break; fi
  if ! kill -0 "$SRV_PID" 2>/dev/null; then echo "!! server process exited early"; break; fi
  if grep -qiE "Traceback|RuntimeError|CUDA error|AssertionError|Scheduler hit an exception" "$LOG" 2>/dev/null; then
    echo "!! error detected in server log"; break; fi
  sleep 3
done

if [[ $ready -eq 1 ]]; then
  echo ">>> server READY"
  grep -i "attention-sink\|DFlash\|draft" "$LOG" | tail -3
  "$PYTHON" "$HERE/test_dflash_client.py" --port "$PORT" --max-new-tokens 200 --temp "${TEMP:-0}"
  if [[ "$RUN_AB" == "1" ]]; then
    "$PYTHON" "$HERE/ab_client.py" \
      --port "$PORT" \
      --prompts-file "$AB_PROMPTS" \
      --max-new-tokens "$AB_MAX_NEW_TOKENS" \
      --temp "${TEMP:-0}" \
      --tokenizer "$TARGET"
  fi
  echo ">>> DFLASH SMOKE OK: target=$NAME"
else
  echo ">>> DFLASH SMOKE FAILED: target=$NAME. Last server log:"; tail -30 "$LOG"
  exit 1
fi
