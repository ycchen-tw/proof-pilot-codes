#!/usr/bin/env python3
"""Precision ablation: quantized checkpoints vs the bf16 baseline.

Loads the bf16 base (stock Olmo3) as reference and each quantized checkpoint
(compressed-tensors auto-decompresses for forward), reports on held-out L4
sequences (seed != calibration):
  - PPL          : perplexity on the real next token (lower better)
  - top1_acc     : teacher-forced next-token accuracy
  - top1_agree   : fraction of positions whose argmax matches the bf16 model
  - KL           : mean KL(bf16 || quant) over positions (lower better)

Controlled for the attention sink: this script ALWAYS runs eager attention so
that --sink-on vs (default) sink-off is the only variable. With --sink-on, the
gpt-oss sink is patched in and per-head sinks loaded for BOTH reference and quant
(this measures the REAL serving regime; without it you only see the sink-less
world the old pipeline calibrated in). Run in the quant venv:
    CUDA_VISIBLE_DEVICES=0,1 .venv/bin/python ablation.py --sink-on --seqlen 8192
"""
import argparse
import json
import os

import torch
import torch.nn.functional as F

import common
import sink_patch

DEFAULT_SCHEMES = ["gptq-w4a16"]  # GPTQ-only deploy decision (override with --schemes)


def load(path, device, eager=True):
    from transformers import AutoModelForCausalLM
    kw = dict(dtype=torch.bfloat16, device_map=device)
    if eager:
        kw["attn_implementation"] = "eager"
    return AutoModelForCausalLM.from_pretrained(path, **kw).eval()


@torch.no_grad()
def logits_for(model, batches, device):
    outs = []
    for ids in batches:
        lg = model(ids.to(device)).logits[0].float().cpu()  # [L, V]
        outs.append(lg)
    return outs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=48)
    ap.add_argument("--seqlen", type=int, default=2048)
    ap.add_argument("--sink-on", action="store_true",
                    help="patch gpt-oss sink + load per-head sinks (serving regime)")
    ap.add_argument("--sink-src", default=common.SRC,
                    help="checkpoint to read self_attn.sinks from (default PP_QUANT_SRC)")
    ap.add_argument("--schemes", nargs="+", default=DEFAULT_SCHEMES)
    ap.add_argument("--tag", default=os.environ.get("PP_QUANT_MODEL_TAG", "stage1-v2-7b"))
    ap.add_argument("--ref-gpu", default="cuda:0")
    ap.add_argument("--quant-gpu", default="cuda:1")
    ap.add_argument("--out", default="ablation_results.json")
    args = ap.parse_args()

    common.build_base()
    ds = common.load_calib(num_samples=args.n, seqlen=args.seqlen, seed=999)
    batches = [torch.tensor([ds[i]["input_ids"]]) for i in range(len(ds))]
    targets = [b[0, 1:] for b in batches]  # next-token targets

    regime = f"sink-{'ON' if args.sink_on else 'off'} seqlen={args.seqlen} eager"
    print(f"[ablation] {args.n} seqs x {args.seqlen} tok, held-out seed=999 | {regime}")

    if args.sink_on:
        sink_patch.patch_eager()

    # reference: bf16 base
    ref_model = load(common.BASE, args.ref_gpu)
    if args.sink_on:
        sink_patch.load_sinks_into(ref_model, args.sink_src)
    ref_logits = logits_for(ref_model, batches, args.ref_gpu)
    ref_top1 = [lg[:-1].argmax(-1) for lg in ref_logits]
    ref_logp = [F.log_softmax(lg[:-1], dim=-1) for lg in ref_logits]

    def metrics(qlogits):
        n_tok = ce = agree = topok = kl = 0.0
        for qlg, rtop, rlp, tgt in zip(qlogits, ref_top1, ref_logp, targets):
            ql = qlg[:-1]
            qlp = F.log_softmax(ql, dim=-1)
            L = tgt.shape[0]
            n_tok += L
            ce += F.nll_loss(qlp, tgt, reduction="sum").item()
            qtop = ql.argmax(-1)
            agree += (qtop == rtop).sum().item()
            topok += (qtop == tgt).sum().item()
            p = rlp.exp()
            kl += (p * (rlp - qlp)).sum().item()
        return {
            "ppl": float(torch.tensor(ce / n_tok).exp()),
            "top1_acc": topok / n_tok,
            "top1_agree": agree / n_tok,
            "kl": kl / n_tok,
        }

    results = {"_regime": regime, "bf16-ref": metrics(ref_logits)}
    print("bf16-ref:", results["bf16-ref"])

    del ref_model
    torch.cuda.empty_cache()

    for s in args.schemes:
        path = f"{common.OUT_ROOT}/{args.tag}-{s}"
        if not os.path.exists(f"{path}/model.safetensors") and not os.path.exists(
                f"{path}/model.safetensors.index.json"):
            print(f"  skip {s} (missing {path})")
            continue
        try:
            qm = load(path, args.quant_gpu)
            if args.sink_on:
                sink_patch.load_sinks_into(qm, args.sink_src)
            ql = logits_for(qm, batches, args.quant_gpu)
            results[s] = metrics(ql)
            print(f"{s}: {results[s]}")
            del qm
            torch.cuda.empty_cache()
        except Exception as e:  # noqa: BLE001
            print(f"  FAIL {s}: {type(e).__name__}: {str(e)[:120]}")
            results[s] = {"error": str(e)[:200]}

    with open(args.out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"[ablation] wrote {args.out}")

    # pretty table
    print(f"\n{regime}")
    print(f"{'scheme':16s} {'ppl':>8s} {'top1_acc':>9s} {'top1_agree':>11s} {'KL':>9s}")
    for k, v in results.items():
        if k == "_regime" or not isinstance(v, dict):
            continue
        if "error" in v:
            print(f"{k:16s} {'ERR':>8s}")
        else:
            print(f"{k:16s} {v['ppl']:8.3f} {v['top1_acc']:9.4f} "
                  f"{v['top1_agree']:11.4f} {v['kl']:9.4f}")


if __name__ == "__main__":
    main()
