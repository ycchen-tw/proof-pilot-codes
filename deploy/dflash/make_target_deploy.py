#!/usr/bin/env python3
"""Build an sglang-servable deploy dir for the stage1-v2-7b olmo3_sink target.

Hardlinks the weights (original untouched) and rewrites config.json per the
stage-1 deploy recipe (docs/stage1_deploy_test.md): model_type=olmo3,
architectures=Olmo3SinkForCausalLM, dtype=bf16, use_cache=true, and the RoPE
key in *legacy* top-level form (rope_theta + rope_scaling) to dodge sglang's
custom Olmo3Config yarn-validation order bug (tf5 rebuilds rope_parameters from
the aliases afterwards, so olmo2_sink.py's config.rope_parameters still works).
"""
import json
import os
import shutil

SRC = "outputs/stage1-v2-7b"
DST = "outputs/stage1-v2-7b-deploy"


def main():
    os.makedirs(DST, exist_ok=True)
    with open(os.path.join(SRC, "config.json")) as f:
        cfg = json.load(f)

    rp = cfg.pop("rope_parameters")
    cfg.pop("auto_map", None)  # avoid trust_remote_code routing; use sglang olmo2 class
    cfg["model_type"] = "olmo3"
    cfg["architectures"] = ["Olmo3SinkForCausalLM"]
    cfg["dtype"] = "bfloat16"
    cfg["torch_dtype"] = "bfloat16"
    cfg["use_cache"] = True
    cfg["rope_theta"] = rp["rope_theta"]
    cfg["rope_scaling"] = {k: v for k, v in rp.items() if k != "rope_theta"}

    with open(os.path.join(DST, "config.json"), "w") as f:
        json.dump(cfg, f, indent=2)

    # Hardlink weights; copy the small tokenizer/aux files.
    for name in os.listdir(SRC):
        if name in ("config.json",) or name.startswith("_resume"):
            continue
        s, d = os.path.join(SRC, name), os.path.join(DST, name)
        if os.path.isdir(s):
            continue
        if os.path.exists(d):
            os.remove(d)
        if name.endswith(".safetensors"):
            os.link(s, d)
        else:
            shutil.copy2(s, d)
    print(f"wrote deploy dir {DST}")
    print(f"  rope_theta={cfg['rope_theta']} rope_scaling.rope_type={cfg['rope_scaling'].get('rope_type')}")
    print("  files:", sorted(os.listdir(DST)))


if __name__ == "__main__":
    main()
