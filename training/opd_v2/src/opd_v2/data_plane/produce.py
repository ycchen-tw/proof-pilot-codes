# Copyright 2026 proof-pilot. Apache-2.0.
"""produce_sample atom —— 「一條 rollout + 一次 teacher score」= 一個獨立 async coroutine（V3）。

這是使用者要的「優雅設計」核心（PLAN §5）：
- **完全獨立**：不依賴其它任務；唯一共享 = 兩個 pool 的 semaphore + 輸出 buffer。
- **一條跑完就立刻丟 teacher**（不等同 prompt 其它 sample）→ 消滅 v1「等最慢條 gate 整組」（P3/P4）。
- **早完成早入 buffer** → 降 staleness。
- **回 handle 不回 bytes**（teacher server-side 寫 FS）→ buffer/scatter 超輕（P7 修正）。

N sample = N 個獨立 atom（`fan_out`，V1）。任一步失敗 → 回 None（scheduler 計 fail、清半寫檔）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from opd_v2.buffer import ScoredTrajectory
from opd_v2.config import OPDConfig
from opd_v2.data_plane.pools import Pool
from opd_v2.hidden_store import HiddenStore


@dataclass
class Prompt:
    ids: list[int]               # 已 render+tokenize 的 prompt token ids
    meta: dict = field(default_factory=dict)


@dataclass
class ProduceResult:
    """produce_sample 的結果（V33）。把「成功 / admission-drop / fail」三態講清楚，讓 scheduler
    既能對【所有】生成記 finish_reason（EOS/length 生成端比例監控不破），又能把「刻意剔除」
    與「出錯」分開計數。
    - traj：成功 score 且通過 admission → ScoredTrajectory；否則 None。
    - finish_reason：一律帶回（即使 drop/fail），供生成端 eos/length 比例監控。
    - drop_reason：被 admission filter 主動剔除的標籤（如 "length"）；"" = 未被剔除。
      drop ≠ fail：drop 是「有效生成、刻意不訓練」，fail 是「生成/score 出錯」。
    """
    traj: ScoredTrajectory | None = None
    finish_reason: str = ""
    drop_reason: str = ""


def _admission_drop(finish_reason: str, drop_finish_reasons) -> str:
    """training-buffer 進入策略（純函式、好單測、好擴充）。回被剔除的標籤；"" = 收下。

    目前規則：finish_reason ∈ drop_finish_reasons（預設 {"length"}：撞窗口截斷 = OPD self-amplification
    主來源）就剔除。不碰 rollout 取樣分佈——只決定哪些 on-policy 樣本進梯度（rejection filter）。
    擴充點：未來要加「token-level 循環偵測」時，這裡多收 ids/prompt_len 參數、命中回 "loop" 即可，
    上游 produce/scheduler/wandb 的計數管線無需改（drop_reason 是自由字串）。
    """
    if finish_reason in drop_finish_reasons:
        return finish_reason
    return ""


async def produce_sample(prompt: Prompt, *, rollout_pool: Pool, teacher_pool: Pool,
                         store: HiddenStore, cfg: OPDConfig,
                         default_wv: Callable[[], int], dump=None, pool_ingest=None
                         ) -> ProduceResult:
    """一條 rollout + 一次 teacher score。回 ProduceResult（三態：成功 traj / admission-drop / fail）。

    `dump`（RolloutDumpWriter | None）：若給，rollout 一生成（teacher score 前）就把 ids 旁路落盤 →
    連 teacher 失敗 / 之後被 buffer 擠掉 / GC 的 rollout 也存得到（rollout_store.py）。
    `pool_ingest`（agentic.PoolIngestor | None）：agentic 模式才給；rollout 一生成（teacher 前）就把該條
    write-back 到 artifact pool（parse answer-only、validity-gate）→ 下游 role 的 context。與 teacher 成敗
    無關（同 dump 的位置）；非阻塞 enqueue。
    """
    rc = cfg.rollout
    plen = len(prompt.ids)
    # gen budget = 整個剩餘窗口（max_traj_tokens - prompt），上限再被 cfg.max_new_tokens 壓一次。
    # 這樣 proof 能用滿窗口生完，又不會 request 超過 context（prompt+gen ≤ max_traj_tokens）。
    budget = cfg.data_plane.max_traj_tokens - plen
    if budget <= 0:                            # prompt 本身就超過窗口 → 沒得生
        return ProduceResult()
    max_new = min(rc.max_new_tokens, budget)
    # 1) 一條 rollout（一個 request、無 n、直接讀 output_ids）
    try:
        async with rollout_pool.slot() as client:
            gen_ids, wv, finish_reason = await client.generate_one(
                prompt.ids, temperature=rc.temperature, top_p=rc.top_p, top_k=rc.top_k,
                max_new_tokens=max_new, ignore_eos=rc.ignore_eos, timeout=rc.gen_timeout_s)
    except Exception:
        return ProduceResult()                 # 生成出錯（finish_reason 未知）→ fail
    if not gen_ids:
        return ProduceResult(finish_reason=finish_reason)

    full = prompt.ids + list(gen_ids)
    if len(full) > cfg.data_plane.max_traj_tokens:
        full = full[: cfg.data_plane.max_traj_tokens]
    if len(full) <= plen:                      # 截斷後沒剩 generated token → 沒得學
        return ProduceResult(finish_reason=finish_reason)
    wv = wv if wv is not None else int(default_wv())

    # 1b) rollout 一生成就落盤（teacher score 前）→ 存「所有」rollouts（含被 drop 的），脫鉤 teacher/buffer/GC
    if dump is not None:
        dump.append(full, plen, wv, {**prompt.meta, "finish_reason": finish_reason})

    # 1c) admission filter：撞窗口截斷等的不進訓練（teacher 前 → 省 hidden 寫盤；不碰取樣分佈）。
    #     仍回 finish_reason 供生成端比例監控；drop_reason 讓 scheduler 與 wandb 獨立計數（≠ fail）。
    drop = _admission_drop(finish_reason, rc.drop_finish_reasons)
    if drop:
        return ProduceResult(finish_reason=finish_reason, drop_reason=drop)

    # 1d) agentic：把該條 write-back 到 artifact pool（teacher 前；parse answer-only + validity-gate；非阻塞）
    if pool_ingest is not None:
        pool_ingest.append(full, plen, wv, prompt.meta, finish_reason)

    # 2) 跑完就立刻丟 teacher（不等同 prompt 其它 sample）；teacher server-side 寫 FS、回 handle
    out_path = store.new_path()
    try:
        async with teacher_pool.slot() as client:
            handle = await client.score(full, start=plen - 1, out_path=out_path, wv=wv)
    except Exception:
        store.delete(out_path)                 # teacher 可能半寫 → 清掉
        return ProduceResult(finish_reason=finish_reason)

    return ProduceResult(
        traj=ScoredTrajectory(ids=full, prompt_len=plen, wv=wv, handle=handle,
                              meta=dict(prompt.meta), finish_reason=finish_reason or ""),
        finish_reason=finish_reason or "")


def fan_out(prompt: Prompt, n: int) -> list[Prompt]:
    """N sample = N 個獨立 atom 的 input（同題、各自獨立、各自完成、各自入 buffer，V1）。"""
    return [prompt] * n
