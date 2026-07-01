"""Pack distill data into TWO PRIVATE-HF tables and (optionally) upload.

Sources:
  - PLAIN proofs  : collect.py runs (outputs/<run>/records.jsonl) -- one API call per (problem,sample).
  - MATH_3R traces: math_3r/outputs/<run>/records.jsonl -- multi-agent prove/verify/refine/select,
                    full per-stage trace (one record per problem, nested `stages`).

Two output tables (different consumers):

  (a) per_turn.parquet  -- SFT / off-policy distillation.
      One row = ONE teacher turn (a prompt + the teacher's reasoning+answer). PLAIN rows and
      EVERY usable math_3r stage-call are flattened into the same shape. Layout matches the
      existing collect.py HF dataset: `messages_json` holds the PROMPT ONLY (system+user); the
      assistant turn lives in `reasoning_content` + `content` columns. The downstream renderer
      builds  prompt_messages + [{"role":"assistant","content":..,"reasoning_content":..}]  and
      feeds train_core.l3_render (render_manifest.py-style). Only clean turns are kept
      (not error, not truncated, non-empty reasoning+content).

  (b) per_problem.parquet -- analysis / RL (math_3r only).
      One row = one problem, with nested `proofs` (the prover candidates), each proof carrying
      its `verifications` (verifier score + text), plus `refined` and `selection`. Nested blocks
      are JSON strings (mirrors verify_gen/proof_pool's `proofs` column) for parquet robustness.
      This is the (problem -> proofs -> verifies) reward view for RL.

Validation (no tokenizer needed): sampled per_turn rows are round-tripped through
train_core.encoding_dsv4.encode_messages -- assert the full render starts with the prompt render
and the target (assistant tail) is non-empty. That is exactly the invariant l3_render relies on.

CONFIDENTIALITY: repo created PRIVATE; card carries no competition / project naming. Auth via the
cached huggingface-cli login / HF_TOKEN; never hard-coded.

Usage:
    # build + validate locally, do NOT upload (default while a run is still in flight)
    uv run python distill_gen/pack_hf.py \
        --plain-runs mix_v1 mix_v2 mix_v3 \
        --math3r-runs r3_500 r3_hard2000 \
        --out-dir /tmp/hf_dsflash_pack --no-upload

    # then, once hard2000 is done, drop --no-upload and add --repo to push
    uv run python distill_gen/pack_hf.py ... --repo ycchen/<new-private-repo>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from train_core.encoding_dsv4 import encode_messages  # noqa: E402

PLAIN_ROOT = REPO / "distill_gen" / "outputs"
MATH3R_ROOT = REPO / "distill_gen" / "math_3r" / "outputs"
THINKING_MODE = "thinking"  # all data generated with reasoning=high

# ---------------------------------------------------------------- per-turn (a)
TURN_SCHEMA = pa.schema([
    ("pipeline", pa.string()),          # plain | math_3r
    ("run_id", pa.string()),
    ("problem_id", pa.string()),
    ("problem", pa.string()),
    ("origin", pa.string()), ("source", pa.string()), ("category", pa.string()),
    ("competition", pa.string()), ("nm_uuid", pa.string()),
    ("difficulty_source", pa.string()), ("difficulty_value", pa.float64()),
    ("stage", pa.string()),             # plain | prove | verify | refine | select
    ("candidate_id", pa.string()),      # P#/R#/S# ; for verify the reviewed proof P#
    ("verifier_idx", pa.int64()),       # verify turns only
    ("score", pa.string()),             # prove/refine: self_score ; verify: verifier score
    ("thinking_mode", pa.string()),
    ("messages_json", pa.string()),     # PROMPT ONLY (system+user)
    ("reasoning_content", pa.string()), ("content", pa.string()),
    ("finish_reason", pa.string()),
    ("prompt_tokens", pa.int64()), ("completion_tokens", pa.int64()),
    ("reasoning_tokens", pa.int64()), ("latency_s", pa.float64()),
    ("model", pa.string()), ("max_tokens", pa.int64()),
    ("template", pa.string()), ("effort", pa.string()), ("seed", pa.int64()),
])

# ------------------------------------------------------------ per-problem (b)
# Keyed by problem_id and RESTRICTED to the hard2000 spine (the primary math_3r run's problems);
# any problem not in that spine is dropped. For each spine problem we merge every proof we hold
# from matching-problem_id records of the other sources: math_3r prover candidates carry their
# verifications; plain (pure-proof) attempts have no verifier. refined / selection come from the
# math_3r run(s); top-level selection is the primary (spine) run's.
PROBLEM_SCHEMA = pa.schema([
    ("problem_id", pa.string()),
    ("problem", pa.string()),
    ("origin", pa.string()), ("source", pa.string()), ("category", pa.string()),
    ("competition", pa.string()), ("nm_uuid", pa.string()),
    ("difficulty_source", pa.string()), ("difficulty_value", pa.float64()),
    ("source_runs_json", pa.string()),     # run_ids contributing to this problem
    ("primary_run", pa.string()),          # math_3r run whose selection is at top level (the spine)
    ("n_proofs", pa.int64()),              # total proof attempts (math_3r prove + plain)
    ("n_proofs_math3r", pa.int64()), ("n_proofs_plain", pa.int64()),
    ("n_proofs_with_verif", pa.int64()),   # proofs carrying >=1 verifier review
    # selection outcome from the primary math_3r run (null for plain-only problems):
    ("final_proof", pa.string()), ("final_source", pa.string()),
    ("selected_id", pa.string()), ("selected_ids_json", pa.string()),
    ("n_valid_proofs", pa.int64()), ("n_verifs", pa.int64()), ("n_refined_valid", pa.int64()),
    ("proofs_json", pa.string()),    # [{run_id, pipeline, role(prove|plain), candidate_id, valid,
                                     #   truncated, self_score, reasoning_content, content,
                                     #   verifications:[{verifier_idx, score, truncated,
                                     #                   reasoning_content, content}]}]
    ("refined_json", pa.string()),   # math_3r refined across runs: [{run_id, refiner_id, valid,
                                     #   truncated, self_score, reasoning_content, content}]
    ("select_json", pa.string()),    # math_3r select turns across runs: [{run_id, selector_id,
                                     #   selected_id, truncated, reasoning_content, content}]
])


def _usable(call: dict) -> bool:
    """A teacher turn worth training on: completed, not truncated, with real output."""
    return (not call.get("error") and not call.get("truncated")
            and bool((call.get("content") or "").strip())
            and bool((call.get("reasoning_content") or "").strip()))


def _score_str(x) -> str | None:
    return None if x is None else ("%g" % x if isinstance(x, (int, float)) else str(x))


# ---------------------------------------------------------------- loaders

def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(path)
    return [json.loads(ln) for ln in open(path) if ln.strip()]


def _pid_of(problem: str) -> str:
    """Same key run.py / select_hard.py use, so difficulty re-joins by problem_id."""
    import hashlib
    return hashlib.blake2b((problem or "").encode(), digest_size=8).hexdigest()


def load_diff_map(paths: list[str]) -> dict[str, tuple[str | None, float | None]]:
    """problem_id -> (difficulty_source, difficulty_value) from the hard-subset input parquet(s).

    run.py does NOT persist difficulty columns into its records, so re-join them here from the
    input parquet by problem_id (lossless; no rerun needed)."""
    m: dict[str, tuple[str | None, float | None]] = {}
    for p in paths:
        t = pq.read_table(p, columns=["problem", "difficulty_source", "difficulty_value"])
        for prob, src, val in zip(t.column("problem").to_pylist(),
                                  t.column("difficulty_source").to_pylist(),
                                  t.column("difficulty_value").to_pylist()):
            m[_pid_of(prob)] = (src, val)
    return m


_DIFF: dict[str, tuple[str | None, float | None]] = {}


def _diff(rec: dict) -> tuple[str | None, float | None]:
    """rec's own difficulty if present, else the re-joined value, else (None, None)."""
    if rec.get("difficulty_source") is not None:
        return rec["difficulty_source"], rec.get("difficulty_value")
    return _DIFF.get(rec["problem_id"], (None, None))


