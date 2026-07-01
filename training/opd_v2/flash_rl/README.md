# flash_rl —— OPD rollout 用 FP8 量化 + `update_weights_from_disk`

讓 OPD 的 student rollout server 能**以 FP8 量化部署**(省 VRAM、加速),同時**反覆用 `update_weights_from_disk` 從 disk 換上新的 bf16 student checkpoint**(sglang 自動重新量化成 FP8)。

- 目標範圍:**sglang 0.5.12.post1、7B `stage1-v2-7b`(olmo3_sink)**;原始驗證 TP=1 bf16-KV,**TP=4 + fp8-KV + SWA-ratio long-context 配置已另測通過**(見 §5.3)。
- 結論:stock sglang 這條路是壞的;本目錄提供一個 **3 處修改的 `loader.py` bind-mount patch**,實測 10/10 反覆 reload 穩定、bit-exact、無洩漏。

---

## 1. 問題:為什麼 stock 不行

OPD rollout 目前是 **bf16**(`training/opd/examples/run_rollout_service.sh`,無 `--quantization`),`update_weights_from_disk` 正常。一旦想加 FP8:

| 配置 | 結果 |
|---|---|
| `--quantization fp8`(線上量化 bf16) | 服務 OK(權重 15G→8.1G),但 **第 1 次 `update_weights_from_disk` 就 crash** |
| 預量化 compressed-tensors fp8 + 從 fp8 disk 更新 | **同樣 crash** |

**機制**:`--quantization fp8` 啟動時 `process_weights_after_loading` 會把每層 weight **量化成 fp8 並轉置**(`[out,in]`→`[in,out]`)且丟掉量化用的 `weight_loader`。`update_weights_from_disk` 再呼叫 `model.load_weights()` 時對這些 param 退回 `default_weight_loader`,把 bf16 `[out,in]` 硬塞進轉置後的 fp8 `[in,out]` → shape assert 失敗 → scheduler SIGQUIT。

## 2. 正解是 flash_rl,但它的 from_disk 路徑壞掉

sglang 內建 **`--load-format flash_rl`(`QuantizedRLModelLoader`)** 就是為「serve fp8 + reload 重新量化」設計的(verl/slime RLHF 用)。但它只在 **`update_weights_from_tensor`**(co-located、GPU tensor)被驗證過;**`update_weights_from_disk`** 這條在 0.5.12.post1 / 0.5.13 對自訂 Olmo3Sink 會踩一串 bug。逐一追出來並修掉:

| # | bug | 症狀 | 修法 |
|---|---|---|---|
| 1 | `load_weights_and_postprocess` 在 reload 時**重新包一層 proxy**,每層捕捉上一層 proxy → 第 N 次 reload 遞迴 N 層,每層 `list(weights)`+重量化整個模型 | 越跑越慢、**第幾輪後 OOM**(看似洩漏) | reload 時直接呼叫既有 proxy 並 `return`,不 re-wrap(順帶跳過會 double-quant 的尾段 postprocess) |
| 2 | `SKIP_QUANTIZATION_PARAMS` 是 Qwen2 形狀,**漏了 Olmo2 的 `q_norm`/`k_norm`/`post_feedforward_layernorm`**,去量化 1-D norm | `RuntimeError: Tensor match failed`(2-D quant kernel 吃到 1-D) | 量化分支加 `weight.dim() >= 2`,1-D 一律走 keep 原樣載入 |
| 3 | from_disk 吐 **CPU** tensor,直接丟給只支援 CUDA 的 `per_token_group_quant_8bit` | `NotImplementedError: ... 'CPU' backend` | 量化前 `weight.to(cuda)` |

> 註:遞迴(bug 1)才是「多輪後才壞」的真因——不是真洩漏。每次 reload 起始 GPU avail 是穩定的;修掉遞迴後暫態固定、不隨輪數成長。

3 處修改的完整 diff 見 `patches/flash_rl.patch.diff`(46 行),邏輯上只動 `QuantizedRLModelLoader` 兩個方法。

