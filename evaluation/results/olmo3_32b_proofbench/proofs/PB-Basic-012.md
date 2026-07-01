# PB-Basic-012 — IMO-medium / Combinatorics

**Score: 7/7** &middot; pipeline output via `select:R2(4/4)`

**Grader note (Claude grader, sympy-verified):** f(10)=5924217936 が reference と一致、Dyck 語+Vandermonde 導出を n=1..5 brute で裏付け

## Problem

Consider a positive integer $n$. We define $f(n)$ as the number of pairs of paths on an $n \times n$ grid that:

 (1) Both paths start at $(0, 0)$ (bottom left corner) and end at $(n, n)$ (top right corner).

 (2) Both paths allow only right or up movements (one unit each).

 (3) The $y$ coordinate of the first path never exceeds the y coordinate of the second path at any timestep.

 For example, when $n = 2$, consider the following pair of paths:

 The first path: $(0,0) \rightarrow (1,0) \rightarrow (1,1) \rightarrow (2,1) \rightarrow (2,2)$
 The second path: $(0,0) \rightarrow (1,0) \rightarrow (2,0) \rightarrow (2,1) \rightarrow(2,2)$
 The example is invalid because after 2 steps, the y coordinate of the first path (1) is larger than the y coordinate of the second path (0).

 However, the following example is valid,

 The first path: $(0,0) \rightarrow (1,0) \rightarrow (2,0) \rightarrow (2,1) \rightarrow (2,2)$
 The second path: $(0,0) \rightarrow (1,0) \rightarrow (1,1) \rightarrow (2,1) \rightarrow (2,2)$

 since the y coordinate of the first path is never larger than the second path. Find $f(10)$.

**Reference short answer:** $\binom{20}{10}^2 - \binom{20}{9}^2$

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

Let \(n\) be a positive integer. A path from \((0,0)\) to \((n,n)\) using steps \((1,0)\) (right) and \((0,1)\) (up) is determined by a sequence of \(2n\) steps containing exactly \(n\) rights and \(n\) ups. For two such paths \(P\) (first) and \(Q\) (second), let \(y_P(k)\) and \(y_Q(k)\) be the \(y\)-coordinates after \(k\) steps (\(k=0,\dots,2n\)). The condition is \(y_P(k)\le y_Q(k)\) for all \(k\).

Define \(d(k)=y_Q(k)-y_P(k)\). Then \(d(0)=d(2n)=0\) and \(d(k)\ge0\) for all \(k\).

Now consider the step types:

- Both right: \((R,R)\) → \(d\) unchanged.
- Both up: \((U,U)\) → \(d\) unchanged.
- \(P\) right, \(Q\) up: \((R,U)\) → \(d\) increases by \(1\).
- \(P\) up, \(Q\) right: \((U,R)\) → \(d\) decreases by \(1\).

Let \(a\) be the number of \((R,U)\) steps. Because each path has exactly \(n\) up steps, the number of \((U,U)\) steps must be \(n-a\) (since \(Q\) has \(n\) up steps, and \(a\) of them are paired with \(R\) from \(P\)). Similarly, the number of \((U,R)\) steps must also be \(n-a\) (because \(P\) has \(n\) up steps, and the remaining \(n-a\) after the \((U,U)\) steps are paired with \(R\) from \(Q\)). Hence the number of \((R,R)\) steps is also \(n-a\). The total number of steps is \(2n\), consistent.

Thus the sequence of \(\Delta d\) consists of \(a\) \(+1\)'s, \(a\) \(-1\)'s, and \(2(n-a)\) zeros. The condition \(d(k)\ge0\) for all \(k\) is equivalent to the subsequence of \(+1\) and \(-1\) (ignoring zeros) being a Dyck word: a sequence of \(a\) up steps and \(a\) down steps that never goes below zero. The number of such Dyck words of length \(2a\) is the Catalan number
\[
C_a = \frac{1}{a+1}\binom{2a}{a}.
\]

