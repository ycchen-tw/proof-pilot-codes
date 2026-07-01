# PB-Basic-003 — IMO-easy / Algebra

**Score: 7/7** &middot; pipeline output via `select:R0(2/4)`

**Grader note (Claude grader, sympy-verified):** Handles both c≠0 and c=0; the injectivity argument is rigorous; candidates verified by substitution.

## Problem

Find all functions $f\colon \mathbb{R} \rightarrow \mathbb{R}$ such that for all $a,b \in \mathbb{R}$,
 \[ (b - a)f(f(a)) = a f(a + f(b)). \]"

**Reference short answer:** $f(x)=0, f(x)=-x+k$ where $k$ is a constant

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

Let \(f:\mathbb{R}\to\mathbb{R}\) satisfy
\[
(b-a)f(f(a))=a\,f(a+f(b))\qquad\text{for all }a,b\in\mathbb{R}.
\tag{★}
\]

---

### 1. Preliminary consequences

Set \(a=0\) in (★): \((b-0)f(f(0))=0\cdot f(0+f(b))\) ⇒ \(b\,f(f(0))=0\) for all \(b\). Hence
\[
f(f(0))=0.
\tag{1}
\]

Denote \(c=f(0)\). Then (1) gives \(f(c)=0\).

Set \(a=c\) in (★): \((b-c)f(f(c))=c\,f(c+f(b))\). Since \(f(c)=0\) and \(f(f(c))=f(0)=c\), we obtain
\[
(b-c)c=c\,f(c+f(b)).
\tag{2}
\]

Set \(a=b\) in (★): \((a-a)f(f(a))=a\,f(a+f(a))\) ⇒ \(a\,f(a+f(a))=0\) for all \(a\). Consequently,
\[
f(a+f(a))=0\qquad\text{for every }a\neq0.
\tag{3}
\]

---

### 2. Case \(c\neq0\)

From (2) we may divide by \(c\) (since \(c\neq0\)):
\[
f(c+f(b))=b-c\qquad\text{for all }b.
\tag{4}
\]

**Injectivity of \(f\).**  
For any \(t\in\mathbb{R}\) put \(b=t+c\) in (4): \(f(c+f(t+c))=t\). Thus \(f\) is surjective. Because \(f\) is surjective, for every \(x\in\mathbb{R}\) there exists \(b\) with \(f(b)=x-c\); hence \(x=c+f(b)\). So every real number can be written as \(c+f(b)\).  
If \(f(u)=f(v)\), choose \(b_1,b_2\) such that \(u=c+f(b_1)\), \(v=c+f(b_2)\). Then from (4)
\[
f(u)=f(c+f(b_1))=b_1-c,\qquad f(v)=f(c+f(b_2))=b_2-c.
\]
Since \(f(u)=f(v)\), we get \(b_1=b_2\) and therefore \(u=v\). Hence \(f\) is injective.

**Determination of \(f\).**  
From (3) we have \(f(a+f(a))=0\) for all \(a\neq0\). Because \(f(c)=0\) and \(f\) is injective, it follows that \(a+f(a)=c\) for all \(a\neq0\). For \(a=0\) we also have \(0+f(0)=c\). Therefore
\[
f(a)=c-a\quad\text{for every }a\in\mathbb{R}.
\]
Substituting \(f(x)=c-x\) into (★) gives
\[
(b-a)f(f(a))=(b-a)(c-(c-a))=a(b-a),\qquad
a\,f(a+f(b))=a\bigl(c-(a+(c-b))\bigr)=a(b-a),
\]
so the equality holds for any \(c\in\mathbb{R}\). Hence all functions \(f(x)=c-x\) with \(c\neq0\) are solutions.

---

### 3. Case \(c=0\)

Now \(f(0)=0\) and (2) becomes \(0=0\). From (3) we have \(f(a+f(a))=0\) for all \(a\neq0\).  
From \(b=0\) in (★) we obtain \(-a f(f(a))=a f(a)\); for \(a\neq0\) this yields
\[
f(f(a))=-f(a)\qquad(a\neq0).
\tag{5}
\]

**Subcase 1: \(f\equiv0\).**  
The zero function clearly satisfies (★).

**Subcase 2: \(f\) is not identically zero.**  
Then there exists \(a_0\neq0\) with \(f(a_0)\neq0\). Apply (★) with \(a=a_0\):
\[
(b-a_0)f(f(a_0))=a_0\,f(a_0+f(b)).
\]
Using (5) we have \(f(f(a_0))=-f(a_0)\), hence
\[
-(b-a_0)f(a_0)=a_0\,f(a_0+f(b))\;\Longrightarrow\;
f(a_0+f(b))=-\frac{f(a_0)}{a_0}(b-a_0).
\tag{6}
\]
Since \(f(a_0)\neq0\) and \(a_0\neq0\), the right‑hand side of (6) is an injective function of \(b\). If \(f(b_1)=f(b_2)\), then \(a_0+f(b_1)=a_0+f(b_2)\) and (6) gives \(b_1=b_2\); thus \(f\) is injective.

From (3) we have \(f(a+f(a))=0\) for all \(a\neq0\). Because \(f(0)=0\) and \(f\) is injective, we obtain \(a+f(a)=0\) for all \(a\neq0\). For \(a=0\) we also have \(0+f(0)=0\). Consequently
\[
f(a)=-a\qquad\text{for every }a\in\mathbb{R}.
\]
Direct substitution shows that \(f(x)=-x\) satisfies (★). This is the case \(c=0\) of the family \(f(x)=c-x\).

---

### 4. Conclusion

The functions that satisfy the functional equation are exactly
\[
\boxed{f(x)=0\ \text{for all }x}\qquad\text{and}\qquad\boxed{f(x)=c-x\ \text{for all }x,\ c\in\mathbb{R}}.
\]
(Note that \(c=0\) gives \(f(x)=-x\), which is included in the second family.)
