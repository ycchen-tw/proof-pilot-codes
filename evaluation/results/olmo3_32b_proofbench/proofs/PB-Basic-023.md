# PB-Basic-023 — IMO-medium / Number theory

**Score: 7/7** &middot; pipeline output via `select:R2(3/4)`

**Grader note (Claude grader, sympy-verified):** boxed{(3,1,1),(6,2,4)} matches. The LTE valuation and the full case split on b odd/even and t=0/t≥1 are rigorous; the solution set matches brute force.

## Problem

Suppose $a,b,c$ are positive integers such that $2^{a}+1=7^{b}+2^{c}$.
 Find all possible values of $(a,b,c)$.

**Reference short answer:** $(a,b,c) =( 3,1,1) ,( 6,2,4)$.

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

We are to find all positive integers \(a,b,c\) such that  
\[
2^{a}+1=7^{b}+2^{c}.
\]

---

### 1.  Preliminary observations

Since \(2^{a}\) and \(2^{c}\) are even, the left‑hand side is odd and the right‑hand side is odd, so parity gives no restriction.  
If \(a=c\) then \(2^{a}+1=7^{b}+2^{a}\) would force \(7^{b}=1\), impossible. Hence \(a>c\).  

Set \(d=a-c\ge 1\). Then  
\[
2^{c}(2^{d}-1)=7^{b}-1. \tag{1}
\]
Because \(2^{d}-1\) is odd, the exponent of \(2\) in the right‑hand side is exactly \(c\); therefore  
\[
c=v_{2}(7^{b}-1). \tag{2}
\]

---

### 2.  The 2‑adic valuation of \(7^{b}-1\)

For an odd prime \(p\) the Lifting‑the‑Exponent lemma gives  
\[
v_{2}(7^{n}-1)=
\begin{cases}
v_{2}(7-1)=1 & \text{if }n\text{ is odd},\\[2mm]
v_{2}(7-1)+v_{2}(7+1)+v_{2}(n)-1=1+3+v_{2}(n)-1=3+v_{2}(n) & \text{if }n\text{ is even}.
\end{cases}
\]  
Thus from (2)

\[
c=\begin{cases}
1 & \text{if }b\text{ is odd},\\[2mm]
3+v_{2}(b) & \text{if }b\text{ is even}.
\end{cases} \tag{3}
\]

---

### 3.  The case \(b\) odd

Then \(c=1\) and (1) becomes  
\[
2(2^{d}-1)=7^{b}-1\;\Longrightarrow\;7^{b}+1=2^{d+1}. \tag{4}
\]

If \(b=1\) we obtain \(7+1=8=2^{3}\), so \(d=2\) and \(a=c+d=1+2=3\). Hence \((a,b,c)=(3,1,1)\) is a solution.

If \(b\ge 3\) is odd, then \(7^{b}\equiv7\pmod{16}\) (since \(7^{2}\equiv1\pmod{16}\) and \(b\) odd), so \(7^{b}+1\equiv8\pmod{16}\). The only power of two congruent to \(8\) modulo \(16\) is \(8\) itself; therefore \(2^{d+1}=8\), i.e. \(d+1=3\) and \(7^{b}=7\), contradicting \(b\ge3\). Hence no further solution with odd \(b\) exists.

---

### 4.  The case \(b\) even

Write \(b=2k\) with \(k\ge1\). Then by (3),  
\[
c=3+v_{2}(b)=3+v_{2}(2k)=4+v_{2}(k).
\]  
Let \(v_{2}(k)=t\;(t\ge0)\); thus \(c=4+t\) and \(k=2^{t}u\) with \(u\) odd.  

Equation (1) becomes  
\[
2^{4+t}(2^{d}-1)=7^{2k}-1=(7^{k}-1)(7^{k}+1). \tag{5}
\]

---

#### 4.1  Subcase \(t=0\) (i.e. \(k\) odd)

