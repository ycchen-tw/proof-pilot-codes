# k=4 4-config 評測結果 — DeepSeek-V4-flash on IMO-ProofBench

robust 評測：`dsv4-flash × {high,max} reasoning × {notool,pytool} × 60 題 × k=4 = 960 候選`，用校準過的 **flash high_notool** grader（reasoning=high、max_tokens 65536、B.5+reference、`parse_score`）**每候選 2 passes**，空白候選 skip 記 0。原始分數在 `runs/dsv4-flash__*_k4/grades_flashHighNotool_k4_2pass.jsonl`，聚合在 `runs/_grade_high_notool_k4/summary.json`。

## 1. 分數（best-of-4 是 k=4 頭條指標）

| config | **best-of-4** | almost+ | correct | mean-of-4 | advanced | basic | pass一致 |
|---|---|---|---|---|---|---|---|
| high_notool | 4.40 | 0.60 | 0.533 | 3.37 | 2.7 | 6.1 | 0.92 |
| high_pytool | 4.18 | 0.55 | 0.517 | 3.25 | 2.42 | 5.95 | 0.88 |
| max_notool | 4.50 | 0.60 | 0.583 | 3.60 | 2.7 | 6.3 | 0.92 |
| **max_pytool** | **4.64** | **0.617** | 0.567 | **3.62** | **3.1** | 6.18 | 0.88 |

- **best-of-4 比 mean-of-4 高 ~1 分**（4.4 vs 3.4）→ 抽 4 取最好實質加分，坐實 agentic 多候選的價值。
- **max_pytool 整體最佳**（尤其 advanced 3.1 領先）；**high_notool 最便宜且幾乎追平**（4.40）。
- **teacher 天花板**＝max_pytool best-of-4 **4.64/7**、advanced 3.1。

### Delta（best-of-4）
| 對比 | mean delta | 勝/負/平 |
|---|---|---|
| tool @ high | −0.217 | 8/9/43 |
| tool @ max | +0.142 | 11/7/42 |
| reasoning @ notool（max−high） | +0.10 | 12/8/40 |
| reasoning @ pytool（max−high） | +0.458 | 10/9/41 |

這些 delta 都小、多在噪音內（見 §2）。

## 2. 統計分析（用每 config×題 的 8 分數 = 4 候選×2 passes 區分訊號/噪音）

主指標＝逐題 **solve-rate（分數≥6 比例）**（對 grader 在 6-vs-7 / 0-vs-1 的噪音穩健，校準顯示只有 0/1↔6/7 軸可靠）。

- **tool / notool 不互補、反而高度冗餘**：pooled（high+max，每側 16 樣本）solve-rate **r=0.947**；delta mean −0.011；60 題僅 **1 題明確偏 tool、0 題偏 notool、59 題噪音內**。
  - **與 k=1 的「覆蓋互補」差異**：之前互補在**覆蓋層級**（notool runaway vs pytool tool-lock，兩失敗不重疊）。本次 **budget 修正消除 tool-lock + k=4 best-of 救回 runaway** → 兩失敗模式都被填掉 → 品質層級兩者同一條能力曲線。
- **tool 顯著幫助：1/60** — `PB-Advanced-017`（Number theory）：notool solve 0.25(mean 1.8) → tool solve 0.75(mean 4.9)，Δ+0.50，MWU p=0.017。符合「tool 在 NT『算答案』型有用」。
- **tool 顯著傷害：0/60** — budget 修正把舊 k=1 那種 7→0 災難（鑽搜尋迴圈蓋掉正確推理）也消除了。
- **high 勝過 max：0/60** — 無任何題 high 統計上勝 max；max 各處 weakly ≥ high。high 唯一優勢是便宜。
- **真·難題（4 config solve 全 <0.25）：15 題**（14 advanced + `PB-Basic-009`/`PB-Basic-023`）＝能力天花板，tool/max 都救不了。一致簡單（全 >0.75）：16 題。
- **結論**：此 harness 下 pytool 對 flash 既不傷也幾乎不提品質（除 NT 個案）；要突破那 15 題 advanced 天花板靠**訓練**，不是 tool 或加大 reasoning。

## 3. Token / 成本

| config | prompt(輸入) | completion(輸出) | 中位輪數 | 中位延遲 |
|---|---|---|---|---|
| high_notool | 270 | 68.7k | 1 | 499s |
| high_pytool | 351k | **47.7k ↓30%** | 19 | **364s** |
| max_notool | 349 | 112.7k | 1 | 967s |
| max_pytool | 423k | **69.7k ↓38%** | 25 | **576s** |

- **輸出 token：tool 砍 30–38%**（工具打斷 runaway，不再空轉燒滿 budget）；**輸入 token 暴增**（多輪每輪重送成長對話）→ 總 token pytool 是 notool ~6–7 倍。
- **API 金錢成本 ≈ 打平**：pytool 那幾十萬 prompt token 多為重送前綴 = **DeepSeek context cache 命中（幾乎全中）**，極便宜（這正是「tools 全程不變、保 prefix cache」設計的回報）。粗估有 cache：high_pytool ≈ high_notool（略貴）、**max_pytool 略便宜於 max_notool**。無 cache 則 pytool 貴一倍。
- **Kaggle 本機推理（RTX6000Pro）才是 tool 省 token 的真戰場**：無 API 計價，瓶頸＝自迴歸生成（output token）；prompt 是便宜的 prefill（多輪 KV-cache 重用）。**output ↓30–38% + 延遲 ↓25–40%** 對「每題 1 小時」硬限制是實打實優勢。
- ⚠️ **未記 cache-hit token**（`client._usage` 只抓 prompt/completion/reasoning）→ 上面 API 省多少是估算，要實測需補抓 `prompt_cache_hit_tokens`。

## 4. Caveats（必記）

- **利益衝突**：grader=flash、被評也=flash（teacher 自評）→ 可能對 DeepSeek 風格給分偏高，**correct 0.53–0.58、advanced 7 分題務必人工抽查**。
- grader **系統性偏嚴**（校準 bias −0.77）→ 絕對分是保守下限。
- 可靠的方向性訊號只有：**max_pytool 在 advanced 領先**、**tool 在 NT 個案有用**、**15 題 advanced 天花板**；其餘小 delta 皆噪音。
