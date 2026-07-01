# PB-Basic-001 — IMO-easy / Algebra

**Score: 7/7** &middot; pipeline output via `select:R0(4/4)`

**Grader note (Claude grader, sympy-verified):** Identity → Cauchy → linear over Z → parametric family → full verification; completely correct.

## Problem

Determine all functions $f: \mathbb{Z} \rightarrow \mathbb{Z}$ such that, for all $x, y \in \mathbb{Z}$, we have \[ f(2x)+2f(y)=f(f(x+y)).\]

**Reference short answer:** $f(x) = 0$ and $f(x) = 2x + c$ for all integer $x$ and some constant $c$.

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

We determine all functions \(f:\mathbb{Z}\to\mathbb{Z}\) satisfying  
\[
f(2x)+2f(y)=f(f(x+y))\qquad\text{for all }x,y\in\mathbb{Z}. \tag{0}
\]

**1.  Basic identities.**  
Set \(x=0\) in (0): \(f(0)+2f(y)=f(f(y))\) for all \(y\). Hence  
\[
f(f(y))=2f(y)+f(0). \tag{1}
\]  
Set \(y=0\) in (0): \(f(2x)+2f(0)=f(f(x))\) for all \(x\). Using (1) with argument \(x\) we get  
\[
f(2x)+2f(0)=2f(x)+f(0)\quad\Longrightarrow\quad f(2x)=2f(x)-f(0). \tag{2}
\]

**2.  Reduction to a Cauchy equation.**  
Insert (2) into the left‑hand side of (0):  
\[
\bigl(2f(x)-f(0)\bigr)+2f(y)=2f(x)+2f(y)-f(0).
\]  
The right‑hand side of (0) is \(f(f(x+y))\). By (1) with argument \(x+y\) we have \(f(f(x+y))=2f(x+y)+f(0)\). Equating gives  
\[
2f(x)+2f(y)-f(0)=2f(x+y)+f(0)\quad\Longrightarrow\quad f(x)+f(y)=f(x+y)+f(0). \tag{3}
\]

Let \(c=f(0)\) and define \(g(x)=f(x)-c\). Then \(g(0)=0\) and (3) becomes  
\[
g(x+y)+c = (g(x)+c)+(g(y)+c)-c = g(x)+g(y)+c,
\]  
so  
\[
g(x+y)=g(x)+g(y)\qquad\text{for all }x,y\in\mathbb{Z}. \tag{4}
\]

**3.  Structure of additive functions on \(\mathbb{Z}\).**  
From (4) we obtain by induction \(g(n)=n\,g(1)\) for every integer \(n\). (Indeed, \(g(0)=0\); for \(n>0\), \(g(n)=g(n-1)+g(1)=\cdots=n\,g(1)\); for negative \(n\), \(g(-n)=-g(n)=-n\,g(1)\).) Set \(a=g(1)\in\mathbb{Z}\). Then  
\[
g(x)=ax\quad\text{and consequently}\quad f(x)=ax+c. \tag{5}
\]

**4.  Determining the parameters.**  
Substitute the linear form (5) into (1):  
\[
f(f(y))=f(ay+c)=a(ay+c)+c=a^2y+ac+c,
\]  
\[
2f(y)+c=2(ay+c)+c=2ay+3c.
\]  
For (1) to hold for all \(y\) we need  
\[
a^2y+ac+c = 2ay+3c\qquad(\forall y\in\mathbb{Z}).
\]  
Comparing coefficients yields the system  
\[
a^2-2a=0,\qquad ac-2c=0.
\]  
The first equation gives \(a=0\) or \(a=2\).  
If \(a=0\) then the second equation forces \(c=0\).  
If \(a=2\) then the second equation becomes \(2c-2c=0\), which is satisfied for every integer \(c\).

Thus the only possibilities are  
\[
f(x)=0\quad\text{for all }x,\qquad\text{and}\qquad f(x)=2x+c\;(c\in\mathbb{Z}).
\]

**5.  Verification.**  
- For \(f(x)=0\): \(f(2x)+2f(y)=0+0=0\) and \(f(f(x+y))=f(0)=0\).  
- For \(f(x)=2x+c\):  
  \[
  f(2x)+2f(y)=(4x+c)+2(2y+c)=4x+4y+3c,
  \]  
  \[
  f(f(x+y))=f(2(x+y)+c)=2(2(x+y)+c)+c=4x+4y+3c.
  \]  
Both families satisfy the original equation for all integers \(x,y\).

Therefore the complete set of solutions is  
\[
\boxed{f(x)=0\ \forall x\in\mathbb{Z}\quad\text{or}\quad f(x)=2x+b\ \forall x\in\mathbb{Z}\ \text{with }b\in\mathbb{Z}}.
\]