Now we count the number of sequences of step types that correspond to a given Dyck word. The \(2a\) non‑zero steps (the Dyck word) must be placed among the \(2n\) positions. Choose the positions for them in \(\binom{2n}{2a}\) ways. The Dyck word is then placed in these positions in its predetermined order (1 way). The remaining \(2n-2a\) positions are filled with the zero steps: \(n-a\) of type \((R,R)\) and \(n-a\) of type \((U,U)\). The number of ways to assign these types is \(\binom{2n-2a}{n-a}\). Hence for each Dyck word we obtain
\[
\binom{2n}{2a}\binom{2n-2a}{n-a}
\]
sequences.

Summing over all \(a\) from \(0\) to \(n\) gives
\[
f(n)=\sum_{a=0}^{n} C_a \binom{2n}{2a}\binom{2n-2a}{n-a}.
\]

Simplify the term. Using factorials,
\[
\binom{2n}{2a}\binom{2n-2a}{n-a}
= \frac{(2n)!}{(2a)!\,(2n-2a)!}\cdot\frac{(2n-2a)!}{(n-a)!\,(n-a)!}
= \frac{(2n)!}{(2a)!\,(n-a)!^2}.
\]
Also \(C_a = \frac{1}{a+1}\binom{2a}{a} = \frac{1}{a+1}\frac{(2a)!}{a!\,a!}\). Therefore
\[
f(n)=\sum_{a=0}^{n} \frac{(2n)!}{(2a)!\,(n-a)!^2}\cdot\frac{1}{a+1}\frac{(2a)!}{a!\,a!}
= (2n)!\sum_{a=0}^{n}\frac{1}{(a+1)\,a!^2\,(n-a)!^2}.
\]
Write \((2n)!/(n!^2)=\binom{2n}{n}\) and \(n!^2/(a!^2\,(n-a)!^2)=\binom{n}{a}^2\). Hence
\[
f(n)=\binom{2n}{n}\sum_{a=0}^{n}\frac{\binom{n}{a}^2}{a+1}.
\]

Now evaluate the sum \(S=\sum_{a=0}^{n}\frac{\binom{n}{a}^2}{a+1}\). Using the identity \(\frac{\binom{n}{a}}{a+1}=\frac{\binom{n+1}{a+1}}{n+1}\), we get
\[
S=\frac{1}{n+1}\sum_{a=0}^{n}\binom{n}{a}\binom{n+1}{a+1}.
\]
Change index \(k=a+1\) (so \(k=1,\dots,n+1\)):
\[
\sum_{a=0}^{n}\binom{n}{a}\binom{n+1}{a+1}
= \sum_{k=1}^{n+1}\binom{n}{k-1}\binom{n+1}{k}.
\]
By symmetry \(\binom{n}{k-1}=\binom{n}{n+1-k}\). Let \(j=n+1-k\); then the sum becomes
\[
\sum_{j=0}^{n+1}\binom{n}{j}\binom{n+1}{n+1-j}
= \sum_{j=0}^{n+1}\binom{n}{j}\binom{n+1}{j},
\]
where we used \(\binom{n+1}{n+1-j}=\binom{n+1}{j}\). Vandermonde’s identity gives
\[
\sum_{j=0}^{n+1}\binom{n}{j}\binom{n+1}{j}=\binom{2n+1}{n+1}.
\]
Thus \(S=\frac{1}{n+1}\binom{2n+1}{n+1}\).

Substituting back,
\[
f(n)=\binom{2n}{n}\cdot\frac{1}{n+1}\binom{2n+1}{n+1}.
\]
Since \(\binom{2n+1}{n+1}=\frac{2n+1}{n+1}\binom{2n}{n}\), we obtain the compact form
\[
f(n)=\frac{2n+1}{(n+1)^2}\binom{2n}{n}^2.
\]

For \(n=10\):
\[
\binom{20}{10}=184756,\qquad \binom{20}{10}^2=34\,134\,779\,536,\qquad
\frac{2\cdot10+1}{(10+1)^2}=\frac{21}{121}.
\]
Hence
\[
f(10)=\frac{21}{121}\cdot34\,134\,779\,536
=21\cdot282\,105\,616
=5\,924\,217\,936.
\]

Thus \(f(10)=\boxed{5924217936}\).
