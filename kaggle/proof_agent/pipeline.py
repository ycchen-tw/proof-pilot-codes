"""DSMV2-Simple-3R orchestration (offline Kaggle port).

`solve_problem` (prove -> verify -> rank -> refine -> select-by-id -> clean/fallback) is byte-for-byte
the same control flow as distill_gen/math_3r/pipeline.py. The ONLY differences live in `Engine`:

  - local sglang client + explicit temperature/top_p (no DeepSeek reasoning_effort).
  - WALL-CLOCK WATCHDOG: a per-problem deadline caps each call's max_tokens by remaining time
    (so one runaway call can't eat the hour) and short-circuits to a synthetic timeout record once
    time is up — the stage then sees fewer valid items and solve_problem's fallback chain still emits
    a best-available proof.
  - FORCE-CLOSE-THINK SALVAGE: a prove/refine call that hit the token cap still inside <think>
    (finish=length, empty content) is recovered by appending </think> to its CoT and continuing,
    so a truncated-but-real proof is not wasted.

Engine.generate never raises: failures yield a record with `error` set and the pipeline degrades.
"""
from __future__ import annotations

import asyncio
import time
from collections import Counter

from bundle import build_refine_bundle, build_select_bundle
from clean import deterministic_clean, fallback_best_available, fallback_from_raw
from parser import (parse_proof_package, parse_refined_package,
                    parse_selected_id, parse_verification)
from prompts import (render_prover_prompt, render_refiner_prompt,
                     render_selector_prompt, render_verifier_prompt, to_messages)
from rank import rank_proofs
from salvage import force_close_think

# wall-clock guard constants
_MARGIN_S = 20.0          # never start a call with less than this much time left
_SLACK_S = 30.0           # request timeout = (remaining budget for this call) + slack
_MIN_CALL_TOKENS = 2048   # don't bother starting a call we can't get a useful answer from


