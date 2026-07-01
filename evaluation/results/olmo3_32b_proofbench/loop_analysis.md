# OPD 32B (v33/s200) ProofBench cap-hitting generations: infinite-loop vs overthinking analysis

**Source run**: `tmp/pb_agentloop/runs/full60_opd32b_s200/` (OPD 32B v33 step_200, agentic
prove→verify→refine→select, max_tokens=128000, 2026-06-22).
**Method**: across all 60 problems' 1,418 generations, 53 have `finish_reason=length / truncated=True`
(hit the 128k cap). For each, take the **last 8,000 characters of reasoning_content** and have 9
general-purpose agents **read them blind** and classify (no metrics fed), then cross-check against the
cheap metric `zlib_tail` afterward.
**Reasoning preserved**: the full reasoning_content of all 53 (each ~150k–510k chars / 128k tokens) is
**100% preserved** in the stage JSON; the loop runs in `reasoning_content`, with `content` empty.

## Conclusion: 85% are genuine loops, only 15% are overthinking

| Category | n | % | Definition |
|---|---|---|---|
| **infinite_loop** | 35 | 66% | Degenerate verbatim repetition (single token / phrase / sentence / whole-paragraph verbatim copy), no new information |
| **semantic_loop** | 10 | 19% | No verbatim repetition, but repeatedly restarts the same lemma/case with cosmetic changes and no real progress |
| **overthinking** | 8 | 15% | Genuinely diverse mathematical reasoning, continually producing new expressions / cases / self-corrections, just not converging before the cap |

→ **Any form of loop (IL+SL) = 45 / 53 (85%); genuine "thought too long but not broken" is only 8 (15%).**

## A cheap metric can triage on its own (blind metric vs agent reading, almost perfect agreement)

`zlib_tail` (the zlib compression ratio of the last 8000 chars) separates cleanly into three bands:

| zlib_tail band | verdict distribution | interpretation |
|---|---|---|
| **< 0.02** | infinite_loop 16 / 16 | Degenerated to a single-token/phrase (` a?`, `+2`, `1,`, `3+`, `2^?`, `384*?`…) hard attractor |
| **0.02–0.28** | infinite_loop 19 + semantic_loop 9 | Paragraph-level verbatim repetition / semantic looping |
| **> 0.28** | overthinking 8 + semantic_loop 1 | Genuine long reasoning (except 1 case, S53, a borderline numerical descent) |

**So `zlib_tail > 0.28` ⇒ almost certainly overthinking; `< 0.02` ⇒ certainly a degenerate loop.** Only
the middle band needs the text read.

## Distribution of the pathology

- **By stage**: prove 38 (IL26 / SL4 / OT8), refine 15 (IL9 / SL6, **not a single refine is overthinking
  — all are loops**). Hitting the cap in the refine stage = 100% pathological looping, consistent with
  memory [[opd32b-s200-proofbench-eval]] ("refine truncation = looping, not long thinking").
- **All 8 overthinking cases are in prove**, and concentrated on **long-coordinate / long-computation
  problems**: Geometry 4 (Adv-015×2, Adv-016, Basic-026), Combinatorics 2, Algebra-FE 1, NT 1. These
  "genuinely need to be long" rather than being broken.

## Strong signal: capitulation opener → paragraph loop

Of the 45 loops, about 18 have their repeating unit begin with the same sentence: **"Given the time, I
think/will produce a solution that…"**. After writing this kind of "time/length is nearly up, I'll just
give an answer" capitulation paragraph, the model **copies the whole paragraph verbatim dozens of times**
until it hits the cap. This is a fingerprint of EOS-under-training: the model wants to stop but hasn't
learned to emit EOS, so instead it repeats the capitulation passage. → An excellent trigger signal for
V34 tail-masking / EOS-anchoring.

## Implications for V34

- **Tail-masking instead of whole-trajectory drop holds up**: 85% of cap-hits are loops; the tail really
  is bad tokens, so masking the repeated tail region while keeping the earlier valid reasoning is correct.
- **The 8 overthinking cases should not be dropped as loops**: use `zlib_tail > 0.28` (or an equivalent
  repetition metric) as a gate to avoid killing long coordinate-bashing.
- The detector is cheap to deploy: `zlib_tail` settles both ends directly, with the middle band paired
  with an n-gram repetition rate + capitulation-phrase detection.

Full per-case verdicts (53 verdicts + metrics): `loop_classification.json` (this directory).
Detector implementation: `evaluation/harness/zlib_runaway_detector.py` (streaming + offline, with
`--stage-json` to scan ProofBench stage files).

## Appendix: streaming loop detector (zlib sliding window, false positives measured)

`zlib_tail` = the zlib compression ratio of a span of text (`compressed/raw`) = LZ77 catching repetition
→ a loop compresses toward 0, normal reasoning ~0.3. It can be computed while decoding (12k bytes ~ tens
of µs) and can run directly on token-id bytes without detokenizing.

**Single-threshold zlib sliding window (W=12000 chars, step 1000, hard<0.05 or soft<0.18×3), measured**:
- Loop detection: catches token / paragraph / semantic loops all (saves 30–95k tokens; W=6000 misses
  paragraph loops, whose period must be < W/2).
- FP scan over **1,008 sufficiently-long clean-EOS generations**: **only 3 false positives (0.30%)**, all
  of them **legitimate structured enumeration / long arithmetic** (`o=1409,L=2,k=5 / o=1411,…`, prime
  factorization) — the template repeats but the numbers keep changing, and they all recover to a valid
  \boxed at the end.

**Robust two-stage rule (0% FP / 100% loop catch on this dataset)**:
- **HARD**: `zlib < 0.05` → abort immediately (degenerate token loop; the enumeration floor is 0.141, so
  it never gets this low).
- **SOFT**: `zlib < 0.18` **sustained for ≥ ~20 consecutive windows (~20k chars / ~12–15k tokens)** →
  abort. Rationale: the max_low_run of the enumeration FPs is only **5/5/9**, whereas true loops are
  **≥62** (paragraph loops 198–381) — a huge gap.
- Failed attempt (recorded): a distinct-shingle second signal is **unusable** — paragraph loops are
  "approximately verbatim" (each copy drifts slightly), so exact-shingle distinct≈1.0 is indistinguishable
  from enumeration. zlib's fuzzy LZ77 + a "sustained" criterion is the right approach.

**Where it lands**: ① sglang server-side runaway early abort (abort ≠ changing the sampling distribution,
so it's on-policy safe; see [[opd-rollout-no-distribution-change]]); ② an eval / Kaggle per-problem stop
criterion; ③ the V34 trainer EOS-region diagnostic uses the same metric. **Cost**: the SOFT stage has a
~12–15k-token detection latency (the HARD stage is instant), but a loop would otherwise run to 128k, so
it still saves 100k+. **Caveat**: FP n is only 3 (a 60-problem eval); the threshold should be re-validated
on a larger sample before going into production.
