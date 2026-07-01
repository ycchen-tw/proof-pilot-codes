# Copyright 2026 proof-pilot. Apache-2.0.
"""把 Trajectory 組成 JSD loss 的輸入 —— position 對齊邏輯（PLAN §6 G4 的核心）。

最尖的刀口：teacher hidden 與 student hidden 必須在**同一個 s_t=(x,y_<t)** 上、預測**同一個下一
token y_t**。對齊定義（與 buffer.Trajectory.target_positions / teacher_service 的 start 一致）：

  trajectory token_ids[0..L-1]，prompt_len = P。
  - 要學的是 generated 段 token_ids[P..L-1]（共 L-P 個 token）。
  - student：hidden[t] 經 head 預測 token_ids[t+1]。所以預測 generated 段的 student position 是
    t = P-1 .. L-2（共 L-P 個），其 hidden 預測 token_ids[P..L-1]。
  - teacher service 以 start=P-1 呼叫 → 回 position [P-1 .. L-1]（L-P+1 個）的 quant hidden；
    取前 L-P 個（[P-1 .. L-2]）即與 student target position 一一對齊。
  - labels[i] = token_ids[P+i]，i=0..L-P-1。student_pos[i]=P-1+i，teacher_pos[i]=P-1+i（同一絕對
    position），兩者 hidden 都預測 labels[i]。

所以三者（student hidden 切片、teacher hidden 切片、labels）逐 i 對齊。off-by-one 就是 G4 要抓的。
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field

import torch

from opd.buffer import Trajectory
from opd.config import HID_DIM

# 重用 olmo3_sink 的 packing（Example/greedy_pack/pack_to_tensors）——repo 根目錄可 import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))
from olmo3_sink.sft_data import Example, greedy_pack, pack_to_tensors  # noqa: E402

PACKED_ROW_BYTES = HID_DIM * 6 // 8
SCALE_ROW_BYTES = (HID_DIM // 32) * 2
TOP1_ROW_BYTES = 4


@dataclass
class AssembledTraj:
    input_ids: torch.Tensor       # [1, L]  餵 student model.model 的完整序列
    student_pos: torch.Tensor     # [n_t]   要取 student hidden 的 position（= P-1 .. L-2）
    labels: torch.Tensor          # [n_t]   generated next-token（= token_ids[P..L-1]）
    teacher_keep: int             # n_t：teacher hidden 取前幾個（service 多回了最後一格）

    @property
    def n_targets(self) -> int:
        return self.labels.numel()


def _slice_rows(blob: bytes | None, row_bytes: int, start: int, n_rows: int,
                name: str) -> bytes | None:
    if blob is None:
        return None
    a = start * row_bytes
    b = (start + n_rows) * row_bytes
    if b > len(blob):
        raise ValueError(f"{name} too short for row slice: need end={b} bytes, have={len(blob)}")
    return blob[a:b]


def window_trajectory(traj: Trajectory, micro_len: int, context_tokens: int = 4096,
                      target_tokens: int | None = None) -> list[Trajectory]:
    """Split an oversized scored trajectory into trainable target windows.

    The teacher service scored the full sequence from absolute position P-1, so row
    k in teacher bytes corresponds to original position P-1+k. Each returned window
    keeps enough left context for the student forward, slices teacher rows to the
    window target range, and preserves absolute RoPE positions via `position_offset`.
    """
    L, P = len(traj.token_ids), traj.prompt_len
    gen_len = L - P
    if gen_len <= 0:
        return []
    if not traj.scored():
        raise ValueError("window_trajectory() requires a scored trajectory")
    seq_len = traj.teacher_seq_len if traj.teacher_seq_len is not None else gen_len + 1
    if seq_len != gen_len + 1:
        raise ValueError(f"teacher seq_len mismatch: got={seq_len} expected={gen_len + 1}")
    if L <= micro_len:
        return [traj]

    context_tokens = max(1, min(context_tokens, micro_len - 1))
    if target_tokens is None:
        target_tokens = micro_len - context_tokens
    target_tokens = max(1, min(target_tokens, micro_len - 1))

    out: list[Trajectory] = []
    target_start = P
    while target_start < L:
        context_start = 0 if target_start == P else max(0, target_start - context_tokens)
        local_prompt = target_start - context_start
        if local_prompt >= micro_len:
            context_start = target_start - (micro_len - 1)
            local_prompt = micro_len - 1
        n_t = min(target_tokens, micro_len - local_prompt, L - target_start)
        if n_t <= 0:
            break
        target_end = target_start + n_t
        row_start = target_start - P
        rows = n_t + 1
        meta = dict(traj.meta)
        meta.update({
            "windowed_from_len": L,
            "window_context_start": context_start,
            "window_target_start": target_start,
            "window_target_end": target_end,
        })
        out.append(Trajectory(
            token_ids=traj.token_ids[context_start:target_end],
            prompt_len=local_prompt,
            weight_version=traj.weight_version,
            teacher_packed=_slice_rows(traj.teacher_packed, PACKED_ROW_BYTES, row_start, rows,
                                       "teacher_packed"),
            teacher_scales=_slice_rows(traj.teacher_scales, SCALE_ROW_BYTES, row_start, rows,
                                       "teacher_scales"),
            teacher_seq_len=rows,
            teacher_top1=_slice_rows(traj.teacher_top1, TOP1_ROW_BYTES, row_start, rows,
                                     "teacher_top1"),
            position_offset=traj.position_offset + context_start,
            meta=meta,
        ))
        target_start = target_end
    return out


def assemble(traj: Trajectory, device: str = "cpu") -> AssembledTraj:
    """從一條 trajectory 算出對齊用的 index/labels（不碰 teacher bytes；decode 在 trainer 端做）。"""
    L = len(traj.token_ids)
    P = traj.prompt_len
    n_t = L - P
    if n_t <= 0:
        raise ValueError(f"trajectory 無 generated token：L={L} P={P}")
    ids = torch.tensor(traj.token_ids, device=device)
    student_pos = torch.arange(P - 1, L - 1, device=device)   # [n_t]
    labels = ids[P:L]                                          # [n_t]
    assert student_pos.numel() == n_t == labels.numel()
    return AssembledTraj(
        input_ids=ids.view(1, L),
        student_pos=student_pos,
        labels=labels,
        teacher_keep=n_t,           # service 以 start=P-1 回 L-P+1 格，取前 n_t 個
    )


def slice_teacher_hidden(decoded_hidden: torch.Tensor, a: AssembledTraj) -> torch.Tensor:
    """teacher service 回的 hidden（position [P-1 .. L-1]，L-P+1 格）取前 n_t 格對齊 student。"""
    if decoded_hidden.shape[0] < a.teacher_keep:
        raise ValueError(f"teacher hidden 太短：{decoded_hidden.shape[0]} < {a.teacher_keep}")
    return decoded_hidden[: a.teacher_keep]


# ---- seq packing（重用 olmo3_sink；TRAINER_DESIGN §7c）----
@dataclass
class Segment:
    """packed bin 裡的一條 trajectory，帶絕對 index 對齊資訊（G4）。"""
    off: int                       # 段在 bin 中的起始絕對 index
    prompt_len: int
    n_t: int                       # = L - P（generated token 數）
    student_pos: torch.Tensor      # [n_t] 絕對 index = off + (P-1 .. L-2)
    labels: torch.Tensor           # [n_t] = token_ids[P:L]（generated next-token）
    teacher_packed: bytes
    teacher_scales: bytes
    teacher_seq_len: int | None = None
    teacher_top1: bytes | None = None
    position_offset: int = 0


@dataclass
class PackedBin:
    tensors: dict                  # pack_to_tensors 產出：input_ids/position_ids/cu_seq_lens_q/k/max_length_q/k [+labels/n_docs]
    segments: list[Segment] = field(default_factory=list)

    @property
    def total_targets(self) -> int:
        return sum(s.n_t for s in self.segments)


def pack_trajectories(trajs: list[Trajectory], micro_len: int, pad_id: int,
                      max_segs: int | None = None, device: str = "cpu") -> list[PackedBin]:
    """FFD pack trajectory → micro_len bins（reuse olmo3_sink greedy_pack/pack_to_tensors），
    每段附 (off, student_pos 絕對 index, labels, teacher bytes)。

    contract：pack_to_tensors 依 bin_ 的 Example 順序串接，offset = 前面段長度的 cumsum——與
    greedy_pack 回傳的每個 bin 內 Example 順序一致，故段偏移可重建（G4 對齊）。長度 > micro_len 或
    無 generated（L<=P）的 trajectory 被丟（greedy_pack 丟過長、這裡先濾 L<=P）。
    """
    usable = [t for t in trajs if len(t.token_ids) > t.prompt_len and t.scored()]
    examples = [Example(input_ids=list(t.token_ids), prompt_len=t.prompt_len) for t in usable]
    ex2traj = {id(e): t for e, t in zip(examples, usable)}
    out: list[PackedBin] = []
    for bin_ in greedy_pack(examples, micro_len):
        tens = pack_to_tensors(bin_, micro_len, pad_id, device, max_segs)
        segs: list[Segment] = []
        off = 0
        for e in bin_:
            t = ex2traj[id(e)]
            P, L = t.prompt_len, len(t.token_ids)
            n_t = L - P
            tens["position_ids"][0, off:off + L] = torch.arange(
                t.position_offset, t.position_offset + L, device=device)
            segs.append(Segment(
                off=off, prompt_len=P, n_t=n_t,
                student_pos=torch.arange(off + P - 1, off + L - 1, device=device),
                labels=torch.tensor(t.token_ids[P:L], device=device),
                teacher_packed=t.teacher_packed, teacher_scales=t.teacher_scales,
                teacher_seq_len=t.teacher_seq_len,
                teacher_top1=t.teacher_top1,
                position_offset=t.position_offset,
            ))
            off += L
        out.append(PackedBin(tensors=tens, segments=segs))
    return out
