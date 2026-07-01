# k=4 4-config evaluation results — DeepSeek-V4-flash on IMO-ProofBench

Robust evaluation: `dsv4-flash × {high,max} reasoning × {notool,pytool} × 60 problems × k=4 = 960 candidates`, graded with the calibrated **flash high_notool** grader (reasoning=high, max_tokens 65536, B.5+reference, `parse_score`), **2 passes per candidate**, blank candidates skipped and recorded as 0. Raw scores in `runs/dsv4-flash__*_k4/grades_flashHighNotool_k4_2pass.jsonl`, aggregated in `runs/_grade_high_notool_k4/summary.json`.

## 1. Scores (best-of-4 is the headline metric at k=4)

| config | **best-of-4** | almost+ | correct | mean-of-4 | advanced | basic | pass agreement |
|---|---|---|---|---|---|---|---|
| high_notool | 4.40 | 0.60 | 0.533 | 3.37 | 2.7 | 6.1 | 0.92 |
| high_pytool | 4.18 | 0.55 | 0.517 | 3.25 | 2.42 | 5.95 | 0.88 |
| max_notool | 4.50 | 0.60 | 0.583 | 3.60 | 2.7 | 6.3 | 0.92 |
| **max_pytool** | **4.64** | **0.617** | 0.567 | **3.62** | **3.1** | 6.18 | 0.88 |

- **best-of-4 is ~1 point higher than mean-of-4** (4.4 vs 3.4) → sampling 4 and taking the best genuinely adds score, confirming the value of agentic multi-candidate.
- **max_pytool is best overall** (especially advanced 3.1 in the lead); **high_notool is the cheapest and nearly ties it** (4.40).
- **teacher ceiling** = max_pytool best-of-4 **4.64/7**, advanced 3.1.

### Delta (best-of-4)
| Comparison | mean delta | win/loss/tie |
|---|---|---|
| tool @ high | −0.217 | 8/9/43 |
| tool @ max | +0.142 | 11/7/42 |
| reasoning @ notool (max−high) | +0.10 | 12/8/40 |
| reasoning @ pytool (max−high) | +0.458 | 10/9/41 |

These deltas are all small, mostly within the noise (see §2).

## 2. Statistical analysis (using the 8 scores per config×problem = 4 candidates×2 passes to separate signal from noise)

Main metric = per-problem **solve-rate (fraction of scores ≥6)** (robust to the grader's 6-vs-7 / 0-vs-1 noise; calibration shows only the 0/1↔6/7 axis is reliable).

- **tool / notool are not complementary but highly redundant**: pooled (high+max, 16 samples per side) solve-rate **r=0.947**; delta mean −0.011; of 60 problems only **1 clearly favors tool, 0 favor notool, 59 within noise**.
  - **Difference from the k=1 "coverage complementarity"**: earlier the complementarity was at the **coverage level** (notool runaway vs pytool tool-lock, the two failures not overlapping). This time the **budget fix eliminated tool-lock + k=4 best-of recovered runaway** → both failure modes are filled in → at the quality level both lie on the same capability curve.
- **tool helps significantly: 1/60** — `PB-Advanced-017` (Number theory): notool solve 0.25 (mean 1.8) → tool solve 0.75 (mean 4.9), Δ+0.50, MWU p=0.017. Consistent with "tool is useful for NT 'compute-the-answer' problems".
- **tool hurts significantly: 0/60** — the budget fix also eliminated the old k=1-style 7→0 disaster (getting stuck in a search loop that overwrites correct reasoning).
- **high beats max: 0/60** — no problem where high statistically beats max; max is weakly ≥ high everywhere. high's only advantage is being cheaper.
- **Truly hard problems (all 4 configs solve <0.25): 15 problems** (14 advanced + `PB-Basic-009`/`PB-Basic-023`) = the capability ceiling, which neither tool nor max can rescue. Consistently easy (all >0.75): 16 problems.
- **Conclusion**: under this harness pytool neither hurts nor meaningfully improves quality for flash (except the NT case); breaking through those 15 advanced ceiling problems takes **training**, not tools or more reasoning.

## 3. Token / cost

| config | prompt (input) | completion (output) | median turns | median latency |
|---|---|---|---|---|
| high_notool | 270 | 68.7k | 1 | 499s |
| high_pytool | 351k | **47.7k ↓30%** | 19 | **364s** |
| max_notool | 349 | 112.7k | 1 | 967s |
| max_pytool | 423k | **69.7k ↓38%** | 25 | **576s** |

- **Output tokens: tool cuts 30–38%** (the tool interrupts runaway, no longer spinning until the budget is burned); **input tokens explode** (multi-turn resends the growing conversation each turn) → total tokens for pytool are ~6–7× notool.
- **API dollar cost ≈ break-even**: those hundreds of thousands of pytool prompt tokens are mostly resent prefixes = **DeepSeek context-cache hits (almost all)**, extremely cheap (this is exactly the payoff of the "tools array never changes, keep the prefix cache" design). Roughly, with cache: high_pytool ≈ high_notool (slightly more expensive), **max_pytool slightly cheaper than max_notool**. Without cache, pytool costs double.
- **Local Kaggle inference (RTX6000Pro) is where tool's token savings really matter**: no API pricing, the bottleneck = autoregressive generation (output tokens); the prompt is cheap prefill (multi-turn KV-cache reuse). **output ↓30–38% + latency ↓25–40%** is a real advantage against the hard "1 hour per problem" limit.
- ⚠️ **cache-hit tokens are not recorded** (`client._usage` only captures prompt/completion/reasoning) → the API savings above are estimates; measuring precisely requires also capturing `prompt_cache_hit_tokens`.

## 4. Caveats (must note)

- **Conflict of interest**: grader=flash and the graded=flash too (teacher self-grading) → may score DeepSeek's style too high, so **correct 0.53–0.58 and advanced 7-point problems must be human spot-checked**.
- The grader is **systematically strict** (calibration bias −0.77) → the absolute scores are a conservative lower bound.
- The only reliable directional signals are: **max_pytool leads on advanced**, **tool helps in the NT case**, **the 15-problem advanced ceiling**; all other small deltas are noise.
