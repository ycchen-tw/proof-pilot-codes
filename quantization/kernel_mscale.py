#!/usr/bin/env python3
"""GPTQ-Marlin(W4A16) vs fp8 vs bf16 dense Linear latency vs M, using REAL GPTQ
weights (down_proj 11008->4096) so Marlin repack is valid. sm120."""
import time, torch
from sglang.srt.distributed import init_distributed_environment, initialize_model_parallel
init_distributed_environment(world_size=1, rank=0, local_rank=0,
                             distributed_init_method="tcp://127.0.0.1:29531", backend="nccl")
initialize_model_parallel(tensor_model_parallel_size=1)
from sglang.srt.layers.linear import RowParallelLinear
from sglang.srt.layers.quantization.compressed_tensors.compressed_tensors import CompressedTensorsConfig
from safetensors import safe_open

dev = "cuda"; torch.set_grad_enabled(False)
# dense sweep to find Marlin per-token-efficiency peak + tile-alignment effects
import os
if os.environ.get("MSCALE_MS"):     # explicit comma-sep list, e.g. tile-boundary sweep
    Ms = [int(x) for x in os.environ["MSCALE_MS"].split(",")]
elif os.environ.get("MSCALE_SMALL"):  # verify-M range for dflash block sweep (M ≈ block_size at bs=1)
    Ms = [1, 2, 4, 6, 8, 11, 12, 16, 24, 32, 48, 64]
else:
    Ms = [8, 16, 24, 32, 40, 48, 56, 64, 72, 80, 88, 96, 104, 112, 120, 128, 144, 160, 192, 224, 256]
IN, OUT = 11008, 4096
CKPT = "/workspace/proof-pilot/quantization/out/stage1-v2-7b-gptq-w4a16/model.safetensors"
PFX = "model.layers.0.mlp.down_proj"

W4A16 = CompressedTensorsConfig.from_config({
    "config_groups": {"group_0": {"targets": ["Linear"],
        "weights": {"num_bits": 4, "type": "int", "symmetric": True, "strategy": "group",
                    "group_size": 128, "actorder": None, "dynamic": False}}},
    "format": "pack-quantized", "ignore": [], "quant_method": "compressed-tensors"})
FP8 = CompressedTensorsConfig.from_config({
    "config_groups": {"group_0": {"targets": ["Linear"],
        "weights": {"num_bits": 8, "type": "float", "symmetric": True, "strategy": "channel", "dynamic": False},
        "input_activations": {"num_bits": 8, "type": "float", "symmetric": True, "strategy": "token", "dynamic": True}}},
    "format": "float-quantized", "ignore": [], "quant_method": "compressed-tensors"})


def time_fwd(layer, M, iters=80):
    x = torch.randn(M, IN, device=dev, dtype=torch.bfloat16)
    for _ in range(10): layer(x)
    torch.cuda.synchronize(); t0 = time.time()
    for _ in range(iters): layer(x)
    torch.cuda.synchronize()
    return (time.time() - t0) / iters * 1e3


def build_w4a16():
    lyr = RowParallelLinear(IN, OUT, bias=False, quant_config=W4A16, prefix=PFX).to(dev)
    params = dict(lyr.named_parameters())
    with safe_open(CKPT, framework="pt") as f:
        for nm in ["weight_packed", "weight_scale", "weight_shape"]:
            if nm in params:
                params[nm].data.copy_(f.get_tensor(f"{PFX}.{nm}").to(params[nm].dtype).to(dev))
    lyr.quant_method.process_weights_after_loading(lyr)
    return lyr


def build_fp8():
    lyr = RowParallelLinear(IN, OUT, bias=False, quant_config=FP8, prefix=PFX).to(dev)
    for n, p in lyr.named_parameters():
        if p.dtype == torch.float8_e4m3fn:
            p.data.copy_(torch.randn(p.shape, device=dev).clamp(-3, 3).to(torch.float8_e4m3fn))
        elif p.is_floating_point():
            p.data.normal_(0, 0.02)
    if hasattr(lyr.quant_method, "process_weights_after_loading"):
        lyr.quant_method.process_weights_after_loading(lyr)
    return lyr


def build_bf16():
    return torch.nn.Linear(IN, OUT, bias=False).to(dev).to(torch.bfloat16)


if __name__ == "__main__":
    print(f"GPU cc={torch.cuda.get_device_capability()}  down_proj {IN}->{OUT}\n")
    layers = {}
    for k, fn in [("bf16", build_bf16), ("fp8", build_fp8), ("w4a16-gptq", build_w4a16)]:
        try: layers[k] = fn()
        except Exception as e: print(f"build {k} FAILED: {str(e)[:120]}")
    print("  M    " + "".join(f"{k+' ms':>13}" for k in layers) + f"{'int4 tok/ms':>13}")
    for M in Ms:
        row = f"  {M:<5}"; w4t = None
        for k, lyr in layers.items():
            try:
                t = time_fwd(lyr, M); row += f"{t:>13.4f}"
                if k == "w4a16-gptq": w4t = t
            except Exception: row += f"{'ERR':>13}"
        row += f"{(M/w4t if w4t else 0):>13.0f}"
        print(row)
    print("\n  (int4 tok/ms = M/time; higher=more GEMM-efficient; peak=optimal verify M)")
