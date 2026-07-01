# Copyright 2026 proof-pilot. Apache-2.0.
"""OPD v2 設定 —— **單一 source-of-truth**（修 v1 的 P10「三套 default 漂移」）。

四個 process（rollout sglang / teacher sglang / trainer server / orchestrator）都從**同一份**
`OPDConfig` 取值。落地方式：launcher 解析一次 → 寫 `<run>/config.json` → 四個 process 啟動時
`OPDConfig.load(run_dir)` 讀回同一份，沒有任何 process 各自帶 default。

本檔**不 import torch**（orchestrator 是純 CPU async process，要能在沒有 GPU 環境 import）。
路徑/維度常數沿用 v1（已驗證）：student=stage1-v2-7b、teacher=DeepSeek-V4-Flash、hid=4096、
vocab=129280（teacher==student，G1 已驗）。
"""
from __future__ import annotations

import dataclasses
import json
import os
from dataclasses import dataclass, field

# ---- 既定常數（此 cluster，沿用 v1）----
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
STUDENT_PATH = f"{REPO}/outputs/stage1-v2-7b"
STUDENT_DEPLOY_PATH = f"{REPO}/outputs/stage1-v2-7b-deploy"  # legacy-rope config（rollout reload 安全）
TEACHER_PATH = os.environ.get("DEEPSEEK_V4_FLASH", "/models/DeepSeek-V4-Flash")
SGLANG_SIF = os.environ.get("SGLANG_SIF", "/images/sglang.sif")
HID_DIM = 4096
VOCAB_SIZE = 129280
PAD_ID = 2          # student pad_token_id（packing pad tail 用；被 cu_seqlens/IGNORE 遮掉）
EOS_ID = 1


@dataclass
class RolloutCfg:
    """student rollout sglang server（fp8 flash_rl 部署，token-in-token-out）。"""
    urls: list[str] = field(default_factory=lambda: ["http://127.0.0.1:8200"])
    tp_size: int = 1
    fp8: bool = True                    # flash_rl fp8 部署（V30；opd_v2/flash_rl）
    # sampling（V1：一 request 一條；N sample 在 client fan-out）
    n_samples: int = 4                  # 每 prompt 跑幾條獨立 atom
    temperature: float = 1.0
    top_p: float = 0.95                 # top_p=1.0 尾端亂採會生出 teacher 沒法有效 score 的垃圾
    top_k: int = -1
    # 整條 proof 要能生完（teacher high-effort proof 用到 65536；student yarn 窗也是 65536）。
    # produce_sample 會 per-request clamp 成 max_traj_tokens - len(prompt) → 實際 = 整個剩餘窗口。
    # 4096 是 dev 殘留的錯誤值：proof 平均 ~40k tok，4096 等於拿被截斷的半截 proof 在訓練。
    max_new_tokens: int = 65536
    ignore_eos: bool = False
    # 單條 rollout 的 aiohttp client timeout（秒）。撞滿 = doomed/慢條被砍、產 0、放掉 slot。
    # 長 CoT（128k gen）下 decode 慢，預設 3600 可能在合法長 proof 生完前就 timeout（abort 浪費整段算力）。
    gen_timeout_s: float = 3600.0
    # 每 replica 的在飛行限流（與 sglang --max-running-requests 對齊）
    max_inflight_per_replica: int = 8
    # ---- training-buffer admission（V33；不碰 rollout 取樣分佈，只決定哪些 on-policy 樣本進梯度）----
    # finish_reason 命中這裡的，generated 後直接剔除、不進 teacher/buffer（teacher 前 → 省 hidden 寫盤）。
    # 預設 ("length",)：撞窗口截斷的半截 proof / 退化長循環 = OPD self-amplification 主來源（實測 ~5.7%、
    #   其中 ~2% 是真退化循環）。設 () 關閉。擴充點見 produce._admission_drop（未來可加 token-level loop 偵測）。
    drop_finish_reasons: tuple[str, ...] = ("length",)


