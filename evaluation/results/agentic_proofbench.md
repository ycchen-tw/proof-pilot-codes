# Agentic pipeline on IMO-ProofBench — DSMV2-Simple-3R (refined-only)

把 `distill_gen/math_3r` 的多 agent 證明 pipeline（**prove→verify→rank→refine→select**，refined-only
版）當作 ProofBench 的一個 condition 跑全 60 題，量它相對於既有單模型 baseline（`k4_grading.md`）的
分數。對應 `plan.md` §Phase 4（agentic）。

## 設定

- **pipeline**：6 provers（同 prompt，多樣性靠 backend 取樣）→ 每個 valid proof × 2 verifiers → rank →
  top-4 進 3 refiners → **4 selectors 在 valid refined 中多數決挑 1 個** → `final_proof`。effort=high、
  所有階段 `max_tokens=180000`、refined-only selector（git `f44996f`）。
- **生成**：`run.py --input proofbench_v2.parquet --run-id pb_r3`（`proofbench_v2.parquet` = 由
  `data/proofbench_v2.csv` 的 `Problem` 欄建的 60-row 輸入）。60 題、1496 calls、**0 error / 0 fallback**、
  34.5M ctok（96.8% reasoning）、~$10–12。輸出 full trace 在 `distill_gen/math_3r/outputs/pb_r3/`（gitignored）。
- **adapter**：`harness/agentic_to_responses.py` 把 full-trace record 攤成 grader 吃的 `responses.jsonl`，
  **同一份生成**寫三個 run（join `Problem` 文字取 PB id / subset / level）：
  - `pb_r3_select` — k=1 = 選出的 `final_proof`（pipeline 真正輸出）
  - `pb_r3_refined` — 全部 valid refined（179 個，mean 2.98/題）= **best-of-3-refined**（selector oracle 上界）
  - `pb_r3_provers` — 全部 valid prover（358 個，mean 5.97/題）= best-of-6 raw-sampling 對照
- **grader**：校準過的 `flash high_notool`（B.5 verbatim、reasoning=high、max_tokens 65536、**2 passes**），
  與 `k4_grading.md` baseline **完全同一個 grader** → 可直接比。`grade_proofs.py … --out-name grades_pb_r3.jsonl`。

## 分數（best-of-k，flash high_notool ×2pass）

| run | best-of-k | mean-of-k | almost+ | correct | basic | adv | pre-IMO | easy | medium | hard |
|---|---|---|---|---|---|---|---|---|---|---|
| **select（k=1，真正輸出）** | **4.83** | 4.83 | .667 | .567 | 6.23 | **3.42** | 6.94 | 6.23 | **3.89** | **1.45** |
| refined best-of-3（selector oracle） | **5.00** | 4.44 | — | — | 6.52 | 3.48 | 7 | 6.40 | — | 1.45 |
| provers best-of-6（raw 對照） | 4.56 | 3.52 | .60 | .567 | 6.38 | 2.73 | 7 | 6.17 | 3.56 | 0.55 |

既有單模型 baseline（`k4_grading.md`，同 grader、k=4）：

| config | best-of-4 | mean-of-4 | adv |
|---|---|---|---|
| high_notool | 4.40 | 3.37 | 2.7 |
| high_pytool | 4.18 | 3.25 | 2.42 |
| max_notool | 4.50 | 3.60 | 2.7 |
| **max_pytool（前天花板）** | **4.64** | 3.62 | 3.1 |

by category（select vs 最佳 baseline）：Algebra **5.91**（vs 5.03）、Combinatorics 4.47（vs 4.5）、
Number theory **5.5**（vs 5.14）、**Geometry 3.32**（vs max_notool 4.46）。

## 主要結論

1. **agentic 單一輸出 4.83 > 所有 k=4 best-of-4 baseline（最高 4.64）**。注意公平性：baseline 是「抽 4 個 +
   grader oracle 挑最好」；agentic **只交 1 份**就贏過 oracle-pick-of-4。代價是 ~25 calls/題（vs baseline 4）。
   對「單發品質」（mean-of-k ≈ 3.4–3.6）則領先 **+1.2~1.5**。

2. **refine 是真正的品質引擎**：
   - 每份證明 refine **+0.92**（單個 prover 3.52 → 單個 refined 4.44）。
   - best-of-3-refined **5.00 > best-of-6-prover 4.56（+0.44）**：用更少候選贏更多 raw 候選 → refine 在改，不是多抽。
   - advanced 尤其明顯：refined 3.48 vs raw 2.73。

3. **selector 接近最優、漏分少**：selected 4.83 / oracle-best-refined 5.00 = **96.5%**，平均每題只比「3 個
   refined 挑最好」差 **0.175**。selected（4.83）也 > 平均 refined（4.44），確實在挑好的。9/60 題有更好的 refined
   沒被選中，且 **2 題主導**：`PB-Basic-007`（選 3.5、池有 7）、`PB-Basic-030`（選 3、池有 6.5），其餘 7 題都只差
   +0.5（6.5→7 邊際）。改善方向＝這幾題的多數決判斷。

