# PB-Basic-007 — IMO-medium / Algebra

**Score: 7/7** &middot; pipeline output via `select:R1(2/4)`

**Grader note (Claude grader, sympy-verified):** n=2 の (-1,1,3) 唯一性を brute 確認；M≤1 境界・n≥3 の Q(x) walk-back も妥当

## Problem

Determine all positive integers $n$ and integer sequences $a_0, a_1,\ldots, a_n$ such that $a_n = 3$ and
 \[f(a_{i-1}) = a_i\]
 for all $i = 1,2,\ldots,n$, where $f(x) = a_n x^n + a_{n-1} x^{n-1} + \cdots + a_1 x + a_0$.

**Reference short answer:** $n=2$ with $\left(a_{0}, a_{1}, a_{2}\right)=(-1,1,3)$

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

We determine all positive integers \(n\) and integer sequences \(a_0,a_1,\dots ,a_n\) with \(a_n=3\) such that
\[
f(a_{i-1})=a_i\qquad (i=1,2,\dots ,n),
\]
where \(f(x)=a_nx^n+a_{n-1}x^{n-1}+\cdots +a_1x+a_0\).

---
### 1.  The case \(n=1\)

Here \(f(x)=3x+a_0\) and \(a_1=f(a_0)=3a_0+a_0=4a_0\).  Since \(a_1=3\), we obtain \(4a_0=3\), which has no integer solution.  Hence no solution for \(n=1\).

---
### 2.  Bounding the coefficients for \(n\ge 2\)

Let \(M=\max\{|a_0|,|a_1|,\dots ,|a_{n-1}|\}\).  We show that \(M\le 1\).

Suppose \(M\ge 2\).  Choose the smallest index \(k\) with \(|a_k|=M\) (such an index exists because the maximum is attained).  For every \(j<k\) we have \(|a_j|<M\).  From the recurrence for \(a_{k+1}\),
\[
|a_{k+1}| = |f(a_k)|
\ge 3|a_k|^n - \sum_{j=0}^{n-1}|a_j|\,|a_k|^j
\ge 3M^n - M\sum_{j=0}^{n-1}M^j
= 3M^n - M\frac{M^n-1}{M-1}
= \frac{M(2M^n-3M^{n-1}+1)}{M-1}.
\]
For \(M\ge 2\) the right‑hand side is strictly larger than \(M\) (e.g. for \(M=2\) it is \(2^{n+1}+2>2\); for \(M=3\) it is \((3^{n+1}+3)/2>3\); for larger \(M\) it is even larger).  Hence \(|a_{k+1}|>M\), contradicting the maximality of \(M\).  Therefore the maximum cannot be attained at any index \(k<n-1\); it must be attained at \(k=n-1\).  Thus \(M=|a_{n-1}|\).

Now apply the same inequality with \(x=a_{n-1}\) (using that all \(|a_j|\le M\)):
\[
|f(a_{n-1})| \ge 3M^n - M\frac{M^n-1}{M-1}
= \frac{M(2M^n-3M^{n-1}+1)}{M-1}.
\]
For \(M\ge 2\) this expression exceeds \(3\), but \(|f(a_{n-1})|=|3|=3\).  Hence \(M\) cannot be \(\ge 2\); therefore \(M\le 1\).

Consequently
\[
|a_i|\le 1\qquad\text{for all } i=0,1,\dots ,n-1.
\]

In particular \(a_{n-1}\in\{-1,0,1\}\).  If \(a_{n-1}=0\) then \(f(0)=a_0=3\), contradicting \(|a_0|\le 1\).  Thus
\[
a_{n-1}\in\{1,-1\}.
\]

---
### 3.  The factorization and the first consequences

Let \(b=a_{n-1}\in\{1,-1\}\).  Because \(f(b)=3\), the polynomial \(f(x)-3\) has the factor \(x-b\); write
\[
f(x)-3 = (x-b)\,Q(x),
\]
where \(Q(x)\) is a polynomial with integer coefficients.

