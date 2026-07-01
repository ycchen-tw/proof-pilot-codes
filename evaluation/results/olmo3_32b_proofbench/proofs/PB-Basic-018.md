# PB-Basic-018 — pre-IMO / Number theory

**Score: 7/7** &middot; pipeline output via `select:R1(2/4)`

**Grader note (Claude grader, sympy-verified):** The proof of (x-y)(2x+2y+1)=y² with gcd=1 is complete; since a coprime product is a square, each factor is a square; the actual solutions 81,7921 are confirmed to be squares.

## Problem

Let $x$ and $y$ be positive integers satisfying $2x^2 + x = 3y^2 + y$. Prove that $2x+2y+1$ is a perfect square.

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

**Proof.**  
Let \(x,y\) be positive integers satisfying  

\[
2x^2 + x = 3y^2 + y.
\]

Rewrite the equation:

\[
2x^2 + x - 2y^2 - y = y^2 \quad\Longrightarrow\quad 2(x^2 - y^2) + (x - y) = y^2.
\]

Factor \(x^2 - y^2 = (x-y)(x+y)\):

\[
2(x-y)(x+y) + (x-y) = (x-y)(2x+2y+1) = y^2. \tag{1}
\]

Since \(y>0\), the right‑hand side is positive and \(2x+2y+1>0\); therefore \(x-y>0\), i.e. \(x>y\).

Set  

\[
a = x-y,\qquad b = 2x+2y+1.
\]

Then \(a,b\) are positive integers and  

\[
ab = y^2. \tag{2}
\]

**Claim:** \(\gcd(a,b)=1\).  

Let \(d\) be any common divisor of \(a\) and \(b\). Then  

\[
d \mid b - 2a = (2x+2y+1) - 2(x-y) = 4y+1.
\]

Hence \(d\) divides both \(a\) and \(4y+1\).  

Suppose a prime \(p\) divides \(d\). Then \(p\mid a\) and \(p\mid 4y+1\). From \(p\mid a\) we have \(x\equiv y\pmod p\). Substituting into the original equation modulo \(p\) gives  

\[
2x^2+x \equiv 3y^2+y \pmod p \;\Longrightarrow\; 2y^2+y \equiv 3y^2+y \pmod p \;\Longrightarrow\; y^2\equiv0\pmod p,
\]

so \(p\mid y\). Then \(x\equiv y\pmod p\) implies \(p\mid x\). Consequently  

\[
b = 2x+2y+1 \equiv 2\cdot0+2\cdot0+1 = 1 \pmod p,
\]

but \(p\mid b\) by assumption, so \(1\equiv0\pmod p\), impossible. Thus no prime divides \(d\); therefore \(d=1\) and \(\gcd(a,b)=1\).

Now \(a\) and \(b\) are coprime positive integers whose product is a perfect square. A standard number‑theoretic fact (if two coprime positive integers multiply to a square, then each is a square) follows because every prime factor of \(a\) appears with an even exponent in \(ab=y^2\), and since \(a\) and \(b\) share no primes, the exponent of that prime in \(a\) must be even; the same holds for \(b\). Hence \(b = 2x+2y+1\) is a perfect square. ∎
