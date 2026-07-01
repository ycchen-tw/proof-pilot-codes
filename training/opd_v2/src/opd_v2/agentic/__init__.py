# Copyright 2026 proof-pilot. Apache-2.0.
"""agentic semi-on-policy OPD —— pool-based 多 role 蒸餾（producer="agentic" 才載入）。

把 single-round prover OPD 推到整條 math_3r loop（prove/verify/refine/select）。本套件只在
orchestrator process 內、且 cfg.producer=="agentic" 時被 import → 單輪路徑零接觸（import 期也不載）。

模組：
- pool.py       PoolStore：per-problem graph + append-only JSONL + 記憶體 index（純資料/持久化）
- roles.py      reconstruct math_3r dataclasses + rank/bundle + render XML 模板 → Prompt
- sampler.py    fill-fraction role 採樣 + role 內 deficit item 選擇
- writeback.py  PoolIngestor：rollout → decode/parse(answer-only) → validity-gate → pool.admit
- seed.py       cold-start：DeepSeek r3_hard2000 nested data → seed.jsonl（全灌）
"""
