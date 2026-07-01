# PB-Advanced-025 — IMO-easy / Number theory

**Score: 7/7** &middot; pipeline output via `select:R0(3/4)`

**Grader note (Claude grader, sympy-verified):** Fully self-contained: the greedy expansion, the r_i induction, a_i≥⌊n/2^(k-i)⌋, and the choice of N are all computationally verified.

## Problem

Let $k$ and $d$ be positive integers. Prove that there exists a
 positive integer $N$ such that for every odd integer $n>N$, the
 digits in the base-$2n$ representation of $n^{k}$ are all greater
 than $d$.

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

Let \(k,d\) be positive integers. We prove that there exists a positive integer \(N\) such that for every odd integer \(n>N\) the base-\(2n\) representation of \(n^{k}\) has all digits greater than \(d\).

**Case \(k=1\).**  
Then \(n^{k}=n\) and the base-\(2n\) representation of \(n\) is simply the single digit \(n\) (since \(n<2n\)). Choose \(N = d+1\). For any odd integer \(n>N\) we have \(n\ge d+3>d\), so the digit is \(>d\). The statement holds for \(k=1\).

**Case \(k\ge 2\).**  
Set \(B=2n\). Because \(n\) is odd, \(B\) is even. Observe that
\[
n^{k} = \frac{(2n)^{k}}{2^{k}}.
\]
The rational number \(\frac1{2^{k}}\) has a terminating base-\(B\) expansion because \(B^{k}\cdot\frac1{2^{k}}=n^{k}\) is an integer. Write
\[
\frac1{2^{k}} = \sum_{i=1}^{k} a_i B^{-i},\qquad 0\le a_i<B,
\]
where the digits are obtained by the greedy algorithm. Multiplying by \(B^{k}\) gives
\[
n^{k} = \sum_{i=1}^{k} a_i B^{\,k-i}.
\]
Hence the base-\(B\) digits of \(n^{k}\) are exactly \(a_{1},a_{2},\dots ,a_{k}\) (in that order, from most significant to least).

Now compute the \(a_i\) by the greedy algorithm. Let \(x_{0}=1/2^{k}\). For \(i=1,\dots ,k\) define
\[
a_i = \bigl\lfloor B x_{i-1}\bigr\rfloor,\qquad x_i = B x_{i-1} - a_i.
\]
Then \(x_k=0\).

We claim that for \(i=1,\dots ,k\),
\[
a_i \ge \bigl\lfloor \frac{n}{2^{k-i}}\bigr\rfloor.
\]
Moreover, \(a_k = n\).

*Proof of the claim.*  We prove by induction that for \(i=0,1,\dots ,k-1\),
\[
x_i = \frac{r_i}{2^{k-i}},\qquad\text{where } r_i \text{ is odd and } 1\le r_i < 2^{k-i},
\]
with \(r_0=1\) (since \(x_0=1/2^{k}\)).  The case \(i=0\) is true.  Assume the statement holds for some \(i\le k-2\).  Then
\[
B x_i = 2n\cdot \frac{r_i}{2^{k-i}} = \frac{n r_i}{2^{k-i-1}}.
\]
Set \(a_{i+1}= \bigl\lfloor n r_i/2^{k-i-1}\bigr\rfloor\) and let
\[
r_{i+1} = n r_i - 2^{k-i-1}a_{i+1} = n r_i \bmod 2^{k-i-1}.
\]
Because \(n\) and \(r_i\) are odd, \(n r_i\) is odd.  For \(i\le k-2\) we have \(2^{k-i-1}\ge 2\), so the modulus is even.  An odd number modulo an even number is odd and non‑zero; consequently \(r_{i+1}\) is odd and satisfies \(1\le r_{i+1}<2^{k-i-1}\).  Thus the induction hypothesis holds for \(i+1\).  For \(i=k-1\) we have \(2^{k-(k-1)}=2\), so the same argument gives \(r_{k-1}=1\) (odd and \(<2\)).  Then
\[
a_k = \bigl\lfloor B x_{k-1}\bigr\rfloor = \bigl\lfloor 2n\cdot\frac{1}{2}\bigr\rfloor = n.
\]

Now for any \(i=1,\dots ,k\),
\[
a_i = \bigl\lfloor B x_{i-1}\bigr\rfloor
      = \bigl\lfloor 2n\cdot\frac{r_{i-1}}{2^{k-i+1}}\bigr\rfloor
      = \bigl\lfloor \frac{n\,r_{i-1}}{2^{k-i}}\bigr\rfloor.
\]
Since \(r_{i-1}\ge 1\), we obtain
\[
a_i \ge \bigl\lfloor \frac{n}{2^{k-i}}\bigr\rfloor.
\]
This proves the claim.

Therefore the digits of \(n^{k}\) in base \(2n\) satisfy
\[
a_i \ge \bigl\lfloor \frac{n}{2^{k-i}}\bigr\rfloor \qquad (i=1,\dots ,k).
\]
In particular, the smallest bound is for \(i=1\):
\[
a_1 \ge \bigl\lfloor \frac{n}{2^{k-1}}\bigr\rfloor.
\]

Now choose
\[
N = (d+1)2^{k-1}+1.
\]
(For \(k\ge2\), \(2^{k-1}\) is even, so \(N\) is odd.)  Let \(n\) be any odd integer with \(n>N\).  Then
\[
n \ge N+2 = (d+1)2^{k-1}+3 > (d+1)2^{k-1},
\]
so
\[
\bigl\lfloor \frac{n}{2^{k-1}}\bigr\rfloor \ge d+1.
\]
Consequently, for every \(i=1,\dots ,k\),
\[
a_i \ge d+1 > d.
\]
Thus all digits of \(n^{k}\) in base \(2n\) are greater than \(d\).

This completes the proof for \(k\ge2\).  Together with the trivial case \(k=1\), the statement is proved for all positive integers \(k,d\). ∎
