# Copyright 2026 proof-pilot. Apache-2.0.
"""Orchestrator (process #4): drives the rollout / teacher / trainer services through the
training loop. Touches only small data (token ids / handles / control), never bulk hidden.

Responsibilities (see README.md):
- Opens an aiohttp session; builds two load-aware pools (rollout/teacher) + HiddenStore + buffer.
- Runs the Scheduler in the background: produce_sample atoms (one rollout + one teacher score
  each) continuously fill the buffer.
- Discovers the trainer endpoint (reads trainer_endpoint.json from shared FS).
- Train loop: pull train_batch_trajs (staleness-filtered) -> POST /train_step (ids + handle) ->
  GC that batch's hidden files -> every N steps drive a weight sync (/save -> pause rollout ->
  update_weights_from_disk -> resume).
- Teardown: stop scheduler, POST /stop, clean up.
"""
from __future__ import annotations

import argparse
import asyncio
import functools
import json
import logging
import os
import sys
import time

import aiohttp

_THIS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_THIS, "..")))   # opd_v2/src

from opd_v2.buffer import TrajectoryBuffer
from opd_v2.config import OPDConfig
from opd_v2.data_plane.clients import TrainerHTTPClient
from opd_v2.data_plane.pools import build_pools
from opd_v2.data_plane.produce import produce_sample
from opd_v2.data_plane.scheduler import Scheduler
from opd_v2.hidden_store import HiddenHandle, HiddenStore

log = logging.getLogger("opd_v2.orchestrator")