From the recurrence for \(a_{n-2}\) we have \(f(a_{n-2})=b\), so
\[
(a_{n-2}-b)\,Q(a_{n-2}) = b-3. \tag{1}
\]
All \(a_i\) for \(i\le n-2\) satisfy \(|a_i|\le 1\), hence \(a_{n-2}\in\{-1,0,1\}\).

We examine the two possibilities for \(b\).

#### Case \(b=1\)

Then \(b-3=-2\).  Equation (1) becomes \((a_{n-2}-1)Q(a_{n-2})=-2\).  
- \(a_{n-2}=1\) gives \(0\cdot Q(1)=-2\) – impossible.  
- \(a_{n-2}=0\) gives \((-1)Q(0)=-2\) \(\Rightarrow\) \(Q(0)=2\).  
- \(a_{n-2}=-1\) gives \((-2)Q(-1)=-2\) \(\Rightarrow\) \(Q(-1)=1\).

Hence \(a_{n-2}\in\{0,-1\}\).

#### Case \(b=-1\)

Then \(b-3=-4\).  Equation (1) becomes \((a_{n-2}+1)Q(a_{n-2})=-4\).  
- \(a_{n-2}=-1\) gives \(0\cdot Q(-1)=-4\) – impossible.  
- \(a_{n-2}=0\) gives \(1\cdot Q(0)=-4\) \(\Rightarrow\) \(Q(0)=-4\).  
- \(a_{n-2}=1\) gives \(2\cdot Q(1)=-4\) \(\Rightarrow\) \(Q(1)=-2\).

Hence \(a_{n-2}\in\{0,1\}\).

---
### 4.  Iterative contradiction for \(n\ge 3\)

We now show that no sequence can satisfy the conditions when \(n\ge 3\).  The argument uses the same factorization for each step.

For any index \(i\) we have
\[
a_i-3 = (a_{i-1}-b)\,Q(a_{i-1}). \tag{2}
\]

We treat the two values of \(b\) separately.

#### 4.1  Case \(b=1\)

From §3 we have \(a_{n-2}\in\{0,-1\}\).

*Subcase \(a_{n-2}=0\).*  
Then \(Q(0)=2\).  Equation (2) with \(i=n-1\) (i.e. \(a_{n-2}-3 = -3\)) gives
\[
(a_{n-3}-1)\,Q(a_{n-3}) = -3.
\]
Since \(a_{n-3}\in\{-1,0,1\}\):
- \(a_{n-3}=1\): impossible.
- \(a_{n-3}=0\): \((-1)Q(0)=-3\) \(\Rightarrow\) \(Q(0)=3\), contradicting \(Q(0)=2\).
- \(a_{n-3}=-1\): \((-2)Q(-1)=-3\) \(\Rightarrow\) \(Q(-1)=3/2\) (not an integer).

Hence \(a_{n-2}\neq 0\).

*Subcase \(a_{n-2}=-1\).*  
Then \(Q(-1)=1\).  Equation (2) with \(i=n-1\) gives
\[
(a_{n-3}-1)\,Q(a_{n-3}) = -4.
\]
Again \(a_{n-3}\in\{-1,0,1\}\):
- \(a_{n-3}=1\): impossible.
- \(a_{n-3}=0\): \((-1)Q(0)=-4\) \(\Rightarrow\) \(Q(0)=4\).
- \(a_{n-3}=-1\): \((-2)Q(-1)=-4\) \(\Rightarrow\) \(Q(-1)=2\), contradicting \(Q(-1)=1\).

Thus \(a_{n-3}=0\) and \(Q(0)=4\).

Now consider \(a_{n-4}\) (this exists when \(n\ge4\)).  Equation (2) with \(i=n-2\) gives
\[
(a_{n-4}-1)\,Q(a_{n-4}) = a_{n-3}-3 = -3.
\]
The same analysis yields:
- \(a_{n-4}=1\): impossible.
- \(a_{n-4}=0\): \((-1)Q(0)=-3\) \(\Rightarrow\) \(Q(0)=3\), contradicting \(Q(0)=4\).
- \(a_{n-4}=-1\): \((-2)Q(-1)=-3\) \(\Rightarrow\) \(Q(-1)=3/2\) (not an integer).

