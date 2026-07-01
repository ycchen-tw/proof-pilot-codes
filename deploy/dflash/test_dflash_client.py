#!/usr/bin/env python3
"""Validate the DFlash-served target: generate on a few math prompts and report
output + speculative acceptance length (meta_info). Compares text against the
Phase-0 oracle expectation (should be coherent; greedy output)."""
import argparse
import json
import time
import urllib.request

PROMPTS = [
    "Compute 17 * 23 and show your reasoning step by step.",
    "Prove that the sum of the first n positive odd numbers equals n^2.",
    "Let f(x) = x^2 - 4x + 3. Find all real roots and explain.",
]


def gen(port, text, max_new=200, temp=0.0):
    body = json.dumps({
        "text": text,
        "sampling_params": {"temperature": temp, "max_new_tokens": max_new},
    }).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/generate", data=body,
        headers={"Content-Type": "application/json"},
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=600) as r:
        out = json.load(r)
    dt = time.time() - t0
    return out, dt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=30010)
    ap.add_argument("--max-new-tokens", type=int, default=200)
    ap.add_argument("--temp", type=float, default=0.0)
    args = ap.parse_args()
    for i, p in enumerate(PROMPTS):
        # chat format for the deepseek-style template
        prompt = f"<｜begin▁of▁sentence｜><｜User｜>{p}<｜Assistant｜>"
        out, dt = gen(args.port, prompt, args.max_new_tokens, args.temp)
        meta = out.get("meta_info", {})
        ctoks = meta.get("completion_tokens", 0)
        accept = meta.get("spec_accept_length") or meta.get("spec_verify_ct")
        print(f"\n=== prompt {i}: {p[:50]!r} ===")
        print(f"  completion_tokens={ctoks}, time={dt:.2f}s ({ctoks/dt:.1f} tok/s), "
              f"spec_accept_length={accept}")
        print("  text: " + repr(out.get("text", "")[:300]))


if __name__ == "__main__":
    main()
