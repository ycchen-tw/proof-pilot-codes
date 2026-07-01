# PB-Basic-005 — IMO-easy / Algebra

**Score: 7/7** &middot; pipeline output via `select:R0(3/4)`

**Grader note (Claude grader, sympy-verified):** Even function → Q(x²) → coefficient/degree analysis rules out deg≥6 → constant term=6; complete with verification.

## Problem

Let $P$ be a polynomial with real coefficients whose leading coefficient is $1$. Suppose that for all nonzero real numbers $x$, we have $P(x) + P(1/x) = \frac{P(x + 1/x) + P(x - 1/x)}{2}$. Determine all possibilities for $P$.

**Reference short answer:** $P(x)= x^4 +ax^2 +6$, $P(x)=x^2$

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

We are given a polynomial \(P\) with real coefficients and leading coefficient \(1\) such that
\[
P(x)+P(1/x)=\frac{P(x+1/x)+P(x-1/x)}{2}\qquad(\forall x\neq0).
\]
We determine all such polynomials.

---
### 1.  \(P\) is even

Replace \(x\) by \(1/x\) in the given equation.  Because \(x\neq0\), \(1/x\) is also nonzero, so we obtain
\[
P(1/x)+P(x)=\frac{P(1/x+x)+P(1/x-x)}{2}
=\frac{P(x+1/x)+P(-(x-1/x))}{2}.
\]
The left‑hand side is the same as the original left‑hand side, hence
\[
P(x)+P(1/x)=\frac{P(x+1/x)+P(-(x-1/x))}{2}.
\]
Comparing with the original equation gives
\[
P(x-1/x)=P(-(x-1/x))\qquad(\forall x\neq0).
\]

The map \(x\mapsto x-1/x\) is surjective onto \(\mathbb{R}\): for any real \(y\) the equation \(x-1/x=y\) has discriminant \(y^2+4>0\), hence two real solutions, both nonzero.  Therefore \(P(y)=P(-y)\) for every real \(y\); i.e., \(P\) is an **even** polynomial.

---
### 2.  Reduction to a polynomial in \(x^2\)

Since \(P\) is even, we can write \(P(x)=Q(x^{2})\) for some polynomial \(Q\) with real coefficients.  The leading coefficient of \(P\) is \(1\), so if \(\deg P=2d\) then \(\deg Q=d\) and the leading coefficient of \(Q\) is \(1\).  Set
\[
Q(t)=t^{d}+a_{d-1}t^{d-1}+\dots+a_{0},\qquad a_{d}=1.
\]

Substitute \(x^{2}=t>0\) into the original equation.  Using the evenness of \(P\) we have
\[
\begin{aligned}
P(x+1/x)&=Q\bigl((x+1/x)^{2}\bigr)=Q(t+2+1/t),\\
P(x-1/x)&=Q\bigl((x-1/x)^{2}\bigr)=Q(t-2+1/t).
\end{aligned}
\]
Hence
\[
Q(t)+Q(1/t)=\frac{Q(t+2+1/t)+Q(t-2+1/t)}{2}\qquad(\forall t>0).
\]
Multiplying by \(2\) we obtain
\[
2Q(t)+2Q(1/t)=Q(t+2+1/t)+Q(t-2+1/t)\qquad(t>0). \tag{1}
\]

---
### 3.  Introducing \(y=t+1/t\)

Let \(y=t+1/t\) (so \(y\ge2\)).  Then \(t+2+1/t=y+2\) and \(t-2+1/t=y-2\).  
The expression \(Q(t)+Q(1/t)\) is symmetric in \(t\) and \(1/t\); for each integer \(k\ge0\) we have \(t^{k}+t^{-k}\) is a polynomial in \(y\) (Chebyshev polynomials).  Therefore there exists a polynomial \(R\) such that
\[
R(y)=Q(t)+Q(1/t).
\]
Equation (1) becomes
\[
2R(y)=Q(y+2)+Q(y-2)\qquad(\forall y\ge2).
\]
Both sides are polynomials in \(y\), so the equality holds for all real \(y\):
\[
2R(y)=Q(y+2)+Q(y-2)\qquad(\forall y\in\mathbb{R}). \tag{2}
\]

---
### 4.  Degree analysis

Let \(d=\deg Q\) (so \(d\ge0\)).  Write
\[
Q(y)=y^{d}+a_{d-1}y^{d-1}+\dots+a_{0},\qquad a_{d}=1.
\]

We examine the coefficient of \(y^{d-2}\) in (2).  

