#!/bin/bash
# Serve the soft_distill_v2 7B (olmo3_sink, bf16) on 1 GPU via sglang 0.5.13.
# bind-mounts deploy/target/olmo2_sink.py over the in-image olmo2 model class (gpt-oss-style
# sink + olmo3 yarn). No quantization, no sink merge. Run inside job 107743 on the GPU node:
#   bash evaluation_local/servers/serve_sd.sh   (override PROOF_PILOT_ROOT / SGLANG_SIF as needed)
set -euo pipefail
ROOT="${PROOF_PILOT_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
SGL=/sgl-workspace/sglang/python/sglang/srt
PORT=${PORT:-30000}
CTX=${CTX:-200000}
GPU=${GPU:-0}
QUANT=${QUANT:-fp8}              # fp8 = online dynamic fp8 weight quant (7B 14->~7GB); "" = bf16
KVDTYPE=${KVDTYPE:-fp8_e4m3}     # fp8 KV cache (half KV mem). MUST be e4m3 to keep fa3 (sink-correct);
                                 # e5m2 forces sglang to fall back to triton backend. "auto" = bf16 KV
MEMFRAC=${MEMFRAC:-0.85}
QFLAG=(); [ -n "$QUANT" ] && QFLAG=(--quantization "$QUANT")
echo "[serve_sd] host=$(hostname) gpu=$GPU port=$PORT ctx=$CTX quant=${QUANT:-bf16} kv=$KVDTYPE model=stage1-v2-7b-softdistill-v2-deploy"
exec env CUDA_VISIBLE_DEVICES="$GPU" apptainer exec --nv \
  --bind "$ROOT" \
  --bind "$ROOT/deploy/target/olmo2_sink.py:$SGL/models/olmo2.py" \
  "${SGLANG_SIF:-/images/sglang.sif}" \
  python -m sglang.launch_server \
    --model-path "$ROOT/outputs/stage1-v2-7b-softdistill-v2-deploy" \
    --host 127.0.0.1 --port "$PORT" --tp 1 \
    --attention-backend fa3 --mem-fraction-static "$MEMFRAC" \
    --context-length "$CTX" \
    "${QFLAG[@]}" --kv-cache-dtype "$KVDTYPE" \
    --reasoning-parser deepseek-r1
