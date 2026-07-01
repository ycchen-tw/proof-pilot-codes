# Eval harness

ProofBench 評測三段式 pipeline，全用 OpenAI-compatible `/v1/chat/completions`（本機 SGLang 與 DeepSeek API 同一套 client）。從**主 proof-pilot venv** 跑（需 `requests`/`httpx`/`pandas`/`numpy`/`sympy`）。

```
run_eval.py        題目 -> 模型 -> runs/<run_id>/responses.jsonl  (k 個候選/題；支援 notool / pytool)
grader.py          responses + 參考解/標準 -> grades.jsonl        (0/1/6/7；--limit 可只評前 N 題)
score.py           grades -> summary.json + 表格                  (mean/almost+/correct/best-of-k，分 subset/level/category)
client.py          同步 HTTP client（重試、health、reasoning 旋鈕、chat_raw 給 tool loop）
async_client.py    async HTTP client（httpx，pooled，~1000 併發用）
tool_loop.py       native function-calling 證明迴圈（prover 用，pytool；存無損 messages，cache-friendly tool budget）
grade_proofs.py    用校準過的 flash high_notool grader 評分 run 的候選（async；--passes、grade-all/intersect）
make_review_html.py 把 run 打包成自包含 HTML 檢視器（prompt/逐輪reasoning/tool code/output/proof，離線可開）
calibrate_grader.py grader 校準（async；gradingbench × 多 config，算 accuracy/MAE/Pearson）
tools/             python tool sandbox：python_tool.py(vendored)、safe_session.py(限額版)、_exec_driver.py
```

### ⚠️ 資料持久化原則（打 API 必守）

**每次 LLM/API 呼叫，一律把完整原始資料逐筆存到磁碟，不可只存摘要或事後丟棄。** API 呼叫貴、且 thinking 模式有隨機性＝不可重現；沒存好，事後要稽核（tool 成功率、grader rationale、踩雷案例）就只能重跑，浪費錢又遺失資料。每筆至少存：

