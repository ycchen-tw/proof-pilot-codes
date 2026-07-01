# PB-Advanced-007 — IMO-easy / Algebra

**Score: 7/7** &middot; pipeline output via `select:R0(2/4)`

**Grader note (Claude grader, sympy-verified):** 構成 P=Q^11(x-1/2),Q=x^2+7/2 x を sympy で完全検算、自己完結で正しい

## Problem

Prove that there exist two real-coefficient polynomials $P(x)$ and $Q(x)$ satisfying the following condition:

 (Condition) The degree of the polynomial $P(x)$ is at least 2024, the degree of $Q(x)$ is at least 2, and for any real number $x$, the following holds:

 \[
 P(Q(x)-x-1)=Q(P(x))
 \]

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

We construct explicit polynomials \(P\) and \(Q\) satisfying the required condition.

Let  
\[
Q(x)=x^{2}+\frac{7}{2}x,\qquad L(x)=x-\frac12.
\]  
Then  
\[
Q(x)-x-1 = x^{2}+\frac72x-x-1 = x^{2}+\frac52x-1,
\]  
and  
\[
L\bigl(Q(x)-x-1\bigr) = \bigl(x^{2}+\frac52x-1\bigr)-\frac12 = x^{2}+\frac52x-\frac32.
\]  
On the other hand,  
\[
Q(L(x)) = Q\bigl(x-\tfrac12\bigr) = \bigl(x-\tfrac12\bigr)^{2}+\frac72\bigl(x-\tfrac12\bigr)
= x^{2}-\frac12x+\frac14+\frac72x-\frac74 = x^{2}+\frac52x-\frac32.
\]  
Thus we have the identity  
\[
L\bigl(Q(x)-x-1\bigr) = Q(L(x)) \qquad \text{for all } x. \tag{1}
\]

Now take any polynomial \(H\) that commutes with \(Q\), i.e. \(H(Q(y))=Q(H(y))\) for all \(y\).  Define \(P(x)=H(L(x))\).  Then  
\[
P\bigl(Q(x)-x-1\bigr)=H\bigl(L(Q(x)-x-1)\bigr)=H\bigl(Q(L(x))\bigr)
=Q\bigl(H(L(x))\bigr)=Q(P(x)),
\]  
so the required functional equation holds.

It remains to choose \(H\) so that \(\deg P\ge 2024\) and \(\deg Q\ge 2\).  Since \(Q\) is quadratic, \(\deg Q=2\) already.  For the iterates of \(Q\) we have \(Q^{k}(x)\) of degree \(2^{k}\).  Choose \(k\) with \(2^{k}\ge 2024\); for instance \(k=11\) gives \(2^{11}=2048\).  Set \(H(x)=Q^{11}(x)\).  Then  
\[
P(x)=Q^{11}\bigl(x-\tfrac12\bigr)
\]  
is a polynomial of degree \(2^{11}=2048\).  Because \(Q\) has real coefficients, all its iterates have real coefficients, so \(P\) also has real coefficients.  Thus the polynomials  
\[
P(x)=Q^{11}\bigl(x-\tfrac12\bigr),\qquad Q(x)=x^{2}+\frac72x
\]  
satisfy \(\deg P\ge 2024\), \(\deg Q\ge 2\), and the identity  
\[
P\bigl(Q(x)-x-1\bigr)=Q\bigl(P(x)\bigr) \quad\text{for all real } x.
\]  

Hence such polynomials exist.