def plain_turns(run_id: str):
    """Yield per-turn rows from a collect.py run. Prompt = r['messages']; answer = columns."""
    for r in _read_jsonl(PLAIN_ROOT / run_id / "records.jsonl"):
        if not _usable(r):
            continue
        yield {
            "pipeline": "plain", "run_id": run_id, "problem_id": r["problem_id"],
            "problem": r["problem"], "origin": r["origin"], "source": r["source"],
            "category": r["category"], "competition": r["competition"], "nm_uuid": r["nm_uuid"],
            "difficulty_source": None, "difficulty_value": None,
            "stage": "plain", "candidate_id": None, "verifier_idx": None,
            "score": _score_str(r.get("self_score")), "thinking_mode": THINKING_MODE,
            "messages_json": json.dumps(r["messages"], ensure_ascii=False),
            "reasoning_content": r["reasoning_content"], "content": r["content"],
            "finish_reason": r["finish_reason"],
            "prompt_tokens": r["prompt_tokens"], "completion_tokens": r["completion_tokens"],
            "reasoning_tokens": r["reasoning_tokens"], "latency_s": r["latency_s"],
            "model": r["model"], "max_tokens": r["max_tokens"],
            "template": r["template"], "effort": r["effort"], "seed": r["seed"],
        }


def _turn_base(rec: dict, run_id: str) -> dict:
    dsrc, dval = _diff(rec)
    return {
        "pipeline": "math_3r", "run_id": run_id, "problem_id": rec["problem_id"],
        "problem": rec["problem"], "origin": rec["origin"], "source": rec["source"],
        "category": rec["category"], "competition": rec["competition"], "nm_uuid": rec["nm_uuid"],
        "difficulty_source": dsrc, "difficulty_value": dval,
        "thinking_mode": THINKING_MODE, "model": rec["model"], "max_tokens": rec["max_tokens"],
        "template": None, "effort": rec.get("effort"), "seed": None,
    }


