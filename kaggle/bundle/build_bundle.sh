#!/bin/bash
# build_bundle.sh — stage the offline Kaggle datasets on Vast. Run AFTER the W1 config is locked.
# Produces (upload each as a Kaggle dataset):
#   $OUT/upload_env/proof-pilot-env.tar.zst  -> "proof-pilot-env" : ONE archive = pybase + venv +
#        patches + humming + warm caches + repo subset + uv
#   $OUT/model/                              -> "proof-pilot-32b"  : ONLY the chosen CONFIG's weights + dflash draft
#
# The env is a SINGLE .tar.zst (not a raw dir): the venv has ~81k files (slow/limit-prone as loose
# dataset files) and is NOT self-contained — its stdlib lives in the standalone CPython ($BASE), so
# that MUST ship too (as pp-env/pybase). bootstrap.sh extracts to /tmp and rewrites pyvenv.cfg home.
# tar-from-source (no cp staging) avoids the cp-hardlink-break that doubled the venv to 21G.
#
# Usage:  CONFIG=w4a8 WHAT=both OUT=/workspace/kaggle_bundle bash build_bundle.sh
#   WHAT ∈ { env | model | code | both }   (default both; "env" = ignore model, useful when model
#     not locked; "code" = ONLY the small proof-pilot-code dataset = volatile running code, for
#     fast re-uploads without rebaking the 11G env — the notebook prefers it over the env's copy)
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONFIG="${CONFIG:-w4a8}"
WHAT="${WHAT:-both}"
OUT="${OUT:-/workspace/kaggle_bundle}"
VENV="${VENV:-/workspace/sglang-nightly-py312-venv}"
BASE="${BASE:-/.uv/python_install/cpython-3.12.13-linux-x86_64-gnu}"   # standalone CPython (stdlib!)
BUNDLE="${BUNDLE:-/workspace/models/proof-pilot-deploy-bundle}"
GPTQ="${GPTQ:-$REPO/quantization/out/soft-distill-32b-gptq-w4a16}"
HUMMING="${HUMMING:-/tmp/humming-survey}"
MODEL_OUT="$OUT/model"
mkdir -p "$OUT"

