"""Parse model outputs into typed packages and decide validity.

Outputs use XML tags (NOT markdown / \\boxed) so parsing is unambiguous and never collides with
`\\boxed{answer}` inside a proof:
  - prover / refiner: <solution>...</solution> <self_evaluation>...</self_evaluation> <score>0|0.5|1</score>
  - verifier:         <evaluation>...</evaluation> <suggestions>...</suggestions> <score>0|0.5|1</score>
  - selector:         <selected_id>P#|R#</selected_id>

Parsing is pure and never raises: a malformed generation yields valid=False / score=None, which
the pipeline filters out (the sample is dropped, others are used).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

MIN_SOLUTION_CHARS = 500

_SOLUTION_RE = re.compile(r"<solution>(.*?)</solution>", re.DOTALL | re.IGNORECASE)
_SELFEVAL_RE = re.compile(r"<self_evaluation>(.*?)</self_evaluation>", re.DOTALL | re.IGNORECASE)
_SCORE_RE = re.compile(r"<score>\s*(0(?:\.5)?|1)\s*</score>", re.IGNORECASE)
_ID_RE = re.compile(r"<selected_id>\s*([PR]\d+)\s*</selected_id>", re.IGNORECASE)

# --- lenient extraction (this model systematically OMITS </solution>) ---
# Observed: the model reliably writes "<solution>" + a correct proof, then jumps straight to the
# self_evaluation section (often as a stray "</self_evaluation>") and a "<score>", but NEVER closes
# with "</solution>". Strict <solution>...</solution> then drops perfectly good proofs. So take the
# text from "<solution>" up to whichever section boundary appears first.
_SOLUTION_OPEN_RE = re.compile(r"<solution>", re.IGNORECASE)
_SOLUTION_END_RE = re.compile(r"</solution>|</?self_evaluation>|<score>", re.IGNORECASE)
# selected_id: tolerate a missing close tag, then fall back to the last bare P#/R# token.
_ID_OPEN_RE = re.compile(r"<selected_id>\s*([PR]\d+)", re.IGNORECASE)
_ID_BARE_RE = re.compile(r"\b([PR]\d+)\b")


def _lenient_solution(text: str) -> str:
    """<solution> ... up to the first of </solution> / <self_evaluation> / </self_evaluation> /
    <score> / end. Recovers proofs from this model's missing-</solution> outputs."""
    m = _SOLUTION_OPEN_RE.search(text or "")
    if not m:
        return ""
    rest = text[m.end():]
    e = _SOLUTION_END_RE.search(rest)
    return (rest[:e.start()] if e else rest).strip()


@dataclass
class ProofPackage:
    candidate_id: str          # P0, P1, ...
    proof: str                 # <solution> content
    self_eval: str             # <self_evaluation> content
    self_score: float | None   # <score>
    valid: bool
    call: dict = field(repr=False)


@dataclass
class VerificationPackage:
    candidate_id: str          # which proof this verifies
    verifier_idx: int
    text: str                  # full verifier output (evaluation + suggestions)
    score: float | None
    call: dict = field(repr=False)


@dataclass
class RefinedPackage:
    refiner_id: str            # R0, R1, ...
    proof: str
    self_eval: str
    self_score: float | None
    valid: bool
    call: dict = field(repr=False)


def _first(regex: re.Pattern, text: str) -> str:
    m = regex.search(text or "")
    return m.group(1).strip() if m else ""


def parse_score(text: str) -> float | None:
    m = _SCORE_RE.search(text or "")
    return float(m.group(1)) if m else None


def parse_selected_id(text: str) -> str | None:
    text = text or ""
    m = _ID_RE.findall(text)            # well-formed <selected_id>P#</selected_id>
    if m:
        return m[-1]
    m = _ID_OPEN_RE.findall(text)       # open tag, missing close (this model's quirk)
    if m:
        return m[-1]
    m = _ID_BARE_RE.findall(text)       # last resort: a bare P#/R# token in the answer
    return m[-1] if m else None


def _two_section(text: str, finish_reason: str | None, error) -> tuple[str, str, float | None, bool]:
    """Shared parsing/validity for prover & refiner outputs. Lenient: this model omits </solution>
    and sometimes the <score>, so validity hinges on a long-enough recovered solution, not on the
    exact closing tags. A still-truncated call (finish=length, not salvaged) stays invalid."""
    solution = _first(_SOLUTION_RE, text) or _lenient_solution(text)
    self_eval = _first(_SELFEVAL_RE, text)
    score = parse_score(text)
    valid = (
        error is None
        and finish_reason != "length"
        and len(solution) > MIN_SOLUTION_CHARS
    )
    return solution, self_eval, score, valid


def parse_proof_package(call: dict, candidate_id: str) -> ProofPackage:
    sol, se, score, valid = _two_section(call.get("content", ""),
                                         call.get("finish_reason"), call.get("error"))
    return ProofPackage(candidate_id=candidate_id, proof=sol, self_eval=se,
                        self_score=score, valid=valid, call=call)


def parse_refined_package(call: dict, refiner_id: str) -> RefinedPackage:
    sol, se, score, valid = _two_section(call.get("content", ""),
                                         call.get("finish_reason"), call.get("error"))
    return RefinedPackage(refiner_id=refiner_id, proof=sol, self_eval=se,
                          self_score=score, valid=valid, call=call)


def parse_verification(call: dict, candidate_id: str, verifier_idx: int) -> VerificationPackage:
    text = call.get("content", "") or ""
    score = None if call.get("error") else parse_score(text)
    return VerificationPackage(candidate_id=candidate_id, verifier_idx=verifier_idx,
                               text=text, score=score, call=call)
