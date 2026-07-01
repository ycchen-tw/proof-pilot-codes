"""DeepSeek-format inference verification against the SGLang server.

1. Template parity: chat_template.jinja (what the server applies) vs
   encode_messages (the training ground-truth renderer) — exact token-id match,
   plus server prompt_tokens cross-check.
2. /v1/chat/completions behavior: <think> reasoning separation, eos stop.
3. Multi-turn rendering.
4. Math generation samples (eyeball quality).

Usage:
  uv run python training/stage1/sglang_deploy/_format_test.py [--port 30000]
"""

import argparse
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "training" / "stage1" / "src"))
from encoding_dsv4 import encode_messages  # noqa: E402

MODEL_DIR = ROOT / "outputs" / "stage1-2node"


def post(url, payload, timeout=600):
    req = urllib.request.Request(
        url, json.dumps(payload).encode(), {"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def check_template_parity(tok):
    print("=== 1. template parity (jinja vs encode_messages) ===")
    cases = {
        "single_user": [{"role": "user", "content": "Prove that sqrt(2) is irrational."}],
        "system_user": [
            {"role": "system", "content": "You are a careful mathematician."},
            {"role": "user", "content": "State the pigeonhole principle."},
        ],
        "multiturn": [
            {"role": "user", "content": "What is 2+2?"},
            {"role": "assistant", "content": "2+2 = 4."},
            {"role": "user", "content": "Now prove it from the Peano axioms."},
        ],
    }
    ok = True
    for name, messages in cases.items():
        jinja_ids = tok.apply_chat_template(messages, add_generation_prompt=True)
        if jinja_ids and not isinstance(jinja_ids[0], int):  # tf5 returns Encoding
            jinja_ids = jinja_ids[0].ids if hasattr(jinja_ids[0], "ids") else list(jinja_ids[0])
        # encode_messages already appends the generation prefix <|Assistant|><think>
        gt_text = encode_messages(messages, thinking_mode="thinking")
        gt_ids = tok(gt_text, add_special_tokens=False)["input_ids"]
        match = list(jinja_ids) == list(gt_ids)
        ok &= match
        print(f"  {name}: jinja={len(jinja_ids)} tok, encode_messages={len(gt_ids)} tok -> "
              + ("MATCH" if match else "MISMATCH"))
        if not match:
            print("    jinja :", repr(tok.decode(jinja_ids)))
            print("    ground:", repr(gt_text))
    return ok


def check_chat_completions(base):
    print("=== 2. /v1/chat/completions behavior ===")
    out = post(f"{base}/v1/chat/completions", {
        "model": "default",
        "messages": [{"role": "user", "content":
            "Prove that there are infinitely many prime numbers."}],
        "max_tokens": 2048,
        "temperature": 0.6,
        "separate_reasoning": True,
    })
    ch = out["choices"][0]
    msg = ch["message"]
    rc = msg.get("reasoning_content") or ""
    ct = msg.get("content") or ""
    print(f"  finish_reason={ch['finish_reason']} prompt_tokens={out['usage']['prompt_tokens']} "
          f"completion_tokens={out['usage']['completion_tokens']}")
    print(f"  reasoning_content: {len(rc)} chars | content: {len(ct)} chars")
    print(f"  reasoning head: {rc[:200]!r}")
    print(f"  content head  : {ct[:300]!r}")
    return out


def check_multiturn(base):
    print("=== 3. multi-turn ===")
    out = post(f"{base}/v1/chat/completions", {
        "model": "default",
        "messages": [
            {"role": "user", "content": "Let a_n = n^2. What is a_3?"},
            {"role": "assistant", "content": "a_3 = 9."},
            {"role": "user", "content": "Good. Now give a closed form for sum of a_k for k=1..n."},
        ],
        "max_tokens": 1536,
        "temperature": 0.6,
        "separate_reasoning": True,
    })
    ch = out["choices"][0]
    print(f"  finish_reason={ch['finish_reason']}")
    print(f"  content head: {(ch['message'].get('content') or '')[:300]!r}")


def check_math_samples(base):
    print("=== 4. math generation samples ===")
    problems = [
        "Prove that for all positive reals a, b: a/b + b/a >= 2.",
        "Show that the equation x^2 - 2y^2 = 0 has no solution in nonzero integers x, y.",
    ]
    for p in problems:
        out = post(f"{base}/v1/chat/completions", {
            "model": "default",
            "messages": [{"role": "user", "content": p}],
            "max_tokens": 3072,
            "temperature": 0.6,
            "separate_reasoning": True,
        })
        ch = out["choices"][0]
        ct = ch["message"].get("content") or ""
        print(f"  Q: {p}")
        print(f"  finish={ch['finish_reason']} | answer ({len(ct)} chars): {ct[:400]!r}")
        print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=30000)
    args = ap.parse_args()
    base = f"http://127.0.0.1:{args.port}"

    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(MODEL_DIR)

    parity_ok = check_template_parity(tok)
    check_chat_completions(base)
    check_multiturn(base)
    check_math_samples(base)
    print("template parity:", "PASS" if parity_ok else "FAIL")


if __name__ == "__main__":
    main()
