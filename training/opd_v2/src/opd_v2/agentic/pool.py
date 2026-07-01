# Copyright 2026 proof-pilot. Apache-2.0.
"""PoolStore —— agentic OPD 的 per-problem artifact pool（純資料結構 + 持久化）。

graph：`problem → proofs → verifies`、`problem → refined`。select **不存 node**（無下游消費它的
輸出，只是 training 樣本）→ 只計數。每個 node 帶 provenance（id/wv/source/step），方便事後追蹤
vintage 與 on-policy 佔比。

設計（PLAN agentic 段）：
- **index 是記憶體真相**（`dict[problem_id → ProblemNode]`）；sampler 讀、admit 寫，**都在 orchestrator
  單一 event loop** → 無鎖（同 buffer.py 的理由）。本模組**不碰 tokenizer / parsing**（那在 writeback.py），
  admit_* 收的是「已 parse 的 artifact」。
- **持久化 = append-only JSONL**：`seed.jsonl`（cold-start 由 seed.py 寫、不可變）+ `artifacts.jsonl`
  （student admit append）。`load()` 啟動時 replay 兩者 → resume-safe（呼應 collect.py / rollout_store 慣例）。
- **on-policy 轉移**：depth/fill 計數**只數 student-source**（seed 給 context、不滿足 student depth）→ student
  持續生成 → pool 自然從 seed-dominated 漂成 student-dominated；sampler 組 context 時優先 student-source。

id：`p{n}/v{n}/r{n}` 全域單調（per kind）；replay 時從既有最大值回復 counter（不衝突、可 resume）。
"""
from __future__ import annotations

import json
import logging
import os
import random
import threading
from dataclasses import dataclass, field

log = logging.getLogger("opd_v2.agentic.pool")

ROLES = ("prove", "verify", "refine", "select")


@dataclass
class VerifyNode:
    id: str
    problem_id: str
    proof_id: str
    score: float | None        # verifier <score> ∈ {0, .5, 1}（用於 rank / refine bundle review）
    text: str                  # verifier <evaluation>/<suggestions>（refine bundle 用）
    wv: int
    source: str                # "deepseek_seed" | "student"


@dataclass
class ProofNode:
    id: str
    problem_id: str
    content: str               # parsed <solution>（answer-only，無 think）
    self_eval: str
    self_score: float | None
    wv: int
    source: str
    verifies: list = field(default_factory=list)   # list[VerifyNode]

    def n_verifies(self, student_only: bool = False) -> int:
        if student_only:
            return sum(1 for v in self.verifies if v.source == "student")
        return len(self.verifies)


@dataclass
class RefinedNode:
    id: str
    problem_id: str
    parent_proof_ids: list
    content: str
    self_eval: str
    self_score: float | None
    wv: int
    source: str


@dataclass
class ProblemNode:
    problem_id: str
    text: str
    meta: dict = field(default_factory=dict)
    proofs: list = field(default_factory=list)     # list[ProofNode]
    refined: list = field(default_factory=list)    # list[RefinedNode]

    def has_verified_proof(self, student_only: bool = False) -> bool:
        return any(p.n_verifies(student_only) > 0 for p in self.proofs)


