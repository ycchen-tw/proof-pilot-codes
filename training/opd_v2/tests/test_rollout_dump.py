# Copyright 2026 proof-pilot. Apache-2.0.
"""rollout dump 測試（純 CPU、無 GPU、秒級）。

驗：
1. append→close 落成 parquet，row 數/欄位/型別正確、loss_mask = [F]*plen+[T]*gen、input_ids==ids。
2. **dflash 零轉換消費**：照 dflash data.py 的 load 邏輯（glob **/*.parquet → datasets.load_dataset）
   讀回，input_ids/loss_mask 取得出、可重建 next-token target（loss_mask 只蓋 completion）。
3. **resume 不覆蓋**：同目錄第二個 writer 接續 part 編號，總 row = 兩次相加。
4. flush_interval 定期落盤（不足一批也會寫）。
5. enabled=False / dump=None：produce 路徑不炸（append no-op）。

跑法：PYTHONPATH=src .venv/bin/python tests/test_rollout_dump.py
"""
from __future__ import annotations

import asyncio
import glob
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from opd_v2.rollout_store import RolloutDumpWriter


def _mk_rollouts(n, base=0):
    """造 n 條假 rollout：(ids, prompt_len, wv, meta)。長度/plen 各異以驗 loss_mask。"""
    out = []
    for i in range(n):
        k = base + i
        plen = 3 + (k % 5)
        glen = 2 + (k % 7)
        ids = list(range(100 + k, 100 + k + plen + glen))   # 任意但可驗證的 token ids
        out.append((ids, plen, 10 + (k % 3), {"problem_id": f"p{k}", "template": "t"}))
    return out


def _read_all_parquet(d):
    import pyarrow.parquet as pq
    files = sorted(glob.glob(os.path.join(d, "part-*.parquet")))
    assert files, f"no parquet files in {d}"
    tabs = [pq.read_table(f) for f in files]
    import pyarrow as pa
    return pa.concat_tables(tabs), files


async def _run_writer(d, rollouts, **kw):
    w = RolloutDumpWriter(d, **kw)
    w.start()
    for (ids, plen, wv, meta) in rollouts:
        w.append(ids, plen, wv, meta)
    await w.close()
    return w


def test_basic_and_schema():
    with tempfile.TemporaryDirectory() as d:
        rollouts = _mk_rollouts(25)
        w = asyncio.run(_run_writer(d, rollouts, rows_per_file=10, flush_interval_s=3600))
        assert w.n_written == 25, w.n_written
        # 25 條 / 10 per file → 3 檔（10+10+5）
        tab, files = _read_all_parquet(d)
        assert len(files) == 3, files
        assert tab.num_rows == 25
        names = set(tab.column_names)
        assert {"input_ids", "loss_mask", "wv", "prompt_len", "seq", "meta"} <= names, names
        import pyarrow as pa
        assert tab.schema.field("input_ids").type == pa.list_(pa.int32())
        assert tab.schema.field("loss_mask").type == pa.list_(pa.bool_())
        # 逐筆驗（seq 排序後對回原 rollout）
        rows = tab.to_pylist()
        rows.sort(key=lambda r: r["seq"])
        for r, (ids, plen, wv, meta) in zip(rows, rollouts):
            assert r["input_ids"] == ids
            assert r["prompt_len"] == plen
            assert r["wv"] == wv
            assert r["loss_mask"] == [False] * plen + [True] * (len(ids) - plen)
            assert json.loads(r["meta"])["problem_id"] == meta["problem_id"]
        # dataset_info.json
        info = json.load(open(os.path.join(d, "dataset_info.json")))
        assert info["n_rollouts"] == 25 and info["n_files"] == 3
        print(f"[basic] OK: {w.n_written} rows, {len(files)} files, schema dflash-native + analysis cols")


