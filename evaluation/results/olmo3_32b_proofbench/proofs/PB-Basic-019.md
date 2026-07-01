# PB-Basic-019 — IMO-easy / Number theory

**Score: 7/7** &middot; pipeline output via `select:R0(2/4)`

**Grader note (Claude grader, sympy-verified):** The closed form S(N)=N−Σ⌊N/2^k⌋2^{−k} and the geometric series 1/3, with 0<E<1, are rigorously proven (|error|<1 numerically); only minor LaTeX typos.

## Problem

For any positive integer $n$, let $\delta(n)$ be the largest odd divisor of $n$. Prove for any $N>0$ that we have
 \[
 \left| \sum_{n=1}^N \frac{\delta(n)}{n}- \frac{2}{3}N \right| <1.
 \]

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

Let \(v_2(n)\) denote the exponent of the highest power of \(2\) dividing \(n\), so that \(n=2^{v_2(n)}m\) with \(m\) odd. Then the largest odd divisor \(\delta(n)=m\) and therefore  
\[
\frac{\delta(n)}{n}=2^{-v_2(n)}.
\]  
Hence  
\[
S(N):=\sum_{n=1}^{N}\frac{\delta(n)}{n}= \sum_{n=1}^{N}2^{-v_2(n)}.
\]

For each \(k\ge 0\) let  
\[
A_k(N)=\#\{n\le N:v_2(n)=k\}.
\]  
The numbers with exactly \(k\) factors of \(2\) are precisely \(n=2^k m\) where \(m\) is odd and \(2^k m\le N\), i.e. \(m\le N/2^k\).  Counting the odd integers not exceeding \(x\) gives \(\lfloor (x+1)/2\rfloor\), so  
\[
A_k(N)=\Bigl\lfloor\frac{N/2^k+1}{2}\Bigr\rfloor.
\]  
However a more convenient expression is obtained by noting that the numbers divisible by \(2^k\) are \(\lfloor N/2^k\rfloor\) and those divisible by \(2^{k+1}\) are \(\lfloor N/2^{k+1}\rfloor\); thus  
\[
A_k(N)=\lfloor N/2^k\rfloor-\lfloor N/2^{k+1}\rfloor.
\]  
Consequently  
\[
S(N)=\sum_{k=0}^{\infty}\bigl(\lfloor N/2^k\rfloor-\lfloor N/2^{k+1}\rfloor\bigr)2^{-k}.
\]

Separate the two sums:
\[
\begin{aligned}
S(N)&=\sum_{k=0}^{\infty}\lfloor N/2^k\rfloor 2^{-k}-\sum_{k=0}^{\infty}\lfloor N/2^{k+1}\rfloor 2^{-k} \\
&= \lfloor N\rfloor + \sum_{k=1}^{\infty}\lfloor N/2^k\rfloor 2^{-k} - \sum_{k=0}^{\infty}\lfloor N/2^{k+1}\rfloor 2^{-k}.
\end{aligned}
\]
In the last sum set \(j=k+1\); then \(2^{-k}=2^{-(j-1)}=2\cdot2^{-j}\) and  
\[
\sum_{k=0}^{\infty}\lfloor N/2^{k+1}\rfloor 2^{-k}=2\sum_{j=1}^{\infty}\lfloor N/2^j\rfloor 2^{-j}.
\]  
Hence  
\[
\begin{aligned}
S(N)&=N+\sum_{k=1}^{\infty}\lfloor N/2^k\rfloor 2^{-k}-2\sum_{k=1}^{\infty}\lfloor N/2^k\rfloor 2^{-k} \\
&= N-\sum_{k=1}^{\infty}\lfloor N/2^k\rfloor 2^{-k}.
\end{aligned}
\]

Write \(\lfloor N/2^k\rfloor = N/2^k - \{N/2^k\}\), where \(\{x\}\) denotes the fractional part of \(x\) (\(0\le\{x\}<1\)).  Substituting,
\[
\begin{aligned}
S(N)&=N-\sum_{k=1}^{\infty}\bigl(N/2^k-\{N/2^k\}\bigr)2^{-k} \\
&= N-N\sum_{k=1}^{\infty}2^{-2k}+\sum_{k=1}^{\infty}\{N/2^k\}2^{-k} \\
&= N-N\cdot\frac{1}{4}{1-\frac{1}{4}}^{-1}+\sum_{k=1}^{\infty}\{N/2^k\}2^{-k} \\
&= \frac{2}{3}N+E,
\end{aligned}
\]
where we have used \(\sum_{k=1}^{\infty}2^{-2k}= \frac{1}{4}\cdot\frac{1}{1-1/4}=\frac13\) and  
\[
E:=\sum_{k=1}^{\infty}\{N/2^k\}2^{-k}.
\]

Now bound \(E\).  Because \(0\le\{N/2^k\}<1\) for every \(k\), we have  
\[
0\le\{N/2^k\}2^{-k}<2^{-k}.
\]  
Thus the series of positive terms satisfies  
\[
0\le E<\sum_{k=1}^{\infty}2^{-k}=1.
\]  
Moreover \(E>0\).  Indeed, let \(v=v_2(N)\) be the exponent of \(2\) in the factorisation of \(N\); then \(N=2^v m\) with \(m\) odd.  For \(k=v+1\) we have \(N/2^{v+1}=m/2\) which is not an integer, so its fractional part is \(\frac12\).  Hence the term in the series corresponding to this \(k\) is \(\frac12\cdot2^{-(v+1)}=2^{-(v+2)}>0\), and consequently \(E>0\).

Therefore \(0<E<1\), i.e.  
\[
\Bigl|S(N)-\frac{2}{3}N\Bigr| = E < 1,
\]  
which is exactly what was to be proved.  ∎
