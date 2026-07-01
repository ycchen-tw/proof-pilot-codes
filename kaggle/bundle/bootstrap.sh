#!/bin/bash
# bootstrap.sh — Kaggle notebook offline bootstrap (scoring runs with NO network). Idempotent.
# Extracts the single env archive to writable scratch, makes the RELOCATED venv usable
# (rewrites pyvenv.cfg so the bundled standalone CPython provides the stdlib — the venv ships
#  only site-packages and is NOT self-contained), restores warm caches, applies patches.
#
# Datasets mounted (read-only) — see bundle/build_bundle.sh / MANIFEST.md:
#   DS_ENV    : proof-pilot-env.tar.zst  (pybase + venv + humming + caches + proof-pilot subset + uv)
#   DS_MODEL  : model weights (target + draft)
# Usage:  DS_ENV=/kaggle/input/proof-pilot-env DS_MODEL=/kaggle/input/proof-pilot-32b \
#           source bootstrap.sh
set -uo pipefail

DS_ENV="${DS_ENV:-/kaggle/input/proof-pilot-env}"
DS_MODEL="${DS_MODEL:-/kaggle/input/proof-pilot-32b}"
WORK="${WORK:-/tmp/pp}"                 # writable scratch (Kaggle input is READ-ONLY)
export VENV="${VENV:-$WORK/venv}"
export PYBASE="${PYBASE:-$WORK/pybase}" # standalone CPython holding the stdlib

mkdir -p "$WORK" "$HOME/.cache" "$HOME/.humming"

# ---- 1. offline env ----
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export FLASHINFER_USE_CUDA_NORM=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export HF_HOME="$WORK/hf_home"; mkdir -p "$HF_HOME"
export CUDA_VISIBLE_DEVICES=0           # Kaggle = single GPU

# ---- 2. extract env archive -> writable scratch (idempotent: skip if venv already staged) ----
# The archive ships gzip CONTENT under an opaque name (proof-pilot-env.bin) so Kaggle stores it as a
# blob instead of auto-extracting it (which fails on the 11G venv). Detect by MAGIC bytes, not name:
# gzip=1f8b -> tar -xz (universal; Kaggle has no zstd); zstd=28b52ffd -> tar -I zstd if a binary exists.
if [ ! -x "$VENV/bin/python" ]; then
  ARC="$(ls "$DS_ENV"/proof-pilot-env.bin "$DS_ENV"/*.bin "$DS_ENV"/*.tar.gz "$DS_ENV"/*.tar.zst 2>/dev/null | head -1 || true)"
  if [ -n "$ARC" ]; then
    echo "[bootstrap] extracting $ARC -> $WORK"
    MAGIC="$(od -An -tx1 -N4 "$ARC" | tr -d ' \n')"
    case "$MAGIC" in
      1f8b*)    tar -xzf "$ARC" -C "$WORK" --strip-components=1 ;;                          # gzip; strip pp-env/
      28b52ffd) tar -x -I 'zstd -d --long=31' -f "$ARC" -C "$WORK" --strip-components=1 ;;  # zstd
      *) echo "[bootstrap] FATAL: unknown archive magic $MAGIC for $ARC"; return 1 2>/dev/null || exit 1 ;;
    esac
  elif [ -d "$DS_ENV/pp-env/venv" ]; then        # Kaggle auto-extracted the archive
    echo "[bootstrap] copying pre-extracted env -> $WORK"
    cp -a "$DS_ENV/pp-env/." "$WORK/"
  elif [ -d "$DS_ENV/venv" ]; then               # legacy raw-dir layout
    echo "[bootstrap] copying raw env dir -> $WORK"
    cp -a "$DS_ENV/." "$WORK/"
  else
    echo "[bootstrap] FATAL: no env archive/dir under $DS_ENV"; return 1 2>/dev/null || exit 1
  fi
fi

# ---- 3. relocate the venv: point pyvenv.cfg at the bundled standalone CPython ----
# Without this the venv python's sys.base_prefix points at the BUILD HOST's /.uv path (absent on
# Kaggle) -> no stdlib -> `import os` dies. Rewriting `home` makes stdlib resolve from $PYBASE.
if [ -f "$VENV/pyvenv.cfg" ] && [ -d "$PYBASE/bin" ]; then
  sed -i "s|^home = .*|home = $PYBASE/bin|" "$VENV/pyvenv.cfg"
fi
"$VENV/bin/python" -c "import sys,os; assert os.path.realpath(sys.base_prefix)==os.path.realpath('$PYBASE'), sys.base_prefix; import sglang, torch; print('[bootstrap] sglang', sglang.__version__, 'torch', torch.__version__, '| base', sys.base_prefix)"

# ---- 4. restore warm caches (avoid first-call JIT at scoring time) ----
[ -d "$WORK/flashinfer_cache" ] && { mkdir -p "$HOME/.cache/flashinfer"; cp -rn "$WORK/flashinfer_cache/." "$HOME/.cache/flashinfer/"; }
[ -d "$WORK/humming_cache" ]    && { mkdir -p "$HOME/.humming/cache"; cp -rn "$WORK/humming_cache/." "$HOME/.humming/cache/"; }

# ---- 5. paths consumed by serve_final.sh ----
export REPO="${REPO:-$WORK/proof-pilot}"      # the repo subset shipped in the env archive
# HUMMING_DIR = the dir CONTAINING the `humming/` package (serve_final sets HUMMING_PATH=$HUMMING_DIR,
# the w4a8 glue does sys.path.insert(HUMMING_PATH); import humming). The package extracts to
# $WORK/humming, so its parent $WORK is the path to put on sys.path.
export HUMMING_DIR="${HUMMING_DIR:-$WORK}"

# ---- 6. apply patches (idempotent; pre-baked into the shipped venv, re-apply is a no-op cmp) ----
bash "$REPO/kaggle/serve/apply_all_patches.sh" "$VENV" || true

# ---- 7. SWA on the target config(s) (config-only; idempotent) ----
for d in "$DS_MODEL"/*; do
  [ -f "$d/config.json" ] && "$VENV/bin/python" "$REPO/kaggle/serve/enable_swa_config.py" "$d" || true
done

echo "[bootstrap] ready. VENV=$VENV PYBASE=$PYBASE REPO=$REPO HUMMING_DIR=$HUMMING_DIR DS_MODEL=$DS_MODEL"