## 3. 實測驗證(sglang 0.5.12.post1、H200、TP=1、stage1-v2-7b)

打完 patch 後(`tests/` 腳本):

- **10/10 反覆 reload 成功**,每次 ~3.2s;**GPU avail 全程死穩 19.8GB(0 洩漏)**,即使 `mem-fraction-static 0.85`(僅 ~20GB headroom)。
- **`update_weights_from_disk` 到 opd ＝ 直接 fresh-load opd,完全 bit-exact**(`tests/hashgen.py`,4 種 prompt 輸出雜湊一字不差)。這是**最強的保真證明**:reload 與全新載入產生「位元相同」的模型 → **所有參數**(含 `embed_tokens`/`lm_head`/各 `layernorm`/`q_norm`/`k_norm`/`sinks`)都正確更新,**無任何 stale**。
- **deploy → opd → deploy round-trip bit-exact**(輸出雜湊完全相同)→ 重量化確定且與啟動路徑一致。
- **opd checkpoint 權重確實生效**(輸出改變),且更新後**生成正常**:多步算式、proof、512-token 長解碼、chat-completions(`80 km/h`、`12`)皆正確。
- 0 個 hard error(CPU-backend / Tensor-match / contiguity / OOM 全消失)。
- 已過獨立 agent code review:對本範圍**無 must-fix**;審查疑慮「skip-list 的 norm 不更新」經上述 fresh-vs-reload 實測**反證**(見 §5.1)。

## 4. 用法

### 啟動 FP8 rollout server
```bash
CUDA_VISIBLE_DEVICES=4 PORT=8200 ./run_rollout_fp8.sh --port 8200
# = run_rollout_service.sh + --quantization fp8 --load-format flash_rl
#   + bind-mount patches/loader.py。權重 ~8.1G(bf16 ~15G）。

# long-context 配置（TP4 + fp8 KV + SWA mem，見 §5.3）：
CUDA_VISIBLE_DEVICES=4,5,6,7 KV_CACHE_DTYPE=fp8_e4m3 SWA_RATIO=0.5 CONTEXT_LEN=65536 \
  ./run_rollout_fp8.sh --port 8200 --tp 4
```
之後照舊打 `/update_weights_from_disk`(OPD 的 `RolloutClient.update_weights_from_disk(path)` 不用改),sglang 會自動把新 bf16 checkpoint 重新量化成 fp8。

### 換 sglang 版本時重生 patched loader
`patches/loader.py` 是從 0.5.12.post1 image 抽出來改的(版本相依)。換版時用 `apply_patch.py` 以 anchor 字串重新套(idempotent；anchor 對不上會明確報錯):
```bash
apptainer exec <img.sif> cat /sgl-workspace/sglang/python/sglang/srt/model_loader/loader.py > stock.py
python apply_patch.py stock.py patches/loader.py
# 或啟動時自動重生：REGEN_LOADER=1 ./run_rollout_fp8.sh
```

### 重跑驗證
```bash
python tests/cycle.py    <port> <ckptA> <ckptB> 10      # 10 輪 reload 壓力 + bit-exact round-trip
python tests/validate.py <port>                          # 多 prompt/長解碼/round-trip/degeneration
python tests/probe.py    generate <port>                 # 單發生成 / update
# 保真比對：兩台 server（一台 reload 到 X、一台 fresh-load X）輸出 hash 應全 MATCH
python tests/hashgen.py  <portA> update <ckptX>          # server A: 先 reload 到 X 再生成
python tests/hashgen.py  <portB>                         # server B: fresh-load X 直接生成
```

## 5. 範圍與注意

