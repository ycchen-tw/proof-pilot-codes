# Copyright 2026 proof-pilot. Apache-2.0.
"""load-aware concurrency pools（修 v1 P9：teacher 靜態 by-wid round-robin → load-aware）。

每個 service（rollout / teacher）一個 `Pool`，內含多個 replica。`slot()` 是 async context manager：
1. `await` 全域 semaphore（限總在飛行數）；
2. 選**最閒的活 replica**（in-flight 計數最小；連錯的 replica `dead_until` 期間跳過）；
3. yield 該 replica 的 client；
4. 結束時 in-flight -1、釋放 semaphore；途中拋例外 → 標該 replica dead（短暫 sideline、自癒）。

用「在飛行計數」而非 `/v1/loads` 當 load 訊號：永遠可用、零額外 round-trip、單一 event loop 下 pick+inc
原子。（`/v1/loads` 留作未來升級。）兩個 pool 各自獨立 semaphore → rollout(TP1 慢)/teacher(TP4 快)
容量分開調（PLAN §5.3/§5.4）。
"""
from __future__ import annotations

import contextlib
import logging
import time
from dataclasses import dataclass, field

import aiohttp

from opd_v2.config import OPDConfig
from opd_v2.data_plane.clients import RolloutClient, TeacherClient

log = logging.getLogger("opd_v2.pools")


@dataclass
class Replica:
    base_url: str
    client: object                 # RolloutClient | TeacherClient
    cap: int = 8                   # per-replica 軟上限（在飛行）
    in_flight: int = 0
    dead_until: float = 0.0
    n_errors: int = 0
    n_done: int = 0

    def live(self, now: float) -> bool:
        return now >= self.dead_until


class Pool:
    def __init__(self, replicas: list[Replica], concurrency: int, dead_seconds: float = 10.0,
                 name: str = "pool"):
        if not replicas:
            raise ValueError(f"{name}: no replicas")
        self.replicas = replicas
        self.name = name
        self.dead_seconds = dead_seconds
        self._sem = __import__("asyncio").Semaphore(max(1, concurrency))
        self.concurrency = max(1, concurrency)

    def _pick(self) -> Replica:
        now = time.monotonic()
        live = [r for r in self.replicas if r.live(now)]
        if live:
            # 最閒（in_flight 最小）；平手取先者
            return min(live, key=lambda r: r.in_flight)
        # 全 dead：挑最快復活的那台樂觀重試（避免全停）
        return min(self.replicas, key=lambda r: r.dead_until)

    @contextlib.asynccontextmanager
    async def slot(self):
        """`async with pool.slot() as client:` —— 限流 + load-aware 選台 + 失敗 sideline。"""
        await self._sem.acquire()
        r = self._pick()
        r.in_flight += 1
        try:
            yield r.client
            r.n_done += 1
        except Exception as e:
            r.n_errors += 1
            r.dead_until = time.monotonic() + self.dead_seconds
            log.warning("%s slot err on %s: %r", self.name, r.base_url, e)   # V33: 記例外型別供診斷 err 來源
            raise
        finally:
            r.in_flight -= 1
            self._sem.release()

    def stats(self) -> dict:
        now = time.monotonic()
        return {
            "concurrency": self.concurrency,
            "live": sum(1 for r in self.replicas if r.live(now)),
            "replicas": len(self.replicas),
            "in_flight": sum(r.in_flight for r in self.replicas),
            "errors": sum(r.n_errors for r in self.replicas),
            "done": sum(r.n_done for r in self.replicas),
        }


def build_pools(session: aiohttp.ClientSession, cfg: OPDConfig) -> tuple[Pool, Pool]:
    """從 config 建 rollout/teacher 兩個 pool（共用一個 aiohttp session）。"""
    r_caps = cfg.rollout.max_inflight_per_replica
    rollout_reps = [Replica(u, RolloutClient(session, u), cap=r_caps) for u in cfg.rollout.urls]
    r_conc = cfg.data_plane.rollout_concurrency or sum(r.cap for r in rollout_reps)
    rollout_pool = Pool(rollout_reps, r_conc, cfg.data_plane.dead_until_seconds, name="rollout")

    t_caps = cfg.teacher.max_inflight_per_replica
    teacher_reps = [Replica(u, TeacherClient(session, u), cap=t_caps) for u in cfg.teacher.urls]
    t_conc = cfg.data_plane.teacher_concurrency or sum(r.cap for r in teacher_reps)
    teacher_pool = Pool(teacher_reps, t_conc, cfg.data_plane.dead_until_seconds, name="teacher")
    return rollout_pool, teacher_pool
