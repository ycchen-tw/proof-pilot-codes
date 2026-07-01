"""Continuous pool loop (v2) — streaming engine + concurrency gate.

Same lifecycle as v1 (seed provers -> verify-on-complete -> merge-refine -> selector vote
in a reserved tail) but built on the streaming StreamingEngine (loop / time force-close
early-stop) and a ConcurrencyGate (prove/refine capped at GEN_CAP, verify prioritised).
See DESIGN.md. v1 modules parser/bundle/clean/prompts/rank are reused unchanged.
"""
from __future__ import annotations

import asyncio
import json
import random
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))   # reuse v1 shared modules

from bundle import build_refine_bundle, build_select_bundle           # noqa: E402
from clean import deterministic_clean, fallback_preamble              # noqa: E402
from parser import (ProofPackage, RefinedPackage, parse_proof_package,  # noqa: E402
                    parse_refined_package, parse_selected_id, parse_verification)
from prompts import (render_prover_prompt, render_refiner_prompt,      # noqa: E402
                     render_selector_prompt, render_verifier_prompt, to_messages)
from loopguard import degenerate                                       # noqa: E402

_SELECT_MARGIN_S = 30.0
_MIN_SELECT_S = 60.0
_MIN_ACTIVE_FRAC = 0.7
_MIN_GEN_S = 180.0          # don't start a new prove/refine with less than this active-time left
_MAX_CONSEC_ERR = 24
_MAX_GENS = 2000


@dataclass
class Candidate:
    cid: str
    proof: str
    self_eval: str
    self_score: float | None
    source: str                    # "prove" | "refine"
    gen: int
    salvaged: bool = False
    parents: list = field(default_factory=list)   # cids merged into this refine (lineage)
    verifs: list = field(default_factory=list)

    def scores(self) -> list[float]:
        return [v.score for v in self.verifs if v.score is not None]

    def mean(self) -> float:
        s = self.scores(); return sum(s) / len(s) if s else -1.0

    def minv(self) -> float:
        s = self.scores(); return min(s) if s else -1.0

    def agreement(self) -> float:
        s = self.scores(); return 1.0 if s and max(s) == min(s) else 0.0

    def rank_key(self):
        # verify score first (mean, min); THEN prefer natural-stop over salvaged even when
        # verify ties; agreement/self_score only break remaining ties.
        return (self.mean(), self.minv(), 0.0 if self.salvaged else 1.0, self.agreement(),
                self.self_score if self.self_score is not None else -1.0)

    def as_proofpkg(self, *, with_self_eval: bool = True) -> ProofPackage:
        return ProofPackage(candidate_id=self.cid, proof=self.proof,
                            self_eval=self.self_eval if with_self_eval else "",
                            self_score=self.self_score, valid=True, call={})


