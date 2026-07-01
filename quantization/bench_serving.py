#!/usr/bin/env python3
"""Real-workload benchmark for a served sglang model (the proof-agent workload).

Uses REAL olympiad problems from problems.parquet, the proper chat template, and
NATURAL generation (no ignore_eos) so dflash accept-length reflects true draft
prediction on real reasoning content. Context sweep concatenates real math text
(not repeated filler) to reach target KV lengths.

Usage: python full_bench.py <port> <label>
"""
import sys, time, json, urllib.request, threading
import pandas as pd
from transformers import PreTrainedTokenizerFast

PORT = int(sys.argv[1]); LABEL = sys.argv[2]
ROOT = f"http://127.0.0.1:{PORT}"
TOKJSON = "/workspace/models/proof-pilot-deploy-bundle/soft-distill-7b-deploy/tokenizer.json"
tok = PreTrainedTokenizerFast(tokenizer_file=TOKJSON)

df = pd.read_parquet("/workspace/proof-pilot/distill_gen/problems/problems.parquet")
# fixed, reproducible spread of real problems of moderate prompt length
cand = [p for p in df["problem"].tolist() if 200 < len(p) < 1200]
PROBS = cand[:16]
MAXTOK = 1024  # cap on natural generation (most proofs finish earlier)


def chat_stream(prompt, max_tokens):
    """Natural chat generation, streamed. Return (ttft, decode_tps, comp_tokens, text)."""
    body = json.dumps({"model": "default", "stream": True,
                       "stream_options": {"include_usage": True},
                       "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": max_tokens, "temperature": 0.0}).encode()
    req = urllib.request.Request(ROOT + "/v1/chat/completions", body,
                                 {"Content-Type": "application/json"})
    t0 = time.time(); first = None; nchunk = 0; comp = 0; chunks = []
    with urllib.request.urlopen(req, timeout=2400) as r:
        for raw in r:
            line = raw.decode().strip()
            if not line.startswith("data:"):
                continue
            d = line[5:].strip()
            if d == "[DONE]":
                break
            obj = json.loads(d)
            u = obj.get("usage")
            if u:
                comp = u.get("completion_tokens", comp)
            ch = obj.get("choices") or []
            if ch:
                delta = ch[0].get("delta", {})
                piece = (delta.get("content") or "") + (delta.get("reasoning_content") or "")
                if piece:
                    if first is None:
                        first = time.time()
                    nchunk += 1; chunks.append(piece)
    end = time.time()
    if comp == 0:
        comp = nchunk
    ttft = (first - t0) if first else (end - t0)
    dec = (end - first) if first else 0
    dtps = (comp - 1) / dec if dec > 0 and comp > 1 else 0.0
    return ttft, dtps, comp, "".join(chunks)


def correctness():
    checks = [("Compute 17*23. Give only the number in \\boxed{}.", "391"),
              ("Factor x^2-4x+3 completely.", "(x-1)(x-3)"),
              ("Sum of the first 5 odd numbers? Give only the number.", "25")]
    passed = 0
    for q, want in checks:
        _, _, _, text = chat_stream(q, 600)
        t = text.replace(" ", "")
        if want.replace(" ", "") in t or (want == "(x-1)(x-3)" and "(x-3)(x-1)" in t):
            passed += 1
    print(f"RESULT correct {LABEL} pass={passed}/3", flush=True)


def single_real():
    """Single-stream on real problems: decode tok/s + natural length + coherence."""
    tps = []; comps = []; degen = 0
    for i in range(6):
        _, dtps, comp, text = chat_stream(PROBS[i], MAXTOK)
        tps.append(dtps); comps.append(comp)
        # crude degeneration check: long output dominated by a repeated short n-gram
        words = text.split()
        if len(words) > 60 and len(set(words[-40:])) < 8:
            degen += 1
    print(f"RESULT single {LABEL} mean_decode_tps={sum(tps)/len(tps):.1f} "
          f"mean_comp={sum(comps)//len(comps)} degen={degen}/6", flush=True)


def conc_sweep():
    for N in [1, 2, 4, 8, 16]:
        res = [None] * N
        def work(i):
            res[i] = chat_stream(PROBS[i % len(PROBS)], MAXTOK)
        ths = [threading.Thread(target=work, args=(i,)) for i in range(N)]
        t0 = time.time()
        for t in ths: t.start()
        for t in ths: t.join()
        wall = time.time() - t0
        comp = sum(r[2] for r in res)
        print(f"RESULT conc {LABEL} N={N} agg_tps={comp/wall:.1f} "
              f"per_req_tps={sum(r[1] for r in res)/N:.1f} tot_tok={comp} wall={wall:.2f}", flush=True)


def ctx_sweep():
    # real math text: concatenate distinct real problems until the target length
    pool_ids = tok("\n\n".join(df["problem"].tolist()[:6000])).input_ids
    for target in [2000, 8000, 16000, 30000]:
        prompt = tok.decode(pool_ids[:target]) + "\n\nBased on the problems above, state one general proof technique and apply it."
        try:
            ttft, dtps, comp, _ = chat_stream(prompt, 256)
            ptok = len(tok(prompt).input_ids)
            print(f"RESULT ctx {LABEL} ctx={target} prompt_tok={ptok} ttft={ttft:.2f} "
                  f"decode_tps={dtps:.1f} comp={comp}", flush=True)
        except Exception as e:
            print(f"RESULT ctx {LABEL} ctx={target} ERROR={str(e)[:60]}", flush=True)


if __name__ == "__main__":
    chat_stream("hi", 8)
    correctness()
    single_real()
    conc_sweep()
    ctx_sweep()
    print(f"DONE {LABEL}", flush=True)
