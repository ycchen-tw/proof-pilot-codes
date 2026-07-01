# W1 — serving config benchmark (RTX PRO 6000 Blackwell sm120, the Kaggle GPU twin)

Real agentic loop (`proof_agent`, full 6/2/3/4), one problem at a time = the Kaggle setting.
4 configs in parallel, one per GPU. ProofBench problem #0 (Z→Z functional equation, hard).
Settings: ctx 200000, kv-fp8, triton, hybrid-SWA r=0.2, max_tokens/call 32000, budget 1800s, temp 0.7.

## Per-problem wall-clock (the decisive metric)

| config | wall-clock | vs w4a8 | valid/6 | refined | calls | ctok |
|---|---:|---:|---:|---:|---:|---:|
| **w4a8 (native, humming)** | **1170 s** | — | 4 | 3 | 21 | 273k |
| **w4a8 + dflash** | 1295 s | **+11% slower** | 4 | 3 | 21 | 268k |
| w4a16 (Marlin int4) | 1498 s | +28% | 5 | 3 | 23 | 270k |
| fp8 | 1713 s | +46% | 3 | 2 | 19 | 147k |

## Findings

1. **w4a8 native is the throughput winner.** On the real concurrent loop it beats w4a16 by 28% and
   fp8 by 46% — the humming W4A8 prefill/large-M advantage (big refine bundles + N=12 verify wave)
   materializes end-to-end, not just in micro-bench.
2. **DFlash is a NET LOSS on 32B here: w4a8+dflash is ~11% SLOWER than w4a8 native.** Confirms
   `EXP_32B_VS_7B.md` ("32B dflash concurrency no benefit"): the agentic loop runs concurrent waves,
   GQA keeps 32B compute-bound, and the fixed bf16-draft cost isn't amortized. The earlier
   server-log "throughput looked higher" was a phase/wave confound — end-to-end wall-clock is the
   truth. → **drop dflash for the loop.**
