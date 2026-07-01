# PB-Basic-016 — pre-IMO / Combinatorics

**Score: 7/7** &middot; pipeline output via `select:R0(4/4)`

**Grader note (Claude grader, sympy-verified):** Z3 辺差不変量 K、隣接が等しい時のみ再塗りの補題が正しく、K=52≠49 で到達不能を封鎖

## Problem

101 stones are arranged in a circle, numbered 1 through 101 in order (so that stone 1 is next to stone 101). Each stone is painted either red, white, or blue. Initially, stone 101 is the only blue stone. Among the remaining stones, even-numbered stones are red, and odd-numbered stones are white.

We perform a sequence of modifications to the coloring, where in each step, we may choose a stone and repaint it a different color, as long as we ensure that no two adjacent stones are ever the same color. Prove that it is not possible to eventually reach a state where again stone 101 is the only blue stone, but among the remaining stones, all even-numbered stones are white and all odd-numbered stones are red.

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

We assign to each color a number in \(\mathbb{Z}_3\): white \(=0\), red \(=1\), blue \(=2\).  
Let the stones be numbered \(1,2,\dots,101\) in order around the circle, with stone \(101\) adjacent to stone \(1\).  
A coloring is a function \(c:\{1,\dots,101\}\to\{0,1,2\}\) such that \(c(i)\neq c(i+1)\) for all \(i\) (indices taken modulo \(101\), so \(c(101)\neq c(1)\)).  

For each edge \((i,i+1)\) (with \(i=1,\dots,101\)) define the directed difference  
\[
\delta_i = c(i+1)-c(i) \pmod 3.
\]
Because adjacent stones have different colors, each \(\delta_i\) is non‑zero, hence \(\delta_i\in\{1,2\}\).

**Invariant.**  
Consider the number \(K\) of edges with \(\delta_i=1\).  
We claim that \(K\) is invariant under any allowed move.

*Proof of invariance.*  
Suppose we repaint stone \(v\) from its current color \(d\) to a different color \(e\) while keeping the whole coloring proper.  
Let the neighbours of \(v\) be \(u\) and \(w\).  
If \(c(u)\neq c(w)\), then the only color different from both \(c(u)\) and \(c(w)\) is the third color; but that third color is exactly \(d\) (since \(d\) is different from both). Hence no other color is available for a repaint, so such a move is impossible.  
Therefore a move can only occur when \(c(u)=c(w)\).  
Let \(c(u)=c(w)=c\). Because the coloring is proper, \(d\neq c\) and the allowed new color is the third colour \(e\) (the one different from \(c\) and \(d\)).

Before the move we have  
\[
\delta_{v-1}=c(v)-c(v-1)=d-c,\qquad \delta_v=c(v+1)-c(v)=c-d.
\]
Since \(d-c\in\{1,2\}\), the two differences are opposite: one is \(1\) and the other is \(2\).  
After the move, with \(c(v)=e\), we obtain  
\[
\delta'_{v-1}=e-c,\qquad \delta'_v=c-e.
\]
Because \(d\) and \(e\) are the two colors different from \(c\), the pair \(\{e-c,\,c-e\}\) is again \(\{1,2\}\), and exactly the same as before, but swapped: if \(\delta_{v-1}=1\) then \(\delta_v=2\) and \(\delta'_{v-1}=2\), \(\delta'_v=1\), and vice‑versa.  
Thus the two incident edges still contain exactly one edge with \(\delta=1\) and one with \(\delta=2\); the total number \(K\) of edges with \(\delta_i=1\) does not change.  
All other \(\delta_i\) are unchanged, so \(K\) is invariant. ∎

**Initial configuration.**  
Stone \(101\) is blue (\(2\)). For \(i=1,\dots,100\): odd \(i\) are white (\(0\)), even \(i\) are red (\(1\)).  
For \(i=1,\dots,99\):  
- if \(i\) is odd: \(c(i)=0,\;c(i+1)=1 \Rightarrow \delta_i=1\);  
- if \(i\) is even: \(c(i)=1,\;c(i+1)=0 \Rightarrow \delta_i=2\).  
There are \(50\) odd indices among \(1,\dots,99\), so \(50\) edges with \(\delta=1\) in this range.  
Edges \((100,101)\) and \((101,1)\):  
\(c(100)=1,\;c(101)=2 \Rightarrow \delta_{100}=1\);  
\(c(101)=2,\;c(1)=0 \Rightarrow \delta_{101}=0-2\equiv1\pmod3\).  
Thus \(K_{\text{initial}}=50+2=52\).

**Target configuration.**  
Stone \(101\) is blue (\(2\)). For \(i=1,\dots,100\): odd \(i\) are red (\(1\)), even \(i\) are white (\(0\)).  
For \(i=1,\dots,99\):  
- if \(i\) is odd: \(c(i)=1,\;c(i+1)=0 \Rightarrow \delta_i=2\);  
- if \(i\) is even: \(c(i)=0,\;c(i+1)=1 \Rightarrow \delta_i=1\).  
There are \(49\) even indices among \(1,\dots,99\), so \(49\) edges with \(\delta=1\) in this range.  
Edges \((100,101)\) and \((101,1)\):  
\(c(100)=0,\;c(101)=2 \Rightarrow \delta_{100}=2\);  
\(c(101)=2,\;c(1)=1 \Rightarrow \delta_{101}=1-2\equiv2\pmod3\).  
Thus \(K_{\text{target}}=49\).

Since \(K\) is invariant under allowed moves and \(52\neq49\), the target configuration cannot be reached from the initial configuration. ∎
