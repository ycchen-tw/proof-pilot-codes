# Prompt-template sweep — IMO-ProofBench grades

- **Model**: DeepSeek-V4-Flash, reasoning **high**, no-tool, single-round.
- **Data**: ProofBench v2, 60 problems (30 basic + 30 advanced), k=3 samples.
- **Grader**: flash `high_notool` (paper B.5 verbatim, calibrated), 2 passes/candidate, graded on the **meta-stripped proof body** (`graded_text`).
- **Score** = mean over 2 passes per candidate; **best-of-3** = max over the 3 candidates, **mean-of-3** = their mean, per problem; table aggregates over 60 problems.
- ⚠️ k=3 → per-template differences are noisy; the paired win/loss vs t0 is the more reliable signal. Grader is flash judging flash (self-grading) and under-scores the middle band — absolute numbers are conservative.


## Ranking (by best-of-3 mean)

| rank | tmpl | template | best-of-3 | almost+ | correct | mean-of-3 | basic | adv | vs t0 (Δ) | win/tie/loss | overclaim | gen tok/cand | reason% | gen total | grade total |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **t3** | DeepSeekMath-V2 self-verify | **4.583** | 0.6 | 0.533 | 3.789 | 6.583 | 2.583 | +0.12 | 9/45/6 | 65/150 (0.433) | 64,503 | 97% | 11.61M | 2.71M |
| 2 | **t1** | Huang-Yang rigorous | **4.5** | 0.617 | 0.55 | 3.731 | 6.333 | 2.667 | +0.04 | 9/41/10 | 85/173 (0.491) | 62,312 | 97% | 11.22M | 2.54M |
| 3 | **t0** | minimal baseline | **4.458** | 0.6 | 0.583 | 3.669 | 6.3 | 2.617 | — | — | — | 74,150 | 98% | 13.35M | 2.58M |
| 4 | **t4** | STAR-Pólya plan-verify | **4.383** | 0.567 | 0.55 | 3.428 | 6.1 | 2.667 | -0.07 | 9/44/7 | 38/83 (0.458) | 61,722 | 97% | 11.11M | 2.59M |
| 5 | **t7** | rubric-aware | **4.317** | 0.55 | 0.517 | 3.525 | 5.967 | 2.667 | -0.14 | 9/44/7 | 73/155 (0.471) | 66,226 | 98% | 11.92M | 2.6M |
| 6 | **t2** | HY self-repair | **4.308** | 0.6 | 0.517 | 3.722 | 6.067 | 2.55 | -0.15 | 5/46/9 | 86/175 (0.491) | 64,735 | 97% | 11.65M | 2.52M |
| 7 | **t6** | Aletheia gen-verify-revise | **4.042** | 0.533 | 0.483 | 3.233 | 5.783 | 2.3 | -0.42 | 7/40/13 | 92/165 (0.558) | 60,486 | 97% | 10.89M | 2.56M |
| 8 | **t5** | Momus dialectic | **3.983** | 0.533 | 0.5 | 3.247 | 5.633 | 2.333 | -0.47 | 6/43/11 | — | 54,050 | 96% | 9.73M | 2.55M |

Totals: **generation** 91.5M completion tokens, **grading** 20.6M completion tokens (all 8 templates).


### Notes
- **best-of-3** ≈ the agentic best-of-k ceiling; **mean-of-3** ≈ single-sample expectation.
- **vs t0 (Δ)** = mean per-problem best-of-3 difference vs the minimal baseline; **win/tie/loss** counts problems where the template's best-of-3 beats/ties/loses to t0.
- **overclaim** = candidates that claimed a *complete* solution but graded <6 (only templates that emit a completeness verdict: t1/t2/t3/t4/t6/t7).
- **gen tok/cand** = mean completion tokens per candidate (generation); **reason%** = share that is hidden reasoning; **gen total** = completion tokens over all 180 candidates (60 problems × k=3); **grade total** = grader completion tokens (B.5, 2 passes). Generation completion is ~97% reasoning — the real cost driver; structured templates that make the model think/repair more cost more for little or negative quality gain.
