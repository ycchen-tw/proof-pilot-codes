# Evaluation data — IMO-ProofBench

來源：Google DeepMind *IMO-Bench*（論文 *Towards Robust Mathematical Reasoning*, EMNLP 2025, arXiv:2511.01846）。

| 檔案 | 內容 | sha256 |
|---|---|---|
| `proofbench_v2.csv` | **IMO-ProofBench**，60 題證明題（Basic 30 + Advanced 30）。**用 v2**（v1 已 deprecated，修了 PB-Advanced-022 typo）。 | `aa8b813dbd4068137e3d165e5da228f6e0e1cc85a91c37883e1791b954e43af0` |
| `gradingbench.csv` | **IMO-GradingBench**，autograder 校準參考（題目×候選解×人工分數）。供驗證 ProofAutoGrader 與人工的相關性，非主評測集。 | `e85a520c2bbb5a89f2db35088c7935d485922f26cf2bbd04f15e1d967af26cfe` |

下載自：`https://raw.githubusercontent.com/google-deepmind/superhuman/main/imobench/`（抓取日 2026-06-01）。

License：資料 **CC-BY 4.0**、原始程式碼 Apache-2.0。引用見 arXiv:2511.01846 / imobench.github.io。

## proofbench_v2.csv 欄位

`Problem ID, Problem, Solution, Grading guidelines, Category, Level, Short Answer, Source`

- **Problem ID**：`PB-Basic-NNN` / `PB-Advanced-NNN`。
- **Problem / Solution**：LaTeX 題目與參考解。
- **Grading guidelines**：分級標準（標 `(Partial)` / `(Almost)` 各需達到的條件），餵給 grader。
- **Category**：Algebra(16) / Combinatorics(16) / Number theory(14) / Geometry(14)。
- **Level**：pre-IMO(8) / IMO-easy(24) / IMO-medium(18) / IMO-hard(10)。
- **Short Answer**：最終答案（純證明題可能空白）。
- **Source**：出處，如 `(Modified) IMO 2019, P1`。

## 汙染注意

Advanced 子集多為 medalist 新寫 / robustified 改編題（防背題）；Basic 子集含改編公開題。SFT 資料（Nemotron / Cascade-2）若含 olympiad 來源，評測前需檢查是否與本集重疊（尤其 Basic）。
