# Copyright 2026 proof-pilot. Apache-2.0.
"""Async trajectory buffer，帶 weight_version 標記 + max_staleness 丟棄（PLAN §2/§4 D4）。

OPD 是 near-on-policy：rollout 由落後 trainer 幾步的權重版本抽出。沒有 importance ratio 修正
（full-vocab GKD 直接散度），所以「夠 on-policy」靠**限制 staleness**達成，而非 IS weight。每條
trajectory 標上抽樣時的 `weight_version`；trainer 在 step `cur_step` 取 batch 時，丟掉
`cur_step - weight_version > max_staleness` 的。

純邏輯、thread-safe（orchestrator 多個 async producer + trainer consumer）；staleness 規則抽成
純函式 `is_stale` 方便單測。
"""
from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Trajectory:
    """一條 student rollout + （scoring 後）對應的 quant teacher hidden。

    token_ids 是 **完整序列**（prompt + generated），全程 token-in-token-out（D12）。
    teacher_* 在 teacher service scoring 後填入（packed/scales，旋轉空間 had+int6）。
    """
    token_ids: list[int]                 # prompt + generated（完整）
    prompt_len: int                      # 前 prompt_len 個是 prompt
    weight_version: int                  # 抽樣時 rollout server 上的 trainer step
    teacher_packed: Optional[bytes] = None   # had+int6 packed（scoring 後）
    teacher_scales: Optional[bytes] = None   # fp16 scales（scoring 後）
    teacher_seq_len: Optional[int] = None     # teacher service 回傳 position 數（通常 = gen_len + 1）
    teacher_top1: Optional[bytes] = None      # optional int32 teacher argmax ids（同 teacher_seq_len 長度）
    position_offset: int = 0                  # token_ids[0] 對應的 RoPE position；long-window crop 用
    meta: dict = field(default_factory=dict)

    @property
    def gen_len(self) -> int:
        return len(self.token_ids) - self.prompt_len

    def target_positions(self) -> range:
        """預測 generated token 的 hidden position：prompt_len-1 .. len-2（含），
        其 hidden 經 head 預測 token_ids[prompt_len .. len-1]（即 generated 段）。
        這是 G4 對齊的定義：teacher hidden[t] 與 student hidden[t] 都預測 token_ids[t+1]。"""
        return range(self.prompt_len - 1, len(self.token_ids) - 1)

    def scored(self) -> bool:
        return self.teacher_packed is not None


def is_stale(weight_version: int, cur_step: int, max_staleness: int) -> bool:
    """trajectory 是否太舊而該丟。純函式，方便單測。"""
    return (cur_step - weight_version) > max_staleness


class TrajectoryBuffer:
    """有界、thread-safe 的 trajectory 佇列，取 batch 時做 staleness 丟棄。"""

    def __init__(self, capacity: int, capacity_tokens: int | None = None):
        """capacity = 條數上限；capacity_tokens = 總 token 上限。長 CoT 時 token 上限主導：teacher
        hidden bytes ~3.3KB/token，4096 條 × 32k token 會吃數百 GB RAM，必須以 token 計界。"""
        self.capacity = capacity
        self.capacity_tokens = capacity_tokens
        self._dq: deque[Trajectory] = deque()
        self._tok = 0                       # 佇列中總 token 數（與 _dq 同鎖維護）
        self._lock = threading.Lock()
        # 統計（log 用）
        self.n_put = 0
        self.n_dropped_stale = 0
        self.n_dropped_overflow = 0
        self.n_served = 0

    def __len__(self) -> int:
        with self._lock:
            return len(self._dq)

    def near_full(self, frac: float = 0.9) -> bool:
        """producer 背壓判定：條數或 token 任一逼近上限。"""
        with self._lock:
            if len(self._dq) >= self.capacity * frac:
                return True
            return bool(self.capacity_tokens) and self._tok >= self.capacity_tokens * frac

    def put(self, traj: Trajectory) -> None:
        """加一條（必須已 scored）。滿了就丟最舊的（背壓 + 偏好新鮮）。"""
        if not traj.scored():
            raise ValueError("put() 只收已 scored 的 trajectory")
        L = len(traj.token_ids)
        with self._lock:
            while self._dq and (len(self._dq) >= self.capacity
                                or (self.capacity_tokens and self._tok + L > self.capacity_tokens)):
                old = self._dq.popleft()
                self._tok -= len(old.token_ids)
                self.n_dropped_overflow += 1
            self._dq.append(traj)
            self._tok += L
            self.n_put += 1

    def get_batch(self, n: int, cur_step: int, max_staleness: int) -> list[Trajectory]:
        """取最多 n 條夠新鮮的；過程遇到 stale 的就丟掉（計數）。FIFO。"""
        out: list[Trajectory] = []
        with self._lock:
            while self._dq and len(out) < n:
                t = self._dq.popleft()
                self._tok -= len(t.token_ids)
                if is_stale(t.weight_version, cur_step, max_staleness):
                    self.n_dropped_stale += 1
                    continue
                out.append(t)
            self.n_served += len(out)
        return out

    def note_overflow_drop(self, n: int = 1) -> None:
        """Record a producer-side drop that happened before put(), e.g. failed long-window slicing."""
        with self._lock:
            self.n_dropped_overflow += n

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