class Engine:
    """One .generate() == one local sglang call. Holds the per-problem wall-clock deadline."""

    def __init__(self, client, sem: asyncio.Semaphore, *, max_tokens: int,
                 temperature: float = 0.7, top_p: float = 0.95,
                 deadline: float | None = None, est_tps: float = 35.0,
                 call_cap: int = 32000, salvage: bool = True, salvage_tokens: int = 16000,
                 role_temps: dict | None = None, seed_base: int = 1234):
        self.client = client
        self.sem = sem
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = top_p
        # per-call sampling seed = seed_base + monotonic counter (recorded in each rec for
        # reproducibility: re-issue any single call with its logged seed to reproduce it).
        self.seed_base = seed_base
        self._seed_ctr = 0
        # B4: discrete tasks (verify scoring, select picking an id) want LOW temperature for format
        # compliance + stable scores; prove/refine want the configured temp for diversity. Keyed by
        # label prefix ("verify/", "select/"); anything else falls back to self.temperature.
        self.role_temps = role_temps or {}
        self.deadline = deadline          # monotonic clock; None = no wall-clock limit
        self.est_tps = est_tps            # tok/s estimate (concurrent) to convert time <-> tokens
        self.call_cap = call_cap          # B1: fixed generous per-call ceiling, not time-shrunk
        self.salvage = salvage
        self.salvage_tokens = salvage_tokens

    def _remaining(self) -> float:
        return float("inf") if self.deadline is None else self.deadline - time.monotonic()

    def _temp_for(self, label: str) -> float:
        for prefix, t in self.role_temps.items():
            if label.startswith(prefix):
                return t
        return self.temperature

    def fits(self, tokens: float) -> bool:
        """True if `tokens` can plausibly be generated before the deadline at est_tps. The pool's
        spawn gate uses this so a generation is only started when there's time to finish it."""
        if self.deadline is None:
            return True
        return (self._remaining() - _MARGIN_S) * self.est_tps >= tokens

    def _blank(self, messages, label) -> dict:
        return {"label": label, "messages": messages, "reasoning_content": "", "content": "",
                "finish_reason": None, "truncated": False, "prompt_tokens": None,
                "completion_tokens": None, "reasoning_tokens": None, "latency_s": None,
                "error": None, "salvaged": False, "seed": None, "temperature": None,
                "max_tokens": None}

    async def generate(self, messages: list[dict], *, label: str) -> dict:
        async with self.sem:
            rec = self._blank(messages, label)
            remaining = self._remaining()
            if remaining <= _MARGIN_S:
                rec.update(finish_reason="timeout", error="deadline: no time left")
                return rec
            budget_s = remaining - _MARGIN_S
            # B1: ceiling is the fixed call_cap, NOT time-shrunk — so mid-phase calls aren't
            # truncated into salvage. `fit` is only a backstop for a call that slipped past the
            # pool's spawn gate near the deadline (keeps us from requesting more than can fit).
            fit = self.max_tokens if self.deadline is None else int(budget_s * self.est_tps)
            cap = max(_MIN_CALL_TOKENS, min(self.max_tokens, self.call_cap, max(fit, _MIN_CALL_TOKENS)))
            req_timeout = None if self.deadline is None else (budget_s + _SLACK_S)
            temp = self._temp_for(label)
            seed = self.seed_base + self._seed_ctr
            self._seed_ctr += 1
            rec.update(seed=seed, temperature=temp, max_tokens=cap)
            try:
                out = await self.client.chat(messages, max_tokens=cap, temperature=temp,
                                             top_p=self.top_p, timeout=req_timeout, seed=seed)
                m = out["message"]
                rec.update(reasoning_content=m.get("reasoning_content") or "",
                           content=m.get("content") or "",
                           finish_reason=out["finish_reason"],
                           truncated=out["finish_reason"] == "length",
                           prompt_tokens=out["prompt_tokens"],
                           completion_tokens=out["completion_tokens"],
                           reasoning_tokens=out["reasoning_tokens"], latency_s=out["latency_s"])
                await self._maybe_salvage(rec, messages, label)
            except Exception as e:  # noqa: BLE001 - record cause chain, never raise
                parts, cur, seen = [], e, set()
                while cur is not None and id(cur) not in seen:
                    seen.add(id(cur)); parts.append(repr(cur))
                    cur = cur.__cause__ or cur.__context__
                rec.update(finish_reason="error", error=" <- ".join(parts))
            return rec

    # the structural tag each role must emit; if a truncated call already has it, no salvage needed
    _ROLE_TAG = {"prove/": "<solution>", "refine/": "<solution>",
                 "verify/": "<score>", "select/": "<selected_id>"}

    async def _maybe_salvage(self, rec: dict, messages, label: str) -> None:
        """Any call that hit the cap still inside <think> (missing its structural output): append
        </think> to its CoT and continue, so the truncated-but-real answer is recovered. Applies to
        all roles — prove/refine (<solution>), verify (<score>), select (<selected_id>)."""
        if not self.salvage:
            return
        if rec["finish_reason"] != "length":
            return
        if not (rec["reasoning_content"] or "").strip():
            return  # nothing to salvage from
        tag = next((t for p, t in self._ROLE_TAG.items() if label.startswith(p)), None)
        if tag and tag in (rec["content"] or "").lower():
            return  # already has its parsable output despite truncation
        remaining = self._remaining()
        if remaining <= _MARGIN_S:
            return
        sv_cap = max(_MIN_CALL_TOKENS,
                     min(self.salvage_tokens, int((remaining - _MARGIN_S) * self.est_tps)))
        try:
            out = await force_close_think(self.client, messages, rec["reasoning_content"],
                                          max_new_tokens=sv_cap,
                                          temperature=self._temp_for(label), top_p=self.top_p,
                                          timeout=(remaining - _MARGIN_S + _SLACK_S),
                                          seed=rec.get("seed"))
        except Exception:  # noqa: BLE001 - salvage is best-effort
            return
        text = out.get("text") or ""
        if text.strip():
            # force_close_think steered the model past "<solution>\n" (which lives in the prompt,
            # not the output) — re-attach it so the parser sees the tag. Avoid a double tag if the
            # model happened to emit its own.
            rec["content"] = text if "<solution>" in text.lower() else "<solution>\n" + text
            fr = (out.get("meta_info") or {}).get("finish_reason")
            if isinstance(fr, dict):           # native /generate returns {"type": "length", ...}
                fr = fr.get("type")
            rec["finish_reason"] = fr or "stop"
            rec["truncated"] = rec["finish_reason"] == "length"
            rec["salvaged"] = True

    async def run_parallel(self, jobs: list[tuple[list[dict], str]]) -> list[dict]:
        return await asyncio.gather(*(self.generate(m, label=lbl) for m, lbl in jobs))


# ---- views / totals (verbatim from math_3r) ----
def _proof_view(p) -> dict:
    return {"candidate_id": p.candidate_id, "self_score": p.self_score, "valid": p.valid, **p.call}


def _verif_view(v) -> dict:
    return {"candidate_id": v.candidate_id, "verifier_idx": v.verifier_idx, "score": v.score, **v.call}


def _refined_view(r) -> dict:
    return {"refiner_id": r.refiner_id, "self_score": r.self_score, "valid": r.valid, **r.call}


