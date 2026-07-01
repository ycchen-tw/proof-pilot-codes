# deploy/

SGLang serving / deployment code (kept out of `training/`).

- `make_olmo3sink_deploy.py` — generalized deploy-dir builder (`--src/--dst`, single/multi-shard)
  for any olmo3_sink checkpoint: hardlinks weights + rewrites config to the serve recipe
  (rope_parameters→legacy rope_theta+rope_scaling **verbatim**, drop `auto_map`, model_type=olmo3,
  dtype/torch_dtype=bf16, use_cache). Supersedes the hardcoded `dflash/make_target_deploy.py`;
  used for the soft_distill_v2 7B/32B checkpoints (`outputs/stage1-v2-*-softdistill-v2-deploy`).

## `target/` — olmo3_sink target serving
In-engine attention-sink model class for serving the stage-1 / stage1-v2 olmo3_sink
checkpoints under SGLang, plus the validation suite.
- `olmo2_sink.py` — patch bind-mounted over sglang `srt/models/olmo2.py` (adds the
  gpt-oss-style sink; `olmo2_orig.py` is the pristine image reference for diffing).
- `_hf_reference.py`, `_parity_test.py`, `_format_test.py`, `_tool_test.py` — logprob parity /
  DeepSeek format / tool-calling validation. `ref/` holds regenerable baseline logprobs.
- Full write-up: `docs/stage1_deploy_test.md`.

## `dflash/` — DFlash speculative-decoding deployment
Serve the olmo3_sink target + the trained DFlash draft together.
- `dflash_sink.py` — sglang DFlash draft rewritten to OLMo3+sink (post-norm, full-projection
  QK-norm, per-head sink, all-SWA, learnable `mask_embed`); bind-mounted over `srt/models/dflash.py`.
- `olmo2_sink_dflash.py` — target serving + `set_dflash_layers_to_capture()` aux-hidden capture;
  bind-mounted over `srt/models/olmo2.py`.
- `convert_draft.py` — `final.pt` → `outputs/dflash-sink-sglang-draft/` (sglang-loadable).
- `make_target_deploy.py` — `outputs/stage1-v2-7b` → `outputs/stage1-v2-7b-deploy/` (rope-legacy config).
- `run_dflash_server.sh` — launch the DFLASH server (single-GPU / TP1).
- `test_dflash_client.py` — hit the server, report output + `spec_accept_length`.

Quick start:
```
cd deploy/dflash
uv run python make_target_deploy.py      # build target deploy dir
uv run python convert_draft.py           # build draft deploy dir
GPU=0 PORT=30010 bash run_dflash_server.sh   # serve
uv run python test_dflash_client.py --port 30010
```
