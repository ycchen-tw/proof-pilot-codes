# OLMo 3 32B — IMO-ProofBench v2 評測（agentic prove→verify→refine→select）

OLMo 3 32B（`olmo3_sink`，OPD on-policy distillation 的 step_200 checkpoint）在 **IMO-ProofBench v2 全 60 題**上、用 prove→verify→refine→select agentic loop 跑出的證明與評分。每題的最終證明在 [`proofs/`](proofs/)，逐題分數在 [`SCORES.md`](SCORES.md) / [`scores.tsv`](scores.tsv)。

> ⚠️ 評分用 **Claude grader（含 sympy/brute-force 驗算）**，與 repo 內 teacher 天花板所用的 **flash high_notool grader 不是同一個**，故與 4.64/4.83 等 teacher 數字**不能直接相減比較**（見下方 §teacher 比較）。

## 結果

| 區分 | n | 平均分 (/7) | solved (≥6) |
|---|---|---|---|
| **全體** | 60 | **4.48** | 36/60 (60%) |
| Basic | 30 | **6.13** | 26/30 |
| Advanced | 30 | **2.83** | 10/30 |

依難度（強烈的難度分層）：

| level | n | 平均 | solved |
|---|---|---|---|
| pre-IMO | 8 | **7.00** | 8/8 |
| IMO-easy | 24 | **5.92** | 20/24 |
| IMO-medium | 18 | **3.22** | 7/18 |
| IMO-hard | 10 | **1.30** | 1/10 |

**分數分布極度 bimodal**：`7×32, 6×4, 1×21, 0×3`。也就是「要嘛完全做對(7)，要嘛卡在核心 lemma／答案就錯(0–1)」，中間極少。3 個 0 分是答案本身就錯（PB-Advanced-018 L=2≠3、PB-Advanced-023 3001≠3、PB-Advanced-027 Bob≠Alice）。

**典型失分模式（medium/hard）**：能正確化簡、建立框架、甚至猜對最終答案，但在**最關鍵的一步**（無窮遞降、關鍵恒等式、case 網羅、involution 引理…）改用 hand-wave 或寫出**可被反例推翻的假引理**，被 grader 以 sympy/brute-force 抓出 → 1 分。easy/pre-IMO 則幾乎都能完整做出（pre-IMO 滿分）。

## 方法

- **模型**：OLMo 3 32B = `olmo3_sink`（OLMo 3 + 可學 attention sink），student 來自 OPD（DeepSeek-V4-Flash teacher 的 on-policy distillation）的 `agentic_32b_lc140k_v33` run、**step_200** checkpoint。
- **部署**：training-format checkpoint → `deploy/make_olmo3sink_deploy.py`（legacy-rope/bf16）→ `kaggle/serve/enable_swa_config.py`（hybrid-SWA）→ SGLang **TP4 / fp8 weight / fp8_e4m3 KV / SWA / FA3 / reasoning-parser deepseek-r1**（4×H200，`.sif` + `deploy/target/olmo2_sink.py` bind-mount）。
- **agentic loop**：`distill_gen/math_3r` 的 `solve_problem`，每題 **6 prover → 每個有效證明 2 verifier → 3 refiner → 4 selector（多數決）**，`max_tokens=128000`、`temperature=1.0`。selector 只輸出 ID、證明由 map 決定性取出（不重寫、不會截斷最終證明）。
- **生成規模**：60 題、~5.8 小時、共 ~36.5M completion tokens。完整逐 call reasoning trace（prove/verify/refine/select 每一次呼叫的 reasoning_content+content）保存在本機（118MB，未入 git；可另發 HF）。

## 評分

- 10 個 Claude grading agent（每個 6 題）以 **IMO 0/1/6/7 rubric** 評分，並用 **Bash 跑 sympy / brute-force 實際驗算**最終答案與關鍵步驟（恒等式、候選解、反例搜尋），把 hand-wave 與假引理嚴格抓出。
- rubric：0=幾乎無進展、1=部分進展但有本質性 gap、6=幾乎完整僅軽微瑕疵、7=完全正確。

### teacher 比較（apples-to-apples，同一 grader 家族）

teacher（DeepSeek-V4-Flash/Pro）跑**同一個 math_3r agentic pipeline**，並由 `../agentic_proofbench.md` 的 **Claude 盲評交叉驗證**（`evaluation/harness/claude_xcheck.py`：Claude sub-agents、B.5 rubric、0/1/6/7、含數值驗算）評分 —— 與本評測**同方法**，故可直接比：

| 系統 | 方法 | Claude grader | flash grader |
|---|---|---|---|
| **OLMo 3 32B（OPD student, s200）** | agentic select | **4.48** | — |
| DeepSeek-V4-Flash（teacher） | agentic select | **5.30** | 4.83 |
| DeepSeek-V4-Pro | agentic select | 5.32 | 5.31 |

**相同 pipeline + 相同 Claude grader 方法下：student 4.48 vs flash teacher 5.30 → 約 −0.82**（真實可比的差距，不是 grader 不同造成的假象）。差距**集中在 medium/hard**；easy/pre-IMO student 已接近天花板（pre-IMO 7.0）。

注意：(1) 兩次 Claude 評分是**不同 batch**（可能有跨批 variance）；(2) teacher 那次是 pro/flash 隨機 A/B **盲評**，本評測非盲；(3) `claude_xcheck.py` 的結論也指出 Claude grader 偏寬待 flash 的嚴謹漏洞、flash grader 偏嚴抓循環論證 —— **沒有任一 grader 是真值**，最穩是 rigor 稽核 + 數值驗算並用。單輪 flash baseline（flash grader）：best-of-4 4.64、t3 self-verify 4.58。

## 其他發現

- **agentic loop 很穩**：60 題裡 **59/60 都走完整 select**，只有 1 題 fallback（refiner 全失敗）。call 層級 truncation 53/1418 (3.7%)，但 6 prover/3 refiner 的冗餘把它吸收掉。
- **refine 截斷＝退化迴圈，不是「想太久」**：截斷的 refiner 是 reasoning 落入重複吸引子、一路衝到 128k cap（zlib≈0.08、同一行重複 80–214 次、15-gram 60% 重複），這是 OPD step_200 的 length 自我放大在思考端的體現（細節見 repo memory `opd-loop-rootcause` / `soft-distill-v2-loops-eos-undertraining`）。verify/refine 的**輸入只含 `<solution>` 本文、不含 thinking**。

## 重現

```bash
# 1) 部署權重（OPD step_200 → serve-ready）
python deploy/make_olmo3sink_deploy.py \
  --src training/opd_v2/runs/agentic_32b_lc140k_v33/checkpoints/step_000200/hf \
  --dst outputs/agentic_32b_lc140k_v33-s200-deploy
python kaggle/serve/enable_swa_config.py outputs/agentic_32b_lc140k_v33-s200-deploy
# 2) SGLang TP4 fp8 serve（GPU 0-3）：見 tmp/pb_agentloop/serve_tp4.sh
# 3) 跑 agentic loop（math_3r.solve_problem，6/2/3/4，128k，temp 1.0）→ 存全 stages
# 4) Claude grader（每 6 題一個 agent）以 0/1/6/7 + sympy 驗算
```

## 檔案

- [`SCORES.md`](SCORES.md) — 逐題分數表（連結到各證明）
- [`scores.tsv`](scores.tsv) — 機器可讀分數
- [`proofs/PB-*.md`](proofs/) — 60 題各自的：題目 + 模型最終證明 + 分數 + grader note
