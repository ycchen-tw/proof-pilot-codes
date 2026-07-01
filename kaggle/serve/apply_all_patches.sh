#!/bin/bash
# apply_all_patches.sh — apply all sglang patches needed for the 32B deployment to a given venv (idempotent).
#   1) dflash 4 patches (olmo2_sink + dflash_sink + worker_v2_ring + fused_kv_fullnorm)
#   2) w4a8 humming patch (compressed_tensors_wNa16, env-gated by SGLANG_USE_HUMMING_W4A8)
# All pure .py copies, no compilation needed; works offline on Kaggle.
# Usage: bash apply_all_patches.sh <venv_path> [--verify-only]
set -euo pipefail
VENV="${1:?usage: apply_all_patches.sh <venv_path> [--verify-only]}"
MODE="${2:-apply}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"   # proof-pilot/

echo "=== dflash patches ==="
bash "$REPO/deploy/sm120/apply_dflash_patches.sh" "$VENV" ${MODE/apply/}
if [ "$MODE" = "--verify-only" ]; then
  echo "=== w4a8 humming patch (verify) ==="
  DST="$(echo "$VENV"/lib/python*/site-packages/sglang/srt/layers/quantization/compressed_tensors/schemes/compressed_tensors_wNa16.py)"
  grep -qi humming "$DST" && echo "  OK (humming applied): compressed_tensors_wNa16.py" || echo "  NOT applied: compressed_tensors_wNa16.py"
  echo "=== decode-tune patch (verify) ==="
  python "$REPO/deploy/sm120/patch_decode_tune.py" "$VENV" --verify-only
  echo "=== gqa-packed extend patch (verify) ==="
  python "$REPO/deploy/sm120/patch_gqa_packed_extend.py" "$VENV" --verify-only
else
  echo "=== w4a8 humming patch ==="
  bash "$REPO/deploy/w4a8/apply_w4a8_patch.sh" "$VENV"
  echo "=== decode-tune patch (env-gate BLOCK_N/num_stages) ==="
  python "$REPO/deploy/sm120/patch_decode_tune.py" "$VENV"
  echo "=== gqa-packed extend patch (env-gate SGLANG_GQA_PACKED_EXTEND) ==="
  python "$REPO/deploy/sm120/patch_gqa_packed_extend.py" "$VENV"
fi
echo "[apply_all_patches] done"