def _call_cols(call: dict) -> dict:
    return {
        "messages_json": json.dumps(call["messages"], ensure_ascii=False),
        "reasoning_content": call.get("reasoning_content") or "",
        "content": call.get("content") or "",
        "finish_reason": call.get("finish_reason"),
        "prompt_tokens": call.get("prompt_tokens"), "completion_tokens": call.get("completion_tokens"),
        "reasoning_tokens": call.get("reasoning_tokens"), "latency_s": call.get("latency_s"),
    }


def math3r_turns(run_id: str):
    """Yield per-turn rows from a math_3r run -- every usable stage call across all problems."""
    for rec in _read_jsonl(MATH3R_ROOT / run_id / "records.jsonl"):
        base = _turn_base(rec, run_id)
        st = rec["stages"]
        for c in st.get("prove", []):
            if _usable(c):
                yield {**base, "stage": "prove", "candidate_id": c.get("candidate_id"),
                       "verifier_idx": None, "score": _score_str(c.get("self_score")), **_call_cols(c)}
        for c in st.get("verify", []):
            if _usable(c):
                yield {**base, "stage": "verify", "candidate_id": c.get("candidate_id"),
                       "verifier_idx": c.get("verifier_idx"), "score": _score_str(c.get("score")),
                       **_call_cols(c)}
        for c in st.get("refine", []):
            if _usable(c):
                yield {**base, "stage": "refine", "candidate_id": c.get("refiner_id"),
                       "verifier_idx": None, "score": _score_str(c.get("self_score")), **_call_cols(c)}
        for i, c in enumerate(st.get("select", [])):
            if _usable(c):
                yield {**base, "stage": "select", "candidate_id": f"S{i}",
                       "verifier_idx": None, "score": None, **_call_cols(c)}


