# PB-Basic-008 — pre-IMO / Algebra

**Score: 7/7** &middot; pipeline output via `select:R2(3/4)`

**Grader note (Claude grader, sympy-verified):** 不等式を乱択検証、Schur・因数分解・k(√2)=3√6-3>0 を全て sympy で厳密一致

## Problem

Let $a,b,c$ be positive reals such that $a+b+c = 1$, prove that $\sqrt{a}+\sqrt{b}+\sqrt{c} \geq 3\sqrt{3}(ab+bc+ca)$.

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

Let \(a,b,c>0\) with \(a+b+c=1\).  Set  
\[
x=\sqrt{a},\;y=\sqrt{b},\;z=\sqrt{c}.
\]  
Then \(x,y,z>0\) and \(x^{2}+y^{2}+z^{2}=1\).  The required inequality becomes  
\[
x+y+z \ge 3\sqrt3\,(x^{2}y^{2}+y^{2}z^{2}+z^{2}x^{2}). \tag{1}
\]

Denote  
\[
s=x+y+z,\qquad p=xy+yz+zx,\qquad r=xyz.
\]  
From \(x^{2}+y^{2}+z^{2}=s^{2}-2p=1\) we obtain  
\[
p=\frac{s^{2}-1}{2}. \tag{2}
\]  
Moreover,  
\[
x^{2}y^{2}+y^{2}z^{2}+z^{2}x^{2}=p^{2}-2rs,
\]  
so (1) is equivalent to  
\[
s \ge 3\sqrt3\,(p^{2}-2rs)\quad\Longleftrightarrow\quad s+6\sqrt3\,rs \ge 3\sqrt3\,p^{2}. \tag{3}
\]

By Cauchy–Schwarz,  
\[
s^{2}\le 3(x^{2}+y^{2}+z^{2})=3,\qquad s^{2}\ge x^{2}+y^{2}+z^{2}=1,
\]  
hence \(1\le s\le\sqrt3\).

---

### Case 1: \(1\le s\le\sqrt2\)

Since \(r\ge0\), we have \(s+6\sqrt3\,rs\ge s\).  Thus it is enough to prove  
\[
s \ge 3\sqrt3\,p^{2}= \frac{3\sqrt3}{4}(s^{2}-1)^{2}. \tag{4}
\]  
For \(s^{2}\le2\) we have \(0\le s^{2}-1\le1\), so \((s^{2}-1)^{2}\le s^{2}-1\).  Therefore it suffices to show  
\[
s \ge \frac{3\sqrt3}{4}(s^{2}-1).
\]  
Rearranging gives  
\[
3\sqrt3\,s^{2}-4s-3\sqrt3\le0.
\]  
The quadratic has its positive root \(\frac{2+\sqrt{31}}{3\sqrt3}\approx1.456\).  Because \(s\le\sqrt2<1.456\), the quadratic is negative, so the inequality holds.  Hence (4) is true, and consequently (3) holds in this case.

---

### Case 2: \(\sqrt2\le s\le\sqrt3\)

We use Schur’s inequality for non‑negative numbers:  
\[
x^{3}+y^{3}+z^{3}+3xyz \ge \sum_{\text{sym}}x^{2}y.
\]  
In terms of \(s,p,r\) this is equivalent to  
\[
s^{3}+9r \ge 4sp. \tag{5}
\]  
(Indeed, \(\sum x^{3}=s^{3}-3sp+3r\) and \(\sum_{\text{sym}}x^{2}y=sp-3r\).)  
From (2) we have \(p=(s^{2}-1)/2\), so (5) yields  
\[
s^{3}+9r \ge 4s\cdot\frac{s^{2}-1}{2}=2s(s^{2}-1),
\]  
i.e.  
\[
9r \ge 2s^{3}-2s \quad\Longrightarrow\quad r \ge \frac{s(s^{2}-2)}{9}. \tag{6}
\]  
Because \(s\ge\sqrt2\), the right‑hand side is non‑negative.

Since the left‑hand side of (3) is increasing in \(r\), we may replace \(r\) by the lower bound (6):  
\[
s+6\sqrt3\,rs \ge s+6\sqrt3\,s\cdot\frac{s(s^{2}-2)}{9}=s+\frac{2\sqrt3}{3}s^{2}(s^{2}-2).
\]  
Hence it is sufficient to prove  
\[
s+\frac{2\sqrt3}{3}s^{2}(s^{2}-2) \ge \frac{3\sqrt3}{4}(s^{2}-1)^{2}. \tag{7}
\]

Multiply by \(12\):  
\[
12s+8\sqrt3\,s^{2}(s^{2}-2) \ge 9\sqrt3\,(s^{2}-1)^{2}.
\]  
Expanding and simplifying:  
\[
12s+8\sqrt3\,s^{4}-16\sqrt3\,s^{2} \ge 9\sqrt3\,(s^{4}-2s^{2}+1)=9\sqrt3\,s^{4}-18\sqrt3\,s^{2}+9\sqrt3,
\]  
\[
12s-\sqrt3\,s^{4}+2\sqrt3\,s^{2}-9\sqrt3 \ge 0,
\]  
or equivalently  
\[
\sqrt3\,s^{4}-2\sqrt3\,s^{2}-12s+9\sqrt3 \le 0. \tag{8}
\]

Factor the left‑hand side:  
\[
\sqrt3\,s^{4}-2\sqrt3\,s^{2}-12s+9\sqrt3=(s-\sqrt3)(\sqrt3\,s^{3}+3s^{2}+\sqrt3\,s-9). \tag{9}
\]  
For \(s\in[\sqrt2,\sqrt3]\) we have \(s-\sqrt3\le0\).  Consider the cubic  
\[
k(s)=\sqrt3\,s^{3}+3s^{2}+\sqrt3\,s-9.
\]  
Its derivative \(k'(s)=3\sqrt3\,s^{2}+6s+\sqrt3>0\) for all \(s>0\); thus \(k\) is strictly increasing.  Since  
\[
k(\sqrt2)=\sqrt3\cdot2\sqrt2+3\cdot2+\sqrt3\cdot\sqrt2-9=3\sqrt6-3>0,
\]  
we have \(k(s)>0\) for every \(s\ge\sqrt2\).  Therefore the product in (9) is \(\le0\), so (8) holds.  This establishes (7), and consequently (3) for \(\sqrt2\le s\le\sqrt3\).

---

Both cases cover the whole interval \(1\le s\le\sqrt3\); hence (3) is true for all non‑negative \(x,y,z\) with \(x^{2}+y^{2}+z^{2}=1\).  Returning to the original variables, we obtain  
\[
\sqrt{a}+\sqrt{b}+\sqrt{c} \ge 3\sqrt3\,(ab+bc+ca),
\]  
as required.  

Equality occurs when \(s=\sqrt3\) and all inequalities used become equalities.  From (6) this forces \(r=\frac{s(s^{2}-2)}{9}}=\frac{\sqrt3}{9}\), and Schur’s equality condition together with \(x,y,z>0\) implies \(x=y=z\).  Then \(x=y=z=1/\sqrt3\), i.e. \(a=b=c=1/3\).  Substituting gives \(3\sqrt{1/3}= \sqrt3\) and \(3\sqrt3\cdot3\cdot\frac19=\sqrt3\), so equality holds.  ∎
