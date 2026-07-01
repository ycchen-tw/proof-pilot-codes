# Evaluation data — IMO-ProofBench

Source: Google DeepMind *IMO-Bench* (paper *Towards Robust Mathematical Reasoning*, EMNLP 2025, arXiv:2511.01846).

| File | Contents | sha256 |
|---|---|---|
| `proofbench_v2.csv` | **IMO-ProofBench**, 60 proof problems (Basic 30 + Advanced 30). **Use v2** (v1 is deprecated; it fixed the PB-Advanced-022 typo). | `aa8b813dbd4068137e3d165e5da228f6e0e1cc85a91c37883e1791b954e43af0` |
| `gradingbench.csv` | **IMO-GradingBench**, autograder calibration reference (problem × candidate solution × human score). Used to validate the correlation between the ProofAutoGrader and human scores; not the main eval set. | `e85a520c2bbb5a89f2db35088c7935d485922f26cf2bbd04f15e1d967af26cfe` |

Downloaded from: `https://raw.githubusercontent.com/google-deepmind/superhuman/main/imobench/` (fetched 2026-06-01).

License: data is **CC-BY 4.0**, original source code Apache-2.0. Cite arXiv:2511.01846 / imobench.github.io.

## proofbench_v2.csv columns

`Problem ID, Problem, Solution, Grading guidelines, Category, Level, Short Answer, Source`

- **Problem ID**: `PB-Basic-NNN` / `PB-Advanced-NNN`.
- **Problem / Solution**: LaTeX problem statement and reference solution.
- **Grading guidelines**: the grading rubric (states the conditions each `(Partial)` / `(Almost)` level must meet); fed to the grader.
- **Category**: Algebra(16) / Combinatorics(16) / Number theory(14) / Geometry(14).
- **Level**: pre-IMO(8) / IMO-easy(24) / IMO-medium(18) / IMO-hard(10).
- **Short Answer**: the final answer (may be blank for pure proof problems).
- **Source**: origin, e.g. `(Modified) IMO 2019, P1`.

## Contamination note

The Advanced subset is mostly newly written by medalists / robustified adaptations (to prevent memorization); the Basic subset includes adapted public problems. If the SFT data (Nemotron / Cascade-2) contains olympiad sources, check for overlap with this set before evaluating (especially the Basic subset).
