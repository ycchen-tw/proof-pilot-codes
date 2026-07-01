# Copyright 2026 proof-pilot. Apache-2.0.
"""輕量 trajectory buffer（V16）—— 只存 `{ids, prompt_len, wv, handle}`，**無 teacher bytes**。

v1 buffer 把 teacher hidden bytes 整包存在 Trajectory 裡（~3.3KB/token），4096 條長 CoT 直接吃數百 GB
RAM。v2 buffer 只存 token ids + 一個 HiddenHandle（指向 shared-FS 的 hidden 檔），所以條數/token 上限
可以大很多，scatter 也超輕。bytes 由 trainer owning rank 用 handle 從 FS 直讀（見 hidden_store）。

near-on-policy：無 importance ratio，靠 `max_staleness` 丟太舊的（`cur_step - wv > max_staleness`）。
staleness 規則抽成純函式 `is_stale` 方便單測。orchestrator 是單一 asyncio event loop（單執行緒），
鎖只為保險（async 臨界區內無 await，本就原子）。
"""
from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field

from opd_v2.hidden_store import HiddenHandle


@dataclass
class ScoredTrajectory:
    """一條 student rollout + 已 score 的 teacher hidden handle（指向 shared FS）。"""
    ids: list[int]               # 完整序列（prompt + generated），token-in-token-out
    prompt_len: int              # 前 prompt_len 個是 prompt
    wv: int                      # rollout server 生成時的 weight_version（server-reported，V6）
    handle: HiddenHandle         # teacher hidden 在 shared FS 的 handle（無 bytes）
    meta: dict = field(default_factory=dict)
    finish_reason: str = ""      # rollout 停止原因："stop"=EOS / "length"=撞窗口（截斷監控；不進 wire）

    @property
    def gen_len(self) -> int:
        return len(self.ids) - self.prompt_len

    @property
    def n_tokens(self) -> int:
        return len(self.ids)

    def to_wire(self) -> dict:
        """送給 trainer 的最小表示（HTTP body / gloo scatter 都用這個；不含 bytes）。"""
        return {"ids": self.ids, "prompt_len": self.prompt_len, "wv": self.wv,
                "handle": self.handle.to_dict()}

    @classmethod
    def from_wire(cls, d: dict) -> "ScoredTrajectory":
        return cls(ids=list(d["ids"]), prompt_len=int(d["prompt_len"]), wv=int(d["wv"]),
                   handle=HiddenHandle.from_dict(d["handle"]))


def is_stale(wv: int, cur_step: int, max_staleness: int) -> bool:
    """trajectory 是否太舊而該丟。純函式，方便單測。

    `max_staleness <= 0` = **關閉**（永不 stale）。OPD 沒用 importance ratio（不存 generation logprob）→
    staleness 不是正確性需求、teacher hidden frozen 永遠有效，舊 wv 的 rollout 一樣是合法蒸餾資料。
    long CoT rollout 超貴，預設關掉不丟（見 config 預設 0）。設正值才啟用「偏好新鮮」。
    """
    return max_staleness > 0 and (cur_step - wv) > max_staleness


class TrajectoryBuffer:
    """有界 trajectory 佇列；取 batch 時做 staleness 丟棄。FIFO + 偏好新鮮（滿了丟最舊）。"""

    def __init__(self, capacity: int, capacity_tokens: int | None = None):
        self.capacity = capacity
        self.capacity_tokens = capacity_tokens
        self._dq: deque[ScoredTrajectory] = deque()
        self._tok = 0
        self._lock = threading.Lock()
        self.n_put = 0
        self.n_dropped_stale = 0
        self.n_dropped_overflow = 0
        self.n_served = 0

    def __len__(self) -> int:
        with self._lock:
            return len(self._dq)

    def token_count(self) -> int:
        with self._lock:
            return self._tok

    def near_full(self, frac: float = 0.9) -> bool:
        """producer 背壓判定：條數或 token 任一逼近上限。"""
        with self._lock:
            if len(self._dq) >= self.capacity * frac:
                return True
            return bool(self.capacity_tokens) and self._tok >= self.capacity_tokens * frac

    def put(self, traj: ScoredTrajectory) -> list[ScoredTrajectory]:
        """加一條。滿了就丟最舊的（背壓 + 偏好新鮮）。回**被擠出的 trajectory**（呼叫端負責 GC 其 handle）。"""
        L = traj.n_tokens
        evicted: list[ScoredTrajectory] = []
        with self._lock:
            while self._dq and (len(self._dq) >= self.capacity
                                or (self.capacity_tokens and self._tok + L > self.capacity_tokens)):
                old = self._dq.popleft()
                self._tok -= old.n_tokens
                self.n_dropped_overflow += 1
                evicted.append(old)
            self._dq.append(traj)
            self._tok += L
            self.n_put += 1
        return evicted

    def get_batch(self, n: int, cur_step: int, max_staleness: int
                  ) -> tuple[list[ScoredTrajectory], list[ScoredTrajectory]]:
        """取最多 n 條夠新鮮的；遇到 stale 的丟掉。回 (kept, dropped_stale)。

        dropped_stale 一併回傳讓呼叫端 GC 其 hidden 檔（V14：stale-drop 後 unlink）。
        """
        out: list[ScoredTrajectory] = []
        stale: list[ScoredTrajectory] = []
        with self._lock:
            while self._dq and len(out) < n:
                t = self._dq.popleft()
                self._tok -= t.n_tokens
                if is_stale(t.wv, cur_step, max_staleness):
                    self.n_dropped_stale += 1
                    stale.append(t)
                    continue
                out.append(t)
            self.n_served += len(out)
        return out, stale

    def stats(self) -> dict:
        with self._lock:
            return {
                "size": len(self._dq),
                "tokens": self._tok,
                "n_put": self.n_put,
                "n_served": self.n_served,
                "n_dropped_stale": self.n_dropped_stale,
                "n_dropped_overflow": self.n_dropped_overflow,
            }