4. **advanced / hard 全場最高**（adv 3.42 > max_pytool 3.1；IMO-hard 1.45 > 所有 baseline 的 ≤1.25）→ 多 agent
   在難題上推得比 tool / max-reasoning 更高；但 **hard 仍 ~1.5/7，天花板沒打破**（與 `k4_grading.md`「15 題 advanced
   靠訓練突破」一致）。

5. **Geometry「輸」是 best-of-4 oracle 假象，非 agentic 弱點**：逐題看 **select ≈ provers（同生成，無一題差 ≥1）**
   → refine/select 沒傷幾何。max_notool 幾何 4.46 高，是靠 **2 題孤立幸運命中**（`PB-Advanced-003` 7、`PB-Basic-026`
   6.5，其他 config 全 0）——k=4 抽 4 取最好在低 solve-rate 難題的變異紅利。扣掉那 2 題 max_notool 幾何 ≈ 3.5，與
   select/provers 打平。要拉高幾何靠**生成端**多樣性，不是改 refine/select。

```
單個 raw prover  3.52
  → refine       4.44   (+0.92／份；refine 核心價值)
  → best-of-3    5.00   (refine 池天花板，已勝所有 baseline)
  → selector 挑1 4.83   (捕捉 96.5%，漏 0.175，主要卡 2 題)
```

## Caveats（必記）

- **利益衝突**：grader=flash、被評的 pipeline 也走 flash → 對 DeepSeek 風格證明可能給分偏高。對所有列**一致**，
  相對比較仍有效；但**絕對分保守 + 高分 advanced / 34 題 correct 需人工抽查**（plan §4）。
- **汙染**：flash 可能背過公開題（尤其 basic 6.2+）→ 評 teacher pipeline 的固有限制，非 bug。
- 這是量 **teacher pipeline 的證明品質**，非訓練後 student；student 評測另跑（plan §Phase 3）。
- best-of-4 baseline 享 oracle-pick-of-4 紅利；agentic 只交 1 份但花 ~6× call。比較時分清「committed 單發」vs「oracle best-of」。

---

## DeepSeek-V4-Pro vs Flash（同 pipeline、全 60、同 flash grader）

把同一個 refined-only pipeline 換成 `--model deepseek-v4-pro`（其餘設定不變）跑全 60 題（`run-id pb_r3pro`），同 flash high_notool grader ×2pass 評分。生成健康：60 題 0 fallback、valid μ 5.82、43M ctok（其中 12 errored/1 trunc 為連線 drop + 餘額耗盡時的尾段 select；該 2 題已刪記錄 resume 補跑乾淨）。

| run | pro | flash | Δ | pro correct |
|---|---|---|---|---|
| select（k=1） | **5.31** | 4.83 | +0.48 | .683 (41/60) |
| refined best-of-3 | 5.38 | 5.00 | +0.38 | .70 |
| provers best-of-6 | 5.02 | 4.56 | +0.46 | .683 |

**by level（select）**：pre-IMO 7.0/6.94、IMO-easy 6.73/6.23、IMO-medium 3.97/3.89、**IMO-hard 2.95/1.45（pro 翻倍）**。
**by category（select）**：Algebra 5.81/5.91、Combi 4.06/4.47、NT 5.32/5.5、**Geometry 6.14/3.32（pro +2.82 輾壓）**。

→ flash grader 下，**pro 的整體 +0.48 幾乎全來自 Geometry（+2.82）與 IMO-hard（+1.5）**；easy/medium 與 algebra/combi/nt 兩者相當（combi flash 微勝）。pro 把 flash 最弱的幾何與難題補強，其餘打平。

## Grader 交叉驗證 — Claude 獨立盲評（`claude_xcheck.py`）

flash grader 評的是同家族（flash/pro 都 DeepSeek），故用 **Claude Code sub-agents 當獨立 grader 盲評**：每題 2 份 selected proof 隨機標 A/B（agent 不知哪份是 pro/flash），10 個 sub-agent 各評 6 題、同 B.5 rubric、0/1/6/7。

**結論被修正——pro 的整體優勢 grader-dependent：**

| grader | pro | flash | 判定 |
|---|---|---|---|
| flash grader | 5.31 | 4.83 | pro **+0.48** |
| **Claude grader** | 5.32 | 5.30 | **+0.02（打平）** |

兩 grader **對 pro 一致（~5.31）**，但 flash grader 給 flash-pipeline 較低（4.83 vs Claude 5.30）。**by category（Claude）**：Geometry pro 5.93 ≫ flash 3.64（**兩 grader 都同意 pro 幾何輾壓，robust**）；但 Algebra/Combi/NT 上 **Claude 反而認為 flash 略勝**（6.25/5.19/6.00 > 5.38/4.44/5.64）。grader bucket-一致率 88%。

**深挖原因（adjudicated 案例）——不是「flash 偏袒自家」，是兩 grader 互補盲點：**

