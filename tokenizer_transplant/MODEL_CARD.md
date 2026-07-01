# Olmo-3-1025-7B + DeepSeek-V4-Flash tokenizer（centered-OMP transplant）

> 這是隨產出模型一起存放在 `/models/Olmo-3-1025-7B-deepseekTok` 的 model card 的
> vendored 版本。方法分析與 mergekit 比對見 `../../docs/tokenizer/transplant.md`。

本模型是把 **`allenai/Olmo-3-1025-7B`** 的 tokenizer/vocabulary 換成
**`deepseek-ai/DeepSeek-V4-Flash`** 的 tokenizer（vocab 100,278 → 129,280）。Transformer body 權重
全部保留原本的 Olmo 權重；只有 `embed_tokens` 與 `lm_head` 被重建以對應新 vocab，方法是
**mean-centered Orthogonal Matching Pursuit (OMP)** embedding transplant。

- **Base（保留權重）**：allenai/Olmo-3-1025-7B（olmo3，32 層，hidden 4096，untied embeddings）
- **Donor（tokenizer + reference embeddings）**：deepseek-ai/DeepSeek-V4-Flash
- **Tokenizer**：DeepSeek-V4-Flash byte-level BPE，vocab 129,280，`bos/eos/pad = 0/1/1`
- **動機**：DeepSeek tokenizer 對 CJK/多語的壓縮率遠優於 Olmo 的 cl100k 系 tokenizer（中文 ~2.6× 少 token）。

> ⚠️ **這是 warm-start 初始化，不是成品模型。** Zero-shot 可生成通順的英文/程式碼，但 70k 個新
> （多為 CJK）token 只是被*初始化*，其 output 分布尚未校準。要有強的多語生成需先做 continued
> pretraining。見 **限制** 一節。

---

## 方法

