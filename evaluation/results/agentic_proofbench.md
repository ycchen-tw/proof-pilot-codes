# Agentic pipeline on IMO-ProofBench — DSMV2-Simple-3R (refined-only)

Runs `distill_gen/math_3r`'s multi-agent proof pipeline (**prove→verify→rank→refine→select**, the refined-only variant) as one ProofBench condition over all 60 problems, measuring its score relative to the existing single-model baseline (`k4_grading.md`). Corresponds to `plan.md` §Phase 4 (agentic).

## Setup

- **pipeline**: 6 provers (same prompt, diversity from backend sampling) → each valid proof × 2 verifiers → rank →
  top-4 into 3 refiners → **4 selectors take a majority vote among the valid refined ones to pick 1** → `final_proof`. effort=high,
  all stages `max_tokens=180000`, refined-only selector (git `f44996f`).
- **generation**: `run.py --input proofbench_v2.parquet --run-id pb_r3` (`proofbench_v2.parquet` = a 60-row input built from the
  `Problem` column of `data/proofbench_v2.csv`). 60 problems, 1496 calls, **0 error / 0 fallback**,
  34.5M ctok (96.8% reasoning), ~$10–12. Output full trace in `distill_gen/math_3r/outputs/pb_r3/` (gitignored).
- **adapter**: `harness/agentic_to_responses.py` flattens the full-trace records into the `responses.jsonl` the grader eats,
  writing three runs from **the same generation** (joining the `Problem` text to get PB id / subset / level):
  - `pb_r3_select` — k=1 = the selected `final_proof` (the pipeline's real output)
  - `pb_r3_refined` — all valid refined (179, mean 2.98/problem) = **best-of-3-refined** (selector oracle upper bound)
  - `pb_r3_provers` — all valid prover (358, mean 5.97/problem) = best-of-6 raw-sampling reference
- **grader**: the calibrated `flash high_notool` (B.5 verbatim, reasoning=high, max_tokens 65536, **2 passes**),
  the **exact same grader** as the `k4_grading.md` baseline → directly comparable. `grade_proofs.py … --out-name grades_pb_r3.jsonl`.

## Scores (best-of-k, flash high_notool ×2pass)

| run | best-of-k | mean-of-k | almost+ | correct | basic | adv | pre-IMO | easy | medium | hard |
|---|---|---|---|---|---|---|---|---|---|---|
| **select (k=1, real output)** | **4.83** | 4.83 | .667 | .567 | 6.23 | **3.42** | 6.94 | 6.23 | **3.89** | **1.45** |
| refined best-of-3 (selector oracle) | **5.00** | 4.44 | — | — | 6.52 | 3.48 | 7 | 6.40 | — | 1.45 |
| provers best-of-6 (raw reference) | 4.56 | 3.52 | .60 | .567 | 6.38 | 2.73 | 7 | 6.17 | 3.56 | 0.55 |

Existing single-model baseline (`k4_grading.md`, same grader, k=4):

| config | best-of-4 | mean-of-4 | adv |
|---|---|---|---|
| high_notool | 4.40 | 3.37 | 2.7 |
| high_pytool | 4.18 | 3.25 | 2.42 |
| max_notool | 4.50 | 3.60 | 2.7 |
| **max_pytool (prior ceiling)** | **4.64** | 3.62 | 3.1 |

by category (select vs best baseline): Algebra **5.91** (vs 5.03), Combinatorics 4.47 (vs 4.5),
Number theory **5.5** (vs 5.14), **Geometry 3.32** (vs max_notool 4.46).

## Key conclusions

1. **The agentic single output 4.83 > every k=4 best-of-4 baseline (max 4.64)**. Note the fairness: the baseline is "sample 4 +
   grader oracle picks the best"; the agentic pipeline **submits only 1** and still beats oracle-pick-of-4. The cost is ~25 calls/problem (vs baseline 4).
   Against "single-shot quality" (mean-of-k ≈ 3.4–3.6) it leads by **+1.2~1.5**.

2. **refine is the real quality engine**:
   - refine per proof **+0.92** (a single prover 3.52 → a single refined 4.44).
   - best-of-3-refined **5.00 > best-of-6-prover 4.56 (+0.44)**: winning with fewer candidates against more raw candidates → refine is fixing, not just sampling more.
   - Especially clear on advanced: refined 3.48 vs raw 2.73.

3. **the selector is near-optimal, losing little**: selected 4.83 / oracle-best-refined 5.00 = **96.5%**, on average only **0.175** below "pick the best of 3
   refined" per problem. selected (4.83) also > mean refined (4.44), so it really is picking the good ones. 9/60 problems had a better refined
   not selected, and **2 dominate**: `PB-Basic-007` (selected 3.5, pool has 7), `PB-Basic-030` (selected 3, pool has 6.5); the other 7 are off by only
   +0.5 (6.5→7 margin). The improvement direction = the majority-vote judgment on those few problems.

4. **advanced / hard are the highest of the whole field** (adv 3.42 > max_pytool 3.1; IMO-hard 1.45 > every baseline's ≤1.25) → multi-agent
   pushes harder on hard problems than tool / max-reasoning; but **hard is still ~1.5/7, the ceiling isn't broken** (consistent with `k4_grading.md`'s "15 advanced
   problems need training to break through").

5. **The Geometry "loss" is a best-of-4 oracle artifact, not an agentic weakness**: per-problem, **select ≈ provers (same generation, no problem differs by ≥1)**
   → refine/select didn't hurt geometry. max_notool's high geometry 4.46 rests on **2 isolated lucky hits** (`PB-Advanced-003` 7, `PB-Basic-026`
   6.5, all other configs 0) — the variance dividend of k=4 sampling on low-solve-rate hard problems. Removing those 2, max_notool geometry ≈ 3.5, tied with
   select/provers. Raising geometry takes **generation-side** diversity, not changing refine/select.

```
single raw prover  3.52
  → refine         4.44   (+0.92/proof; refine's core value)
  → best-of-3      5.00   (refine-pool ceiling, already beats every baseline)
  → selector pick-1 4.83  (captures 96.5%, loses 0.175, mainly stuck on 2 problems)
```

## Caveats (must note)

- **Conflict of interest**: grader=flash and the graded pipeline also runs on flash → may score DeepSeek's style too high. It is **consistent** across all rows,
  so relative comparison is still valid; but **the absolute scores are conservative + high-scoring advanced / 34 correct problems need human spot-checks** (plan §4).
- **Contamination**: flash may have memorized public problems (especially basic 6.2+) → an inherent limitation of grading a teacher pipeline, not a bug.
- This measures the **teacher pipeline's proof quality**, not the post-trained student; the student is evaluated separately (plan §Phase 3).
- The best-of-4 baseline enjoys the oracle-pick-of-4 dividend; the agentic pipeline submits only 1 but spends ~6× the calls. When comparing, distinguish "committed single-shot" vs "oracle best-of".

---

## DeepSeek-V4-Pro vs Flash (same pipeline, all 60, same flash grader)

Runs the same refined-only pipeline with `--model deepseek-v4-pro` (all else unchanged) over all 60 problems (`run-id pb_r3pro`), graded by the same flash high_notool grader ×2pass. Generation was healthy: 60 problems, 0 fallback, valid μ 5.82, 43M ctok (of which 12 errored/1 trunc were the tail-end select during a connection drop + balance exhaustion; those 2 problems were re-run cleanly after deleting the records).

| run | pro | flash | Δ | pro correct |
|---|---|---|---|---|
| select (k=1) | **5.31** | 4.83 | +0.48 | .683 (41/60) |
| refined best-of-3 | 5.38 | 5.00 | +0.38 | .70 |
| provers best-of-6 | 5.02 | 4.56 | +0.46 | .683 |

**by level (select)**: pre-IMO 7.0/6.94, IMO-easy 6.73/6.23, IMO-medium 3.97/3.89, **IMO-hard 2.95/1.45 (pro doubles it)**.
**by category (select)**: Algebra 5.81/5.91, Combi 4.06/4.47, NT 5.32/5.5, **Geometry 6.14/3.32 (pro +2.82, crushing)**.

→ Under the flash grader, **pro's overall +0.48 comes almost entirely from Geometry (+2.82) and IMO-hard (+1.5)**; easy/medium and algebra/combi/nt are comparable (combi slightly to flash). pro shores up flash's weakest — geometry and hard problems — and ties elsewhere.

## Grader cross-validation — Claude independent blind grading (`claude_xcheck.py`)

The flash grader grades the same family (flash/pro are both DeepSeek), so we use **Claude Code sub-agents as an independent blind grader**: for each problem the 2 selected proofs are randomly labeled A/B (the agent doesn't know which is pro/flash), 10 sub-agents each grade 6 problems, same B.5 rubric, 0/1/6/7.

**The conclusion is revised — pro's overall advantage is grader-dependent:**

| grader | pro | flash | verdict |
|---|---|---|---|
| flash grader | 5.31 | 4.83 | pro **+0.48** |
| **Claude grader** | 5.32 | 5.30 | **+0.02 (tie)** |

Both graders **agree on pro (~5.31)**, but the flash grader scores the flash-pipeline lower (4.83 vs Claude 5.30). **by category (Claude)**: Geometry pro 5.93 ≫ flash 3.64 (**both graders agree pro crushes geometry, robust**); but on Algebra/Combi/NT **Claude instead thinks flash is slightly better** (6.25/5.19/6.00 > 5.38/4.44/5.64). Grader bucket agreement 88%.

**Digging into the cause (adjudicated cases) — it's not "flash favoring its own", it's two graders with complementary blind spots:**

- **flash grader = strict logical audit** (doesn't run code): catches circular arguments, fake lemmas, hand-waving.
  - `PB-Advanced-006`: the flash proof's "the zero set is a subgroup" is **circular** (using closure to prove closure) + `f(6)=0` fails for any d≥2 → flashG 0 (**correct**), Claude 7 "rigorous" (**missed both errors**).
  - `PB-Advanced-029`: the sufficiency lemma `C(n,i)≡C(n₁,a)C(p−1,b) mod p^e` is **false for both p=2 and p=3** (verified by computation) and hand-waved → flashG 1 (**correct**), Claude 6 "Almost" (**too lenient**).
- **Claude grader = numerical verification** (will brute-force/simulate): catches wrong final answers/coordinates.
  - `PB-Advanced-003` (pro): the proof's claimed mixtilinear touch-point coordinates are **wrong** → Claude recomputes numerically, catches it, gives 0; flashG can't verify, believes it, gives 7 (**fooled by a confident wrong computation**).
  - Adv-023/020/018/010 etc. wrong-answer problems are mostly caught by both graders (given 0).

**Net effect**: flash's proofs are more circular/hand-wavy than pro's → the flash grader dings those gaps (low flash-pipeline scores) while Claude is lenient (high scores) → the discrepancy all falls on the flash-pipeline; pro is consistent across both graders. **So "Claude shows a tie" is mainly Claude being overly lenient on flash's rigor gaps; the flash grader's "pro > flash" is closer to the truth on the rigor axis. But no single grader is ground truth — safest is using both (rigor audit + numerical verification) or human.**

## Token usage comparison (pro vs flash, same 60 problems)

| | flash | pro | pro/flash |
|---|---|---|---|
| per problem completion (all) | mean 576k / med 592k | mean 706k / med 781k | **1.23×** |
| per problem (**advanced** 30) | 730k / 785k | **918k / 1014k** | **1.26×** |
| per problem (basic 30) | 421k | 494k | 1.17× |

reasoning is ~97% (the proof body content is only 3%). **Per-stage per-call (all / advanced) pro/flash ratio**: prove 1.17× / 1.19×, verify 1.42× / 1.37×, **refine 1.45× / 1.55×**, select 1.10× / 1.29×. prove dominates the total (~60%), but **pro's "extra burn" concentrates in verify+refine (review+polish)**, and **the harder the problem the more pronounced** (advanced refine 1.55×, share 16%→20%). This matches pro's lead on IMO-hard = the extra compute goes into making hard-problem proofs correct and rigorous, not thinking longer on the first draft.

## Reproduction

```bash
# 1. build the input parquet (60-row, from the Problem column of proofbench_v2.csv) — see proofbench_v2.parquet in the commit
# 2. generate
DEEPSEEK_API_KEY=... uv run python distill_gen/math_3r/run.py \
    --input distill_gen/math_3r/proofbench_v2.parquet --run-id pb_r3 \
    --effort high --max-tokens 180000 --num-provers 6 --verify-k 2 --num-refiners 3 \
    --num-selectors 4 --concurrency 300 --problem-concurrency 60
# 3. adapter -> three runs (select / refined / provers)
uv run python evaluation/harness/agentic_to_responses.py \
    --records distill_gen/math_3r/outputs/pb_r3/records.jsonl \
    --data evaluation/data/proofbench_v2.csv --out-prefix pb_r3
# 4. grade (same baseline grader)
cd evaluation/harness && DEEPSEEK_API_KEY=... uv run python grade_proofs.py \
    --run-ids pb_r3_select,pb_r3_refined,pb_r3_provers --data ../data/proofbench_v2.csv \
    --passes 2 --reasoning high --max-tokens 65536 \
    --base-url https://api.deepseek.com/v1 --served-model deepseek-v4-flash \
    --api-key-env DEEPSEEK_API_KEY --concurrency 200 --out-name grades_pb_r3.jsonl

# 5. pro: steps 2-4 with --model deepseek-v4-pro --run-id pb_r3pro (grader still flash)
# 6. Claude blind cross-validation
uv run python evaluation/harness/claude_xcheck.py chunks \
    --runs pb_r3pro_select,pb_r3_select --data evaluation/data/proofbench_v2.csv --n-chunks 10
#   -> spawns one Claude sub-agent per chunk_00..09 to write result_NN.json (B.5 blind A/B)
uv run python evaluation/harness/claude_xcheck.py agg --runs pb_r3pro_select,pb_r3_select
```

> ⚠️ `grade_proofs.py`'s aggregate summary is written to `runs/_grade_high_notool_k4/summary.json` (path keyed by grader config, colliding with the
> baseline k4 name). The numbers in this doc are re-aggregated uniformly from each run's raw `grades_pb_r3.jsonl` (same logic as the baseline),
> not relying on that summary which gets overwritten.
