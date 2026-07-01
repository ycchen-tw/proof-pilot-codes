# Copyright 2026 proof-pilot. Apache-2.0.
"""量化 teacher hidden 的 codec —— 直接重用 distill/hidden_codec（had+int6_blk32）。

OPD 的 wire 格式：teacher service 把 post-norm last-hidden `[L, 4096]` 用 `encode()` 壓成
`had+int6`（3328 B/tok），trainer 端 `decode()` 回**旋轉空間** hidden，配上預摺好的 teacher head
`W_rot`（`build_w_rot()`），`decode(packed) @ W_rotᵀ == h @ Wᵀ`（差 int6 噪音）。旋轉永不在 hot
path 跑 inverse（見 hidden_codec.py 頂部說明）。

這個檔只做兩件事：(1) 轉發 distill 的 Rotator/encode/decode；(2) 提供從 teacher safetensors 載
`head.weight` 並摺成 `W_rot` 的 helper（trainer 常駐這顆 1.06 GB bf16）。
"""
from __future__ import annotations

import json
import os
import sys

import torch

# distill 是 training/ 下的 sibling，無 __init__ 套件化 -> 直接把它的目錄加進 path。
_DISTILL = os.path.join(os.path.dirname(__file__), "..", "..", "..", "distill")
sys.path.insert(0, os.path.abspath(_DISTILL))
from hidden_codec import BLOCK, ROT_SEED, Rotator, decode, encode  # noqa: E402

__all__ = ["BLOCK", "ROT_SEED", "Rotator", "encode", "decode", "build_w_rot", "load_teacher_head"]


def load_teacher_head(model_path: str, hid: int, device: str = "cpu") -> torch.Tensor:
    """從 teacher HF shards 載 `head.weight` bf16 `[V, hid]`（與 _validate_hidden.py 同法）。"""
    from safetensors import safe_open

    idx = json.load(open(f"{model_path}/model.safetensors.index.json"))["weight_map"]
    with safe_open(f"{model_path}/{idx['head.weight']}", framework="pt", device="cpu") as f:
        w = f.get_tensor("head.weight")
    assert w.dtype == torch.bfloat16 and w.shape[1] == hid, (w.dtype, tuple(w.shape))
    return w.to(device)


def build_w_rot(model_path: str, hid: int, device: str = "cpu",
                seed: int = ROT_SEED) -> tuple[torch.Tensor, Rotator]:
    """回 (W_rot [V, hid] bf16, rotator)。trainer 啟動時呼叫一次、常駐 W_rot。

    `W_rot = fold_head(head.weight)`，之後 `decode(packed,scales) @ W_rotᵀ` 直接是 teacher
    logits（旋轉空間 hidden × 旋轉空間 head，旋轉抵銷）。rotator 給 teacher service 端 encode 用。
    """
    rot = Rotator(hid, device=device, seed=seed)
    head = load_teacher_head(model_path, hid, device=device)
    w_rot = rot.fold_head(head)  # [V, hid], same dtype as head (bf16)
    return w_rot, rot
