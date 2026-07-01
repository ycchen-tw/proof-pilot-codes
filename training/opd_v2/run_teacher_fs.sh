#!/usr/bin/env bash
# OPD v2 teacher scoring service = sglang 原生 server + hidden-extract patches，
# **但 /score 支援 out_path → server-side 寫 shared FS、回 handle JSON**（P7 修正，V12）。
#
# 與 v1 `training/opd/examples/run_teacher_service.sh` 的差別：
#   - http_server 換成 opd_v2/teacher_patch/http_server.py（含 out_path 分支；其餘 3 個 patch 沿用
#     teacher_extract/_patched，同一 image 版本，已驗一致）。
#   - 多設 OPD_V2_SRC，讓容器內 /score 能 `from opd_v2.hidden_store import write_hidden`
#     （hidden 檔格式單一 source-of-truth）。
#
#   CUDA_VISIBLE_DEVICES=0,1,2,3 ./run_teacher_fs.sh --tp 4 --port 8100
set -euo pipefail
TP=4; PORT=8100
while [ $# -gt 0 ]; do case "$1" in --tp) TP="$2"; shift 2;; --port) PORT="$2"; shift 2;; *) echo "unknown arg: $1" >&2; exit 1;; esac; done

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${REPO:-$(cd "$(dirname "$0")/../.." && pwd)}"
SIF=${SIF:-/images/sglang.sif}
TE="$REPO/training/teacher_extract"
PDIR="$TE/_patched"                                  # deepseek_v4 / scheduler / output_processor
V2HTTP="$HERE/teacher_patch/http_server.py"          # opd_v2: out_path FS-write 版
MODEL=${MODEL:-/models/DeepSeek-V4-Flash}
SPOOL=${SPOOL:-/dev/shm/opd-v2-teacher-spool}        # 內部 bf16 spool（node-local tmpfs；非 v2 shared hidden）

for f in deepseek_v4.py scheduler.py scheduler_output_processor_mixin.py; do
  [ -f "$PDIR/$f" ] || { echo "缺 $PDIR/$f：先在 teacher_extract 跑 REPATCH 重生" >&2; exit 1; }
done
[ -f "$V2HTTP" ] || { echo "缺 $V2HTTP：先跑 opd_v2 的 regen（見 README）" >&2; exit 1; }
mkdir -p "$SPOOL"
SGL=${SGLANG_PKG_DIR:-/sgl-workspace/sglang/python/sglang}

DIST_ARGS=()
[ -n "${DIST_INIT_ADDR:-}" ] && DIST_ARGS+=(--dist-init-addr "$DIST_INIT_ADDR")
[ -n "${SGLANG_NCCL_PORT:-}" ] && DIST_ARGS+=(--nccl-port "$SGLANG_NCCL_PORT")

exec apptainer exec --nv \
  --bind /work \
  --bind "$PDIR/deepseek_v4.py:$SGL/srt/models/deepseek_v4.py" \
  --bind "$PDIR/scheduler.py:$SGL/srt/managers/scheduler.py" \
  --bind "$PDIR/scheduler_output_processor_mixin.py:$SGL/srt/managers/scheduler_output_processor_mixin.py" \
  --bind "$V2HTTP:$SGL/srt/entrypoints/http_server.py" \
  --env SGLANG_DSV4_HIDDEN_POST_NORM=1 \
  --env SGLANG_JIT_DEEPGEMM_FAST_WARMUP=1 \
  --env MALLOC_ARENA_MAX=4 \
  --env SGLANG_HIDDEN_SPOOL_DIR="$SPOOL" \
  --env SGLANG_HIDDEN_CODEC_DIR="$REPO/training/_common" \
  --env OPD_V2_SRC="$HERE/src" \
  --env OPD_TEACHER_MODEL_PATH="$MODEL" \
  --env OPD_SCORE_TOP1_CHUNK="${OPD_SCORE_TOP1_CHUNK:-1024}" \
  --env CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0,1,2,3}" \
  "$SIF" python3 -m sglang.launch_server \
    --model-path "$MODEL" --tp-size "$TP" --host 0.0.0.0 --port "$PORT" \
    "${DIST_ARGS[@]}" \
    --enable-return-hidden-states --disable-radix-cache \
    --chunked-prefill-size "${CHUNKED_PREFILL:-11264}" --mem-fraction-static "${MEMFRAC:-0.80}" \
    --max-running-requests "${MAXRUN:-128}" --disable-cuda-graph \
    --context-length "${TEACHER_CONTEXT_LEN:-${CONTEXT_LEN:-69632}}" --moe-runner-backend marlin \
    --watchdog-timeout 1800 --log-level info