Training-free tokenizer transplant via Orthogonal Matching Pursuit
（Goddard & Fernandes Neto 2025, [arXiv:2506.06607](https://arxiv.org/abs/2506.06607)）。

對每個 output matrix（`embed_tokens` 與 `lm_head`，各自獨立處理）：

1. **Anchors** = 字串同時存在於兩邊 vocab 的 token（**59,084** 個），以 byte-level surface form 比對
   （兩個 tokenizer 共用相同的 `Ġ` byte-mapping，已用 decode 驗證）。
2. **Shared tokens** → 把 base（Olmo）的 row **完全複製**到新的 vocab id。
3. **New tokens**（**70,196** 個，佔 vocab 54.3%）→ OMP。把新 token 的 *donor* embedding 表示成
   anchors 的 donor embedding 的稀疏（k=64）線性組合；再把**相同係數**套到那些 anchor 的 *base*
   embedding 上，得到 Olmo 空間中的 row。
4. **Mean-centering**：OMP 前先把 donor 與 base 的 anchor 空間都減去均值，重建後再把 base 均值加回。

### Faithfulness 註記（重要）

這**不是** raw-canonical OMP，而是 **centered variant**。它和 mergekit 的 `SPARSE_TOKEN_BASIS`
(STB) 共用 mean-centering 的想法，但**不等於** STB：STB 是把每個新 token 用 dense lstsq 投影到由
SVD 得到的 shared basis，本法則是直接對 anchors 做稀疏 k=64 的 OMP。用 mergekit 的詞彙講，它最接近
`--approximation-method omp` **再加上 centering**。與 canonical OMP 的差異與實測影響：

| 差異點 | Canonical | 本法 | 影響（實測） |
|---|---|---|---|
| Atom 選擇 | raw inner product | 單位化（cosine） | fidelity-neutral |
| Least squares | ridge-free incremental QR | normal-eq + adaptive ridge 1e-3 | fidelity-neutral |
| **Mean-centering** | 無 | **有** | output-logit 校準；fidelity-neutral |

centered vs uncentered、以及與 mergekit 的對照實驗見 `../../docs/tokenizer/transplant.md`。

---

## 建置方式

- Donor embedding 只從 **46 個 shard 中的 2 個**抽出（`embed.weight`、`head.weight`，皆為 dense
  `[129280, 4096]` bf16）——約 2 GB，而非完整 160 GB。
- 建置程式：本套件 `tokenizer_transplant/`，純 PyTorch，無 mergekit 依賴（DeepSeek 的自訂
  `deepseek_v4` arch 不被 mergekit-tokensurgeon 認得——見 docs）。
- Runtime：單張 H100 80GB 約 196 秒。

重現（在 repo 根目錄）：
```bash
uv run python -m tokenizer_transplant full \
  --config tokenizer_transplant/configs/olmo3_7b__deepseek_v4_flash.yaml
uv run python -m tokenizer_transplant selftest \
  --config tokenizer_transplant/configs/olmo3_7b__deepseek_v4_flash.yaml --which embed
```

---

## 驗證

**正確性**
- Shared-token rows 與原始 Olmo rows **bitwise 相等**（embed + head）。
- Anchor 切分精確且互斥（59,084 + 70,196 = 129,280）。
- 對全為 shared token 的 prompt，transplant 的 last hidden state 與原 Olmo **bit 完全相同**
  （cosine 1.0）——embeddings + body 未被動到。

**重建保真度**（held-out shared tokens，對真實 base row 的 cosine；random floor 0.024）：
embed **0.59**、lm_head **0.70**。與 canonical OMP 在 noise 範圍內相符。

**Zero-shot 生成（通順）：**
```
The capital of France is  → known for its rich history and culture...
def add(a, b):            → return a + b\ndef subtract(a, b): return a - b\ndef multiply...
The three primary colors are → red, yellow, and blue. These colors are called primary because...
Q: What is 2+2?\nA:       → 4
深度学习是一种            → 模式识别技术，它将输入数据映射到输出数据。在机器学习中...
```

---

## 限制

1. **新 token 的 output 未校準。** 在多語文字上的 teacher-forced next-token 統計：

   | target token | perplexity | top-1 | top-10 |
   |---|---|---|---|
   | shared | ~7 | ~50% | ~88% |
   | **new** | **~3400** | **~2%** | ~19% |

   模型*看得懂*由新 token 組成的文字，其 argmax 通常也合理（所以自由生成流暢），但無法對特定 gold
   token 給出 sharp 的機率。
2. **Bits-per-byte vs 原 Olmo**（與 tokenizer 無關，越低越好）：en 0.53→0.64、zh 0.70→1.63、
   ja 0.76→1.53、ru 0.32→1.04。多語在 output 端明顯變差。
3. **Greedy decoding 在新 token 密集處會 drift/loop**（distinct-token ratio ~0.45）。CPT 前請用
   `repetition_penalty≈1.3` 或 sampling 才有可用輸出。
4. **數字分組為左對齊三位制**（`\p{N}{1,3}`，`1000`→`100|0`、`1000000`→`100|000|0`）。注意這
   **與 Olmo 完全相同**——Olmo / DeepSeek / Kimi 三者數字切分逐字一致（已窮舉驗證，見
   `../../docs/tokenizer/comparison.md`），所以 transplant **不會改變數字處理**。真正的弱點是左對齊
   分組使同一數字在不同長度下 place-value 錯位（末位被孤立），對多位數運算不利，但這是三方共有、
   換 tokenizer 解決不了，只能靠訓練資料 / CoT 格式緩解。
5. 即使輸入是繁體中文也會輸出**簡體**（DeepSeek 訓練分布所致）。

---

## 建議的下一步：continued pretraining (CPT)

需要一段短的 low-LR CPT 來校準 70k 新 token rows 並適應數字分組。建議 recipe（參考 paper，~2B
tokens，LR ~4e-7）：
- 可先 freeze transformer body、只訓練 `embed_tokens` + `lm_head`，再 unfreeze；
- corpus 偏向 CJK / 多語 + math；
- CPT 前後各評一次 GSM8K 與多語 BPB 以量化恢復程度。

---

## 檔案（在產出模型目錄中）
- `model.safetensors` — transplanted 權重（vocab 129,280）
- `config.json` / `generation_config.json` — olmo3 config，`vocab_size=129280`，`bos/eos/pad=0/1/1`
- `tokenizer.json` / `tokenizer_config.json` — DeepSeek-V4-Flash tokenizer