Thus no solution for \(n\ge4\).  For \(n=3\) we have \(a_2=b=1\), \(a_1=a_{n-2}=-1\), \(a_0=a_{n-3}=0\).  Then \(f(x)=3x^3+x^2-x\) and \(f(0)=0\neq a_1=-1\).  Hence no solution for \(n=3\) either.

#### 4.2  Case \(b=-1\)

From §3 we have \(a_{n-2}\in\{0,1\}\).

*Subcase \(a_{n-2}=0\).*  
Then \(Q(0)=-4\).  Equation (2) with \(i=n-1\) gives
\[
(a_{n-3}+1)\,Q(a_{n-3}) = -3.
\]
Since \(a_{n-3}\in\{-1,0,1\}\):
- \(a_{n-3}=-1\): impossible.
- \(a_{n-3}=0\): \(1\cdot Q(0)=-3\) \(\Rightarrow\) \(Q(0)=-3\), contradicting \(Q(0)=-4\).
- \(a_{n-3}=1\): \(2\cdot Q(1)=-3\) \(\Rightarrow\) \(Q(1)=-3/2\) (not an integer).

Hence \(a_{n-2}\neq 0\).

*Subcase \(a_{n-2}=1\).*  
Then \(Q(1)=-2\).  Equation (2) with \(i=n-1\) gives
\[
(a_{n-3}+1)\,Q(a_{n-3}) = -2.
\]
Again \(a_{n-3}\in\{-1,0,1\}\):
- \(a_{n-3}=-1\): impossible.
- \(a_{n-3}=0\): \(1\cdot Q(0)=-2\) \(\Rightarrow\) \(Q(0)=-2\).
- \(a_{n-3}=1\): \(2\cdot Q(1)=-2\) \(\Rightarrow\) \(Q(1)=-1\), contradicting \(Q(1)=-2\).

Thus \(a_{n-3}=0\) and \(Q(0)=-2\).

Now for \(n\ge4\) consider \(a_{n-4}\).  Equation (2) with \(i=n-2\) gives
\[
(a_{n-4}+1)\,Q(a_{n-4}) = a_{n-3}-3 = -3.
\]
The same analysis:
- \(a_{n-4}=-1\): impossible.
- \(a_{n-4}=0\): \(1\cdot Q(0)=-3\) \(\Rightarrow\) \(Q(0)=-3\), contradicting \(Q(0)=-2\).
- \(a_{n-4}=1\): \(2\cdot Q(1)=-3\) \(\Rightarrow\) \(Q(1)=-3/2\) (not an integer).

Thus no solution for \(n\ge4\).  For \(n=3\) we have \(a_2=b=-1\), \(a_1=a_{n-2}=1\), \(a_0=a_{n-3}=0\).  Then \(f(x)=3x^3-x^2+x\) and \(f(0)=0\neq a_1=1\).  Hence no solution for \(n=3\).

Therefore no integer sequence exists for any \(n\ge3\).

---
### 5.  The case \(n=2\)

We solve the system directly.  Here
\[
f(x)=3x^2+a_1x+a_0,\qquad a_2=3,
\]
and the conditions are
\[
a_1=3a_0^2+a_1a_0+a_0,\qquad 3=3a_1^2+a_1^2+a_0=4a_1^2+a_0.
\]
From the second equation \(a_0=3-4a_1^2\).  Substituting into the first:
\[
a_1=3(3-4a_1^2)^2+(3-4a_1^2)a_1+(3-4a_1^2).
\]
Simplifying yields
\[
24a_1^4-2a_1^3-38a_1^2+a_1+15=0.
\]
The only integer root is \(a_1=1\) (testing divisors of \(15\) gives \(a_1=1\) as the only solution), and then \(a_0=3-4=-1\).  Thus the unique sequence for \(n=2\) is
\[
a_0=-1,\quad a_1=1,\quad a_2=3.
\]
One checks that \(f(x)=3x^2+x-1\) satisfies \(f(-1)=1\) and \(f(1)=3\).

---
### 6.  Conclusion

The only positive integer \(n\) for which such an integer sequence exists is \(n=2\), and the unique sequence is
\[
\boxed{n=2,\quad a_0=-1,\ a_1=1,\ a_2=3}.
\]
