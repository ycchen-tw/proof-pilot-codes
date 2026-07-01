# PB-Basic-010 — IMO-easy / Combinatorics

**Score: 7/7** &middot; pipeline output via `select:R2(3/4)`

**Grader note (Claude grader, sympy-verified):** The identity D=1011(ΣB−ΣA) is verified at small scale; the total being odd ⇒ ΣA≠ΣB ⇒ D≠0; complete and concise.

## Problem

The numbers $\{ 1, 2, 3, \ldots , 2022 \}$ are partitioned into two sets $A$ and $B$ of size $1011$ each. Let $S_{AB}$ denote the set of all pairs $(a, b) \in A \times B$ where $a < b$, and let $S_{BA}$ denote the set of all pairs $(a, b) \in A \times B$ where $b < a$.

 Prove that $\sum_{(a, b) \in S_{AB}} (b - a) \neq \sum_{(a, b) \in S_{BA}} (a - b)$.

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

Let \(A\) and \(B\) be a partition of \(\{1,2,\dots,2022\}\) with \(|A|=|B|=1011\).  
Define  
\[
S_{AB}=\sum_{(a,b)\in A\times B,\ a<b}(b-a),\qquad 
S_{BA}=\sum_{(a,b)\in A\times B,\ b<a}(a-b).
\]

Consider the difference  
\[
D=S_{AB}-S_{BA}.
\]  
For every ordered pair \((a,b)\in A\times B\) we have  
\[
b-a=
\begin{cases}
b-a & \text{if }a<b,\\[2pt]
-(a-b) & \text{if }a>b.
\end{cases}
\]  
Summing over all pairs gives  
\[
\sum_{a\in A}\sum_{b\in B}(b-a)=\sum_{a<b}(b-a)+\sum_{b<a}(b-a)
=S_{AB}-\sum_{b<a}(a-b)=S_{AB}-S_{BA}=D.
\]

Now compute the double sum explicitly:
\[
\begin{aligned}
\sum_{a\in A}\sum_{b\in B}(b-a)
&=\sum_{a\in A}\Bigl(\sum_{b\in B}b-|A|a\Bigr)\\
&=|A|\sum_{b\in B}b-|A|\sum_{a\in A}a
=1011\bigl(\sum B-\sum A\bigr),
\end{aligned}
\]
where \(\sum A=\sum_{a\in A}a\) and \(\sum B=\sum_{b\in B}b\).

Hence  
\[
S_{AB}-S_{BA}=1011\bigl(\sum B-\sum A\bigr).
\]

The total sum of all numbers from \(1\) to \(2022\) is  
\[
\sum_{n=1}^{2022}n=\frac{2022\cdot2023}{2}=1011\cdot2023,
\]  
which is odd because both \(1011\) and \(2023\) are odd.  
Since \(A\) and \(B\) partition the set, \(\sum A+\sum B=1011\cdot2023\).  
If \(\sum A=\sum B\) then the total sum would be \(2\sum A\), an even number – a contradiction.  
Thus \(\sum A\neq\sum B\), and consequently \(S_{AB}-S_{BA}\neq0\).  

Therefore  
\[
\sum_{(a,b)\in S_{AB}}(b-a)\neq\sum_{(a,b)\in S_{BA}}(a-b),
\]  
as required.
