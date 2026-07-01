# deploy/quant/ — serve quantized stage1-v2-7b under SGLang

Serves the compressed-tensors checkpoints produced by `../../quantization/` (GPTQ /
AWQ / MXFP4 / NVFP4 / FP8 …). Each quantized dir already carries a config with
`architectures=Olmo3SinkForCausalLM`, legacy rope keys, `sink_init_value`, and a
`quantization_config` that sglang auto-detects — so we only bind-mount the
sink-aware olmo2 model class (`../target/olmo2_sink.py`, which builds every Linear
through `quant_config`) over the image and point `--model-path` at the dir.

## Usage

```bash
MODEL=quantization/out/stage1-v2-7b-gptq-w4a16 \
  GPU=0 PORT=30020 bash run_quant_server.sh

# in another shell once it's up:
uv run python test_quant_client.py --port 30020 --temp 0
```

`run_quant_server.sh` env knobs: `MODEL` (required), `GPU`, `PORT`, `ATTN`
(default fa3 — required for the in-kernel sink), `MEMFRAC`, `CTX`, `QUANT`
(override auto-detected quant method if needed).

## Notes

- H200 is sm90 (Hopper). int4 (GPTQ/AWQ via compressed-tensors WNA16) and FP8 run
  natively. FP4 formats (MXFP4/NVFP4) have no native Hopper tensor-core path and
  rely on sglang's emulation/marlin kernels — see the per-format status table.
- The sink is loaded by `olmo2_sink.py:load_weights` as a separate per-head
  parameter (not quantized); look for `Olmo3Sink: loaded 32 attention-sink
  tensors` in the server log to confirm.
