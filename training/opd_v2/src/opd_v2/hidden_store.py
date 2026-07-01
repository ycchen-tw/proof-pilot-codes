# Copyright 2026 proof-pilot. Apache-2.0.
"""teacher hidden 的 shared-FS spool —— v2 的核心搬運修正（修 v1 P7）。

v1 把 teacher hidden（單條 100k traj = 332MB）走 HTTP bytes → orchestrator RAM → gloo scatter 整包
pickle 散到各 rank，是整個 pipeline 最大的浪費。v2 改成：

    teacher 算完 hidden → **server-side 寫進 shared FS（WekaFS /work）** → 只回 handle（幾十 bytes）
    → orchestrator/buffer/scatter 全程只搬 handle → **trainer 那個 owning rank 自己從 FS 讀**。

bytes 的實體路徑因此是 teacher → FS → trainer rank 點對點，**永不經 orchestrator、永不進 gloo**。

本檔提供：
- **檔案格式**：64-byte self-describing header + payload（`packed || scales || top1`）。檔案自帶 layout，
  reader 不依賴 handle 的 metadata（避免 v1 那種 header/handle 漂移 bug）。
- `HiddenHandle`：orchestrator 端只需 `{path, seq_len, wv}`（seq_len 給 buffer token 計帳、wv 給 staleness
  再驗、path 給讀取 + GC）。
- `write_hidden` / `read_hidden`：teacher 端寫（atomic：tmp + rename）、trainer 端讀。
- `HiddenStore`：管 hidden 目錄、產生唯一 path、GC（unlink + 背景 TTL 兜底，V14）。

torch-free（orchestrator 純 CPU process 要能 import）；payload 是 raw bytes，decode 在 trainer GPU 端做。
"""
from __future__ import annotations

import os
import struct
import time
import uuid
from dataclasses import dataclass

from opd_v2.config import HID_DIM

# header：magic(4) version(4) seq_len(4) hid(4) packed_len(8) scales_len(8) top1_len(8) = 40，pad 到 64。
_MAGIC = b"OPDH"
_VERSION = 1
_HEADER_FMT = "<4sIIIQQQ"
_HEADER_CORE = struct.calcsize(_HEADER_FMT)   # 40
HEADER_SIZE = 64


def packed_row_bytes(hid: int = HID_DIM) -> int:
    return hid * 6 // 8


def scale_row_bytes(hid: int = HID_DIM) -> int:
    return (hid // 32) * 2


@dataclass
class HiddenHandle:
    """orchestrator 端搬的小物件（不含 bytes）。檔案 self-describing，這裡只留 GC/accounting 需要的。"""
    path: str          # shared-FS 絕對路徑
    seq_len: int       # teacher 回傳 position 數（= 對齊用的 row 數）；給 buffer token 計帳
    wv: int            # rollout 生成時的 weight_version（讀時可再驗 staleness）

    def to_dict(self) -> dict:
        return {"path": self.path, "seq_len": self.seq_len, "wv": self.wv}

    @classmethod
    def from_dict(cls, d: dict) -> "HiddenHandle":
        return cls(path=d["path"], seq_len=int(d["seq_len"]), wv=int(d["wv"]))


def write_hidden(path: str, packed: bytes, scales: bytes, seq_len: int,
                 top1: bytes = b"", hid: int = HID_DIM) -> None:
    """atomic 寫 hidden 檔（teacher server-side 呼叫）。先寫 `<path>.tmp.<pid>` 再 rename。

    驗證 payload 長度與 seq_len/hid 一致（早抓 codec/slicing bug，勝過 trainer 端神秘 reshape 爆掉）。
    """
    exp_p = seq_len * packed_row_bytes(hid)
    exp_s = seq_len * scale_row_bytes(hid)
    if len(packed) != exp_p:
        raise ValueError(f"packed len {len(packed)} != seq_len*pcols {exp_p} (seq_len={seq_len} hid={hid})")
    if len(scales) != exp_s:
        raise ValueError(f"scales len {len(scales)} != seq_len*scols {exp_s} (seq_len={seq_len} hid={hid})")
    if top1 and len(top1) != seq_len * 4:
        raise ValueError(f"top1 len {len(top1)} != seq_len*4 {seq_len * 4}")
    header = struct.pack(_HEADER_FMT, _MAGIC, _VERSION, seq_len, hid,
                         len(packed), len(scales), len(top1))
    header = header + b"\x00" * (HEADER_SIZE - _HEADER_CORE)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}"
    with open(tmp, "wb") as f:
        f.write(header)
        f.write(packed)
        f.write(scales)
        if top1:
            f.write(top1)
    os.replace(tmp, path)   # atomic on POSIX；reader 永遠看到完整檔或不存在


