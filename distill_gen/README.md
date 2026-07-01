# distill_gen — teacher data generation

Generates proof / verify / refine / select data from the **DeepSeek-V4 teacher** on a deduplicated
olympiad problem pool. This is the offline data source for the student's SFT-stage-2 and distillation
training. Its multi-agent `math_3r/` pipeline is also the blueprint for the final Kaggle agentic loop
(the prove→verify→refine→select structure is shared).

Related: `training/teacher_extract/` extracts teacher *hidden states* (soft-distillation targets);
this directory calls the teacher *API* to collect teacher *text* (including chain-of-thought).

## Layout

| path | purpose |
|------|---------|
| `collect.py` | Single-shot collector: one weighted prover template + effort per problem, async high-concurrency, seeded-hash assignment, lossless resume. |
| `math_3r/` | Multi-agent pipeline: prove(6)→verify→rank→refine→select(refined-only), full trace saved. See `math_3r/README.md`. |
| `math_3r/gen_refsel.py` | Augmentation: re-sample bundles over an existing proof pool to add cheap refine/select samples. |
| `pack_hf.py` | Packs all generators' traces into one HF dataset (`per_turn` distillation table + `per_problem` analysis/RL table; every row carries a `run_id` provenance tag). |
| `prompts/` | 10 prover prompt templates (3 original + 7 materialized from the eval sweep); `catalog.md` lists all sources. |
| `problems/` | Input prompt pool: `problems.parquet` (9,834 unique problems, FineProofs + Nemotron, deduplicated). |
| `materialize_templates.py` | Regenerates the sweep-derived templates from the eval sweep JSON. |
| `upload_hf.py` | Publishes the packed dataset to the Hugging Face Hub. |

## Usage

```bash
# single-shot collection
DEEPSEEK_API_KEY=... uv run python distill_gen/collect.py \
    --input distill_gen/problems/problems.parquet --run-id r1 --high-frac 0.9

# multi-agent pipeline (see math_3r/README.md for options)
DEEPSEEK_API_KEY=... uv run python distill_gen/math_3r/run.py \
    --input distill_gen/math_3r/hard2000.parquet --run-id r3

# pack all runs into an HF dataset
uv run python distill_gen/pack_hf.py --out <hf-repo-or-dir>
```

`DEEPSEEK_API_KEY` is read from the environment (never hard-coded). `base_url` defaults to the DeepSeek API.

## Notes

- Assignment `(template, effort)` is a pure `blake2b(problem_id, sample, seed)` function → reproducible and
  resume-safe. Changing `--seed` / `--high-frac` / the template pool is a different logical run: use a new `--run-id`.
- `max_tokens` is a combined reasoning+content budget; `finish_reason == "length"` rows are flagged `truncated`
  and never auto-retried. Failed calls are written as `error` records and skipped on resume.
- Training should use the **verifier** score as the quality signal, not the prover/refiner self-score
  (self-scores are over-confident, ~92% "1").
