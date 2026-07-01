"""Enable sglang hybrid-SWA memory for an olmo3_sink model's config.json (no sglang patch needed).

Mechanism (see the sm120 deploy notes): sglang `get_hybrid_layer_ids` has a generic fallback — when a
model config carries both `is_hybrid_swa: true` and `hybrid_layer_pattern` (a list, 1=sliding/SWA,
0=full), it takes the generic path, capping the KV of sliding layers to sliding_window size and
greatly increasing concurrency capacity. This script derives `hybrid_layer_pattern` from the config's
existing `layer_types` and writes it back (idempotent, makes a backup).

Usage: python enable_swa_config.py <model_dir>
"""
import json
import os
import shutil
import sys


def main(model_dir: str) -> None:
    cfg_path = os.path.join(model_dir, "config.json")
    cfg = json.load(open(cfg_path))
    layer_types = cfg.get("layer_types")
    if not layer_types:
        raise SystemExit("config has no layer_types; cannot derive hybrid_layer_pattern")
    pattern = [1 if x == "sliding_attention" else 0 for x in layer_types]
    if not os.path.exists(cfg_path + ".orig"):
        shutil.copy(cfg_path, cfg_path + ".orig")
    cfg["is_hybrid_swa"] = True
    cfg["hybrid_layer_pattern"] = pattern
    json.dump(cfg, open(cfg_path, "w"), indent=2)
    print(f"enabled hybrid-SWA: {sum(pattern)} sliding / {len(pattern) - sum(pattern)} full layers")
    print(f"sliding_window={cfg.get('sliding_window')}  -> {cfg_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python enable_swa_config.py <model_dir>")
    main(sys.argv[1])