def _totals(stages: dict) -> dict:
    calls = (list(stages["prove"]) + list(stages["verify"]) + list(stages["refine"])
             + list(stages["select"]))
    return {
        "n_calls": len(calls),
        "n_errors": sum(1 for c in calls if c.get("error")),
        "n_truncated": sum(1 for c in calls if c.get("truncated")),
        "n_salvaged": sum(1 for c in calls if c.get("salvaged")),
        "completion_tokens": sum(c.get("completion_tokens") or 0 for c in calls),
        "reasoning_tokens": sum(c.get("reasoning_tokens") or 0 for c in calls),
        "prompt_tokens": sum(c.get("prompt_tokens") or 0 for c in calls),
    }


async def solve_problem(problem: str, engine: Engine, *, num_provers: int = 6,
                        verify_k: int = 2, num_refiners: int = 3, num_selectors: int = 4) -> dict:
    stages = {"prove": [], "verify": [], "ranking": [], "refine": [], "select": []}

    # 1. Prove (identical prompt x num_provers; diversity from sampling)
    prover_msgs = to_messages(render_prover_prompt(problem))
    prove_calls = await engine.run_parallel([(prover_msgs, f"prove/P{i}") for i in range(num_provers)])
    proofs = [parse_proof_package(prove_calls[i], f"P{i}") for i in range(num_provers)]
    stages["prove"] = [_proof_view(p) for p in proofs]
    valid_proofs = [p for p in proofs if p.valid]

    if not valid_proofs:
        return {"stages": stages, "final_proof": fallback_from_raw(proofs),
                "final_source": "fallback_from_raw", "selected_id": None, "selected_ids": [],
                "counts": {"n_provers": num_provers, "n_valid_proofs": 0, "n_verifs": 0,
                           "n_refined_valid": 0}, "totals": _totals(stages)}

    # 2. Verify (each valid proof x verify_k identical verifiers)
    verify_jobs = [(to_messages(render_verifier_prompt(problem, p.proof, p.self_eval)),
                    f"verify/{p.candidate_id}/{j}")
                   for p in valid_proofs for j in range(verify_k)]
    verify_calls = await engine.run_parallel(verify_jobs)
    verifs, k = [], 0
    for p in valid_proofs:
        for j in range(verify_k):
            verifs.append(parse_verification(verify_calls[k], p.candidate_id, j))
            k += 1
    stages["verify"] = [_verif_view(v) for v in verifs]

    ranked = rank_proofs(valid_proofs, verifs)
    stages["ranking"] = [p.candidate_id for p in ranked]

    # 3. Refine (num_refiners identical refiners share one bundle; diversity from sampling)
    refine_bundle = build_refine_bundle(ranked, verifs)
    refiner_msgs = to_messages(render_refiner_prompt(problem, refine_bundle))
    refine_calls = await engine.run_parallel([(refiner_msgs, f"refine/R{i}") for i in range(num_refiners)])
    refined = [parse_refined_package(refine_calls[i], f"R{i}") for i in range(num_refiners)]
    stages["refine"] = [_refined_view(r) for r in refined]
    valid_refined = [r for r in refined if r.valid]

    # 4. Select-by-id over REFINED candidates only (num_selectors voters) / Clean.
    select_bundle, id_map = build_select_bundle(valid_refined)
    votes: list[str | None] = []
    winner, final, final_source = None, "", None
    if id_map:
        sel_msgs = to_messages(render_selector_prompt(problem, select_bundle))
        select_calls = await engine.run_parallel([(sel_msgs, f"select/S{i}") for i in range(num_selectors)])
        stages["select"] = select_calls
        votes = [parse_selected_id(c["content"]) for c in select_calls]
        valid_votes = [v for v in votes if v in id_map]
        if valid_votes:
            counts = Counter(valid_votes)
            order = list(id_map)
            winner = max(counts, key=lambda k: (counts[k], -order.index(k)))
            final = deterministic_clean(id_map[winner])
            final_source = f"select:{winner}({counts[winner]}/{num_selectors})"
    if not final:
        final = fallback_best_available(ranked, valid_refined)
        final_source = "fallback_no_refined" if not id_map else "fallback_no_valid_id"

    return {"stages": stages, "final_proof": final, "final_source": final_source,
            "selected_id": winner, "selected_ids": votes,
            "counts": {"n_provers": num_provers, "n_valid_proofs": len(valid_proofs),
                       "n_verifs": len(verifs), "n_refined_valid": len(valid_refined)},
            "totals": _totals(stages)}
