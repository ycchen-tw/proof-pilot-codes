# Copyright 2026 proof-pilot. Apache-2.0.
"""cold-start seed —— 把 DeepSeek **r3_hard2000 nested data**（proofs→verifies、refined）全灌進 pool。

寫成 `<pool_dir>/seed.jsonl`（不可變；PoolStore.load() 啟動時 replay）。讓四個 role 在 step 0 就採得到
context（否則早期只有 prove 可採）。seed 是 DeepSeek-source（off-policy context）；隨 student 生成 +
ring-free 的 prefer-student 選取，pool 自然漂成 student-dominated（depth/fill 只數 student → seed 不滿足
student depth）。

來源（cfg.agentic.seed_format）：
- "hf_per_problem"：HF dataset 的 per_problem config（每列一題，nested `proofs_json`/`refined_json`，
  各 artifact 的 `content` 是 raw XML → 用 math_3r parser 解出 solution/score）。**已 cache 本地、免下載。**
- "records_jsonl"：math_3r run.py 的 records.jsonl（每列一題，`stages.{prove,verify,refine}`）。

gate（同 writeback）：**只有 parse-pass 的 artifact 進 seed**（截斷/格式爛的 DeepSeek 生成不當 context）。
select 不進 pool（無下游消費）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys

log = logging.getLogger("opd_v2.agentic.seed")

_M3R = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..", "distill_gen", "math_3r"))
if _M3R not in sys.path:
    sys.path.insert(0, _M3R)


def _pid_of(problem: str) -> str:
    return hashlib.blake2b(problem.encode(), digest_size=8).hexdigest()


class _IdGen:
    def __init__(self):
        self.c = {"p": 0, "v": 0, "r": 0}

    def new(self, kind: str) -> str:
        self.c[kind] += 1
        return f"{kind}{self.c[kind]}"


def _proof_artifact(content: str):
    """raw proof XML → (solution, self_eval, self_score) 或 None（parse-gate）。"""
    from parser import parse_proof_package
    pkg = parse_proof_package({"content": content or "", "finish_reason": "stop", "error": None}, "P0")
    if not pkg.valid:
        return None
    return pkg.proof, pkg.self_eval, pkg.self_score


def _refined_artifact(content: str):
    from parser import parse_refined_package
    pkg = parse_refined_package({"content": content or "", "finish_reason": "stop", "error": None}, "R0")
    if not pkg.valid:
        return None
    return pkg.proof, pkg.self_eval, pkg.self_score


def _emit_problem(rows_out: list, ids: _IdGen, problem_id: str, text: str,
                  proofs: list, refined: list, *, wv: int = -1, source: str = "deepseek_seed") -> dict:
    """把一題的 (proofs[{content, verifications:[{score,content}]}], refined[{content}]) 攤成 records。

    回該題的計數統計。"""
    rows_out.append({"kind": "problem", "problem_id": problem_id, "text": text})
    n_p = n_v = n_r = 0
    for p in proofs:
        art = _proof_artifact(p.get("content"))
        if art is None:
            continue
        pid = ids.new("p")
        rows_out.append({"kind": "proof", "id": pid, "problem_id": problem_id, "content": art[0],
                         "self_eval": art[1], "self_score": art[2], "wv": wv, "source": source})
        n_p += 1
        for v in p.get("verifications") or []:
            score = v.get("score")
            if score is None:
                continue
            rows_out.append({"kind": "verify", "id": ids.new("v"), "problem_id": problem_id,
                             "proof_id": pid, "score": score, "text": v.get("content") or "",
                             "wv": wv, "source": source})
            n_v += 1
    for r in refined or []:
        art = _refined_artifact(r.get("content"))
        if art is None:
            continue
        rows_out.append({"kind": "refined", "id": ids.new("r"), "problem_id": problem_id,
                         "parent_proof_ids": [], "content": art[0], "self_eval": art[1],
                         "self_score": art[2], "wv": wv, "source": source})
        n_r += 1
    return {"proofs": n_p, "verifies": n_v, "refined": n_r}


def _iter_hf_per_problem(repo: str, config: str):
    from datasets import load_dataset
    ds = load_dataset(repo, config, split="train")
    for row in ds:
        problem = row.get("problem")
        if not problem:
            continue
        pid = row.get("problem_id") or _pid_of(problem)
        proofs = json.loads(row["proofs_json"]) if row.get("proofs_json") else []
        refined = json.loads(row["refined_json"]) if row.get("refined_json") else []
        yield pid, problem, proofs, refined


def _iter_records_jsonl(path: str):
    """math_3r records.jsonl：每列 `stages.{prove,verify,refine}`，verify 用 candidate_id 連回 proof。"""
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            problem = rec.get("problem")
            if not problem:
                continue
            st = rec.get("stages") or {}
            by_cand: dict = {}
            for v in st.get("verify", []):
                by_cand.setdefault(v.get("candidate_id"), []).append(
                    {"score": v.get("score"), "content": v.get("content") or ""})
            proofs = [{"content": p.get("content") or "",
                       "verifications": by_cand.get(p.get("candidate_id"), [])}
                      for p in st.get("prove", [])]
            refined = [{"content": r.get("content") or ""} for r in st.get("refine", [])]
            yield (rec.get("problem_id") or _pid_of(problem)), problem, proofs, refined


def build_seed(cfg, *, force: bool = False) -> str:
    """產 <pool_dir>/seed.jsonl（已存在且非空且非 force → 跳過）。回 path。"""
    pool_dir = cfg.pool_dir
    os.makedirs(pool_dir, exist_ok=True)
    out = os.path.join(pool_dir, "seed.jsonl")
    if os.path.exists(out) and os.path.getsize(out) > 0 and not force:
        log.info("seed.jsonl already exists (%s) — skip (use force to rebuild)", out)
        return out

    ag = cfg.agentic
    if ag.seed_format == "hf_per_problem":
        src = _iter_hf_per_problem(ag.seed_source, ag.seed_hf_config)
    elif ag.seed_format == "records_jsonl":
        src = _iter_records_jsonl(ag.seed_source)
    else:
        raise ValueError(f"unknown seed_format {ag.seed_format!r}")

    ids = _IdGen()
    rows: list = []
    n_prob = 0
    tot = {"proofs": 0, "verifies": 0, "refined": 0}
    for pid, problem, proofs, refined in src:
        c = _emit_problem(rows, ids, pid, problem, proofs, refined)
        n_prob += 1
        for k in tot:
            tot[k] += c[k]

    tmp = out + ".tmp"
    with open(tmp, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        f.flush()
    os.replace(tmp, out)
    log.info("seed built: %d problems, proofs=%d verifies=%d refined=%d -> %s",
             n_prob, tot["proofs"], tot["verifies"], tot["refined"], out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="build agentic OPD pool seed.jsonl from DeepSeek nested data")
    ap.add_argument("--run-dir", default=os.environ.get("OPD_RUN_DIR", ""))
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    if not a.run_dir:
        raise SystemExit("--run-dir (or OPD_RUN_DIR) required")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s: %(message)s")
    from opd_v2.config import OPDConfig
    # config.json 存在就用（與 run 一致的 seed 設定）；不存在則用預設（給 login-node **預建** seed.jsonl
    # 用——避開正式 run 在 headless 連私有 HF repo 的 auth/block；預設 seed_source=canonical HF repo）。
    cfg_path = os.path.join(a.run_dir, "config.json")
    cfg = OPDConfig.load(a.run_dir) if os.path.exists(cfg_path) else OPDConfig(run_dir=a.run_dir).resolve()
    build_seed(cfg, force=a.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
