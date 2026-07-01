# PB-Advanced-029 — IMO-medium / Number theory

**Score: 1/7** &middot; pipeline output via `select:R2(4/4)`

**Grader note (Claude grader, sympy-verified):** The answer and necessity are correct, but the core of sufficiency, C(n,i)≡(−1)^i mod(n+1), is a false proposition (counterexamples n=3,5,9); the hard direction is unproven.

## Problem

Determine, with proof, all positive integers $k$ such that
 \[
 \frac{1}{n+1}\sum_{i=0}^{n}\binom{n}{i}^{k}
 \]
 is an integer for every positive integer $n$.

**Reference short answer:** All even integer $k$

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

The positive integers \(k\) for which 
\[
\frac{1}{n+1}\sum_{i=0}^{n}\binom{n}{i}^{k}
\]
is an integer for every positive integer \(n\) are exactly the even positive integers.

**Proof.**

**Necessity.**  
Take \(n=2\). Then  
\[
\frac{1}{3}\sum_{i=0}^{2}\binom{2}{i}^{k}= \frac{1+2^{k}+1}{3}=\frac{2+2^{k}}{3}.
\]  
If \(k\) is odd, then \(2^{k}\equiv 2\pmod 3\); hence \(2+2^{k}\equiv 2+2\equiv 4\equiv 1\pmod 3\) and the fraction is not an integer. Therefore any \(k\) that works must be even.

**Sufficiency.**  
Now assume \(k\) is even and write \(k=2m\) with \(m\ge 1\). We prove that for every positive integer \(n\) the sum  
\[
S(n,k)=\sum_{i=0}^{n}\binom{n}{i}^{k}
\]  
is divisible by \(n+1\).

We first establish a congruence modulo \(n+1\). For any non‑negative integers \(n,i\) we have the identity  
\[
\binom{n}{i}=(-1)^{i}\binom{i-n-1}{i}.
\]  
(The identity is valid for all \(i\); when \(i>n\) the left side is \(0\) and the right side is also \(0\) because \(\binom{i-n-1}{i}=0\) for \(i>n\).)

Consider the polynomial \(P(x)=\binom{x}{i}=x(x-1)\cdots(x-i+1)/i!\) with integer coefficients.  
Since \(i-n-1\equiv i\pmod{n+1}\) (because \(-n-1\equiv 0\pmod{n+1}\)), we have  
\[
\binom{i-n-1}{i}\equiv \binom{i}{i}=1\pmod{n+1}.
\]  
Therefore  
\[
\binom{n}{i}\equiv (-1)^{i}\cdot 1 = (-1)^{i}\pmod{n+1}.
\]

Now because \(k\) is even, \((-1)^{k i}=1\). Hence for every \(i\),  
\[
\binom{n}{i}^{k}\equiv \bigl((-1)^{i}\bigr)^{k}=1\pmod{n+1}.
\]  
Summing over \(i=0,1,\dots ,n\) gives  
\[
S(n,k)\equiv \sum_{i=0}^{n}1 = n+1 \equiv 0\pmod{n+1}.
\]  
Thus \(n+1\) divides \(S(n,k)\), and consequently  
\[
\frac{1}{n+1}\sum_{i=0}^{n}\binom{n}{i}^{k}
\]  
is an integer for every positive integer \(n\).

**Conclusion.**  
The required positive integers are precisely the even ones.
