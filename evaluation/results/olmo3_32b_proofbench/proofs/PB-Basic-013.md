# PB-Basic-013 — pre-IMO / Combinatorics

**Score: 7/7** &middot; pipeline output via `select:R1(2/4)`

**Grader note (Claude grader, sympy-verified):** 矛盾法+凸性最小化、d(c)≤4 と min Σbinom=30 を DP 検証、30≤·≤28 の矛盾が成立

## Problem

Each of 8 boxes contains 6 balls. Each ball has been colored with one of 22 colors. If no two balls in the same box are the same color, prove that there are two colors that occur together in more than one box.

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

We prove by contradiction.  
Assume that no two colors occur together in more than one box.

**Step 1: Consequences of the assumption.**  
For any two boxes, they cannot share two colors; otherwise that pair of colors would appear in both boxes, contradicting the assumption. Hence any two boxes share at most one color.

For each color \(c\) (there are 22 colors) let \(d(c)\) be the number of boxes that contain \(c\). Since each box contains 6 distinct colors, the total number of ball occurrences is \(8\cdot6=48\); therefore
\[
\sum_{c} d(c)=48.
\]

Fix a color \(c\). In each box that contains \(c\) there are 5 other colors. Because no two colors occur together in more than one box, the \(5\,d(c)\) pairs \((c,x)\) with \(x\neq c\) that appear together in some box are all distinct. There are only 21 other colors, so
\[
5\,d(c)\le 21 \quad\Longrightarrow\quad d(c)\le 4.
\]

**Step 2: Counting intersecting box pairs.**  
For a fixed color \(c\), the number of unordered pairs of boxes that both contain \(c\) is \(\binom{d(c)}{2}\). Since any two boxes share at most one color, these pairs are disjoint for different colors. Hence the total number of intersecting pairs of boxes equals
\[
\sum_{c}\binom{d(c)}{2}.
\]
There are \(\binom{8}{2}=28\) pairs of boxes in total, so
\[
\sum_{c}\binom{d(c)}{2}\le 28. \tag{1}
\]

**Step 3: A lower bound for \(\sum\binom{d(c)}{2}\).**  
We have the constraints
\[
\sum_{c} d(c)=48,\qquad 0\le d(c)\le 4,\qquad |\{c\}|=22.
\]
The function \(f(x)=\binom{x}{2}=\frac{x(x-1)}{2}\) is convex for \(x\ge0\). For a fixed sum, the sum of convex functions is minimized when the arguments are as equal as possible. The average value is \(48/22\approx2.1818\); the most equal integer distribution respecting \(d(c)\le4\) is four colors with \(d(c)=3\) and the remaining eighteen colors with \(d(c)=2\). For this distribution
\[
\sum_{c}\binom{d(c)}{2}=4\binom{3}{2}+18\binom{2}{2}=4\cdot3+18\cdot1=30.
\]
Any deviation from this distribution makes the numbers more unequal. For instance, replacing a \(2\) and a \(3\) by a \(1\) and a \(4\) (keeping the sum constant) increases the sum because \(\binom{1}{2}+\binom{4}{2}=0+6>1+3\). Therefore the minimum possible value of \(\sum\binom{d(c)}{2}\) is \(30\):
\[
\sum_{c}\binom{d(c)}{2}\ge 30. \tag{2}
\]

**Step 4: Contradiction.**  
From (1) and (2) we obtain \(30\le\sum\binom{d(c)}{2}\le28\), an impossibility. Hence our initial assumption is false, and there must exist two colors that occur together in more than one box. ∎