@dataclass
class TeacherCfg:
    """DeepSeek-V4-Flash teacher scoring sglang server（+ /score FS-write patch）。"""
    urls: list[str] = field(default_factory=lambda: ["http://127.0.0.1:8100"])
    tp_size: int = 4
    max_inflight_per_replica: int = 64   # 引擎 continuous-batching 容量（v1 實測 64-conc ~22.9k tok/s）


@dataclass
class DataPlaneCfg:
    """資料生產（produce_sample atom + 兩個 load-aware pool + scheduler）。"""
    target_inflight: int = 64            # keep-N-in-flight：同時飛行的 atom 數
    rollout_concurrency: int = 0         # 全域 rollout semaphore（0 = sum(replica max_inflight)）
    teacher_concurrency: int = 0         # 全域 teacher semaphore（0 = sum(replica max_inflight)）
    max_traj_tokens: int = 65536         # prompt+gen cap（student yarn 上限）；超過 truncate
    dead_until_seconds: float = 10.0     # replica 連錯後跳過多久
    starve_timeout_s: float = 600.0      # buffer 連續飢餓多久才視為 producer 卡死而 raise；long-CoT
                                         # （單條 100k decode 很慢、第一批可能久）要調大（如 3600+）


@dataclass
class BufferCfg:
    """輕量 trajectory buffer（只存 handle，無 bytes，V16）+ bounded-staleness。"""
    capacity: int = 4096                 # 條數上限
    capacity_tokens: int = 16_000_000    # token 上限（背壓；只存 ids+handle，故可比 v1 大）
    max_staleness: int = 0               # 丟 cur_step - wv > 此值；**0=關閉**（OPD 無 importance ratio，
                                         # staleness 非正確性需求、long CoT rollout 貴不該丟，預設關，見 is_stale）
    near_full_frac: float = 0.9          # producer 背壓門檻


@dataclass
class LossCfg:
    """full-vocab JSD(β) + V34 routed-OPD 穩定化（skew-KL base + routed top-K FKL + EOS/tail reweight）。
    repo chunked fp32-softmax kernel（V26，非 Liger）。**所有 V34 旋鈕預設 0/關 → bit-identical 回 β OPD。**
    設計見 `V34_PLAN.md`；root-cause = length 自我放大 / EOS under-training（DEEP_REVIEW §A2）。"""
    beta: float = 1.0                    # 0=fwdKL 0.5=JSD 1=revKL（on-policy canonical OPD）
    temperature: float = 1.0
    hard_weight: float = 0.0             # 純蒸餾（CE anchor 預設關）
    soft_weight: float = 1.0
    chunk_size: int = 4096               # chunked JSD 的 token chunk（soft_v2 用 4096）
    mask_easy: bool = False              # 實驗性、非 canonical；預設關
    # ---- V34 routed-OPD loss-side root-cause 修法（全預設 0/關 = 退回 naive β）----
    # skew reverse-KL：base 改 KL(student ‖ (1-α)·teacher + α·student)，α≈0.1 拆掉 teacher-near-zero
    # token 的 zero-avoiding 病理（length 自我放大正解；非「純降 β」，保訊號強度）。**只在 beta==1 生效**。
    skew_alpha: float = 0.0
    # routed top-K forward-KL：對 high-entropy / overconfident-wrong / severe-outlier token 疊 FKL（advice §2）。
    # **整包 routing 由 fkl_lambda>0 開關**（含對 outlier 的 base 降權）。
    fkl_lambda: float = 0.0              # 0=關；0.15~0.25=開
    fkl_top_k: int = 64
    route_high_ent_nats: float = 2.5     # teacher entropy(nats) > 此 → high-entropy（+FKL）
    route_oc_hs_nats: float = 0.30       # student entropy < 此 且 ...
    route_oc_js: float = 0.30            # ... top-K JS > 此 → overconfident-wrong（+FKL、↓base）
    route_outlier_nll: float = 8.0       # teacher 對實抽 token 的 -logp > 此 → severe outlier（+FKL、↓base）
    base_outlier_down: float = 1.0       # outlier/oc token 的 base RKL 權重乘 (1−此)；1=完全關 base（advice）
    # ---- EOS / tail reweight（訓練端、on-policy 安全；用 seg.labels token-id 在 trainer 算）----
    clean_eos_reweight: float = 0.0      # clean-EOS（traj 尾 label==eos）尾段 K token 的 soft loss ×(1+此)
    clean_eos_k: int = 64                # clean-EOS 尾段 token 數
    tail_loop_mask: bool = False         # 退化尾段（verbatim 週期循環）weight→0，取代 produce 端 whole-traj drop
    tail_loop_period_max: int = 64       # 偵測的最大循環週期
    tail_loop_min_repeats: int = 4       # 尾段至少重複幾次才判定為循環
    eos_region_n: int = 64               # EOS-region 診斷：每 seg 取尾段幾 token（總列 cap 512）


