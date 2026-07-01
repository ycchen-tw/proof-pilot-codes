# Copyright 2026 proof-pilot. Apache-2.0.
"""prompt source —— 重用 v1 `opd.prompts.ProblemPromptLoader`（distill_gen 證明題庫 + prover template
→ student chat template → input_ids），包成**無限** iterator（每 epoch reshuffle）。

OPD rollout 要的是 prompt 的 token_ids（token-in-token-out）。v1 loader 已驗證可用，直接重用。
"""
from __future__ import annotations

import os
import sys
from typing import Iterator

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "_vendor_opd")))

from opd_v2.config import OPDConfig
from opd_v2.data_plane.produce import Prompt


def iter_prompts_forever(cfg: OPDConfig) -> Iterator[Prompt]:
    """無限 prompt 流：跑完一輪題庫就換 seed reshuffle 再跑（連續訓練用）。"""
    from opd.prompts import ProblemPromptLoader

    epoch = 0
    while True:
        loader = ProblemPromptLoader(
            cfg.trainer.student_path, cfg.problems_parquet,
            template_pool=list(cfg.prover_template_pool),
            seed=cfg.seed + epoch * 100003)
        n = 0
        for p in loader.iter_prompts(shuffle=True):
            n += 1
            yield Prompt(ids=p.input_ids,
                         meta={"id": p.id, "domain": p.domain, **(p.meta or {})})
        if n == 0:
            raise RuntimeError(f"prompt source produced 0 prompts (parquet={cfg.problems_parquet})")
        epoch += 1


def iter_prompts_debug(n: int = 64, plen: int = 48, seed: int = 0) -> Iterator[Prompt]:
    """無 tokenizer/parquet 依賴的假 prompt 流（單元測/快速 smoke 用）。"""
    import random
    rng = random.Random(seed)
    i = 0
    while i < n:
        yield Prompt(ids=[rng.randint(3, 129279) for _ in range(plen)], meta={"id": f"dbg-{i}"})
        i += 1