For odd \(k\) we have  
\[
v_{2}(7^{k}-1)=1,\qquad v_{2}(7^{k}+1)=3.
\]  
Write  
\[
7^{k}-1=2A,\qquad 7^{k}+1=8B,
\]  
with \(A,B\) odd. Substituting into (5) gives  
\[
2^{4}(2^{d}-1)=16AB\;\Longrightarrow\;2^{d}-1=AB. \tag{6}
\]  
Also, from the two expressions we obtain  
\[
2A+2=8B\;\Longrightarrow\;A+1=4B,\quad\text{so}\quad A=4B-1. \tag{7}
\]  
Insert (7) into (6):  
\[
B(4B-1)=2^{d}-1\;\Longrightarrow\;4B^{2}-B+1=2^{d}. \tag{8}
\]  
Treat (8) as a quadratic in \(B\): \(4B^{2}-B+(1-2^{d})=0\). Its discriminant is  
\[
\Delta=1-16(1-2^{d})=16\cdot2^{d}-15=2^{d+4}-15.
\]  
For \(d\) odd, \(d+4\) is odd, so \(2^{d+4}\equiv2\pmod{3}\) and \(\Delta\equiv2-15\equiv2\pmod{3}\); squares modulo \(3\) are \(0,1\), contradiction. Hence \(d\) is even; write \(d=2e\). Then  
\[
\Delta=2^{2e+4}-15=m^{2}
\]  
for some integer \(m\). Factorising,
\[
(2^{e+2}-m)(2^{e+2}+m)=15.
\]  
Both factors are positive and have the same parity (odd, because \(2^{e+2}\) is even and \(m\) is odd). The factorisations of \(15\) into two odd positive factors are \((1,15)\) and \((3,5)\).

* \((1,15)\): \(2^{e+2}-m=1,\;2^{e+2}+m=15\) \(\Rightarrow\) \(2^{e+3}=16\) \(\Rightarrow\) \(e=1,\;d=2,\;m=7\). Then \(B=\frac{1+m}{8}=1\). From (7), \(A=4\cdot1-1=3\), so \(7^{k}-1=2A=6\) \(\Rightarrow\) \(k=1\). Hence \(b=2k=2\), \(c=4+t=4\), \(a=c+d=4+2=6\). This yields \((a,b,c)=(6,2,4)\).

* \((3,5)\): \(2^{e+2}-m=3,\;2^{e+2}+m=5\) \(\Rightarrow\) \(2^{e+3}=8\) \(\Rightarrow\) \(e=0,\;d=0\), impossible because \(d\ge1\).

Thus the only solution with \(t=0\) is \((6,2,4)\).

---

#### 4.2  Subcase \(t\ge1\) (i.e. \(k\) even)

Now \(k\) is even, so \(v_{2}(7^{k}-1)=3+t\) and \(v_{2}(7^{k}+1)=1\). Write  
\[
7^{k}-1=2^{3+t}A,\qquad 7^{k}+1=2B,
\]  
with \(A,B\) odd. Substituting into (5) gives  
\[
2^{4+t}(2^{d}-1)=2^{3+t}A\cdot2B=2^{4+t}AB\;\Longrightarrow\;2^{d}-1=AB. \tag{9}
\]  
From the two expressions we obtain  
\[
2^{3+t}A+2=2B\;\Longrightarrow\;2^{2+t}A+1=B. \tag{10}
\]  
Insert (10) into (9):  
\[
A\bigl(2^{2+t}A+1\bigr)=2^{d}-1. \tag{11}
\]  

Define  
\[
X=2^{3+t}A+1.
\]  
Then  
\[
X-1=2^{3+t}A,\qquad X+1=2^{3+t}A+2=2\bigl(2^{2+t}A+1\bigr)=2B.
\]  
Since \(A\) is odd, \(v_{2}(X-1)=3+t\); also \(2^{2+t}A+1\) is odd, so \(v_{2}(X+1)=1\). Hence  
\[
v_{2}\bigl((X-1)(X+1)\bigr)=(3+t)+1=4+t. \tag{12}
\]  

Now compute \(X^{2}\) using (11). From (11) we have  
\[
2^{d}=2^{2+t}A^{2}+A+1.
\]  
Multiply by \(2^{4+2t}\):
\[
2^{4+2t}\,2^{d}=2^{6+2t}A^{2}+2^{4+2t}A+2^{4+2t}.
\]  
On the other hand,
\[
X^{2}=(2^{3+t}A+1)^{2}=2^{6+2t}A^{2}+2^{4+2t}A+1.
\]  
Therefore  
\[
X^{2}=2^{4+2t}\,2^{d}-2^{4+2t}+1=2^{4+2t}(2^{d}-1)+1.
\]  
Thus  
\[
X^{2}-1=2^{4+2t}(2^{d}-1). \tag{13}
\]  
Since \(2^{d}-1\) is odd, the right‑hand side of (13) has \(2\)-adic valuation \(4+2t\). The left‑hand side is \((X-1)(X+1)\); by (12) its valuation is \(4+t\). Hence we must have  
\[
4+t=4+2t\quad\Longrightarrow\quad t=0,
\]  
contradicting \(t\ge1\). Therefore no solution exists for \(t\ge1\).

---

### 5.  Conclusion

The only positive integer triples \((a,b,c)\) satisfying \(2^{a}+1=7^{b}+2^{c}\) are  

\[
\boxed{(3,1,1)}\quad\text{and}\quad\boxed{(6,2,4)}.
\]