@dataclass
class TrainerCfg:
    """HSDP trainer-as-service（rank-0 HTTP ingress + 全 rank command-loop）。"""
    student_path: str = STUDENT_PATH
    teacher_path: str = TEACHER_PATH
    attn: str = "olmo3_sink_fa3"
    lr: float = 1e-5
    adam_beta1: float = 0.9
    adam_beta2: float = 0.95
    weight_decay: float = 0.0
    grad_clip: float = 1.0
    grad_ckpt: bool = True
    master_dtype: str = "fp32"           # fp32 master + bf16 compute
    cpu_offload: bool = False            # 32B/超長 context 才開（FSDP2 CPUOffloadPolicy，V27）
    micro_batch_tokens: int = 65536      # packed bin 長度上限（整條 traj 不切窗，V25）
    train_batch_trajs: int = 8           # 每 step 全域吃幾條 traj（rank-0 LPT 切成 world 份）
    weight_sync_every: int = 1           # orchestrator 每 N 步觸發 weight sync（N=1=最 on-policy，V22）
    log_every: int = 1                   # 每 N 步印一行 + 上 wandb（1=每步）
    g4_every: int = 5                    # 每 N 步算一次 g4 agreement + 學習診斷（entropy/雙向KL）；
                                         # 是 reuse-hidden 的 no_grad 小 GEMM（cap 4096），5 步夠密又不貴
    lr_schedule: str = "constant"        # constant | cosine | warmup_cosine
    warmup_steps: int = 0
    total_steps: int = 100000
    http_port: int = 8300                # rank-0 ingress port
    # weight sync 複製哪份 config/tokenizer（空=student；設 deploy dir 避 sglang rope 驗證 bug）
    deploy_config_src: str = STUDENT_DEPLOY_PATH
    # durable checkpoint / resume（DCP model+optim+sched，跟 _a/_b rolling buffer 完全分開、永不覆寫，V32）
    # —— rolling buffer 每 weight_sync 覆寫、無 optim state；這條才是抗 time-limit/crash 的真存檔 + 精確 resume。
    checkpoint_every: int = 50           # 每 N 步寫一個 durable ckpt 到 <run>/checkpoints/step_<N>/（0 = 關）
    checkpoint_keep: int = 2             # 保留最近幾個 step_* dir（-1 = 全留；**commit latest 後才修剪**）
    checkpoint_dir: str = ""             # 空 = <run>/checkpoints
    hf_export: bool = True               # 每個 ckpt 也輸出 consolidated bf16 HF（step_N/hf/，給 eval/serve）
    resume: bool = True                  # 啟動時自動從 checkpoints/latest.json 續跑（model+optim+sched+step）
    resume_from: str = ""                # 明指 step dir（空 = 自動找 latest.json）


