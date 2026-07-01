# Copyright 2026 proof-pilot. Apache-2.0.
"""async（aiohttp）clients —— rollout 與 teacher sglang server。

設計原則（PLAN §5.5）：
- **rollout**：`/generate` 一個 request 一條 rollout（**無 `n`**，V1）；**直接讀 `output_ids`**（V2，
  不用 return_logprob/logprob_start_len/skip-tokenizer-init 那套 v1 爛 hack）；`wv` 取 server-reported
  `meta_info.weight_version`（V6）。
- **teacher**：`/score` 帶 `out_path` → teacher **server-side 寫 shared FS**、回 handle metadata JSON
  （**不回 bytes**，V12）。client 組成 `HiddenHandle`（path 由 orchestrator 產、stamp rollout 的 wv）。

全 async，共用一個 `aiohttp.ClientSession`（由 orchestrator 建、傳進 pool/clients）。每個方法自帶 timeout
（rollout 32k 生成可破 20min；teacher score 較快）。非 2xx 直接 raise → 由 pool/produce 端處理。
"""
from __future__ import annotations

import aiohttp

from opd_v2.hidden_store import HiddenHandle


class RolloutError(RuntimeError):
    pass


class TeacherError(RuntimeError):
    pass


class RolloutClient:
    """token-in-token-out student rollout（fp8 flash_rl 部署；client 不送 load_format，V30/§5.6）。"""

    def __init__(self, session: aiohttp.ClientSession, base_url: str):
        self.s = session
        self.base = base_url.rstrip("/")

    async def health(self, timeout: float = 5.0) -> bool:
        try:
            async with self.s.get(f"{self.base}/health",
                                  timeout=aiohttp.ClientTimeout(total=timeout)) as r:
                return r.status == 200
        except Exception:
            return False

    async def generate_one(self, input_ids: list[int], *, temperature: float, top_p: float,
                           top_k: int, max_new_tokens: int, ignore_eos: bool,
                           timeout: float = 3600.0) -> tuple[list[int], int | None, str | None]:
        """一條 rollout。回 (output_ids, weight_version|None, finish_reason|None)。

        finish_reason = sglang `meta_info.finish_reason.type`（"stop"=EOS/stop-token、"length"=撞
        max_new_tokens/context、"abort" 等）→ 用來算 EOS-停 / length-停 比例（截斷監控）。
        """
        sp = {
            "temperature": temperature, "top_p": top_p,
            "max_new_tokens": max_new_tokens, "ignore_eos": ignore_eos,
        }
        if top_k and top_k > 0:
            sp["top_k"] = top_k
        payload = {"input_ids": input_ids, "sampling_params": sp, "stream": False}
        async with self.s.post(f"{self.base}/generate", json=payload,
                               timeout=aiohttp.ClientTimeout(total=timeout)) as r:
            if r.status != 200:
                raise RolloutError(f"/generate -> {r.status}: {(await r.text())[:200]}")
            data = await r.json()
        if isinstance(data, list):
            data = data[0] if data else {}
        if not isinstance(data, dict):
            raise RolloutError(f"unexpected /generate response type {type(data)}")
        meta = data.get("meta_info") or {}
        out = data.get("output_ids")
        if out is None:                       # 某些 sglang 版本把 output_ids 放 meta_info
            out = meta.get("output_ids")
        if out is None:
            raise RolloutError(f"/generate response has no output_ids (keys={list(data)})")
        # sglang reports "default" until first update_weights_from_disk(weight_version=...) →
        # 非數字一律 None，由 produce 端 fall back 到 orchestrator 當前 weight_version。
        wv = None
        wv_raw = meta.get("weight_version")
        if wv_raw not in (None, ""):
            try:
                wv = int(wv_raw)
            except (ValueError, TypeError):
                wv = None
        fr = meta.get("finish_reason")
        if isinstance(fr, dict):
            fr = fr.get("type")
        return list(out), wv, (fr if isinstance(fr, str) else None)

    # ---- weight sync（orchestrator 主導；parallel 跨所有 replica，V22）----
    async def pause_generation(self, mode: str = "in_place", timeout: float = 120.0) -> dict:
        async with self.s.post(f"{self.base}/pause_generation", json={"mode": mode},
                               timeout=aiohttp.ClientTimeout(total=timeout)) as r:
            r.raise_for_status()
            return await r.json()

    async def continue_generation(self, timeout: float = 120.0) -> dict:
        # 空 body 必帶（sglang 否則回 422）
        async with self.s.post(f"{self.base}/continue_generation", json={},
                               timeout=aiohttp.ClientTimeout(total=timeout)) as r:
            r.raise_for_status()
            return await r.json()

    async def update_weights_from_disk(self, path: str, weight_version: int,
                                       flush_cache: bool = False, timeout: float = 1800.0) -> dict:
        """flush_cache=False 給 in_place pause（必要：in_place 下 flush 失敗會 assert 殺 scheduler）。
        **不送 load_format**：維持 server 的 flash_rl fp8 loader（送 auto 會走 DefaultLoader 炸，§5.6）。"""
        payload = {"model_path": path, "flush_cache": flush_cache,
                   "weight_version": str(weight_version)}
        async with self.s.post(f"{self.base}/update_weights_from_disk", json=payload,
                               timeout=aiohttp.ClientTimeout(total=timeout)) as r:
            r.raise_for_status()
            return await r.json()


