# PB-Basic-022 — IMO-easy / Number theory

**Score: 6/7** &middot; pipeline output via `select:R2(4/4)`

**Grader note (Claude grader, sympy-verified):** boxed (x+c)^d / −(x+c)^d, d|2024 matches. The 2-adic valuation T≡0⇒Q=x^d is mostly sound, but part of the contradiction derivation is loosely stated — a minor gap.

## Problem

Let $S=\{0,1,2^{2024},3^{2024},\ldots\}$ be the set of all perfect
 2024-th powers. Find all polynomials $P$ with integer coefficients
 such that $P(x)=s$ has an integer solution $x$ for every $s\in S$.

**Reference short answer:** $P(x) = (x - a)^d or P(x) = (-x - a)^d$, where $d | 2024$.

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

Let \(k=2024\).  We are to determine all polynomials \(P\in\mathbb Z[x]\) such that for every non‑negative integer \(n\) there exists an integer \(x\) with \(P(x)=n^{k}\).

---
### 1.  Normalisation  

Because \(0\in S\) there exists an integer \(a\) with \(P(a)=0\).  Set \(P_1(x)=P(x+a)\); then \(P_1(0)=0\) and the condition still holds.  
Since \(1\in S\) there is an integer \(b\) with \(P_1(b)=1\).  Factor \(P_1(x)=x\,R(x)\) with \(R\in\mathbb Z[x]\) (the constant term is \(0\)).  Then \(b\,R(b)=1\), so \(b=\pm1\).  

*If \(b=1\)* we have \(P_1(1)=1\).  
*If \(b=-1\)* define \(P_2(x)=P_1(-x)\).  Then \(P_2(0)=0\), \(P_2(1)=P_1(-1)=1\) and the condition is preserved (if \(P_1(y)=n^{k}\) then \(P_2(-y)=n^{k}\)).  

Thus, after a possible translation and reflection, we may assume that the polynomial \(Q\) satisfies  

\[
Q(0)=0,\qquad Q(1)=1,\qquad Q\in\mathbb Z[x],
\]

and for every \(n\ge0\) there exists an integer \(x\) with \(Q(x)=n^{k}\).

---
### 2.  Degree and leading coefficient  

\(Q\) is non‑constant (otherwise it could not take infinitely many values).  Let \(d=\deg Q\) and write \(Q(x)=a_d x^{d}+a_{d-1}x^{d-1}+\cdots+a_0\) with \(a_d\neq0\).  Because \(Q\) attains arbitrarily large positive values (it contains all \(n^{k}\)), the leading coefficient must be positive (if it were negative we could replace \(Q\) by \(Q(-x)\) and the condition still holds).  Hence \(a_d>0\).

---
### 3.  Using powers of two  

For each integer \(r\ge1\) let \(n=2^{r}\).  By the hypothesis there exists an integer \(x_r\) with  

\[
Q(x_r)=2^{rk}.
\]

Because \(Q(x)=x\,R(x)\) and \(R(1)=1\), we have \(x_r\mid 2^{rk}\).  Consequently  

\[
|x_r|=2^{a_r}\quad\text{for some integer }a_r\ge0.
\]

Now choose a number \(M\) large enough so that for all \(|x|\ge M\) the following bounds hold:

\[
\frac{a_d}{2}\,|x|^{d}\le |Q(x)|\le 2a_d\,|x|^{d}.
\]

(Indeed, for \(|x|\) large the lower‑order terms are dominated by \(\frac{a_d}{2}|x|^{d}\); the upper bound follows because the sum of the lower terms is eventually at most \(a_d|x|^{d}\).)  
For all sufficiently large \(r\) we have \(a_r\ge M\) (since \(|x_r|=2^{a_r}\to\infty\)), therefore  

\[
\frac{a_d}{2}\,2^{d a_r}\le 2^{rk}\le 2a_d\,2^{d a_r}.
\]

Taking base‑\(2\) logarithms gives  

\[
d a_r+\log_2\frac{a_d}{2}\le rk\le d a_r+\log_2(2a_d).
\]

Thus the integer sequence \(rk-d a_r\) is bounded.  Hence there exists an integer \(t\) such that  

\[
rk-d a_r=t\qquad\text{for infinitely many }r.
\]

---
### 4.  The key factorisation  

Because \(Q(0)=0\) and \(Q(1)=1\), the polynomial \(Q(x)-x^{d}\) vanishes at \(x=0\) and \(x=1\); therefore  

\[
Q(x)-x^{d}=x(x-1)\,T(x) \qquad\text{with }T\in\mathbb Z[x].
\]

Substitute \(x=x_r\).  Write \(x_r=\varepsilon\,2^{a_r}\) with \(\varepsilon=\pm1\).  Then  

