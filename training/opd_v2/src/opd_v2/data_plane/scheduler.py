# Copyright 2026 proof-pilot. Apache-2.0.
"""keep-N-in-flight scheduler + 背壓（PLAN §5.3）。

維持 ~`target_inflight` 個 atom 在飛行；完成一個收一個入 buffer；buffer `near_full` 就停發新 atom
（背壓）。每個 prompt fan-out 成 `n_samples` 個獨立 atom（V1）。純 asyncio worker-pool，無 blocking
thread（修 v1 P5 的 40~64 條 OS thread）。

GC 掛在這裡：buffer 滿了擠出的舊 traj、其 hidden 檔由 scheduler 立刻 unlink（overflow GC）；
stale-drop / batch 消費後的 GC 在 orchestrator 端（V14）。
"""
from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, Iterator

from opd_v2.buffer import ScoredTrajectory, TrajectoryBuffer
from opd_v2.data_plane.produce import ProduceResult, Prompt
from opd_v2.hidden_store import HiddenStore

log = logging.getLogger("opd_v2.scheduler")


class Scheduler:
    def __init__(self, *, prompts: Iterator[Prompt],
                 produce: Callable[[Prompt], Awaitable[ProduceResult | None]],
                 buffer: TrajectoryBuffer, store: HiddenStore,
                 target_inflight: int, n_samples: int, near_full_frac: float = 0.9):
        self.prompts = prompts
        self.produce = produce
        self.buf = buffer
        self.store = store
        self.target = max(1, target_inflight)
        self.n = max(1, n_samples)
        self.frac = near_full_frac
        self._pending: list[Prompt] = []        # fan-out 後待發 atom
        self._exhausted = False
        self.n_produced = 0
        self.n_failed = 0
        self._gen_sum = 0          # rollout 生成長度累計（degeneration/length-collapse 監控）
        self._gen_max = 0
        self._gen_n = 0
        self._fr = {"stop": 0, "length": 0, "other": 0}   # finish_reason 累計（EOS/length-停 比例）
        self._n_admit_drop: dict[str, int] = {}           # admission filter 主動剔除（by reason；≠ fail）

    def _refill_pending(self) -> bool:
        """從 prompt source 拉一題、fan-out 成 n 個 atom 進 pending。回是否還有 prompt。"""
        if self._exhausted:
            return False
        try:
            p = next(self.prompts)
        except StopIteration:
            self._exhausted = True
            return False
        self._pending.extend([p] * self.n)
        return True

    async def run(self, stop: asyncio.Event) -> None:
        """跑到 stop 被 set（orchestrator 收尾）或 prompt source 枯竭且 in-flight 清空。"""
        inflight: set[asyncio.Task] = set()
        try:
            while not stop.is_set():
                # 在容量內、且未背壓時，盡量補滿 in-flight
                while len(inflight) < self.target and not self.buf.near_full(self.frac):
                    if not self._pending and not self._refill_pending():
                        break
                    p = self._pending.pop()
                    inflight.add(asyncio.create_task(self.produce(p)))

                if not inflight:
                    if self._exhausted and not self._pending:
                        break                      # 枯竭：沒東西可跑了
                    await asyncio.sleep(0.05)       # 背壓中 / 暫無 prompt：讓出
                    continue

                done, inflight = await asyncio.wait(
                    inflight, return_when=asyncio.FIRST_COMPLETED, timeout=1.0)
                for t in done:
                    try:
                        res = t.result()
                    except Exception:
                        res = None
                    if res is None:                        # 例外 / 早退（prompt 超窗、生成出錯）
                        self.n_failed += 1
                        continue
                    # 對【所有】完成的生成記 finish_reason（drop/fail 也算 → eos/length 反映生成端、不被 filter 扭曲）
                    fr = res.finish_reason
                    if fr:
                        self._fr[fr if fr in self._fr else "other"] += 1
                    if res.drop_reason:                    # admission 主動剔除（≠ fail；teacher 前就 drop、無 hidden 可 GC）
                        self._n_admit_drop[res.drop_reason] = self._n_admit_drop.get(res.drop_reason, 0) + 1
                        continue
                    traj = res.traj
                    if traj is None:                       # 生成/teacher 失敗
                        self.n_failed += 1
                        continue
                    evicted = self.buf.put(traj)           # 滿了擠出最舊的
                    if evicted:
                        self.store.delete_handles([e.handle for e in evicted])  # overflow GC（V14）
                    self.n_produced += 1
                    g = traj.gen_len
                    self._gen_sum += g
                    self._gen_max = max(self._gen_max, g)
                    self._gen_n += 1
        finally:
            for t in inflight:
                t.cancel()
            res = await asyncio.gather(*inflight, return_exceptions=True)
            # 被取消但其實已產出的（race）：GC 其檔，避免孤兒
            for r in res:
                if isinstance(r, ProduceResult) and r.traj is not None:
                    self.store.delete(r.traj.handle.path)

    def stats(self) -> dict:
        return {"produced": self.n_produced, "failed": self.n_failed,
                "pending": len(self._pending), "exhausted": self._exhausted,
                "gen_len_mean": (self._gen_sum / self._gen_n) if self._gen_n else 0.0,
                "gen_len_max": self._gen_max,
                "fr_stop": self._fr["stop"], "fr_length": self._fr["length"],
                "fr_other": self._fr["other"],
                # admission filter：主動剔除（by reason）+ 總數（≠ failed）。剔除率 = dropped/(produced+dropped)。
                "admit_dropped": dict(self._n_admit_drop),
                "admit_dropped_total": sum(self._n_admit_drop.values())}
