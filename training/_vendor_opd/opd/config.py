# Copyright 2026 proof-pilot. Apache-2.0.
"""OPD 全域設定（見 ../../PLAN.md §3 決策表）。

所有旋鈕集中一處；orchestrator / 三個 service / loss 都從這裡取值。預設值對應 PLAN 的
「最低風險、最大重用既有 infra」配方：full-vocab via quant-hidden、JSD(β=0.5)、Flash teacher、
token-in-token-out、disk 權重同步、near-on-policy（max_staleness 有界）。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

# ---- Resource paths (override via environment variables) ----
STUDENT_PATH = os.environ.get("STUDENT_PATH", "/models/olmo3-sink-stage1-v2-7b")
TEACHER_PATH = os.environ.get("DEEPSEEK_V4_FLASH", "/models/DeepSeek-V4-Flash")
SGLANG_SIF = os.environ.get("SGLANG_SIF", "/images/sglang.sif")
HID_DIM = 4096          # Flash / student 同為 4096（JSD 在 vocab logits 上比，hidden dim 不需相同）
VOCAB_SIZE = 129280     # teacher == student（已驗證；見 G1）


@dataclass
class TeacherCfg:
    """DeepSeek-V4-Flash teacher scoring service（sglang，容器內）。"""
    model_path: str = TEACHER_PATH
    tp_size: int = 4
    # 來自 _validate_hidden.py 驗過的 Flash 配置：
    chunked_prefill_size: int = 11264   # flash_mla get_decoding_sched_meta smem cap ~11.6k；
                                        # 比 doc 短也 OK（patch 2/3 跨 chunk 累積 hidden）。16384 會 CUDA invalid argument；-1 會崩
    mem_fraction_static: float = 0.80
    max_running_requests: int = 128
    context_length: int = 69632        # ≥ max_traj_tokens + margin（Flash 本身支援 1M；student 才是瓶頸）
    moe_runner_backend: str = "marlin"  # Hopper 上吃原生 fp4 checkpoint
    watchdog_timeout: int = 1800        # 冷啟 JIT 編譯 >5min
    host: str = "0.0.0.0"
    port: int = 8100
    max_traj_tokens: int = 65536        # 超過則 cap。student yarn 上限 65536 → 整條 stack 對齊它
    # 並發/批次化交給 sglang 內建 continuous-batching scheduler（/score async + async_generate）；
    # max_running_requests 即引擎的在飛行上限，不需 server 端自製 batch 旋鈕。


@dataclass
class RolloutCfg:
    """student sglang server（deploy/target olmo2_sink），token-in-token-out。"""
    model_path: str = STUDENT_PATH
    tp_size: int = 1
    temperature: float = 1.0            # D9：rollout 多樣性
    top_p: float = 0.95                 # nucleus：top_p=1.0 尾端亂採會生出 teacher 沒法有效 score 的垃圾
    ignore_eos: bool = False            # 100k smoke 用；正常訓練預設尊重 EOS
    n: int = 4                          # 每 prompt 幾條 rollout
    max_new_tokens: int = 4096
    host: str = "0.0.0.0"
    port: int = 8200
    # deploy 必要 flag（見 docs/stage1_deploy_test）：legacy rope、reasoning/tool parser
    reasoning_parser: str = "deepseek-r1"
    tool_call_parser: str = "deepseekv4"


@dataclass
class LossCfg:
    """Liger fused-linear JSD（D2/D3）。"""
    beta: float = 0.5                   # 0=forward KL, 0.5=JSD, 1=reverse KL（canonical OPD）
    temperature: float = 1.0            # distillation 溫度（teacher/student logits 同除）
    length_normalize: bool = True       # D8：length-normalized mean over generated tokens
    chunk_size: int = 1024              # Liger 逐 token chunk 大小（不 materialize [L,V]）


@dataclass
class TrainerCfg:
    """HSDP trainer（fork stage1_v2/train.py）。"""
    student_path: str = STUDENT_PATH
    lr: float = 1e-5
    adam_beta1: float = 0.9
    adam_beta2: float = 0.95
    weight_decay: float = 0.0
    weight_sync_every: int = 8          # 每 N step 存權重給 rollout（D13；Phase 1 量過再定）
    micro_batch_tokens: int = 32768
    grad_accum: int = 1
    grad_ckpt: bool = True
    master_dtype: str = "fp32"          # fp32 master + bf16 compute（見 README 2026-06-01）
    weight_out_dir: str = "/tmp/opd-weights"  # 本地快碟；跨節點需 shared（見 h200-node-small-file-io）
    mask_easy: bool = False             # 實驗性、非 canonical：mask teacher-argmax==student-token position。
                                        # canonical OPD = 全 generated token RKL mean；預設關，數據說話再開
    compute_frac_agree: bool = False    # 沒有 cached teacher_top1 時，per-step argmax 會多做一次 full-vocab
                                        # teacher head matmul；預設關，只靠 diag_every 做低頻診斷。
    require_teacher_hidden: bool = True # CE-only speed baselines can skip int6 decode + teacher-hidden tensors.
    # weight sync 寫檔時複製哪份非權重 metadata（config/tokenizer）進同步 dir。空 = 用 student_path（訓練
    # config，tf5 rope_parameters）；設成 deploy dir（legacy rope）讓 rollout update_weights 重讀也不踩
    # sglang Olmo3Config yarn 驗證 bug（見 docs/stage1_deploy_test）。
    deploy_config_src: str = ""


@dataclass
class OrchestratorCfg:
    """大腦：buffer / staleness / 速率。"""
    buffer_capacity: int = 4096         # trajectory buffer 條數上限（背壓）
    buffer_capacity_tokens: int = 8_000_000  # token 上限（長 CoT 主導：~3.3KB/token teacher bytes ≈ 26GB RAM）
    max_staleness: int = 16             # D4：丟 cur_step - weight_version > 此值的 trajectory
    prompts_per_pull: int = 32          # 每次抽多少 prompt 去 rollout
    train_batch_trajs: int = 8          # trainer 每 step 吃幾條 trajectory
    long_windowing: bool = True         # 超過 micro_batch_tokens 的長 trajectory 切 window，而非整條丟掉
    window_context_tokens: int = 4096   # 每個非首 window 保留多少左側 context
    window_target_tokens: int = 32768   # 每個 window 訓練多少 generated target token


@dataclass
class OPDConfig:
    teacher: TeacherCfg = field(default_factory=TeacherCfg)
    rollout: RolloutCfg = field(default_factory=RolloutCfg)
    loss: LossCfg = field(default_factory=LossCfg)
    trainer: TrainerCfg = field(default_factory=TrainerCfg)
    orch: OrchestratorCfg = field(default_factory=OrchestratorCfg)

    # prompt 來源：'problems' = distill_gen 去重證明題庫（OPD 實訓母體，套 prover template）；
    #            'l2' = L2 messages mix（prompts.py 內建 math/proof 預設）
    prompt_source: str = "problems"
    prompt_seed: int = 0                  # prompt shuffle/template seed；launcher 可用 SLURM_JOB_ID 避免跨 run 重複
    problems_parquet: str = os.environ.get("PROBLEMS_PARQUET", "distill_gen/problems/problems.parquet")
    prover_template_pool: tuple[str, ...] = ("proofbench_generator", "dsmv2_a1", "imo25_prover")
    # L2 來源（prompt_source='l2' 時用）
    dataset_roots: tuple[str, ...] = (
        os.environ.get("SFT_MIX", "data/nemotron-deepseek-sft-mix"),
        os.environ.get("SFT_MIX_V2", "data/nemotron-deepseek-sft-mix-v2"),
    )
    mix_config: str = ""                # 空 = 用內建 math/proof 預設（見 prompts.py）
    wandb_project: str = "opd-olmo3"

    def hidden_dim(self) -> int:
        return HID_DIM
