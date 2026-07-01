# PB-Basic-024 — IMO-medium / Number theory

**Score: 7/7** &middot; pipeline output via `select:R2(3/4)`

**Grader note (Claude grader, sympy-verified):** boxed(0,0,0) 一致。mod 11 で b^4 と −20^a の residue 集合が素(全数値検算)→c≥1 不可、reference より簡潔だが完全

## Problem

Find all non-negative integers $a,b,c$ such that $20^{a}+b^{4}=2024^{c}$

**Reference short answer:** $(a,b,c) = (0,0,0)$

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

We solve \(20^{a}+b^{4}=2024^{c}\) for non‑negative integers \(a,b,c\).

**Case \(c=0\).**  
Then \(2024^{0}=1\), so \(20^{a}+b^{4}=1\). Since \(20^{a}\ge1\) and \(b^{4}\ge0\), the only possibility is \(a=0\) and \(b=0\). Thus \((a,b,c)=(0,0,0)\) is a solution.

**Case \(c\ge1\).**  
Because \(2024=11\cdot184\), we have \(2024^{c}\equiv0\pmod{11}\). The equation gives  
\[
20^{a}+b^{4}\equiv0\pmod{11}.
\]

Now determine the possible residues modulo \(11\).

* For any integer \(b\), the fourth power modulo \(11\) can only be  
  \[
  b^{4}\equiv0,1,3,4,5,9\pmod{11}.
  \]  
  (Check \(b=0,1,\dots,10\): \(0^{4}=0\), \(1^{4}=1\), \(2^{4}=16\equiv5\), \(3^{4}=81\equiv4\), \(4^{4}=256\equiv3\), \(5^{4}=625\equiv9\), \(6^{4}=1296\equiv9\), \(7^{4}=2401\equiv3\), \(8^{4}=4096\equiv4\), \(9^{4}=6561\equiv5\), \(10^{4}=10000\equiv1\).)

* \(20\equiv9\pmod{11}\), so \(20^{a}\equiv9^{a}\pmod{11}\). The powers of \(9\) modulo \(11\) cycle with period \(5\):  
  \(9^{1}\equiv9\), \(9^{2}\equiv4\), \(9^{3}\equiv3\), \(9^{4}\equiv5\), \(9^{5}\equiv1\).  
  Hence for any \(a\ge0\),  
  \[
  20^{a}\pmod{11}\in\{1,3,4,5,9\}.
  \]

From the congruence \(20^{a}+b^{4}\equiv0\pmod{11}\) we obtain  
\[
b^{4}\equiv-20^{a}\pmod{11}\in\{10,8,7,6,2\}.
\]

The set \(\{10,8,7,6,2\}\) is disjoint from \(\{0,1,3,4,5,9\}\). Therefore no integer \(b\) can satisfy the required congruence for any \(a\). Consequently there is no solution with \(c\ge1\).

Thus the only solution in non‑negative integers is  
\[
\boxed{(a,b,c)=(0,0,0)}.
\]
