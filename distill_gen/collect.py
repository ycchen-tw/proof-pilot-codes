"""Off-policy distillation data collection: generate teacher (DeepSeek-V4) proofs over the
deduped olympiad prompt pool. Each (problem, sample) is assigned ONE randomly-chosen
proof-writing template and ONE reasoning effort (high/max), via a seeded hash so the whole
run is reproducible and resume-safe.

Design notes
------------
- Reuses evaluation/harness/async_client.AsyncChatClient (httpx, high concurrency). We call
  `chat_raw` (not `chat`) so we keep the model's `reasoning_content` (thinking) — distillation
  trains on it (stage-1 L3 render uses drop_thinking=False; see memory persist-full-api-data).
- DETERMINISTIC RANDOM: (template, effort) = f(problem_id, sample, seed). Pure function, so a
  rerun reproduces identical assignments and resume matches exactly. Changing --seed / --high-frac
  / the --template list (or its ORDER) is a different logical run -> use a fresh --run-id.
- LOSSLESS append-JSONL with resume: writes outputs/<run_id>/records.jsonl; rerunning the same
  command skips (problem_id, sample) keys already present. append+flush, resumable under the
  host's bit-flip instability (memory host-memory-instability).
- We save the full rendered `messages` (prompt), `reasoning_content` (thinking) and `content`
  (final proof) — prompt/reasoning/final all preserved.
- RUNAWAY guard: max_tokens is a hard combined (reasoning+content) budget. finish_reason=="length"
  is flagged `truncated` and counted; we do NOT auto-retry (it would just truncate again).
- Templates: a file with `{problem}` is sent as a single user message; a file WITHOUT the
  placeholder (e.g. imo25_prover) is sent as a system message with the problem as the user turn.

Smoke test:
    DEEPSEEK_API_KEY=... uv run python distill_gen/collect.py --limit 2 --run-id smoke

Real run:
    DEEPSEEK_API_KEY=... uv run python distill_gen/collect.py \
        --k 1 --high-frac 0.75 --max-tokens 120000 --concurrency 2500 --run-id mix_v1
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import pyarrow.parquet as pq

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "evaluation" / "harness"))
from async_client import AsyncChatClient  # noqa: E402

PROMPT_DIR = Path(__file__).resolve().parent / "prompts"
DEFAULT_INPUT = Path(__file__).resolve().parent / "problems" / "problems.parquet"
OUT_ROOT = Path(__file__).resolve().parent / "outputs"
BASE_URL = "https://api.deepseek.com/v1"
MODEL = "deepseek-v4-flash"
ALL_TEMPLATES = "dsmv2_a1,proofbench_generator,imo25_prover"


def pid_of(problem: str) -> str:
    return hashlib.blake2b(problem.encode(), digest_size=8).hexdigest()


def assign(pid: str, sample: int, seed: int, templates: list[str], high_frac: float) -> tuple[str, str]:
    """Deterministically pick (template, effort) for a (problem, sample). Pure function of the
    inputs -> reproducible and resume-safe. templates ORDER matters (kept in run_meta)."""
    h = hashlib.blake2b(f"{pid}|{sample}|{seed}".encode(), digest_size=16).digest()
    template = templates[h[0] % len(templates)]
    effort = "high" if h[1] < int(256 * high_frac) else "max"
    return template, effort


def load_template(name: str) -> str:
    p = PROMPT_DIR / f"{name}.txt"
    if not p.exists():
        raise FileNotFoundError(f"template {name!r} not found at {p}")
    return p.read_text()


SYS_DELIM = "===SYSTEM==="
USR_DELIM = "===USER==="


def build_messages(template: str, problem: str) -> list[dict]:
    # explicit system+user template (sweep candidates t0/t2/.../t7): the user part carries {problem}
    if SYS_DELIM in template and USR_DELIM in template:
        sys_part = template.split(SYS_DELIM, 1)[1].split(USR_DELIM, 1)[0].strip()
        usr_part = template.split(USR_DELIM, 1)[1].strip()
        if "{problem}" not in usr_part:
            raise ValueError("system+user template missing {problem} in its USER section")
        return [{"role": "system", "content": sys_part},
                {"role": "user", "content": usr_part.replace("{problem}", problem)}]
    if "{problem}" in template:
        return [{"role": "user", "content": template.replace("{problem}", problem)}]
    # placeholder-free template (e.g. IMO25) -> system instructions + problem as user turn
    return [{"role": "system", "content": template}, {"role": "user", "content": problem}]


def parse_pool(spec: str) -> tuple[list[str], dict[str, int], list[str]]:
    """Parse a `--template` pool that may carry per-template weights as `name:weight`.
    Returns (unique names in input order, weights, weighted-expanded list). The expanded
    list is what assign() indexes into, so weight = number of repeats = draw probability.
    ORDER and weights are recorded in run_meta (they change the assignment hash)."""
    names: list[str] = []
    weights: dict[str, int] = {}
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            name, w = part.rsplit(":", 1)
            name, w = name.strip(), int(w)
            if w < 1:
                raise ValueError(f"template weight must be >= 1, got {part!r}")
        else:
            name, w = part, 1
        if name in weights:
            raise ValueError(f"template {name!r} listed twice in --template")
        names.append(name)
        weights[name] = w
    expanded = [name for name in names for _ in range(weights[name])]
    return names, weights, expanded


def done_keys(records_path: Path) -> set[tuple[str, int]]:
    keys: set[tuple[str, int]] = set()
    if not records_path.exists():
        return keys
    with open(records_path) as f:
        for line in f:
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue  # tolerate a torn last line from an interrupted run
            keys.add((r["problem_id"], r["sample"]))
    return keys


def git_commit() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO,
                                       text=True).strip()
    except Exception:  # noqa: BLE001
        return None


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", default=ALL_TEMPLATES,
                    help="comma-separated template pool to randomly draw from (ORDER matters)")
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--run-id", default="run")
    ap.add_argument("--k", type=int, default=1, help="samples per problem")
    ap.add_argument("--high-frac", type=float, default=0.75,
                    help="fraction of calls using reasoning=high; rest use max (default 3:1)")
    ap.add_argument("--seed", type=int, default=1234, help="global seed for template/effort draw")
    ap.add_argument("--max-tokens", type=int, default=120000,
                    help="hard combined reasoning+content budget")
    ap.add_argument("--concurrency", type=int, default=32, help="in-flight requests")
    ap.add_argument("--max-retries", type=int, default=1,
                    help="attempts per request (1 = no retry; failures are recorded, not retried)")
    ap.add_argument("--limit", type=int, default=0, help="cap #problems (0 = all); for testing")
    ap.add_argument("--origin", default="", help="filter by origin substring (e.g. FineProofs)")
    args = ap.parse_args()

    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise SystemExit("set DEEPSEEK_API_KEY in the environment (never hard-code it)")

    # template pool may be weighted: "t3:5,dsmv2_a1:4,imo25_prover:3,...". `templates` is the
    # weighted-expanded list assign() draws from; tmpl_text is keyed by the unique names.
    tmpl_names, tmpl_weights, templates = parse_pool(args.template)
    tmpl_text = {t: load_template(t) for t in tmpl_names}

    cols = ["problem", "origin", "category", "competition", "source", "nm_uuid"]
    rows = pq.read_table(args.input, columns=cols).to_pylist()
    if args.origin:
        rows = [r for r in rows if args.origin in (r["origin"] or "")]
    if args.limit:
        rows = rows[: args.limit]

    out_dir = OUT_ROOT / args.run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    records_path = out_dir / "records.jsonl"
    done = done_keys(records_path)

    # build the task list, skipping already-done (problem, sample); assign template+effort
    tasks = []
    from collections import Counter
    plan_t, plan_e = Counter(), Counter()
    for r in rows:
        pid = pid_of(r["problem"])
        for s in range(args.k):
            tname, effort = assign(pid, s, args.seed, templates, args.high_frac)
            plan_t[tname] += 1
            plan_e[effort] += 1
            if (pid, s) not in done:
                tasks.append((pid, s, tname, effort, r))
    total = len(rows) * args.k
    print(f"[collect] problems={len(rows)} k={args.k} -> planned={total} done={len(done)} "
          f"todo={len(tasks)}", flush=True)
    print(f"[collect] template mix (planned): {dict(plan_t)}", flush=True)
    print(f"[collect] effort   mix (planned): {dict(plan_e)} (high-frac={args.high_frac})", flush=True)

    meta = {
        "run_id": args.run_id, "model": MODEL, "base_url": BASE_URL,
        "high_frac": args.high_frac, "seed": args.seed, "max_tokens": args.max_tokens,
        "k": args.k, "concurrency": args.concurrency, "max_retries": args.max_retries,
        "input": str(args.input),
        "n_problems": len(rows), "origin_filter": args.origin or None,
        "template_spec": args.template,          # raw --template string
        "template_weights": tmpl_weights,         # name -> weight
        "template_pool_expanded": templates,      # weighted-expanded list; ORDER matters for the hash
        "template_sha256": {t: hashlib.sha256(tmpl_text[t].encode()).hexdigest() for t in tmpl_names},
        "git_commit": git_commit(),
    }
    (out_dir / "run_meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))

    if not tasks:
        print("[collect] nothing to do (all done).")
        return

    client = AsyncChatClient(BASE_URL, MODEL, api_key=key,
                             max_connections=args.concurrency + 8, max_retries=args.max_retries)
    sem = asyncio.Semaphore(args.concurrency)
    fout = open(records_path, "a")          # append: resume-safe
    write_lock = asyncio.Lock()
    state = {"done": 0, "trunc": 0, "err": 0, "ctok": 0, "rtok": 0,
             "high": 0, "max": 0, "t0": time.monotonic()}

    async def worker(pid: str, sample: int, tname: str, effort: str, row: dict) -> None:
        async with sem:
            messages = build_messages(tmpl_text[tname], row["problem"])
            # common identity/provenance fields shared by success AND error records
            rec = {
                "problem_id": pid, "sample": sample,
                "template": tname, "effort": effort, "seed": args.seed,
                "origin": row["origin"], "category": row["category"],
                "competition": row["competition"], "source": row["source"],
                "nm_uuid": row["nm_uuid"], "problem": row["problem"],
                "messages": messages,                               # full rendered prompt
                "reasoning_content": "", "content": "",             # thinking / final proof
                "finish_reason": None, "truncated": False, "self_score": None,
                "error": None,                                      # set iff the call failed
                "prompt_tokens": None, "completion_tokens": None,
                "reasoning_tokens": None, "latency_s": None,
                "model": MODEL, "max_tokens": args.max_tokens,
            }
            # SINGLE attempt — no retry (client built with max_retries=args.max_retries,
            # default 1). On failure we record an error row and move on; the same item is
            # never re-attempted within a run, and resume skips it (no repeated erroring).
            try:
                out = await client.chat_raw(messages, max_tokens=args.max_tokens,
                                            reasoning=effort)
                msg = out["message"]
                content = msg.get("content") or ""
                sc = re.search(r"\\boxed\{([^}]*)\}", content)
                rec.update(
                    reasoning_content=msg.get("reasoning_content") or "", content=content,
                    finish_reason=out["finish_reason"],
                    truncated=out["finish_reason"] == "length",
                    self_score=sc.group(1) if sc else None,
                    prompt_tokens=out["prompt_tokens"], completion_tokens=out["completion_tokens"],
                    reasoning_tokens=out["reasoning_tokens"], latency_s=out["latency_s"],
                )
            except Exception as e:  # noqa: BLE001 - record the failure, do NOT retry (max_retries=1)
                # fail-loud: keep the root cause. httpx errors sometimes have an empty str(),
                # so record a repr chain by walking __cause__/__context__ (cycle-guarded).
                parts, cur, seen = [], e, set()
                while cur is not None and id(cur) not in seen:
                    seen.add(id(cur))
                    parts.append(repr(cur))
                    cur = cur.__cause__ or cur.__context__
                rec.update(finish_reason="error", error=" <- ".join(parts))
                print(f"  [err] pid={pid} {tname}/{effort}#{sample}: {rec['error']}", flush=True)

            async with write_lock:
                fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
                fout.flush()
                state["done"] += 1
                if rec["error"]:
                    state["err"] += 1
                else:
                    state["trunc"] += int(rec["truncated"])
                    state[effort] += 1
                    state["ctok"] += rec["completion_tokens"] or 0
                    state["rtok"] += rec["reasoning_tokens"] or 0
                n = state["done"]
                if n % 50 == 0 or n == len(tasks):
                    dt = time.monotonic() - state["t0"]
                    print(f"  [{n}/{len(tasks)}] high={state['high']} max={state['max']} "
                          f"trunc={state['trunc']} err={state['err']} "
                          f"| {state['ctok']/1e6:.1f}M ctok ({state['rtok']/1e6:.1f}M reasoning) "
                          f"| {n/dt*60:.0f} req/min", flush=True)

    try:
        await asyncio.gather(*(worker(*t) for t in tasks))
    finally:
        fout.close()
        await client.aclose()
    print(f"[collect] finished: {state['done']} written "
          f"(high={state['high']} max={state['max']}), {state['trunc']} truncated, "
          f"{state['err']} errored -> {records_path}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