### 5.1 weight fidelity:所有參數都會更新(已實測,非只更新量化 linear)
`_get_updated_params` / copy-back 迴圈裡的 `SKIP_QUANTIZATION_PARAMS` **只控制「copy-back fixup」**(替量化後被轉置的 fp8 linear 還原原始 storage),**不影響真正的權重載入**——真正載入由 `rebinding_and_load_weights` 內 `first_time_load_weights(...)`(＝真實 `model.load_weights`,loader.py:1203)完成,它把整條 bf16 weight stream(含 embed/lm_head/各 norm)寫進對應 param。因此 norm/embed/lm_head **不會 stale**。已用 fresh-load-opd vs reload-to-opd **bit-exact** 實測確認(`tests/hashgen.py`,4/4 MATCH)。

### 5.2 其他
- **TP=1 與 TP=4 已驗證(7B);32B 未測**。Edit #3 的 device-move per-rank 正確;**TP>1 的 scale sharding(`_apply_scale_update`)原為未驗點,2026-06-17 long-context 實測 TP4 通過(§5.3)**。32B 的 reload 暫態更大,要用需留更多 mem headroom 另測。
- **`load_format` 必須是 flash_rl**:early-return 只在 reload 解析成 `load_format=flash_rl` 時生效(client 顯式帶、或省略而 server 預設 `--load-format flash_rl`)。OPD client/orchestrator 呼叫 `update_weights_from_disk` 時**不要傳別的 `load_format`**(如 `auto`),否則會走 `DefaultModelLoader`、繞過整個 override 而炸。`RolloutClient.update_weights_from_disk` 目前不送 `load_format`,正確。
- **僅適用 dense per-channel fp8**:本 patch 對 H200/Blackwell 走 cutlass per-channel fp8 正確;若改用 block-fp8(`weight_block_size`)或舊卡的 per-tensor 路徑,scale 粒度/layout 會與啟動量化不符,需重驗。
- **版本相依**:`patches/loader.py` 對應 0.5.12.post1;0.5.13 同段程式碼相同、邏輯適用,但請 pin image 或用 `apply_patch.py` 重生。
- **記憶體**:reload 需暫態 scratch;fp8 比 bf16 省 ~6G 權重,但 reload 峰值會用掉部分 KV headroom。7B/TP1 在 `mem-fraction 0.85` OK。
- **精度**:fp8 rollout 對 distillation 的 train/deploy mismatch 風險未在此評估(本目錄只解「能不能跑通」)。若在意,rollout 維持 bf16 仍是最穩選項;fp8 的 VRAM/速度效益對**凍結部署**(`deploy/quant`)最划算。
- 這是 bind-mount monkeypatch,**不改 image**;風格同 `deploy/target/olmo2_sink.py`、`deploy/quant/patches/compressed_tensors.py`。
- 已就此 3 處修改做 code review(見 git 紀錄外的審查結論):對本範圍正確、無 must-fix。

### 5.3 long-context 配置實測(2026-06-17,H200×4,TP4)
為因應長 CoT,rollout 可同時開三個 long-context 旗標,實測**都能啟用且 weight update 正常**:

| 旗標 | env | 結果 |
|---|---|---|
| fp8 KV cache | `KV_CACHE_DTYPE=fp8_e4m3` | ✓ KV pool 撐到 ~1.88M tokens。**用 e4m3**:FA3 支援(保住 fa3 backend)、mantissa 3-bit 較不失真;`fp8_e5m2` 會逼 attn backend 退 **triton**(較慢)。 |
| TP4 | `--tp 4` | ✓ 32 heads÷4=8/rank;TP8(÷8=4/rank)亦整除可行。對 7B 而言 TP 不是為了塞模型,是把 **KV cache 切 N 份換 long-context 容量**(拿 decode TP 通訊換 KV headroom)。 |
| sliding-window mem | `SWA_RATIO=0.5` → `--swa-full-tokens-ratio` | ✓ hybrid SWA pool 啟用(olmo3 = 24 SWA : 8 full,window 4096);window 遠小於 ctx 時可再調低省更多。 |