@dataclass
class RolloutDumpCfg:
    """把**所有** rollouts(prompt+response token ids)落盤成 dflash 原生 parquet（旁路、脫鉤 hidden GC）。

    給事後分析 / spec-decode draft（dflash）訓練用。dump 點在 produce_sample（rollout 成功+truncate 後、
    teacher score 前）→ 連 teacher 失敗的 rollout 也存得到。見 rollout_store.py。
    """
    enabled: bool = True
    dir: str = ""                        # 空 = <run_dir>/rollouts
    rows_per_file: int = 1000            # 每個 parquet 檔幾條（檔數 vs 記憶體/小檔權衡）
    flush_interval_s: float = 60.0       # 低速率也定期落盤（避免久留記憶體）
    store_meta: bool = True              # 連 meta(problem_id/template) 一起存（JSON 欄）
    compression: str = "zstd"            # pyarrow 內建 codec；= dflash convert_dataset 慣例


@dataclass
class AgenticCfg:
    """agentic semi-on-policy OPD（pool-based 多 role 蒸餾）—— 只在 producer="agentic" 啟用。

    把 single-round prover OPD 推到整條 math_3r loop（prove/verify/refine/select）：維護一個 per-problem
    pool（problem→proofs→verifies、refined），每個 atom 抽一個 role、從 pool 組 context（用 math_3r 的
    XML 模板 + rank/bundle）、student on-policy 生成、teacher /score。parse-pass 的 student 生成寫回 pool
    （只有 answer、去 think）→ pool 漸深、context 漸 on-policy。比例靠 fill-fraction 採樣自動平衡（verify
    因 fan-out 自然最大宗，不堆積未-verify proof）。設計見 PLAN §（V33+）/DECISIONS。
    """
    # role 目標權重（fill_fraction = student_count(role) / weight；採最低 fill_fraction 的 available role）。
    # 22/44/20/14：verify=2×prove（=每 proof 2 verify 的 fan-out，verify 跟得上 proof、零未-verify 堆積）。
    role_mix: dict = field(default_factory=lambda: {
        "prove": 22.0, "verify": 44.0, "refine": 20.0, "select": 14.0})
    softmax_temp: float = 0.5            # role 選擇的 softmax 溫度（>0 加隨機避免 thrash；→0 = argmin）
    # 每題/每 proof 的「展開上限」——只用來在 role 內把工作攤平（spread），不是硬 gate
    max_proofs_per_problem: int = 6
    max_verifies_per_proof: int = 2
    max_refined_per_problem: int = 4
    # context 來源偏好：True = 優先用 student-source artifact 當 context（推 on-policy 轉移）
    prefer_student_context: bool = True
    # bundle 截斷上限（est tokens = chars//4；< student 128k 窗，留空間給長 reasoning）
    refine_bundle_cap_tokens: int = 40000
    select_bundle_cap_tokens: int = 50000
    max_prompt_tokens: int = 100000     # render 後超過此 token 數的 prompt 跳過（罕見，安全閥）
    min_gen_room: int = 48000           # 啟動 guard：max_traj_tokens 須 ≥ max(bundle_cap)+此值，
                                        # 否則 refine/select 的長 reasoning 會被截斷（見 orchestrator guard）
    max_artifact_chars: int = 200000    # 進 pool 的 proof/refined content 字數上限（防病態超長 proof
                                        # 撐爆 render → 該 role starve；200k 字≈50k tok，正常 proof 遠不到）
    # seed（cold-start）：全灌 DeepSeek r3_hard2000 nested data
    seed_format: str = "hf_per_problem"  # "hf_per_problem" | "records_jsonl"
    seed_source: str = "ycchen/dsflash-proof-distill-v2-test"  # HF repo（per_problem config）或 records.jsonl 路徑
    seed_hf_config: str = "per_problem"
    pool_dir: str = ""                   # 空 = <run>/pool


@dataclass
class EvalCfg:
    """in-loop ProofBench eval（修 P11）。"""
    enabled: bool = False
    every_weight_versions: int = 50
    teacher_ceiling: float = 4.64        # dsv4-flash high_notool 天花板（/7）


