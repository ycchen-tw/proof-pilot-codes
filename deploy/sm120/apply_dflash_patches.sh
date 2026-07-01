#!/bin/bash
# Apply the patches needed for DFlash deployment to a given venv's sglang (idempotent: the original is backed up to *.orig once).
# Works on both Vast and Kaggle (offline) — the patches are pure .py, just cp, no compilation needed.
#
# patches (source -> target inside the venv):
#   deploy/dflash/olmo2_sink_dflash.py     -> sglang/srt/models/olmo2.py            (target: OLMo3 + attention sink)
#   deploy/dflash/dflash_sink.py           -> sglang/srt/models/dflash.py           (draft: all-SWA + sink + window-size method)
#   deploy/dflash/dflash_worker_v2_ring.py -> sglang/srt/speculative/dflash_worker_v2.py
#        ^ spec-v2 worker + draft SWA KV ring (shrinks the draft KV pool from ~max_total to O(reqs*window),
#          saving ~5GB headroom; env SGLANG_DFLASH_DRAFT_RING is on by default, see README §6.9).
#        Only nightly (0.5.14.dev, with PR #23000) has dflash_worker_v2.py; 0.5.13 (spec-v1) lacks it -> auto-skip.
#   deploy/dflash/fused_kv_materialize_fullnorm.py -> sglang/srt/speculative/triton_ops/fused_kv_materialize.py
#        ^ Makes DFLASH fused-KV materialization support OLMo3's full-projection k_norm (RMS over kv_size,
#          not per-head). The stock kernel asserts k_norm is (n_layers, head_dim) -> a sink draft with
#          (n_layers, kv_size) falls back to a per-layer sequential eager loop. Adds a full-norm triton kernel:
#          single-stream decode +4% (291->303 tok/s), lossless (acceptance unchanged). Only nightly has this file; 0.5.13 lacks it -> auto-skip.
#   deploy/dflash/dflash_info_v2_swa_evict.py -> sglang/srt/speculative/dflash_info_v2.py
#        ^ DFLASH prepare_for_decode missed batch.maybe_evict_swa() (EAGLE/MTP have it, DFLASH did not),
#          and never incremented req.decode_batch_idx -> out-of-window SWA KV is never freed, #swa climbs to
#          ~total-window, and the 1/10-size swa pool hits its ceiling under long concurrency and retracts (~20k cutoff).
#          This patch adds the evict call + idx increment (mirroring eagle_info_v2.py) -> #swa drops from ~15k
#          back to ~6k (window+512*accept), retracts gone, lossless.
#          eviction frequency = sliding_window * SGLANG_SWA_EVICTION_INTERVAL_MULTIPLIER (0.125 recommended).
#          Only nightly has this file; 0.5.13 lacks it -> auto-skip.
#
# Usage: bash apply_dflash_patches.sh <venv_path> [--verify-only]
#   e.g. bash apply_dflash_patches.sh /workspace/sglang-nightly-py312-venv
set -euo pipefail

VENV="${1:?usage: apply_dflash_patches.sh <venv_path> [--verify-only]}"
MODE="${2:-apply}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"   # proof-pilot/ (script lives at deploy/sm120/)
SRC="$REPO/deploy/dflash"

# Find sglang/srt inside the venv
SROOT="$(echo "$VENV"/lib/python*/site-packages/sglang/srt 2>/dev/null | awk '{print $1}')"
if [ ! -d "$SROOT" ]; then
  echo "ERROR: sglang/srt not found under $VENV"; exit 1
fi
echo "[patch] venv=$VENV"
echo "[patch] sglang srt=$SROOT"

# target tuple: src_file  dest_relpath  required(1)|optional(0)
PATCHES=(
  "olmo2_sink_dflash.py|models/olmo2.py|1"
  "dflash_sink.py|models/dflash.py|1"
  "dflash_worker_v2_ring.py|speculative/dflash_worker_v2.py|0"
  "fused_kv_materialize_fullnorm.py|speculative/triton_ops/fused_kv_materialize.py|0"
  "dflash_info_v2_swa_evict.py|speculative/dflash_info_v2.py|0"
)

apply_one() {
  local src="$SRC/$1" dest="$SROOT/$2" req="$3"
  if [ ! -f "$dest" ]; then
    if [ "$req" = "1" ]; then echo "  MISSING dest (required): $dest"; return 1
    else echo "  skip (not present in this sglang): $2"; return 0; fi
  fi
  if [ ! -f "$src" ]; then echo "  MISSING src: $src"; return 1; fi
  if [ "$MODE" = "--verify-only" ]; then
    if cmp -s "$src" "$dest"; then echo "  OK (applied): $2"; else echo "  NOT applied / differs: $2"; fi
    return 0
  fi
  [ -f "$dest.orig" ] || cp "$dest" "$dest.orig"   # backup once
  cp "$src" "$dest"
  echo "  patched: $2"
}

rc=0
for p in "${PATCHES[@]}"; do
  IFS='|' read -r s d r <<< "$p"
  apply_one "$s" "$d" "$r" || rc=1
done

# Remove stale .pyc to ensure the new files are loaded
[ "$MODE" = "--verify-only" ] || find "$SROOT/models" "$SROOT/speculative" -name '*.pyc' -delete 2>/dev/null || true

if [ "$MODE" = "--verify-only" ]; then echo "[patch] verify done"; else echo "[patch] done (rc=$rc)"; fi
exit $rc
