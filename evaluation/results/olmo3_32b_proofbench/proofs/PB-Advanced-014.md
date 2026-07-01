# PB-Advanced-014 — IMO-medium / Combinatorics

**Score: 7/7** &middot; pipeline output via `select:R1(2/4)`

**Grader note (Claude grader, sympy-verified):** Answer matches the reference; the necessity of the mod-2/mod-4 invariants and the explicit constructions for the 4 sufficiency cases are verified in Python; fully self-contained.

## Problem

Two distinct positive integers \( a \) and \( b \) are written on a blackboard. At each step, you must choose one of the two operations — either adding 2 or multiplying by 3 — for each number separately, and apply the chosen operation to both numbers (possibly using different operations). You must apply an operation to both numbers every step. Find all pairs $(a, b)$ such that we can make the two numbers on the blackboard equal after a finite number of steps.

**Reference short answer:** $a$ and $b$ are both even, or $a$ and $b$ are both odd and have the same remainder when divided by 4.

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

**Solution.** We determine all pairs \((a,b)\) of distinct positive integers for which the two numbers can be made equal after a finite number of steps.  

---

### 1.  Necessary conditions

The two operations are:  
- \(x\mapsto x+2\) (adding \(2\)),  
- \(x\mapsto 3x\) (multiplying by \(3\)).  

Both operations preserve parity: adding \(2\) does not change parity, and multiplying by \(3\) (an odd number) also does not change parity. Hence the parity of each number is invariant. Consequently, if \(a\) and \(b\) have opposite parity, they can never become equal. Thus a necessary condition is  

\[
a\equiv b\pmod 2.
\]

Now assume that both \(a\) and \(b\) are odd.  Consider the effect of one operation modulo \(4\).  
- Adding \(2\): \(x\mapsto x+2\equiv x+2\pmod4\).  
- Multiplying by \(3\): \(3x\equiv -x\pmod4\). For an odd \(x\) we have \(-x\equiv x+2\pmod4\) because \(x\equiv1\) or \(3\) gives \(-x\equiv3\) or \(1\) respectively, which is exactly \(x+2\pmod4\).  

Thus every operation adds \(2\) modulo \(4\).  After \(t\) steps the number is congruent to the original plus \(2t\) modulo \(4\).  If after \(t\) steps the two numbers are equal, then  

\[
a+2t\equiv b+2t\pmod4\qquad\Longrightarrow\qquad a\equiv b\pmod4.
\]

Hence for odd numbers we must have  

\[
a\equiv b\pmod4.
\]

So the necessary conditions are:  

\[
a\equiv b\pmod2,\qquad\text{and if }a,b\text{ are both odd then }a\equiv b\pmod4.
\]

---

### 2.  Sufficiency

We show that every pair satisfying these conditions can indeed be made equal.

#### 2.1  Both numbers odd

Assume \(a,b\) are odd and \(a\equiv b\pmod4\).  Without loss of generality let \(a<b\).  Then \(b-a\) is a positive multiple of \(4\); write  

\[
b = a+4k,\qquad k\ge1.
\]

We construct two sequences of the same length that lead to the same number.

* For the smaller number \(a\):  
  perform \(r = 3k\) additions of \(2\), then one multiplication by \(3\).  
  \[
  a\;\xrightarrow{+\!2\text{ }r\text{ times}}\; a+2r\;\xrightarrow{\times3}\; 3a+6r.
  \]

* For the larger number \(b\):  
  perform one multiplication by \(3\) first, then \(r\) additions of \(2\).  
  \[
  b\;\xrightarrow{\times3}\; 3b\;\xrightarrow{+\!2\text{ }r\text{ times}}\; 3b+2r.
  \]

Now compute:  

\[
3a+6r = 3a+18k = 3(a+6k) = 3(a+4k+2k) = 3b+6k,
\]  
\[
3b+2r = 3b+6k.
\]

Thus both numbers become \(N = 3b+6k\) after exactly \(1+r = 1+3k\) steps.  Hence \((a,b)\) is solvable.

#### 2.2  Both numbers even

Write \(a=2A,\; b=2B\) with \(A,B\in\mathbb N\).  Since the condition is symmetric, we may assume \(a<b\); then \(B>A\).  Set  

\[
d = \frac{b-a}{2} = B-A>0.
\]

We treat two cases according to the parity of \(d\).

---

##### 2.2.1  \(d\) even  

