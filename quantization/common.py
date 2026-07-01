"""Shared helpers for quantizing the stage1-v2-7b olmo3_sink checkpoint.

Quantization runs in an isolated venv (torch 2.11 / transformers 4.57.6 /
llmcompressor 0.11). The olmo3_sink modeling code targets transformers 5.9 and
will NOT import here, so we load the checkpoint as a *stock* transformers Olmo3
model (per-layer RoPE is correct in 4.57; the tf5 RoPE regression does not apply).

The attention sink (`self_attn.sinks`, 32 fp scalars/layer) is orthogonal to
weight quantization: it is an extra softmax-logit column, not a Linear weight.
So we quantize without it (a small, second-order effect on calibration stats)
and `finalize()` merges the original sink tensors back into every quantized
checkpoint. At serve time sglang's `deploy/target/olmo2_sink.py` re-applies them.
"""
import json
import os
import shutil

import numpy as np

# All paths are env-overridable so the same pipeline runs on the HPC cluster
# (defaults below) and on the Vast/Kaggle sm120 box (export PP_* overrides).
ROOT = os.environ.get("PP_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.environ.get("PP_QUANT_SRC", f"{ROOT}/outputs/stage1-v2-7b")  # original bf16 ckpt (may be sharded)
BASE = os.environ.get("PP_QUANT_BASE", f"{ROOT}/quantization/base")   # tf4.57-loadable view of SRC
OUT_ROOT = os.environ.get("PP_QUANT_OUT", f"{ROOT}/quantization/out") # quantized checkpoints land here
L4_DIR = f"{ROOT}/data/l4-g2r05-ml12288-mc65536"           # pre-tokenized calibration source (cluster)
# Fallback calibration when the L4 bins aren't present (e.g. the sm120 box): a
# parquet of in-distribution problem text, tokenized on the fly. See load_calib().
CALIB_PARQUET = os.environ.get("PP_CALIB_PARQUET", "")

MICRO_LEN = 65536  # row stride of input_ids.i32


def _legacy_rope(rp: dict) -> tuple[float, dict]:
    """Split tf5 rope_parameters into legacy (rope_theta, rope_scaling)."""
    rope_theta = rp["rope_theta"]
    rope_scaling = {k: v for k, v in rp.items() if k != "rope_theta"}
    return rope_theta, rope_scaling


def build_base() -> str:
    """Materialize a stock-Olmo3-loadable view of SRC (hardlinked weights).

    Rewrites config: model_type=olmo3, drop auto_map (no trust_remote_code),
    rope in legacy top-level form, dtype bf16. The 32 `...self_attn.sinks`
    tensors stay in the weights file; stock Olmo3 ignores them on load.
    """
    os.makedirs(BASE, exist_ok=True)
    # idempotent: once built, leave it alone so concurrent quant runs don't race
    # on the hardlinked weights file. SRC may be single-file or sharded.
    if os.path.exists(f"{BASE}/config.json") and (
        os.path.exists(f"{BASE}/model.safetensors")
        or os.path.exists(f"{BASE}/model.safetensors.index.json")
    ):
        return BASE
    with open(f"{SRC}/config.json") as f:
        cfg = json.load(f)

    # rope: the cluster checkpoint stores tf5 `rope_parameters`; the deployed
    # checkpoint is already in legacy `rope_theta`/`rope_scaling` form. Handle both.
    rp = cfg.pop("rope_parameters", None)
    if rp is not None:
        cfg["rope_theta"], cfg["rope_scaling"] = _legacy_rope(rp)
    cfg.pop("auto_map", None)
    cfg["model_type"] = "olmo3"
    cfg["architectures"] = ["Olmo3ForCausalLM"]
    cfg["dtype"] = "bfloat16"
    cfg["torch_dtype"] = "bfloat16"
    cfg["use_cache"] = False
    # drop sink / custom keys: stock Olmo3Config keeps them as unused kwargs
    # (harmless), but they're irrelevant to weight quantization. layer_types /
    # sliding_window stay (stock Olmo3 honours its hybrid-SWA pattern).
    for k in ("sink_init_value", "reuse_packing_metadata",
              "is_hybrid_swa", "hybrid_layer_pattern"):
        cfg.pop(k, None)

    with open(f"{BASE}/config.json", "w") as f:
        json.dump(cfg, f, indent=2)

    for name in os.listdir(SRC):
        if name in ("config.json", "config.json.orig") or name.startswith("_resume"):
            continue
        s, d = f"{SRC}/{name}", f"{BASE}/{name}"
        if os.path.isdir(s):
            continue
        if os.path.exists(d):
            os.remove(d)
        if name.endswith(".safetensors"):
            os.link(s, d)
        else:
            shutil.copy2(s, d)
    return BASE


def patch_llmcompressor():
    """Fix llmcompressor's observe()/update_qparams() for models with a
    per-layer-RoPE `rotary_embs` ModuleDict (stock Olmo3 in tf4.57).

    Both functions do `if isinstance(module, Iterable): for m in module: recurse`.
    For an nn.ModuleDict, iteration yields *string keys*; a length-1 string is
    iterable and yields itself -> infinite recursion (RecursionError). This hits
    the AWQ and data-free calibration paths (GPTQ uses a different weight update).

    Fix: flatten the module tree correctly (ModuleDict -> values, skip str/bytes)
    into leaf modules, then delegate each leaf to the *original* function (whose
    non-iterable branch then runs the real per-module logic).
    """
    from collections.abc import Iterable

    import torch.nn as nn
    from llmcompressor.modifiers.quantization import calibration as _cal
    from llmcompressor.modifiers.quantization.quantization import base as _base

    if getattr(_cal, "_pp_patched", False):
        return
    orig_observe = _cal.observe
    orig_update = _cal.update_qparams

    def flatten(module):
        if isinstance(module, nn.ModuleDict):
            for m in module.values():
                yield from flatten(m)
        elif isinstance(module, (str, bytes)):
            return
        elif isinstance(module, Iterable):
            for m in module:
                yield from flatten(m)
        else:
            yield module

    def observe(module, base_name):
        for m in flatten(module):
            orig_observe(m, base_name)  # leaf -> non-iterable branch

    def update_qparams(module, base_name, only_update_onload=False):
        names = [base_name] if isinstance(base_name, str) else list(base_name)
        for m in flatten(module):
            for b in names:
                orig_update(m, b, only_update_onload=only_update_onload)

    for mod in (_cal, _base):
        if hasattr(mod, "observe"):
            mod.observe = observe
        if hasattr(mod, "update_qparams"):
            mod.update_qparams = update_qparams
    _cal._pp_patched = True
    print("[patch] llmcompressor observe/update_qparams patched for ModuleDict")


def load_fast_tokenizer():
    """Load the transplant tokenizer as a plain fast tokenizer.

    The checkpoint's tokenizer_config declares tf5's `TokenizersBackend` class,
    which doesn't exist under tf4.57; load tokenizer.json directly instead.
    llmcompressor only needs this as a `processor` for pipeline init -- the
    calibration dataset is already tokenized.
    """
    from transformers import PreTrainedTokenizerFast

    return PreTrainedTokenizerFast(
        tokenizer_file=f"{SRC}/tokenizer.json",
        bos_token="<｜begin▁of▁sentence｜>",
        eos_token="<｜end▁of▁sentence｜>",
        pad_token="<｜▁pad▁｜>",
    )


def _load_calib_parquet(parquet: str, num_samples: int, seqlen: int, seed: int):
    """Calibration fallback: tokenize in-distribution problem text into fixed-length
    sequences. Used when the pre-packed L4 bins are unavailable (sm120 box).

    Concatenates the `problem` column (BOS-separated), tokenizes with the model's
    own fast tokenizer, then slices into `num_samples` windows of `seqlen` tokens.
    Same domain/vocab as training; calibration only needs representative activations.
    """
    import pandas as pd
    from datasets import Dataset

    df = pd.read_parquet(parquet)
    col = "problem" if "problem" in df.columns else df.columns[0]
    rng = np.random.default_rng(seed)
    order = rng.permutation(len(df))

    tok = load_fast_tokenizer()
    bos = tok.bos_token or ""
    ids: list[int] = []
    need = num_samples * seqlen
    for i in order:
        text = str(df[col].iloc[int(i)])
        ids.extend(tok(bos + text).input_ids)
        if len(ids) >= need:
            break
    if len(ids) < need:
        raise RuntimeError(
            f"calib parquet only yielded {len(ids)} tokens, need {need} "
            f"({num_samples}x{seqlen}); lower --num-calib/--seqlen or add data")

    rows = [{"input_ids": ids[k * seqlen:(k + 1) * seqlen]} for k in range(num_samples)]
    print(f"[calib] parquet {os.path.basename(parquet)}: {num_samples}x{seqlen} "
          f"tokens from {col!r}")
    return Dataset.from_list(rows)


def load_calib(num_samples: int = 512, seqlen: int = 2048, seed: int = 0):
    """Build a tokenized calibration dataset from the L4 pre-packed bins.

    Returns a `datasets.Dataset` with an `input_ids` column. Tokens are already
    in this model's (DeepSeek-transplant) vocab and match the training mix.

    When the L4 bins aren't present (e.g. the sm120 box) and PP_CALIB_PARQUET
    points at a problems parquet, fall back to tokenizing in-distribution problem
    text on the fly (same domain, just not the exact training packing).
    """
    from datasets import Dataset

    path = f"{L4_DIR}/input_ids.i32"
    if not os.path.exists(path) and CALIB_PARQUET:
        return _load_calib_parquet(CALIB_PARQUET, num_samples, seqlen, seed)
    total_tokens = os.path.getsize(path) // 4
    n_bins = total_tokens // MICRO_LEN
    arr = np.memmap(path, dtype=np.int32, mode="r", shape=(n_bins, MICRO_LEN))

    rng = np.random.default_rng(seed)
    bin_idx = rng.choice(n_bins, size=num_samples, replace=False)
    # take a random in-bin offset so we don't always start at a doc boundary
    rows = []
    for b in bin_idx:
        # seqlen may equal/exceed MICRO_LEN (long-ctx calib): integers(0, 0) raises,
        # so clamp to offset 0 and take the whole row (truncated to seqlen below).
        off = 0 if seqlen >= MICRO_LEN else int(rng.integers(0, MICRO_LEN - seqlen))
        ids = np.asarray(arr[b, off:off + seqlen], dtype=np.int64)
        rows.append({"input_ids": ids.tolist()})
    return Dataset.from_list(rows)


def _read_all_tensors(model_dir: str):
    """Load every tensor from a (possibly sharded) safetensors checkpoint.

    Returns (tensors: dict[str, Tensor], metadata: dict). Reads on CPU.
    """
    from safetensors import safe_open

    index = f"{model_dir}/model.safetensors.index.json"
    files = []
    if os.path.exists(index):
        with open(index) as f:
            weight_map = json.load(f)["weight_map"]
        files = sorted(set(weight_map.values()))
    else:
        files = ["model.safetensors"]

    tensors, metadata = {}, {}
    for fn in files:
        with safe_open(f"{model_dir}/{fn}", framework="pt") as f:
            md = f.metadata()
            if md:
                metadata.update(md)
            for k in f.keys():
                tensors[k] = f.get_tensor(k)
    return tensors, metadata


def finalize(out_dir: str):
    """Post-process an llmcompressor-saved checkpoint into a deployable one.

    1. Merge the 32 original sink tensors back into the weights.
    2. Re-emit a single model.safetensors (drops any index/shards).
    3. Patch config.json: re-add sink_init_value, set architectures to
       Olmo3SinkForCausalLM and rope legacy keys, use_cache=true.
    """
    import torch
    from safetensors import safe_open
    from safetensors.torch import save_file

    tensors, metadata = _read_all_tensors(out_dir)

    # pull sinks from the original checkpoint (single-file or sharded)
    index = f"{SRC}/model.safetensors.index.json"
    if os.path.exists(index):
        with open(index) as f:
            src_files = sorted(set(json.load(f)["weight_map"].values()))
    else:
        src_files = ["model.safetensors"]
    n_sinks = 0
    for fn in src_files:
        with safe_open(f"{SRC}/{fn}", framework="pt") as f:
            for k in f.keys():
                if k.endswith(".self_attn.sinks"):
                    tensors[k] = f.get_tensor(k).to(torch.bfloat16)
                    n_sinks += 1
    n_layers = json.load(open(f"{SRC}/config.json")).get("num_hidden_layers", n_sinks)
    assert n_sinks == n_layers, f"expected {n_layers} sinks (1/layer), merged {n_sinks}"

    # drop any prior sharding artifacts, write one file
    for fn in os.listdir(out_dir):
        if fn.endswith(".safetensors") or fn == "model.safetensors.index.json":
            os.remove(f"{out_dir}/{fn}")
    if not metadata:
        metadata = {"format": "pt"}
    save_file(tensors, f"{out_dir}/model.safetensors", metadata=metadata)

    # patch config for sglang olmo2_sink serving. Start from the ORIGINAL serving
    # config (it already carries sink / hybrid-SWA / rope correctly) and graft in
    # only the quantization_config that llmcompressor wrote, so we don't lose any
    # serving keys that build_base() stripped for the tf4.57 load.
    with open(f"{out_dir}/config.json") as f:
        qcfg = json.load(f)
    with open(f"{SRC}/config.json") as f:
        cfg = json.load(f)
    if "quantization_config" in qcfg:
        cfg["quantization_config"] = qcfg["quantization_config"]
    # rope: convert tf5 rope_parameters -> legacy if present (cluster ckpt);
    # the deployed ckpt is already legacy and untouched.
    if "rope_parameters" in cfg:
        cfg["rope_theta"], cfg["rope_scaling"] = _legacy_rope(cfg.pop("rope_parameters"))
    cfg["model_type"] = "olmo3"
    cfg["architectures"] = ["Olmo3SinkForCausalLM"]
    cfg.setdefault("sink_init_value", 0.0)
    cfg["use_cache"] = True
    cfg["dtype"] = "bfloat16"
    cfg["torch_dtype"] = "bfloat16"
    with open(f"{out_dir}/config.json", "w") as f:
        json.dump(cfg, f, indent=2)

    # copy tokenizer / aux files verbatim (the tf5 TokenizersBackend class can't
    # be re-saved under tf4.57; sglang's image loads these raw files fine)
    for name in ("tokenizer.json", "tokenizer_config.json", "chat_template.jinja",
                 "special_tokens_map.json", "generation_config.json"):
        s = f"{SRC}/{name}"
        if os.path.exists(s):
            shutil.copy2(s, f"{out_dir}/{name}")

    print(f"[finalize] {out_dir}: merged {n_sinks} sinks, "
          f"{len(tensors)} tensors, quant_method="
          f"{cfg.get('quantization_config', {}).get('quant_method')}")
