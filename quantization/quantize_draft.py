#!/usr/bin/env python3
"""int4-quantize the DFlash draft's MLP (gate/up/down) only, keep qkv/o + all
dflash-specific tensors (fc / hidden_norm / sinks / mask_embed) in bf16.

Why RTN (data-free): GPTQ's Hessian calib needs the draft's REAL inputs = target
hidden states (the draft is not a standalone LM), impractical via stock tooling.
A fake-quant probe (deploy/dflash/probe_int4mlp_draft.py) showed int4-MLP costs
~0 acceptance (Δtau -0.6%), so RTN is the right call for a draft (output stays
lossless; only tau matters). MLP-only keeps qkv unquantized -> DFlash fused-KV
materialization stays on.

Pipeline: load draft as a *stock Olmo3 8L* (the draft is Olmo3-structured:
post-norm + qk-norm), RTN-quantize MLP only (data-free), then SURGERY: the stock
load drops the dflash tensors (fc/hidden_norm/sinks/mask_embed) and invents random
embed/lm_head -> restore the real dflash tensors, drop the random ones, rename to
the draft's bare naming, write the dflash config + a compressed-tensors quant cfg.

Run in the quant venv on a dev GPU:
  .venv/bin/python quantize_draft.py
"""
import json
import os
import shutil

SRC = os.environ.get("PP_DRAFT_SRC",
                     "outputs/dflash-canonical-32b-v2test-phaseL-deploy")
BASE = os.environ.get("PP_DRAFT_BASE", "quantization/base-draft")
OUT_LLMC = os.environ.get("PP_DRAFT_OUT_LLMC",
                          "quantization/out/draft-llmc-tmp")
OUT = os.environ.get("PP_DRAFT_OUT",
                     "quantization/out/dflash-32b-phaseL-int4mlp")


def build_base_olmo3(src, base):
    """stock-Olmo3-loadable 8L view of the draft (drops dflash tensors on load)."""
    os.makedirs(base, exist_ok=True)
    c = json.load(open(f"{src}/config.json"))
    olmo = {
        "architectures": ["Olmo3ForCausalLM"], "model_type": "olmo3",
        "hidden_size": c["hidden_size"], "intermediate_size": c["intermediate_size"],
        "num_hidden_layers": c["num_hidden_layers"], "num_attention_heads": c["num_attention_heads"],
        "num_key_value_heads": c["num_key_value_heads"], "head_dim": c["head_dim"],
        "vocab_size": c["vocab_size"], "max_position_embeddings": c["max_position_embeddings"],
        "rope_theta": c["rope_theta"], "rms_norm_eps": c["rms_norm_eps"],
        "hidden_act": c["hidden_act"], "attention_bias": c.get("attention_bias", False),
        "sliding_window": c["sliding_window"], "layer_types": c["layer_types"],
        "tie_word_embeddings": False, "dtype": "bfloat16", "torch_dtype": "bfloat16",
        "use_cache": False,
    }
    json.dump(olmo, open(f"{base}/config.json", "w"), indent=2)
    d = f"{base}/model.safetensors"
    if os.path.exists(d):
        os.remove(d)
    os.link(f"{src}/model.safetensors", d)
    return base


def finalize_draft(out_llmc, src, out):
    """Surgery: llmc output (quantized MLP + bf16 attn/norm, model.* names, random
    embed/lm_head) -> deployable draft (bare names, dflash tensors restored)."""
    import torch
    from safetensors import safe_open
    from safetensors.torch import save_file

    os.makedirs(out, exist_ok=True)
    # 1) llmc output tensors -> rename model.* to bare, drop random embed/lm_head
    q = {}
    with safe_open(f"{out_llmc}/model.safetensors", framework="pt") as f:
        meta = f.metadata() or {"format": "pt"}
        for k in f.keys():
            nk = k[len("model."):] if k.startswith("model.") else k
            if nk.startswith("embed_tokens") or nk == "lm_head.weight":
                continue  # random (draft has none; uses target's)
            q[nk] = f.get_tensor(k)
    # 2) restore the dflash-specific tensors from the original draft (bare names)
    restored = 0
    with safe_open(f"{src}/model.safetensors", framework="pt") as f:
        for k in f.keys():
            if (k in ("fc.weight", "hidden_norm.weight", "mask_embed")
                    or k.endswith(".self_attn.sinks")):
                q[k] = f.get_tensor(k)
                restored += 1
    # 3) config = original dflash config + compressed-tensors quant cfg (MLP only)
    cfg = json.load(open(f"{src}/config.json"))
    cfg["quantization_config"] = {
        "quant_method": "compressed-tensors", "format": "pack-quantized",
        "config_groups": {"group_0": {"targets": ["Linear"], "weights": {
            "num_bits": 4, "type": "int", "symmetric": True, "strategy": "group",
            "group_size": 128, "actorder": None, "dynamic": False}}},
        "ignore": ["re:.*self_attn.*"],  # keep qkv/o bf16 (fused-KV stays on); quantize MLP
    }
    save_file(q, f"{out}/model.safetensors", metadata=meta)
    json.dump(cfg, open(f"{out}/config.json", "w"), indent=2)
    npacked = sum(1 for k in q if k.endswith(".weight_packed"))
    print(f"[finalize_draft] {out}: {len(q)} tensors, {npacked} packed-MLP, "
          f"restored {restored} dflash tensors (fc/hidden_norm/sinks/mask_embed)")


def main():
    import torch
    from transformers import AutoModelForCausalLM
    from llmcompressor import oneshot
    from llmcompressor.modifiers.quantization import QuantizationModifier

    import common
    print(f"[draft-quant] SRC={SRC}")
    build_base_olmo3(SRC, BASE)
    model = AutoModelForCausalLM.from_pretrained(BASE, dtype=torch.bfloat16, device_map="cuda:0")
    # data-free RTN: pop the stock-Olmo3 per-layer-RoPE ModuleDict, else llmc's
    # observe() recurses on its str keys -> RecursionError (quantize.py does the
    # same for data-free schemes).
    model.model._modules.pop("rotary_embs", None)
    # RTN W4A16, MLP-only: ignore lm_head + all attention projections (data-free).
    recipe = QuantizationModifier(targets="Linear", scheme="W4A16",
                                  ignore=["lm_head", "re:.*self_attn.*"])
    os.makedirs(OUT_LLMC, exist_ok=True)
    # processor: load the DeepSeek transplant tokenizer.json directly (the draft dir
    # has no tokenizer; base-draft has no processing class) so oneshot can init.
    oneshot(model=model, recipe=recipe, output_dir=OUT_LLMC,
            processor=common.load_fast_tokenizer())
    print("[draft-quant] RTN oneshot done")
    del model
    import gc; gc.collect(); torch.cuda.empty_cache()
    finalize_draft(OUT_LLMC, SRC, OUT)
    print(f"[draft-quant] DONE -> {OUT}")


if __name__ == "__main__":
    main()
