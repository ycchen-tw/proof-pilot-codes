# PB-Advanced-001 — IMO-easy / Algebra

**Score: 7/7** &middot; pipeline output via `select:R0(4/4)`

**Grader note (Claude grader, sympy-verified):** Construction (intervals + CRT) and both lemmas pass all computational checks (219/219); self-contained and complete.

## Problem

For a positive integer $n$, let $A_{n}$ be the number of perfect powers less than or equal to $n$. Here, a perfect power is a number that can be expressed in the form $a^{b}$, where $a$ is a positive integer and $b$ is an integer greater than or equal to 2. Prove that there are infinitely many $n$ such that $A_{n}$ divides $n+2024$.

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

Let \(P\) be the set of perfect powers, i.e. numbers of the form \(a^{b}\) with \(a\in\mathbb{N}\), \(b\ge 2\).  
For a positive integer \(n\) let \(A_n=|P\cap[1,n]|\).

---

### Lemma 1
There are infinitely many integers \(k\) such that the open interval \((k^2,(k+1)^2)\) contains no element of \(P\).

*Proof.*  
Call a positive integer \(k\) *bad* if there exists a non‑square perfect power in \((k^2,(k+1)^2)\); otherwise \(k\) is *good*.  
Fix a large integer \(N\). Every bad \(k\le N\) yields a distinct non‑square perfect power \(p\) with \(p\le (N+1)^2\) (the intervals are disjoint). Hence the number \(B(N)\) of bad \(k\le N\) is at most the number of non‑square perfect powers \(\le (N+1)^2\).

For a given exponent \(b\ge 3\), the numbers \(a^b\le X\) satisfy \(a\le X^{1/b}\). If \(b>\log_2 X\) then \(2^b>X\) and the only possibility is \(a=1\) (giving the square \(1\)), so we need only consider \(b\le\lfloor\log_2 X\rfloor\). Therefore
\[
\#\{\text{non‑square perfect powers}\le X\}\le\sum_{b=3}^{\lfloor\log_2 X\rfloor}X^{1/b}.
\]
Set \(X=(N+1)^2\). Then \(\lfloor\log_2 X\rfloor\le 2\log_2(N+1)\). Hence
\[
B(N)\le\sum_{b=3}^{2\log_2(N+1)}(N+1)^{2/b}
\le (N+1)^{2/3}+2(\log_2(N+1))(N+1)^{1/2}.
\]
The right‑hand side is \(o(N)\) as \(N\to\infty\). Consequently \(B(N)<N\) for all sufficiently large \(N\); thus there are infinitely many good \(k\). ∎

---

### Lemma 2
There exists a constant \(K_0\) such that for all \(k\ge K_0\) we have \(A_{k^2}\le 2k\).

*Proof.*  
For any \(x\ge 2\) we bound the number of perfect powers \(\le x\). Squares contribute at most \(\sqrt{x}\). For an exponent \(b\ge 3\) we have \(a^b\le x\Rightarrow a\le x^{1/b}\); if \(b>\log_2 x\) then only \(a=1\) is possible (giving \(1\), already a square). Hence
\[
A_x\le\sqrt{x}+\sum_{b=3}^{\lfloor\log_2 x\rfloor}x^{1/b}.
\]
Take \(x=k^2\). Then \(\sqrt{x}=k\) and \(\lfloor\log_2(k^2)\rfloor\le 2\log_2 k\). For \(b=3\) we have \(k^{2/3}\); for \(b\ge4\) we have \(k^{2/b}\le k^{1/2}\). Therefore
\[
A_{k^2}\le k+k^{2/3}+\sum_{b=4}^{2\log_2 k}k^{1/2}
\le k+k^{2/3}+(2\log_2 k)k^{1/2}.
\]
Now \(\displaystyle\frac{k^{2/3}}{k}=k^{-1/3}\to0\) and \(\displaystyle\frac{(2\log_2 k)k^{1/2}}{k}=\frac{2\log_2 k}{k^{1/2}}\to0\). Hence there exists \(K_0\) such that for all \(k\ge K_0\),
\[
k^{2/3}+(2\log_2 k)k^{1/2}<k.
\]
For such \(k\) we obtain \(A_{k^2}\le k+k=2k\). ∎

---

### Construction of infinitely many \(n\)

Choose any integer \(k\ge K_0\) that satisfies the condition of Lemma 1 (such \(k\) exist because Lemma 1 gives infinitely many, and we may discard those below \(K_0\)).  
Let \(m=A_{k^2}\). By Lemma 2 we have \(m\le 2k\).

Consider the interval  
\[
I=[k^2,\,(k+1)^2-1].
\]
Its length is \((k+1)^2-k^2=2k+1\). Since \(m\le 2k\), we have \(|I|=2k+1\ge m\).  
Because \((k^2,(k+1)^2)\) contains no perfect power, every integer \(n\in I\) satisfies \(A_n=m\) (the perfect powers up to \(n\) are exactly those up to \(k^2\)).

The residues modulo \(m\) of the consecutive integers in \(I\) cover all residues \(0,1,\dots,m-1\) because \(|I|\ge m\). Hence there exists an integer \(n\in I\) such that
\[
n\equiv -2024\pmod{m}.
\]
For this \(n\) we have \(A_n=m\) and
\[
n+2024\equiv0\pmod{m},
\]
so \(m\mid n+2024\). Thus \(n\) satisfies the required property.

The set of admissible \(k\) is infinite, and for each such \(k\) we obtain at least one \(n\) (different \(k\) give disjoint intervals \(I\), hence distinct \(n\)). Therefore there are infinitely many positive integers \(n\) with \(A_n\mid n+2024\). ∎
