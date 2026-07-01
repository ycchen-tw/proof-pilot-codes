"""Package one or more collect.py runs into a single parquet and upload to a PRIVATE
HuggingFace dataset (teacher-distillation data).

Each run's outputs/<run_id>/records.jsonl is read, tagged with `run_id`, and concatenated
into data/records.parquet. `messages` is stored as a JSON string (`messages_json`) for robust
loading; every other field is kept verbatim (incl. reasoning_content / content). Each run's
run_meta.json is uploaded alongside for provenance. The dataset card (README.md) is maintained
directly on the hub (upload_folder adds/updates, never deletes it).

CONFIDENTIALITY: the repo is created PRIVATE and the card carries no competition / project
naming (project secrecy clause). Keep it private.

Auth: uses the cached HuggingFace login (huggingface-cli login) or HF_TOKEN; never hard-coded.

Usage:
    uv run python distill_gen/upload_hf.py \
        --repo ycchen/dsflash-proof-distill-test \
        --runs mix_v1 mix_v2
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

OUT_ROOT = Path(__file__).resolve().parent / "outputs"

SCHEMA = pa.schema([
    ("run_id", pa.string()), ("problem_id", pa.string()), ("sample", pa.int64()),
    ("template", pa.string()), ("effort", pa.string()), ("seed", pa.int64()),
    ("origin", pa.string()), ("category", pa.string()), ("competition", pa.string()),
    ("source", pa.string()), ("nm_uuid", pa.string()), ("problem", pa.string()),
    ("messages_json", pa.string()), ("reasoning_content", pa.string()), ("content", pa.string()),
    ("finish_reason", pa.string()), ("truncated", pa.bool_()), ("self_score", pa.string()),
    ("error", pa.string()), ("prompt_tokens", pa.int64()), ("completion_tokens", pa.int64()),
    ("reasoning_tokens", pa.int64()), ("latency_s", pa.float64()),
    ("model", pa.string()), ("max_tokens", pa.int64()),
])


def load_run(run_id: str) -> list[dict]:
    path = OUT_ROOT / run_id / "records.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"no records for run {run_id!r} at {path}")
    rows = []
    for line in open(path):
        if not line.strip():
            continue
        r = json.loads(line)
        rows.append({
            "run_id": run_id, "problem_id": r["problem_id"], "sample": r["sample"],
            "template": r["template"], "effort": r["effort"], "seed": r["seed"],
            "origin": r["origin"], "category": r["category"], "competition": r["competition"],
            "source": r["source"], "nm_uuid": r["nm_uuid"], "problem": r["problem"],
            "messages_json": json.dumps(r["messages"], ensure_ascii=False),
            "reasoning_content": r["reasoning_content"], "content": r["content"],
            "finish_reason": r["finish_reason"], "truncated": r["truncated"],
            "self_score": r["self_score"], "error": r["error"],
            "prompt_tokens": r["prompt_tokens"], "completion_tokens": r["completion_tokens"],
            "reasoning_tokens": r["reasoning_tokens"], "latency_s": r["latency_s"],
            "model": r["model"], "max_tokens": r["max_tokens"],
        })
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="HF dataset id, e.g. ycchen/dsflash-proof-distill-test")
    ap.add_argument("--runs", nargs="+", required=True, help="run_id(s) under outputs/ to include")
    ap.add_argument("--stage", type=Path, default=Path("/tmp/hf_dsflash"),
                    help="local staging dir to assemble before upload")
    ap.add_argument("--no-upload", action="store_true", help="build+verify locally, skip upload")
    args = ap.parse_args()

    rows: list[dict] = []
    for run_id in args.runs:
        r = load_run(run_id)
        print(f"[pack] {run_id}: {len(r)} rows")
        rows.extend(r)

    stage = args.stage
    (stage / "data").mkdir(parents=True, exist_ok=True)
    out = stage / "data" / "records.parquet"
    pq.write_table(pa.Table.from_pylist(rows, schema=SCHEMA), out, compression="zstd")

    # read-back verify (host bit-flip safety, memory host-memory-instability)
    back = pq.read_table(out)
    assert back.num_rows == len(rows), "row count mismatch on readback"
    assert set(back.column("problem_id").to_pylist()) == {r["problem_id"] for r in rows}
    clean = sum(1 for r in rows if not r["error"] and not r["truncated"] and (r["content"] or "").strip())
    print(f"[pack] wrote {out} rows={back.num_rows} ({out.stat().st_size/1e6:.1f}MB) "
          f"clean={clean} -- readback OK")

    # copy each run's run_meta for provenance
    for run_id in args.runs:
        meta = OUT_ROOT / run_id / "run_meta.json"
        if meta.exists():
            (stage / f"run_meta.{run_id}.json").write_text(meta.read_text())

    if args.no_upload:
        print(f"[pack] --no-upload: staged at {stage}, not uploading")
        return

    from huggingface_hub import HfApi, create_repo
    api = HfApi()
    url = create_repo(args.repo, repo_type="dataset", private=True, exist_ok=True)
    print(f"[upload] repo (PRIVATE): {url}")
    api.upload_folder(folder_path=str(stage), repo_id=args.repo, repo_type="dataset",
                      commit_message=f"distill data: runs {', '.join(args.runs)} ({len(rows)} rows)")
    print(f"[upload] done; files: {api.list_repo_files(args.repo, repo_type='dataset')}")


if __name__ == "__main__":
    main()