\[
Q(x_r)-x_r^{d}=2^{rk}-\varepsilon^{d}2^{d a_r}=2^{d a_r}\bigl(2^{t}-\varepsilon^{d}\bigr).
\]

On the other hand  

\[
x_r(x_r-1)=(\varepsilon2^{a_r})(\varepsilon2^{a_r}-1)=2^{a_r}(2^{a_r}-\varepsilon).
\]

Thus  

\[
2^{a_r}(2^{a_r}-\varepsilon)\,T(x_r)=2^{d a_r}\bigl(2^{t}-\varepsilon^{d}\bigr).
\]

Dividing by \(2^{a_r}\) we obtain  

\[
(2^{a_r}-\varepsilon)\,T(x_r)=2^{(d-1)a_r}\bigl(2^{t}-\varepsilon^{d}\bigr). \tag{1}
\]

---
### 5.  Analysing the sign  

We consider two cases.

*Case \(\varepsilon=1\):*  Then (1) becomes  

\[
(2^{a_r}-1)\,T(2^{a_r})=2^{(d-1)a_r}(2^{t}-1).
\]

Since \(2^{a_r}-1\) is odd, it must divide \(2^{t}-1\).  If \(t\neq0\) then \(2^{t}-1\neq0\) and for large \(a_r\) the left‑hand side would be a factor of a fixed non‑zero integer, which is impossible.  Hence \(t=0\).  Then the equation reduces to \((2^{a_r}-1)T(2^{a_r})=0\), so \(T(2^{a_r})=0\) for infinitely many \(a_r\).  Therefore \(T\) is the zero polynomial and \(Q(x)=x^{d}\).  From \(t=0\) we also get \(a_r=rk/d\), which forces \(d\mid k\).

*Case \(\varepsilon=-1\):*  Then (1) becomes  

\[
(2^{a_r}+1)\,T(-2^{a_r})=2^{(d-1)a_r}\bigl(2^{t}-(-1)^{d}\bigr).
\]

If \(d\) is even, \((-1)^{d}=1\) and the same argument as above shows that \(2^{t}-1=0\), so \(t=0\) and consequently \(T\equiv0\).  
If \(d\) is odd, \((-1)^{d}=-1\) and we obtain  

\[
(2^{a_r}+1)\,T(-2^{a_r})=2^{(d-1)a_r}\bigl(2^{t}+1\bigr).
\]

Now \(2^{a_r}+1\) is odd and divides \(2^{t}+1\).  For large \(a_r\) this forces \(2^{t}+1=0\), which is impossible.  Hence for odd \(d\) the case \(\varepsilon=-1\) can occur only for finitely many \(r\).  Consequently, among the infinitely many \(r\) with the same \(t\), all but finitely many satisfy \(\varepsilon=1\); for those we are back in the first situation and again obtain \(Q(x)=x^{d}\) with \(d\mid k\).

Thus in every case we have proved that  

\[
Q(x)=x^{d},\qquad d\mid k.
\]

---
### 6.  Reversing the normalisation  

Recall that \(Q\) was obtained from the original polynomial \(P\) by a translation (and possibly a reflection).  

* If no reflection was used, then \(P(x)=Q(x-c)=(x-c)^{d}\) for some integer \(c\).  
* If a reflection was used, then \(P_2(x)=Q(x)\) and \(P_1(x)=P_2(-x)=(-x)^{d}=(-1)^{d}x^{d}\), so \(P(x)=P_1(x-a)=(-1)^{d}(x-a)^{d}\).

Therefore every admissible polynomial is of the form  

\[
P(x)=\varepsilon\,(x+c)^{d},
\]

with \(c\in\mathbb Z\), \(d\mid k\), and \(\varepsilon=\pm1\).  Moreover, if \(\varepsilon=-1\) then \(d\) must be odd (because otherwise \((-1)^{d}=1\) and the sign is irrelevant).  Conversely, for any divisor \(d\) of \(2024\) and any integer \(c\), the polynomials \((x+c)^{d}\) and, when \(d\) is odd, \(-(x+c)^{d}\) satisfy the required property: for \(n\ge0\) take \(x=n^{k/d}-c\) (or \(x=-n^{k/d}-c\) in the negative case) to obtain \(P(x)=n^{k}\).

---
### 7.  Conclusion  

All polynomials \(P\) with integer coefficients such that for every perfect \(2024\)-th power \(s\) the equation \(P(x)=s\) has an integer solution are exactly  

\[
\boxed{P(x)=(x+c)^{d}\quad\text{or}\quad P(x)=-(x+c)^{d}}
\]

where \(c\in\mathbb Z\), \(d\) is a positive divisor of \(2024\), and in the second case \(d\) is odd.
