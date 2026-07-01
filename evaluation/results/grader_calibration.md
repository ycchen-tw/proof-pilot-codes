# Grader calibration results — IMO-GradingBench

Validates "how accurately our DeepSeek grader scores", as the prerequisite for trusting every subsequent ProofBench score (plan §4 / Phase 0.5).

## Setup

- Calibration set: `data/gradingbench.csv` (1000 rows = 30 **Advanced** problems × ~33 candidate solutions, each row with a human `Points` 0–7 and a 4-level `Reward`).
- Take a **200-row stratified subset** (50 per `Reward` category: Incorrect/Partial/Almost/Correct; seed 1234).
- Score each row with the **grader prompt aligned to paper §B.5** (`prompts/grader.md`, with reference solution + guidelines) → parsed into 0/1/6/7.
- Run **4 configs = {high, max} reasoning × {notool, pytool}**, one round each for flash and pro (same 200 problems, same seed → directly comparable). `pytool` = gives the grader an `execute_python` tool to verify computations itself.
- Metrics aligned to paper §5.4: bucket the human 7-scale into 4 levels `(7 / 6–4 / 3–1 / 0)` (= the `Reward` column); compute 4-cat accuracy, MAE (golden floor 3.9%), Pearson (per-problem + aggregated by problem), confusion, bias.
- Tool: `harness/calibrate_grader.py` (async). Raw outputs: `runs/grader_calibration/` (flash), `runs/grader_calibration_pro/` (pro).

## Results

| config | model | acc4 | MAE% | r per-problem | r aggregated | bias | avg tokens |
|---|---|---|---|---|---|---|---|
| high_notool | flash | 0.540 | 20.6 | 0.706 | 0.875 | −0.77 | 6.9k |
| | **pro** | 0.553 | 20.5 | 0.699 | 0.848 | −0.68 | 13.7k |
| high_pytool | flash | 0.550 | 20.7 | 0.706 | 0.878 | −0.86 | 13.3k |
| | pro | 0.556 | 20.1 | 0.711 | 0.835 | −0.60 | 14.5k |
| max_notool | flash | 0.540 | 20.8 | 0.722 | 0.870 | −1.06 | 24.4k |
| | pro | 0.571 | 20.2 | 0.711 | 0.875 | −0.84 | 27.4k |
| max_pytool | flash | 0.548 | 21.4 | 0.699 | 0.881 | −1.01 | 21.1k |
| | **pro** | **0.582** | **19.4** | **0.731** | 0.869 | −0.86 | 22.3k |

"Almost(6)" class recall (the weakest class): flash **0.04–0.08** → pro **0.14–0.16**.

## Key conclusions

1. **Per-problem vs aggregated — don't misread the accuracy.** Per-problem Pearson ~0.70–0.73 looks low, but **aggregating by problem jumps it to ~0.85–0.88**; the paper's 0.96/0.93 further aggregates by "model" (mean over 30 problems), which is stronger smoothing. Per-problem is inherently hard (paper Table 7: even o3/Gemini only reach ~0.54 per-problem accuracy). **Ranking models uses the aggregated view, where flash and pro are both ~0.87 = equivalent.**
2. **Tool and max effort: useless for flash, a little useful for pro.** flash's 4 configs are nearly flat in accuracy (~0.54); pro goes from high_notool 0.553 → max_pytool 0.582 (+0.029). pro is a more capable grader that can exploit extra compute/tools, but the ceiling is still ~0.58.
3. **The middle classes (Almost/Partial) are a shared hard failure for both.** The grader is very accurate at the extremes (Incorrect ~0.88, Correct ~0.90) but poor in the middle; "6 vs 7" is almost undistinguishable for flash (Almost recall 0.04), and pro improves it to 0.14–0.16 but remains unreliable.
4. **Both grade strictly** (systematically underestimating the human, bias all negative; pro is less strict than flash). This conservatively underestimates our model's proofs.
5. **Cost: pro ≈ 19× flash** (flash 200×4 ~5.5 CNY; pro 200×4 = **104.6 CNY / ~$14.5**; pro ~4 CNY/M output ≈ 10× flash, and uses ~2× more tokens).

## Decision (grader selection)

| Use | Choice | Reason |
|---|---|---|
| **Ranking checkpoints** (main use, 60-problem aggregate) | **flash high_notool** | aggregate correlation ~0.87 = pro, 19× cheaper; max/tool give flash no gain |
| **Per-candidate verifier in the agentic loop** (per-problem good/bad judgment) | **pro max_pytool** (if needed) | best per-problem in the table (0.582 / MAE 19.4%), pro can use tool+max |
| Any fine "Almost vs Correct" call | not fully trustworthy, needs human spot-check | both have Almost recall ≤ 0.16 |

## Caveats

- **The balanced subset is harder than the natural distribution**: weighted to the natural distribution, accuracy is ~0.62 (the extremes dominate, and the grader is accurate there).
- **Advanced only** (all 30 gradingbench problems are Advanced); Basic grading is uncalibrated, expected to be more accurate.
- **Not apples-to-apples with paper Table 7**: the paper is reference-free, whereas we have reference+guidelines (easier) yet only reach 0.54–0.58, meaning DeepSeek as a grader is weaker than the frontier.
- The grader runs in thinking mode → temperature is ignored, so **the grader has intrinsic randomness** (single scoring pass); part of the per-problem noise comes from this.
