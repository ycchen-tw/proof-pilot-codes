"""W1 benchmark: run the full proof_agent loop over a few ProofBench problems against one server,
recording per-problem wall-clock + saving final proofs (for later precision grading).

Run one instance per config (different port/model/GPU) in parallel. Example:
    python bench_loop.py --port 30000 --model <gptq-dir> --tag w4a8 \
        --n 3 --provers 6 --verify-k 2 --refiners 3 --selectors 4 \
        --max-tokens 48000 --budget 2400 --out /tmp/w1_bench/w4a8.jsonl
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "kaggle" / "proof_agent"))
from agent import ProofAgent  # noqa: E402

import pyarrow.parquet as pq  # noqa: E402

PROOFBENCH = REPO / "distill_gen" / "math_3r" / "proofbench_v2.parquet"


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--model", required=True, help="model path (for tokenizer + served name)")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--input", type=Path, default=PROOFBENCH)
    ap.add_argument("--n", type=int, default=3, help="#problems")
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--provers", type=int, default=6)
    ap.add_argument("--verify-k", type=int, default=2)
    ap.add_argument("--refiners", type=int, default=3)
    ap.add_argument("--selectors", type=int, default=4)
    ap.add_argument("--max-tokens", type=int, default=48000)
    ap.add_argument("--budget", type=float, default=2400.0, help="wall-clock per problem (s)")
    ap.add_argument("--concurrency", type=int, default=16)
    ap.add_argument("--est-tps", type=float, default=20.0)
    ap.add_argument("--temperature", type=float, default=0.6)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    rows = pq.read_table(args.input, columns=["problem", "competition", "source"]).to_pylist()
    rows = rows[args.offset: args.offset + args.n]

    agent = ProofAgent(f"http://127.0.0.1:{args.port}", args.model, temperature=args.temperature,
                       max_tokens=args.max_tokens, concurrency=args.concurrency, est_tps=args.est_tps)
    if not await agent.health():
        print(f"[{args.tag}] server :{args.port} not healthy", flush=True); sys.exit(1)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fout = open(args.out, "w")
    t_all = time.monotonic()
    for i, row in enumerate(rows):
        tr = await agent.solve(row["problem"], budget_s=args.budget, num_provers=args.provers,
                               verify_k=args.verify_k, num_refiners=args.refiners,
                               num_selectors=args.selectors)
        c, to = tr["counts"], tr["totals"]
        rec = {"tag": args.tag, "idx": args.offset + i, "competition": row.get("competition"),
               "problem": row["problem"], "final_proof": tr["final_proof"],
               "final_source": tr["final_source"], "wall_s": tr.get("wall_s"),
               "counts": c, "totals": to}
        fout.write(json.dumps(rec, ensure_ascii=False) + "\n"); fout.flush()
        print(f"[{args.tag}] #{args.offset+i} wall={tr.get('wall_s',0):.0f}s "
              f"src={tr['final_source']} valid={c.get('n_valid_proofs')}/{args.provers} "
              f"refined={c.get('n_refined_valid')} calls={to.get('n_calls')} "
              f"errs={to.get('n_errors')} salv={to.get('n_salvaged')} "
              f"ctok={to.get('completion_tokens')} prooflen={len(tr['final_proof'] or '')}", flush=True)
    fout.close()
    await agent.aclose()
    print(f"[{args.tag}] all done in {(time.monotonic()-t_all)/60:.1f} min -> {args.out}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
