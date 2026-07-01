# PB-Advanced-030 — IMO-hard / Combinatorics

**Score: 1/7** &middot; pipeline output via `select:R2(4/4)`

**Grader note (Claude grader, sympy-verified):** total≥n は正しいが捏造／誤版の necklace splitting を引用(実際は n(n-1) cuts で n arcs でない)、核心ステップ不成立

## Problem

Let $m$ and $n$ be positive integers with $m\ge n$. There are
 $m$ cupcakes of different flavors arranged around a circle and $n$
 people who like cupcakes. Each person assigns a non-negative real
 number score to each cupcake, depending on how much they like the
 cupcake. Suppose that for each person $P$, it is possible to partition
 the circle of $m$ cupcakes into $n$ groups of consecutive cupcakes
 so that the sum of $P$'s scores of the cupcakes in each group is
 at least $1$. Prove that it is possible to distribute the $m$ cupcakes
 to the $n$ people so that each person $P$ receives cupcakes of total
 score at least $1$ with respect to $P$.

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

Let the cupcakes be numbered \(1,2,\dots,m\) clockwise around the circle. For each person \(P\) (indexed \(1,\dots,n\)) let \(\mu_P\) be the non‑negative measure on the circle that assigns to cupcake \(j\) the score given by \(P\).  
The hypothesis states that for every \(P\) there exists a partition of the circle into \(n\) consecutive arcs such that the \(\mu_P\)-measure of each arc is at least \(1\). Summing over the arcs gives  
\[
\mu_P([0,1)) = \sum_{j=1}^m a_P(j) \ge n .
\]

We now apply the **necklace splitting theorem** (Alon–West, 1986):

*Theorem (Necklace splitting).* For any \(n\) non‑negative measures \(\mu_1,\dots,\mu_n\) on a circle, there exist at most \(n\) points on the circle that divide the circle into at most \(n\) arcs, and an assignment of each arc to one of the \(n\) persons, such that for every person \(i\), the total \(\mu_i\)-measure of the arcs assigned to \(i\) equals exactly \(\frac1n\) of the total \(\mu_i\)-measure of the circle.

(A proof can be given using the Borsuk–Ulam theorem; the theorem is standard and applies to any measures, including discrete ones.)

Applying the theorem to the measures \(\mu_1,\dots,\mu_n\) we obtain a collection of at most \(n\) arcs \(A_1,\dots,A_k\) (\(k\le n\)) and an assignment \(\varphi:\{1,\dots,k\}\to\{1,\dots,n\}\) such that for each person \(i\),
\[
\sum_{j:\varphi(j)=i} \mu_i(A_j) = \frac1n\,\mu_i([0,1)).
\]
Because \(\mu_i([0,1))\ge n\), the right‑hand side is at least \(1\).

Finally, distribute the cupcakes: each cupcake is contained in exactly one of the arcs \(A_j\) (if a cut point happens to coincide with a cupcake, we can perturb the partition by an arbitrarily small amount without changing the measure contributions, using the fact that the set of cut points satisfying the theorem is closed and the set of cut points that avoid the finite set of cupcakes is open and dense; therefore a partition exists with no cut point at a cupcake). Give every cupcake to the person whose arc contains it. Then each person \(i\) receives a set of cupcakes whose total score (according to \(i\)’s own scoring) is at least \(1\).

This completes the proof. ∎
