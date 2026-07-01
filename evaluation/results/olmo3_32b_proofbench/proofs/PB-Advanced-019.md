# PB-Advanced-019 — IMO-easy / Algebra

**Score: 7/7** &middot; pipeline output via `select:R0(3/4)`

**Grader note (Claude grader, sympy-verified):** 正解 ℕ；reformulation・dichotomy・逆向き検証まで自己完結、symbolic/brute で全確認

## Problem

For a real number $r$, let $A(r)$ denote the fractional part of $2r$ in its decimal representation. For a real number $r$ and a positive integer $n$, define $B(n,r)$ as
 $$
 B(n,r)=\sum_{k=1}^n A(kr).
 $$
 Find all positive real numbers $r$ such that $n(n+1)r - B(n,r)$ is a multiple of $n$ for all positive integers $n$.

**Reference short answer:** all integers

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

Let \(r>0\) and for a real number \(x\) denote the fractional part by \(\{x\}=x-\lfloor x\rfloor\).  
Define \(A(r)=\{2r\}\) and \(B(n,r)=\sum_{k=1}^{n}A(kr)=\sum_{k=1}^{n}\{2kr\}\).

The hypothesis is that \(n(n+1)r-B(n,r)\) is a multiple of \(n\) for every positive integer \(n\).  
Hence there exists an integer \(t\) such that  
\[
n(n+1)r-B(n,r)=nt\quad\Longleftrightarrow\quad B(n,r)=n\bigl((n+1)r-t\bigr).
\]  
Since each \(\{2kr\}\in[0,1)\), we have \(0\le B(n,r)<n\); therefore  
\[
0\le (n+1)r-t<1,
\]  
so \(t=\lfloor (n+1)r\rfloor\) and consequently  
\[
B(n,r)=n\bigl\{(n+1)r\bigr\}.
\]  
Thus the condition is equivalent to  
\[
\sum_{k=1}^{n}\{2kr\}=n\bigl\{(n+1)r\bigr\}\qquad\text{for all }n\ge1. \tag{1}
\]

Write \(r=m+\delta\) with \(m=\lfloor r\rfloor\in\mathbb{N}_0\) and \(\delta=\{r\}\in[0,1)\).  
Because \(\{2k(m+\delta)\}=\{2k\delta\}\) and \(\{(n+1)(m+\delta)\}=\{(n+1)\delta\}\), (1) becomes  
\[
\sum_{k=1}^{n}\{2k\delta\}=n\bigl\{(n+1)\delta\bigr\}\qquad\text{for all }n\ge1. \tag{2}
\]

If \(\delta=0\) then \(r\) is an integer. In this case \(\{2k\delta\}=0\) and \(\{(n+1)\delta\}=0\), so (2) holds trivially. Hence every positive integer satisfies the required condition.

Now suppose \(\delta>0\) and assume that (2) holds. We will obtain a contradiction.  

For each integer \(k\ge1\) set  
\[
a_k=\lfloor k\delta\rfloor,\qquad \delta_k=\lfloor 2\{k\delta\}\rfloor\in\{0,1\},
\]  
so that \(\{2k\delta\}=2\{k\delta\}-\delta_k=2(k\delta-a_k)-\delta_k=2k\delta-2a_k-\delta_k\).  
Substituting into (2) gives  
\[
\sum_{k=1}^{n}(2k\delta-2a_k-\delta_k)=n\bigl((n+1)\delta-a_{n+1}\bigr).
\]  
Simplifying:  
\[
2\delta\frac{n(n+1)}{2}-2\sum_{k=1}^{n}a_k-\sum_{k=1}^{n}\delta_k = n(n+1)\delta-n a_{n+1},
\]  
hence  
\[
2\sum_{k=1}^{n}a_k+\sum_{k=1}^{n}\delta_k = n a_{n+1}. \tag{3}
\]

Subtract (3) for \(n-1\) from (3) for \(n\) (valid for \(n\ge2\)):  
\[
2a_n+\delta_n = n a_{n+1}-(n-1)a_n = a_n + n(a_{n+1}-a_n),
\]  
so  
\[
a_n+\delta_n = n(a_{n+1}-a_n). \tag{4}
\]  
Because \(0<\delta<1\), we have \(a_{n+1}-a_n\in\{0,1\}\). Therefore the right‑hand side of (4) is either \(0\) or \(n\), and consequently  
\[
a_n+\delta_n\in\{0,n\}. \tag{5}
\]

We now translate (5) into inequalities for \(\delta\).

*If \(a_n+\delta_n=0\)*, then \(a_n=0\) and \(\delta_n=0\).  
\(a_n=0\) means \(n\delta<1\), i.e. \(\delta<\frac1n\).  
\(\delta_n=0\) means \(\{n\delta\}<\frac12\). For \(n\delta<1\) we have \(\{n\delta\}=n\delta\), so \(n\delta<\frac12\) i.e. \(\delta<\frac1{2n}\).  
Thus the first case is equivalent to \(\delta<\frac1{2n}\).

*If \(a_n+\delta_n=n\)*, then \(a_n=n-1\) and \(\delta_n=1\).  
\(a_n=n-1\) means \(n\delta\ge n-1\), i.e. \(\delta\ge 1-\frac1n\).  
\(\delta_n=1\) means \(\{n\delta\}\ge\frac12\). With \(a_n=n-1\) we have \(\{n\delta\}=n\delta-(n-1)=n(\delta-1)+1\); the inequality \(\{n\delta\}\ge\frac12\) becomes \(n(\delta-1)+1\ge\frac12\), i.e. \(\delta\ge 1-\frac1{2n}\).  
Thus the second case is equivalent to \(\delta\ge 1-\frac1{2n}\).

Hence for every integer \(n\ge2\) we must have  
\[
\delta<\frac1{2n}\quad\text{or}\quad \delta\ge 1-\frac1{2n}. \tag{6}
\]

Now assume \(\delta>0\). Because \(\frac1{2n}\to0\), we can choose an integer \(N\) such that \(\frac1{2N}<\delta\). For all \(n\ge N\) the first alternative in (6) is impossible, so we must have \(\delta\ge 1-\frac1{2n}\). But \(1-\frac1{2n}\) increases to \(1\) as \(n\to\infty\), and \(\delta<1\); therefore there exists some \(n\ge N\) for which \(1-\frac1{2n}>\delta\), contradicting \(\delta\ge 1-\frac1{2n}\). Hence no \(\delta\in(0,1)\) can satisfy (2).

Therefore \(\delta\) must be \(0\), i.e. \(r\) is an integer. Since \(r\) is positive, the only solutions are the positive integers.

Conversely, if \(r\) is a positive integer, then \(2kr\) is an even integer for every \(k\), so \(\{2kr\}=0\) and \(B(n,r)=0\). Then \(n(n+1)r\) is clearly a multiple of \(n\), so the condition holds.

\[
\boxed{\mathbb{N}}
\]
