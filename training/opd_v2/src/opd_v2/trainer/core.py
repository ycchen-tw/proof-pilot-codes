# Copyright 2026 proof-pilot. Apache-2.0.
"""OPD v2 trainer core: HSDP model build + clean single-layer forward wrapper + one train step.

Design (see ../../README.md):
- One clean forward wrapper: backbone hidden -> gather target positions -> repo chunked
  `fused_linear_jsd_fp32_softmax` (from ../_common, not Liger). No layered monkeypatch.
- Whole trajectory, no windowing: each traj fills one bin, per-traj RoPE position reset.
- Exactly one bin per rank per step (rank-0 LPT balances the flat batch into `world` bins of
  <= micro_batch_tokens each) so every rank runs the same number of forwards -> FSDP
  collectives never desync; empty ranks run a dummy forward.
- Teacher hidden read from shared FS (owning-rank lazy read via handle), decoded + W_rot.
- Collective-safe gate: after reading, all ranks all_reduce(min, ok); any failure -> all skip.
"""
from __future__ import annotations

import os
import sys
import types

import torch
import torch.nn.functional as F

# ---- sys.path：把要重用的 sibling 套件掛上 ----
_THIS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(_THIS, "..", "..", "..", "..", ".."))
for _p in (
    REPO,
    f"{REPO}/training/stage1_v2/src",
    f"{REPO}/training/_vendor_opd",
    f"{REPO}/training/_common",
    os.path.abspath(os.path.join(_THIS, "..", "..")),   # opd_v2/src
):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from train import build_model, load_resume, save_consolidated, save_resume, setup_parallelism  # noqa: E402
from jsd_kernel import fused_linear_jsd_fp32_softmax  # noqa: E402
from opd.batch import PackedBin, pack_trajectories  # noqa: E402
from opd.buffer import Trajectory  # noqa: E402
from opd.clients.teacher_client import decode_teacher_hidden  # noqa: E402

from opd_v2.codec import build_w_rot  # noqa: E402
from opd_v2.config import EOS_ID, HID_DIM, PAD_ID, OPDConfig  # noqa: E402
from opd_v2.hidden_store import read_hidden  # noqa: E402

IGNORE = -100


# ---------------------------------------------------------------------------
# forward wrapper（V28/V26）
# ---------------------------------------------------------------------------
def opd_v2_forward(self, input_ids, position_ids, cu_seq_lens_q, cu_seq_lens_k,
                   max_length_q, max_length_k, opd_student_pos, opd_teacher_hidden,
                   opd_labels, opd_w_rot, opd_chunk_size,
                   opd_tok_weight=None, opd_seg_lens=None):
    """裝進 model.forward：FSDP root unshard region 內算 full-vocab chunked JSD。回 scalar loss。

    bf16 GEMM + 強制 fp32 log-softmax/KL（jsd_kernel 內），不 materialize [BT,V]（soft_v2 驗 rel 1.9e-5）。
    opd_student_pos 為空（dummy/空 rank）時：sh=[0,H]、kernel loop 0 次 → loss 0、grad 0，但 backbone
    forward 照常觸發 collective（維持 rank 間一致）。

    V34：傳 skew_alpha / fkl_lambda / routing 閾值 + per-token `opd_tok_weight`（clean-EOS reweight）給
    kernel；diag 在 head + EOS-region 兩處取樣（後者用 opd_seg_lens 切 per-traj 尾段，補上 length 自我放大的
    leading indicator）。所有 V34 旋鈕預設值 → kernel 行為 bit-identical 回 β OPD。
    """
    h = self.model(
        input_ids=input_ids, position_ids=position_ids,
        cu_seq_lens_q=cu_seq_lens_q, cu_seq_lens_k=cu_seq_lens_k,
        max_length_q=max_length_q, max_length_k=max_length_k,
    ).last_hidden_state                              # [1, L, H]
    sh = h[0, opd_student_pos]                        # [BT, H]
    # learning-quality diagnostics（entropy/雙向 KL/teacher-nll + EOS-region）：no_grad、capped、reuse sh
    # （不重跑 backbone），只多小 GEMM。由 train_step 設 self._opd_diag（want_g4 且 rank0 時）。
    if getattr(self, "_opd_diag", False) and opd_student_pos.numel() > 0:
        self._diag_out = _compute_diag(sh, self.lm_head.weight, opd_teacher_hidden,
                                       opd_w_rot, opd_labels, self._opd_temp)
        if opd_seg_lens:
            self._diag_out.update(_compute_eos_diag(
                sh, self.lm_head.weight, opd_teacher_hidden, opd_w_rot, opd_seg_lens,
                self._opd_eos_id, int(self._opd_eos_region_n), self._opd_temp))
    return fused_linear_jsd_fp32_softmax(
        sh.bfloat16(), self.lm_head.weight.bfloat16(),
        opd_teacher_hidden.bfloat16(), opd_w_rot.bfloat16(), opd_labels,
        weight_hard_loss=self._opd_hard, weight_soft_loss=self._opd_soft,
        beta=self._opd_beta, ignore_index=IGNORE, temperature=self._opd_temp,
        compiled=False, chunk_size=int(opd_chunk_size),
        compute_ce_loss=self._opd_hard != 0.0,
        tok_weight=opd_tok_weight,
        skew_alpha=self._opd_skew_alpha, fkl_lambda=self._opd_fkl_lambda,
        fkl_top_k=self._opd_fkl_top_k,
        route_high_ent_nats=self._opd_route[0], route_oc_hs_nats=self._opd_route[1],
        route_oc_js=self._opd_route[2], route_outlier_nll=self._opd_route[3],
        base_outlier_down=self._opd_route[4],
    )


