"""Continuous pool-based agentic loop — fills the full per-problem budget.

Replaces the fixed-wave prove→verify→rank→refine→select barrier (pipeline.py) with a continuous,
work-stealing pool that keeps generating + refining candidates until a reserved selection window,
then votes. Designed to (a) eliminate head-of-line blocking (a finished proof is verified
immediately, not after the slowest sibling), (b) keep concurrency saturated, (c) use the whole hour.

Lifecycle (one problem):
  ACTIVE phase  [0 .. deadline - select_reserve_s]:
    - seed `init_provers` provers
    - prove done & valid        -> spawn its verifiers
    - verify done               -> candidate enters the pool (now has a score)
    - refiner driver: whenever the pool has >=2 verified candidates and a slot is free, spawn a
      merge-refine over the top-k (occasionally a random subset for diversity)
    - refine done & valid       -> spawn its verifiers -> re-enters the pool (can be merged again)
    Every model call shares one concurrency semaphore; per-call max_tokens is capped by the
    remaining ACTIVE time so nothing bleeds into the selection window.
  SELECT phase  [last select_reserve_s]:
    - stop spawning, cancel in-flight generations (httpx cancel -> sglang abort)
    - run selectors over the top-N pooled candidates, majority vote -> final proof
    - no valid vote -> highest verifier-scored candidate (never empty)

Reuses Engine (watchdog + salvage), the prompts, parser, bundle, clean from the fixed pipeline.
"""
from __future__ import annotations

import asyncio
import json
import random
import time
from collections import Counter
from dataclasses import dataclass, field

from bundle import build_refine_bundle, build_select_bundle
from clean import deterministic_clean, fallback_preamble
from parser import (ProofPackage, RefinedPackage, parse_proof_package, parse_refined_package,
                    parse_selected_id, parse_verification)
from prompts import (render_prover_prompt, render_refiner_prompt,
                     render_selector_prompt, render_verifier_prompt, to_messages)

# safety guards (commit 1)
_SELECT_MARGIN_S = 30.0   # finish the selector vote this far before the hard per-problem deadline
_MIN_SELECT_S = 60.0      # never give the selector vote less than this, even on a tight budget
_MIN_ACTIVE_FRAC = 0.7    # ACTIVE phase always keeps at least this fraction of the budget
# circuit breaker: if the server dies mid-run, generations error in microseconds and the driver
# would otherwise busy-spawn millions of doomed tasks. Stop spawning after this many CONSECUTIVE
# errored generations; _MAX_GENS is an absolute backstop far above any real run (~50-150 gens).
_MAX_CONSEC_ERR = 24
_MAX_GENS = 2000


@dataclass
class Candidate:
    cid: str                       # P0.. (prove) / R0.. (refine)
    proof: str
    self_eval: str
    self_score: float | None
    source: str                    # "prove" | "refine"
    gen: int                       # refinement generation (0 = original)
    salvaged: bool = False         # B3: came from a force-close-think rescue (CoT truncated)
    verifs: list = field(default_factory=list)   # VerificationPackage list

    def scores(self) -> list[float]:
        return [v.score for v in self.verifs if v.score is not None]

    def mean(self) -> float:
        s = self.scores(); return sum(s) / len(s) if s else -1.0

    def minv(self) -> float:
        s = self.scores(); return min(s) if s else -1.0

    def agreement(self) -> float:
        s = self.scores(); return 1.0 if s and max(s) == min(s) else 0.0

    def rank_key(self):
        # B3: discrete verifier scores ({0,0.5,1}) tie a lot — break ties by verifier *agreement*
        # and by "not salvaged" (a clean EOS proof beats a truncated-then-rescued one), NOT by
        # length (long != correct). self_score is the weakest signal so it comes last.
        return (self.mean(), self.minv(), self.agreement(), 0.0 if self.salvaged else 1.0,
                self.self_score if self.self_score is not None else -1.0)

    def as_proofpkg(self) -> ProofPackage:
        return ProofPackage(candidate_id=self.cid, proof=self.proof, self_eval=self.self_eval,
                            self_score=self.self_score, valid=True, call={})


