# Grader 校準結果 — IMO-GradingBench

驗證「我們的 DeepSeek grader 評得準不準」，作為信任後續所有 ProofBench 分數的前提（plan §4 / Phase 0.5）。

## 設定

- 校準集：`data/gradingbench.csv`（1000 列 = 30 題 **Advanced** × ~33 候選解，每列附人工 `Points` 0–7 與 `Reward` 4 級）。
- 取 **200 題分層子集**（每個 `Reward` 類別各 50：Incorrect/Partial/Almost/Correct；seed 1234）。
- 每列用**對齊論文 B.5 的 grader prompt**（`prompts/grader.md`，有 reference solution + guidelines）評分 → parse 成 0/1/6/7。
- 跑 **4 個 config = {high, max} reasoning × {notool, pytool}**，flash 與 pro 各一輪（同 200 題同 seed，可直接對比）。`pytool` = 給 grader 一個 `execute_python` 工具自行驗算。
- 指標對齊論文 §5.4：人工 7→4 級 bucket `(7 / 6–4 / 3–1 / 0)`（= `Reward` 欄）；算 4-cat accuracy、MAE（golden floor 3.9%）、Pearson（逐題 + 按題聚合）、confusion、bias。
- 工具：`harness/calibrate_grader.py`（async）。原始輸出：`runs/grader_calibration/`（flash）、`runs/grader_calibration_pro/`（pro）。

## 結果

| config | model | acc4 | MAE% | r逐題 | r聚合 | bias | 平均 token |
|---|---|---|---|---|---|---|---|
| high_notool | flash | 0.540 | 20.6 | 0.706 | 0.875 | −0.77 | 6.9k |
| | **pro** | 0.553 | 20.5 | 0.699 | 0.848 | −0.68 | 13.7k |
| high_pytool | flash | 0.550 | 20.7 | 0.706 | 0.878 | −0.86 | 13.3k |
| | pro | 0.556 | 20.1 | 0.711 | 0.835 | −0.60 | 14.5k |
| max_notool | flash | 0.540 | 20.8 | 0.722 | 0.870 | −1.06 | 24.4k |
| | pro | 0.571 | 20.2 | 0.711 | 0.875 | −0.84 | 27.4k |
| max_pytool | flash | 0.548 | 21.4 | 0.699 | 0.881 | −1.01 | 21.1k |
| | **pro** | **0.582** | **19.4** | **0.731** | 0.869 | −0.86 | 22.3k |

「Almost(6)」class recall（最弱的一類）：flash **0.04–0.08** → pro **0.14–0.16**。

## 重點結論

1. **逐題 vs 聚合 — 別誤讀準度**。逐題 Pearson ~0.70–0.73 看似低，但**按題聚合就跳到 ~0.85–0.88**；論文的 0.96/0.93 是再按「模型」聚合（30 題平均），是更強的 smoothing。逐題本來就難（論文 Table 7：o3/Gemini 逐題也才 ~0.54 準度）。**排名模型用的是聚合視角，flash 與 pro 在此都 ~0.87，等價。**
2. **tool 與 max effort：對 flash 無用，對 pro 有一點用**。flash 4 個 config 準度幾乎平（~0.54）；pro 從 high_notool 0.553 → max_pytool 0.582（+0.029）。pro 是更有能力、能利用額外算力/工具的 grader，但天花板仍 ~0.58。
3. **中間類（Almost/Partial）是兩者共同硬傷**。grader 兩端很準（Incorrect ~0.88、Correct ~0.90）但中間爛；「6 vs 7」對 flash 幾乎判不出（Almost recall 0.04），pro 改善到 0.14–0.16 仍不可靠。
4. **兩者都偏嚴**（系統性低估人工，bias 全為負；pro 沒 flash 嚴）。會保守低估我們模型的證明。
5. **成本：pro ≈ flash 的 19×**（flash 200×4 ~5.5 CNY；pro 200×4 = **104.6 CNY / ~$14.5**；pro ~4 CNY/M output ≈ 10× flash，且多用 ~2× token）。

## 決策（grader 選型）

| 用途 | 選擇 | 理由 |
|---|---|---|
| **排名 checkpoint**（主用途，60 題聚合） | **flash high_notool** | 聚合相關 ~0.87 = pro，便宜 19×；max/tool 對 flash 無增益 |
| **agentic loop 單候選 verifier**（逐題判好壞） | **pro max_pytool**（若需要） | 全表最佳逐題（0.582 / MAE 19.4%），pro 能用 tool+max |
| 任何「Almost vs Correct」細判 | 不可全信，需人工抽查 | 兩者 Almost recall ≤ 0.16 |

## Caveats

- **balanced 子集比自然分布難**：自然分布加權後準度 ~0.62（兩端佔多、grader 兩端準）。
- **僅 Advanced**（gradingbench 30 題皆 Advanced）；Basic 評分未校準，預期更準。
- **與論文 Table 7 非 apples-to-apples**：論文是 reference-free，我們有 reference+guidelines（較簡單）卻只到 0.54–0.58，代表 DeepSeek 當 grader 比 frontier 弱。
- grader 走 thinking 模式 → temperature 被忽略，**grader 有內在隨機**（單次評分），逐題雜訊一部分來自此。