@torch.no_grad()
def _compute_diag(sh, lm_w, th, w_rot, labels, temp, cap: int = 512) -> dict:
    """OPD 學習品質診斷（no_grad、capped 前 cap 個 target）。reuse 已算好的 student hidden `sh`。

    回 per-valid-token 平均：student_entropy（↓=entropy collapse 警訊，β=1 主要 failure mode）、
    reverse_kl=KL(student‖teacher)（OPD 目標、應↓）、forward_kl=KL(teacher‖student)（升而 reverse 降
    = mode-dropping）、teacher_nll（teacher 對 student 實抽 token 的 -logprob）。
    """
    n = min(sh.shape[0], cap)
    if n == 0:
        return {}
    s = sh[:n].float()
    t = th[:n].float()
    lab = labels[:n]
    s_logits = s @ lm_w.float().T
    t_logits = t @ w_rot.float().T
    if temp != 1.0:
        s_logits = s_logits / temp
        t_logits = t_logits / temp
    s_lp = F.log_softmax(s_logits, dim=-1)
    t_lp = F.log_softmax(t_logits, dim=-1)
    s_p = s_lp.exp()
    t_p = t_lp.exp()
    mask = (lab != IGNORE).float()
    nv = mask.sum().clamp_min(1.0)
    ent = -(s_p * s_lp).sum(-1)
    rkl = (s_p * (s_lp - t_lp)).sum(-1)
    fkl = (t_p * (t_lp - s_lp)).sum(-1)
    tnll = -t_lp.gather(-1, lab.clamp_min(0).unsqueeze(-1)).squeeze(-1)

    def _m(x):
        return float((x * mask).sum().item() / nv.item())
    return {"entropy": _m(ent), "reverse_kl": _m(rkl), "forward_kl": _m(fkl),
            "teacher_nll": _m(tnll), "n": int(nv.item())}


@torch.no_grad()
def _compute_eos_diag(sh, lm_w, th, w_rot, seg_lens, eos_id, n_tail, temp, cap: int = 512) -> dict:
    """EOS-region 診斷（DEEP_REVIEW §A1 / V34 §2）：取每條 traj **尾段** n_tail token（總列 cap），算
    student 對 EOS 的機率質量、teacher 對 EOS 的 -logp、尾段 entropy gap —— length 自我放大的 leading
    indicator（in-loop 既有 diag 只看 largest-first pack 的開頭，永遠看不到 EOS region）。

    sh/th 的列序 = segment 串接（cu_seqlens 對齊），seg_lens 是各 seg 的 target 列數 → 切尾段。
    student_eos_prob ↓ / teacher_eos_nll↓-while-student-flat = 學不會收尾的早期警訊。
    """
    rows_s, rows_t, off, used = [], [], 0, 0
    for L in seg_lens:
        if used >= cap:
            break
        take = min(int(n_tail), int(L), cap - used)
        if take > 0:
            rows_s.append(sh[off + L - take: off + L])
            rows_t.append(th[off + L - take: off + L])
            used += take
        off += int(L)
    if not rows_s:
        return {}
    s = torch.cat(rows_s).float()
    t = torch.cat(rows_t).float()
    s_logits = s @ lm_w.float().T
    t_logits = t @ w_rot.float().T
    if temp != 1.0:
        s_logits = s_logits / temp
        t_logits = t_logits / temp
    s_lp = F.log_softmax(s_logits, dim=-1)
    t_lp = F.log_softmax(t_logits, dim=-1)
    s_ent = -(s_lp.exp() * s_lp).sum(-1).mean()
    t_ent = -(t_lp.exp() * t_lp).sum(-1).mean()
    return {"eos_student_prob": float(s_lp[:, eos_id].exp().mean().item()),
            "eos_teacher_nll": float((-t_lp[:, eos_id]).mean().item()),
            "tail_entropy_gap": float((s_ent - t_ent).item()), "eos_n": used}


