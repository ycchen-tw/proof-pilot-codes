# training/dflash — DFlash speculative-decoding draft training

Trains a **DFlash draft model** for an `olmo3_sink` target. DFlash is single-step
block-diffusion drafting: one draft forward proposes a whole block of tokens, which the
target then verifies. The draft here is an OLMo3-style 8-layer model with the same attention
sink as the target, trained with greedy-prefix filtering and a no-duplicate FA3 full-attention
block. The trained draft is deployed via [`deploy/dflash/`](../../deploy/dflash).

## Layout
| file | purpose |
|------|---------|
| `nodup_fa3_train_prod.py` | production trainer (checkpoint/resume, preflight); the entrypoint |
| `nodup_fa3_train.py` | validated model + loss/metrics core, imported by the prod trainer |
| `fa3_nodup_attention.py` | no-duplicate full-attention FA3 block used during training |
| `draft_model_olmo3.py` | the OLMo3-style DFlash draft model |
| `target_model.py`, `target_utils.py` | frozen target (FSDP2) + embedding/head sharing |
| `data.py`, `build_l4_pretokenized.py` | L4 packed-data loader + builder (from rollout dumps / teacher manifests) |
| `optimizer.py`, `lr_scheduler.py`, `tracker.py`, `utils.py`, `train.py` | training-loop support |
| `configs/` | draft configs (7B/32B × SWA window 128/512) |
| `tests/` | unit tests (attention, sampler resume, target, misc) |

## Usage
```bash
torchrun --nproc_per_node=8 training/dflash/nodup_fa3_train_prod.py \
    --target-model-path "$TARGET_MODEL_PATH" \
    --draft-config-path training/dflash/configs/dflash-olmo3-7b-8L-bs10-swa128-sink.json \
    --train-data-path "$DFLASH_TRAIN_DATA" \
    --output-dir "$DFLASH_OUTPUT_DIR" \
    --steps 12000 --window-size 128
```

## Notes
- Resource paths come from env vars (`TARGET_MODEL_PATH`, `DFLASH_TRAIN_DATA`,
  `DFLASH_OUTPUT_DIR`, `DFLASH_TOKENIZER`); configs are resolved relative to this directory.
- `build_l4_pretokenized.py` consumes a teacher manifest produced by
  [`teacher_extract/dataprep`](../teacher_extract) and reuses the FFD packer from `stage1_v2/build_l4.py`.
