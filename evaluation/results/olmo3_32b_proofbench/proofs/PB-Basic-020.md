# PB-Basic-020 — IMO-easy / Number theory

**Score: 7/7** &middot; pipeline output via `select:R0(3/4)`

**Grader note (Claude grader, sympy-verified):** boxed(7,3) 一致。判別式→完全平方→互素因子へ b² 割当の論法が健全、b=5→a=14 非素数を棄却、唯一性 brute 確認

## Problem

Find all pairs of primes $(a, b)$ such that $a^2 - ab - b^3 = 1$.

**Reference short answer:** $(p,q) = (7,3)$

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

We solve \(a^2 - ab - b^3 = 1\) for primes \(a,b\) (positive).

**1.  Small cases.**  
If \(b=2\): \(a^2-2a-8=1 \Rightarrow a^2-2a-9=0\); discriminant \(40\) is not a perfect square, so no integer \(a\).  
If \(a=2\): \(4-2b-b^3=1 \Rightarrow b^3+2b=3\); the only possibility is \(b=1\), not prime.  
Hence \(a,b\ge 3\) and both are odd.

**2.  Basic relation.**  
Rewrite the equation as \(a(a-b)=b^3+1\). The right‑hand side is positive, so \(a>0\) and \(a-b>0\); thus \(a>b\).  
Set \(d=a-b>0\). Then \(a=b+d\) and  
\[
(b+d)d = b^3+1 \quad\Longrightarrow\quad d^2+bd-(b^3+1)=0.
\]  
This quadratic in \(d\) has discriminant  
\[
\Delta = b^2+4(b^3+1)=4b^3+b^2+4.
\]  
For integer \(d\) we must have \(\Delta\) a perfect square. Write \(\Delta = k^2\) with \(k\in\mathbb{N}\).  
Then \(d = \frac{-b\pm k}{2}\). Because \(d>0\) we need \(k>b\), so  
\[
d = \frac{k-b}{2},\qquad a = b+d = \frac{b+k}{2}.
\]  
Since \(b\) is odd, \(k\) must also be odd (otherwise \(k^2\equiv 0\pmod 4\) but \(\Delta\equiv 1\pmod 4\)).

**3.  Factorisation and coprimality.**  
From \(k^2 = 4b^3+b^2+4\) we obtain  
\[
k^2-4 = 4b^3+b^2 = b^2(4b+1)\quad\Longrightarrow\quad (k-2)(k+2)=b^2(4b+1).
\]  
Because \(k\) is odd, \(k-2\) and \(k+2\) are odd. Their difference is \(4\), so any common divisor divides \(4\); since they are odd, \(\gcd(k-2,k+2)=1\).  
The factors \(k-2\) and \(k+2\) are therefore coprime positive integers whose product is \(b^2(4b+1)\).

**4.  Splitting the square factor.**  
The prime \(b\) is odd, and \(\gcd(b,4b+1)=1\) (any common divisor divides \(1\)).  
Because \(b^2\) and \(4b+1\) are coprime, the whole factor \(b^2\) must be contained in exactly one of the coprime factors \(k-2\) or \(k+2\).  
Thus we have two cases.

*Case I: \(b^2\mid(k-2)\).*  
Write \(k-2 = b^2x\) and \(k+2 = y\) with positive integers \(x,y\). Then  
\[
xy = 4b+1,\qquad y - b^2x = 4 \;\Longrightarrow\; y = b^2x+4.
\]  
Substituting gives  
\[
(b^2x+4)x = 4b+1 \;\Longrightarrow\; b^2x^2+4x-4b-1=0. \tag{1}
\]  
For \(b\ge 3\) and \(x\ge 1\): if \(x\ge 2\) then  
\[
b^2x^2+4x \ge 4b^2+8 > 4b+1 \quad\text{(since }4b^2+8-(4b+1)=4b(b-1)+7>0\text{)}.
\]  
Hence only \(x=1\) is possible. Substituting \(x=1\) in (1):  
\[
b^2+4 = 4b+1 \;\Longrightarrow\; b^2-4b+3=0 \;\Longrightarrow\; (b-1)(b-3)=0.
\]  
Thus \(b=3\) (the only prime). Then \(x=1\), \(y=9+4=13\), \(k=y-2=11\), and  
\[
a = \frac{b+k}{2} = \frac{3+11}{2}=7,
\]  
which is prime. So \((a,b)=(7,3)\) is a solution.

*Case II: \(b^2\mid(k+2)\).*  
Write \(k+2 = b^2y\) and \(k-2 = x\) with positive integers \(x,y\). Then  
\[
xy = 4b+1,\qquad b^2y - x = 4 \;\Longrightarrow\; x = b^2y-4.
\]  
Substituting gives  
\[
(b^2y-4)y = 4b+1 \;\Longrightarrow\; b^2y^2-4y-4b-1=0. \tag{2}
\]  
For \(b\ge 3\) and \(y\ge 1\): if \(y\ge 2\) then  
\[
b^2y^2-4y-4b-1 \ge 4b^2-8-4b-1 = 4b^2-4b-9.
\]  
For \(b=3\) this is \(15>0\); for \(b\ge5\) it is even larger. Hence the left‑hand side of (2) is positive, so no solution with \(y\ge2\). Thus \(y=1\). Substituting \(y=1\) in (2):  
\[
b^2-4-4b-1=0 \;\Longrightarrow\; b^2-4b-5=0 \;\Longrightarrow\; (b-5)(b+1)=0.
\]  
Thus \(b=5\). Then \(y=1\), \(x=25-4=21\), \(k=b^2y-2=23\), and  
\[
a = \frac{b+k}{2} = \frac{5+23}{2}=14,
\]  
which is not prime. Hence no prime solution arises from this case.

**5.  Conclusion.**  
The only pair of primes satisfying \(a^2-ab-b^3=1\) is \((a,b)=(7,3)\).

\[
\boxed{(7,3)}
\]