@dataclass
class OPDConfig:
    # run 識別 + 目錄
    run_name: str = "opd_v2_dev"
    run_dir: str = ""                    # 空 = <opd_v2>/runs/<run_name>（resolve() 補上）
    seed: int = 0
    producer: str = "single_round"       # "single_round"（單輪 prover OPD）| "agentic"（pool-based 多 role）
    prompt_source: str = "problems"
    problems_parquet: str = f"{REPO}/distill_gen/problems/problems.parquet"
    prover_template_pool: tuple[str, ...] = ("proofbench_generator", "dsmv2_a1", "imo25_prover")
    wandb_project: str = "opd-v2"
    wandb_mode: str = "online"

    rollout: RolloutCfg = field(default_factory=RolloutCfg)
    teacher: TeacherCfg = field(default_factory=TeacherCfg)
    data_plane: DataPlaneCfg = field(default_factory=DataPlaneCfg)
    buffer: BufferCfg = field(default_factory=BufferCfg)
    loss: LossCfg = field(default_factory=LossCfg)
    trainer: TrainerCfg = field(default_factory=TrainerCfg)
    eval: EvalCfg = field(default_factory=EvalCfg)
    rollout_dump: RolloutDumpCfg = field(default_factory=RolloutDumpCfg)
    agentic: AgenticCfg = field(default_factory=AgenticCfg)

    # ---- 衍生路徑（run_dir 之下；全 shared-FS WekaFS）----
    def resolve(self) -> "OPDConfig":
        """補上預設 run_dir，確保是絕對 shared-FS 路徑。launcher 啟動時呼叫一次。"""
        if not self.run_dir:
            self.run_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__)))), "runs", self.run_name)
        self.run_dir = os.path.abspath(self.run_dir)
        return self

    @property
    def hidden_dir(self) -> str:
        return os.path.join(self.run_dir, "hidden")

    @property
    def weights_dir(self) -> str:
        return os.path.join(self.run_dir, "weights")

    @property
    def checkpoints_dir(self) -> str:
        """durable ckpt 根目錄（與 weights_dir 的 rolling _a/_b 分開）。"""
        return self.trainer.checkpoint_dir or os.path.join(self.run_dir, "checkpoints")

    @property
    def rollouts_dir(self) -> str:
        return self.rollout_dump.dir or os.path.join(self.run_dir, "rollouts")

    @property
    def pool_dir(self) -> str:
        """agentic pool 根目錄（per-problem graph 的 append-only JSONL + index）。"""
        return self.agentic.pool_dir or os.path.join(self.run_dir, "pool")

    @property
    def trainer_endpoint_file(self) -> str:
        return os.path.join(self.run_dir, "trainer_endpoint.json")

    @property
    def config_file(self) -> str:
        return os.path.join(self.run_dir, "config.json")

    def hidden_dim(self) -> int:
        return HID_DIM

    # ---- JSON round-trip（單一 source-of-truth 落地）----
    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    def save(self) -> str:
        """resolve 後寫 <run>/config.json。回 path。"""
        self.resolve()
        os.makedirs(self.run_dir, exist_ok=True)
        with open(self.config_file, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        return self.config_file

    @classmethod
    def from_dict(cls, d: dict) -> "OPDConfig":
        sub = {
            "rollout": RolloutCfg, "teacher": TeacherCfg, "data_plane": DataPlaneCfg,
            "buffer": BufferCfg, "loss": LossCfg, "trainer": TrainerCfg, "eval": EvalCfg,
            "rollout_dump": RolloutDumpCfg, "agentic": AgenticCfg,
        }
        kw = dict(d)
        for k, klass in sub.items():
            if k in kw and isinstance(kw[k], dict):
                kw[k] = klass(**kw[k])
        # tuple 欄位（json 變 list）還原
        if "prover_template_pool" in kw and isinstance(kw["prover_template_pool"], list):
            kw["prover_template_pool"] = tuple(kw["prover_template_pool"])
        return cls(**kw)

    @classmethod
    def load(cls, run_dir: str) -> "OPDConfig":
        """四個 process 啟動時讀回同一份 resolved config。"""
        path = run_dir if run_dir.endswith(".json") else os.path.join(run_dir, "config.json")
        with open(path) as f:
            return cls.from_dict(json.load(f)).resolve()
