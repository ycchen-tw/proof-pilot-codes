"""Sink-aware eager attention for sink-on calibration / ablation.

The quant pipeline loads olmo3_sink checkpoints as *stock* transformers Olmo3
(tf4.57), whose eager attention has NO attention sink -> every calibration and
ablation forward is sink-less. The trained sinks are large (per-head logit mean
~+6.7, max ~+13.8, same magnitude as the largest real key logit), so sink-less
forwards are a *first-order* error on o_proj / down_proj, not second-order.

This module:
  1. patches stock Olmo3's module-level `eager_attention_forward` to the gpt-oss
     sink variant (math verbatim from olmo3_sink/modeling_olmo3_sink.py:85-100,
     masking matched to stock modeling_olmo3.py:88-101), and
  2. loads the per-head `self_attn.sinks` from a source checkpoint as buffers.

Olmo3 attention dispatches to the module-level `eager_attention_forward` ONLY when
config._attn_implementation == "eager" (modeling_olmo3.py:199-201). llmcompressor's
sequential pipeline forces eager and bakes the eager fn into the FX subgraph at
trace time -> call patch_eager() BEFORE oneshot/trace. For offline ablation, load
the model with attn_implementation="eager".
"""
import torch
import torch.nn as nn
from transformers.models.olmo3 import modeling_olmo3 as _m

_orig_eager = None


def _eager_attention_forward_with_sink(module, query, key, value, attention_mask,
                                       scaling, dropout=0.0, **kwargs):
    key_states = _m.repeat_kv(key, module.num_key_value_groups)
    value_states = _m.repeat_kv(value, module.num_key_value_groups)

    attn_weights = torch.matmul(query, key_states.transpose(2, 3)) * scaling
    if attention_mask is not None:
        causal_mask = attention_mask[:, :, :, : key_states.shape[-2]]
        attn_weights = attn_weights + causal_mask

    # gpt-oss sink: append per-head sink as an extra softmax logit, drop after
    # normalization. fp32 + max-subtract for stability (matches the FA3 sink).
    sink = module.sinks  # [Hq]
    sinks = sink.reshape(1, -1, 1, 1).expand(query.shape[0], -1, query.shape[-2], 1)
    combined = torch.cat([attn_weights, sinks.to(attn_weights.dtype)], dim=-1).float()
    combined = combined - combined.amax(dim=-1, keepdim=True)
    probs = torch.softmax(combined, dim=-1)[..., :-1].to(query.dtype)  # drop sink col
    probs = nn.functional.dropout(probs, p=dropout, training=module.training)

    attn_output = torch.matmul(probs, value_states).transpose(1, 2).contiguous()
    return attn_output, probs


def patch_eager():
    """Monkeypatch stock Olmo3 eager attention -> sink-aware. Idempotent."""
    global _orig_eager
    if getattr(_m, "_pp_sink_patched", False):
        return
    _orig_eager = _m.eager_attention_forward
    _m.eager_attention_forward = _eager_attention_forward_with_sink
    _m._pp_sink_patched = True
    print("[sink_patch] eager_attention_forward -> sink-aware (gpt-oss)")


def unpatch_eager():
    global _orig_eager
    if _orig_eager is not None:
        _m.eager_attention_forward = _orig_eager
        _m._pp_sink_patched = False
        _orig_eager = None


@torch.no_grad()
def load_sinks_into(model, src):
    """Load per-head `model.layers.{i}.self_attn.sinks` from `src` checkpoint into
    each layer as a non-persistent buffer, so patched eager can read module.sinks.
    `src` may be single-file or sharded (uses common._read_all_tensors)."""
    import common
    tensors, _ = common._read_all_tensors(src)
    layers = model.model.layers
    n = 0
    for li, layer in enumerate(layers):
        key = f"model.layers.{li}.self_attn.sinks"
        if key not in tensors:
            raise KeyError(f"{key} not found in {src}")
        # robust device probe: compressed-tensors quant Linears have no `.weight`
        # (only weight_packed), so go through whatever parameter exists.
        dev = next(layer.self_attn.parameters()).device
        layer.self_attn.register_buffer(
            "sinks", tensors[key].to(torch.float32).to(dev), persistent=False)
        n += 1
    assert n == model.config.num_hidden_layers, (
        f"loaded {n} sinks but model has {model.config.num_hidden_layers} layers")
    print(f"[sink_patch] loaded {n} per-head sinks from {src}")
    return n
