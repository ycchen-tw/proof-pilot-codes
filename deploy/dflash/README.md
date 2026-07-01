# DFlash SGLang deployment (speculative decoding)

Serve the `olmo3_sink` target together with a trained DFlash draft for speculative decoding.
On a single H200 with the spec-v2 (overlap) nightly image: 7B ~468 tok/s (accept length 3.81),
32B ~124 tok/s (accept 2.90) — +23.7% / +5.2% over the SGLang 0.5.13 non-overlap baseline.

## Components
| file | role |
|---|---|
| `olmo2_sink_dflash.py` | target model class + DFlash aux-hidden capture; bind-mounted over sglang `srt/models/olmo2.py` |
| `dflash_sink.py` | DFlash draft rewritten to OLMo3+sink (post-norm, full-projection QK-norm, per-head sink, all-SWA); bind-mounted over `srt/models/dflash.py` |
| `convert_draft.py` | trained draft (`final.pt`/`latest.pt`) → sglang-loadable dir |
| `make_target_deploy.py` | training checkpoint → servable target dir (rope-legacy config) |
| `fused_kv_materialize_fullnorm.py` (`.patch`) | full-projection RMS kernel so the sink draft uses fused-KV materialization instead of the slower sequential append |
| `dflash_worker_v2_ring.py` (`.patch`), `dflash_info_v2_swa_evict.py` | SWA-eviction ring worker for long-context spec-v2 |
| `run_dflash_server.sh`, `serve_and_test_dflash.sh` | launch + bounded smoke test / teardown |
| `test_dflash_client.py` | client; reports output + `spec_accept_length` |

## Usage
```bash
python deploy/dflash/make_target_deploy.py     # build target deploy dir
python deploy/dflash/convert_draft.py          # build draft deploy dir
SGLANG_SIF=/path/to/sglang.sif TARGET=<target-dir> DRAFT=<draft-dir> PORT=30010 \
  bash deploy/dflash/run_dflash_server.sh
python deploy/dflash/test_dflash_client.py --port 30010
```
Requires an SGLang image with DFlash spec-v2 (upstream sgl-project/sglang#23000; the nightly
cu13 build). Configure via `SGLANG_SIF`, `PP_ROOT`, `TARGET`, `DRAFT`, `PORT`.

## Notes
- The sink draft uses full-projection QK-norm; `fused_kv_materialize_fullnorm` supplies the matching
  fused-KV kernel (without it sglang falls back to a slower sequential append).
- Attention sink is applied only on the triton / fa3 backends; flashinfer decode silently drops sinks.