def read_hidden(path: str) -> tuple[bytes, bytes, bytes, int, int]:
    """讀 hidden 檔（trainer owning rank 呼叫）。回 (packed, scales, top1, seq_len, hid)。

    檔案自帶 layout（不靠 handle），出錯（被 GC/孤兒/半寫）丟 FileNotFoundError/ValueError，
    由 trainer 的 collective-safe gate（§6.5）轉成全 rank 一起 skip。
    """
    with open(path, "rb") as f:
        head = f.read(HEADER_SIZE)
        if len(head) < HEADER_SIZE:
            raise ValueError(f"hidden file too short for header: {path}")
        magic, ver, seq_len, hid, plen, slen, tlen = struct.unpack(_HEADER_FMT, head[:_HEADER_CORE])
        if magic != _MAGIC:
            raise ValueError(f"bad hidden magic {magic!r} in {path}")
        if ver != _VERSION:
            raise ValueError(f"unsupported hidden version {ver} in {path}")
        packed = f.read(plen)
        scales = f.read(slen)
        top1 = f.read(tlen) if tlen else b""
    if len(packed) != plen or len(scales) != slen or len(top1) != tlen:
        raise ValueError(f"hidden payload truncated: {path}")
    return packed, scales, top1, int(seq_len), int(hid)


class HiddenStore:
    """管一個 run 的 hidden 目錄（shared FS）：產生唯一 path、GC（unlink + TTL 兜底）。

    owner = orchestrator（它創 handle、追 staleness、送 trainer，故它管刪，V14）。
    """

    def __init__(self, hidden_dir: str):
        self.dir = hidden_dir
        os.makedirs(self.dir, exist_ok=True)

    def new_path(self) -> str:
        """產生本 run 內唯一 hidden 檔路徑（client 在打 teacher 前產，傳給 teacher 寫、自己記著 GC）。"""
        return os.path.join(self.dir, f"{uuid.uuid4().hex}.bin")

    def delete(self, path: str) -> bool:
        try:
            os.remove(path)
            return True
        except FileNotFoundError:
            return False
        except OSError:
            return False

    def delete_handles(self, handles) -> int:
        """刪一批（batch /train_step 回來後 / stale-drop 後）。回實刪數。"""
        n = 0
        for h in handles:
            p = h.path if isinstance(h, HiddenHandle) else h
            if p and self.delete(p):
                n += 1
        return n

    def sweep_ttl(self, ttl_seconds: float) -> int:
        """背景 TTL 掃：清 orchestrator crash 留下的孤兒（mtime 超過 ttl）。回清掉的檔數。

        run-scoped（只掃本 run 的 hidden_dir），不會誤刪別 run。
        """
        now = time.time()
        n = 0
        try:
            entries = os.listdir(self.dir)
        except FileNotFoundError:
            return 0
        for name in entries:
            if not name.endswith(".bin"):
                continue
            p = os.path.join(self.dir, name)
            try:
                if now - os.path.getmtime(p) > ttl_seconds:
                    if self.delete(p):
                        n += 1
            except OSError:
                pass
        return n

    def usage(self) -> tuple[int, int]:
        """(檔數, 總 bytes)——wandb 觀測用。"""
        n, total = 0, 0
        try:
            for name in os.listdir(self.dir):
                if name.endswith(".bin"):
                    try:
                        total += os.path.getsize(os.path.join(self.dir, name))
                        n += 1
                    except OSError:
                        pass
        except FileNotFoundError:
            pass
        return n, total
