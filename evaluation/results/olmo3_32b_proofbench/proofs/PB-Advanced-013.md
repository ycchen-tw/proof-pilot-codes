# PB-Advanced-013 — IMO-easy / Algebra

**Score: 1/7** &middot; pipeline output via `select:R0(3/4)`

**Grader note (Claude grader, sympy-verified):** 不等式と等号点は正しいが Lagrange「最小は内部」を非紧集で未証・臨界点=最小も未証、Step3 算式も誤り

## Problem

For an integer $n \geq 2$, let $a_{1} \leq a_{2} \leq \cdots \leq a_{n}$ be positive real numbers satisfying $a_{1} a_{2} \cdots a_{n}=1$. For each $k=1,2, \cdots, n$, define $b_{k}=2^{k}\left(1+a_{k}^{2^{k}}\right)$. Prove that the following inequality holds:

 \[
 \frac{1}{2}-\frac{1}{2^{n+1}} \leq \frac{1}{b_{1}}+\frac{1}{b_{2}}+\cdots+\frac{1}{b_{n}}
 \]

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

We prove the inequality by analyzing the minimum of the left‑hand side.

Let \(a_1\le a_2\le\cdots\le a_n\) be positive real numbers with \(\prod_{k=1}^n a_k =1\).  
Define
\[
S = \sum_{k=1}^n \frac{1}{2^k(1+a_k^{2^k})}.
\]
We shall show that \(S\ge \frac12-\frac1{2^{n+1}}\).

**1.  Existence of a minimum.**  
If some \(a_k\to0\) then, because the sequence is non‑decreasing, we have \(a_1\le a_k\to0\) and the first term of \(S\) tends to \(\frac{1}{2(1+0)}=\frac12\). All other terms are positive, so \(S>\frac12\).  
If some \(a_k\to\infty\) then the product condition forces some \(a_j\to0\), and again \(S>\frac12\).  
The value at the point \(a_1=\cdots=a_n=1\) is \(\sum_{k=1}^n\frac1{2^{k+1}}=\frac12-\frac1{2^{n+1}}<\frac12\).  
Hence the minimum of \(S\) over the admissible set is attained at an interior point where all \(a_k\) are strictly positive and bounded away from \(0\) and \(\infty\); we may therefore apply the method of Lagrange multipliers.

**2.  Lagrange multiplier conditions.**  
Consider the Lagrangian
\[
L = \sum_{k=1}^n \frac{1}{2^k(1+a_k^{2^k})} - \lambda\sum_{k=1}^n \ln a_k.
\]
For a critical point we have \(\frac{\partial L}{\partial a_k}=0\) for every \(k\):
\[
-\frac{1}{2^k}\cdot\frac{2^k a_k^{2^k-1}}{(1+a_k^{2^k})^2} - \frac{\lambda}{a_k}=0
\quad\Longrightarrow\quad
\frac{a_k^{2^k}}{(1+a_k^{2^k})^2}= -\lambda.
\]
Thus for each \(k\) the number \(t_k = a_k^{2^k}\) satisfies
\[
\frac{t_k}{(1+t_k)^2}=c,
\]
where \(c=-\lambda\) is the same constant for all \(k\).  
The function \(\varphi(t)=\frac{t}{(1+t)^2}\) is strictly increasing on \((0,1]\) and strictly decreasing on \([1,\infty)\), with maximum \(\varphi(1)=\frac14\); moreover \(\varphi(t)=\varphi(1/t)\).  
Hence the equation \(\varphi(t)=c\) has at most two solutions: one in \((0,1]\) and one in \([1,\infty)\), unless \(c=\frac14\) in which case the only solution is \(t=1\). Consequently each \(t_k\) is either \(r\) or \(\frac1r\) for some \(r>0\). Therefore
\[
a_k = r^{\,1/2^k}\quad\text{or}\quad a_k = r^{-1/2^k}.
\]

**3.  Ordering and product condition.**  
Because the sequence \((a_k)\) is non‑decreasing and the exponents \(1/2^k\) are decreasing, the only way to maintain the order is that the smaller values are of the form \(r^{-1/2^k}\) and the larger values are of the form \(r^{1/2^k}\). Hence there exists an integer \(p\ge0\) such that
\[
a_k = r^{-1/2^k}\;\text{for }k\le p,\qquad
a_k = r^{\,1/2^k}\;\text{for }k>p,
\]
with the understanding that the case \(p=0\) means all \(a_k = r^{1/2^k}\) and the case \(p=n\) means all \(a_k = r^{-1/2^k}\).  
The product condition gives
\[
\sum_{k=1}^n \frac{\ln a_k}{2^k}
= \sum_{k=1}^p \frac{(-\ln r)}{2^k} + \sum_{k=p+1}^n \frac{\ln r}{2^k}
= \Bigl(\sum_{k=p+1}^n \frac1{2^k} - \sum_{k=1}^p \frac1{2^k}\Bigr)\ln r =0.
\]
Thus either \(\ln r=0\) (so \(r=1\) and all \(a_k=1\)) or the two sums are equal.  
The total sum \(\sum_{k=1}^n 1/2^k = 1-1/2^n\). The equality of the two sums would require
\[
\sum_{k=p+1}^n \frac1{2^k} = \sum_{k=1}^p \frac1{2^k} = \frac12\Bigl(1-\frac1{2^n}\Bigr) = \frac{2^n-1}{2^{n+1}}.
\]
The left‑hand side is \(\frac{2^{n-p}-1}{2^{n+1}}\) (for \(p\ge1\)). For \(n\ge2\) the number \(2^n-1\) is odd, while \(2^{n-p}-1\) is also odd, but the equality \(\frac{2^{n-p}-1}{2^{n+1}} = \frac{2^n-1}{2^{n+1}}\) would imply \(2^{n-p}=2^n\), i.e. \(p=0\). Since \(p\ge1\) (if there is any negative exponent), this is impossible. Hence the only possibility is \(\ln r=0\), so \(r=1\) and consequently all \(a_k=1\).

**4.  Conclusion.**  
The only interior critical point is \(a_1=\cdots=a_n=1\). At this point
\[
S = \sum_{k=1}^n \frac1{2^{k+1}} = \frac12-\frac1{2^{n+1}}.
\]
Because the minimum is attained in the interior and the only critical point gives this value, we have
\[
S \ge \frac12-\frac1{2^{n+1}}
\]
for all admissible \(a_k\). Equality holds precisely when \(a_1=\cdots=a_n=1\).

∎