def test_dflash_load_path():
    """完全照 dflash data.py:load_dataset 的邏輯讀，證明零轉換可消費。"""
    from datasets import load_dataset as hf_load
    with tempfile.TemporaryDirectory() as d:
        rollouts = _mk_rollouts(13)
        asyncio.run(_run_writer(d, rollouts, rows_per_file=5, flush_interval_s=3600))
        # dflash data.py: glob('**/*.parquet') → load_dataset('parquet', data_files=files)['train']
        files = sorted(glob.glob(os.path.join(d, "**", "*.parquet"), recursive=True))
        ds = hf_load("parquet", data_files=files)["train"]
        assert len(ds) == 13, len(ds)
        assert "input_ids" in ds.column_names and "loss_mask" in ds.column_names
        # 重建 dflash 的 next-token 監督（只在 loss_mask=True 的位置算）— 證明語義可用
        s = ds[0]
        ii, lm = s["input_ids"], s["loss_mask"]
        assert len(ii) == len(lm)
        n_train = sum(1 for x in lm if x)
        assert n_train == len(ii) - s["prompt_len"]   # 只有 completion 段被算 loss
        print(f"[dflash] OK: load_dataset 讀回 {len(ds)} 筆，input_ids/loss_mask 可消費，loss 蓋 completion {n_train} tok")


def test_resume_no_overwrite():
    with tempfile.TemporaryDirectory() as d:
        asyncio.run(_run_writer(d, _mk_rollouts(8, base=0), rows_per_file=5, flush_interval_s=3600))
        files1 = sorted(glob.glob(os.path.join(d, "part-*.parquet")))
        # 第二個 writer 同目錄：應接續編號、不覆蓋
        asyncio.run(_run_writer(d, _mk_rollouts(6, base=100), rows_per_file=5, flush_interval_s=3600))
        files2 = sorted(glob.glob(os.path.join(d, "part-*.parquet")))
        assert len(files2) > len(files1), (files1, files2)
        assert set(files1) <= set(files2), "舊檔被覆蓋了"
        tab, _ = _read_all_parquet(d)
        assert tab.num_rows == 14, tab.num_rows   # 8 + 6
        print(f"[resume] OK: {len(files1)}→{len(files2)} files, 不覆蓋, 共 {tab.num_rows} rows")


def test_time_flush():
    """flush_interval 到期應落盤（即使不足一批）。"""
    async def go(d):
        w = RolloutDumpWriter(d, rows_per_file=10000, flush_interval_s=1.0)
        w.start()
        for (ids, plen, wv, meta) in _mk_rollouts(3):
            w.append(ids, plen, wv, meta)
        await asyncio.sleep(2.5)            # 等至少一次 flush tick
        n_mid = w.n_files
        await w.close()
        return n_mid, w.n_written
    with tempfile.TemporaryDirectory() as d:
        n_mid, n_written = asyncio.run(go(d))
        assert n_mid >= 1, f"time-flush 沒觸發（n_files={n_mid}）"
        assert n_written == 3
        print(f"[time_flush] OK: flush_interval 觸發落盤（close 前已 {n_mid} 檔）")


def test_steady_load_flush():
    """穩定湧入（queue 從不閒置）下仍須每 flush_interval 定期落盤（回歸：舊版只靠 queue 閒置 _TICK，
    穩定湧入時永不定期 flush、只能等 rows_per_file）。"""
    async def go(d):
        w = RolloutDumpWriter(d, rows_per_file=100000, flush_interval_s=1.0)  # row cap 高到不會觸發
        w.start()
        # 每 0.2s append 一條，持續 ~3s（間隔 < flush_interval=1s → queue 從不閒置 1s）
        for _ in range(15):
            w.append(list(range(10, 18)), 3, 0, {})
            await asyncio.sleep(0.2)
        n_mid = w.n_files          # close 前就該有檔（定期 flush 生效）
        await w.close()
        return n_mid, w.n_written
    with tempfile.TemporaryDirectory() as d:
        n_mid, n_written = asyncio.run(go(d))
        assert n_mid >= 2, f"穩定湧入下沒定期 flush（close 前 n_files={n_mid}）= 回歸 bug"
        assert n_written == 15
        print(f"[steady_load] OK: 穩定湧入下定期 flush 生效（close 前已 {n_mid} 檔）")


def test_disabled_noop():
    """dump=None 時 produce 的 append 呼叫不該炸（這裡直接驗 writer 未 start 的 append 安全）。"""
    w = RolloutDumpWriter(tempfile.mkdtemp(), rows_per_file=10)
    w.append([1, 2, 3], 1, 0, {})          # 未 start → no-op 不炸
    print("[disabled] OK: 未 start 的 append no-op 安全")


if __name__ == "__main__":
    test_basic_and_schema()
    test_dflash_load_path()
    test_resume_no_overwrite()
    test_time_flush()
    test_steady_load_flush()
    test_disabled_noop()
    print("\nALL ROLLOUT-DUMP TESTS PASSED")
