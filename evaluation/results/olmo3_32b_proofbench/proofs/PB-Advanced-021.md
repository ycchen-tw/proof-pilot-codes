# PB-Advanced-021 — IMO-hard / Combinatorics

**Score: 1/7** &middot; pipeline output via `select:R2(4/4)`

**Grader note (Claude grader, sympy-verified):** 「new 数無限・1 無限出現」は正しい(部分点)が「片側が恒等的に 1」が誤り(実測で 1..8)、本質的ギャップ

## Problem

Infinitely many boys and girls stand in a line alternatingly. For
 a given positive integer $N$, they choose positive integers according
 to the following rules:

 (1) The first $N$ people in the line choose any positive integers
 they want.

 (2) For each $m>N$, the $m$-th person chooses the number that is
 one more than the number of appearances of the number chosen by the
 $(m-1)$-th person appears among the numbers chosen by the first $m-2$
 people.

 Let $b_{i}$ be the number chosen by the $i$-th boy, and $g_{i}$
 be the number chosen by the $i$-th girl. Prove that at least one
 of the following holds:

 (i) There exists a sufficiently large integer $M$ such that $\{b_{n}\}_{n\ge M}$
 is a periodic sequence.

 (ii) There exists a sufficiently large integer $M$ such that $\{g_{n}\}_{n\ge M}$
 is a periodic sequence.

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

Let \(a_n\) be the number chosen by the \(n\)-th person. For \(n>N\) we have  
\[
a_n = 1 + \#\{i\le n-2 : a_i = a_{n-1}\}.
\]  
Define \(f_n(x) = \#\{i\le n : a_i = x\}\). Then for \(n\ge N+1\) we obtain  
\[
a_{n+1} = 1 + f_{n-1}(a_n). \tag{1}
\]

A number \(a_k\) is called **new** if it appears for the first time at index \(k\) (i.e. \(f_{k-1}(a_k)=0\)). From (1) we get  
\[
a_k \text{ new } \;\Longrightarrow\; a_{k+1}=1,\qquad a_{k+1}=1 \;\Longrightarrow\; a_k \text{ new}. \tag{2}
\]  
Thus every \(1\) is immediately preceded by a new number, and every new number is followed by a \(1\).

**Infinitely many new numbers.** If only finitely many new numbers existed, then all terms would belong to a finite set \(S\). For any \(x\in S\) the frequency \(f_n(x)\) grows without bound; choose \(x\) with the largest value in \(S\). For sufficiently large \(n\) we would have \(f_{n-1}(x) > \max S\), so the term after an occurrence of \(x\) would exceed \(\max S\), contradicting that all terms lie in \(S\). Hence there are infinitely many new numbers. Let \(n_1<n_2<\cdots\) be their indices and let \(x_i = a_{n_i}\).

**Counting the \(1\)’s.** Let \(C\) be the number of \(1\)’s among the first \(N\) terms. Because each new number gives a \(1\) at its index \(+1\) and the indices of the first \(i-1\) new numbers are all \(< n_i\), the \(1\)’s from these new numbers are all contained in the first \(n_i\) terms. Therefore for every \(i\ge 1\)  
\[
f_{n_i}(1) = C + (i-1). \tag{3}
\]

**The term after a new number.** Applying (1) with \(n = n_i\) gives  
\[
a_{n_i+2} = 1 + f_{n_i}(1) = i + C. \tag{4}
\]

**Eventually \(i+C\) is new.** The initial segment contains only finitely many numbers, so there exists an integer \(I\) such that for all \(i\ge I\) the number \(i+C\) is not among the first \(N\) terms. For such \(i\) the number \(i+C\) has not appeared before; consequently it is a new number. Hence for every \(i\ge I\), \(a_{n_i+2}=i+C\) is new, and therefore the next new number occurs at index \(n_{i+1}=n_i+2\).

**Parity stabilisation.** For \(i\ge I\) the indices of the new numbers differ by \(2\), so they all have the same parity. The \(1\)’s are at the positions \(n_i+1\) (by (2)), and these indices have the opposite parity. Hence for all sufficiently large indices of that parity the value is \(1\).

**Conclusion.** The people stand in an alternating line. Without loss of generality we may assume that the first person is a boy (otherwise swap the names); then boys are at odd indices and girls at even indices. The parity of the indices of the \(1\)’s is fixed, so either all boys (if the \(1\)’s are at odd indices) or all girls (if the \(1\)’s are at even indices) are eventually constant \(1\)’s. A constant sequence is periodic. Thus at least one of the sequences \(\{b_n\}_{n\ge M}\) or \(\{g_n\}_{n\ge M\}\) is eventually periodic. ∎
