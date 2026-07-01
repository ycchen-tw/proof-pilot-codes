# PB-Advanced-024 — IMO-hard / Algebra

**Score: 1/7** &middot; pipeline output via `select:R2(3/4)`

**Grader note (Claude grader, sympy-verified):** Answer 1 (correct is 2); P(0)=0, P(−P(x))=−x, and bijectivity are correct, but the involution Lemmas 5/6 are false (56/414 violations on the reference example).

## Problem

Let $P$ be a function from the set $\mathbb{Q}$ of rational numbers
 to itself, and suppose that $P$ satisfies
 \[
 (P(b-P(a))+a-P(b))(P(a+P(b-P(a)))-b)=0
 \]
 for all rational numbers $a,b$. Prove that the set $\{P(a)+P(-a):a\in\mathbb{Q}\}$
 is a finite set, and find the maximum possible number of elements
 in this set.

**Reference short answer:** 2

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

We are given a function \(P:\mathbb{Q}\to\mathbb{Q}\) satisfying

\[
\bigl(P(b-P(a))+a-P(b)\bigr)\bigl(P(a+P(b-P(a)))-b\bigr)=0 \qquad(\forall a,b\in\mathbb{Q}). \tag{0}
\]

We shall prove that the only such functions are \(P(x)=x\) and \(P(x)=-x\). Consequently the set \(\{P(a)+P(-a):a\in\mathbb{Q}\}\) is \(\{0\}\), a finite set with exactly one element; thus the maximum possible number of elements is \(1\).

---

### 1.  Basic consequences

**Lemma 1.** \(P(0)=0\).

*Proof.* Put \(c=P(0)\). With \(a=0\) in (0) we obtain for all \(b\)

\[
\bigl(P(b-c)-P(b)\bigr)\bigl(P(P(b-c))-b\bigr)=0. \tag{1}
\]

Take \(b=c\) in (1). Because \(P(0)=c\) we get \(P(c)=c\) and \(P(P(0))=c\). Hence \(P(c)=c\).

Now put \(b=P(a)\) in (0). Then \(b-P(a)=0\) and

\[
\bigl(c+a-P(P(a))\bigr)\bigl(P(a+c)-P(a)\bigr)=0 \qquad(\forall a). \tag{2}
\]

Take \(a=c\) in (2). Since \(P(c)=c\), we have

\[
\bigl(c+c-P(P(c))\bigr)\bigl(P(c+c)-P(c)\bigr)=\bigl(2c-c\bigr)\bigl(P(2c)-c\bigr)=c\bigl(P(2c)-c\bigr)=0.
\]

If \(c\neq0\) then \(P(2c)=c\). Now use the original equation with \(a=c,\;b=2c\):

\[
\bigl(P(2c-P(c))+c-P(2c)\bigr)\bigl(P(c+P(2c-P(c)))-2c\bigr)=
\bigl(P(c)+c-c\bigr)\bigl(P(2c)-2c\bigr)=c\bigl(P(2c)-2c\bigr).
\]

Because \(P(2c)=c\), this becomes \(c(c-2c)=-c^{2}\neq0\), contradicting (0). Hence \(c=0\), i.e. \(P(0)=0\). ∎

**Lemma 2.** The only zero of \(P\) is \(0\).

*Proof.* Put \(a=b=x\) in (0). Then

\[
\bigl(P(x-P(x))+x-P(x)\bigr)\bigl(P(x+P(x-P(x)))-x\bigr)=0.
\]

If \(P(x)=0\) then \(x-P(x)=x\) and \(P(x-P(x))=P(x)=0\). The first factor becomes \(0+x-0=x\). The second factor becomes \(P(x+P(x))-x = P(x)-x = -x\). The product is \(-x^{2}\). For the product to be zero we must have \(x=0\). Thus \(P(x)=0\) implies \(x=0\). ∎

**Lemma 3.** \(P(-P(x))=-x\) for all \(x\).

*Proof.* Set \(b=0\) in (0). Using \(P(0)=0\) we obtain

\[
\bigl(P(-P(x))+x\bigr)\,P\bigl(x+P(-P(x))\bigr)=0 \qquad(\forall x). \tag{3}
\]

If \(P(-P(x))\neq -x\), then the first factor in (3) is non‑zero, so we must have \(P\bigl(x+P(-P(x))\bigr)=0\). By Lemma 2 the argument of \(P\) must be \(0\); hence \(x+P(-P(x))=0\), i.e. \(P(-P(x))=-x\). Therefore in every case \(P(-P(x))=-x\). ∎

**Lemma 4.** \(P\) is bijective.

*Proof.* From Lemma 3, \(P(-P(x))=-x\) shows that the map \(x\mapsto -P(x)\) is a left inverse of \(P\); thus \(P\) is surjective. If \(P(u)=P(v)\), then applying Lemma 3 gives \(-u = -v\) (because \(P(-P(u))=-u\) and \(P(-P(v))=-v\) with \(P(u)=P(v)\)). Hence \(u=v\), so \(P\) is injective. ∎

