"""Incremental degenerate-loop detection for streaming generation.

A **loop** is the *same* text segment repeated **densely within a short span** — the model
stuck emitting the same thing over and over with no progress. That is the ONLY thing we abort.

What is NOT a loop (and must never trip detection):
  - re-attempting an approach several times across long reasoning (the same identity recurs,
    but spread far apart — genuine work happens in between);
  - checking small cases "u=1,v=1: … u=2,v=1: …" — each line is a *different* computation,
    bounded, with a conclusion, then the proof moves on.
Both recur, but the recurrences are SPREAD OUT (or each instance differs). So we require
**local density** — one chunk repeating > `threshold` times inside a `span`-char window —
not a raw count over the whole scan window (the old detector's bug: it fired on scattered
recurrence and aborted healthy reasoning).

Calibration (measured on real OPD traces, PB-Advanced-012): genuine reasoning — including
small-case enumeration — tops out at maxlocal ≈ 4 within a 1500-char window; real loops sit
at 20+. `threshold=8` leaves a 2× safety margin below genuine and well under any real loop.

NOTE: an earlier attempt added skeleton normalization (digits→#, vars→V) to catch "a1,a2,a3"
index cycles. It was REMOVED — it collapses distinct legitimate cases ("u=1,v=1" vs "u=2,v=1")
to the same skeleton and false-positives on normal small-case checking, which is not cheaply
separable from a true enumeration loop. A genuine degenerate enumeration repeats its verbatim
connective text densely and is caught by the raw detector anyway.

Both functions are pure and cheap. For streaming, call on a bounded recent window every N chars.
"""
from __future__ import annotations


def _dense_first(text: str, chunk: int, step: int, threshold: int, span: int) -> int | None:
    """First offset of a chunk that recurs > `threshold` times within some `span`-char
    window (a real, local loop). None if no chunk is that locally dense.

    Sliding-window over each chunk's sorted occurrence offsets: a window holds the
    occurrences with `offset[k] - offset[j] <= span`; if it ever holds > threshold of
    them, that cluster (starting at offset[j]) is the loop's onset."""
    t = text or ""
    pos: dict[str, list[int]] = {}
    for i in range(0, len(t) - chunk, step):
        pos.setdefault(t[i:i + chunk], []).append(i)
    best: int | None = None
    for offs in pos.values():
        if len(offs) <= threshold:
            continue
        j = 0
        for k in range(len(offs)):
            while offs[k] - offs[j] > span:
                j += 1
            if k - j + 1 > threshold:
                if best is None or offs[j] < best:
                    best = offs[j]
                break
    return best


def degenerate(text: str, *, chunk: int = 25, step: int = 5,
               threshold: int = 8, span: int = 1500) -> bool:
    """True only for a real loop: one `chunk`-char segment repeated > `threshold` times
    within a `span`-char window. Scattered recurrence / small-case checking does NOT trip."""
    t = text or ""
    if len(t) < chunk * 2:
        return False
    return _dense_first(t, chunk, step, threshold, span) is not None


def find_loop_cut(text: str, *, chunk: int = 25, step: int = 5,
                  threshold: int = 8, span: int = 1500) -> int | None:
    """If `text` contains a loop, return the index where the dense looping cluster begins
    (truncate there to keep the clean, pre-loop prefix). Else None."""
    t = text or ""
    if len(t) < chunk * 2:
        return None
    return _dense_first(t, chunk, step, threshold, span)


def recent_window(text: str, window: int = 16_000) -> str:
    """The tail to scan — a loop manifests in recently generated text, so bounding the
    scan keeps detection O(window) per check instead of O(total)."""
    t = text or ""
    return t[-window:] if len(t) > window else t