- **完整 messages**：system/user/assistant、**tool_calls 的 code、tool 回傳的 output**（多輪都要）。
- **模型輸出全文** `content` ＋ **`reasoning_content`（思考）**。
- `finish_reason`、`usage`（prompt/completion/**reasoning** tokens）、`latency`、seed 與所有 sampling/reasoning 參數。
- 逐筆 **append + resume**（host 不穩，見 memory `host-memory-instability`）。

> 教訓：`calibrate_grader.py` 早期只存 `n_tool_calls` 計數、丟掉 transcript，導致無法回頭查 tool 呼叫是否成功——只能重跑。**寧可多存，不要事後後悔。** 摘要（分數/指標）是衍生品，原始 messages 才是真資料。

### reasoning / tool 旋鈕

- `--reasoning {default,no_think,high,max}`（client `_apply_reasoning`）：對應 DeepSeek thinking/reasoning_effort；`high`/`max` 會自動丟掉 temperature/top_p（thinking 模式忽略）。見 memory `deepseek-v4-api`。
- `--condition pytool`：給模型 native `execute_python` 工具（numpy/sympy sandbox），多輪 tool loop 直到產出最終證明。`--max-turns` 控回合上限。
  - **cache-friendly tool budget（`--max-tool-calls`，預設 24）**：每題工具呼叫上限**寫進 tool description**（穩定 cached prefix）＋ 每個 tool result 尾巴 `[k remaining]` 倒數（suffix）；用完餵 `BUDGET_SPENT_MSG`，**tools array 全程不變**（不 invalidate prefix cache）。`--max-turns`（預設 32）只當硬 backstop。**不 detach tools**——改 tools array 會讓最長那次呼叫 prefix cache miss。實測（k=4×60）：tool-lock 空白 0、`n_tool_calls` 從不超過上限。取代舊的 max_turns-64 + `FINAL_NUDGE` detach 方案。
  - 歷史教訓：`--max-turns` 太小（10）會讓 flash high 把回合用光、空證明（usable 假掉到 19/60）；budget 方案下不需要大 max_turns。
  - **存檔（無損）**：`candidates_raw.jsonl` 每筆含 `messages`（完整對話：user→assistant 含 `content`+**每輪 `reasoning_content`**+原始 `tool_calls`→tool 含 `tool_call_id`/`name`/output+倒數→final）＋ `turns`（逐輪 finish/tokens）。**notool 同 schema**（messages=user+assistant含reasoning_content）。`run_meta` 另存 `tools`（確切 schema）+ `repro`（git/sha）。
  - **tool-call 回合的 `reasoning_content` 會回灌 API**（DeepSeek thinking_mode 規定：tool-call 回合的思考必須帶回後續輪，否則 cold-cache-miss 會 400）；**免費**（context cache 去重、prompt_tokens 不變，usage 實測 A=B）。非 tool-call 回合不需回灌。詳見 memory `deepseek-v4-api`。

### Python tool sandbox（安全措施）

**高併發 tool use 必須用 `tools/safe_session.py`（`SafePythonSession`）**，不要用裸 `python_tool.py` 的 `SecureLightweightPythonSession`：後者**無 RAM 限制、且非主執行緒不觸發 timeout**（曾在 conc 400 下與一次 host/terminal crash 同時發生）。`SafePythonSession` 把每次 exec 丟進子進程，有 **RLIMIT_AS 記憶體上限 + wall-clock SIGKILL + 子進程內 SIGALRM**（三重保護），介面與行為對 LLM 完全相同（`execute(code)->stdout`、變數跨呼叫保留）。`tool_loop.py` 與 `calibrate_grader.py` 都已改用它。
（`tools/python_tool.py` 由 `agent-factory-3/mcp_tools/python_tool/secure_python_session.py` vendored，供 import 限制；安全限額由 `safe_session.py` 外加。）

**sandbox 內可用 math lib**（實測，跑在主 venv）：`numpy scipy sympy mpmath networkx gmpy2 galois` + 全 stdlib（math/cmath/fractions/decimal/itertools/…）。被擋：`os/sys/subprocess/socket/pathlib/pickle/importlib`、`pandas/matplotlib`、builtin `open/eval/exec/getattr/setattr`。`gmpy2`(大數/數論)/`galois`(有限體) 由 `uv add` 裝（記在 pyproject）。tool description 已列出這些 lib 給模型。

### 長 job / 高併發守則

host 重載下會 byte-flip（memory `host-memory-instability`）。長跑請：(1) `setsid` detached（terminal 重啟不會帶走 job）、(2) 保守併發（pytool 尤其，子進程 sandbox 有記憶體成本）、(3) 逐筆 append + resume（`run_eval.py`/`calibrate_grader.py` 皆支援，靠輸出檔的 key 去重）。

## 1. 起 SGLang server（本機 OLMo / 訓練後模型）

獨立 venv 在 `../serving/.venv`（sglang 0.5.9 / torch 2.9.1+cu128，**與主訓練 venv 隔離**，避免動到 torch 2.12+cu126）。需要 `ninja`（已裝在該 venv）。

```bash
cd ../serving
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 CUDA_VISIBLE_DEVICES=0 \
  nohup .venv/bin/python -m sglang.launch_server \
    --model-path ${OLMO3_7B:-/models/Olmo-3-7B-Think} \
    --host 127.0.0.1 --port 30000 --tp 1 \
    --mem-fraction-static 0.85 --context-length 32768 --trust-remote-code \
    > logs/server.log 2>&1 &
# ready: curl -s http://127.0.0.1:30000/health
```

關閉（殺整棵樹，否則 scheduler 子進程仍佔卡，見 docs/tokenizer/deploy.md）：
```bash
pkill -9 -f sglang.launch_server
```

## 2. 跑評測

```bash
PY=python
cd harness

# 生成
$PY run_eval.py --data ../data/subset_dev.csv \
  --base-url http://127.0.0.1:30000/v1 --served-model default \
  --model-name olmo3-7b-think --condition notool \
  --k 1 --temperature 0.7 --max-tokens 32768

# 評分（DeepSeek key 到手後）
$PY grader.py --run-id olmo3-7b-think__notool --data ../data/subset_dev.csv \
  --grader deepseek --base-url https://api.deepseek.com/v1 \
  --served-model <pro-model-id> --api-key-env DEEPSEEK_API_KEY
#   key 還沒來 -> --grader stub（null 分數，只驗 pipeline）

# 聚合
$PY score.py --run-id olmo3-7b-think__notool
```

DeepSeek teacher 評測：`run_eval.py` 改 `--base-url https://api.deepseek.com/v1 --served-model <id> --api-key-env DEEPSEEK_API_KEY`，不需起本機 server。

pytool 條件（給模型 python 工具）：`run_eval.py --condition pytool --reasoning high --max-tokens 131072 --max-tool-calls 24 --max-turns 32`（budget 24 寫進 tool description；max_turns 只當 backstop）。

## 3. Grader 校準（calibrate_grader.py）

驗 grader 準度（vs gradingbench 人工分數），是信任分數的前提。async、高併發、resume。

```bash
$PY calibrate_grader.py --data ../data/gradingbench.csv --n 200 \
  --base-url https://api.deepseek.com/v1 --served-model deepseek-v4-flash \
  --api-key-env DEEPSEEK_API_KEY --concurrency 60 \
  --configs high_notool,high_pytool,max_notool,max_pytool \
  --max-tokens 65536 --max-turns 30 --run-id grader_calibration
```

輸出 `runs/<run_id>/grades_all.jsonl` + `summary.json`（每 config 的 coverage/accuracy/MAE%/Pearson/token）。校準結論見 `../results/grader_calibration.md`（**排名用 flash high_notool；逐題 verifier 才考慮 pro max_pytool**）。

## 已知事項（smoke 2026-06-01）

- **`--max-tokens` 要夠大**：Olmo-3-7B-Think 推理很長，8192 下 8 題中 7 題被截斷（`finish=length`）。正式評測用 **32768**（context-length 已設 32768）。truncated = 未完成證明，grader 多半判 0/1。
- Think 模型把 reasoning 直接寫在 content（無獨立 reasoning channel，`reasoning_tokens=0`）；grader 看到完整含思考的文字。若要只評最終證明，需在 grader 前抽取（目前整段送評）。
- subset_dev 8 題偏 Algebra（分層抽樣湊難度的副作用），smoke 夠用；正式跑全 60 題。

## DeepSeek（2026-06-03）

- model id：`deepseek-v4-flash` / `deepseek-v4-pro`，base_url `https://api.deepseek.com/v1`。`run_eval.py` 不改、指過去即可（預設 = thinking on + effort high）。
- **`--max-tokens` 是 reasoning+output 合併預算**：flash high 在難題會把預算全花在思考、最終 `content` 留空。32768 → 36/60 空證明；正式跑 DeepSeek thinking 用 **131072**。截斷（finish=length）多半 content 為空＝無證明，不只是「截短」。
- thinking 模式**忽略 temperature/top_p**（含 grader 的 `--temperature 0`）；no_think（`thinking:{type:disabled}`）才吃取樣參數。3 條件 no_think/high/max 對應見 `plan.md` §現況、memory `deepseek-v4-api`。
- flash high 約 ~3% reasoning runaway（>131k 無結論）；重骰可救多數，殘餘記 incomplete=0。
- flash high baseline 全 60 題：`runs/dsv4-flash__high_131k/`（`gen_summary.json`）。
- flash high **pytool** 全 60 題：`runs/dsv4-flash__high_pytool/`（max_turns 64、無損 messages）。usable 55/60；finish stop 55/tool_calls 5（5 空白＝tool-locked 撞 64）。
- **notool vs pytool 覆蓋**：交集 53、聯集 60（全覆蓋）、兩邊都空 0。失敗模式互補（notool=reasoning-runaway、pytool=tool-lock）。詳見 `plan.md` §現況（2026-06-04）。
