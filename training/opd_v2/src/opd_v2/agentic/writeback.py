# Copyright 2026 proof-pilot. Apache-2.0.
"""PoolIngestor —— rollout → decode(answer-only) → parse → validity-gate → pool.admit（write-back）。

設計（PLAN agentic 段，鏡像 rollout_store 的非阻塞 writer + produce.py 的 dump hook）：
- **gate**：所有生成都是 training 樣本（teacher /score 照常）；**只有 parse-pass 的 artifact 才寫進 pool**
  當下游 context（user 定的規則）。截斷（finish_reason=="length"）→ 不進 pool（但仍訓練、仍被 rollout_store dump）。
- **兩種抽取**：training 樣本 = 完整 continuation（含 think，由 trainer 處理）；**pool artifact = 只 parse 出
  answer（<solution>/<score>...），丟掉 think**——下游 verifier 不該看到 prover 的私有 reasoning（同 math_3r）。
- **非阻塞**：`append()` 只 enqueue（event loop 微秒級）；背景 coroutine `run_in_executor` 解 token→text，
  parse（cheap、on loop），`pool.admit_*`（on loop，index mutation 與 sampler 讀同一 event loop → 無鎖）。
- admit 與 teacher 成敗無關（在 produce.py 的 teacher /score **之前**呼叫）：proof 是否能當 context 跟它的
  teacher 分數無關。teacher 失敗只丟 training 樣本、不丟 pool artifact。

select：無 pool node（無下游消費）→ 不 parse、只 `admit_select`（計數，供 fill_fraction）。
"""
from __future__ import annotations

import asyncio
import logging

from opd_v2.agentic.pool import PoolStore
from opd_v2.config import OPDConfig

log = logging.getLogger("opd_v2.agentic.writeback")

_STOP = object()


def parse_artifact(text: str, stage: str, finish_reason: str | None):
    """parse student 生成（answer-only text）成 pool artifact dict；invalid 回 None。

    重用 math_3r parser（不 re-implement）：prove/refine 走 _two_section validity（非截斷∧有<solution>∧
    score∈{0,.5,1}∧len>500）；verify 需 score 可解析且非截斷。
    """
    import os
    import sys
    m3r = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..", "distill_gen", "math_3r"))
    if m3r not in sys.path:
        sys.path.insert(0, m3r)
    from parser import parse_proof_package, parse_refined_package, parse_verification  # noqa: E402

    call = {"content": text or "", "finish_reason": finish_reason, "error": None}
    if stage in ("prove", "refine"):
        pkg = (parse_proof_package if stage == "prove" else parse_refined_package)(call, "X0")
        if not pkg.valid:
            return None
        return {"content": pkg.proof, "self_eval": pkg.self_eval, "self_score": pkg.self_score}
    if stage == "verify":
        if finish_reason == "length":
            return None
        v = parse_verification(call, "X0", 0)
        if v.score is None:
            return None
        return {"score": v.score, "text": v.text}
    return None


class PoolIngestor:
    """把 student rollout 旁路寫回 pool（非阻塞、背景 decode/parse/admit）。"""

    def __init__(self, pool: PoolStore, tokenizer, cfg: OPDConfig):
        self.pool = pool
        self.tok = tokenizer
        self.cfg = cfg
        self._q: asyncio.Queue | None = None
        self._task: asyncio.Task | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self.n_admitted = {"prove": 0, "verify": 0, "refine": 0, "select": 0}
        self.n_rejected = 0
        self.n_seen = 0

    def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._q = asyncio.Queue()
        self._task = asyncio.create_task(self._run(), name="pool_ingestor")

    def append(self, full_ids: list, prompt_len: int, wv: int, meta: dict,
               finish_reason: str | None) -> None:
        """非阻塞 enqueue（mirror dump.append）。在 produce.py 的 teacher /score 前呼叫。"""
        if self._q is None:
            return
        self.n_seen += 1
        self._q.put_nowait((list(full_ids), int(prompt_len), int(wv), dict(meta or {}), finish_reason))

    async def _run(self) -> None:
        while True:
            item = await self._q.get()
            if item is _STOP:
                break
            try:
                await self._ingest(*item)
            except Exception:
                log.exception("pool ingest failed (skipped)")

    async def _ingest(self, full_ids, prompt_len, wv, meta, finish_reason) -> None:
        stage = meta.get("stage")
        problem_id = meta.get("problem_id")
        if stage is None or problem_id is None:
            return
        if stage == "select":
            if finish_reason == "length":      # 截斷的 select 不計進度（fill_fraction 不高估 select，R3）
                self.n_rejected += 1
                return
            self.pool.admit_select(problem_id, wv=wv, source="student")
            self.n_admitted["select"] += 1
            return
        gen_ids = full_ids[prompt_len:]
        if not gen_ids:
            self.n_rejected += 1
            return
        text = await self._loop.run_in_executor(None, self._decode, gen_ids)
        art = parse_artifact(text, stage, finish_reason)
        if art is None:
            self.n_rejected += 1
            return
        if stage == "prove":
            ok = self.pool.admit_proof(problem_id, art["content"], art["self_eval"],
                                       art["self_score"], wv=wv, source="student")
        elif stage == "verify":
            refs = meta.get("refs") or []
            ok = self.pool.admit_verify(problem_id, refs[0], art["score"], art["text"],
                                        wv=wv, source="student") if refs else None
        elif stage == "refine":
            ok = self.pool.admit_refined(problem_id, meta.get("refs") or [], art["content"],
                                         art["self_eval"], art["self_score"], wv=wv, source="student")
        else:
            ok = None
        if ok is not None:
            self.n_admitted[stage] += 1
        else:
            self.n_rejected += 1

    def _decode(self, gen_ids: list) -> str:
        return self.tok.decode(gen_ids, skip_special_tokens=False)

    async def close(self) -> None:
        if self._task is None:
            return
        self._q.put_nowait(_STOP)
        try:
            await self._task
        except Exception:
            log.exception("pool ingestor close error")
        self._task = None

    def stats(self) -> dict:
        return {"seen": self.n_seen, "rejected": self.n_rejected,
                "queue": (self._q.qsize() if self._q is not None else 0), **self.n_admitted}