def _math3r_proofs(run_id: str, rec: dict) -> tuple[list[dict], list[dict], list[dict]]:
    """(proofs, refined, select) blocks for one math_3r record, verifications nested per proof."""
    st = rec["stages"]
    by_cand: dict[str, list[dict]] = {}
    for v in st.get("verify", []):
        by_cand.setdefault(v.get("candidate_id"), []).append({
            "verifier_idx": v.get("verifier_idx"), "score": v.get("score"),
            "truncated": v.get("truncated"), "error": v.get("error"),
            "reasoning_content": v.get("reasoning_content") or "", "content": v.get("content") or "",
        })
    proofs = [{
        "run_id": run_id, "pipeline": "math_3r", "role": "prove",
        "candidate_id": p.get("candidate_id"), "valid": p.get("valid"),
        "truncated": p.get("truncated"), "error": p.get("error"), "self_score": p.get("self_score"),
        "reasoning_content": p.get("reasoning_content") or "", "content": p.get("content") or "",
        "verifications": by_cand.get(p.get("candidate_id"), []),
    } for p in st.get("prove", [])]
    refined = [{
        "run_id": run_id, "refiner_id": r.get("refiner_id"), "valid": r.get("valid"),
        "truncated": r.get("truncated"), "error": r.get("error"), "self_score": r.get("self_score"),
        "reasoning_content": r.get("reasoning_content") or "", "content": r.get("content") or "",
    } for r in st.get("refine", [])]
    votes = rec.get("selected_ids") or []
    select = [{
        "run_id": run_id, "selector_id": f"S{i}",
        "selected_id": votes[i] if i < len(votes) else None,
        "truncated": c.get("truncated"), "error": c.get("error"),
        "reasoning_content": c.get("reasoning_content") or "", "content": c.get("content") or "",
    } for i, c in enumerate(st.get("select", []))]
    return proofs, refined, select


def build_per_problem(math3r_runs: list[str], plain_runs: list[str]) -> list[dict]:
    """RESTRICTED to the hard2000 spine = the FIRST math3r run's problems. Merge matching-pid
    proofs from the other math3r runs and the plain runs; drop anything not in the spine."""
    if not math3r_runs:
        return []
    spine_run = math3r_runs[0]
    agg: dict[str, dict] = {}

    # 1. spine: the primary math_3r run (hard2000). Sets top-level selection + difficulty.
    for rec in _read_jsonl(MATH3R_ROOT / spine_run / "records.jsonl"):
        pid = rec["problem_id"]
        proofs, refined, select = _math3r_proofs(spine_run, rec)
        dsrc, dval = _diff(rec)
        cnt = rec.get("counts", {})
        agg[pid] = {
            "problem_id": pid, "problem": rec["problem"], "origin": rec["origin"],
            "source": rec["source"], "category": rec["category"], "competition": rec["competition"],
            "nm_uuid": rec["nm_uuid"], "difficulty_source": dsrc, "difficulty_value": dval,
            "primary_run": spine_run, "final_proof": rec.get("final_proof"),
            "final_source": rec.get("final_source"), "selected_id": rec.get("selected_id"),
            "selected_ids_json": json.dumps(rec.get("selected_ids") or [], ensure_ascii=False),
            "n_valid_proofs": cnt.get("n_valid_proofs"), "n_verifs": cnt.get("n_verifs"),
            "n_refined_valid": cnt.get("n_refined_valid"),
            "_runs": {spine_run}, "_proofs": proofs, "_refined": refined, "_select": select,
        }

    # 2. merge the other math_3r runs (e.g. r3_500) -- only for spine problems.
    for run_id in math3r_runs[1:]:
        for rec in _read_jsonl(MATH3R_ROOT / run_id / "records.jsonl"):
            a = agg.get(rec["problem_id"])
            if a is None:
                continue  # not in the hard2000 spine -> drop
            proofs, refined, select = _math3r_proofs(run_id, rec)
            a["_proofs"] += proofs; a["_refined"] += refined; a["_select"] += select
            a["_runs"].add(run_id)

    # 3. merge plain (pure-proof) runs -- only for spine problems, no verifier.
    for run_id in plain_runs:
        for r in _read_jsonl(PLAIN_ROOT / run_id / "records.jsonl"):
            a = agg.get(r["problem_id"])
            if a is None or not _usable(r):
                continue
            a["_proofs"].append({
                "run_id": run_id, "pipeline": "plain", "role": "plain", "candidate_id": None,
                "valid": None, "truncated": r.get("truncated"), "error": r.get("error"),
                "self_score": r.get("self_score"),
                "reasoning_content": r.get("reasoning_content") or "", "content": r.get("content") or "",
                "verifications": [],
            })
            a["_runs"].add(run_id)

    rows = []
    for a in agg.values():
        proofs = a.pop("_proofs"); refined = a.pop("_refined"); select = a.pop("_select")
        runs = a.pop("_runs")
        n_m3r = sum(1 for p in proofs if p["pipeline"] == "math_3r")
        rows.append({
            **a, "source_runs_json": json.dumps(sorted(runs), ensure_ascii=False),
            "n_proofs": len(proofs), "n_proofs_math3r": n_m3r, "n_proofs_plain": len(proofs) - n_m3r,
            "n_proofs_with_verif": sum(1 for p in proofs if p["verifications"]),
            "proofs_json": json.dumps(proofs, ensure_ascii=False),
            "refined_json": json.dumps(refined, ensure_ascii=False),
            "select_json": json.dumps(select, ensure_ascii=False),
        })
    return rows


