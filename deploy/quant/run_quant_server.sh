#!/usr/bin/env bash
# Serve a quantized stage1-v2-7b olmo3_sink checkpoint under sglang.
#
# The quantized dirs (quantization/out/stage1-v2-7b-<scheme>) already carry a
# config with architectures=Olmo3SinkForCausalLM, legacy rope keys, sink_init_value
# and a compressed-tensors quantization_config -- sglang auto-detects the quant
# method. We only bind-mount the sink-aware olmo2 model class over the image.
#
# Usage: MODEL=<dir> GPU=0 PORT=30020 [QUANT=<override>] bash run_quant_server.sh
set -euo pipefail

ROOT=${PP_ROOT:-$PWD}
SGL=/sgl-workspace/sglang/python/sglang/srt
IMG=${SGLANG_SIF:-/images/sglang.sif}
SINK=$ROOT/deploy/target/olmo2_sink.py
# patched compressed-tensors: adds a dense MXFP4 (float4-group) weight-only
# scheme; identical to the image's file otherwise, so safe to always bind.
CT_PATCH=$ROOT/deploy/quant/patches/compressed_tensors.py
CT_DST=$SGL/layers/quantization/compressed_tensors/compressed_tensors.py

MODEL=${MODEL:?set MODEL to a quantized checkpoint dir}
GPU=${GPU:-0}
PORT=${PORT:-30020}
ATTN=${ATTN:-fa3}
MEMFRAC=${MEMFRAC:-0.85}
CTX=${CTX:-32768}
KVDTYPE=${KVDTYPE:-}   # e.g. fp8_e4m3 -> loads calibrated k_scale/v_scale from config

EXTRA=()
[[ -n "${QUANT:-}" ]] && EXTRA+=(--quantization "$QUANT")
[[ -n "$KVDTYPE" ]] && EXTRA+=(--kv-cache-dtype "$KVDTYPE")

set -x
CUDA_VISIBLE_DEVICES=$GPU apptainer exec --nv \
  --env PP_MXFP4_KERNEL="${PP_MXFP4_KERNEL:-dequant}" \
  --bind ${PP_BIND:-$ROOT} \
  --bind "$SINK:$SGL/models/olmo2.py" \
  --bind "$CT_PATCH:$CT_DST" \
  "$IMG" \
  python -m sglang.launch_server \
    --model-path "$MODEL" \
    --attention-backend "$ATTN" \
    --tp 1 \
    --mem-fraction-static "$MEMFRAC" \
    --context-length "$CTX" \
    --host 127.0.0.1 --port "$PORT" \
    --reasoning-parser deepseek-r1 \
    "${EXTRA[@]}"
