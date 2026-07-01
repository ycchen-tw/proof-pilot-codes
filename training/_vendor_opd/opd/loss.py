# Copyright 2026 proof-pilot. Apache-2.0.
"""OPD full-vocab 散度 loss —— Liger fused-linear JSD(β)（PLAN §1/§2，D2/D3）。

GKD 直接可微散度（非 PPO/IS）：在 student-rollout 的每個 generated position 上，最小化
`D_JSD(β)(π_T ‖ π_θ)`。用 `LigerFusedLinearJSDFunction` 逐 token chunk 重建兩邊 logits、kernel 內
算散度，**不 materialize [BT,V]**（已在 distill/_liger_jsd_test 驗過數值）。

OPD 是純蒸餾（teacher 分布即 target，無 ground-truth label）：weight_hard(CE)=0、weight_soft=1。
labels 只用來做 ignore 遮罩——prompt/pad position 設 IGNORE 跳過，generated position 給其 next-token
（值不進 loss，只標「要算」）。Liger 的 mean reduction 即 length-normalized（D8）。

輸入（trainer 端組好；teacher hidden 是 codec.decode 的旋轉空間值，配 W_rot）：
  student_hidden     [BT, H_s]   student 在 generated position 的 hidden
  student_head_w     [V, H_s]    student lm_head.weight
  teacher_hidden_rot [BT, H_t]   decode(quant) 旋轉空間 hidden
  w_rot              [V, H_t]    fold_head(teacher head)（旋轉空間）
  labels             [BT]        generated next-token id；masked 位置 = IGNORE

β：0=forward KL（mode-covering），0.5=JSD，1=reverse KL（mode-seeking，canonical OPD）。
"""
from __future__ import annotations

import torch

from liger_kernel.chunked_loss.jsd_loss import LigerFusedLinearJSDFunction

IGNORE = -100


def opd_jsd_loss(student_hidden: torch.Tensor, student_head_w: torch.Tensor,
                 teacher_hidden_rot: torch.Tensor, w_rot: torch.Tensor,
                 labels: torch.Tensor, beta: float = 0.5, temperature: float = 1.0,
                 chunk_size: int = 1024, compiled: bool = False) -> torch.Tensor:
    # compiled=False：BT（target 數）每 bin 都不同 → dynamo 每步重編 + 第三次編譯撞
    # produce_guards IndexError（torch dynamic-shape bug，mnlong1 step1 全 rank 炸）。
    # eager chunked 慢一點但 shape 免疫。
    """純蒸餾 full-vocab JSD(β)，length-normalized scalar。

    arg 次序對齊 distill/_liger_jsd_test：
      apply(x_s, w_s, x_t, w_t, labels, bias_s, bias_t, w_hard, w_soft, beta,
            ignore_index, temperature, compiled, chunk_size, <accum bool>)
    """
    return LigerFusedLinearJSDFunction.apply(
        student_hidden, student_head_w, teacher_hidden_rot, w_rot, labels,
        None, None, 0.0, 1.0, beta, IGNORE, temperature, compiled, chunk_size, False,
    )


class OPDLoss:
    """握著 LossCfg 的薄 wrapper。"""

    def __init__(self, beta: float = 0.5, temperature: float = 1.0, chunk_size: int = 1024):
        self.beta = beta
        self.temperature = temperature
        self.chunk_size = chunk_size

    def __call__(self, student_hidden, student_head_w, teacher_hidden_rot, w_rot, labels):
        return opd_jsd_loss(student_hidden, student_head_w, teacher_hidden_rot, w_rot, labels,
                            beta=self.beta, temperature=self.temperature,
                            chunk_size=self.chunk_size)
