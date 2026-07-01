# Copyright 2026 proof-pilot. Apache-2.0.
"""把 env 解析成 OPDConfig 並寫 <run>/config.json（單一 source-of-truth；四 process 啟動讀同一份）。

launcher（run_mn.sh）解析好 server URL + 拓撲後呼叫一次。env 覆寫見下；未設用 config 預設。
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from opd_v2.config import OPDConfig


def _envf(k, d): return float(os.environ[k]) if k in os.environ and os.environ[k] != "" else d
def _envi(k, d): return int(os.environ[k]) if k in os.environ and os.environ[k] != "" else d
def _env(k, d): return os.environ.get(k) or d


def main():
    cfg = OPDConfig(run_name=_env("RUN_NAME", "opd_v2"), run_dir=os.environ["RUN_DIR"]).resolve()
    # servers
    cfg.rollout.urls = [u for u in _env("ROLLOUT_URLS", "").split(",") if u]
    cfg.teacher.urls = [u for u in _env("TEACHER_URLS", "").split(",") if u]
    if not cfg.rollout.urls or not cfg.teacher.urls:
        raise SystemExit("ROLLOUT_URLS / TEACHER_URLS required")
    cfg.rollout.tp_size = _envi("ROLLOUT_TP", cfg.rollout.tp_size)
    cfg.rollout.fp8 = _env("ROLLOUT_FP8", "1") == "1"
    cfg.rollout.n_samples = _envi("ROLLOUT_N", cfg.rollout.n_samples)
    cfg.rollout.max_new_tokens = _envi("MAX_NEW_TOKENS", cfg.rollout.max_new_tokens)
    cfg.rollout.temperature = _envf("ROLLOUT_T", cfg.rollout.temperature)
    cfg.rollout.top_p = _envf("ROLLOUT_TOP_P", cfg.rollout.top_p)
    cfg.rollout.max_inflight_per_replica = _envi("ROLLOUT_MAXRUN", cfg.rollout.max_inflight_per_replica)
    cfg.rollout.gen_timeout_s = _envf("ROLLOUT_GEN_TIMEOUT", cfg.rollout.gen_timeout_s)
    # admission filter：comma-sep finish_reason，命中的 generated 後直接剔除、不進訓練 buffer
    # （預設 "length"=撞窗口截斷；"" = 關閉）。不碰 rollout 取樣分佈，只 reject 進梯度的樣本。
    # ⚠️ 用 os.environ.get 的 sentinel（非 _env 的 `or`）：DROP_FINISH_REASONS="" 是合法值（=關閉），
    #    `or` 會把空字串當未設而錯誤回退到預設（V34 要設空、改由 trainer tail-mask）。
    _dfr = os.environ.get("DROP_FINISH_REASONS")
    if _dfr is not None:
        cfg.rollout.drop_finish_reasons = tuple(x for x in _dfr.split(",") if x)
    cfg.teacher.tp_size = _envi("TEACHER_TP", cfg.teacher.tp_size)
    cfg.teacher.max_inflight_per_replica = _envi("TEACHER_MAXRUN", cfg.teacher.max_inflight_per_replica)
    # data plane / buffer
    cfg.data_plane.target_inflight = _envi("TARGET_INFLIGHT", cfg.data_plane.target_inflight)
    cfg.data_plane.max_traj_tokens = _envi("MAX_TRAJ_TOKENS", cfg.data_plane.max_traj_tokens)
    cfg.data_plane.starve_timeout_s = _envf("STARVE_TIMEOUT", cfg.data_plane.starve_timeout_s)
    cfg.buffer.capacity = _envi("BUF_CAPACITY", cfg.buffer.capacity)
    cfg.buffer.capacity_tokens = _envi("BUF_CAPACITY_TOKENS", cfg.buffer.capacity_tokens)
    cfg.buffer.max_staleness = _envi("MAX_STALENESS", cfg.buffer.max_staleness)
    # trainer
    # student model（換 long-context softdistill model 用；deploy 變體給 weight-sync 存檔的 rope-safe config）
    cfg.trainer.student_path = _env("STUDENT_PATH", cfg.trainer.student_path)
    cfg.trainer.deploy_config_src = _env("STUDENT_DEPLOY_PATH", cfg.trainer.deploy_config_src)
    cfg.trainer.lr = _envf("LR", cfg.trainer.lr)
    cfg.trainer.micro_batch_tokens = _envi("MICRO", cfg.trainer.micro_batch_tokens)
    cfg.trainer.train_batch_trajs = _envi("TRAIN_BATCH_TRAJS", cfg.trainer.train_batch_trajs)
    cfg.trainer.weight_sync_every = _envi("WEIGHT_SYNC_EVERY", cfg.trainer.weight_sync_every)
    cfg.trainer.log_every = _envi("LOG_EVERY", cfg.trainer.log_every)
    cfg.trainer.g4_every = _envi("G4_EVERY", cfg.trainer.g4_every)
    cfg.trainer.cpu_offload = _env("CPU_OFFLOAD", "0") == "1"
    cfg.trainer.http_port = _envi("TRAINER_HTTP_PORT", cfg.trainer.http_port)
    cfg.trainer.total_steps = _envi("MAX_STEPS", cfg.trainer.total_steps)
    cfg.trainer.lr_schedule = _env("LR_SCHEDULE", cfg.trainer.lr_schedule)
    cfg.trainer.warmup_steps = _envi("WARMUP_STEPS", cfg.trainer.warmup_steps)
    # durable checkpoint / resume（DCP model+optim+sched；跟 _a/_b rolling buffer 分開）
    cfg.trainer.checkpoint_every = _envi("CHECKPOINT_EVERY", cfg.trainer.checkpoint_every)
    cfg.trainer.checkpoint_keep = _envi("CHECKPOINT_KEEP", cfg.trainer.checkpoint_keep)
    cfg.trainer.checkpoint_dir = _env("CHECKPOINT_DIR", cfg.trainer.checkpoint_dir)
    cfg.trainer.hf_export = _env("HF_EXPORT", "1") == "1"
    cfg.trainer.resume = _env("RESUME", "1") == "1"
    cfg.trainer.resume_from = _env("RESUME_FROM", cfg.trainer.resume_from)
    # loss
    cfg.loss.beta = _envf("BETA", cfg.loss.beta)
    cfg.loss.chunk_size = _envi("CHUNK_SIZE", cfg.loss.chunk_size)
    # V34 routed-OPD（全預設 0/關 = 回 naive β；見 training/opd_v2/V34_PLAN.md）
    cfg.loss.skew_alpha = _envf("SKEW_ALPHA", cfg.loss.skew_alpha)
    cfg.loss.fkl_lambda = _envf("FKL_LAMBDA", cfg.loss.fkl_lambda)
    cfg.loss.fkl_top_k = _envi("FKL_TOP_K", cfg.loss.fkl_top_k)
    cfg.loss.route_high_ent_nats = _envf("ROUTE_HIGH_ENT_NATS", cfg.loss.route_high_ent_nats)
    cfg.loss.route_oc_hs_nats = _envf("ROUTE_OC_HS_NATS", cfg.loss.route_oc_hs_nats)
    cfg.loss.route_oc_js = _envf("ROUTE_OC_JS", cfg.loss.route_oc_js)
    cfg.loss.route_outlier_nll = _envf("ROUTE_OUTLIER_NLL", cfg.loss.route_outlier_nll)
    cfg.loss.base_outlier_down = _envf("BASE_OUTLIER_DOWN", cfg.loss.base_outlier_down)
    cfg.loss.clean_eos_reweight = _envf("CLEAN_EOS_REWEIGHT", cfg.loss.clean_eos_reweight)
    cfg.loss.clean_eos_k = _envi("CLEAN_EOS_K", cfg.loss.clean_eos_k)
    cfg.loss.tail_loop_mask = _env("TAIL_LOOP_MASK", "1" if cfg.loss.tail_loop_mask else "0") == "1"
    cfg.loss.tail_loop_period_max = _envi("TAIL_LOOP_PERIOD_MAX", cfg.loss.tail_loop_period_max)
    cfg.loss.tail_loop_min_repeats = _envi("TAIL_LOOP_MIN_REPEATS", cfg.loss.tail_loop_min_repeats)
    cfg.loss.eos_region_n = _envi("EOS_REGION_N", cfg.loss.eos_region_n)
    # rollout dump（存所有 rollouts → dflash 原生 parquet；預設開）
    cfg.rollout_dump.enabled = _env("ROLLOUT_DUMP", "1") == "1"
    cfg.rollout_dump.dir = _env("ROLLOUT_DUMP_DIR", cfg.rollout_dump.dir)
    cfg.rollout_dump.rows_per_file = _envi("ROLLOUT_DUMP_ROWS", cfg.rollout_dump.rows_per_file)
    cfg.rollout_dump.flush_interval_s = _envf("ROLLOUT_DUMP_FLUSH_S", cfg.rollout_dump.flush_interval_s)
    cfg.rollout_dump.store_meta = _env("ROLLOUT_DUMP_META", "1") == "1"
    # agentic（producer="agentic" 才生效；single_round 完全不碰，向前相容）
    cfg.producer = _env("PRODUCER", cfg.producer)
    if "ROLE_MIX" in os.environ and os.environ["ROLE_MIX"]:
        # "prove:22,verify:44,refine:20,select:14"
        cfg.agentic.role_mix = {kv.split(":")[0]: float(kv.split(":")[1])
                                for kv in os.environ["ROLE_MIX"].split(",") if ":" in kv}
    cfg.agentic.softmax_temp = _envf("ROLE_SOFTMAX_TEMP", cfg.agentic.softmax_temp)
    cfg.agentic.max_proofs_per_problem = _envi("MAX_PROOFS_PER_PROBLEM", cfg.agentic.max_proofs_per_problem)
    cfg.agentic.max_verifies_per_proof = _envi("MAX_VERIFIES_PER_PROOF", cfg.agentic.max_verifies_per_proof)
    cfg.agentic.max_refined_per_problem = _envi("MAX_REFINED_PER_PROBLEM", cfg.agentic.max_refined_per_problem)
    cfg.agentic.prefer_student_context = _env("PREFER_STUDENT_CONTEXT", "1") == "1"
    cfg.agentic.refine_bundle_cap_tokens = _envi("REFINE_BUNDLE_CAP", cfg.agentic.refine_bundle_cap_tokens)
    cfg.agentic.select_bundle_cap_tokens = _envi("SELECT_BUNDLE_CAP", cfg.agentic.select_bundle_cap_tokens)
    cfg.agentic.max_prompt_tokens = _envi("AGENTIC_MAX_PROMPT_TOKENS", cfg.agentic.max_prompt_tokens)
    cfg.agentic.seed_format = _env("SEED_FORMAT", cfg.agentic.seed_format)
    cfg.agentic.seed_source = _env("SEED_SOURCE", cfg.agentic.seed_source)
    cfg.agentic.seed_hf_config = _env("SEED_HF_CONFIG", cfg.agentic.seed_hf_config)
    cfg.agentic.pool_dir = _env("POOL_DIR", cfg.agentic.pool_dir)
    # misc
    cfg.seed = _envi("SEED", cfg.seed)
    cfg.wandb_mode = _env("WANDB_MODE", cfg.wandb_mode)
    cfg.wandb_project = _env("WANDB_PROJECT", cfg.wandb_project)
    path = cfg.save()
    print(path)
    print(f"  rollout={len(cfg.rollout.urls)} replicas, teacher={len(cfg.teacher.urls)} replicas, "
          f"micro={cfg.trainer.micro_batch_tokens} batch_trajs={cfg.trainer.train_batch_trajs} "
          f"wsync_every={cfg.trainer.weight_sync_every} beta={cfg.loss.beta} max_steps={cfg.trainer.total_steps}\n"
          f"  V34 loss: skew_alpha={cfg.loss.skew_alpha} fkl_lambda={cfg.loss.fkl_lambda} "
          f"clean_eos_reweight={cfg.loss.clean_eos_reweight} tail_loop_mask={cfg.loss.tail_loop_mask} "
          f"drop_finish={cfg.rollout.drop_finish_reasons}\n"
          f"  checkpoint_every={cfg.trainer.checkpoint_every} keep={cfg.trainer.checkpoint_keep} "
          f"hf_export={cfg.trainer.hf_export} resume={cfg.trainer.resume}")


if __name__ == "__main__":
    main()
