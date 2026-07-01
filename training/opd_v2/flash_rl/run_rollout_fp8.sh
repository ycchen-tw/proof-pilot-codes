#!/usr/bin/env bash
# Launch an OPD student rollout server with FP8 quantization + working
# update_weights_from_disk (repeated bf16 reload + re-quantize to fp8).
#
# This is run_rollout_service.sh + two extra knobs:
#   --quantization fp8 --load-format flash_rl   (online fp8 + RL reload loader)
# plus a bind-mount of the patched flash_rl loader (see patches/ + README.md).
# Without the patch, `--quantization fp8` + update_weights_from_disk CRASHES
# (transpose assert); stock flash_rl from_disk OOMs after a few reloads.
#
#   CUDA_VISIBLE_DEVICES=4 ./run_rollout_fp8.sh --port 8200
#
# Tunables via env: SIF MODEL PORT TP MEMFRAC MAXRUN CUDA_GRAPH_MAX_BS CHUNKED_PREFILL CONTEXT_LEN
#                   KV_CACHE_DTYPE SWA_RATIO   (long-context KV 省記憶體；見下)
#   CUDA_GRAPH_MAX_BS 預設 = MAXRUN：conc(MAXRUN)>10 時**必須**一起拉高，否則 cuda graph 只 capture 到
#   預設 bs，超過的 batch 退 eager 變慢（2026-06-20 KV-pool 測：graph 只到 bs=10 = 預設 MAXRUN）。
# Validated: sglang 0.5.12.post1, H200.
#   - TP=1 bf16-KV: 原始驗證（10/10 reload bit-exact）。
#   - TP=4 + fp8-KV(e4m3) + SWA-ratio: long-context 實測（2026-06-17）——三旗標可同時啟用、
#     update_weights_from_disk 6/6 success、reload→reload bit-exact、e4m3 保住 FA3。TP8 head 可整除亦可行。
#   - TP4 + fp8 + e4m3 + SWA r=0.2 + ctx131072 + memfrac0.85（2026-06-20 實測）：hybrid SWA pool 啟用，
#     full_layer_tokens=4,711,012 / swa_layer_tokens=942,202（115GB，avail 20.6GB）→ 長序列綁 full pool：
#     conc×avg_len ≤ 4.71M（avg 64k → ~72 條/replica）。OPD agentic 定 MAXRUN=64（見 run_agentic_mn.sbatch）。
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${ROOT:-$(cd "$(dirname "$0")/../../.." && pwd)}"

SIF=${SIF:-/images/sglang.sif}     # 0.5.12.post1
MODEL=${MODEL:-$ROOT/outputs/stage1-v2-7b-deploy}
PORT=8200; TP=1
while [ $# -gt 0 ]; do case "$1" in --port) PORT=$2; shift 2;; --tp) TP=$2; shift 2;; *) shift;; esac; done

SGL=${SGLANG_PKG_DIR:-/sgl-workspace/sglang/python/sglang}
SINK=$ROOT/deploy/target/olmo2_sink.py                  # in-engine sink target
LOADER=$HERE/patches/loader.py                          # patched flash_rl loader
LOADER_DST=$SGL/srt/model_loader/loader.py
MCFG=$HERE/patches/model_config.py                      # SWA-pool patch（讓 olmo3 開 hybrid SWA KV pool）
MCFG_DST=$SGL/srt/configs/model_config.py

# Regenerate the patched loader/model_config from THIS image if stale or you
# switched sglang versions (idempotent; see apply_patch.py / apply_swa_patch.py).
if [ "${REGEN_LOADER:-0}" = "1" ]; then
  apptainer exec "$SIF" cat "$LOADER_DST" > /tmp/_flashrl_stock.py
  python3 "$HERE/apply_patch.py" /tmp/_flashrl_stock.py "$LOADER"
  apptainer exec "$SIF" cat "$MCFG_DST" > /tmp/_mcfg_stock.py
  python3 "$HERE/patches/apply_swa_patch.py" /tmp/_mcfg_stock.py "$MCFG"
fi

PARSER_ARGS=(--reasoning-parser deepseek-r1 --tool-call-parser deepseekv4)
if [ "${SKIP_TOKENIZER_INIT:-0}" = "1" ]; then
  # OPD rollout is token-in/token-out; drop parsers (need a tokenizer/template).
  PARSER_ARGS=(--skip-tokenizer-init)
fi
EXTRA_ARGS=()
[ -n "${CONTEXT_LEN:-}" ] && EXTRA_ARGS+=(--context-length "$CONTEXT_LEN")
# long-context KV 省記憶體（2026-06-17 實測）：
#  - fp8 KV cache：用 fp8_e4m3（FA3 支援、mantissa 3-bit 較不失真）；fp8_e5m2 會逼 attn backend 退 triton。
[ -n "${KV_CACHE_DTYPE:-}" ] && EXTRA_ARGS+=(--kv-cache-dtype "$KV_CACHE_DTYPE")
#  - hybrid SWA memory pool：SWA 層 KV tokens / full 層 KV tokens 比例（olmo3 = 24 SWA : 8 full，window 4096）。
[ -n "${SWA_RATIO:-}" ] && EXTRA_ARGS+=(--swa-full-tokens-ratio "$SWA_RATIO")
#  - TP>1 + 多 replica/node：custom all-reduce 用 CUDA IPC handle,同節點 2 個 TP-group 在 cuda-graph
#    capture 下會撞 `custom_all_reduce.cuh: CUDA error: invalid argument`(2026-06-20 job131796 實爆,單
#    replica 本機測不到)→ 退 NCCL all-reduce(7B TP4 decode all-reduce 小,走 NVLink,吞吐影響可忽略)。
[ "${TP:-1}" -gt 1 ] && EXTRA_ARGS+=(--disable-custom-all-reduce)

# NOTE on memory: each reload needs transient scratch for the bf16->fp8
# re-quant. fp8 frees ~6GB of weights vs bf16; keep mem-fraction-static at a
# level that leaves headroom for the reload. 0.85 validated OK for 7B/TP1.
exec apptainer exec --nv \
  --bind /work \
  --bind "$SINK:$SGL/srt/models/olmo2.py" \
  --bind "$LOADER:$LOADER_DST" \
  --bind "$MCFG:$MCFG_DST" \
  --env CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}" \
  --env PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  "$SIF" python3 -m sglang.launch_server \
    --model-path "$MODEL" \
    --tp-size "$TP" \
    --host 0.0.0.0 --port "$PORT" \
    --quantization fp8 \
    --load-format flash_rl \
    --mem-fraction-static "${MEMFRAC:-0.85}" \
    --max-running-requests "${MAXRUN:-10}" \
    --cuda-graph-max-bs "${CUDA_GRAPH_MAX_BS:-${MAXRUN:-10}}" \
    --chunked-prefill-size "${CHUNKED_PREFILL:-4096}" \
    --disable-radix-cache \
    "${EXTRA_ARGS[@]}" \
    "${PARSER_ARGS[@]}"
