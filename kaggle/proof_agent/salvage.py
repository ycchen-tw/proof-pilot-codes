"""Force-close-think salvage: recover a proof from a chain-of-thought that hit the token cap.

When a prove/refine call runs out of tokens still inside <think> (finish=length, empty content),
rebuild the exact prefix input_ids = chat_template([system,user], add_generation_prompt=True)
(ends in <think>) + encode(reasoning + "</think>\n\n"), then continue generation via the native
/generate endpoint so the model emits a final <solution> from its (incomplete) reasoning.

Ported from evaluation_local/harness/force_close_think.py (token-space, no double-BOS).
"""
from __future__ import annotations


def _normalize(prefix):
    if hasattr(prefix, "keys"):                       # tf5 may return a BatchEncoding
        prefix = prefix["input_ids"]
    if prefix and isinstance(prefix[0], list):        # nested (batch of 1)
        prefix = prefix[0]
    return list(prefix)


async def force_close_think(client, messages: list[dict], reasoning_content: str, *,
                            max_new_tokens: int, temperature: float | None = None,
                            top_p: float | None = None, timeout: float | None = None,
                            seed: int | None = None) -> dict:
    """Returns the raw /generate output dict: {"text": ..., "meta_info": {...}}."""
    sys_user = [m for m in messages if m.get("role") in ("system", "user")]
    prefix = client.tok.apply_chat_template(sys_user, add_generation_prompt=True,
                                            tokenize=True, return_dict=False)
    prefix = _normalize(prefix)
    # STEER into the solution: close </think> AND open <solution> so the model writes the proof
    # body immediately. Just "</think>" lets a model that hasn't converged (hard problems) keep
    # reasoning in the answer space and never emit the tag. The caller re-attaches "<solution>".
    cont = client.tok.encode((reasoning_content or "") + "</think>\n\n<solution>\n",
                             add_special_tokens=False)
    return await client.generate_raw(prefix + cont, max_new_tokens=max_new_tokens,
                                     temperature=temperature, top_p=top_p, timeout=timeout, seed=seed)
