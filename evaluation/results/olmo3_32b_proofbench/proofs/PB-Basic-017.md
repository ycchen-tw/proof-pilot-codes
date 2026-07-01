# PB-Basic-017 — pre-IMO / Number theory

**Score: 7/7** &middot; pipeline output via `select:R1(3/4)`

**Grader note (Claude grader, sympy-verified):** The factorization of x^7+x^5+1 is verified symbolically; for a≥81 both factors are >1; the conclusion 'no such n' matches the reference.

## Problem

Find all non-negative integer $n$ such that $A_n = 1 + 3^{20(n^2+n+1)} + 9^{14(n^2+n+1)}$ is a prime number.

**Reference short answer:** There is no such $n$.

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

Let \(n\) be a non‑negative integer and set \(k = n^2 + n + 1\). Then
\[
A_n = 1 + 3^{20k} + 9^{14k} = 1 + 3^{20k} + (3^2)^{14k} = 1 + 3^{20k} + 3^{28k}.
\]
Define \(a = 3^{4k}\). Then \(a^5 = 3^{20k}\) and \(a^7 = 3^{28k}\), so
\[
A_n = a^7 + a^5 + 1.
\]

Now factor the polynomial \(x^7 + x^5 + 1\):
\[
x^7 + x^5 + 1 = (x^2 + x + 1)(x^5 - x^4 + x^3 - x + 1).
\]
(Verification: expand the right‑hand side:
\[
\begin{aligned}
&(x^2 + x + 1)(x^5 - x^4 + x^3 - x + 1) \\
&= x^7 - x^6 + x^5 - x^4 + x^3 + x^6 - x^5 + x^4 - x^3 + x^2 + x^5 - x^4 + x^3 - x^2 + x + x^5 - x^4 + x^3 - x + 1 \\
&= x^7 + ( -x^6 + x^6) + (x^5 - x^5 + x^5) + (-x^4 + x^4 - x^4) + (x^3 - x^3 + x^3) + (x^2 - x^2) + (x - x) + 1 \\
&= x^7 + x^5 + 1.
\end{aligned}
\]
Thus the identity holds for every integer \(x\).)

Substituting \(x = a\) gives
\[
A_n = (a^2 + a + 1)(a^5 - a^4 + a^3 - a + 1).
\]

For any \(n \ge 0\), we have \(k = n^2 + n + 1 \ge 1\) (since \(n=0\) gives \(k=1\), and \(n>0\) gives \(k>1\)). Hence
\[
a = 3^{4k} \ge 3^4 = 81 > 1.
\]

Now both factors are integers greater than \(1\):
\[
a^2 + a + 1 \ge 81^2 + 81 + 1 = 6643 > 1,
\]
and for \(a \ge 2\),
\[
a^5 - a^4 + a^3 - a + 1 = a^4(a-1) + (a^3 - a + 1) \ge 2^4 \cdot 1 + (8 - 2 + 1) = 16 + 7 = 23 > 1.
\]

Therefore \(A_n\) is a product of two integers each larger than \(1\); consequently \(A_n\) is composite for every non‑negative integer \(n\). No such \(n\) exists for which \(A_n\) is prime.

\[
\boxed{\text{No non‑negative integer } n \text{ makes } A_n \text{ prime.}}
\]