class PoolStore:
    """per-problem artifact pool。admit_* = 記憶體 index 插入（+ append-only 持久化）。"""

    def __init__(self, pool_dir: str, *, seed: int = 0, max_artifact_chars: int = 200000):
        self.dir = pool_dir
        os.makedirs(self.dir, exist_ok=True)
        self.max_artifact_chars = max_artifact_chars
        self.problems: dict[str, ProblemNode] = {}
        self._proof_by_id: dict[str, ProofNode] = {}
        self._ctr = {"p": 0, "v": 0, "r": 0}
        # 增量 student 計數（O(1) student_counts；select 無 node 也在此計）→ fill_fraction 不必每 atom 全掃
        self._sc = {"prove": 0, "verify": 0, "refine": 0, "select": 0}
        # 持久化：student admit 累積到 _wal，flusher / persist() 寫 artifacts.jsonl（append-only）
        self._wal: list[dict] = []
        self._persisted_n = 0
        self._persist_lock = threading.Lock()   # persist 跨 thread（flusher executor vs close on loop）冪等
        self._flusher = None
        self._loop = None

    # ---- paths ----
    @property
    def seed_path(self) -> str:
        return os.path.join(self.dir, "seed.jsonl")

    @property
    def artifacts_path(self) -> str:
        return os.path.join(self.dir, "artifacts.jsonl")

    # ---- id ----
    def _new_id(self, kind: str) -> str:
        self._ctr[kind] += 1
        return f"{kind}{self._ctr[kind]}"

    def _bump_ctr_from_id(self, _id: str) -> None:
        kind, n = _id[0], _id[1:]
        if kind in self._ctr and n.isdigit():
            self._ctr[kind] = max(self._ctr[kind], int(n))

    # ---- problems ----
    def add_problem(self, problem_id: str, text: str, meta: dict | None = None) -> ProblemNode:
        p = self.problems.get(problem_id)
        if p is None:
            p = ProblemNode(problem_id=problem_id, text=text, meta=dict(meta or {}))
            self.problems[problem_id] = p
        elif text and not p.text:
            p.text = text
        return p

    # ---- admit（live，student；建 node + 記 wal）----
    def admit_proof(self, problem_id: str, content: str, self_eval: str, self_score: float | None,
                    *, wv: int, source: str = "student") -> ProofNode | None:
        prob = self.problems.get(problem_id)
        if prob is None or len(content or "") > self.max_artifact_chars:
            return None                      # 病態超長 proof 不進 pool（否則 render 撐爆 → role starve）
        node = ProofNode(id=self._new_id("p"), problem_id=problem_id, content=content,
                         self_eval=self_eval, self_score=self_score, wv=wv, source=source)
        prob.proofs.append(node)
        self._proof_by_id[node.id] = node
        if source == "student":
            self._sc["prove"] += 1
        self._log({"kind": "proof", "id": node.id, "problem_id": problem_id, "content": content,
                   "self_eval": self_eval, "self_score": self_score, "wv": wv, "source": source})
        return node

    def admit_verify(self, problem_id: str, proof_id: str, score: float | None, text: str,
                     *, wv: int, source: str = "student") -> VerifyNode | None:
        proof = self._proof_by_id.get(proof_id)
        if proof is None or proof.problem_id != problem_id:
            return None
        node = VerifyNode(id=self._new_id("v"), problem_id=problem_id, proof_id=proof_id,
                          score=score, text=text, wv=wv, source=source)
        proof.verifies.append(node)
        if source == "student":
            self._sc["verify"] += 1
        self._log({"kind": "verify", "id": node.id, "problem_id": problem_id, "proof_id": proof_id,
                   "score": score, "text": text, "wv": wv, "source": source})
        return node

    def admit_refined(self, problem_id: str, parent_proof_ids: list, content: str, self_eval: str,
                      self_score: float | None, *, wv: int, source: str = "student") -> RefinedNode | None:
        prob = self.problems.get(problem_id)
        if prob is None or len(content or "") > self.max_artifact_chars:
            return None
        node = RefinedNode(id=self._new_id("r"), problem_id=problem_id,
                           parent_proof_ids=list(parent_proof_ids or []), content=content,
                           self_eval=self_eval, self_score=self_score, wv=wv, source=source)
        prob.refined.append(node)
        if source == "student":
            self._sc["refine"] += 1
        self._log({"kind": "refined", "id": node.id, "problem_id": problem_id,
                   "parent_proof_ids": node.parent_proof_ids, "content": content,
                   "self_eval": self_eval, "self_score": self_score, "wv": wv, "source": source})
        return node

    def admit_select(self, problem_id: str, *, wv: int, source: str = "student") -> None:
        """select 無 node（無下游消費）→ 只計數 + 記一筆供事後追蹤。"""
        if source == "student":
            self._sc["select"] += 1
        self._log({"kind": "select", "problem_id": problem_id, "wv": wv, "source": source})

    # ---- persistence ----
    def _log(self, rec: dict) -> None:
        """student admit 記進 wal（之後 flusher / persist() append 到 artifacts.jsonl）。"""
        self._wal.append(rec)

    def persist(self) -> int:
        """把未落盤的 wal 記錄 append 到 artifacts.jsonl（同步、append-only）。回新寫筆數。

        ★ 並發安全：persist 在 executor thread 跑、`_log`(append) 在 event loop thread 跑。先**快照
        `end = len(_wal)`**，只寫 `[persisted_n:end]`、只把 `_persisted_n` 推進到 end——這之後 loop 再
        append 的會落在下一次 persist（list.append 不會 invalidate 既有 slice；GIL 保護單一 append）。
        若改成 `_persisted_n = len(_wal)`（在寫完後重讀 len），中間新 append 的會被跳過 → 資料遺失。
        """
        with self._persist_lock:        # flusher(executor) 與 close(loop) 不會並發寫重複行
            end = len(self._wal)
            new = self._wal[self._persisted_n:end]
            if not new:
                return 0
            with open(self.artifacts_path, "a") as f:
                for rec in new:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                f.flush()
            self._persisted_n = end
            return len(new)

    def _apply_record(self, rec: dict) -> None:
        """replay 一筆持久化記錄到 index（load / seed 共用；id 來自 rec，不新生）。

        缺必要欄位（id/problem_id）的合法-JSON 壞行 → 跳過（不崩 load；load 端另有 try/except 兜底）。
        """
        kind = rec.get("kind")
        if kind == "problem":
            if rec.get("problem_id"):
                self.add_problem(rec["problem_id"], rec.get("text") or "", rec.get("meta"))
            return
        if kind in ("proof", "verify", "refined") and (not rec.get("id") or not rec.get("problem_id")):
            return
        student = rec.get("source") == "student"
        if kind == "proof":
            if len(rec.get("content") or "") > self.max_artifact_chars:
                return
            prob = self.problems.get(rec["problem_id"]) or self.add_problem(rec["problem_id"], "")
            node = ProofNode(id=rec["id"], problem_id=rec["problem_id"], content=rec.get("content") or "",
                             self_eval=rec.get("self_eval") or "", self_score=rec.get("self_score"),
                             wv=int(rec.get("wv", -1)), source=rec.get("source") or "deepseek_seed")
            prob.proofs.append(node)
            self._proof_by_id[node.id] = node
            self._bump_ctr_from_id(node.id)
            if student:
                self._sc["prove"] += 1
        elif kind == "verify":
            proof = self._proof_by_id.get(rec.get("proof_id"))
            if proof is not None:
                node = VerifyNode(id=rec["id"], problem_id=rec["problem_id"], proof_id=rec["proof_id"],
                                  score=rec.get("score"), text=rec.get("text") or "",
                                  wv=int(rec.get("wv", -1)), source=rec.get("source") or "deepseek_seed")
                proof.verifies.append(node)
                self._bump_ctr_from_id(node.id)
                if student:
                    self._sc["verify"] += 1
        elif kind == "refined":
            if len(rec.get("content") or "") > self.max_artifact_chars:
                return
            prob = self.problems.get(rec["problem_id"]) or self.add_problem(rec["problem_id"], "")
            node = RefinedNode(id=rec["id"], problem_id=rec["problem_id"],
                               parent_proof_ids=rec.get("parent_proof_ids") or [],
                               content=rec.get("content") or "", self_eval=rec.get("self_eval") or "",
                               self_score=rec.get("self_score"), wv=int(rec.get("wv", -1)),
                               source=rec.get("source") or "deepseek_seed")
            prob.refined.append(node)
            self._bump_ctr_from_id(node.id)
            if student:
                self._sc["refine"] += 1
        elif kind == "select":
            if student:
                self._sc["select"] += 1

    def load(self) -> dict:
        """啟動 replay：seed.jsonl（cold-start，不可變）+ artifacts.jsonl（student，可續）。回統計。"""
        for path in (self.seed_path, self.artifacts_path):
            if not os.path.exists(path):
                continue
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        self._apply_record(json.loads(line))
                    except Exception:   # noqa: BLE001 — 容忍半行/壞欄位，跳過該行不崩 load（resume 韌性）
                        continue
        # artifacts.jsonl 已全部在盤上 → 標記為已持久化（wal 從這之後才累積新 student admit）
        self._wal.clear()
        self._persisted_n = 0
        st = self.stats()
        log.info("pool loaded: %d problems, proofs=%d verifies=%d refined=%d (student p/v/r/s=%d/%d/%d/%d)",
                 st["n_problems"], st["n_proofs"], st["n_verifies"], st["n_refined"],
                 st["student"]["prove"], st["student"]["verify"], st["student"]["refine"],
                 st["student"]["select"])
        return st

    # ---- 背景 flusher（live；非阻塞定期 persist）----
    def start(self, flush_interval_s: float = 30.0) -> None:
        import asyncio
        self._loop = asyncio.get_running_loop()
        self._flusher = asyncio.create_task(self._run_flusher(flush_interval_s), name="pool_flusher")

    async def _run_flusher(self, interval: float) -> None:
        import asyncio
        try:
            while True:
                await asyncio.sleep(interval)
                n = await self._loop.run_in_executor(None, self.persist)
                if n:
                    log.debug("pool persisted %d records", n)
        except asyncio.CancelledError:
            pass

    async def close(self) -> None:
        import asyncio
        if self._flusher is not None:
            self._flusher.cancel()
            try:
                await self._flusher
            except (asyncio.CancelledError, Exception):
                pass
            self._flusher = None
        self.persist()

    # ---- counts ----
    def student_counts(self) -> dict:
        """O(1)：增量維護（admit/_apply_record 時更新）→ next_prompt 不必每次全掃 pool（P1）。"""
        return dict(self._sc)

    def stats(self) -> dict:
        n_proofs = n_verifies = n_refined = 0
        for prob in self.problems.values():
            n_proofs += len(prob.proofs)
            n_refined += len(prob.refined)
            for p in prob.proofs:
                n_verifies += len(p.verifies)
        return {"n_problems": len(self.problems), "n_proofs": n_proofs,
                "n_verifies": n_verifies, "n_refined": n_refined,
                "student": self.student_counts(), "wal_pending": len(self._wal) - self._persisted_n}

    # ---- availability / item-selection（sampler 用；簡單掃描，long-CoT 下 atom 稀疏故便宜）----
    def available_roles(self, cfg) -> set:
        """目前哪些 role 採得到（有合法 context）。prove 永遠可（有題即可）。

        verify 的「可採」與 pick_verify_target 一致：存在 **student-verify 數 < cap** 的 proof
        （cap 只數 student verify → seed proof 的 seed verify 不佔 cap，cold-start 仍可對 seed proof
        做 on-policy verify；隨 student proof 累積，prefer-student 自然轉移）。
        """
        cap_v = cfg.agentic.max_verifies_per_proof
        roles = set()
        if self.problems:
            roles.add("prove")
        for prob in self.problems.values():
            if any(p.n_verifies(student_only=True) < cap_v for p in prob.proofs):
                roles.add("verify")
            if prob.has_verified_proof():
                roles.add("refine")
            if len(prob.refined) >= 2:
                roles.add("select")
            if {"verify", "refine", "select"} <= roles:
                break
        return roles

    def pick_prove_problem(self, cfg, rng: random.Random) -> ProblemNode | None:
        """攤平：在 student-proof 數最少的題中隨機挑（< max_proofs_per_problem 優先）。"""
        if not self.problems:
            return None
        cap = cfg.agentic.max_proofs_per_problem
        probs = list(self.problems.values())
        under = [p for p in probs if sum(1 for x in p.proofs if x.source == "student") < cap]
        pool = under or probs
        m = min(sum(1 for x in p.proofs if x.source == "student") for p in pool)
        cands = [p for p in pool if sum(1 for x in p.proofs if x.source == "student") == m]
        return rng.choice(cands)

    def pick_verify_target(self, cfg, rng: random.Random) -> tuple[ProblemNode, ProofNode] | None:
        """挑「student-verify 最少」的 proof（攤平，避免堆積未-verify proof）；prefer student-source proof。

        cap 只數 **student** verify（與 available_roles 一致）→ seed proof（0 student verify）cold-start
        即可採，做 on-policy verify；隨 student proof 出現（key 的 not_student=0 較小）優先 verify 自家 proof。
        """
        cap = cfg.agentic.max_verifies_per_proof
        prefer = cfg.agentic.prefer_student_context
        best = None  # (key, proof, problem)
        n_tie = 0    # reservoir：在 min-key tie 中均勻隨機取（避免決定性永遠挑同一 proof → verify 集中）
        for prob in self.problems.values():
            for p in prob.proofs:
                nv = p.n_verifies(student_only=True)
                if nv >= cap:
                    continue
                key = (nv, 0 if (p.source == "student" or not prefer) else 1)
                if best is None or key < best[0]:
                    best = (key, p, prob); n_tie = 1
                elif key == best[0]:
                    n_tie += 1
                    if rng.random() < 1.0 / n_tie:
                        best = (key, p, prob)
        if best is None:
            return None
        return best[2], best[1]

    def pick_refine_problem(self, cfg, rng: random.Random) -> ProblemNode | None:
        """挑「有 verified proof、且 student-refined 最少」的題（< max_refined_per_problem 優先）。"""
        cap = cfg.agentic.max_refined_per_problem
        cands = [p for p in self.problems.values() if p.has_verified_proof()]
        if not cands:
            return None
        under = [p for p in cands if sum(1 for r in p.refined if r.source == "student") < cap]
        pool = under or cands
        m = min(sum(1 for r in p.refined if r.source == "student") for p in pool)
        return rng.choice([p for p in pool if sum(1 for r in p.refined if r.source == "student") == m])

    def pick_select_problem(self, cfg, rng: random.Random) -> ProblemNode | None:
        """挑有 ≥2 refined 的題，在合格題中**隨機**（多樣性；避免 select 訓練集中在少數題）。"""
        cands = [p for p in self.problems.values() if len(p.refined) >= 2]
        return rng.choice(cands) if cands else None