- **flash grader = 嚴格邏輯稽核**（不跑 code）：抓循環論證、假 lemma、hand-wave。
  - `PB-Advanced-006`：flash proof 的「零點集合是子群」**循環論證**（拿封閉性證封閉性）+ `f(6)=0` 對任意 d≥2 不成立 → flashG 0（**正確**），Claude 7「rigorous」（**漏看兩個錯**）。
  - `PB-Advanced-029`：sufficiency 的 lemma `C(n,i)≡C(n₁,a)C(p−1,b) mod p^e` **對 p=2 和 p=3 都假**（實算驗證）且 hand-wave → flashG 1（**正確**），Claude 6「Almost」（**太鬆**）。
- **Claude grader = 數值驗證**（會 brute-force/模擬）：抓錯的最終答案/座標。
  - `PB-Advanced-003`(pro)：proof 宣稱的 mixtilinear 觸點座標**錯** → Claude 數值重算抓到給 0；flashG 無法驗證、相信了給 7（**被自信錯算騙**）。
  - Adv-023/020/018/010 等錯答案題兩 grader 多半都抓到（給 0）。

**淨效果**：flash 的證明 circular/hand-wave 比 pro 多 → flash grader 把這些 gap ding 下去（flash-pipeline 低分）、Claude 寬待（高分）→ 差異全落在 flash-pipeline，pro 兩 grader 一致。**所以「Claude 顯示打平」主要是 Claude 過度寬待 flash 的嚴謹漏洞；flash grader 的「pro > flash」在 rigor 維度上更接近真相。但沒有任一 grader 是真值——最穩是兩者並用（rigor 稽核 + 數值驗證）或人工。**

## Token 使用對照（pro vs flash，同 60 題）

| | flash | pro | pro/flash |
|---|---|---|---|
| 每題 completion（全）| mean 576k / med 592k | mean 706k / med 781k | **1.23×** |
| 每題（**advanced** 30）| 730k / 785k | **918k / 1014k** | **1.26×** |
| 每題（basic 30）| 421k | 494k | 1.17× |

reasoning 佔 ~97%（proof 本體 content 僅 3%）。**各階段 per-call（全 / advanced）pro/flash 比**：prove 1.17× / 1.19×、verify 1.42× / 1.37×、**refine 1.45× / 1.55×**、select 1.10× / 1.29×。prove 主導總量（~60%），但 **pro 的「多燒」集中在 verify+refine（審查+打磨）**，且**題目越難越明顯**（advanced refine 1.55×、佔比 16%→20%）。對應 pro 在 IMO-hard 的領先＝多出來的算力花在把難題證明改對改嚴謹，而非初版想更久。

## 重現

```bash
# 1. 建輸入 parquet（60-row，由 proofbench_v2.csv 的 Problem 欄）—— 見 commit 內 proofbench_v2.parquet
# 2. 生成
DEEPSEEK_API_KEY=... uv run python distill_gen/math_3r/run.py \
    --input distill_gen/math_3r/proofbench_v2.parquet --run-id pb_r3 \
    --effort high --max-tokens 180000 --num-provers 6 --verify-k 2 --num-refiners 3 \
    --num-selectors 4 --concurrency 300 --problem-concurrency 60
# 3. adapter -> 三個 run（select / refined / provers）
uv run python evaluation/harness/agentic_to_responses.py \
    --records distill_gen/math_3r/outputs/pb_r3/records.jsonl \
    --data evaluation/data/proofbench_v2.csv --out-prefix pb_r3
# 4. grade（同 baseline grader）
cd evaluation/harness && DEEPSEEK_API_KEY=... uv run python grade_proofs.py \
    --run-ids pb_r3_select,pb_r3_refined,pb_r3_provers --data ../data/proofbench_v2.csv \
    --passes 2 --reasoning high --max-tokens 65536 \
    --base-url https://api.deepseek.com/v1 --served-model deepseek-v4-flash \
    --api-key-env DEEPSEEK_API_KEY --concurrency 200 --out-name grades_pb_r3.jsonl

# 5. pro：步驟 2-4 改 --model deepseek-v4-pro --run-id pb_r3pro（grader 仍 flash）
# 6. Claude 盲評交叉驗證
uv run python evaluation/harness/claude_xcheck.py chunks \
    --runs pb_r3pro_select,pb_r3_select --data evaluation/data/proofbench_v2.csv --n-chunks 10
#   -> 對 chunk_00..09 各 spawn 一個 Claude sub-agent 寫 result_NN.json（B.5 盲評 A/B）
uv run python evaluation/harness/claude_xcheck.py agg --runs pb_r3pro_select,pb_r3_select
```

> ⚠️ `grade_proofs.py` 的聚合 summary 寫到 `runs/_grade_high_notool_k4/summary.json`（路徑按 grader config，與
> baseline k4 撞名）。本 doc 的數字是用各 run 的 raw `grades_pb_r3.jsonl` 重新統一聚合得出（與 baseline 同邏輯），
> 不依賴那個會被覆蓋的 summary。
