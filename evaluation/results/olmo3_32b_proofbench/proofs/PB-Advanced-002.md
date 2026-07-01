# PB-Advanced-002 — IMO-medium / Combinatorics

**Score: 1/7** &middot; pipeline output via `select:R1(3/4)`

**Grader note (Claude grader, sympy-verified):** Counterexample to 'subset cycle length ≤|U|≤120' (a 12-orbit on 7 points); misses the core lcm-exponent argument; the bound 239 is wrong.

## Problem

There are 120 students in DeepMind highschool, and each student `loves' some of the students. Here `love' is not always a mutual relationship; a student A may love B while B may not love A, and it is also possible that a student loves oneself. For the set $F$ of all $2^{120}$ subsets of the students, define the function $f: F \rightarrow F$ as the function that maps each $X \in F$ to the set of students loved by one or more students in $X$. For $A, B \in F$, $A$ and $B$ are said to have a 'lovely relationship' iff there exists a natural number $k$ such that $f^{k}(A)=B$. Now we want to select distinct elements $A_{1}, A_{2}, \cdots A_{t}$ from $F$ such that for any $1 \leq i<j \leq t$, $A_{i}$ and $A_{j}$ have a lovely relationship. Let $M(f)$ be the maximum possible value of $t$.  Show that $M(f) \leq 2^{70}$.

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

Let \(V=\{1,\dots,120\}\) be the set of students. For each \(i\in V\) let \(L(i)\subseteq V\) be the set of students that \(i\) loves. The function \(f:2^V\to 2^V\) is defined by
\[
f(X)=\bigcup_{i\in X}L(i)\qquad (X\subseteq V).
\]
Two subsets \(A,B\) have a *lovely relationship* if there exists a natural number \(k\) with \(f^k(A)=B\).  
We are to choose distinct subsets \(A_1,\dots,A_t\) such that every pair is lovely; the maximum possible \(t\) is denoted \(M(f)\).  We shall prove \(M(f)\le 2^{70}\).

---

### 1.  Reduction to orbits

If \(A\) and \(B\) are lovely, then one can be obtained from the other by iterating \(f\).  Hence a family of pairwise lovely subsets is contained in a single orbit of the functional graph of \(f\).  Moreover, we may order the subsets so that each is the image of the preceding one; therefore the maximal length of a lovely family is the maximal length of a directed path (i.e. a chain) in the functional graph.  Thus it suffices to bound the length of any chain of distinct subsets that are reachable from each other.

---

### 2.  A height function that decreases

For a vertex \(v\in V\) define its **distance to a cycle** \(d(v)\) as the length of a longest simple directed path starting at \(v\) that ends at a vertex belonging to a directed cycle.  Because the graph is finite, \(d(v)\) is well‑defined.  For a vertex in a cycle we have \(d(v)=0\); for a vertex not on a cycle we have \(d(v)\ge 1\).

For a subset \(X\subseteq V\) set
\[
h(X)=\max_{v\in X}d(v)\quad\text{(with }h(\varnothing)=-1\text{)}.
\]

**Lemma.**  If \(h(X)>0\) then \(h(f(X))\le h(X)-1\).

*Proof.*  Choose a vertex \(v\in X\) with \(d(v)=h(X)\).  Because \(h(X)>0\), \(v\) is not on a cycle.  For any \(u\in L(v)\) we have \(d(u)\le d(v)-1\) (a longest path from \(u\) to a cycle can be extended by the edge \(v\to u\)).  Since \(f(X)=\bigcup_{w\in X}L(w)\), every element of \(f(X)\) is in some \(L(w)\) with \(w\in X\); consequently
\[
h(f(X))=\max_{u\in f(X)}d(u)\le d(v)-1=h(X)-1.
\]
∎

Now consider an orbit \(X_0,X_1,X_2,\dots\) with \(X_{i+1}=f(X_i)\).  The sequence \(h(X_i)\) is non‑increasing and strictly decreases whenever it is positive.  Since \(h(X_0)\le 119\) (the graph has only 120 vertices, a longest simple path has length at most \(119\)), there are at most \(119\) indices with \(h(X_i)>0\).  After that all sets have \(h=0\), i.e. they consist only of vertices that lie on cycles.  Hence the transient part of the orbit contains at most \(119\) distinct subsets.

---

### 3.  Bounding the length of a cycle

Let \(C\) be the set of vertices that belong to directed cycles.  The orbit after the height becomes zero is contained in the power set of \(C\).  Let \(U=\bigcup_{i\in\mathcal{I}}X_i\) be the union of the sets that belong to the cycle (the periodic part).  Then \(f(U)=U\), so \(U\) is a fixed point of \(f\).

We claim that any cycle of distinct subsets of \(U\) has length at most \(|U|\).

*Proof of the claim.*  Let \(X_0,X_1,\dots,X_{L-1}\) be a cycle with \(f(X_i)=X_{i+1}\) (indices modulo \(L\)) and assume \(L>|U|\).  Define the partial unions
\[
S_k=\bigcup_{j=0}^{k}X_j\qquad(k=0,\dots,L-1).
\]
These sets are increasing and \(S_{L-1}=U\).  Because \(L>|U|\), not every step can increase the union; there must be an index \(i\) with \(S_i=S_{i-1}\) (otherwise we would have \(L\) distinct elements, contradicting \(|U|<L\)).  Take the smallest such \(i\); then \(X_i\subseteq S_{i-1}\).

Since the cycle is periodic, \(X_{i+L}=X_i\).  Using the monotonicity of \(f\) (if \(A\subseteq B\) then \(f(A)\subseteq f(B)\)) we obtain
\[
X_{i+1}=f(X_i)\subseteq f(S_{i-1})=\bigcup_{j=0}^{i-1}f(X_j)=\bigcup_{j=0}^{i-1}X_{j+1}=S_{i-1}\cup X_i=S_{i-1}.
\]
By induction \(X_{i+t}\subseteq S_{i-1}\) for all \(t\ge0\).  Hence the whole cycle lies inside the power set of \(S_{i-1}\).  Moreover, \(U\subseteq S_{i-1}\) (because \(S_{i-1}\) already contains the union of the first \(i-1\) sets, and all later sets are subsets of it).  Thus we have a cycle of length \(L\) inside the functional graph on \(S_{i-1}\) with \(L>|S_{i-1}|\).  Repeating the same argument on this smaller set yields a strictly decreasing sequence of subsets of \(U\) – an impossibility, because the size of the union cannot decrease indefinitely.  Therefore \(L\le|U|\). ∎

Consequently the cycle part of the orbit has at most \(|U|\le|C|\le120\) distinct subsets.

---

### 4.  Putting the bounds together

Any chain of lovely subsets is contained in a single orbit, which consists of a transient part (at most \(119\) sets) followed by a cycle (at most \(120\) sets).  Hence the total number of distinct subsets in the chain is at most
\[
119+120=239.
\]
Since \(239<2^{70}\) (because \(2^{70}>10^{21}\)), we obtain \(M(f)\le2^{70}\).

∎
