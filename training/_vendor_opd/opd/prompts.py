# Copyright 2026 proof-pilot. Apache-2.0.
"""「只取題目」的 prompt loader（PLAN §3 D11、§7 Phase 0）。

OPD 的 rollout 需要 **prompt 的 token_ids**（token-in-token-out，D12）：讀 L2 parquet 的
OpenAI-style `messages`，取到第一個 assistant 之前（system + user 輪），用 **student 的 chat
template**（`add_generation_prompt=True`）渲染成 input_ids 給 rollout server。答案/assistant 內容
全部丟掉——OPD 在 teacher 分布上學，不需要參考解。

domain 選擇重用 data_mix 的 partition 掃描；預設取 math/proof/science（評測領域），排除 agentic
（tool 多輪、與 proof 目標無關）。
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Iterator, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from data_mix import partitions  # noqa: E402  (reuse partition 掃描)

# 預設取的 domain（partition key = "<dataset>/<domain>"）；math/proof/science。
DEFAULT_INCLUDE = ["*/math_cot", "*/math_tir", "*/math*", "*/proof*", "*/*verification*", "*/science*"]
DEFAULT_EXCLUDE = ["*/agent*", "*/swe*", "*/tool*"]


@dataclass
class Prompt:
    id: str
    input_ids: list[int]          # 渲染好的 prompt（含 generation prompt），token-in-token-out
    domain: str
    meta: dict


def _select_shards(roots: list[Path], include: list[str], exclude: list[str]) -> list[tuple[str, Path]]:
    """回 [(partition_key, shard_path)]，依 include/exclude glob 過 partition。"""
    out: list[tuple[str, Path]] = []
    for root in roots:
        for pk, shards in sorted(partitions(root).items()):
            if not any(fnmatchcase(pk, g) for g in include):
                continue
            if any(fnmatchcase(pk, g) for g in exclude):
                continue
            out.extend((pk, s) for s in shards)
    if not out:
        raise FileNotFoundError(f"no partitions matched include={include} exclude={exclude}")
    return out


def _prompt_messages(messages: list[dict]) -> Optional[list[dict]]:
    """取到第一個 assistant 之前的 messages（system + user 輪）；無 user 則 None。"""
    pre: list[dict] = []
    for m in messages:
        if m.get("role") == "assistant":
            break
        pre.append({"role": m["role"], "content": m.get("content") or ""})
    if not any(m["role"] == "user" for m in pre):
        return None
    return pre


class PromptLoader:
    """串流 L2 prompts，渲染成 student-tokenizer 的 input_ids。"""

    def __init__(self, student_path: str, roots: list[str],
                 include: Optional[list[str]] = None, exclude: Optional[list[str]] = None,
                 max_prompt_tokens: int = 8192, seed: int = 0):
        from transformers import AutoTokenizer

        self.tok = AutoTokenizer.from_pretrained(student_path, trust_remote_code=True)
        self.roots = [Path(r) for r in roots]
        self.include = include or DEFAULT_INCLUDE
        self.exclude = exclude or DEFAULT_EXCLUDE
        self.max_prompt_tokens = max_prompt_tokens
        self.seed = seed
        self.shards = _select_shards(self.roots, self.include, self.exclude)

    def render(self, messages: list[dict]) -> Optional[list[int]]:
        pre = _prompt_messages(messages)
        if pre is None:
            return None
        # 先渲染成字串再 encode（add_special_tokens=False，因 DeepSeek chat template 自帶
        # <｜begin▁of▁sentence｜>），保證拿到 list[int]，避免 tokenize=True 的 BatchEncoding。
        text = self.tok.apply_chat_template(pre, add_generation_prompt=True, tokenize=False)
        ids = self.tok.encode(text, add_special_tokens=False)
        if len(ids) > self.max_prompt_tokens:
            return None   # 過長 prompt 丟（Phase 0 簡單處理；後續可改 cap）
        return ids

    def iter_prompts(self, shuffle: bool = True) -> Iterator[Prompt]:
        import random

        import pyarrow.parquet as pq

        shards = list(self.shards)
        if shuffle:
            random.Random(self.seed).shuffle(shards)
        for pk, path in shards:
            # 直讀單檔（不走 dataset/partitioning 推斷，避免 hive 分區欄與檔內同名實欄衝突）
            tbl = pq.ParquetFile(str(path)).read(columns=["id", "domain", "messages", "meta"])
            for row in tbl.to_pylist():
                try:
                    msgs = json.loads(row["messages"])
                except (TypeError, json.JSONDecodeError):
                    continue
                ids = self.render(msgs)
                if ids is None:
                    continue
                meta = {}
                try:
                    meta = json.loads(row["meta"]) if row.get("meta") else {}
                except json.JSONDecodeError:
                    pass
                yield Prompt(id=row["id"], input_ids=ids, domain=row.get("domain") or pk, meta=meta)


# ============================================================================
# Problem-pool loader（distill_gen/problems/problems.parquet，9,834 題去重 olympiad 證明題）
# ============================================================================
# OPD 實訓用的 prompt 母體：把 problem 文字套 prover template → student chat template → input_ids。
# 與 distill_gen 同的 3 個 prover 風格輪流（多樣性 D11）。template 含 {problem} → 單 user message；
# 不含（imo25）→ template 當 system、problem 當 user turn。**用 .replace 不用 .format**（dsmv2 含
# \boxed{...} 等 literal braces）。

_PROVER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                           "..", "..", "..", "..", "distill_gen", "prompts"))
DEFAULT_TEMPLATE_POOL = ("proofbench_generator", "dsmv2_a1", "imo25_prover")


class ProblemPromptLoader:
    """串流 problems.parquet 的題目，套 prover template、渲染成 student input_ids（token-in-token-out）。"""

    def __init__(self, student_path: str, problems_parquet: str,
                 template_pool: Optional[list[str]] = None, template_dir: str = _PROVER_DIR,
                 max_prompt_tokens: int = 4096, seed: int = 0):
        from transformers import AutoTokenizer

        self.tok = AutoTokenizer.from_pretrained(student_path, trust_remote_code=True)
        self.parquet = problems_parquet
        self.max_prompt_tokens = max_prompt_tokens
        self.seed = seed
        self.pool = list(template_pool or DEFAULT_TEMPLATE_POOL)
        self.templates = {}
        for name in self.pool:
            with open(os.path.join(template_dir, f"{name}.txt"), encoding="utf-8") as f:
                self.templates[name] = f.read()

    def render(self, problem: str, template_name: str) -> Optional[list[int]]:
        text = self.templates[template_name]
        if "{problem}" in text:
            msgs = [{"role": "user", "content": text.replace("{problem}", problem)}]
        else:                                   # imo25：template 當 system、題目當 user turn
            msgs = [{"role": "system", "content": text}, {"role": "user", "content": problem}]
        rendered = self.tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)
        ids = self.tok.encode(rendered, add_special_tokens=False)
        if len(ids) > self.max_prompt_tokens:
            return None
        return ids

    def iter_prompts(self, shuffle: bool = True) -> Iterator[Prompt]:
        import random

        import pyarrow.parquet as pq

        probs = pq.ParquetFile(self.parquet).read(columns=["problem", "origin", "category"]).to_pylist()
        order = list(range(len(probs)))
        if shuffle:
            random.Random(self.seed).shuffle(order)
        for j, i in enumerate(order):
            row = probs[i]
            problem = row.get("problem")
            if not problem:
                continue
            tname = self.pool[(i + self.seed) % len(self.pool)]   # 決定性輪流 template
            ids = self.render(problem, tname)
            if ids is None:
                continue
            yield Prompt(id=f"prob-{i}", input_ids=ids,
                         domain=row.get("category") or row.get("origin") or "proof",
                         meta={"template": tname, "origin": row.get("origin")})


def make_prompt_loader(cfg):
    """依 cfg.prompt_source 回對應 loader（'problems' = distill_gen 題庫；'l2' = L2 messages）。"""
    src = getattr(cfg, "prompt_source", "problems")
    if src == "problems":
        return ProblemPromptLoader(cfg.rollout.model_path, cfg.problems_parquet,
                                   template_pool=list(cfg.prover_template_pool),
                                   seed=int(getattr(cfg, "prompt_seed", 0)))
    return PromptLoader(cfg.rollout.model_path, list(cfg.dataset_roots),
                        seed=int(getattr(cfg, "prompt_seed", 0)))


def _selftest():
    """在真資料上渲染一筆，印出 token 數與 decode 回的 prompt 尾巴（確認 generation prompt）。"""
    from opd.config import STUDENT_PATH, OPDConfig

    cfg = OPDConfig()
    ld = PromptLoader(STUDENT_PATH, list(cfg.dataset_roots))
    print(f"selected partitions/shards: {len(ld.shards)}")
    it = ld.iter_prompts()
    for i, p in enumerate(it):
        tail = ld.tok.decode(p.input_ids[-40:])
        print(f"\n[{p.domain}] id={p.id[:12]} prompt_tokens={len(p.input_ids)}")
        print(f"  尾段 decode: ...{tail!r}")
        if i >= 2:
            break
    print("\nprompts selftest OK")


if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    _selftest()
