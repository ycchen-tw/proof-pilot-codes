# Copyright 2026 proof-pilot. Apache-2.0.
"""量化 teacher hidden 的 codec —— 轉發 `distill/hidden_codec`（had+int6_blk32，3328 B/tok）。

沿用 v1 `opd/src/opd/codec.py`（已驗證 G2/G3）：teacher 端 `encode()` 把 post-norm last-hidden
`[L,4096]` 壓成 had+int6；trainer 端 `decode()` 回**旋轉空間** hidden，配預摺 teacher head `W_rot`
（`build_w_rot()`），`decode(packed) @ W_rotᵀ == h @ Wᵀ`（差 int6 噪音）。旋轉永不在 hot path 跑 inverse。
"""
from __future__ import annotations

import json
import os
import sys

import torch

# distill 是 training/ 下的 sibling（無 __init__）：把它的目錄加進 path。
# codec.py 在 training/opd_v2/src/opd_v2/ → 上溯 3 層到 training/，再進 distill/。
_COMMON = os.path.join(os.path.dirname(__file__), "..", "..", "..", "_common")
sys.path.insert(0, os.path.abspath(_COMMON))
from hidden_codec import BLOCK, ROT_SEED, Rotator, decode, encode  # noqa: E402

__all__ = ["BLOCK", "ROT_SEED", "Rotator", "encode", "decode", "build_w_rot", "load_teacher_head"]


def load_teacher_head(model_path: str, hid: int, device: str = "cpu") -> torch.Tensor:
    """從 teacher HF shards 載 `head.weight` bf16 `[V, hid]`。"""
    from safetensors import safe_open

    idx = json.load(open(f"{model_path}/model.safetensors.index.json"))["weight_map"]
    with safe_open(f"{model_path}/{idx['head.weight']}", framework="pt", device="cpu") as f:
        w = f.get_tensor("head.weight")
    assert w.dtype == torch.bfloat16 and w.shape[1] == hid, (w.dtype, tuple(w.shape))
    return w.to(device)


def build_w_rot(model_path: str, hid: int, device: str = "cpu",
                seed: int = ROT_SEED) -> tuple[torch.Tensor, Rotator]:
    """回 (W_rot [V, hid] bf16, rotator)。trainer 啟動時呼叫一次、常駐 W_rot。"""
    rot = Rotator(hid, device=device, seed=seed)
    head = load_teacher_head(model_path, hid, device=device)
    w_rot = rot.fold_head(head)
    return w_rot, rot