# The volatile "running code" subset — orchestration + serving code read from $REPO at RUNTIME
# (proof_agent, run*.py, serve_final.sh, the helper dirs/patches serve_final references). The
# sglang patches themselves are separately BAKED into the venv at build time, so the heavy env
# rarely changes; this subset changes often. Shared by build_env (folded into the big archive)
# and build_code (the small standalone `proof-pilot-code` dataset for fast re-uploads).
REPO_SUBSET=(
  kaggle deploy/dflash deploy/w4a8
  deploy/sm120/apply_dflash_patches.sh deploy/sm120/patch_decode_tune.py
  kaggle/serve/enable_swa_config.py deploy/sm120/gqa_packed_extend.py
  deploy/sm120/patch_gqa_packed_extend.py
  quantization/out/soft-distill-32b-gptq-w4a16/recipe.yaml
)
stage_repo_subset() {   # $1 = a dir that will CONTAIN proof-pilot/
  local root="$1/proof-pilot" p
  rm -rf "$root"; mkdir -p "$root"
  for p in "${REPO_SUBSET[@]}"; do
    mkdir -p "$root/$(dirname "$p")"
    cp -a "$REPO/$p" "$root/$p" 2>/dev/null || echo "  (skip $p)"
  done
  # drop dev artifacts so the (often re-uploaded) code stays tiny
  find "$root" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
  rm -f "$root"/kaggle/proof_agent/v2/trace_*.json \
        "$root"/kaggle/proof_agent/v2/*.events.jsonl \
        "$root"/kaggle/proof_agent/v2/run_summary_*.json 2>/dev/null || true
}

build_code() {
  # the SMALL, frequently-updated dataset: just the runtime code subset. The notebook points REPO
  # at this mount (read-only import) so iterating on the loop/serve code needs only this fast
  # re-upload, never a full env rebake.
  local UPLOAD_CODE="$OUT/upload_code"
  echo "=== code dataset: volatile running code (proof_agent + run*.py + serve_final + patches) ==="
  stage_repo_subset "$UPLOAD_CODE"
  cat > "$UPLOAD_CODE/dataset-metadata.json" <<'JSON'
{
  "title": "proof-pilot-code",
  "id": "threerabbits/proof-pilot-code",
  "licenses": [{"name": "other"}]
}
JSON
  echo "[build_bundle] code -> $UPLOAD_CODE/proof-pilot ($(du -sh "$UPLOAD_CODE/proof-pilot" | cut -f1))"
  echo "[build_bundle] create once:  kaggle datasets create  -p $UPLOAD_CODE --dir-mode skip"
  echo "[build_bundle] then update :  kaggle datasets version -p $UPLOAD_CODE -m <msg> --dir-mode skip"
}

build_env() {
  # NOTE: gzip CONTENT, but the upload filename ends in .bin (not .tar.gz) on purpose: Kaggle
  # AUTO-EXTRACTS recognized archives (.tar.gz/.zip) on dataset creation, which chokes on this 11G/
  # ~81k-file venv and FAILS the version. An opaque extension makes Kaggle store it as a blob.
  # Decompression is by gzip MAGIC bytes (name-agnostic) in bootstrap.sh / the notebook.
  local UPLOAD="$OUT/upload_env" TAR="$OUT/env.tar" GZ="$OUT/upload_env/proof-pilot-env.bin"
  local EXTRA="$OUT/extra"
  rm -rf "$UPLOAD" "$EXTRA"; mkdir -p "$UPLOAD" "$EXTRA/pp-env/proof-pilot"
  rm -f "$TAR"

  echo "=== env [0/7] repo subset + uv (small, real copy) ==="
  stage_repo_subset "$EXTRA/pp-env"
  cp "$(command -v uv)" "$EXTRA/pp-env/uv" 2>/dev/null || true

  # tar-append each component under a renamed prefix (uncompressed; -r needs no compression)
  echo "=== env [1/7] pybase (~111M, interpreter + stdlib) ==="
  tar -C "$(dirname "$BASE")" -cf "$TAR" \
    --transform="s|^$(basename "$BASE")|pp-env/pybase|" "$(basename "$BASE")"
  echo "=== env [2/7] venv (~11G, patches pre-baked) ==="
  tar -C "$(dirname "$VENV")" -rf "$TAR" \
    --transform="s|^$(basename "$VENV")|pp-env/venv|" "$(basename "$VENV")"
  echo "=== env [3/7] humming pkg ==="
  tar -C "$HUMMING" -rf "$TAR" --transform='s|^humming|pp-env/humming|' humming
  echo "=== env [4/7] humming JIT cache ==="
  tar -C "$HOME/.humming" -rf "$TAR" --transform='s|^cache|pp-env/humming_cache|' cache
  echo "=== env [5/7] flashinfer cache ==="
  tar -C "$HOME/.cache" -rf "$TAR" --transform='s|^flashinfer|pp-env/flashinfer_cache|' flashinfer
  echo "=== env [6/7] extras (proof-pilot subset + uv) ==="
  tar -C "$EXTRA" -rf "$TAR" pp-env
  # gzip, NOT zstd: the Kaggle image has no `zstd` binary and scoring is offline (no pip), so
  # `tar -I zstd` fails there. gzip is universal (tar built-in + python stdlib). pigz if present.
  echo "=== env [7/7] compress (gzip content, .bin name — Kaggle has no zstd + auto-extracts .tar.gz) ==="
  rm -f "$UPLOAD"/proof-pilot-env.tar.zst "$UPLOAD"/proof-pilot-env.tar.gz
  "$(command -v pigz || command -v gzip)" -c "$TAR" > "$GZ"
  rm -f "$TAR"; rm -rf "$EXTRA"

  cat > "$UPLOAD/dataset-metadata.json" <<'JSON'
{
  "title": "proof-pilot-env",
  "id": "threerabbits/proof-pilot-env",
  "licenses": [{"name": "other"}]
}
JSON
  echo "[build_bundle] env -> $GZ ($(du -h "$GZ" | cut -f1))"
  echo "[build_bundle] upload: kaggle datasets create -p $UPLOAD --dir-mode skip   (or 'version -p ... -m msg' to update)"
}

build_model() {
  mkdir -p "$MODEL_OUT"
  echo "=== model weights for CONFIG=$CONFIG + dflash draft ==="
  case "$CONFIG" in
    w4a8*|w4a16*) cp -a "$GPTQ" "$MODEL_OUT/soft-distill-32b-gptq-w4a16" ;;
    fp8*)         cp -a "$BUNDLE/soft-distill-32b-deploy" "$MODEL_OUT/soft-distill-32b-deploy" ;;
  esac
  # always ship the draft (cheap, lets you flip to dflash on Kaggle without re-upload)
  [ -d "$MODEL_OUT/dflash-32b-draft" ] || cp -a "$BUNDLE/dflash-32b-draft" "$MODEL_OUT/dflash-32b-draft"
  echo "[build_bundle] model -> $MODEL_OUT ($(du -sh "$MODEL_OUT" | cut -f1)). Upload as 'proof-pilot-32b'."
}

case "$WHAT" in
  env)   build_env ;;
  model) build_model ;;
  code)  build_code ;;
  both)  build_env; build_model ;;
  *) echo "unknown WHAT=$WHAT (env|model|code|both)"; exit 1 ;;
esac
echo "[build_bundle] done (WHAT=$WHAT)."
