# PB-Basic-002 — pre-IMO / Algebra

**Score: 7/7** &middot; pipeline output via `select:R1(3/4)`

**Grader note (Claude grader, sympy-verified):** 2案 S≥8 / 0<S≤8 を Cauchy-Schwarz+AM-GM で網羅、代数も検証済

## Problem

Show that $x^2 + y^2 + z^2 + t^2 \ge xyzt$ for any positive real numbers $x, y, z, t$ that satisfy $2(x + y + z + t) \ge xyzt$.

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

Let \(S = x + y + z + t\) and \(Q = x^2 + y^2 + z^2 + t^2\), \(P = xyzt\).  
Given: \(2S \ge P\).

By the Cauchy–Schwarz inequality,
\[
(1^2+1^2+1^2+1^2)(x^2+y^2+z^2+t^2) \ge (x+y+z+t)^2,
\]
so \(4Q \ge S^2\), i.e.
\[
Q \ge \frac{S^2}{4}. \tag{1}
\]

We consider two cases.

**Case 1:** \(S \ge 8\).  
From the hypothesis we have \(P \le 2S\).  
Because \(S \ge 8\), we have \(\frac{S^2}{4} \ge 2S\) (since \(S^2 \ge 8S\)).  
Thus
\[
Q \ge \frac{S^2}{4} \ge 2S \ge P,
\]
so \(Q \ge P\).

**Case 2:** \(0 < S \le 8\).  
By the AM–GM inequality,
\[
\frac{S}{4} \ge \sqrt[4]{P} \quad\Longrightarrow\quad P \le \left(\frac{S}{4}\right)^4.
\]
For \(S \le 8\), we have
\[
\frac{S^2}{4} - \left(\frac{S}{4}\right)^4 = \frac{S^2}{4}\left(1 - \frac{S^2}{64}\right) \ge 0,
\]
so \(\frac{S^2}{4} \ge \left(\frac{S}{4}\right)^4\).  
Hence, using (1),
\[
Q \ge \frac{S^2}{4} \ge \left(\frac{S}{4}\right)^4 \ge P,
\]
and again \(Q \ge P\).

In both cases we obtain \(x^2+y^2+z^2+t^2 \ge xyzt\), as required. ∎
