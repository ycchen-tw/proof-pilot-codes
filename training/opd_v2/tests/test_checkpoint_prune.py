# Copyright 2026 proof-pilot. Apache-2.0.
"""快速單元測試：durable checkpoint 的 retention（_prune_checkpoints）+ latest 保護邏輯。

純 tmpdir FS，不建模型（雖 import core 會帶 torch，但不跑 GPU）。驗最易出 off-by-one 的修剪邏輯：
  - keep=N 只留最新 N 個
  - keep<0 全留
  - **絕不刪 latest.json 指到的那個**（即使它是舊的）

run:  PYTHONPATH=src .venv/bin/python tests/test_checkpoint_prune.py
"""
from __future__ import annotations

import glob
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, "..", "src"))
sys.path.insert(0, SRC)

from opd_v2.trainer.core import OPDTrainerV2

prune = OPDTrainerV2._prune_checkpoints


def _mk(root: str, step: int) -> str:
    d = os.path.join(root, f"step_{step:06d}")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "meta.json"), "w") as f:
        f.write("{}")
    return d


def _set_latest(root: str, d: str, step: int) -> None:
    with open(os.path.join(root, "latest.json"), "w") as f:
        json.dump({"dir": d, "step": step}, f)


def _survivors(root: str) -> set[str]:
    return {os.path.basename(x) for x in glob.glob(os.path.join(root, "step_*"))}


def main() -> int:
    fails: list[str] = []

    def check(name, ok, extra=""):
        print(f"  [{'PASS' if ok else 'FAIL'}] {name} {extra}", flush=True)
        if not ok:
            fails.append(name)

    # 1) keep=2，latest=最新 → 只留最新 2 個
    with tempfile.TemporaryDirectory() as root:
        ds = [_mk(root, s) for s in (10, 20, 30, 40, 50)]
        _set_latest(root, ds[-1], 50)
        prune(root, 2)
        check("keep=2 keeps newest 2", _survivors(root) == {"step_000040", "step_000050"}, str(_survivors(root)))

    # 2) keep=-1 → 全留
    with tempfile.TemporaryDirectory() as root:
        ds = [_mk(root, s) for s in (10, 20, 30)]
        _set_latest(root, ds[-1], 30)
        prune(root, -1)
        check("keep=-1 keeps all", _survivors(root) == {"step_000010", "step_000020", "step_000030"}, str(_survivors(root)))

    # 3) latest 指到舊的（病態）→ 新的 2 個 + 被保護的 latest 都活，其餘刪
    with tempfile.TemporaryDirectory() as root:
        ds = [_mk(root, s) for s in (10, 20, 30, 40, 50)]
        _set_latest(root, ds[0], 10)            # latest = 最舊
        prune(root, 2)
        check("never prunes latest (even if old)", _survivors(root) == {"step_000010", "step_000040", "step_000050"}, str(_survivors(root)))

    # 4) keep=1
    with tempfile.TemporaryDirectory() as root:
        ds = [_mk(root, s) for s in (10, 20, 30)]
        _set_latest(root, ds[-1], 30)
        prune(root, 1)
        check("keep=1 keeps newest 1", _survivors(root) == {"step_000030"}, str(_survivors(root)))

    # 5) ckpt 數 <= keep → 不刪
    with tempfile.TemporaryDirectory() as root:
        ds = [_mk(root, s) for s in (10, 20)]
        _set_latest(root, ds[-1], 20)
        prune(root, 5)
        check("ckpts<=keep keeps all", _survivors(root) == {"step_000010", "step_000020"}, str(_survivors(root)))

    print("\n" + "=" * 50, flush=True)
    if fails:
        print(f"FAILED: {fails}")
        return 1
    print("ALL CHECKPOINT-PRUNE TESTS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
