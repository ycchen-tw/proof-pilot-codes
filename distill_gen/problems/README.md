# problems — 去重後的證明題 prompt pool

off-policy distillation（DeepSeek-V4 teacher）用的 **unique 證明題 prompt 母體**。把兩個來源資料集的題目合併、跨資料集語意去重後，每題一列、保留 provenance，方便後續用 DeepSeek API 生成 teacher 資料。

## 來源

| 來源 | unique 題目 | 說明 |
|------|------------:|------|
| [`lm-provers/FineProofs-SFT`](https://huggingface.co/datasets/lm-provers/FineProofs-SFT)（`data` config） | 4,281 | olympiad / 各國競賽題（apache-2.0）；本機在 `datasets/FineProofs-SFT/` |
| [`Nemotron-Math-Proofs-v2`](https://huggingface.co/datasets/nvidia/Nemotron-Math-Proofs-v2) | 5,752 | AoPS 子集（CC BY 4.0）；本機在 `datasets/Nemotron-Math-Proofs-v2/`，82,737 traces / 5,752 題 |

## 去重方法

題目用不同 LaTeX 慣例、變數名、敘述寫同一道 olympiad 名題，純字串比對只抓到 9 對（全是 LaTeX 空格差異）。改用 embedding 語意去重：

- **模型**：`Qwen/Qwen3-Embedding-0.6B`（fp16，單張 4090）。
- **跨資料集（cross-source）**：FineProofs 題以 query+instruction 編碼、Nemotron 題以 document 編碼，每個 FineProofs 題取 Nemotron 最近鄰 cosine，**≥ 0.87 視為同題**。
  - threshold 用 9 個「字串完全相同（去 LaTeX 後）」的已知重複校準：這 9 對 cosine 落在 **0.891–0.945**，故同題的可靠切點 ≈ 0.88；0.87–0.90 區段人工抽查全是真重複。
  - 結果：**193 對**跨資料集重複。
- **同資料集內（intra-source）**：**只用字串正規化**（小寫、剝 LaTeX delimiter 與標點），抓 exact 比對漏掉的 LaTeX 空格變體 —— FP 2 對、NM 4 對。
  - ⚠️ **刻意不對 intra-source 用 embedding**：同源同編碼的 self-similarity 會膨脹，且 olympiad 不等式題結構高度雷同（如 `a²+b²+c²=3` vs `a+b+c=3` self-cosine 0.96 卻是不同題），0.87 self-sim 會大量誤殺。兩個來源各自已被原作者去重，intra 只補安全的字串變體。
- **分群**：上述 cross + intra 邊用 union-find 連通分量，每群留一個代表題（取最長的題目文字 = 敘述最完整），其餘成員的 provenance 全記在 `members`。

### 統計

```
raw 合併輸入 : 4,281 (FP) + 5,752 (NM) = 10,033
merged away  :   199  (193 cross-source embedding + 6 intra-source string)
unique 題目  : 9,834
  ├─ FineProofs only            : 4,086
  ├─ Nemotron-Math-Proofs-v2 only: 5,562
  └─ both (跨資料集同題)         :   186   ← 191 個 merged 群中 183 為 2-member、8 為 3-member
```

## Schema（`problems.parquet`，9,834 列，zstd）

| 欄位 | 型別 | 說明 |
|------|------|------|
| `problem` | string | 代表題目文字（群內最長的敘述） |
| `origin` | string | `FineProofs` / `Nemotron-Math-Proofs-v2` / `both` |
| `rep_source` | string | 代表文字取自哪個來源 |
| `category` | string | FP 的領域分類（Inequalities/Combinatorics…）；非 FP 為 null |
| `competition` | string | FP 的競賽出處（如 `Germany_TST-2020`）；非 FP 為 null |
| `source` | string | FP=`olympiads` 等 / NM=`AoPS` |
| `fp_gemini_grade` | int64 | FineProofs 的 `gemini-3-pro-grade`（0/1/6/7）；非 FP 為 null |
| `fp_qwen_reward` | double | FineProofs 的 `qwen3-4b-thinking-reward@128`；非 FP 為 null |
| `nm_uuid` | string | Nemotron 樣本 uuid（可 join 回原 traces）；非 NM 為 null |
| `nm_n_traces` | int64 | 該題在 Nemotron 的 trace 數（proof/verify/meta-verify 合計） |
| `n_members` | int64 | 該群合併了幾個原始題目（1 = 未合併） |
| `merge_max_cosine` | double | 群內最大邊 cosine（cross 為 embedding sim、intra 為 1.0）；未合併為 null |
| `members` | string (JSON) | 群內所有原始成員的 provenance + 原文，可回溯/稽核 |

## 回溯到原始資料

- **Nemotron**：用 `nm_uuid` 或 `problem` join 回 `datasets/Nemotron-Math-Proofs-v2/data/train.jsonl`（每題含 proof / verification / meta-verification traces，`nm_n_traces` 筆）。
- **FineProofs**：用 `problem` / `competition` join 回 `datasets/FineProofs-SFT/`（`all` config 含每題多份參考解 + grade、reward）。
- `origin=both` 的列，兩個來源的原文都在 `members` 裡。

## 重現

```bash
CUDA_VISIBLE_DEVICES=0 uv run python scripts/build_distill_prompts.py
```

腳本：embed（快取 `/tmp/*_e.npy`）→ cross/intra 邊 → union-find → 寫 parquet（含 read-back 驗證，防本機 bit-flip）。threshold 等參數在檔案頂部。
