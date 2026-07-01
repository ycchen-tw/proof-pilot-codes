# Copyright 2026 proof-pilot. Apache-2.0.
"""rollout dump —— 把**所有** student rollouts(prompt+response token ids)落盤成 dflash 原生 parquet。

為何要存：on-policy distillation 的 rollout token ids 原本全程只在記憶體（producer→buffer→HTTP→
trainer，用後即丟），磁碟上完全沒有（teacher hidden `.bin` 不含 token ids 且用完即 GC）。但這些 rollout
對 (a) 事後分析、(b) spec-decode draft（dflash）訓練很有價值。本模組把每條**成功生成**的 rollout 旁路寫成
parquet，**完全脫鉤** teacher scoring 成敗、buffer overflow/staleness、與 hidden 的 GC。

格式 = **dflash `train.py` 原生**（零轉換消費；dflash `data.py` 按欄位名取 `input_ids`/`loss_mask`，
多餘欄位忽略，見 dflash data.py:302/305）：
  input_ids : list<int32>  = traj.ids（prompt+response，已 truncate 到 max_traj_tokens）
  loss_mask : list<bool>   = [False]*prompt_len + [True]*gen_len（prompt 不算 loss、completion 算）
  # ---- 以下為分析欄位（dflash 忽略；給事後分析/dedup/staleness 研究）----
  wv         : int32       生成此條的 rollout weight_version
  prompt_len : int32
  seq        : int64       全域單調序號（本 process）
  meta       : string(JSON) problem_id/template 等（store_meta=True 才有）

落地策略（單一 writer = orchestrator 單 process、單 event loop）：
- `append()` 只 enqueue（event loop 內微秒級、非阻塞）；背景 coroutine 批次取出、`run_in_executor`
  在 thread 寫檔 → event loop 永不卡 disk I/O。append 只做 `put_nowait`+counter，單 event loop 內原子，
  64 個 produce atom 並發呼叫安全。
- **每次 flush = 一個完整獨立 parquet 檔**（tmp→atomic rename；footer 立即寫入）→ crash 只損失「未 flush
  的記憶體批次」（≤ rows_per_file 或 ≤ flush_interval_s），不用長壽命 ParquetWriter（避免 open writer
  在 crash 時整個 shard 報廢）。dflash glob `**/*.parquet` 整目錄 → 多個小檔即可。
- 啟動掃既有 `part-*.parquet` 接續編號（resume/重跑不覆蓋）。
"""
from __future__ import annotations

import asyncio
import glob
import json
import logging
import os
import re

log = logging.getLogger("opd_v2.rollout_store")

_STOP = object()       # writer 收尾 sentinel
_TICK = object()       # flush_interval 逾時 sentinel（觸發定期落盤）
_PART_RE = re.compile(r"part-(\d+)\.parquet$")


