# PB-Basic-009 — IMO-easy / Combinatorics

**Score: 1/7** &middot; pipeline output via `select:R2(3/4)`

**Grader note (Claude grader, sympy-verified):** 答136と等号構成は正しいが下界証明に本質的欠陥：p≥2 を実質 p=2 と仮定し p≥3 未処理(反例多数)

## Problem

Let $a_1,a_2,...,a_{18}$ be 18 real numbers, not necessarily distinct, with average $m$. Let $A$ denote the number of triples $1 \le i < j < k \le 18$ for which $a_i + a_j + a_k \ge 3m$. What is the minimum possible value of $A$?

**Reference short answer:** $136$

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

We translate the problem so that the average is \(0\).  Let \(a_1,\dots,a_{18}\) be real numbers with \(\sum a_i=0\).  The number \(A\) of triples with sum \(\ge0\) is the same as in the original problem.  We prove that \(A\ge136\) and that this value is attainable.

**Construction.**  
Take \(a_1=17\) and \(a_2=a_3=\dots=a_{18}=-1\).  Then the average is \(0\).  Every triple containing the number \(17\) has sum \(17-2=15>0\); there are \(\binom{17}{2}=136\) such triples.  All other triples consist of three \(-1\)'s and are negative.  Hence \(A=136\) is achievable.

**Lower bound.**  
We show that for any choice of numbers with sum \(0\) we have \(A\ge136\).  Let the numbers be sorted: \(x_1\le x_2\le\cdots\le x_{18}\).  Since the sum is \(0\), the largest number \(x_{18}\) is non‑negative.  Denote by \(P\) the set of indices with \(x_i>0\) and by \(N\) the set with \(x_i\le0\).  Let \(p=|P|\).  

*Case \(p=1\).*  
Let the unique positive number be \(p>0\) and the others be negative (or zero).  For any two negatives \(y,z\) we have \(y+z\ge\sum_{\text{negatives}} y = -p\).  Hence \(p+y+z\ge0\) for every pair of negatives.  Thus every triple that contains the positive number is non‑negative, and there are \(\binom{17}{2}=136\) such triples.  Hence \(A\ge136\) (actually \(A=136\)).

*Case \(p\ge2\).*  
Let the two largest numbers be \(M\) and \(N\) (so \(M\ge N\ge0\)).  The sum of the remaining \(16\) numbers is \(-(M+N)\).  Write these numbers as \(-d_1,\dots,-d_{16}\) with \(d_i\ge0\).  Then \(\sum_{i=1}^{16} d_i = M+N\).  The triples that contain both \(M\) and \(N\) are exactly the \(16\) triples obtained by choosing one of the \(16\) numbers \(-d_i\).  Because the sum of all \(16\) numbers is \(-(M+N)\), for any \(i\) we have \(d_i\ge -(M+N)\) (since adding more non‑positive numbers makes the sum more negative).  Therefore  
\[
M+N+(-d_i)\ge M+N-(M+N)=0,
\]  
so all \(16\) triples are non‑negative.

Now consider the triples that contain exactly one of \(M\) or \(N\) and two of the numbers \(-d_i\).  There are \(2\binom{16}{2}=240\) such triples.  For a pair \((d_i,d_j)\) the triple with \(M\) is non‑negative iff \(d_i+d_j\le M\); the triple with \(N\) is non‑negative iff \(d_i+d_j\le N\).  Because \(M\ge N\), the condition for \(N\) is stronger.

Let  
\[
\begin{aligned}
A &= \{\text{pairs }(i,j)\mid d_i+d_j>M\},\\
B &= \{\text{pairs }(i,j)\mid N< d_i+d_j\le M\},\\
C &= \{\text{pairs }(i,j)\mid d_i+d_j\le N\}.
\end{aligned}
\]  
The number of non‑negative triples among the \(240\) is \(2|C|+|B|\).  Since \(|A|+|B|+|C|=120\), this equals \(240-2|A|-|B|\).

We prove that \(2|A|+|B|\le120\).  Consider two possibilities.

*If there exists an index \(k\) with \(d_k>M\).*  
Then the sum of the remaining \(15\) numbers is \(\sum_{i\ne k}d_i = M+N-d_k < N\).  Hence every pair among these \(15\) numbers has sum \(<N\), so none of them belongs to \(B\) or \(C\)? Actually, they have sum \(<N\), so they are in \(C\).  Moreover, any pair that contains \(d_k\) has sum \(>M\) (because \(d_k>M\) and the other is non‑negative), so all such pairs belong to \(A\).  Thus \(|A|=15\) (the pairs with \(d_k\)) and \(|B|=0\).  Consequently \(2|A|+|B|=30\le120\).

*If no \(d_i\) exceeds \(M\).*  
Then \(|A|=0\).  Clearly \(|B|\le120\), so \(2|A|+|B|\le120\).

Thus in all cases \(240-2|A|-|B|\ge120\).  Hence among the \(240\) triples that contain exactly one of \(M\) or \(N\) at least \(120\) are non‑negative.

Adding the \(16\) triples that contain both \(M\) and \(N\), we obtain at least \(16+120=136\) non‑negative triples.  Therefore \(A\ge136\).

Combining the two cases we have proved that for any set of \(18\) real numbers with average \(m\) the number \(A\) of triples with sum \(\ge3m\) is at least \(136\).  The construction shows that \(136\) is attainable, so the minimum possible value of \(A\) is \(\boxed{136}\).