class Orchestrator:
    def __init__(self, cfg: OPDConfig):
        self.cfg = cfg
        self.store = HiddenStore(cfg.hidden_dir)
        self.buffer = TrajectoryBuffer(cfg.buffer.capacity, cfg.buffer.capacity_tokens)
        self.trainer_step = 0
        self.weight_version = 0
        self.n_starved = 0
        self.n_steps = 0
        self.n_skipped = 0
        self._wait_s = 0.0          # 累計 buffer 飢餓等待（rollout_starved_frac 用）
        self._compute_s = 0.0       # 累計 train_step 時間
        self._last_sync_s = 0.0
        self._last_sync_ok = 0
        self._last_stale = (0.0, 0)  # (mean, max) of cur_step - wv for last batch
        self._last_batch_gen = (0.0, 0)   # (mean, max) gen_len of last training batch
        self._last_batch_n = 0            # 全域 batch 條數（len(batch)）；trainer 回的 n_trajs 是 per-rank
        self._prev_fr = {"stop": 0, "length": 0, "other": 0}  # finish_reason 上次快照（per-interval 比例）
        self._session: aiohttp.ClientSession | None = None
        self._wb = None
        self.dump = None            # RolloutDumpWriter（rollout_dump.enabled 時建）
        self.pool = None            # agentic PoolStore（producer=="agentic" 時建）
        self.pool_ingest = None     # agentic PoolIngestor（write-back）
        self.sampler = None         # agentic PoolSampler（render-drop / role-mix 觀測）

    async def setup(self):
        # aiohttp 預設 TCPConnector(limit=100) → 全域最多 100 條 HTTP 連線，會把 rollout 併發腰斬
        # （target_inflight/semaphore 拉高過 100 也沒用）。限流交給 pool 的 semaphore，這裡放開。
        self._session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=0, limit_per_host=0))
        self.rollout_pool, self.teacher_pool = build_pools(self._session, self.cfg)
        self.rollout_clients = [r.client for r in self.rollout_pool.replicas]
        # rollout dump（存所有 rollouts → dflash 原生 parquet；旁路、脫鉤 hidden GC，V31）
        rd = self.cfg.rollout_dump
        if rd.enabled:
            from opd_v2.rollout_store import RolloutDumpWriter
            self.dump = RolloutDumpWriter(
                self.cfg.rollouts_dir, rows_per_file=rd.rows_per_file,
                flush_interval_s=rd.flush_interval_s, store_meta=rd.store_meta,
                compression=rd.compression,
                provenance={"run_name": self.cfg.run_name,
                            "student": self.cfg.trainer.student_path,
                            "teacher": self.cfg.trainer.teacher_path})
            self.dump.start()
        # producer 選擇（V33）：single_round（單輪 prover OPD，預設）vs agentic（pool-based 多 role）。
        # 唯一差別 = prompt source（iterator）+ produce 是否帶 pool write-back；atom/scheduler/buffer/
        # trainer/teacher/loss/weight-sync 全共用、零改（producer 是個 DI seam）。
        if self.cfg.producer == "agentic":
            from opd_v2.agentic.pool import PoolStore
            from opd_v2.agentic.roles import RolePromptBuilder
            from opd_v2.agentic.sampler import PoolSampler
            from opd_v2.agentic.seed import build_seed
            from opd_v2.agentic.writeback import PoolIngestor
            ag = self.cfg.agentic
            # ★ guard（B1/B2）：max_traj_tokens 須容得下 max bundle cap + 長 reasoning，否則 refine/select
            # 的 long-CoT 會被截斷、靜默被 gate 丟掉（refine 是品質引擎，傷最大）。把 footgun 變顯式失敗。
            need = max(ag.refine_bundle_cap_tokens, ag.select_bundle_cap_tokens) + ag.min_gen_room
            mtt = self.cfg.data_plane.max_traj_tokens
            if mtt < need:
                raise SystemExit(
                    f"agentic: max_traj_tokens={mtt} too small (need >= {need} = max(refine {ag.refine_bundle_cap_tokens}, "
                    f"select {ag.select_bundle_cap_tokens}) + min_gen_room {ag.min_gen_room}). "
                    f"Set MAX_TRAJ_TOKENS=131072 + rollout server --context-length 131072.")
            if ag.max_prompt_tokens > mtt:
                raise SystemExit(f"agentic: max_prompt_tokens={ag.max_prompt_tokens} > max_traj_tokens={mtt} "
                                 f"→ render-pass prompt 可能在 produce 被靜默丟（budget<=0）。降 max_prompt_tokens。")
            self.pool = PoolStore(self.cfg.pool_dir, seed=self.cfg.seed,
                                  max_artifact_chars=ag.max_artifact_chars)
            # build_seed 走 executor：私有 HF load_dataset + 8 萬筆 parse 不 block event loop。
            # ⚠️ headless slurm 連私有 HF 需 HF_TOKEN；建議**先在 login node** 跑
            #    `python -m opd_v2.agentic.seed --run-dir <run>` 預建 seed.jsonl，正式 run 只 load 本地檔（免 auth/免 block）。
            await asyncio.get_running_loop().run_in_executor(None, build_seed, self.cfg)
            self.pool.load()                           # replay seed + artifacts（resume-safe）
            self.pool.start(flush_interval_s=30.0)
            builder = RolePromptBuilder(self.cfg.trainer.student_path, self.cfg)
            self.pool_ingest = PoolIngestor(self.pool, builder.tok, self.cfg)
            self.pool_ingest.start()
            self.sampler = PoolSampler(self.cfg, self.pool, builder)
            prompts = self.sampler.iter_forever()
            n_samples = 1                              # agentic：multiplicity 交給 sampler（非 v1 fan-out）
            produce_fn = functools.partial(
                produce_sample, rollout_pool=self.rollout_pool, teacher_pool=self.teacher_pool,
                store=self.store, cfg=self.cfg, default_wv=lambda: self.weight_version,
                dump=self.dump, pool_ingest=self.pool_ingest)
            log.info("producer=agentic: pool seeded/loaded (max_traj=%d), sampler+ingestor up", mtt)
        else:
            from opd_v2.prompts import iter_prompts_forever
            prompts = iter_prompts_forever(self.cfg)
            n_samples = self.cfg.rollout.n_samples
            produce_fn = functools.partial(
                produce_sample, rollout_pool=self.rollout_pool, teacher_pool=self.teacher_pool,
                store=self.store, cfg=self.cfg, default_wv=lambda: self.weight_version,
                dump=self.dump)
        self.scheduler = Scheduler(
            prompts=prompts, produce=produce_fn,
            buffer=self.buffer, store=self.store,
            target_inflight=self.cfg.data_plane.target_inflight,
            n_samples=n_samples,
            near_full_frac=self.cfg.buffer.near_full_frac)
        await self._wait_servers()
        await self._discover_trainer()
        self._init_wandb()
        # resume：trainer 若從 durable ckpt 續跑（discover 到的 step>0），rollout 此刻仍是 base student
        # → 先做一次 weight sync 把 resumed 權重推上去、把 self.weight_version 對齊（wv = trainer.step）。
        if self.trainer_step > 0:
            log.info("trainer resumed at step=%d → initial weight sync to rollout", self.trainer_step)
            await self.weight_sync()

    async def _wait_servers(self, timeout: float = 1200.0):
        """等 rollout + teacher 都 healthy。"""
        t0 = time.time()
        while time.time() - t0 < timeout:
            r_ok = all(await asyncio.gather(*[c.health() for c in self.rollout_clients]))
            t_ok = all(await asyncio.gather(*[r.client.health() for r in self.teacher_pool.replicas]))
            if r_ok and t_ok:
                log.info("rollout + teacher healthy (%.0fs)", time.time() - t0)
                return
            await asyncio.sleep(3)
        raise TimeoutError("rollout/teacher not healthy in time")

    async def _discover_trainer(self, timeout: float = 1800.0):
        """讀 shared-FS endpoint file（V20）→ 建 trainer client → 等 /health。"""
        t0 = time.time()
        ep = None
        while time.time() - t0 < timeout:
            if os.path.exists(self.cfg.trainer_endpoint_file):
                try:
                    ep = json.load(open(self.cfg.trainer_endpoint_file))
                    break
                except Exception:
                    pass
            await asyncio.sleep(2)
        if ep is None:
            raise TimeoutError("trainer endpoint not registered")
        self.trainer = TrainerHTTPClient(self._session, ep["url"])
        while time.time() - t0 < timeout:
            h = await self.trainer.health()
            if h and h.get("ok"):
                self.trainer_step = int(h.get("step", 0))
                log.info("trainer discovered @ %s (step=%d)", ep["url"], self.trainer_step)
                return
            await asyncio.sleep(3)
        raise TimeoutError("trainer not healthy in time")

    def _init_wandb(self):
        if self.cfg.wandb_mode == "disabled" or os.environ.get("OPD_WANDB", "1") == "0":
            return
        try:
            import wandb
            jid = os.environ.get("SLURM_JOB_ID", "")
            self._wb = wandb.init(project=self.cfg.wandb_project,
                                  name=f"{self.cfg.run_name}-{jid or 'local'}",
                                  mode=self.cfg.wandb_mode, config=self.cfg.to_dict())
            log.info("wandb: %s", getattr(self._wb, "url", "(offline)"))
        except Exception:
            log.exception("wandb init failed; continuing")

    async def weight_sync(self):
        """orchestrator 主導（V22）：/save → parallel pause rollout → update_weights → continue。"""
        t0 = time.time()
        wi = await self.trainer.save()
        path, wv = wi["path"], int(wi["weight_version"])

        async def reload(client):
            await client.pause_generation("in_place")
            try:
                await client.update_weights_from_disk(path, weight_version=wv, flush_cache=False)
            finally:
                await client.continue_generation()
        res = await asyncio.gather(*[reload(c) for c in self.rollout_clients], return_exceptions=True)
        n_ok = sum(1 for r in res if not isinstance(r, Exception))
        self.weight_version = wv
        self._last_sync_s = time.time() - t0
        self._last_sync_ok = n_ok
        log.info("weight sync -> wv=%d (%d/%d rollout replicas, %.1fs)",
                 wv, n_ok, len(self.rollout_clients), self._last_sync_s)
        return wv

    async def run(self, max_steps: int):
        stop = asyncio.Event()
        sched_task = asyncio.create_task(self.scheduler.run(stop))
        cfg = self.cfg
        g4_every = max(1, cfg.trainer.g4_every)
        log_every = max(1, cfg.trainer.log_every)
        try:
            want_batch = max(1, cfg.trainer.train_batch_trajs)
            last_prod = 0
            prog_t0 = time.time()
            while self.trainer_step < max_steps:
                # 累積到一個**完整 batch** 才取（不要 buffer 有 1 條就開一步——梯度吵又浪費 weight sync）。
                # watchdog 盯「producer 有沒有進度」而非「buffer 空」：慢但有在生 → 耐心等（long CoT rollout
                # 本就慢、user 要 trainer 等久一點）；完全沒新 traj 超過 starve_timeout 才視為卡死。
                while (len(self.buffer) < want_batch
                       and not sched_task.done() and not stop.is_set()):
                    prod = self.scheduler.stats()["produced"]
                    if prod > last_prod:
                        last_prod = prod
                        prog_t0 = time.time()       # 有新 traj 進來 = producer 有進度，重置計時
                    elif time.time() - prog_t0 > cfg.data_plane.starve_timeout_s:
                        raise RuntimeError(
                            f"producers no progress > {cfg.data_plane.starve_timeout_s:.0f}s "
                            f"(buf={len(self.buffer)}/{want_batch}, produced={prod})")
                    self.n_starved += 1
                    await asyncio.sleep(0.2)
                    self._wait_s += 0.2             # 等湊滿 batch（= rollout-bound）累計
                if sched_task.done() and len(self.buffer) == 0:
                    await sched_task                # prompt 枯竭且 buffer 空 → 乾淨收尾
                    break
                batch, stale = self.buffer.get_batch(
                    want_batch, cur_step=self.trainer_step,
                    max_staleness=cfg.buffer.max_staleness)
                if stale:
                    self.store.delete_handles([t.handle for t in stale])
                if not batch:
                    continue
                ages = [self.trainer_step - t.wv for t in batch]
                self._last_stale = (sum(ages) / len(ages), max(ages))
                gls = [t.gen_len for t in batch]            # 本訓練 batch 的生成長度（wandb 自己平滑）
                self._last_batch_gen = (sum(gls) / len(gls), max(gls))
                self._last_batch_n = len(batch)             # 全域 batch 條數（送進 trainer 的）
                want_g4 = (self.n_steps % g4_every == 0)
                _t = time.time()
                m = await self.trainer.train_step([t.to_wire() for t in batch], want_g4=want_g4)
                self._compute_s += time.time() - _t
                # GC：batch hidden（trainer 各 rank 已讀完）+ LPT-dropped
                self.store.delete_handles([t.handle for t in batch])
                for d in m.get("dropped", []) or []:
                    self.store.delete(d["handle"]["path"])
                self.n_steps += 1
                if m.get("skipped"):
                    self.n_skipped += 1
                    log.warning("train_step skipped (collective-safe gate; n_read_fail=%s)",
                                m.get("n_read_fail"))
                    continue
                self.trainer_step = int(m["step"])
                if self.trainer_step % cfg.trainer.weight_sync_every == 0:
                    await self.weight_sync()
                # durable checkpoint（DCP model+optim+sched，永不覆寫；rollout-bound 下 trainer 這段被擋
                # 不影響吞吐——scheduler 背景照常生、buffer 吸收，見 DECISIONS）。
                ck = cfg.trainer.checkpoint_every
                if ck and self.trainer_step % ck == 0:
                    _t = time.time()
                    ci = await self.trainer.checkpoint(hf=cfg.trainer.hf_export,
                                                       keep=cfg.trainer.checkpoint_keep)
                    log.info("durable checkpoint -> %s (%.1fs)", ci.get("dir"), time.time() - _t)
                if self.n_steps % log_every == 0 or want_g4:
                    self._log_step(m)
            log.info("reached max_steps=%d (trainer_step=%d)", max_steps, self.trainer_step)
        finally:
            stop.set()
            await sched_task
            try:
                await self.trainer.stop()
            except Exception:
                log.exception("trainer stop failed")
            await self.shutdown()

    def _log_step(self, m: dict):
        bs = self.buffer.stats()
        ss = self.scheduler.stats()
        rp = self.rollout_pool.stats()
        tp = self.teacher_pool.stats()
        n_fs, b_fs = self.store.usage()
        served = bs["n_served"]
        stale_drop_rate = bs["n_dropped_stale"] / max(1, served + bs["n_dropped_stale"])
        starved_frac = self._wait_s / max(1e-9, self._wait_s + self._compute_s)
        skip_rate = self.n_skipped / max(1, self.n_steps)
        st_mean, st_max = self._last_stale
        bgl_mean, bgl_max = self._last_batch_gen          # 本訓練 batch 的 gen_len（wandb 自己平滑）
        # finish_reason per-interval 比例（自上次 log；EOS-停 vs 撞窗口-停 = 截斷監控）
        d_stop = ss["fr_stop"] - self._prev_fr["stop"]
        d_len = ss["fr_length"] - self._prev_fr["length"]
        d_oth = ss["fr_other"] - self._prev_fr["other"]
        d_tot = d_stop + d_len + d_oth
        eos_rate = d_stop / d_tot if d_tot else 0.0
        length_rate = d_len / d_tot if d_tot else 0.0
        self._prev_fr = {"stop": ss["fr_stop"], "length": ss["fr_length"], "other": ss["fr_other"]}
        # admission filter：cap-hit 等被剔除的比例（dropped/(produced+dropped)；不進訓練 buffer）
        admit_dropped = ss.get("admit_dropped_total", 0)
        admit_drop_rate = admit_dropped / max(1, ss["produced"] + admit_dropped)
        msg = (f"step={self.trainer_step} loss={m.get('loss'):.4f} gnorm={m.get('gnorm')} "
               f"lr={m.get('lr')} gtok={m.get('global_target_tokens')} stale={st_mean:.1f}/{st_max} | "
               f"buf={bs['size']}/{bs['tokens']} stale_drop={stale_drop_rate:.2%} starved_frac={starved_frac:.2%} | "
               f"sched prod={ss['produced']} fail={ss['failed']} genlen={bgl_mean:.0f}/{bgl_max} "
               f"eos={eos_rate:.0%} len={length_rate:.0%} drop={admit_drop_rate:.1%} | "
               f"pool r={rp['in_flight']}/{rp['concurrency']}({rp['live']}live,{rp['errors']}err) "
               f"t={tp['in_flight']}/{tp['concurrency']} | fs={n_fs}f/{b_fs/1e9:.1f}G skip={skip_rate:.2%}")
        if self.dump is not None:
            ds = self.dump.stats()
            msg += f" | dump={ds['n_written']}r/{ds['n_files']}f/{ds['n_bytes']/1e9:.2f}G"
        if self.pool is not None:
            ps = self.pool.stats()
            sc = ps["student"]
            msg += (f" | pool P/V/R={ps['n_proofs']}/{ps['n_verifies']}/{ps['n_refined']} "
                    f"stu p/v/r/s={sc['prove']}/{sc['verify']}/{sc['refine']}/{sc['select']}")
        if "learn_reverse_kl" in m:
            msg += (f" | rKL={m['learn_reverse_kl']:.4f} fKL={m.get('learn_forward_kl'):.4f} "
                    f"ent={m.get('learn_entropy'):.3f}")
            if "learn_eos_student_prob" in m:   # V34 length 自我放大 leading indicator
                msg += (f" eosP={m['learn_eos_student_prob']:.3f} "
                        f"eosNLL={m.get('learn_eos_teacher_nll'):.2f} tgap={m.get('learn_tail_entropy_gap'):+.2f}")
        if "g4_top1" in m:
            msg += f" g4={m['g4_top1']:.3f}/{m.get('g4_top5'):.3f}"
        log.info(msg)
        if self._wb is not None:
            rec = {
                # optimization
                "train/loss": m.get("loss"), "train/gnorm": m.get("gnorm"), "train/lr": m.get("lr"),
                "train/peak_gb": m.get("peak_gb"),
                "train/n_trajs": self._last_batch_n,          # 全域 batch 條數（= train_batch_trajs）
                "train/n_trajs_rank0": m.get("n_trajs"),      # rank-0 per-rank（LPT 後，~global/world）
                "train/n_read_fail": m.get("n_read_fail"),
                "tokens/global_target": m.get("global_target_tokens"),
                # learning-quality（want_g4 步才有）
                # on-policy health
                "onpolicy/staleness_mean": st_mean, "onpolicy/staleness_max": st_max,
                "onpolicy/stale_drop_rate": stale_drop_rate,
                "onpolicy/weight_version": self.weight_version,
                "onpolicy/sync_latency_s": self._last_sync_s,
                "onpolicy/sync_replicas_ok": self._last_sync_ok,
                # data-plane / throughput
                "perf/rollout_starved_frac": starved_frac,
                "perf/starved": self.n_starved, "perf/skipped": self.n_skipped,
                "perf/skip_rate": skip_rate,
                "buffer/size": bs["size"], "buffer/tokens": bs["tokens"],
                "buffer/dropped_stale": bs["n_dropped_stale"],
                "buffer/dropped_overflow": bs["n_dropped_overflow"],
                "sched/produced": ss["produced"], "sched/failed": ss["failed"],
                # admission filter（cap-hit 等剔除；不進訓練。drop_rate 想看著它把 self-amplification 壓住）
                "sched/admit_drop_rate": admit_drop_rate,
                "sched/admit_dropped_total": admit_dropped,
                **{f"sched/admit_dropped_{k}": v for k, v in ss.get("admit_dropped", {}).items()},
                # 生成長度：本訓練 batch 的 avg/max（每步記原始值，平滑交給 wandb）
                "rollout/gen_len": bgl_mean, "rollout/gen_len_max": bgl_max,
                # 停止原因比例（per-interval；length=撞窗口被截 → 想降到接近 0）
                "rollout/eos_rate": eos_rate, "rollout/length_rate": length_rate,
                "pool/rollout_inflight": rp["in_flight"], "pool/rollout_util": rp["in_flight"] / max(1, rp["concurrency"]),
                "pool/rollout_live": rp["live"], "pool/rollout_errors": rp["errors"],
                "pool/teacher_inflight": tp["in_flight"], "pool/teacher_util": tp["in_flight"] / max(1, tp["concurrency"]),
                "pool/teacher_live": tp["live"], "pool/teacher_errors": tp["errors"],
                # 累積完成數（持續往上爬 = server 有在做事；util/inflight 是瞬時快照、閒置時=0 易誤判死掉）
                "pool/rollout_done": rp["done"], "pool/teacher_done": tp["done"],
                "hidden_fs/n_files": n_fs, "hidden_fs/bytes": b_fs,
            }
            if self.dump is not None:
                ds = self.dump.stats()
                rec["rollout_dump/n_written"] = ds["n_written"]
                rec["rollout_dump/n_files"] = ds["n_files"]
                rec["rollout_dump/gb"] = ds["n_bytes"] / 1e9
                rec["rollout_dump/queue"] = ds["queue"]
                rec["rollout_dump/queue_high"] = ds["queue_high"]
            if self.pool is not None:
                ps = self.pool.stats()
                rec["agentic/pool_proofs"] = ps["n_proofs"]
                rec["agentic/pool_verifies"] = ps["n_verifies"]
                rec["agentic/pool_refined"] = ps["n_refined"]
                for r in ("prove", "verify", "refine", "select"):
                    rec[f"agentic/student_{r}"] = ps["student"][r]
                if self.pool_ingest is not None:
                    ig = self.pool_ingest.stats()
                    rec["agentic/ingest_seen"] = ig["seen"]
                    rec["agentic/ingest_rejected"] = ig["rejected"]
                    rec["agentic/ingest_queue"] = ig["queue"]
                if self.sampler is not None:
                    ss2 = self.sampler.stats()
                    for r in ("prove", "verify", "refine", "select"):
                        rec[f"agentic/yielded_{r}"] = ss2["yielded"][r]
                        rec[f"agentic/render_dropped_{r}"] = ss2["render_dropped"][r]
                    rec["agentic/fallback_prove"] = ss2["fallback_prove"]
            for k in ("learn_reverse_kl", "learn_forward_kl", "learn_entropy", "learn_teacher_nll",
                      "learn_eos_student_prob", "learn_eos_teacher_nll", "learn_tail_entropy_gap"):
                if k in m:
                    rec[k.replace("learn_", "learn/")] = m[k]
            if "g4_top1" in m:
                rec["g4/top1"] = m["g4_top1"]
                rec["g4/top5"] = m.get("g4_top5")
            self._wb.log(rec, step=self.trainer_step)

    async def shutdown(self):
        if self.pool_ingest is not None:
            try:
                await self.pool_ingest.close()   # drain 待 ingest 的 rollouts
            except Exception:
                log.exception("pool ingestor close failed")
        if self.pool is not None:
            try:
                await self.pool.close()          # 停 flusher + persist 殘留
            except Exception:
                log.exception("pool close failed")
        if self.dump is not None:
            try:
                await self.dump.close()        # flush 殘留 rollouts + 寫 dataset_info.json
            except Exception:
                log.exception("rollout dump close failed")
        if self._wb is not None:
            try:
                self._wb.finish()
            except Exception:
                pass
        # 清殘留 hidden（孤兒兜底）
        n = self.store.sweep_ttl(0)
        if n:
            log.info("final GC swept %d leftover hidden files", n)
        if self._session is not None:
            await self._session.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", default=os.environ.get("OPD_RUN_DIR", ""))
    ap.add_argument("--max-steps", type=int, default=None)
    a = ap.parse_args()
    if not a.run_dir:
        raise SystemExit("--run-dir (or OPD_RUN_DIR) required")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s: %(message)s")
    for noisy in ("aiohttp", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    cfg = OPDConfig.load(a.run_dir)
    max_steps = a.max_steps if a.max_steps is not None else cfg.trainer.total_steps

    async def _run():
        orch = Orchestrator(cfg)
        await orch.setup()
        await orch.run(max_steps)

    asyncio.run(_run())
    return 0


if __name__ == "__main__":
    sys.exit(main())