def easy_problem_ids(prob_rows: list[dict]) -> set[str]:
    """Problems where EVERY scored math_3r proof was verified perfect (per-proof mean verifier
    score == 1.0) -> too easy for the teacher. Requires >=1 scored proof."""
    easy: set[str] = set()
    for r in prob_rows:
        proof_means = []
        for p in json.loads(r["proofs_json"]):
            vs = [v["score"] for v in (p.get("verifications") or []) if v.get("score") is not None]
            if vs:
                proof_means.append(sum(vs) / len(vs))
        if proof_means and all(m == 1.0 for m in proof_means):
            easy.add(r["problem_id"])
    return easy


# ---------------------------------------------------------------- validation

def validate_turns(rows: list[dict], n_sample: int = 60) -> None:
    """Round-trip a deterministic sample through encode_messages (no tokenizer):
    the full render must start with the prompt render and have a non-empty assistant tail."""
    if not rows:
        raise SystemExit("no per-turn rows to validate")
    # deterministic spread across the table
    step = max(1, len(rows) // n_sample)
    idxs = list(range(0, len(rows), step))[:n_sample]
    seen_stage = set()
    for i in idxs:
        r = rows[i]
        prompt = json.loads(r["messages_json"])
        assistant = {"role": "assistant", "content": r["content"],
                     "reasoning_content": r["reasoning_content"]}
        ptext = encode_messages(prompt, thinking_mode=THINKING_MODE, drop_thinking=False)
        ftext = encode_messages(prompt + [assistant], thinking_mode=THINKING_MODE, drop_thinking=False)
        if not ftext.startswith(ptext):
            raise RuntimeError(f"row {i} ({r['pipeline']}/{r['stage']}): full render not prefixed by prompt")
        if len(ftext) - len(ptext) <= 0:
            raise RuntimeError(f"row {i} ({r['pipeline']}/{r['stage']}): empty target tail")
        seen_stage.add(f"{r['pipeline']}/{r['stage']}")
    print(f"[validate] {len(idxs)} sampled turns round-trip OK via encode_messages "
          f"(stages covered: {sorted(seen_stage)})")


# ---------------------------------------------------------------- main

def write_card(out_dir: Path, n_turn: int, n_prob: int, by_stage: dict, by_run: dict) -> None:
    """Dataset card with the two-config mapping so load_dataset picks the right table.

    Confidentiality: NO competition / project naming (private-secrecy clause)."""
    yaml = (
        "---\n"
        "license: other\n"
        "configs:\n"
        "- config_name: per_turn\n"
        "  data_files:\n"
        "  - split: train\n"
        "    path: data/per_turn.parquet\n"
        "- config_name: per_problem\n"
        "  data_files:\n"
        "  - split: train\n"
        "    path: data/per_problem.parquet\n"
        "---\n"
    )
    stage_tbl = "\n".join(f"| `{k}` | {v} |" for k, v in sorted(by_stage.items()))
    run_tbl = "\n".join(f"| `{k}` | {v} |" for k, v in sorted(by_run.items()))
    body = f"""# Olympiad proof distillation data (private)

Teacher-generated olympiad math proof data (teacher **DeepSeek-V4-Flash**, reasoning=high). Two HF
configs — load with `load_dataset(repo, "per_turn")` or `load_dataset(repo, "per_problem")`.

## How the data was made / how to tell sources apart (`run_id`)

Every `per_turn` row and every nested proof/refined/select entry in `per_problem` carries a
**`run_id`**. Use it to separate sources:

| `run_id` | what it is |
|---|---|
| `mix_v1` / `mix_v2` / `mix_v3` | **plain** single-shot proofs (one prompt → one proof) |
| `r3_hard2000` | **multi-agent pipeline** (prove → verify → rank → refine → select) on the hard subset |
| `r3_500` | same pipeline, an earlier 500-problem run (older selector variant) |
| `r3_gen_refsel`(`_smoke`) | **augmentation** — extra `refine`/`select` samples from full-random bundle sampling of the existing proof pool (diversity boost; reuses cached prove/verify). refine/select turns only. |

Filter recipes:
- original-pipeline refine/select: `run_id in {{"r3_hard2000", "r3_500"}}`
- augmented refine/select: `run_id.startswith("r3_gen_refsel")`
- `prove` / `verify` turns come only from the original pipeline runs.

per_turn rows by run_id:
| run_id | rows |
|---|---|
{run_tbl}

## `per_turn` ({n_turn} rows) — SFT / distillation

One row = one teacher turn. `messages_json` holds the prompt (system+user); the assistant reply is
in `reasoning_content` + `content`. To render, build
`prompt + [{{"role": "assistant", "content": .., "reasoning_content": ..}}]`. Columns: `pipeline`
(plain | math_3r), `stage`, `candidate_id`, `verifier_idx`, `score`, `difficulty_*`, token counts,
`run_id`. Only clean turns (no error/truncation, non-empty output).

rows by stage:
| stage | rows |
|---|---|
{stage_tbl}

Stages: `plain` (single-shot proof) · `prove` (pipeline proof candidate) · `verify` (graded review
of a proof) · `refine` (improved proof) · `select` (picks the best candidate, returns an ID).

## `per_problem` ({n_prob} rows) — analysis / RL

One row = one problem (the hard subset spine). Nested JSON columns:
- `proofs_json`: candidate proofs. `math_3r` ones carry `verifications` (each with a verifier
  `score` 0/0.5/1 + text); `plain` ones have none.
- `refined_json`, `select_json`: refined proofs and selector turns (each entry tagged `run_id`).
- `difficulty_source` / `difficulty_value`, `final_*`, `selected_id(s)`, counts.

The proofs → verifications structure is the per-problem reward signal for RL.

## Notes for training

- **Too-easy problems removed**: problems where every scored proof was verified perfect
  (per-proof mean verifier score == 1.0) are excluded.
- Filter out `error` / `truncated` turns; prefer the **verifier `score`** over a turn's
  self-reported `score` (provers/refiners are over-confident).
- Augmented (`r3_gen_refsel`) `select` candidates are raw proofs (IDs `P#`); original-pipeline
  `select` candidates are refined proofs (IDs `R#`).
"""
    (out_dir / "README.md").write_text(yaml + body)


def _write(rows: list[dict], schema: pa.Schema, path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows, schema=schema), path, compression="zstd")
    back = pq.read_table(path)                       # read-back (host bit-flip safety)
    assert back.num_rows == len(rows), f"row count mismatch on readback for {path}"
    return back.num_rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plain-runs", nargs="*", default=[], help="collect.py run_ids")
    ap.add_argument("--math3r-runs", nargs="*", default=[], help="math_3r run_ids")
    ap.add_argument("--difficulty-from", nargs="*", default=[],
                    help="input parquet(s) to re-join difficulty_source/value by problem_id "
                         "(run.py doesn't persist them); e.g. distill_gen/math_3r/hard2000.parquet")
    ap.add_argument("--out-dir", type=Path, default=Path("/tmp/hf_dsflash_pack"))
    ap.add_argument("--repo", default=None, help="HF dataset id; required unless --no-upload")
    ap.add_argument("--no-upload", action="store_true", help="build + validate locally only")
    ap.add_argument("--sample", type=int, default=60, help="#turns to round-trip validate")
    ap.add_argument("--drop-easy", action="store_true",
                    help="drop problems where every scored math_3r proof was verified perfect "
                         "(proof-mean verifier score == 1.0) -> too easy for the teacher")
    args = ap.parse_args()

    if args.difficulty_from:
        global _DIFF
        _DIFF = load_diff_map(args.difficulty_from)
        print(f"[difficulty] re-join map: {len(_DIFF)} problem_ids from {args.difficulty_from}")

    # (b) per-problem first: spine = first math3r run (hard2000); merge other math3r + plain by pid.
    # Built first so we can derive the too-easy problem set and drop it from BOTH tables.
    probs = build_per_problem(args.math3r_runs, args.plain_runs)
    drop = easy_problem_ids(probs) if args.drop_easy else set()
    if drop:
        probs = [p for p in probs if p["problem_id"] not in drop]
        print(f"[drop-easy] excluding {len(drop)} too-easy problems (all proofs verifier-perfect)")

    # (a) per-turn (exclude dropped problem_ids across all pipelines)
    turns: list[dict] = []
    for rid in args.plain_runs:
        n0 = len(turns); turns.extend(t for t in plain_turns(rid) if t["problem_id"] not in drop)
        print(f"[per-turn] plain    {rid}: +{len(turns) - n0} usable turns")
    for rid in args.math3r_runs:
        n0 = len(turns); turns.extend(t for t in math3r_turns(rid) if t["problem_id"] not in drop)
        print(f"[per-turn] math_3r  {rid}: +{len(turns) - n0} usable turns")
    validate_turns(turns, args.sample)
    turn_path = args.out_dir / "data" / "per_turn.parquet"
    n = _write(turns, TURN_SCHEMA, turn_path)
    by_stage: dict[str, int] = {}
    for t in turns:
        by_stage[f"{t['pipeline']}/{t['stage']}"] = by_stage.get(f"{t['pipeline']}/{t['stage']}", 0) + 1
    print(f"[per-turn] wrote {turn_path} rows={n} ({turn_path.stat().st_size/1e6:.1f}MB) -- readback OK")
    print(f"[per-turn] by stage: {dict(sorted(by_stage.items()))}")

    prob_path = args.out_dir / "data" / "per_problem.parquet"
    if probs:
        spine = args.math3r_runs[0]
        enriched = sum(1 for p in probs if len(json.loads(p["source_runs_json"])) > 1)
        m = _write(probs, PROBLEM_SCHEMA, prob_path)
        print(f"[per-problem] spine={spine} problems={m} ({enriched} enriched by other sources) "
              f"({prob_path.stat().st_size/1e6:.1f}MB) -- readback OK")

    # dataset card with the two-config mapping (so load_dataset resolves each table)
    by_run: dict[str, int] = {}
    for t in turns:
        by_run[t["run_id"]] = by_run.get(t["run_id"], 0) + 1
    write_card(args.out_dir, len(turns), len(probs), by_stage, by_run)

    # provenance: copy each run's run_meta
    for root, runs in ((PLAIN_ROOT, args.plain_runs), (MATH3R_ROOT, args.math3r_runs)):
        for rid in runs:
            meta = root / rid / "run_meta.json"
            if meta.exists():
                (args.out_dir / f"run_meta.{rid}.json").write_text(meta.read_text())

    if args.no_upload or not args.repo:
        print(f"[pack] staged at {args.out_dir} -- NOT uploading "
              f"({'--no-upload' if args.no_upload else 'no --repo given'})")
        return 0

    from huggingface_hub import HfApi, create_repo
    api = HfApi()
    url = create_repo(args.repo, repo_type="dataset", private=True, exist_ok=True)
    print(f"[upload] repo (PRIVATE): {url}")
    api.upload_folder(folder_path=str(args.out_dir), repo_id=args.repo, repo_type="dataset",
                      commit_message=f"distill data: per-turn={len(turns)} per-problem={len(probs)}")
    print(f"[upload] done; files: {api.list_repo_files(args.repo, repo_type='dataset')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
