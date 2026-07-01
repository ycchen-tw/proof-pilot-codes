"""Tool-calling tests (DeepSeek-V4 DSML format) against the SGLang server.

Requires the server launched with --tool-call-parser deepseekv4 (which switches
/v1/chat/completions to sglang's vendored encoding_dsv4.encode_messages — same
renderer as training) and --reasoning-parser deepseek-r1.

1. double-BOS guard: prompt_tokens must match local encode_messages render
2. raw /generate: model emits a well-formed <|DSML|>tool_calls block, eos stop
3. /v1/chat/completions + tools: parsed OpenAI tool_calls, valid JSON args
4. full tool loop: tool result -> final answer
5. chat mode (thinking off) tool call
6. two tools available -> picks the right one

Usage: uv run python training/stage1/sglang_deploy/_tool_test.py [--port 30000]
"""

import argparse
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "training" / "stage1" / "src"))
from encoding_dsv4 import encode_messages  # noqa: E402

CALC = {"type": "function", "function": {
    "name": "calculator",
    "description": "Evaluate an arithmetic expression and return the numeric result.",
    "parameters": {"type": "object", "properties": {
        "expression": {"type": "string", "description": "The arithmetic expression to evaluate, e.g. '2*(3+4)'."}},
        "required": ["expression"]}}}

PRIME = {"type": "function", "function": {
    "name": "is_prime",
    "description": "Check whether a given integer is a prime number.",
    "parameters": {"type": "object", "properties": {
        "n": {"type": "integer", "description": "The integer to test for primality."}},
        "required": ["n"]}}}


def post(url, payload, timeout=600):
    req = urllib.request.Request(
        url, json.dumps(payload).encode(), {"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def chat(base, messages, tools=None, thinking=True, **kw):
    body = {
        "model": "default", "messages": messages, "max_tokens": 4096,
        "temperature": 0.6, "separate_reasoning": True,
        "chat_template_kwargs": {"thinking": thinking},
    }
    if tools:
        body["tools"] = tools
    body.update(kw)
    return post(f"{base}/v1/chat/completions", body)


def t1_bos_guard(base, tok):
    print("=== 1. double-BOS guard ===")
    msgs = [{"role": "user", "content": "hi"}]
    out = chat(base, msgs, max_tokens=4)
    # local ground-truth render: empty system inserted by server + thinking mode
    gt = encode_messages(
        [{"role": "system", "content": ""}] + msgs, thinking_mode="thinking")
    n_gt = len(tok(gt, add_special_tokens=False)["input_ids"])
    n_srv = out["usage"]["prompt_tokens"]
    print(f"  server prompt_tokens={n_srv} local render={n_gt} -> "
          + ("MATCH" if n_srv == n_gt else "MISMATCH (double-BOS or render drift?)"))
    return n_srv == n_gt


def t2_raw_dsml(base, tok):
    print("=== 2. raw /generate DSML emission ===")
    msgs = [
        {"role": "system", "content": "", "tools": [CALC]},
        {"role": "user", "content":
         "Use the calculator tool to compute 137*89. Do not compute it yourself."},
    ]
    prompt = encode_messages(msgs, thinking_mode="thinking")
    out = post(f"{base}/generate", {
        "text": prompt,
        "sampling_params": {"max_new_tokens": 2048, "temperature": 0.0,
                            "skip_special_tokens": False},
    })
    txt = out["text"]
    fin = out["meta_info"]["finish_reason"]
    has_open = "<｜DSML｜tool_calls>" in txt
    has_invoke = '<｜DSML｜invoke name="calculator">' in txt
    has_param = "<｜DSML｜parameter" in txt
    has_close = "</｜DSML｜tool_calls>" in txt
    print(f"  finish={fin} | block_open={has_open} invoke={has_invoke} "
          f"param={has_param} block_close={has_close}")
    i = txt.find("<｜DSML｜tool_calls>")
    if i >= 0:
        print("  raw block:", repr(txt[i:i + 300]))
    return all([has_open, has_invoke, has_param, has_close])


def t3_openai_toolcall(base):
    print("=== 3. /v1/chat/completions tools -> parsed tool_calls ===")
    out = chat(base, [{"role": "user", "content":
        "Use the calculator tool to compute 137*89. Do not compute it yourself."}],
        tools=[CALC], temperature=0.0)
    ch = out["choices"][0]
    tcs = ch["message"].get("tool_calls") or []
    print(f"  finish_reason={ch['finish_reason']} n_tool_calls={len(tcs)}")
    ok = False
    args = None
    if tcs:
        f = tcs[0]["function"]
        try:
            args = json.loads(f["arguments"])
            ok = f["name"] == "calculator" and "expression" in args
        except json.JSONDecodeError:
            pass
        print(f"  call: {f['name']}({f['arguments']})")
    print("  reasoning chars:", len(ch["message"].get("reasoning_content") or ""))
    return ok, tcs


def t4_full_loop(base, tcs):
    print("=== 4. full tool loop (call -> result -> answer) ===")
    msgs = [
        {"role": "user", "content":
         "Use the calculator tool to compute 137*89. Do not compute it yourself."},
        {"role": "assistant", "content": "", "tool_calls": tcs},
        {"role": "tool", "tool_call_id": tcs[0]["id"], "content": "12193"},
    ]
    out = chat(base, msgs, tools=[CALC], temperature=0.0)
    ch = out["choices"][0]
    ct = ch["message"].get("content") or ""
    has_answer = "12193" in ct
    print(f"  finish={ch['finish_reason']} | answer uses tool result: {has_answer}")
    print(f"  content: {ct[:200]!r}")
    return has_answer


def t5_chat_mode(base):
    print("=== 5. chat mode (thinking off) tool call ===")
    out = chat(base, [{"role": "user", "content":
        "Use the calculator tool to compute 555+446. Do not compute it yourself."}],
        tools=[CALC], thinking=False, temperature=0.0)
    ch = out["choices"][0]
    tcs = ch["message"].get("tool_calls") or []
    rc = ch["message"].get("reasoning_content") or ""
    print(f"  finish={ch['finish_reason']} n_tool_calls={len(tcs)} reasoning_chars={len(rc)}")
    if tcs:
        print(f"  call: {tcs[0]['function']['name']}({tcs[0]['function']['arguments']})")
    return bool(tcs)


def t6_tool_choice(base):
    print("=== 6. two tools -> picks the right one ===")
    out = chat(base, [{"role": "user", "content":
        "Is 9973 a prime number? Use a tool to check."}],
        tools=[CALC, PRIME], temperature=0.0)
    ch = out["choices"][0]
    tcs = ch["message"].get("tool_calls") or []
    name = tcs[0]["function"]["name"] if tcs else None
    print(f"  finish={ch['finish_reason']} chose: {name} "
          f"args={tcs[0]['function']['arguments'] if tcs else None}")
    return name == "is_prime"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=30000)
    args = ap.parse_args()
    base = f"http://127.0.0.1:{args.port}"

    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(ROOT / "outputs" / "stage1-2node")

    results = {}
    results["bos_guard"] = t1_bos_guard(base, tok)
    results["raw_dsml"] = t2_raw_dsml(base, tok)
    ok3, tcs = t3_openai_toolcall(base)
    results["openai_parse"] = ok3
    results["full_loop"] = t4_full_loop(base, tcs) if tcs else False
    results["chat_mode"] = t5_chat_mode(base)
    results["tool_choice"] = t6_tool_choice(base)

    print("\n=== summary ===")
    for k, v in results.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")


if __name__ == "__main__":
    main()
