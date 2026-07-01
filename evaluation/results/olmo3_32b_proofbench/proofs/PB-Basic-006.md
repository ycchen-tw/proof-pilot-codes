# PB-Basic-006 — IMO-medium / Algebra

**Score: 1/7** &middot; pipeline output via `select:R2(4/4)`

**Grader note (Claude grader, sympy-verified):** The key inequality (1) is derived from a product of sign-mixed Newton inequalities and is actually false (a degree-6 counterexample is constructed); the core contradiction collapses.

## Problem

Consider any infinite sequence of integers $c_0, c_1, c_2, \ldots $ such that $c_0 \neq 0$. Prove that for some integer $k \geq 0$, the polynomial $P(x) = \sum_{i = 0}^k c_i x^i$ has fewer than $k$ distinct real roots.

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

We prove the statement by contradiction.  
Assume that for every \(k\ge 0\) the polynomial  
\[
P_k(x)=\sum_{i=0}^{k}c_i x^i
\]
has at least \(k\) distinct real roots.  
Since \(c_0\neq0\), the leading coefficient \(c_k\) cannot be zero for any \(k\) (otherwise the degree would be smaller than \(k\) and the polynomial would have fewer than \(k\) real roots). Hence all \(c_k\) are nonzero integers.

By multiplying the whole sequence by \(-1\) if necessary, we may assume \(c_0>0\).  
If \(c_1<0\), replace the sequence by \(d_i=(-1)^i c_i\). The polynomials with coefficients \(d_i\) are \(P_i(-x)\); they have the same real roots (negatives) and therefore also have all real roots. Moreover \(d_0=c_0>0\) and \(d_1=-c_1>0\). Hence we may assume \(c_1>0\) as well.  
Thus we have \(c_0>0,\;c_1>0\) and all \(c_k\) are nonzero integers.

For each \(n\ge1\) the polynomial \(P_{n+1}\) has \(n+1\) distinct real roots.  
We use two classical inequalities.

**Newton’s inequalities.** For a polynomial of degree \(n+1\) with all real roots, the coefficients satisfy for \(k=1,\dots,n\):
\[
c_k^2\ge c_{k-1}c_{k+1}\cdot\frac{k+1}{k}\cdot\frac{n+2-k}{n+1-k}.
\]
Multiplying these \(n\) inequalities and cancelling the common factor \((c_2\cdots c_{n-1})^2\) gives
\[
c_1^2c_n^2\ge (n+1)^2 c_0c_1c_nc_{n+1}. \tag{1}
\]

**Sum of squares.** From the roots of \(P_{n+1}\) we have
\[
c_n^2\ge 2c_{n+1}c_{n-1}\qquad(n\ge1). \tag{2}
\]
(For \(n=1\) this is \(c_1^2\ge2c_2c_0\).)

From (1) we obtain
\[
\begin{cases}
c_{n+1}\le\dfrac{c_1c_n}{(n+1)^2c_0}, & \text{if }c_n>0,\\[6pt]
c_{n+1}\ge\dfrac{c_1c_n}{(n+1)^2c_0}, & \text{if }c_n<0.
\end{cases} \tag{3}
\]

Now consider the set \(S=\{n\ge1:c_n>0\}\).  
If \(S\) is infinite, then for any \(n\in S\) we have from (3) that
\[
|c_{n+1}|\le\frac{c_1|c_n|}{(n+1)^2c_0}\le\frac{c_1}{(n+1)^2c_0}.
\]
For sufficiently large \(n\) the right‑hand side is \(<1\), contradicting the fact that \(c_{n+1}\) is a nonzero integer.  
Hence \(S\) is finite, so there are infinitely many \(n\) with \(c_n<0\). Let \(T=\{n\ge1:c_n<0\}\).

If there are infinitely many \(n\in T\) with \(c_{n-1}>0\), then the set of positive indices would be infinite (each such \(n\) gives a positive \(c_{n-1}\)), contradicting the finiteness of \(S\). Therefore, for all sufficiently large \(n\in T\) we have \(c_{n-1}<0\) as well.  
Take such an \(n\). Then \(c_n<0\) and \(c_{n-1}<0\), so \(c_nc_{n-1}>0\). From (2) we obtain
\[
|c_{n+1}|\le\frac{|c_n|^2}{2|c_{n-1}|}. \tag{4}
\]
Let \(a_n=|c_n|\). For the infinite tail of \(T\) we have \(a_{n+1}\le a_n^2/(2a_{n-1})\).  
Set \(r_n=a_n/a_{n-1}\). Then \(r_{n+1}\le r_n/2\). Hence for some \(N\) we have \(r_n\le r_{N-1}/2^{\,n-N+1}\). Consequently
\[
a_n=a_{N-1}\prod_{i=N}^{n}r_i\le a_{N-1}\cdot\frac{r_{N-1}^{\,n-N+1}}{2^{(n-N+1)(n-N)/2}}.
\]
The denominator grows super‑exponentially, so for large \(n\) we have \(a_n<1\). But \(a_n\) is a positive integer, a contradiction.

Thus our initial assumption is false. Therefore there exists some integer \(k\ge0\) such that the polynomial \(\sum_{i=0}^k c_i x^i\) has fewer than \(k\) distinct real roots. ∎
