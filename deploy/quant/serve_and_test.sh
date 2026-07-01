#!/usr/bin/env bash
# Bring a quantized checkpoint up under sglang, wait until ready (or time out),
# run the smoke client, then ALWAYS tear the server down. Designed to never hang:
# bounded readiness wait + guaranteed cleanup.
#
# Usage: MODEL=<dir> GPU=3 PORT=30030 [READY_TIMEOUT=420] [QUANT=...] \
#          bash serve_and_test.sh
set -uo pipefail

ROOT=${PP_ROOT:-$PWD}
HERE=$ROOT/deploy/quant
MODEL=${MODEL:?set MODEL}
GPU=${GPU:-3}
PORT=${PORT:-30030}
READY_TIMEOUT=${READY_TIMEOUT:-420}
NAME=$(basename "$MODEL")
LOG=$HERE/server_${NAME}.log

echo "=== serve_and_test: $NAME on GPU$GPU port $PORT ==="
: > "$LOG"
MODEL=$MODEL GPU=$GPU PORT=$PORT bash "$HERE/run_quant_server.sh" >>"$LOG" 2>&1 &
SRV_PID=$!

cleanup() {
  echo "--- tearing down server (pid $SRV_PID) ---"
  pkill -P "$SRV_PID" 2>/dev/null || true
  kill "$SRV_PID" 2>/dev/null || true
  # apptainer child + sglang scheduler procs
  pkill -f "launch_server --model-path $MODEL" 2>/dev/null || true
  sleep 3
  pkill -9 -f "launch_server --model-path $MODEL" 2>/dev/null || true
}
trap cleanup EXIT

# wait for ready / failure / timeout
ready=0
for ((i=0; i<READY_TIMEOUT; i+=3)); do
  if grep -q "The server is fired up and ready to roll" "$LOG" 2>/dev/null; then ready=1; break; fi
  if ! kill -0 "$SRV_PID" 2>/dev/null; then echo "!! server process exited early"; break; fi
  if grep -qiE "Traceback|RuntimeError|CUDA error|AssertionError|Error:" "$LOG" 2>/dev/null; then
    echo "!! error detected in server log"; break; fi
  sleep 3
done

if [[ $ready -eq 1 ]]; then
  echo ">>> server READY; loaded sinks line:"; grep -i "attention-sink" "$LOG" | tail -1
  echo ">>> detected quant: "; grep -iE "quant|compressed|mxfp4|nvfp4|w4a16|fp8|marlin|awq|gptq" "$LOG" | grep -iv "model-path" | tail -3
  "$ROOT/quantization/.venv/bin/python" "$HERE/test_quant_client.py" --port "$PORT" --temp 0 --max-new-tokens 200
  echo ">>> SMOKE OK: $NAME"
else
  echo ">>> SMOKE FAILED: $NAME (not ready). Last server log:"; tail -25 "$LOG"
fi