def _detect_trailing_loop(ids: list[int], period_max: int, min_repeats: int) -> "int | None":
    """偵測序列尾端的 verbatim 週期循環（catch loop / digit-runaway）。回退化區間的**起始 index**；無→None。

    對每個週期 p≤period_max，數尾端連續重複 p-block 的次數；≥min_repeats 即判定，回 n−reps·p（最早起點）。
    純 python list（在 token-id 上跑、cheap）；只在 tail_loop_mask 開時呼叫。
    """
    n = len(ids)
    best = None
    for p in range(1, min(int(period_max), n // max(1, int(min_repeats))) + 1):
        block = ids[n - p:]
        reps = 1
        while (reps + 1) * p <= n and ids[n - (reps + 1) * p: n - reps * p] == block:
            reps += 1
        if reps >= min_repeats:
            start = n - reps * p
            if best is None or start < best:
                best = start
    return best


def _v34_tail_weights(seg_labels, lc, eos_id):
    """V34 訓練端尾段處理（on-policy 安全，用 seg.labels=generated token-ids 算）。回 (labels, weight|None)。

    - tail_loop_mask：退化週期尾段的 label→IGNORE（真排除，連 num_valid 一起；取代 produce 端 whole-traj
      drop → 保留長解的好 body，DEEP_REVIEW §B1）。
    - clean_eos_reweight：traj 尾 label==eos（乾淨收尾）→ 尾段 K token 的 soft loss ×(1+λ)，明確教收尾。
    預設（tail_loop_mask=False、clean_eos_reweight=0）→ 回 (原 labels, None) → kernel 行為不變。
    """
    n = int(seg_labels.shape[0])
    labels = seg_labels
    weight = None
    if lc.tail_loop_mask and n >= 2 * int(lc.tail_loop_min_repeats):
        start = _detect_trailing_loop(seg_labels.tolist(), lc.tail_loop_period_max, lc.tail_loop_min_repeats)
        if start is not None and start < n:
            labels = seg_labels.clone()
            labels[start:] = IGNORE
    if lc.clean_eos_reweight > 0.0 and n > 0 and int(seg_labels[-1].item()) == eos_id:
        weight = torch.ones(n, device=seg_labels.device, dtype=torch.float32)
        k = min(int(lc.clean_eos_k), n)
        weight[n - k:] = 1.0 + float(lc.clean_eos_reweight)
    return labels, weight


def _setup_fsdp_cpu_offload(model, world, local):
    """FSDP2 + CPUOffloadPolicy（32B/超長 context；borrow soft_distill_v2，V27）。"""
    import logging

    from torch.distributed.device_mesh import init_device_mesh
    from torch.distributed.fsdp import CPUOffloadPolicy, MixedPrecisionPolicy, fully_shard
    gpn = int(os.environ.get("LOCAL_WORLD_SIZE", torch.cuda.device_count())) or 1
    n_nodes = world // gpn
    if n_nodes > 1:
        mesh = init_device_mesh("cuda", (n_nodes, gpn), mesh_dim_names=("replicate", "shard"))
    else:
        mesh = init_device_mesh("cuda", (gpn,), mesh_dim_names=("shard",))
    logging.getLogger("opd_v2.trainer").info("CPUOffload mesh nodes=%d shard=%d", n_nodes, gpn)
    mp = MixedPrecisionPolicy(param_dtype=torch.bfloat16, reduce_dtype=torch.float32)
    off = CPUOffloadPolicy(pin_memory=True)
    model = model.to(f"cuda:{local}")
    for layer in model.model.layers:
        fully_shard(layer, mesh=mesh, mp_policy=mp, offload_policy=off)
    fully_shard(model, mesh=mesh, mp_policy=mp, offload_policy=off)
    return model


def build_opd_v2_model(cfg: OPDConfig, world: int, local: int):
    """build_model（stage1）+ grad-ckpt + train() + 裝乾淨 forward + FSDP/HSDP shard。回 sharded model。"""
    mp = torch.float32 if cfg.trainer.master_dtype == "fp32" else torch.bfloat16
    model = build_model(cfg.trainer.student_path, attn=cfg.trainer.attn, liger=True, master_dtype=mp)
    if cfg.trainer.grad_ckpt:
        model.gradient_checkpointing_enable(
            gradient_checkpointing_kwargs={"use_reentrant": False, "preserve_rng_state": False})
    model.train()   # ★ grad-ckpt 只在 training=True 才觸發（v1 雷：靜默 no-op → OOM）
    if cfg.trainer.cpu_offload:
        model = _setup_fsdp_cpu_offload(model, world, local)
    else:
        model = setup_parallelism(model, world, local)
    model.forward = types.MethodType(opd_v2_forward, model)
    model._opd_hard = cfg.loss.hard_weight
    model._opd_soft = cfg.loss.soft_weight
    model._opd_beta = cfg.loss.beta
    model._opd_temp = cfg.loss.temperature
    # V34 routed-OPD 旋鈕（kernel 預設 = bit-identical 回 β OPD）
    model._opd_skew_alpha = cfg.loss.skew_alpha
    model._opd_fkl_lambda = cfg.loss.fkl_lambda
    model._opd_fkl_top_k = cfg.loss.fkl_top_k
    model._opd_route = (cfg.loss.route_high_ent_nats, cfg.loss.route_oc_hs_nats,
                        cfg.loss.route_oc_js, cfg.loss.route_outlier_nll, cfg.loss.base_outlier_down)
    model._opd_eos_id = EOS_ID
    model._opd_eos_region_n = cfg.loss.eos_region_n
    model._opd_diag = False           # train_step 在 want_g4 且 rank0 時打開
    model._diag_out = {}
    if world > 1:
        from torch.distributed.tensor import DTensor
        if not isinstance(next(model.parameters()), DTensor):
            raise RuntimeError("FSDP2/HSDP did not engage: first param not a DTensor")
    return model


# ---------------------------------------------------------------------------
# LPT assign（rank-0；保證每 rank ≤1 bin → forward 次數一致）
# ---------------------------------------------------------------------------
def lpt_assign(trajs: list, world: int, bin_capacity: int,
               length_fn=lambda t: len(t.ids)) -> tuple[list[list], list]:
    """把 flat batch 分到 world 份，每份總 token ≤ bin_capacity（=1 個 micro_batch_tokens bin）。

    largest-first 放進「現有最空且放得下」的 rank；放不下任何 rank → drop（回 dropped 供 GC）。
    回 (per_rank_lists[world], dropped)。每份之後恰好 pack 成 1 個 bin（trainer 端 assert）。
    `length_fn` 讓 wire-dict（`{"ids":[...]}`）與 ScoredTrajectory（`.ids`）都能用。
    """
    order = sorted(range(len(trajs)), key=lambda i: length_fn(trajs[i]), reverse=True)
    bins: list[list] = [[] for _ in range(world)]
    fills = [0] * world
    dropped = []
    for i in order:
        L = length_fn(trajs[i])
        # 最空且放得下的 rank
        cand = [r for r in range(world) if fills[r] + L <= bin_capacity]
        if not cand:
            dropped.append(trajs[i])
            continue
        r = min(cand, key=lambda r: fills[r])
        bins[r].append(trajs[i])
        fills[r] += L
    return bins, dropped


# ---------------------------------------------------------------------------
# trainer
# ---------------------------------------------------------------------------
def _build_scheduler(opt, schedule: str, warmup: int, total: int):
    if schedule in ("cosine", "warmup_cosine"):
        import math

        def lr_lambda(s):
            if warmup > 0 and s < warmup:
                return (s + 1) / warmup
            prog = min(1.0, max(0.0, (s - warmup) / max(1, total - warmup)))
            return 0.5 * (1.0 + math.cos(math.pi * prog))
        return torch.optim.lr_scheduler.LambdaLR(opt, lr_lambda)
    return torch.optim.lr_scheduler.LambdaLR(opt, lambda s: 1.0)


class OPDTrainerV2:
    """HSDP trainer：read FS hidden → pack（無切窗）→ chunked JSD fwd/bwd → optim。每 rank 每步 1 bin。"""

    def __init__(self, cfg: OPDConfig, world: int, local: int, gloo_group=None):
        self.cfg = cfg
        # DEEP_REVIEW §C1：MICRO < max_traj 時最長 traj 會被 pack 靜默丟（無 log）→ 開機硬擋。
        if cfg.trainer.micro_batch_tokens < cfg.data_plane.max_traj_tokens:
            raise ValueError(
                f"MICRO({cfg.trainer.micro_batch_tokens}) < max_traj_tokens"
                f"({cfg.data_plane.max_traj_tokens})：最長 traj 會被靜默丟（DEEP_REVIEW C1）。"
                f"把 MICRO 與 MAX_TRAJ_TOKENS 一起調，或加 trainer node。")
        self.world, self.local = world, local
        self.rank = int(os.environ.get("RANK", local))
        self.device = f"cuda:{local}"
        self.gloo = gloo_group
        self.step = 0
        self.model = build_opd_v2_model(cfg, world, local)
        self.opt = torch.optim.AdamW(
            self.model.parameters(), lr=cfg.trainer.lr,
            fused=not cfg.trainer.cpu_offload, foreach=cfg.trainer.cpu_offload or None,
            betas=(cfg.trainer.adam_beta1, cfg.trainer.adam_beta2),
            weight_decay=cfg.trainer.weight_decay)
        self.sched = _build_scheduler(self.opt, cfg.trainer.lr_schedule,
                                      cfg.trainer.warmup_steps, cfg.trainer.total_steps)
        self.w_rot, _ = build_w_rot(cfg.trainer.teacher_path, HID_DIM, device=self.device)
        self.w_rot = self.w_rot.to(self.device)
        # tokenizer 給 durable ckpt 的 HF export 用（lazy：第一次 want_hf 才載，見 save_checkpoint；
        # 全 rank 在同一個 collective save_consolidated 前一起載 → 決定一致）。
        self.tokenizer = None

    # ---- FS read → v1 Trajectory（帶 bytes）----
    def _read_traj(self, wire: dict) -> Trajectory | None:
        """deref handle → 讀 FS → 組 v1 Trajectory（teacher bytes 內嵌，給 pack/decode 用）。失敗回 None。"""
        try:
            packed, scales, top1, seq_len, hid = read_hidden(wire["handle"]["path"])
        except (FileNotFoundError, ValueError, OSError):
            return None
        ids = wire["ids"]
        plen = int(wire["prompt_len"])
        n_t = len(ids) - plen
        if n_t <= 0 or seq_len != n_t + 1:
            return None
        return Trajectory(
            token_ids=list(ids), prompt_len=plen, weight_version=int(wire["wv"]),
            teacher_packed=packed, teacher_scales=scales, teacher_seq_len=seq_len,
            teacher_top1=(top1 or None), position_offset=0)   # 整條不切窗 → offset 0

    # ---- assemble 1 bin → forward kwargs（decode teacher hidden）----
    def _assemble_kw(self, b: PackedBin) -> tuple[dict, int]:
        dev = self.device
        lc = self.cfg.loss
        spos, th, lab, tw, seg_lens = [], [], [], [], []
        any_w = False
        for seg in b.segments:
            spos.append(seg.student_pos.to(dev))
            seq_len = seg.teacher_seq_len if seg.teacher_seq_len is not None else seg.n_t + 1
            if seq_len != seg.n_t + 1:
                raise RuntimeError(f"teacher seq_len {seq_len} != n_t+1 {seg.n_t + 1}")
            dec = decode_teacher_hidden(seg.teacher_packed, seg.teacher_scales, seq_len,
                                        device=dev, hid=HID_DIM)
            th.append(dec[: seg.n_t])
            # V34：tail-loop mask（label→IGNORE）+ clean-EOS reweight（tok_weight）。預設關 → 原樣。
            seg_labels, seg_w = _v34_tail_weights(seg.labels.to(dev), lc, EOS_ID)
            lab.append(seg_labels)
            seg_lens.append(int(seg_labels.shape[0]))
            if seg_w is not None:
                any_w = True
                tw.append(seg_w)
            else:
                tw.append(torch.ones(int(seg_labels.shape[0]), device=dev, dtype=torch.float32))
        t = b.tensors
        labels = torch.cat(lab)
        kw = dict(
            input_ids=t["input_ids"].to(dev), position_ids=t["position_ids"].to(dev),
            cu_seq_lens_q=t["cu_seq_lens_q"].to(dev), cu_seq_lens_k=t["cu_seq_lens_k"].to(dev),
            max_length_q=t["max_length_q"], max_length_k=t["max_length_k"],
            opd_student_pos=torch.cat(spos), opd_teacher_hidden=torch.cat(th),
            opd_labels=labels, opd_w_rot=self.w_rot, opd_chunk_size=self.cfg.loss.chunk_size,
            opd_tok_weight=(torch.cat(tw) if any_w else None), opd_seg_lens=seg_lens)
        # nt = kernel normalizer = 有效（非 IGNORE）target token 數（tail-mask 後 < numel）→ 與 kernel
        # 的 num_valid 一致，global token-mean 才正確（DEEP_REVIEW C1 路徑無 IGNORE 時 == numel）。
        nt = int((labels != IGNORE).sum().item())
        return kw, nt

    def _dummy_kw(self) -> tuple[dict, int]:
        """空 rank 的 0-target forward：觸發 backbone collective、loss/grad=0。"""
        dev = self.device
        L = 2
        kw = dict(
            input_ids=torch.full((1, L), PAD_ID, dtype=torch.long, device=dev),
            position_ids=torch.arange(L, device=dev).view(1, L),
            cu_seq_lens_q=torch.tensor([0, L], dtype=torch.int32, device=dev),
            cu_seq_lens_k=torch.tensor([0, L], dtype=torch.int32, device=dev),
            max_length_q=L, max_length_k=L,
            opd_student_pos=torch.empty(0, dtype=torch.long, device=dev),
            opd_teacher_hidden=torch.empty(0, HID_DIM, device=dev, dtype=torch.bfloat16),
            opd_labels=torch.empty(0, dtype=torch.long, device=dev),
            opd_w_rot=self.w_rot, opd_chunk_size=self.cfg.loss.chunk_size,
            opd_tok_weight=None, opd_seg_lens=[])
        return kw, 0

    def forward_backward(self, kw: dict, nt: int) -> dict:
        """1 bin forward → global token-mean → 1 backward（mirror v1，但每 rank 固定 1 forward）。

        global token-level objective：FSDP backward ÷world，故 all_reduce(SUM) local target token → global，
        scale = world/global → 平均後即真正 global token-weighted mean。每 rank 都 1 forward（含 dummy）
        → collective 對齊。
        """
        loss = self.model(**kw)                       # opd_v2_forward → scalar（per-token mean，nt=0 時 0）
        local_tok = nt
        local_loss_sum = loss.detach() * nt
        global_tok, global_loss_sum = local_tok, local_loss_sum
        if self.world > 1:
            tt = torch.stack([torch.tensor(float(local_tok), device=self.device),
                              local_loss_sum.float()])
            torch.distributed.all_reduce(tt, op=torch.distributed.ReduceOp.SUM)
            global_tok = int(tt[0].item())
            global_loss_sum = tt[1]
        # NaN/Inf guard（collective-safe：global_loss_sum 各 rank 相同 → 全 rank 同決定）：
        # 非有限就不 backward（避免毒 param），回 finite=False 讓 train_step 跳過 optim。
        finite = bool(torch.isfinite(global_loss_sum).item())
        if not finite:
            return {"loss": float("nan"), "local_target_tokens": local_tok,
                    "global_target_tokens": global_tok, "finite": False}
        scale = self.world / max(1, global_tok)
        (loss * nt * scale).backward()                # 1 backward → FSDP reduce-scatter 同步
        return {"loss": float((global_loss_sum / max(1, global_tok)).item()),
                "local_target_tokens": local_tok, "global_target_tokens": global_tok, "finite": True}

    def optim_step(self) -> float | None:
        gnorm = None
        gc = self.cfg.trainer.grad_clip
        if gc and gc > 0:
            gn = torch.nn.utils.clip_grad_norm_(self.model.parameters(), gc)
            gnorm = gn.full_tensor().item() if hasattr(gn, "full_tensor") else float(gn)
        self.opt.step()
        self.sched.step()
        self.opt.zero_grad(set_to_none=True)
        self.step += 1
        return gnorm

    @torch.no_grad()
    def g4_agreement(self, b: PackedBin, cap: int = 512) -> dict:
        """G4-real 對齊診斷（rank-local、無 collective）：teacher 重建 logits argmax vs student 實抽 token。"""
        from opd.batch import PACKED_ROW_BYTES, SCALE_ROW_BYTES
        th_parts, lab_parts, remaining = [], [], cap
        for seg in b.segments:
            if remaining <= 0:
                break
            keep = min(seg.n_t, remaining)
            if keep <= 0:
                continue
            packed = seg.teacher_packed[: keep * PACKED_ROW_BYTES]
            scales = seg.teacher_scales[: keep * SCALE_ROW_BYTES]
            th_parts.append(decode_teacher_hidden(packed, scales, keep, device=self.device, hid=HID_DIM))
            lab_parts.append(seg.labels[:keep].to(self.device))
            remaining -= keep
        if not th_parts:
            return {"top1": 0.0, "top5": 0.0, "n": 0}
        th = torch.cat(th_parts).float()
        lab = torch.cat(lab_parts)
        logits = th @ self.w_rot.float().T
        a1 = (logits.argmax(-1) == lab).float().mean().item()
        a5 = (logits.topk(5, -1).indices == lab.unsqueeze(-1)).any(-1).float().mean().item()
        return {"top1": a1, "top5": a5, "n": int(lab.numel())}

    # ---- 一步（每 rank；shard 是該 rank 自己那份 wire-trajs）----
    def train_step(self, shard: list[dict], *, want_g4: bool = False) -> dict:
        """讀 FS → collective-safe gate → pack(1 bin) → fwd/bwd → optim。回 metrics（含 skipped flag）。"""
        torch.cuda.reset_peak_memory_stats()
        # 1) deref + read FS
        trajs = [t for t in (self._read_traj(w) for w in shard) if t is not None]
        n_read_fail = len(shard) - len(trajs)
        # 2) collective-safe gate：任一 rank「該有卻沒讀到」→ 全 rank skip
        ok = 1 if n_read_fail == 0 else 0
        if self.world > 1:
            okf = torch.tensor([ok], device=self.device)
            torch.distributed.all_reduce(okf, op=torch.distributed.ReduceOp.MIN)
            ok = int(okf.item())
        if not ok:
            return {"skipped": True, "step": self.step, "n_read_fail": n_read_fail}
        # 3) pack（whole-traj，no window）；保證 ≤1 bin
        g4 = {}
        if trajs:
            bins = pack_trajectories(trajs, self.cfg.trainer.micro_batch_tokens, PAD_ID,
                                     max_segs=len(trajs) + 2, device="cpu")
            if len(bins) > 1:
                raise RuntimeError(f"rank {self.rank} packed {len(bins)} bins (LPT invariant broken)")
            if bins:
                kw, nt = self._assemble_kw(bins[0])
                if want_g4 and self.rank == 0:
                    g4 = self.g4_agreement(bins[0])
            else:
                kw, nt = self._dummy_kw()
        else:
            kw, nt = self._dummy_kw()            # 空 rank：dummy forward 維持 collective 一致
        # 4) fwd/bwd（want_g4 且 rank0 → 順便算學習診斷 entropy/雙向 KL）+ 5) optim
        want_diag = want_g4 and self.rank == 0
        self.model._opd_diag = want_diag
        self.model._diag_out = {}
        m = self.forward_backward(kw, nt)
        self.model._opd_diag = False
        if not m.get("finite", True):
            # 非有限 loss：不 step（梯度沒算/不可信），zero_grad 後當作 skip（不進 step）
            self.opt.zero_grad(set_to_none=True)
            m.update({"skipped": True, "non_finite": True, "step": self.step,
                      "n_trajs": len(trajs), "n_read_fail": n_read_fail})
            return m
        gnorm = self.optim_step()
        m.update({"skipped": False, "step": self.step, "gnorm": gnorm, "n_bins": 1,
                  "n_trajs": len(trajs), "n_read_fail": n_read_fail,
                  "lr": self.sched.get_last_lr()[0],
                  "peak_gb": torch.cuda.max_memory_allocated() / 1e9})
        diag = getattr(self.model, "_diag_out", {}) or {}
        for k in ("entropy", "reverse_kl", "forward_kl", "teacher_nll",
                  "eos_student_prob", "eos_teacher_nll", "tail_entropy_gap"):
            if k in diag:
                m[f"learn_{k}"] = diag[k]
        if g4:
            m["g4_top1"] = g4["top1"]
            m["g4_top5"] = g4["top5"]
        return m

    def save_weights(self, slot: str | None = None) -> dict:
        """並行 sharded HF save（V33，double-buffer _a/_b）。輸出標準 HF 多檔分片 + index.json，
        sglang update_weights_from_disk 原生吃（零改 flash_rl loader）。

        gather 走 NCCL(GPU)、write-by-owner 各 rank 並行寫自己負責的 tensor 子集 → 32B 從 ~200s
        降到 ~20-30s（hgpn008 4-GPU 實測 45s、bit-exact）。瓶頸是「rank0 單點物化 65GB + 單線程寫」，
        本法把兩者都打散到全 world。GPU headroom 不足時（collective 預檢，避免 mid-collective OOM 卡死）
        fallback 回舊的 rank0 單檔 consolidated 路徑。"""
        import logging
        from torch.distributed.checkpoint.state_dict import StateDictOptions, get_model_state_dict
        from safetensors.torch import save_file
        buf = slot or ("a" if (self.step // max(1, self.cfg.trainer.weight_sync_every)) % 2 == 0 else "b")
        path = os.path.join(self.cfg.weights_dir, f"_{buf}")
        if self.rank == 0:
            os.makedirs(path, exist_ok=True)
            self._clean_weight_dir(path)            # single↔multi 切換 / 上輪殘檔
        if self.world > 1:
            torch.distributed.barrier()

        # collective 預檢：full fp32 state-dict 落 GPU 需 ~param_bytes*4；free 不夠就【全 rank 一致】走
        # consolidated（低 GPU 尖峰）。預檢在任何 risky collective 前 → 不會 mid-gather OOM 卡死別的 rank。
        torch.cuda.empty_cache()
        need = sum(p.numel() * 4 for _, p in self.model.named_parameters())
        free = torch.cuda.mem_get_info()[0]
        safe = 1 if free > need + (6 << 30) else 0   # +6GB margin（NCCL buffer / 碎片）
        if self.world > 1:
            tt = torch.tensor([safe], device=torch.cuda.current_device())
            torch.distributed.all_reduce(tt, op=torch.distributed.ReduceOp.MIN)
            safe = int(tt.item())

        if safe:
            self._save_weights_sharded(path, get_model_state_dict, StateDictOptions, save_file)
        else:
            if self.rank == 0:
                logging.getLogger("opd_v2.trainer").warning(
                    "save_weights: GPU headroom 不足 (free=%.0fGB need=%.0fGB) → consolidated 單檔 fallback",
                    free / 1e9, need / 1e9)
            self._save_weights_consolidated(path, get_model_state_dict, StateDictOptions, save_file)

        if self.rank == 0:
            self._copy_config_files(path)           # 補 config/tokenizer → path 成完整 HF model dir
        if self.world > 1:
            torch.distributed.barrier()
        return {"path": path, "weight_version": self.step}

    def _clean_weight_dir(self, path: str) -> None:
        """清掉 buffer 目錄的舊權重檔（避免 single↔multi 切換殘留、舊 shard 混入 sglang glob）。"""
        import glob as _glob
        for f in (_glob.glob(os.path.join(path, "model*.safetensors")) +
                  _glob.glob(os.path.join(path, "*.index.json"))):
            try:
                os.remove(f)
            except OSError:
                pass

    def _save_weights_sharded(self, path, get_msd, SDOpts, save_file) -> None:
        """快路徑：NCCL gather 落 GPU → 釋放非己 → 各 rank 並行寫自己負責的 bf16 子集 + rank0 寫 index.json。"""
        torch.cuda.empty_cache()
        sd = get_msd(self.model, options=SDOpts(full_state_dict=True, cpu_offload=False))  # GPU、NCCL
        # size-balanced 指派（LPT by numel，over state-dict keys → 含 buffer 若有；所有 rank 確定性一致）
        buckets = [set() for _ in range(self.world)]
        fills = [0] * self.world
        owner: dict[str, int] = {}
        for k, v in sorted(sd.items(), key=lambda kv: kv[1].numel(), reverse=True):
            r = min(range(self.world), key=lambda i: fills[i])
            buckets[r].add(k); fills[r] += v.numel(); owner[k] = r
        mine = buckets[self.rank]
        for k in list(sd.keys()):                # 釋放非自己的 → 壓 GPU 尖峰
            if k not in mine:
                sd[k] = None
        torch.cuda.empty_cache()
        shard = {k: sd[k].bfloat16().contiguous().cpu() for k in mine}   # D2H 只搬自己那份（並行）
        del sd
        torch.cuda.empty_cache()
        save_file(shard, os.path.join(path, f"model-{self.rank + 1:05d}-of-{self.world:05d}.safetensors"))
        if self.world > 1:
            torch.distributed.barrier()          # 確保所有 shard 落地，rank0 才寫 index
        if self.rank == 0:
            import json
            wmap = {k: f"model-{owner[k] + 1:05d}-of-{self.world:05d}.safetensors" for k in owner}
            with open(os.path.join(path, "model.safetensors.index.json"), "w") as fh:
                json.dump({"metadata": {"total_size": sum(fills) * 2}, "weight_map": wmap}, fh)

    def _save_weights_consolidated(self, path, get_msd, SDOpts, save_file) -> None:
        """fallback：舊路徑——gather 落 rank0 CPU（低 GPU 尖峰）、rank0 單檔寫 model.safetensors（無 index）。"""
        sd = get_msd(self.model, options=SDOpts(full_state_dict=True, cpu_offload=True))
        if self.rank == 0:
            save_file({k: v.bfloat16().contiguous() for k, v in sd.items()},
                      os.path.join(path, "model.safetensors"))

    def _copy_config_files(self, path: str) -> None:
        """copy config/tokenizer 等非權重檔（skip 來源的 *.safetensors/index → 用我們自己寫的）。"""
        import shutil
        src = self.cfg.trainer.deploy_config_src or self.cfg.trainer.student_path
        for fn in os.listdir(src):
            if fn.endswith((".safetensors", ".bin", ".pt", ".pth")) or "index" in fn:
                continue
            s = os.path.join(src, fn)
            if os.path.isfile(s):
                shutil.copy2(s, os.path.join(path, fn))

    # ---- durable checkpoint / resume（DCP model+optim+sched；跟 _a/_b rolling buffer 分開，V32）----
    def save_checkpoint(self, want_hf: bool = True, keep: int = -1) -> dict:
        """寫一個 durable ckpt 到 <run>/checkpoints/step_<N>/。全 rank collective。回 {dir, step}。

        - DCP sharded **model+optim** + `meta.json`(step/scheduler)：精確 resume 用（重用 stage1 `save_resume`）。
        - want_hf：另存 consolidated bf16 HF 到 `step_N/hf/`（training-format；serve 前過 make_olmo3sink_deploy.py）。
        - **commit 完才更新 `latest.json` 指標、才修剪舊 ckpt**（永不先刪唯一好檔）。crash 只損失半寫的 step dir。
        """
        ckpt_root = self.cfg.checkpoints_dir
        step_dir = os.path.join(ckpt_root, f"step_{self.step:06d}")
        # OPD 無 epoch/fixed-stream → epoch/bins_consumed 傳 0（resume 不需要 data-replay；on-policy 重新生）
        save_resume(self.model, self.opt, self.sched, step=self.step, epoch=0,
                    bins_consumed_epoch=0, ckpt_dir=step_dir, world=self.world, rank=self.rank)
        if want_hf:
            if self.tokenizer is None:
                from transformers import AutoTokenizer
                self.tokenizer = AutoTokenizer.from_pretrained(self.cfg.trainer.student_path)
            save_consolidated(self.model, self.tokenizer, os.path.join(step_dir, "hf"),
                              self.world, self.rank)
        if self.rank == 0:
            import json
            tmp = os.path.join(ckpt_root, "latest.json.tmp")
            with open(tmp, "w") as f:
                json.dump({"dir": step_dir, "step": self.step}, f)
            os.replace(tmp, os.path.join(ckpt_root, "latest.json"))   # atomic commit
            self._prune_checkpoints(ckpt_root, keep)
        if self.world > 1:
            torch.distributed.barrier()
        return {"dir": step_dir, "step": self.step}

    @staticmethod
    def _prune_checkpoints(ckpt_root: str, keep: int) -> None:
        """保留最近 `keep` 個 step_* dir（keep<0 = 全留）；**絕不刪 latest.json 指到的那個**。"""
        if keep is None or keep < 0:
            return
        import glob
        import json
        import shutil
        latest = ""
        lp = os.path.join(ckpt_root, "latest.json")
        if os.path.exists(lp):
            try:
                latest = json.load(open(lp)).get("dir") or ""
            except Exception:
                latest = ""
        dirs = sorted(glob.glob(os.path.join(ckpt_root, "step_*")))
        victims = dirs[:-keep] if keep > 0 else dirs
        for d in victims:
            if latest and os.path.abspath(d) == os.path.abspath(latest):
                continue
            shutil.rmtree(d, ignore_errors=True)

    def try_resume(self, resume_from: str = "") -> "int | None":
        """全 rank collective：從 latest.json（或明指 resume_from）DCP load model+optim+sched，還原 self.step。

        回 resumed step；無可用 ckpt 回 None。所有 rank 讀同一份 shared-FS latest.json → load 決定一致
        （啟動時 latest.json 是上一個 job 結束寫好的、無並發 writer）。半寫（無 meta.json）的 dir 視為無效。
        """
        import json
        ckpt_root = self.cfg.checkpoints_dir
        ckpt_dir = resume_from
        if not ckpt_dir:
            lp = os.path.join(ckpt_root, "latest.json")
            if not os.path.exists(lp):
                return None
            try:
                ckpt_dir = json.load(open(lp)).get("dir")
            except Exception:
                return None
        if not ckpt_dir or not os.path.exists(os.path.join(ckpt_dir, "meta.json")):
            return None
        meta = load_resume(self.model, self.opt, self.sched, ckpt_dir, self.world)
        self.step = int(meta["step"])
        return self.step
