# Copyright 2026 proof-pilot. Apache-2.0.
"""PoolSampler —— flow-balance 取樣（取代 single-round 的 iter_prompts_forever）。

每個 atom：選一個 role → 從 pool 組 context → yield Prompt（token-in-token-out）。

**比例靠 fill-fraction 自動平衡，不手挑固定比例**（PLAN agentic 段）：
- `fill_fraction(role) = student_count(role) / role_mix_weight(role)`；採 **fill_fraction 最低**的 available
  role（softmax_temp>0 加隨機避免 thrash）。→ 四個 role lockstep 逼近 role_mix 比例。
- role 內挑 **deficit 最大的 item**（verify 挑最少被 verify 的 proof；refine 挑 verified-但少 refined 的題）
  → 攤平、**避免「狂生 proof、verify 跟不上、堆積未-verify proof」**（user 指正的 failure mode）。
- role_mix 22/44/20/14：verify=2×prove（=每 proof 2 verify 的 fan-out）→ verify 自然最大宗、跟得上 proof。

注意：`next()` 內含 tokenizer.encode（同步、可能略 block event loop）——同 ProblemPromptLoader 既有 pattern；
long-CoT 下 atom 稀疏（單條 decode 數分鐘）故便宜。Iterator 永不 StopIteration（prove 永遠可 yield）。
"""
from __future__ import annotations

import logging
import math
import random
from typing import Iterator

from opd_v2.agentic.pool import PoolStore
from opd_v2.agentic.roles import RolePromptBuilder
from opd_v2.config import OPDConfig
from opd_v2.data_plane.produce import Prompt

log = logging.getLogger("opd_v2.agentic.sampler")

_ORDER = ("prove", "verify", "refine", "select")   # tie-break 用的固定順序


class PoolSampler:
    def __init__(self, cfg: OPDConfig, pool: PoolStore, builder: RolePromptBuilder | None = None):
        self.cfg = cfg
        self.pool = pool
        self.builder = builder or RolePromptBuilder(cfg.trainer.student_path, cfg)
        self.rng = random.Random(cfg.seed)
        self.n_yielded = {r: 0 for r in _ORDER}        # 已 yield 的 role 計數（觀測；wandb 可讀）
        self.n_render_dropped = {r: 0 for r in _ORDER}  # build_* 回 None（prompt 過長/無 item）→ 該 role 被丟
        self.n_fallback_prove = 0                       # 全 role 失敗、退到 prove fallback 的次數

    # ---- role 選擇 ----
    def _role_weights(self) -> dict:
        rm = self.cfg.agentic.role_mix
        return {r: float(rm.get(r, 0.0)) for r in _ORDER if float(rm.get(r, 0.0)) > 0.0}

    def _pick_role(self, available: set, counts: dict) -> str | None:
        weights = self._role_weights()
        cands = [r for r in _ORDER if r in available and r in weights]
        if not cands:
            return None
        fill = {r: counts.get(r, 0) / weights[r] for r in cands}   # 越低 = 越落後 = 越該採
        temp = max(1e-3, self.cfg.agentic.softmax_temp)
        # softmax over (-fill/temp)，數值穩定
        xs = [-fill[r] / temp for r in cands]
        mx = max(xs)
        es = [math.exp(x - mx) for x in xs]
        s = sum(es) or 1.0
        probs = [e / s for e in es]
        return self.rng.choices(cands, weights=probs, k=1)[0]

    # ---- role → Prompt ----
    def _build(self, role: str) -> Prompt | None:
        p = self.pool
        if role == "prove":
            prob = p.pick_prove_problem(self.cfg, self.rng)
            return self.builder.build_prove(prob) if prob else None
        if role == "verify":
            tgt = p.pick_verify_target(self.cfg, self.rng)
            return self.builder.build_verify(*tgt) if tgt else None
        if role == "refine":
            prob = p.pick_refine_problem(self.cfg, self.rng)
            return self.builder.build_refine(prob) if prob else None
        if role == "select":
            prob = p.pick_select_problem(self.cfg, self.rng)
            return self.builder.build_select(prob) if prob else None
        return None

    def next_prompt(self) -> Prompt | None:
        """選 role → 組 Prompt。role 內失敗（無 item / prompt 過長）→ 記 render-drop、退到其它 role。"""
        available = self.pool.available_roles(self.cfg)
        if not available:
            return None                       # pool 空（無題）——caller 應已 seed
        counts = self.pool.student_counts()   # O(1)，每 atom 算一次（不在 retry 迴圈裡重算，P1）
        tried: set = set()
        for _ in range(len(_ORDER) + 1):
            remaining = available - tried
            if not remaining:
                break
            role = self._pick_role(remaining, counts)
            if role is None:
                break
            tried.add(role)
            prompt = self._build(role)
            if prompt is not None:
                self.n_yielded[role] += 1
                return prompt
            self.n_render_dropped[role] += 1   # build 回 None（無 item / prompt 過長）→ 可見化（B3）
        # 全失敗 → 最後保險：prove（context 最簡單、幾乎不會 None）
        prob = self.pool.pick_prove_problem(self.cfg, self.rng)
        prompt = self.builder.build_prove(prob) if prob else None
        if prompt is not None:
            self.n_yielded["prove"] += 1
            self.n_fallback_prove += 1
        return prompt

    def stats(self) -> dict:
        return {"yielded": dict(self.n_yielded), "render_dropped": dict(self.n_render_dropped),
                "fallback_prove": self.n_fallback_prove}

    def iter_forever(self) -> Iterator[Prompt]:
        """無限 prompt 流（scheduler 用）。next_prompt 只有在 pool 完全無題（= 沒 seed/設定錯）才回 None
        → 致命，raise 讓 orchestrator 明確失敗（不要悄悄當枯竭收尾）。"""
        while True:
            prompt = self.next_prompt()
            if prompt is None:
                raise RuntimeError("PoolSampler: pool has no problems (seed not loaded?)")
            yield prompt