Let \(r = \dfrac{3d}{2}\) (an integer because \(d\) is even).  

* For \(a\): perform \(r\) additions of \(2\) first, then one multiplication by \(3\).  
  \[
  a\;\xrightarrow{+\!2\text{ }r\text{ times}}\; a+2r\;\xrightarrow{\times3}\; 3a+6r.
  \]

* For \(b\): perform one multiplication by \(3\) first, then \(r\) additions of \(2\).  
  \[
  b\;\xrightarrow{\times3}\; 3b\;\xrightarrow{+\!2\text{ }r\text{ times}}\; 3b+2r.
  \]

Now  

\[
3a+6r = 6A+9d,\qquad
3b+2r = 6B+3d = 6(A+d)+3d = 6A+9d,
\]

so both equal \(N = 6A+9d\) after \(1+r\) steps.  Hence \((a,b)\) is solvable.

---

##### 2.2.2  \(d\) odd  

Now \(d\) is odd.  We split into two subcases.

**Subcase (i): \(b\ge 3a+2\)**  

Then \(b-3a+2\) is non‑negative and, because \(a,b\) are even, it is divisible by \(4\).  Set  

\[
\alpha = \frac{b-3a+2}{4},\qquad r = \max(1,\alpha).
\]

We use one multiplication for \(a\) and none for \(b\).

* For \(a\): perform \(\alpha\) additions of \(2\), then one multiplication by \(3\), then \(r-\alpha\) additions of \(2\).  
  \[
  a\;\xrightarrow{+\!2\text{ }\alpha}\; a+2\alpha\;\xrightarrow{\times3}\; 3a+6\alpha\;\xrightarrow{+\!2\text{ }(r-\alpha)}\; 3a+6\alpha+2(r-\alpha)=3a+4\alpha+2r.
  \]

* For \(b\): perform \(r+1\) additions of \(2\).  
  \[
  b\;\xrightarrow{+\!2\text{ }(r+1)}\; b+2(r+1).
  \]

Equality holds because  

\[
3a+4\alpha+2r = b+2r+2 \quad\Longleftrightarrow\quad 3a+4\alpha = b+2 \quad\Longleftrightarrow\quad \alpha = \frac{b-3a+2}{4},
\]

which is true by definition.  Both sequences use exactly \(r+1\) steps.

**Subcase (ii): \(b < 3a+2\)**  

Here \(b\) is strictly smaller than \(3a+2\).  Since \(a,b\) are even, this implies \(b \le 3a\) and consequently \(2A \ge d+1\).  Set  

\[
\gamma = \frac{3(2A-d)-1}{2},\qquad r = \max(1,\gamma).
\]

We use two multiplications for \(a\) and one for \(b\).

* For \(a\): perform two multiplications by \(3\) first, then \(r\) additions of \(2\).  
  \[
  a\;\xrightarrow{\times3}\;3a\;\xrightarrow{\times3}\;9a\;\xrightarrow{+\!2\text{ }r}\;9a+2r.
  \]

* For \(b\): perform \(\gamma\) additions of \(2\), then one multiplication by \(3\), then \(r+1-\gamma\) additions of \(2\).  
  \[
  b\;\xrightarrow{+\!2\text{ }\gamma}\; b+2\gamma\;\xrightarrow{\times3}\;3b+6\gamma\;\xrightarrow{+\!2\text{ }(r+1-\gamma)}\;3b+6\gamma+2(r+1-\gamma)=3b+2r+2+4\gamma.
  \]

Equality requires  

\[
9a+2r = 3b+2r+2+4\gamma \quad\Longleftrightarrow\quad 9a = 3b+2+4\gamma.
\]

Substituting \(a=2A,\; b=2A+2d\) gives  

\[
18A = 6A+6d+2+4\gamma \quad\Longrightarrow\quad 12A-6d-2 = 4\gamma \quad\Longrightarrow\quad \gamma = \frac{3(2A-d)-1}{2},
\]

which matches the definition of \(\gamma\).  Both sequences use \(2+r\) steps.

Thus in every subcase we have constructed explicit sequences of the same length that make the two numbers equal.  Consequently all pairs of even numbers are solvable.

---

### 3.  Conclusion

The necessary and sufficient condition for the existence of a finite sequence of operations that makes the two numbers equal is:

\[
\boxed{\,a\equiv b\pmod2,\;\text{and if }a\text{ and }b\text{ are both odd then }a\equiv b\pmod4\,}.
\]

This completes the solution.