class RolloutDumpWriter:
    """把 rollout token ids 旁路寫成 dflash 原生 parquet（單 writer、非阻塞、per-flush 完整檔）。"""

    def __init__(self, dump_dir: str, *, rows_per_file: int = 1000,
                 flush_interval_s: float = 60.0, store_meta: bool = True,
                 compression: str = "zstd", provenance: dict | None = None):
        self.dir = dump_dir
        self.rows_per_file = max(1, int(rows_per_file))
        self.flush_interval_s = max(1.0, float(flush_interval_s))
        self.store_meta = bool(store_meta)
        self.compression = compression
        self.provenance = dict(provenance or {})
        os.makedirs(self.dir, exist_ok=True)
        # resume：接續既有最大 part 編號，不覆蓋
        self._file_idx = self._scan_next_idx()
        self._seq = 0
        # 統計（event loop 讀、writer thread 寫；皆為 int/float，stats 只是觀測，容忍鬆散）
        self.n_written = 0
        self.n_files = 0
        self.n_bytes = 0
        self.queue_high = 0
        self._q: asyncio.Queue | None = None
        self._task: asyncio.Task | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._schema = None   # 延後到寫檔 thread 內建（避免 import pyarrow 進 event loop import 期）

    def _scan_next_idx(self) -> int:
        mx = -1
        for p in glob.glob(os.path.join(self.dir, "part-*.parquet")):
            m = _PART_RE.search(os.path.basename(p))
            if m:
                mx = max(mx, int(m.group(1)))
        return mx + 1

    # ---- lifecycle（在 running event loop 內呼叫）----
    def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._q = asyncio.Queue()
        self._task = asyncio.create_task(self._run(), name="rollout_dump_writer")
        log.info("rollout dump -> %s (rows/file=%d, flush=%.0fs, meta=%s, next_part=%d)",
                 self.dir, self.rows_per_file, self.flush_interval_s, self.store_meta, self._file_idx)

    def append(self, ids: list[int], prompt_len: int, wv: int, meta: dict | None = None) -> None:
        """非阻塞 enqueue 一條 rollout。`ids` = prompt+response（已 truncate）。單 event loop 內安全。"""
        if self._q is None:
            return
        seq = self._seq
        self._seq += 1
        # 存 ids 參考（不複製）；meta 先轉成緊湊 JSON 字串（store_meta=False 則略過）
        meta_json = json.dumps(meta, ensure_ascii=False, separators=(",", ":")) if (self.store_meta and meta) else ""
        self._q.put_nowait((seq, int(wv), int(prompt_len), ids, meta_json))
        qs = self._q.qsize()
        if qs > self.queue_high:
            self.queue_high = qs
            if qs and qs % 5000 == 0:
                log.warning("rollout dump queue high-water=%d（writer 落後？）", qs)

    async def close(self) -> None:
        """收尾：停 writer、flush 殘留、寫 dataset_info.json。冪等。"""
        if self._task is None:
            return
        self._q.put_nowait(_STOP)
        try:
            await self._task
        except Exception:
            log.exception("rollout dump writer task error on close")
        self._task = None
        self._write_dataset_info()
        log.info("rollout dump closed: %d rollouts -> %d files (%.2f GB)",
                 self.n_written, self.n_files, self.n_bytes / 1e9)

    # ---- 背景 writer ----
    async def _run(self) -> None:
        batch: list = []
        last_flush = self._loop.time()
        # poll 間隔取 min(flush_interval, 5s)：即使 rollout 穩定湧入（queue 不閒置），也能每隔
        # flush_interval **以 wall-clock** 落盤（修「靠 queue 閒置才 _TICK」→ 穩定湧入時永不定期 flush 的 bug）。
        poll = min(self.flush_interval_s, 5.0)
        while True:
            try:
                item = await asyncio.wait_for(self._q.get(), timeout=poll)
            except asyncio.TimeoutError:
                item = _TICK
            if item is _STOP:
                break
            if item is not _TICK:
                batch.append(item)
            now = self._loop.time()
            # 滿批 → 立刻落盤；否則距上次 flush 已過 flush_interval 且有累積 → 定期落盤
            if batch and (len(batch) >= self.rows_per_file or now - last_flush >= self.flush_interval_s):
                await self._flush(batch)
                batch = []
                last_flush = now
        # 收尾：drain 佇列殘留後最後一次 flush
        while self._q is not None and not self._q.empty():
            it = self._q.get_nowait()
            if it not in (_STOP, _TICK):
                batch.append(it)
            if len(batch) >= self.rows_per_file:
                await self._flush(batch)
                batch = []
        if batch:
            await self._flush(batch)

    async def _flush(self, batch: list) -> None:
        if not batch:
            return
        try:
            await self._loop.run_in_executor(None, self._write_file, batch)
        except Exception:
            log.exception("rollout dump flush failed (%d rows dropped)", len(batch))

    def _write_file(self, batch: list) -> None:
        """在 executor thread 寫一個完整 parquet 檔（tmp→atomic rename）。"""
        import pyarrow as pa
        import pyarrow.parquet as pq
        if self._schema is None:
            fields = [("input_ids", pa.list_(pa.int32())), ("loss_mask", pa.list_(pa.bool_())),
                      ("wv", pa.int32()), ("prompt_len", pa.int32()), ("seq", pa.int64())]
            if self.store_meta:
                fields.append(("meta", pa.string()))
            self._schema = pa.schema(fields)

        input_ids, loss_mask, wv, plen, seq, meta = [], [], [], [], [], []
        for (s, w, pl, ids, mj) in batch:
            input_ids.append(ids)
            loss_mask.append([False] * pl + [True] * (len(ids) - pl))
            wv.append(w); plen.append(pl); seq.append(s); meta.append(mj)
        cols = {"input_ids": pa.array(input_ids, type=pa.list_(pa.int32())),
                "loss_mask": pa.array(loss_mask, type=pa.list_(pa.bool_())),
                "wv": pa.array(wv, type=pa.int32()),
                "prompt_len": pa.array(plen, type=pa.int32()),
                "seq": pa.array(seq, type=pa.int64())}
        if self.store_meta:
            cols["meta"] = pa.array(meta, type=pa.string())
        table = pa.table(cols, schema=self._schema)

        idx = self._file_idx
        self._file_idx += 1
        final = os.path.join(self.dir, f"part-{idx:08d}.parquet")
        tmp = final + ".tmp"
        pq.write_table(table, tmp, compression=self.compression)
        os.replace(tmp, final)            # atomic：dflash glob 永不撈到半寫檔
        self.n_written += len(batch)
        self.n_files += 1
        try:
            self.n_bytes += os.path.getsize(final)
        except OSError:
            pass

    def _write_dataset_info(self) -> None:
        info = {
            "format": "dflash-native parquet",
            "columns": {"input_ids": "list<int32>", "loss_mask": "list<bool>",
                        "wv": "int32", "prompt_len": "int32", "seq": "int64",
                        **({"meta": "string(JSON)"} if self.store_meta else {})},
            "n_rollouts": self.n_written,
            "n_files": self.n_files,
            "n_bytes": self.n_bytes,
            "source": "opd_v2 on-policy distillation rollouts",
            **self.provenance,
        }
        try:
            with open(os.path.join(self.dir, "dataset_info.json"), "w") as f:
                json.dump(info, f, indent=2, ensure_ascii=False)
        except Exception:
            log.exception("rollout dump dataset_info write failed")

    def stats(self) -> dict:
        return {"n_written": self.n_written, "n_files": self.n_files,
                "n_bytes": self.n_bytes,
                "queue": (self._q.qsize() if self._q is not None else 0),
                "queue_high": self.queue_high}