class PoolSolver:
    def __init__(self, engine, gate, problem: str, *, deadline: float,
                 select_reserve_s: float = 600.0, init_provers: int = 6, verify_k: int = 3,
                 refine_inputs: int = 4, refine_min_seeds: int = 2, select_bundle_n: int = 4,
                 num_selectors: int = 5, diversity_p: float = 0.35, refine_min_score: float = 0.0,
                 dump_path: str | None = None):
        self.E = engine
        self.gate = gate
        self.problem = problem
        self.deadline = deadline
        budget = max(0.0, deadline - time.monotonic())
        reserve = min(select_reserve_s, budget * (1.0 - _MIN_ACTIVE_FRAC))
        self.active_deadline = deadline - reserve
        self.verify_k = verify_k
        self.init_provers = init_provers
        self.refine_inputs = refine_inputs
        self.refine_min_seeds = refine_min_seeds   # min verified candidates to merge-refine (else prove)
        self.select_bundle_n = select_bundle_n
        self.num_selectors = num_selectors
        self.diversity_p = diversity_p
        self.refine_min_score = refine_min_score
        self.dump_path = dump_path
        # realtime append-only event stream (one JSON line per completed call / verify / final)
        # for external `tail -f` while the run is in flight — the full _dump still happens at the end.
        self.events_path = (dump_path + ".events.jsonl") if dump_path else None

        self.prover_msgs = to_messages(render_prover_prompt(problem))
        self.candidates: list[Candidate] = []
        self.tasks: set[asyncio.Task] = set()
        self.active = True
        self._n_prove = 0
        self._n_refine = 0
        self._gen_inflight = 0
        self.target_live = gate.gen_cap          # keep ~gen_cap prove/refine in flight
        self._kick = asyncio.Event()
        self._consec_err = 0
        self.calls: list[dict] = []
        self.rng = random.Random(hash(problem) & 0xFFFF)
        self._t0 = time.monotonic()

    # ---- task plumbing ----
    def _spawn(self, coro) -> asyncio.Task:
        t = asyncio.create_task(coro)
        self.tasks.add(t)
        t.add_done_callback(lambda task: (self.tasks.discard(task), self._kick.set()))
        return t

    def _spawn_gen(self, coro) -> None:
        self._gen_inflight += 1
        t = self._spawn(coro)
        t.add_done_callback(lambda _t: self._dec_gen())

    def _dec_gen(self) -> None:
        self._gen_inflight -= 1

    def _note(self, rec: dict) -> None:
        self._consec_err = self._consec_err + 1 if rec.get("error") else 0

    def _breaker_open(self) -> bool:
        return self._consec_err >= _MAX_CONSEC_ERR or (self._n_prove + self._n_refine) >= _MAX_GENS

    def _can_gen(self) -> bool:
        # wall-clock spawn gate (no est_tps): only start a gen with enough active-time left that
        # it can produce a real proof (the streaming engine force-closes near active_deadline).
        return (self.active_deadline - time.monotonic()) > _MIN_GEN_S

    def _verified(self) -> list[Candidate]:
        return [c for c in self.candidates if c.scores()]

    def _emit(self, ev: dict) -> None:
        """Append one event (with a t0-relative timestamp) as a JSON line for realtime external
        tracing. Never raises — a logging failure must never sink the run."""
        if not self.events_path:
            return
        try:
            rec = {"t": round(time.monotonic() - self._t0, 1), **ev}
            with open(self.events_path, "a") as f:
                f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
                f.flush()
        except Exception:  # noqa: BLE001
            pass

    # ---- workers ----
    async def _prove(self) -> None:
        if not self.active:
            return
        i = self._n_prove; self._n_prove += 1
        async with self.gate.gen():
            if not self.active:
                return
            rec = await self.E.generate(self.prover_msgs, label=f"prove/P{i}", t0=self._t0)
        self.calls.append(rec); self._note(rec)
        pkg = parse_proof_package(rec, f"P{i}")
        if pkg.valid:
            c = Candidate(pkg.candidate_id, pkg.proof, pkg.self_eval, pkg.self_score, "prove", 0,
                          salvaged=bool(rec.get("salvaged")))
            self.candidates.append(c)
            for j in range(self.verify_k):
                self._spawn(self._verify(c, j))
        self._emit({"type": "prove", "cid": f"P{i}", "valid": pkg.valid,
                    "stop_reason": rec.get("stop_reason"), "finish_reason": rec.get("finish_reason"),
                    "salvaged": bool(rec.get("salvaged")), "completion_tokens": rec.get("completion_tokens"),
                    "proof_len": len(pkg.proof or ""), "proof": pkg.proof if pkg.valid else None,
                    "reasoning_content": rec.get("reasoning_content")})

    async def _verify(self, cand: Candidate, j: int) -> None:
        if not self.active:
            return
        msgs = to_messages(render_verifier_prompt(self.problem, cand.proof, cand.self_eval))
        async with self.gate.verify():                 # verify has priority over prove/refine
            if not self.active:
                return
            rec = await self.E.generate(msgs, label=f"verify/{cand.cid}/{j}", t0=self._t0)
        self.calls.append(rec); self._note(rec)
        v = parse_verification(rec, cand.cid, j)
        cand.verifs.append(v)
        self._emit({"type": "verify", "cid": cand.cid, "j": j, "score": v.score,
                    "cand_mean": cand.mean(), "content": rec.get("content"),
                    "reasoning_content": rec.get("reasoning_content")})
        self._kick.set()

    async def _refine(self, inputs: list[Candidate]) -> None:
        if not self.active:
            return
        n = self._n_refine; self._n_refine += 1
        ranked = sorted(inputs, key=lambda c: c.rank_key(), reverse=True)
        verifs = [v for c in ranked for v in c.verifs]
        # refine bundle WITHOUT prover self-eval (unreliable ~92% self-score 1); verifier reviews stay
        bundle = build_refine_bundle([c.as_proofpkg(with_self_eval=False) for c in ranked], verifs)
        msgs = to_messages(render_refiner_prompt(self.problem, bundle))
        async with self.gate.gen():
            if not self.active:
                return
            rec = await self.E.generate(msgs, label=f"refine/R{n}", t0=self._t0)
        self.calls.append(rec); self._note(rec)
        pkg = parse_refined_package(rec, f"R{n}")
        parents = [p.cid for p in ranked]
        if pkg.valid:
            gen = max((p.gen for p in inputs), default=0) + 1
            c = Candidate(f"R{n}", pkg.proof, pkg.self_eval, pkg.self_score, "refine", gen,
                          salvaged=bool(rec.get("salvaged")),
                          parents=parents)                      # lineage edges
            self.candidates.append(c)
            for j in range(self.verify_k):
                self._spawn(self._verify(c, j))
        self._emit({"type": "refine", "cid": f"R{n}", "valid": pkg.valid, "parents": parents,
                    "stop_reason": rec.get("stop_reason"), "salvaged": bool(rec.get("salvaged")),
                    "completion_tokens": rec.get("completion_tokens"),
                    "proof_len": len(pkg.proof or ""), "proof": pkg.proof if pkg.valid else None,
                    "reasoning_content": rec.get("reasoning_content")})

    def _pick_refine_inputs(self) -> list[Candidate]:
        # refine-seed order: mean first; ties -> prefer natural-stop over salvaged;
        # remaining ties -> random sample (fresh each call, so equal-score candidates
        # — e.g. the all-0 regime — get explored rather than always taken by index).
        ranked = sorted(self._verified(),
                        key=lambda c: (c.mean(), 0.0 if c.salvaged else 1.0, self.rng.random()),
                        reverse=True)
        return ranked[: self.refine_inputs]

    async def _refine_driver(self) -> None:
        try:
            while self.active and time.monotonic() < self.active_deadline:
                while (self.active and self._gen_inflight < self.target_live and self._can_gen()
                       and not self._breaker_open()):
                    inputs = self._pick_refine_inputs()
                    if len(inputs) >= self.refine_min_seeds:
                        self._spawn_gen(self._refine(inputs))
                    else:
                        self._spawn_gen(self._prove())
                try:
                    await asyncio.wait_for(self._kick.wait(),
                                           timeout=min(2.0, max(0.1, self.active_deadline - time.monotonic())))
                except asyncio.TimeoutError:
                    pass
                self._kick.clear()
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001 — surface a driver crash instead of silently dying
            self.calls.append({"label": "driver/error", "error": repr(e)})

    # ---- selection ----
    @staticmethod
    def _clean_nondegen(proof: str) -> str:
        c = deterministic_clean(proof)
        return c if c and not degenerate(c) else ""

    async def _select_phase(self) -> dict:
        self.E.deadline = self.deadline
        verified = sorted(self._verified(), key=lambda c: c.rank_key(), reverse=True)
        if not verified:
            # no verified candidate: best NON-degenerate raw proof (NOT just the longest — a loop
            # is the longest), else preamble.
            raw = sorted(self.candidates, key=lambda c: len(c.proof or ""), reverse=True)
            proof = next((self._clean_nondegen(c.proof) for c in raw if self._clean_nondegen(c.proof)), "")
            return {"final_proof": proof or fallback_preamble(),
                    "final_source": "fallback_no_verified", "selected_id": None}
        top = verified[: self.select_bundle_n]
        refined_pkgs = [RefinedPackage(refiner_id=c.cid, proof=c.proof, self_eval=c.self_eval,
                                       self_score=c.self_score, valid=True, call={}) for c in top]
        bundle, id_map = build_select_bundle(refined_pkgs)
        sel_msgs = to_messages(render_selector_prompt(self.problem, bundle))
        sel_budget = max(_MIN_SELECT_S, self.deadline - time.monotonic() - _SELECT_MARGIN_S)
        try:
            votes_calls = await asyncio.wait_for(
                asyncio.gather(*(self.E.generate(sel_msgs, label=f"select/S{i}", t0=self._t0)
                                 for i in range(self.num_selectors))),
                timeout=sel_budget)
        except asyncio.TimeoutError:
            return {"final_proof": deterministic_clean(top[0].proof),
                    "final_source": "fallback_select_timeout", "selected_id": None, "selected_ids": []}
        self.calls.extend(votes_calls)
        votes = [parse_selected_id(c["content"]) for c in votes_calls]
        valid = [v for v in votes if v in id_map]
        if valid:
            cnt = Counter(valid); order = list(id_map)
            winner = max(cnt, key=lambda k: (cnt[k], -order.index(k)))
            return {"final_proof": deterministic_clean(id_map[winner]),
                    "final_source": f"select:{winner}({cnt[winner]}/{self.num_selectors})",
                    "selected_id": winner, "selected_ids": votes}
        return {"final_proof": deterministic_clean(top[0].proof),
                "final_source": "fallback_top_scored", "selected_id": None, "selected_ids": votes}

    async def _drain(self) -> None:
        self.active = False
        for t in list(self.tasks):
            t.cancel()
        try:
            await asyncio.wait_for(asyncio.gather(*self.tasks, return_exceptions=True), timeout=10.0)
        except asyncio.TimeoutError:
            pass

    def _dump(self, result: dict) -> None:
        self._emit({"type": "final", "final_source": result.get("final_source"),
                    "selected_id": result.get("selected_id"),
                    "proof_len": len(result.get("final_proof") or ""),
                    "final_proof": result.get("final_proof")})
        if not self.dump_path:
            return
        cands = [{"cid": c.cid, "source": c.source, "gen": c.gen, "salvaged": c.salvaged,
                  "parents": c.parents, "self_score": c.self_score, "scores": c.scores(),
                  "mean": c.mean(), "minv": c.minv(), "won": c.cid == result.get("selected_id"),
                  "proof_len": len(c.proof or ""), "proof": c.proof,
                  "verifs": [{"score": v.score, "text": v.text} for v in c.verifs]}
                 for c in self.candidates]
        calls = [{"label": r.get("label"), "seed": r.get("seed"), "temperature": r.get("temperature"),
                  "max_tokens": r.get("max_tokens"), "finish_reason": r.get("finish_reason"),
                  "stop_reason": r.get("stop_reason"), "t_start": r.get("t_start"),
                  "t_end": r.get("t_end"), "latency_s": r.get("latency_s"),
                  "prompt_tokens": r.get("prompt_tokens"), "completion_tokens": r.get("completion_tokens"),
                  "reasoning_tokens": r.get("reasoning_tokens"), "salvaged": r.get("salvaged"),
                  "error": r.get("error"), "content": r.get("content"),
                  "reasoning_len": len(r.get("reasoning_content") or ""),
                  "reasoning_content": r.get("reasoning_content")}
                 for r in self.calls]
        try:
            with open(self.dump_path, "w") as f:
                json.dump({"result": result, "candidates": cands, "calls": calls},
                          f, ensure_ascii=False, default=str)
        except Exception:  # noqa: BLE001
            pass

    # ---- entry ----
    async def solve(self) -> dict:
        self._t0 = time.monotonic()
        self.E.deadline = self.active_deadline
        for _ in range(self.init_provers):
            self._spawn_gen(self._prove())
        driver = asyncio.create_task(self._refine_driver())
        await asyncio.sleep(max(0.0, self.active_deadline - time.monotonic()))
        driver.cancel()
        with __import__("contextlib").suppress(asyncio.CancelledError):
            await driver
        await self._drain()
        result = await self._select_phase()
        verified = self._verified()
        result.update(wall_s=time.monotonic() - self._t0,
                      counts={"n_candidates": len(self.candidates), "n_verified": len(verified),
                              "n_prove": self._n_prove, "n_refine": self._n_refine,
                              "max_gen": max((c.gen for c in self.candidates), default=0)},
                      totals={"n_calls": len(self.calls),
                              "n_salvaged": sum(1 for c in self.calls if c.get("salvaged")),
                              "n_loop": sum(1 for c in self.calls if c.get("stop_reason") == "loop"),
                              "n_forceclose": sum(1 for c in self.calls if c.get("stop_reason") == "time_forceclose"),
                              "completion_tokens": sum(c.get("completion_tokens") or 0 for c in self.calls)})
        self._dump(result)
        return result


async def solve_pooled(problem: str, engine, gate, *, deadline: float, **kw) -> dict:
    return await PoolSolver(engine, gate, problem, deadline=deadline, **kw).solve()
