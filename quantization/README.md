# quantization

Post-training quantization of `olmo3_sink` checkpoints into
[compressed-tensors](https://github.com/neuralmagic/compressed-tensors) format for SGLang
serving, using [llm-compressor](https://github.com/vllm-project/llm-compressor). The
delivered Kaggle model uses **GPTQ-w4a16** (int4 weight-only, symmetric, group-128); on the
RTX PRO 6000 (sm120) it decodes ~2.3× faster than fp8 via the Marlin W4A16 kernel.

## Layout
| file | purpose |
|---|---|
| `common.py` | stock-OLMo3 loader + L4 calibration data + attention-sink merge/finalize (+ monkeypatch for an llm-compressor ModuleDict recursion bug) |
| `quantize.py` | scheme registry (gptq / awq / mxfp4(±a16) / nvfp4(±a16) / w4a16-rtn / fp8) → `out/<model>-<scheme>/` |
| `quantize_draft.py` | int4-MLP RTN quantization of the DFlash draft (keeps fused-KV in bf16) |
| `ablation.py`, `ablation_results.json` | quantized-vs-bf16 accuracy comparison |
| `bench_serving.py` | decode / prefill throughput benchmark |
| `sink_patch.py`, `kernel_mscale.py` | sink handling + Marlin microscale helpers |
| `phase*_sink{on,off}_*.json` | calibration configs for the sink-on/off long-context ablation |

## Usage
Runs in an **isolated venv** (llm-compressor pins transformers 4.57 / torch 2.11):

```bash
cd quantization
.venv/bin/python quantize.py --scheme gptq-w4a16   # -> out/<model>-gptq-w4a16/
```

Model/output locations resolve from `PP_ROOT` (defaults to the repo root) and the standard
model-path env vars. Attention sinks are merged into the weights before quantization; the
patched checkpoint serves through `deploy/quant/`.

## Notes
- `nvfp4*` schemes need Blackwell hardware; `gptq / awq / mxfp4(±a16) / w4a16-rtn / fp8` are validated on SGLang.
- Sink-aware calibration matters at long context — see the `phase*` ablation configs.
