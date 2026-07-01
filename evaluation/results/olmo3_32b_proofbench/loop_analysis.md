# OPD 32B (v33/s200) ProofBench 撞-cap 生成：infinite-loop vs overthinking 分析

**來源 run**：`tmp/pb_agentloop/runs/full60_opd32b_s200/`（OPD 32B v33 step_200，agentic prove→verify→refine→select，max_tokens=128000，2026-06-22）。
**方法**：全 60 題 1,418 個生成中，53 個 `finish_reason=length / truncated=True`（撞 128k cap）。對每條取 **reasoning_content 最後 8,000 字**，由 9 個 general-purpose agent **盲讀**分類（不餵指標），事後與廉價指標 `zlib_tail` 交叉檢查。
**reasoning 保存**：53 條的完整 reasoning_content（每條 ~150k–510k 字 / 128k token）**100% 完整保存**在 stage JSON；loop 跑在 `reasoning_content`、`content` 為空。

## 結論：85% 是真的 loop，只有 15% 是 overthinking

| 類別 | n | % | 定義 |
|---|---|---|---|
| **infinite_loop** | 35 | 66% | 退化的逐字重複（單 token / 短語 / 句子 / 整段 verbatim 複製），無新資訊 |
| **semantic_loop** | 10 | 19% | 無逐字重複，但反覆重啟同一 lemma/case，cosmetic 變化、無實質進展 |
| **overthinking** | 8 | 15% | 真實多樣的數學推理，持續產出新算式/新 case/自我糾錯，只是沒在 cap 前收斂 |

→ **任何形式的 loop（IL+SL）= 45 / 53（85%）；真正「想太久沒壞掉」只有 8（15%）。**

## 廉價指標可單獨分流（盲指標 vs agent 判讀，幾乎全中）

`zlib_tail`（最後 8000 字的 zlib 壓縮比）三段乾淨分離：

| zlib_tail band | 判定分佈 | 解讀 |
|---|---|---|
| **< 0.02** | infinite_loop 16 / 16 | 退化到單 token/短語（` a?`、`+2`、`1,`、`3+`、`2^?`、`384*?`…）的 hard attractor |
| **0.02–0.28** | infinite_loop 19 + semantic_loop 9 | 段落級 verbatim 重複 / 語義循環 |
| **> 0.28** | overthinking 8 + semantic_loop 1 | 真實長推理（除 1 條 S53 邊界數值降階） |

**即 `zlib_tail > 0.28` ⇒ 幾乎必為 overthinking；`< 0.02` ⇒ 必為退化 loop。** 中段才需讀文字。

## 病灶分佈

- **依 stage**：prove 38 條（IL26 / SL4 / OT8）、refine 15 條（IL9 / SL6，**refine 一條都不是 overthinking ——全是 loop**）。refine 階段撞 cap = 100% 病態循環，與記憶 [[opd32b-s200-proofbench-eval]]「refine 截斷=循環非長考」一致。
- **8 條 overthinking 全在 prove**，且集中在**長座標/長計算題**：Geometry 4（Adv-015×2、Adv-016、Basic-026）、Combinatorics 2、Algebra-FE 1、NT 1。這些是「真的需要很長」而非壞掉。

## 強訊號：capitulation 開頭 → 段落 loop

45 條 loop 中約 18 條的重複單元以同一句開頭：**「Given the time, I think/will produce a solution that…」**。模型寫出這種「時間/長度快用完，我就直接給個解」的投降段落後，**整段被逐字複製數十次**直到撞 cap。這是 EOS-under-training 的指紋：模型想結束卻沒學會發 EOS，改成重複那段投降語。→ 對 V34 是極好的 tail-mask / EOS-anchor 觸發訊號。

## 對 V34 的意涵

- **tail-masking 取代 whole-traj drop 站得住**：85% 撞-cap 是 loop，尾段確實是壞 token，遮掉尾段重複區、保留前段有效推理是對的。
- **8 條 overthinking 不該被當 loop 丟**：用 `zlib_tail > 0.28`（或等價 rep 指標）當 gate，避免把長座標 bash 誤殺。
- detector 可廉價落地：`zlib_tail` 兩端直接定案，中段配 n-gram 重複率 + capitulation-phrase 偵測。

完整逐條判定（53 條 verdict + 指標）：`loop_classification.json`（本目錄）。
detector 實作：`evaluation/harness/zlib_runaway_detector.py`（streaming + offline，附 `--stage-json` 掃描 ProofBench stage 檔）。

## 附錄：streaming loop detector（zlib 滑窗，已實測 FP）

`zlib_tail` = 一段文字 zlib 壓縮比（`compressed/raw`）= LZ77 抓重複 → loop 壓到趨近 0、正常推理 ~0.3。可邊解碼邊算（12k bytes ~ 幾十 µs），且可直接跑在 token-id bytes 上、不必 detokenize。

**單門檻 zlib 滑窗（W=12000 字、step 1000、hard<0.05 或 soft<0.18×3）實測**：
- loop 偵測：token / paragraph / semantic loop 全抓到（省 30–95k token；W=6000 會漏段落 loop，週期要 < W/2）。
- 對 **1,008 條夠長的 clean-EOS 生成**做 FP scan：**僅 3 條誤判（0.30%）**，且全是**合法的結構化列舉/長算術**（`o=1409,L=2,k=5 / o=1411,…`、質因數分解），模板重複但數字一直變、最後都 recover 成 valid \boxed。

**robust 二階規則（本資料集 0% FP / 100% loop catch）**：
- **HARD**：`zlib < 0.05` → 立即 abort（退化 token loop；列舉下限 0.141，永遠不會這麼低）。
- **SOFT**：`zlib < 0.18` **持續 ≥ ~20 個連續視窗（~20k 字 / ~12–15k token）** → abort。依據：列舉 FP 的 max_low_run 只有 **5/5/9**，真 loop **≥62**（段落 loop 198–381）——gap 巨大。
- 失敗的嘗試（記錄）：distinct-shingle 第二訊號**不可用**——段落 loop 是「近似逐字」（每份微小漂移），exact-shingle distinct≈1.0 與列舉無法區分。靠 zlib 的 fuzzy LZ77 + 「持續性」才是對的。

**落地點**：① sglang server-side runaway 早 abort（abort≠改取樣分佈，on-policy 安全，見 [[opd-rollout-no-distribution-change]]）；② eval / Kaggle 每題 stop criterion；③ V34 trainer EOS-region diag 同一指標。**代價**：SOFT 階有 ~12–15k token 偵測延遲（HARD 階即時），但 loop 本會跑到 128k，仍省 100k+。**caveat**：FP n 只有 3（60 題 eval），門檻上線前該在更大樣本再驗。