*Coefficient in \(R(y)\).*  
For any integer \(i\ge0\) set \(s_i(y)=t^{i}+t^{-i}\).  Then \(s_0(y)=2\), \(s_1(y)=y\), and the recurrence \(s_{i+1}=y\,s_i-s_{i-1}\) gives
\[
s_i(y)=y^{i}-i\,y^{i-2}+\text{(lower terms)}\quad(i\ge2).
\]
Thus
\[
R(y)=\sum_{i=0}^{d}a_i s_i(y).
\]
The term \(y^{d-2}\) in \(R(y)\) can only come from:
- \(i=d\): coefficient \(-d\);
- \(i=d-2\): coefficient \(a_{d-2}\) (since \(s_{d-2}\) contributes \(y^{d-2}\) with coefficient \(1\));
- all other \(i\) give either degree \(<d-2\) or no \(y^{d-2}\) term.
Hence, for \(d\ge3\),
\[
\operatorname{coeff}_{y^{d-2}}R(y)=-d+a_{d-2}.
\]
For \(d=2\) we have \(d-2=0\); then
\[
s_2(y)=y^2-2,\qquad s_0(y)=2,
\]
so the constant term of \(R(y)\) is \(2a_0-2\).  For \(d=1\) we treat directly.

*Coefficient in \(Q(y+2)+Q(y-2)\).*  
Expand using the binomial theorem:
\[
(y+2)^{j}+(y-2)^{j}=2y^{j}+4\binom{j}{2}y^{j-2}+\cdots,
\]
where the terms with odd powers of \(2\) cancel.  For \(j=d\) the contribution to \(y^{d-2}\) is \(4\binom{d}{2}y^{d-2}=4d(d-1)y^{d-2}\).  For \(j=d-2\) the contribution is \(2y^{d-2}\).  For \(j=d-1\) the sum contains only terms of parity \(d-1\); the exponent \(d-2\) appears with coefficient \(2(d-1)\) from \((y+2)^{d-1}\) and \(-2(d-1)\) from \((y-2)^{d-1}\), so they cancel.  For \(j\le d-3\) the degree is at most \(d-3\), so they contribute nothing.  Therefore, for \(d\ge2\),
\[
\operatorname{coeff}_{y^{d-2}}\bigl(Q(y+2)+Q(y-2)\bigr)=4d(d-1)+2a_{d-2}.
\]
(For \(d=2\) this gives \(8+2a_0\).)

Now equate the coefficients of \(y^{d-2}\) in (2).

*Case \(d\ge3\):*  
\[
2(-d+a_{d-2})=4d(d-1)+2a_{d-2}\;\Longrightarrow\; -2d=4d(d-1)\;\Longrightarrow\; d=\frac12,
\]
which is impossible for an integer \(d\ge3\).  Hence no solution with \(d\ge3\).

*Case \(d=2\):*  
The constant term (exponent \(0\)) of (2) gives
\[
2(2a_0-2)=8+2a_0\;\Longrightarrow\;4a_0-4=8+2a_0\;\Longrightarrow\;2a_0=12\;\Longrightarrow\;a_0=6.
\]
No condition arises for \(a_1\).  Thus \(Q(y)=y^2+a_1y+6\).

*Case \(d=1\):*  
Write \(Q(y)=y+a_0\).  Then (2) becomes
\[
2(y+2a_0)=(y+2+a_0)+(y-2+a_0)=2y+2a_0,
\]
so \(2y+4a_0=2y+2a_0\;\Longrightarrow\;a_0=0\).  Hence \(Q(y)=y\).

*Case \(d=0\):*  
\(Q(y)=c\) (constant).  Then (2) gives \(4c=2c\Rightarrow c=0\), contradicting the requirement that \(\operatorname{lead}(P)=1\).  Thus \(d=0\) is impossible.

---
### 5.  Back to \(P\)

Since \(P(x)=Q(x^2)\) and \(Q\) is monic:

- For \(d=1\): \(P(x)=x^2\).
- For \(d=2\): \(P(x)=x^4+a_1x^2+6\) with \(a_1\in\mathbb{R}\).

---
### 6.  Verification

Direct substitution confirms that both families satisfy the original equation:

*For \(P(x)=x^2\):*  
\[
P(x)+P(1/x)=x^2+\frac1{x^2},\qquad
\frac{P(x+1/x)+P(x-1/x)}{2}=
\frac{(x+1/x)^2+(x-1/x)^2}{2}=x^2+\frac1{x^2}.
\]

*For \(P(x)=x^4+ax^2+6\):*  
\[
\begin{aligned}
P(x)+P(1/x)&=x^4+\frac1{x^4}+a\Bigl(x^2+\frac1{x^2}\Bigr)+12,\\[2mm]
\frac{P(x+1/x)+P(x-1/x)}{2}&=
\frac12\Bigl((x+1/x)^4+a(x+1/x)^2+6+(x-1/x)^4+a(x-1/x)^2+6\Bigr)\\
&=x^4+\frac1{x^4}+a\Bigl(x^2+\frac1{x^2}\Bigr)+12.
\end{aligned}
\]

Thus both families are solutions.

---
### 7.  Conclusion

All monic polynomials with real coefficients satisfying the given condition are
\[
\boxed{P(x)=x^{2}\quad\text{and}\quad P(x)=x^{4}+c\,x^{2}+6\ \ (c\in\mathbb{R})}.
\]
