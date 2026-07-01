#!/usr/bin/env python3
"""讓 sglang 對 Olmo3Sink 啟用 hybrid SWA KV pool（KV 容量 +1.6~3×→更高併發/吞吐）。

stock sglang `is_hybrid_swa_model` 是硬編碼 arch allowlist，不含 Olmo3SinkForCausalLM → SWA pool 不開、
KV 按 32 層全 full 配置（浪費）。本 patch 兩處 anchored edit：
 1) hybrid_swa_archs set 加入 Olmo3SinkForCausalLM / Olmo2ForCausalLM
 2) get_hybrid_layer_ids 的 GptOss(讀 config.layer_types) 分支條件加入 Olmo（deploy config 已有 layer_types）
model 端 attention 本來就按 layer_types 套 sliding window（olmo2_sink.py），只差 sglang KV pool allocator。

用法（換 image/版本時重生）：
  apptainer exec <sif> cat /sgl-workspace/sglang/python/sglang/srt/configs/model_config.py > stock.py
  python apply_swa_patch.py stock.py model_config.py
"""
import sys
src = open(sys.argv[1]).read(); orig = src
a1 = '    hybrid_swa_archs = {\n        "Llama4ForConditionalGeneration",'
assert src.count(a1) == 1, f"anchor1 count={src.count(a1)} (sglang layout 變了？)"
src = src.replace(a1, '    hybrid_swa_archs = {\n        "Olmo3SinkForCausalLM",\n        "Olmo2ForCausalLM",\n        "Llama4ForConditionalGeneration",')
a2 = '    elif "GptOssForCausalLM" in model_architectures:\n        layer_types = getattr(hf_text_config, "layer_types", [])'
assert src.count(a2) == 1, f"anchor2 count={src.count(a2)} (sglang layout 變了？)"
src = src.replace(a2, '    elif "GptOssForCausalLM" in model_architectures or any(\n        a in ("Olmo3SinkForCausalLM", "Olmo2ForCausalLM") for a in model_architectures\n    ):\n        layer_types = getattr(hf_text_config, "layer_types", [])')
assert src != orig
compile(src, "model_config.py", "exec")
open(sys.argv[2], "w").write(src)
print("patched OK ->", sys.argv[2])
