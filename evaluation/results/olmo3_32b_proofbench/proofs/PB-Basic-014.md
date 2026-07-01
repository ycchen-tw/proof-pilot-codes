# PB-Basic-014 — pre-IMO / Combinatorics

**Score: 7/7** &middot; pipeline output via `select:R0(2/4)`

**Grader note (Claude grader, sympy-verified):** The Mantel (triangle-free) upper bound and the full count (999415<1023132) are verified; the disproof is complete.

## Problem

In Shoreline Amphitheatre, 2024 Googlers each hold up to five flags of various colors. Any group of three Googlers will always have at least two people holding flags of the same color. Prove that one specific flag color is held by at least 200 Googlers.

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

We are given $2024$ Googlers, each holding at most five flags; each flag has a color. The condition: in any triple of Googlers, at least two hold a flag of the same color. We need to prove that some color is held by at least $200$ Googlers.

Let $G$ be the set of Googlers, $|G|=2024$. For each color $c$, let $a_c$ be the number of Googlers who have at least one flag of that color. We will show that $\max_c a_c \ge 200$.

Construct a graph $H$ on vertex set $G$ where two Googlers are adjacent if they do **not** share any color. The given condition implies that $H$ contains no triangle: if three Googlers were pairwise non‑adjacent in $H$, they would be pairwise color‑disjoint, contradicting the condition.

By Mantel’s theorem (the special case of Turán’s theorem for $K_3$), a triangle‑free graph on $n$ vertices has at most $\left\lfloor\frac{n^2}{4}\right\rfloor$ edges. For $n=2024$,
\[
\left\lfloor\frac{2024^2}{4}\right\rfloor = 1012^2 = 1\,024\,144.
\]
Thus the number of non‑sharing pairs in $G$ is at most $1\,024\,144$. The total number of unordered pairs of Googlers is $\binom{2024}{2}=2\,047\,276$, so the number of pairs that **do** share a color is at least
\[
2\,047\,276 - 1\,024\,144 = 1\,023\,132. \tag{1}
\]

Now count these sharing pairs by colors. For each color $c$, the pairs of Googlers that both have color $c$ are $\binom{a_c}{2}$. Since a pair may share several colors, we have
\[
\sum_c \binom{a_c}{2} \ge \text{(number of pairs sharing at least one color)} \ge 1\,023\,132. \tag{2}
\]

Every Googler holds at most five flags, so each Googler can have at most five distinct colors. Therefore
\[
\sum_c a_c \le 2024 \cdot 5 = 10\,120. \tag{3}
\]

Assume, for contradiction, that every color is held by at most $199$ Googlers, i.e., $a_c \le 199$ for all $c$. We will show that under this assumption the left‑hand side of (2) cannot reach $1\,023\,132$.

The function $f(x)=\binom{x}{2}=\frac{x(x-1)}{2}$ is convex for $x\ge0$. For a fixed total sum, the sum $\sum f(a_c)$ is maximized when the numbers are as unequal as possible. More formally, if two colors have sizes $x$ and $y$ with $x+y\le199$, then replacing them by a single color of size $x+y$ increases the sum because
\[
\binom{x+y}{2} - \binom{x}{2} - \binom{y}{2} = xy \ge 0.
\]
Thus, to maximize $\sum f(a_c)$ under the constraints $\sum a_c \le 10\,120$ and $a_c\le199$, we should take as many $199$'s as possible, and put the remaining sum into one additional color.

The maximum possible total sum is $10\,120$, so we take $\left\lfloor\frac{10\,120}{199}\right\rfloor = 50$ colors of size $199$ (since $199\cdot50 = 9\,950$), and the remainder $10\,120-9\,950 = 170$ as the size of one more color. Hence
\[
\sum_c \binom{a_c}{2} \le 50\binom{199}{2} + \binom{170}{2}.
\]
Compute:
\[
\binom{199}{2} = \frac{199\cdot198}{2}=199\cdot99 = 19\,701,\qquad
\binom{170}{2} = \frac{170\cdot169}{2}=170\cdot84.5 = 14\,365.
\]
Thus
\[
50\cdot19\,701 + 14\,365 = 985\,050 + 14\,365 = 999\,415. \tag{4}
\]

But (2) requires $\sum_c \binom{a_c}{2} \ge 1\,023\,132$, which contradicts (4). Therefore our assumption is false; there must exist a color $c$ with $a_c \ge 200$.

Hence one specific flag color is held by at least $200$ Googlers. ∎