class PoolSolver:
    def __init__(self, engine, problem: str, *, deadline: float, select_reserve_s: float = 600.0,
                 concurrency: int = 12, init_provers: int = 6, verify_k: int = 3,
                 refine_inputs: int = 4, select_bundle_n: int = 4, num_selectors: int = 5,
                 diversity_p: float = 0.35, refine_min_score: float = 0.0, gen_gate_frac: float = 0.35,
                 dump_path: str | None = None):
        self.E = engine
        self.problem = problem
        self.deadline = deadline
        # A3: clamp the reserve so a small budget can't push active_deadline into the past
        # (which would skip ACTIVE entirely and hand back only a preamble). ACTIVE always keeps
        # >= _MIN_ACTIVE_FRAC of the budget.
        budget = max(0.0, deadline - time.monotonic())
        reserve = min(select_reserve_s, budget * (1.0 - _MIN_ACTIVE_FRAC))
        self.active_deadline = deadline - reserve
        self.sem = asyncio.Semaphore(concurrency)
        self.verify_k = verify_k
        self.init_provers = init_provers
        self.refine_inputs = refine_inputs
        self.select_bundle_n = select_bundle_n
        self.num_selectors = num_selectors
        self.diversity_p = diversity_p
        self.refine_min_score = refine_min_score   # B3: only refine candidates this good or better
        self.gen_gate_frac = gen_gate_frac         # B1: only start a gen if >= this frac of call_cap fits
        self.dump_path = dump_path                 # if set, write the full per-candidate + per-call trace

        self.prover_msgs = to_messages(render_prover_prompt(problem))
        self.candidates: list[Candidate] = []          # all valid proofs/refines (may lack verifs)
        self.tasks: set[asyncio.Task] = set()
        self.active = True
        self._n_prove = 0
        self._n_refine = 0
        self._live = 0                                  # all worker tasks alive (info only)
        # B2: the driver tops up by *its own* in-flight generations, NOT total task count — so a
        # backlog of queued verifiers can no longer starve the refiner.
        self._gen_inflight = 0                          # driver-spawned prove/refine tasks alive
        self.target_live = concurrency                  # keep ~this many driver gens in flight
        self._kick = asyncio.Event()                    # "state changed" (slot freed or new material)
        self._consec_err = 0                            # consecutive errored generations (server-down breaker)
        self.calls: list[dict] = []                    # full trace
        self.rng = random.Random(hash(problem) & 0xFFFF)

    # ---- task plumbing ----
    def _spawn(self, coro) -> asyncio.Task:
        t = asyncio.create_task(coro)
        self.tasks.add(t)
        self._live += 1

        def _done(task: asyncio.Task) -> None:
            self.tasks.discard(task)
            self._live -= 1
            self._kick.set()                            # a slot freed -> driver should refill
        t.add_done_callback(_done)
        return t

    def _spawn_gen(self, coro) -> None:
        """Spawn a driver-owned generation (prove/refine) and account it against target_live."""
        self._gen_inflight += 1                         # incremented synchronously -> no burst
        t = self._spawn(coro)
        t.add_done_callback(lambda _t: self._dec_gen())

    def _dec_gen(self) -> None:
        self._gen_inflight -= 1

    def _note(self, rec: dict) -> None:
        """Track consecutive errors so the driver can stop spawning if the server has died."""
        self._consec_err = self._consec_err + 1 if rec.get("error") else 0

    def _breaker_open(self) -> bool:
        return self._consec_err >= _MAX_CONSEC_ERR or (self._n_prove + self._n_refine) >= _MAX_GENS

    def _can_gen(self) -> bool:
        """B1 spawn gate: only start a generation if there's time to fit most of a full call_cap
        before active_deadline (else it would only produce a salvage-bound stub)."""
        if time.monotonic() >= self.active_deadline:
            return False
        # measure against active_deadline (E.deadline == active_deadline during ACTIVE)
        return (self.active_deadline - time.monotonic() - 20.0) * self.E.est_tps \
            >= self.E.call_cap * self.gen_gate_frac

    def _verified(self) -> list[Candidate]:
        return [c for c in self.candidates if c.scores()]

    # ---- workers ----
    async def _prove(self) -> None:
        if not self.active:
            return
        i = self._n_prove; self._n_prove += 1
        async with self.sem:
            if not self.active:
                return
            rec = await self.E.generate(self.prover_msgs, label=f"prove/P{i}")
        self.calls.append(rec); self._note(rec)
        pkg = parse_proof_package(rec, f"P{i}")
        if pkg.valid:
            c = Candidate(pkg.candidate_id, pkg.proof, pkg.self_eval, pkg.self_score, "prove", 0,
                          salvaged=bool(rec.get("salvaged")))
            self.candidates.append(c)
            for j in range(self.verify_k):
                self._spawn(self._verify(c, j))

    async def _verify(self, cand: Candidate, j: int) -> None:
        if not self.active:
            return
        msgs = to_messages(render_verifier_prompt(self.problem, cand.proof, cand.self_eval))
        async with self.sem:
            if not self.active:
                return
            rec = await self.E.generate(msgs, label=f"verify/{cand.cid}/{j}")
        self.calls.append(rec); self._note(rec)
        cand.verifs.append(parse_verification(rec, cand.cid, j))
        self._kick.set()                                # new verified material -> wake the driver

    async def _refine(self, inputs: list[Candidate]) -> None:
        if not self.active:
            return
        n = self._n_refine; self._n_refine += 1
        ranked = sorted(inputs, key=lambda c: c.rank_key(), reverse=True)
        verifs = [v for c in ranked for v in c.verifs]
        bundle = build_refine_bundle([c.as_proofpkg() for c in ranked], verifs)
        msgs = to_messages(render_refiner_prompt(self.problem, bundle))
        async with self.sem:
            if not self.active:
                return
            rec = await self.E.generate(msgs, label=f"refine/R{n}")
        self.calls.append(rec); self._note(rec)
        pkg = parse_refined_package(rec, f"R{n}")
        if pkg.valid:
            gen = max((c.gen for c in inputs), default=0) + 1
            c = Candidate(f"R{n}", pkg.proof, pkg.self_eval, pkg.self_score, "refine", gen,
                          salvaged=bool(rec.get("salvaged")))
            self.candidates.append(c)
            for j in range(self.verify_k):
                self._spawn(self._verify(c, j))

    def _pick_refine_inputs(self) -> list[Candidate]:
        # Refine the best-available verified candidates by RANK (rank_key already prefers higher
        # score, verifier agreement, and non-salvaged). NO absolute score floor: on a hard problem
        # the best proofs may all score low, and merging those partials is exactly refine's job —
        # an 0.5 floor would block refine entirely there. refine_min_score (default 0) only drops
        # candidates the verifiers UNANIMOUSLY rejected when better material exists.
        verified = sorted(self._verified(), key=lambda c: c.rank_key(), reverse=True)
        above = [c for c in verified if c.mean() > self.refine_min_score]
        pool = above if len(above) >= 2 else verified
        if len(pool) <= self.refine_inputs or self.rng.random() > self.diversity_p:
            return pool[: self.refine_inputs]
        # diversity: random subset from the top tier
        top = pool[: min(len(pool), self.refine_inputs * 2)]
        k = self.rng.randint(2, self.refine_inputs)
        return self.rng.sample(top, k)

    async def _refine_driver(self) -> None:
        """Keep ~target_live driver-owned generations in flight. Gates on `_gen_inflight` (B2: NOT
        total task count, so a backlog of queued verifiers can't starve the refiner) and on
        `_can_gen` (B1: don't start a generation there's no time to finish). Prefers refining good
        material; when nothing qualifies it spawns a fresh prover for diversity (B3). Wakes on any
        slot-free / new-verified-material event (`self._kick`)."""
        while self.active and time.monotonic() < self.active_deadline:
            while (self.active and self._gen_inflight < self.target_live and self._can_gen()
                   and not self._breaker_open()):
                inputs = self._pick_refine_inputs()
                if len(inputs) >= 2:
                    self._spawn_gen(self._refine(inputs))
                else:
                    self._spawn_gen(self._prove())     # no good refine material yet -> diversify
            try:
                await asyncio.wait_for(self._kick.wait(),
                                       timeout=min(2.0, max(0.1, self.active_deadline - time.monotonic())))
            except asyncio.TimeoutError:
                pass
            self._kick.clear()

    # ---- selection ----
    async def _select_phase(self) -> dict:
        self.E.deadline = self.deadline   # selectors may use the full remaining budget
        verified = sorted(self._verified(), key=lambda c: c.rank_key(), reverse=True)
        if not verified:
            # nothing verified — best raw candidate, else preamble
            raw = sorted(self.candidates, key=lambda c: len(c.proof or ""), reverse=True)
            proof = deterministic_clean(raw[0].proof) if raw else ""
            return {"final_proof": proof or fallback_preamble(),
                    "final_source": "fallback_no_verified", "selected_id": None}
        top = verified[: self.select_bundle_n]
        refined_pkgs = [RefinedPackage(refiner_id=c.cid, proof=c.proof, self_eval=c.self_eval,
                                       self_score=c.self_score, valid=True, call={}) for c in top]
        bundle, id_map = build_select_bundle(refined_pkgs)
        sel_msgs = to_messages(render_selector_prompt(self.problem, bundle))
        # A1: bound the selector vote so it can never run past the hard per-problem deadline.
        # On timeout we still return a real proof (highest-scored candidate).
        sel_budget = max(_MIN_SELECT_S, self.deadline - time.monotonic() - _SELECT_MARGIN_S)
        try:
            votes_calls = await asyncio.wait_for(
                asyncio.gather(
                    *(self.E.generate(sel_msgs, label=f"select/S{i}") for i in range(self.num_selectors))),
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
        """Stop active phase, cancel in-flight generations so the selector gets the GPU. Bounded:
        cancelled tasks resolve at their next await, but never block the selector on a stuck task."""
        self.active = False
        for t in list(self.tasks):
            t.cancel()
        try:
            await asyncio.wait_for(asyncio.gather(*self.tasks, return_exceptions=True), timeout=10.0)
        except asyncio.TimeoutError:
            pass   # abandon any task that didn't unwind in time; selector proceeds regardless

    def _dump(self, result: dict) -> None:
        """Persist the FULL trace so any post-hoc question (e.g. what did each refine score?) is
        answerable from disk — no re-run, no guessing. Keeps every candidate's verifier scores +
        proof and every call's answer content; reasoning CoT is summarised by length to bound size."""
        if not self.dump_path:
            return
        cands = [{"cid": c.cid, "source": c.source, "gen": c.gen, "salvaged": c.salvaged,
                  "self_score": c.self_score, "scores": c.scores(), "mean": c.mean(),
                  "minv": c.minv(), "won": c.cid == result.get("selected_id"),
                  "proof_len": len(c.proof or ""), "proof": c.proof,
                  "verifs": [{"score": v.score, "text": v.text} for v in c.verifs]}
                 for c in self.candidates]
        calls = [{"label": r.get("label"), "seed": r.get("seed"), "temperature": r.get("temperature"),
                  "max_tokens": r.get("max_tokens"), "finish_reason": r.get("finish_reason"),
                  "latency_s": r.get("latency_s"), "prompt_tokens": r.get("prompt_tokens"),
                  "completion_tokens": r.get("completion_tokens"),
                  "reasoning_tokens": r.get("reasoning_tokens"), "salvaged": r.get("salvaged"),
                  "error": r.get("error"), "content": r.get("content"),
                  "reasoning_len": len(r.get("reasoning_content") or "")}
                 for r in self.calls]
        try:
            with open(self.dump_path, "w") as f:
                json.dump({"result": result, "candidates": cands, "calls": calls},
                          f, ensure_ascii=False, default=str)
        except Exception:  # noqa: BLE001 - logging must never sink a submission
            pass

    # ---- entry ----
    async def solve(self) -> dict:
        t0 = time.monotonic()
        self.E.deadline = self.active_deadline   # active-phase calls cap by the active window
        for _ in range(self.init_provers):
            self._spawn_gen(self._prove())       # seed provers count toward _gen_inflight
        driver = asyncio.create_task(self._refine_driver())
        # run the active phase until the reserve window
        await asyncio.sleep(max(0.0, self.active_deadline - time.monotonic()))
        driver.cancel()
        await self._drain()
        result = await self._select_phase()
        verified = self._verified()
        result.update(wall_s=time.monotonic() - t0,
                      counts={"n_candidates": len(self.candidates), "n_verified": len(verified),
                              "n_prove": self._n_prove, "n_refine": self._n_refine,
                              "max_gen": max((c.gen for c in self.candidates), default=0)},
                      totals={"n_calls": len(self.calls),
                              "n_salvaged": sum(1 for c in self.calls if c.get("salvaged")),
                              "completion_tokens": sum(c.get("completion_tokens") or 0 for c in self.calls)})
        self._dump(result)
        return result


async def solve_pooled(problem: str, engine, *, deadline: float, **kw) -> dict:
    return await PoolSolver(engine, problem, deadline=deadline, **kw).solve()
