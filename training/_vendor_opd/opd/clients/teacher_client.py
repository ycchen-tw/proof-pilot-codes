# Copyright 2026 proof-pilot. Apache-2.0.
"""Teacher scoring service 的 client（PLAN §4）。

`score(input_ids, start)` -> 回 (packed_bytes, scales_bytes, seq_len)；trainer 端用
`opd.codec.decode` + 常駐 `W_rot` 重建 teacher logits。bytes 直存進 Trajectory（不在 client 端
decode 成 tensor，省記憶體；trainer 取 batch 時才 decode 到 GPU）。
"""
from __future__ import annotations

import numpy as np
import torch

from opd.config import HID_DIM


class TeacherClient:
    def __init__(self, base_url: str, timeout: float = 600.0):
        import httpx
        self.base = base_url.rstrip("/")
        self._c = httpx.Client(timeout=timeout)

    def health(self) -> dict:
        return self._c.get(f"{self.base}/health").json()

    def score(self, input_ids: list[int], start: int = 0, return_top1: bool = False):
        """回 (packed_bytes, scales_bytes, seq_len)，可選附 int32 teacher top1 bytes。

        `return_top1=True` 時新版 teacher 會在 scales 後追加 `seq_len` 個 int32 argmax id，回
        (packed_bytes, scales_bytes, seq_len, top1_bytes)。舊 teacher 沒有 header 時 top1_bytes=None。
        """
        payload = {"input_ids": input_ids, "start": start}
        if return_top1:
            payload["return_top1"] = True
        r = self._c.post(f"{self.base}/score", json=payload)
        r.raise_for_status()
        seq = int(r.headers["X-Seq-Len"])
        npk = int(r.headers["X-Packed-Bytes"])
        ntop = int(r.headers.get("X-Top1-Bytes", "0"))
        if ntop:
            if ntop != seq * 4:
                raise RuntimeError(f"teacher top1 byte length mismatch: got={ntop} expected={seq * 4}")
            return r.content[:npk], r.content[npk:-ntop], seq, r.content[-ntop:]
        if return_top1:
            return r.content[:npk], r.content[npk:], seq, None
        return r.content[:npk], r.content[npk:], seq


def decode_teacher_hidden(packed_bytes: bytes, scales_bytes: bytes, seq_len: int,
                          device: str = "cuda", hid: int = HID_DIM) -> torch.Tensor:
    """bytes -> 旋轉空間 bf16 hidden [seq_len, hid]（配 trainer 的 W_rot 用）。"""
    from opd.codec import decode
    pcols = hid * 6 // 8
    scols = hid // 32
    packed = torch.from_numpy(
        np.frombuffer(packed_bytes, dtype=np.uint8).reshape(seq_len, pcols).copy())
    scales = torch.from_numpy(
        np.frombuffer(scales_bytes, dtype=np.float16).reshape(seq_len, scols).copy())
    return decode(packed.to(device), scales.to(device))


def decode_teacher_top1(top1_bytes: bytes, seq_len: int, device: str = "cuda") -> torch.Tensor:
    """int32 bytes -> int64 token ids [seq_len]。"""
    top1 = torch.from_numpy(np.frombuffer(top1_bytes, dtype=np.int32).reshape(seq_len).copy())
    return top1.to(device=device, dtype=torch.long)