**weight update(production 路徑:`pause(in_place)` + `update_weights_from_disk(flush_cache=False)` + `continue`)**:
- 6/6 reload `success=True`,~3s/次,無變慢無漏;**reload→reload bit-exact**(deploy/opd 各自每輪同 hash);引擎確定性;6 輪 + 11.7k-tok long-context 解碼後 server 仍活。
- **補上 §5.2 原標記的 TP>1 未驗點**:TP4 的 scale sharding 通了。
- 注意:**initial-boot 量化 ≠ reload-path 量化**(TP4 下,validate.py 的 bit-exact「FAIL」來源),但訓練只走 reload 路徑、reload→reload bit-exact,故**無害**。
- 取捨:fp8 KV 是有損 attention → rollout 採樣分布與 student 真實分布有微差(on-policy 的小破口),e4m3 比 e5m2 準。

### 5.4 KV pool 實測 + conc 定案(2026-06-20,本機 TP4,model=opd-v2-lc128k-softdistill-v2test-deploy)
config:`KV_CACHE_DTYPE=fp8_e4m3 SWA_RATIO=0.2 CONTEXT_LEN=131072 MEMFRAC=0.85 --tp 4`。startup log 確認 SWA+fp8-KV 都生效(`Hybrid swa model: Olmo3SinkForCausalLM` + `Using KV cache dtype: torch.float8_e4m3fn` + `SWAKVPool`):

| pool | tokens | KV 大小 | 對應層 |
|---|---|---|---|
| **full** | **4,711,012** | K+V 各 35.94GB | 8 full-attention 層 |
| swa | 942,202 | K+V 各 21.57GB | 24 sliding-window 層(window 4096) |
| 合計 | — | **115.0GB**(avail 餘 20.6GB) | — |

- **長序列綁 full pool**(full-attn 層存每條並發序列的所有 position):`conc × avg_len ≤ 4.71M`。swa pool 每條只佔 ≤window 4096,942k/4096≈230 條才綁定 → 長 CoT 下非瓶頸。
- conc 表(每 replica):avg 32k→144、64k→72、90k→52、128k(撞滿)→36。
- **定案 `ROLLOUT_MAXRUN=64`/replica**:64×64k=4.1M<4.71M 安全;OPD rollout 平均遠低於 128k → 餘裕足。全撞 128k 才會超(→偶發 preempt,`--disable-radix-cache` 下 preempt=重算,看 `rollout/length_rate`)。
- ⚠️ **conc>10 必須配 `--cuda-graph-max-bs`**:測時 cuda graph 只 capture 到 bs=10(=預設 MAXRUN),bs>10 退 eager。`run_rollout_fp8.sh` 已讓 `CUDA_GRAPH_MAX_BS` 預設=`MAXRUN`(設 MAXRUN=64 即自動 capture 到 64)。
- swa_ratio:0.2 已調好(swa 942k 撐 ~230 並發 window,遠超需求;full pool 最大化)。conc 若遠低於 230 可試 r=0.15 再多 ~9% full pool,邊際。
- **正式 run**:`examples/run_agentic_mn.sbatch` 已把這組(ctx131072 / e4m3 / swa0.2 / MAXRUN64 / teacher memfrac0.5)烤進去。

## 6. 檔案

```
flash_rl/
├── README.md                     # 本文件
├── run_rollout_fp8.sh            # 啟動 fp8 + flash_rl rollout server（含 bind-mount）
├── apply_patch.py                # 從任意 image 的 loader.py 重生 3-edit patch（idempotent）
├── patches/
│   ├── loader.py                 # patched QuantizedRLModelLoader（bind-mount 目標，0.5.12.post1）
│   └── flash_rl.patch.diff       # 3 處修改的 unified diff（human-readable）
└── tests/
    ├── probe.py                  # 單發 generate / update_weights_from_disk
    ├── cycle.py                  # N 輪 reload 壓力 + bit-exact round-trip 檢查
    ├── validate.py               # 多 prompt + 長解碼 + degeneration + round-trip 驗證
    └── hashgen.py                # 逐 prompt 輸出 hash（fresh-load vs reload 保真比對用）
```
