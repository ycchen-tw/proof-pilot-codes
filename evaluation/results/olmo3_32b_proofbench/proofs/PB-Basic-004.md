# PB-Basic-004 — IMO-easy / Algebra

**Score: 7/7** &middot; pipeline output via `select:R1(3/4)`

**Grader note (Claude grader, sympy-verified):** g(0)=0 + recurrence roots 5,−4 + monotonicity give B=0, with verification; completely correct.

## Problem

Find all strictly increasing functions $g:\mathbb{R} \to \mathbb{R}$ such that:
 (a) $g$ is surjective
 (b) $g(g(x))=g(x)+20x.$

**Reference short answer:** $g(x) = 5x$ for all x

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

We prove that the only strictly increasing surjective function \(g:\mathbb{R}\to\mathbb{R}\) satisfying  
\[
g(g(x))=g(x)+20x\qquad(\forall x\in\mathbb{R})
\]  
is \(g(x)=5x\).

---

### 1.  Basic properties
Since \(g\) is strictly increasing and surjective, it is bijective.  
Put \(x=0\) in the functional equation: \(g(g(0))=g(0)\).  Because \(g\) is injective, \(g(0)=0\).

---

### 2.  Iterates and a linear recurrence
For any \(x\in\mathbb{R}\) define the sequence \((a_n)_{n\in\mathbb{Z}}\) by  
\[
a_n = g^n(x),\quad g^0(x)=x,\; g^1(x)=g(x),\;\text{and}\; g^{-n}=(g^{-1})^{n}.
\]  
Because \(g\) is bijective, the iterates are well‑defined for all integers.  
Apply the functional equation to \(y=a_n\):  
\[
g(g(a_n)) = g(a_n)+20a_n \;\Longrightarrow\; a_{n+2}=a_{n+1}+20a_n\qquad(\forall n\in\mathbb{Z}).
\]

The recurrence is linear with constant coefficients.  Its characteristic equation \(r^2-r-20=0\) has roots \(5\) and \(-4\).  Hence for each \(x\) there exist constants \(A(x),B(x)\) such that  
\[
a_n = A(x)\,5^{\,n}+B(x)\,(-4)^{\,n}\qquad(\forall n\in\mathbb{Z}).
\]  
Using the initial values \(a_0=x\) and \(a_1=g(x)\) we solve  
\[
\begin{cases}
A+B = x,\\
5A-4B = g(x),
\end{cases}
\]  
obtaining  
\[
A = \frac{g(x)+4x}{9},\qquad B = \frac{5x-g(x)}{9}. \tag{1}
\]

---

### 3.  Monotonicity of the orbit
Because \(g\) is strictly increasing, its inverse is also strictly increasing.  
If \(g(x)>x\), then for all \(n\ge 0\) we have \(g^{n+1}(x)>g^n(x)\) by induction; for negative indices, applying \(g^{-1}\) repeatedly gives \(g^{-n}(x)<g^{-(n-1)}(x)\) for \(n\ge 1\), so the whole sequence is strictly increasing.  
If \(g(x)<x\), a symmetric argument shows the sequence is strictly decreasing.  
If \(x=0\), then \(g(0)=0\) and the sequence is constant.  
Thus the sign of the difference  
\[
d_n = a_{n+1}-a_n
\]  
is constant (positive for \(g(x)>x\), negative for \(g(x)<x\), zero only for \(x=0\)).

From the explicit form we compute  
\[
d_n = 4A\,5^{\,n}-5B\,(-4)^{\,n}. \tag{2}
\]

---

### 4.  Forcing \(B\) to be zero
Assume that for some \(x\) we have \(B(x)\neq0\).  Consider \(n=-k\) with \(k\in\mathbb{N}\).  Then  
\[
d_{-k} = \frac{4A}{5^{\,k}} - 5B\,\frac{(-1)^k}{4^{\,k}}.
\]  
Since \(5^{\,k}\) grows faster than \(4^{\,k}\), for sufficiently large \(k\) the second term dominates in absolute value.  More precisely,  
\[
\frac{|4A|/5^{\,k}}{|5B|/4^{\,k}} = \frac{4|A|}{5|B|}\left(\frac{4}{5}\right)^{\!k} \to 0,
\]  
so for all large \(k\) the sign of \(d_{-k}\) is the sign of \(-5B(-1)^k/4^{\,k}\), i.e.  
\[
\operatorname{sgn}(d_{-k}) = (-1)^{k+1}\operatorname{sgn}(B).
\]  
Hence the signs of \(d_{-k}\) alternate with \(k\): they are opposite for even and odd \(k\).  This contradicts the fact that all \(d_n\) have the same sign (because the orbit is monotonic).  Therefore \(B(x)=0\) for every \(x\).

(If \(x=0\), then \(g(0)=0\) and (1) gives \(B(0)=0\) automatically.)

---

### 5.  Determining \(g\)
With \(B=0\) we have \(a_n = A\,5^{\,n}\).  From \(a_0=x\) we get \(A=x\).  Then  
\[
g(x)=a_1 = 5A = 5x.
\]  
Thus \(g(x)=5x\) for all \(x\).

---

### 6.  Verification
The function \(g(x)=5x\) is strictly increasing, surjective, and  
\[
g(g(x))=25x = 5x+20x = g(x)+20x,
\]  
so it satisfies all conditions.

---

### 7.  Conclusion
The unique function fulfilling the requirements is  
\[
\boxed{g(x)=5x}.
\]