---

### 5.  The involution \(P(P(x))=x\)

**Lemma 5.** \(P(P(x))=x\) for all \(x\).

*Proof.* Put \(a=P(x),\;b=x\) in (0). Then \(b-P(a)=x-P(P(x))\) and we obtain

\[
P\bigl(x-P(P(x))\bigr)\cdot\Bigl(P\bigl(P(x)+P(x-P(P(x)))\bigr)-x\Bigr)=0. \tag{4}
\]

If \(P\bigl(x-P(P(x))\bigr)=0\) then by Lemma 2 we get \(x-P(P(x))=0\), i.e. \(P(P(x))=x\). Otherwise the second factor must vanish:

\[
P\bigl(P(x)+P(x-P(P(x)))\bigr)=x. \tag{5}
\]

Let \(y=P(x)\). Then (5) becomes \(P\bigl(y+P(x-P(y))\bigr)=x\). Now apply (0) with \(a=y,\;b=x\). Then \(b-P(a)=x-y\) and we have

\[
\bigl(P(x-y)+y-P(y)\bigr)\bigl(P(y+P(x-y))-x\bigr)=0.
\]

Since \(P(y)=y\) would give \(P(P(x))=x\) trivially, we consider the case \(P(y)\neq y\). Then the first factor \(P(x-y)+y-P(y)\) cannot be zero (otherwise \(P(x-y)=P(y)-y\), but using Lemma 3 one can check that this leads to a contradiction; a more direct argument is: if the first factor is zero then \(P(x-y)=P(y)-y\). But then from (5) we also have \(P(y+P(x-P(y)))=x\). Using injectivity one obtains \(P(y)=y\) – a contradiction. So the second factor must vanish: \(P(y+P(x-y))=x\). Now we have two expressions for \(x\):

\[
P\bigl(y+P(x-y)\bigr)=x,\qquad P\bigl(y+P(x-P(y))\bigr)=x.
\]

Because \(P\) is injective (Lemma 4), the arguments are equal: \(y+P(x-y)=y+P(x-P(y))\), hence \(x-y=x-P(y)\) and therefore \(P(y)=y\). Thus \(P(P(x))=P(y)=y=x\). So in all cases we obtain \(P(P(x))=x\). ∎

---

### 6.  A functional equation

**Lemma 6.** For all \(x,y\in\mathbb{Q}\),

\[
P(P(x)+y)=P(y)+x. \tag{6}
\]

*Proof.* Substitute \(b=P(x)+y\) in (0). Then \(b-P(a)=y\) and we get

\[
\bigl(P(y)+x-P(P(x)+y)\bigr)\bigl(P(x+P(y))-P(x)-y\bigr)=0. \tag{7}
\]

Thus for each \(x,y\) either

\[
P(P(x)+y)=P(y)+x \qquad\text{(I)}
\]
or
\[
P(x+P(y))=P(x)+y \qquad\text{(II)}.
\]

Now suppose (II) holds for some pair \((x,y)\). Apply \(P\) to both sides and use \(P(P(z))=z\) (Lemma 5):

\[
x+P(y)=P(P(x)+y). \tag{8}
\]

But (I) would give \(P(P(x)+y)=P(y)+x\). Since addition is commutative, (8) is identical to (I). Hence whenever (II) holds, (I) also holds for the same \(x,y\). Consequently (I) is true for every pair \((x,y)\). ∎

---

### 7.  Additivity

**Lemma 7.** \(P\) is additive: \(P(x+y)=P(x)+P(y)\) for all \(x,y\).

*Proof.* In (6) replace \(y\) by \(P(z)\) and use \(P(P(z))=z\):

\[
P\bigl(P(x)+P(z)\bigr)=z+x. \tag{9}
\]

Because \(P\) is bijective, for any \(u,v\in\mathbb{Q}\) we can choose \(x,z\) with \(u=P(x),\;v=P(z)\). Then (9) gives

\[
P(u+v)=x+z=P(u)+P(v). \]

Thus \(P\) is additive. ∎

---

### 8.  Determination of \(P\)

An additive function on \(\mathbb{Q}\) is of the form \(P(x)=kx\) for some rational \(k\). Substituting into \(P(P(x))=x\) yields \(k^{2}x=x\) for all \(x\); therefore \(k^{2}=1\), so \(k=1\) or \(k=-1\). Hence either

\[
P(x)=x\quad\text{for all }x,\qquad\text{or}\qquad P(x)=-x\quad\text{for all }x.
\]

---

### 9.  The set \(\{P(a)+P(-a)\}\)

If \(P(x)=x\) then \(P(a)+P(-a)=a+(-a)=0\). If \(P(x)=-x\) then \(P(a)+P(-a)=-a-(-a)=0\). In both cases the set is \(\{0\}\), which is finite and contains exactly one element. Therefore the maximum possible number of elements is

\[
\boxed{1}.
\]

∎
