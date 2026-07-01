# PB-Basic-015 — pre-IMO / Combinatorics

**Score: 7/7** &middot; pipeline output via `select:R0(3/4)`

**Grader note (Claude grader, sympy-verified):** Termination via decreasing width inversions + a rigorous induction on the invariant 'if the left is wider then the left is shorter'; the terminal state is sorted.

## Problem

Adrian is lining up $n \geq 2$ toy cars in a row. Each car has a width and length, and no two cars have the same width or length. Initially, the cars are arranged in increasing order of length from left to right. Adrian repeatedly does the following: he chooses some two adjacent cars where the left car is shorter in length and greater in width than the right car, and he swaps them. He keeps doing this until no further moves are possible. Prove that no matter how Adrian chooses his swaps, the procedure will eventually terminate, and in the end, the cars will be sorted in increasing order of width from left to right.

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

Let the cars be labeled by their length rank: car \(i\) has length \(i\) (so initially the order is \(1,2,\dots,n\)) and width \(w_i\) (all distinct).  
A configuration is a permutation \(\pi\) of \(\{1,\dots,n\}\) where \(\pi(k)\) is the car at position \(k\).  
A swap is allowed between adjacent positions \(k,k+1\) if  
\[
\pi(k) < \pi(k+1) \quad\text{and}\quad w_{\pi(k)} > w_{\pi(k+1)}.
\]

---

### 1. Termination

Define the number of inversions in width as  
\[
I(\pi)=\bigl|\{(i,j)\mid i<j,\; w_{\pi(i)} > w_{\pi(j)}\}\bigr|.
\]  
If a swap is performed on adjacent cars \(A\) (left) and \(B\) (right) with \(w_A > w_B\) and \(\pi(A)<\pi(B)\), then the pair \((A,B)\) is an inversion before the swap and becomes a non‑inversion after the swap. For any car \(C\) to the left of \(A\) or to the right of \(B\), the relative order with respect to \(A\) and \(B\) is unchanged, so the inversion status of all other pairs remains the same. Hence the total number of inversions decreases by exactly \(1\).  

Since \(I\) is a non‑negative integer, the process cannot continue indefinitely; it must terminate after at most \(I_{\text{initial}}\) swaps.

---

### 2. An invariant

**Invariant.** In every configuration reachable from the initial identity by allowed swaps, for all positions \(i<j\) we have  
\[
w_{\pi(i)} > w_{\pi(j)} \;\Longrightarrow\; \pi(i) < \pi(j).
\]  
(If a car to the left is wider, it must be shorter.)

*Proof by induction on the number of swaps.*  

*Base case:* Initially \(\pi(i)=i\) for all \(i\). For \(i<j\) we have \(\pi(i)=i<j=\pi(j)\), so the implication holds vacuously (the antecedent may be true, but the consequent is always true).  

*Inductive step.* Assume the invariant holds in some configuration \(C\). Perform an allowed swap on adjacent cars \(A\) (left) and \(B\) (right) with \(\pi(A)<\pi(B)\) and \(w_A > w_B\). After the swap the order becomes \(\dots, B, A, \dots\). We verify that the invariant still holds for all pairs.

- **Pairs involving a car \(X\) to the left of \(A\).** Before and after the swap, \(X\) is to the left of both \(A\) and \(B\), so the relative order of \(X\) with respect to \(A\) and \(B\) is unchanged. Hence the condition for the pairs \((X,A)\) and \((X,B)\) remains true.
- **Pairs involving a car \(Y\) to the right of \(B\).** Before and after the swap, \(Y\) is to the right of both \(A\) and \(B\), so the relative order of \(A\) and \(B\) with respect to \(Y\) is unchanged. Hence the condition for the pairs \((A,Y)\) and \((B,Y)\) remains true.
- **The pair \((B,A)\) after the swap.** We have \(w_B < w_A\), so the antecedent \(w_B > w_A\) is false; therefore the implication is vacuously true.
- **The pair \((A,B)\) before the swap.** It satisfied the invariant because \(\pi(A)<\pi(B)\) and \(w_A>w_B\). After the swap the pair \((A,B)\) no longer exists as an adjacent pair, but the invariant is checked only on the final order; the pair \((B,A)\) has already been handled.

Thus the invariant is preserved. By induction it holds for every configuration reachable from the initial one.

---

### 3. The final configuration is sorted by width

Suppose the process stops; no further swap is possible. Assume, for contradiction, that the widths are not in increasing order. Since all widths are distinct, there must be an adjacent pair \((i,i+1)\) with \(w_i > w_{i+1}\).  

By the invariant (applied to \(i<j\) with \(j=i+1\) and \(w_{\pi(i)} > w_{\pi(i+1)}\)), we have \(\pi(i) < \pi(i+1)\). Hence the pair satisfies  
\[
\pi(i) < \pi(i+1) \quad\text{and}\quad w_{\pi(i)} > w_{\pi(i+1)},
\]  
which is exactly the condition for an allowed swap. This contradicts the fact that no swap is possible.  

Therefore no such adjacent descent exists, and the widths are strictly increasing from left to right. Hence the final configuration is sorted in increasing order of width.

---

### 4. Conclusion

Regardless of the order in which Adrian chooses his swaps, the procedure always terminates and the final arrangement is the increasing‑width order. ∎