3. **ctx 200000 works for all configs including dflash** (`SGLANG_ALLOW_OVERWRITE_LONGER_CONTEXT_LEN=1`;
   draft is sliding-window so long ctx doesn't touch it).

## Precision (quantization vs proof quality) — answered from existing ablation

`docs/quantization.md §8` (held-out 48×1024 tok, bf16 ppl 2.772 / top1_acc 0.7396):

| scheme | ppl | Δppl | top1_acc | KL(bf16‖q) |
|---|---:|---:|---:|---:|
| fp8 | 2.785 | +0.5% | 0.7380 | 0.0048 |
| w4a16 (gptq) | 2.794 | +0.8% | 0.7381 | 0.0155 |
| w4a8 (humming) | — | **+0.68%** (its README) | — | lossless-grade, DFlash accept unchanged |

All within <1% ppl of bf16 → **quantization does not meaningfully hurt proof quality**. w4a8 and w4a16
share the *same int4 weights* (w4a8 only differs in fp8 activations), so proof quality is essentially
identical; 32B tolerates quantization even better than this 7B ablation. **w4a8 wins throughput AND is
precision-safe.**

## Open issue (quality) — selector fallback [FIXED]

All configs ended at `final_source=fallback_no_valid_id` (still a valid proof via rank-based
best-available). **Root cause (diagnosed by direct probe): not a selector bug** — given budget the
selector thinks ~6-7k tokens then correctly emits `<selected_id>R0</selected_id>` (finish=stop). The
benchmark's tight 1800s budget + est_tps watchdog starved the *last* stage (select) of tokens, so it
truncated inside `<think>`. **Fix:** force-close-think salvage extended from prove/refine to ALL roles
(verify `<score>`, select `<selected_id>`) in `pipeline.py::_maybe_salvage`. Production budget (3300s,
128k cap) also leaves select ample headroom. Validated at production settings → see below.

## Decision

**Locked Kaggle config = `w4a8` (native, no dflash).** Fastest end-to-end, lowest VRAM (17.9GB → huge
KV pool), zero spec-decode complexity. Keep `fp8` as the precision gold reference for the quality check;
`dflash-32b-draft` still shipped so the config can be flipped, but it is **off** by default.

---

# W2/W5 — continuous pool loop (`pool_loop.py`) validation & tuning

The agent loop is the **continuous pool** (`solve_pooled`): seed provers → verify-on-complete → enter
pool → merge-refine when ≥2 good verified candidates → re-verify → selector majority vote in a reserved
tail window. Replaces the fixed prove→verify→refine→select barrier. Validated on the GPU twin, w4a8
`:30000`, ProofBench problems, **full 1h budget (3300s / 600s select reserve), temp 1.0 / top_p 0.95**.

## Root cause that gated everything: the model omits `</solution>`

`soft-distill-32b` reliably writes `<solution>` + a correct proof but **never closes with `</solution>`**
(jumps straight to a stray `</self_evaluation>` then `<score>`). The strict `<solution>...</solution>`
parser dropped these perfect proofs → low valid rate → selector starved → `fallback`/`None` votes. This,
NOT any parameter, was the dominant failure. **Fix:** lenient extraction (`<solution>` up to the first of
`</solution>` / `<self_evaluation>` / `</self_evaluation>` / `<score>` / EOF) + score-optional validity +
lenient `selected_id` (open-tag / bare `P#`). See memory `olmo-tag-quirk`.

## Tuning journey (problem #0 unless noted)

| run | config | salvage | selector | valid | wall |
|---|---|---:|---|---:|---:|
| original | est_tps20, strict parser | 53% | 1/5 (fallback) | — | — |
| v3 | parser fix, est_tps35, cap20k, verify0.3 | 34% | **3/5** (1 None) | 71% | 3221s |
| v3b (prob#1) | same | 28% | **3/5** | 75% | 3214s |
| v4s (30min) | cap**32k**, verify**1.0** | 16% | **3/5** (0 None) | 72% | 1743s |
| **v5 (full 1h)** | **cap32k, verify1.0 — FINAL** | **11%** | **3/5** (0 None) | **85%** | **3212s** |

**Findings:** (1) salvage was driven by `call_cap` truncating long reasoning, not by temperature — raising
`call_cap` 20k→**32k** (above the model's natural proof length) halved salvage. est_tps **35** (≈ real
concurrent per-stream) vs the old 20 also matters. (2) Concurrency saturates at 12 once the driver gates on
`_gen_inflight` (its own in-flight gens) instead of total task count — queued verifiers no longer starve the
refiner. (3) selector health (1/5→3/5, 0 None) came from lenient id parsing + salvage, not low temp; verify
stays temp 1.0, only the (cheap, 5-call) selector keeps temp 0.2. (4) `max_gen=1` persists — refinement does
not deepen and the winning proofs are always provers, so direct proving + verify + vote is the value driver
here, not deep refinement.

## Safety (Kaggle 1h hard cap — can NEVER be breached)

- `solve_pooled` wraps the whole solve in `asyncio.wait_for(budget+slack)`; `_select_phase` wraps the
  selector `gather` in its own `wait_for` (returns top-scored candidate on timeout); reserve is clamped so
  a small budget can't push the active phase into the past.
- **Circuit breaker:** if the server dies mid-run every call errors in microseconds — without a guard the
  driver busy-spawned **5.5M** doomed tasks. Now stops after `_MAX_CONSEC_ERR=24` consecutive errors
  (verified: 5.5M → 24) + `_MAX_GENS=2000` absolute backstop. Makes runs reclaim-safe on the shared box.

## Final locked loop config (in `run.py` / notebook defaults)

`est_tps=35, call_cap=32000, temperature=1.0 (prover/refiner), verify_temp=1.0, select_temp=0.2,
init_provers=6, verify_k=3, refine_inputs=4, select_bundle_n=4, num_selectors=5, select_reserve_s=600,
concurrency=12`. `run.py` uses `solve_pooled`; notebook cell passes these explicitly.

_Remaining: W5 full 6-problem offline dress rehearsal; bundle `wheels/` (offline pip fallback) still empty._
