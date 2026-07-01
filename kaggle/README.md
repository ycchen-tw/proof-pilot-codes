# Proof Pilot — Kaggle delivery (`kaggle/`)

32B olmo3_sink agentic proof system for the Kaggle Proof Pilot submission: single RTX PRO 6000
Blackwell (sm120, 96GB), **offline**, **1 hour/problem ×6**, output `id,prediction` (≤5 pages, no figures).

One quantized 32B model serves four roles by prompt swap: **prove → verify → merge-refine → select**
(ported from `distill_gen/math_3r`, the pipeline that beat the single-model ceiling 4.64 → **4.83**).

## Layout
```
serve/        serve_final.sh (CONFIG switch) · apply_all_patches.sh · enable_swa_config.py · bench_loop.py
proof_agent/  offline loop: agent.py · pipeline.py(Engine+watchdog+salvage) · client.py · salvage.py
              + verbatim math_3r: parser/rank/bundle/clean/prompts + prompts/*.txt
bundle/       build_bundle.sh (build env+model datasets) · bootstrap.sh (notebook offline boot)
notebook/     proof_pilot_submit.ipynb (submission) · test_env.ipynb (env smoke test, no model) ·
              run.py (FMI-compatible: --model_path/--input_csv/--output_csv/--logdir) · run_v2.py
rehearsal/    RESULTS.md (offline dry-run results on the GPU twin)
```

## Serving config (`serve/serve_final.sh`, `CONFIG=...`)
All configs share: `--attention-backend triton` (sm120-only sink-correct), `FLASHINFER_USE_CUDA_NORM=1`
(CuTe rmsnorm CUDA13.1 workaround), kv `fp8_e4m3`, hybrid-SWA, `--context-length 200000`,
`--reasoning-parser deepseek-r1`. Patches pre-applied to the venv via `apply_all_patches.sh`.

| CONFIG | target | quant | notes |
|---|---|---|---|
| `w4a8` | gptq-w4a16 ckpt | int4 weight + fp8 act (humming) | concurrency/prefill winner, weights 17.9GB |
| `w4a16` | gptq-w4a16 ckpt | int4 Marlin | robust baseline, zero extra deps |
| `fp8` | soft-distill-32b-deploy | online fp8 | highest-fidelity reference, weights 31.9GB |
| `*-dflash` | + dflash-32b-draft | DFlash spec-v2 + draft KV ring | single-stream win; `ctx 200k` via SWA-draft override |

**Locked config: `w4a8` (native, no dflash).** W1 measured per-problem wall-clock on the real loop
(`rehearsal/RESULTS.md`): w4a8 **1170s** < w4a8+dflash 1295s (+11%) < w4a16 1498s (+28%) < fp8 1713s
(+46%). DFlash is a **net loss** on 32B at the loop's concurrency (confirms `EXP_32B_VS_7B.md`); the
draft is still shipped so it can be flipped on, but it is **off** by default.

## Per-problem budget
Full **6/2/3/4** counts, **128k token/call**, wall-clock **watchdog** (caps each call by remaining
time so one runaway can't eat the hour) + **force-close-think salvage** (recovers a proof from a
truncated `<think>`) + a fallback chain that always emits a best-available proof.

## Run (on the GPU twin / locally)
```bash
# 1. server (one GPU)
CONFIG=w4a8 PORT=30000 CUDA_VISIBLE_DEVICES=0 bash serve/serve_final.sh
# 2. loop over problems -> id,prediction
python notebook/run.py --model_path <gptq-or-fp8 dir> --base-url http://127.0.0.1:30000 \
  --input_csv problems.csv --output_csv submission.csv --logdir logs --budget-s 3300
```

## Kaggle datasets (two; env is independent of the model config)
Build with `bundle/build_bundle.sh` (`WHAT=env|model|both`), upload each as a **private** dataset
(`kaggle datasets create -p <dir> --dir-mode skip`; later `… version -p <dir> -m <msg>`):

| dataset | built file | contents |
|---|---|---|
| `proof-pilot-env`  | `upload_env/proof-pilot-env.bin` (~4.6GB) | pybase + venv + humming + warm caches + repo subset + uv |
| `proof-pilot-32b`  | `model/` (per `CONFIG`)                   | 32B target weights + dflash draft |

### Env packaging contract — three constraints, learned the hard way
- **Bundle the standalone CPython (`pp-env/pybase`).** The venv ships only `site-packages`; its
  stdlib lives in the standalone interpreter. `bootstrap.sh` extracts to `/tmp/pp` and rewrites
  `venv/pyvenv.cfg` `home → /tmp/pp/pybase/bin`. Without this the venv has no stdlib on Kaggle.
- **gzip, not zstd.** The Kaggle image has no `zstd` binary and scoring is offline (no `pip`), so a
  `.tar.zst` can't be opened there. The archive is gzip.
- **Opaque `.bin` name.** Kaggle AUTO-EXTRACTS recognized archives (`.tar.gz`/`.zip`) on dataset
  creation, which fails on this 11G / ~81k-file venv (the version build errors out). An opaque
  extension makes Kaggle store it as a blob. `bootstrap.sh` / the notebooks detect the format by
  **gzip magic bytes** (`1f8b`), not the filename.

## Validate the env first (no model needed)
`notebook/test_env.ipynb` — add the `proof-pilot-env` dataset, Run All. Auto-locates the archive,
relocates the venv, then checks GPU=sm120 + a real CUDA kernel, imports sglang/torch/flashinfer/triton,
imports the humming W4A8 glue, and verifies the sglang patches are baked. Green **ALL PASS** = env good.

## Submit
Open `notebook/proof_pilot_submit.ipynb`, set the two dataset slugs + `CONFIG` + `INPUT_CSV`, Run All.
It bootstraps offline, launches the server, runs the loop one problem at a time, writes `submission.csv`.

> **`proof_pilot_submit.ipynb` is not yet aligned to the new `bootstrap.sh`** (archive extraction +
> `VENV=/tmp/pp/venv`); wire it up and end-to-end test once the model dataset is locked.