class TrainerHTTPClient:
    """orchestrator → trainer-as-service（rank-0 HTTP ingress）。control 面，小資料 + handle（V23）。"""

    def __init__(self, session: aiohttp.ClientSession, base_url: str):
        self.s = session
        self.base = base_url.rstrip("/")

    async def health(self, timeout: float = 5.0) -> dict | None:
        try:
            async with self.s.get(f"{self.base}/health",
                                  timeout=aiohttp.ClientTimeout(total=timeout)) as r:
                return await r.json() if r.status == 200 else None
        except Exception:
            return None

    async def train_step(self, trajs_wire: list[dict], want_g4: bool = False,
                         timeout: float = 7200.0) -> dict:
        payload = {"trajs": trajs_wire, "want_g4": want_g4}
        async with self.s.post(f"{self.base}/train_step", json=payload,
                               timeout=aiohttp.ClientTimeout(total=timeout)) as r:
            r.raise_for_status()
            return await r.json()

    async def save(self, slot: str | None = None, timeout: float = 1800.0) -> dict:
        async with self.s.post(f"{self.base}/save", json={"slot": slot},
                               timeout=aiohttp.ClientTimeout(total=timeout)) as r:
            r.raise_for_status()
            return await r.json()

    async def checkpoint(self, hf: bool = True, keep: int = -1, timeout: float = 3600.0) -> dict:
        """durable DCP+HF ckpt（model+optim+sched）。比 /save 久（gather+HF），timeout 放大。"""
        async with self.s.post(f"{self.base}/checkpoint", json={"hf": hf, "keep": keep},
                               timeout=aiohttp.ClientTimeout(total=timeout)) as r:
            r.raise_for_status()
            return await r.json()

    async def stop(self, timeout: float = 120.0) -> dict:
        async with self.s.post(f"{self.base}/stop", json={},
                               timeout=aiohttp.ClientTimeout(total=timeout)) as r:
            r.raise_for_status()
            return await r.json()


class TeacherClient:
    """DeepSeek-V4-Flash teacher scoring（/score 寫 shared FS、回 handle，V12）。"""

    def __init__(self, session: aiohttp.ClientSession, base_url: str):
        self.s = session
        self.base = base_url.rstrip("/")

    async def health(self, timeout: float = 5.0) -> bool:
        try:
            async with self.s.get(f"{self.base}/health",
                                  timeout=aiohttp.ClientTimeout(total=timeout)) as r:
                return r.status == 200
        except Exception:
            return False

    async def score(self, input_ids: list[int], *, start: int, out_path: str, wv: int,
                    return_top1: bool = False, timeout: float = 1200.0) -> HiddenHandle:
        """teacher 對 full_ids 算 hidden、**server-side 寫 out_path**、回 handle metadata。

        回應 JSON：`{seq_len, packed_bytes, scales_bytes, top1_bytes}`（檔已落 FS）。client 組
        `HiddenHandle(path=out_path, seq_len, wv)`——bytes 全程不過 orchestrator（P7 修正）。
        """
        payload = {"input_ids": input_ids, "start": start, "out_path": out_path,
                   "return_top1": return_top1}
        async with self.s.post(f"{self.base}/score", json=payload,
                               timeout=aiohttp.ClientTimeout(total=timeout)) as r:
            if r.status != 200:
                raise TeacherError(f"/score -> {r.status}: {(await r.text())[:200]}")
            meta = await r.json()
        seq_len = int(meta["seq_len"])
        return HiddenHandle(path=out_path, seq_len=seq_len, wv=wv)
