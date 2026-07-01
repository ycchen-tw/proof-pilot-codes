"""Materialize the single-round prover candidates from the eval sweep JSON into
distill_gen/prompts/*.txt files that collect.py can load.

Source: evaluation/data/imo_proofbench_single_round_prompt_templates.json (t0..t7).
We skip t1 (Huang-Yang rigorous) because it duplicates the already-materialized
imo25_prover.txt (same IMO25 / Huang-Yang lineage, same Summary+Detailed structure).

Each candidate is a system_prompt + user_prompt_template (the user part carries {problem}).
collect.py's build_messages splits on the ===SYSTEM===/===USER=== delimiters, so we write:

    ===SYSTEM===
    <system_prompt>
    ===USER===
    <user_prompt_template with {problem}>

Run:
    uv run python distill_gen/materialize_templates.py
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "evaluation" / "data" / "imo_proofbench_single_round_prompt_templates.json"
OUT = Path(__file__).resolve().parent / "prompts"

# JSON id stem -> short stable filename used in the --template pool. t1 intentionally absent.
NAME_MAP = {
    "t0_minimal_rigorous_baseline": "t0_minimal",
    "t2_huang_yang_self_repair_single_round": "t2_selfrepair",
    "t3_deepseekmath_v2_self_verifiable_proof": "t3_dsmv2_lite",
    "t4_star_polyamath_plan_verify_single_round": "t4_polya",
    "t5_momus_lite_dialectic_single_round": "t5_momus",
    "t6_aletheia_generate_verify_revise_single_round": "t6_aletheia",
    "t7_imo_proofbench_rubric_aware_writer": "t7_rubric",
}


def main() -> None:
    data = json.loads(SRC.read_text())
    by_id = {t["id"]: t for t in data["templates"]}
    OUT.mkdir(parents=True, exist_ok=True)
    for jid, fname in NAME_MAP.items():
        t = by_id[jid]
        sys_p = t["system_prompt"].strip()
        usr_p = t["user_prompt_template"]
        if "{problem}" not in usr_p:
            raise ValueError(f"{jid}: user_prompt_template missing {{problem}} placeholder")
        body = f"===SYSTEM===\n{sys_p}\n===USER===\n{usr_p}\n"
        path = OUT / f"{fname}.txt"
        path.write_text(body)
        print(f"wrote {path.relative_to(REPO)}  ({len(body)} bytes)  <- {jid}")


if __name__ == "__main__":
    main()
