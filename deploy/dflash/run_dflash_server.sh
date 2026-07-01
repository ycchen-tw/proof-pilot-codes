#!/usr/bin/env bash
# Launch sglang serving the olmo3_sink target + DFlash sink draft (single-GPU).
# Bind-mounts the OLMo3+sink draft over srt/models/dflash.py and the
# capture-enabled target over srt/models/olmo2.py.
set -euo pipefail

ROOT=${PP_ROOT:-$PWD}
SGL=/sgl-workspace/sglang/python/sglang/srt
IMG=${IMG:-${SGLANG_SIF:-/images/sglang.sif}}
DEPLOY=$ROOT/deploy/dflash
GPU=${GPU:-0}
PORT=${PORT:-30010}
MEM_FRACTION_STATIC=${MEM_FRACTION_STATIC:-0.80}
CONTEXT_LENGTH=${CONTEXT_LENGTH:-32768}
EXTRA_ARGS=()
PYTHON_ENV=()
if [[ -n "${SGLANG_EXTRA_PYTHONPATH:-}" ]]; then
  PYTHON_ENV=(env "PYTHONPATH=$SGLANG_EXTRA_PYTHONPATH:${PYTHONPATH:-}")
fi
if [[ -n "${MAX_RUNNING_REQUESTS:-}" ]]; then
  EXTRA_ARGS+=(--max-running-requests "$MAX_RUNNING_REQUESTS")
fi
if [[ -n "${CUDA_GRAPH_MAX_BS:-}" ]]; then
  EXTRA_ARGS+=(--cuda-graph-max-bs "$CUDA_GRAPH_MAX_BS")
fi
if [[ "${DFLASH_DISABLE_OVERLAP:-1}" == "1" ]]; then
  EXTRA_ARGS+=(--disable-overlap-schedule)
fi
# DRAFT_QUANT: serve a quantized draft (e.g. compressed-tensors int4-MLP draft).
# Requires dflash_sink.py to thread quant_config to the MLP (patched).
if [[ -n "${DRAFT_QUANT:-}" ]]; then
  EXTRA_ARGS+=(--speculative-draft-model-quantization "$DRAFT_QUANT")
fi
# TARGET defaults to the bf16 deploy; set to a quantized checkpoint (e.g. the
# gptq-w4a16 dir) to run quantized target + DFlash draft together. Quantized
# targets auto-detect their quant_config; olmo2_sink_dflash.py's linears are all
# quant_config-aware, so no extra flags are needed.
TARGET=${TARGET:-$ROOT/outputs/stage1-v2-7b-deploy}
# DRAFT defaults to the canonical-convention draft. The legacy no-dup draft is
# still available at outputs/dflash-sink-sglang-draft but does not match native
# SGLang DFLASH block convention.
DRAFT=${DRAFT:-$ROOT/outputs/dflash-canonical-sink-sglang-draft}

[[ -f "$IMG" ]] || { echo "missing IMG: $IMG" >&2; exit 2; }
[[ -d "$TARGET" ]] || { echo "missing TARGET: $TARGET" >&2; exit 2; }
[[ -d "$DRAFT" ]] || { echo "missing DRAFT: $DRAFT" >&2; exit 2; }

CUDA_VISIBLE_DEVICES=$GPU apptainer exec --nv \
  --bind ${PP_BIND:-$ROOT} \
  --bind "$DEPLOY/dflash_sink.py:$SGL/models/dflash.py" \
  --bind "$DEPLOY/olmo2_sink_dflash.py:$SGL/models/olmo2.py" \
  "$IMG" \
  "${PYTHON_ENV[@]}" python -m sglang.launch_server \
    --model-path "$TARGET" \
    --speculative-algorithm DFLASH \
    --speculative-draft-model-path "$DRAFT" \
    --speculative-dflash-block-size 11 \
    --speculative-draft-window-size 128 \
    --attention-backend fa3 \
    --speculative-draft-attention-backend fa3 \
    --tp 1 \
    --mem-fraction-static "$MEM_FRACTION_STATIC" \
    --context-length "$CONTEXT_LENGTH" \
    --host 127.0.0.1 --port "$PORT" \
    --reasoning-parser deepseek-r1 \
    "${EXTRA_ARGS[@]}"
