# PB-Advanced-026 — IMO-medium / Algebra

**Score: 1/7** &middot; pipeline output via `select:R2(3/4)`

**Grader note (Claude grader, sympy-verified):** lemma と核心の発想は妥当だが k≥3 の case 分析で k+1≤n≤2k-3(例 k=4,n=5)を欠落、実質的ギャップ

## Problem

Let $n$ and $k$ be positive integers with $k<n$. Let $P(x)$ be
 a polynomial of degree $n$ with real coefficients, nonzero constant
 term, and no repeated roots. Suppose that for any real numbers $a_{0},a_{1},\dots,a_{k}$
 such that the polynomial $a_{k}x^{k}+\dots+a_{1}x+a_{0}$ divides
 $P(x)$, the product $a_{0}a_{1}\dots a_{k}$ is zero. Prove that
 $P(x)$ has a non-real root.

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

Let \(P(x)\) be a polynomial of degree \(n\) with real coefficients, nonzero constant term, and no repeated roots. Suppose that for any real numbers \(a_0,\dots,a_k\) such that the polynomial \(a_k x^k+\dots+a_1 x+a_0\) divides \(P(x)\), the product \(a_0a_1\cdots a_k\) is zero. We must prove that \(P(x)\) has a non‑real root.

Assume, for contradiction, that all roots of \(P\) are real.  Then the roots are distinct and nonzero (the constant term is nonzero).  Denote the roots by \(r_1,\dots,r_n\).  For any subset \(S\subseteq\{1,\dots,n\}\) with \(|S|=k\), the monic polynomial \(\prod_{i\in S}(x-r_i)\) divides \(P\).  Its coefficients are (up to sign) the elementary symmetric sums \(e_1(S),\dots,e_k(S)\) of the numbers \(\{r_i:i\in S\}\).  The hypothesis forces that for every such \(S\) the product of the coefficients is zero, hence at least one of the symmetric sums \(e_1(S),\dots,e_{k-1}(S)\) is zero (the product of the roots is nonzero, so \(e_k(S)\neq0\)).  Therefore, if we can find a \(k\)-subset \(S\) for which all \(e_1(S),\dots,e_{k-1}(S)\) are nonzero, we obtain a contradiction.  Thus it suffices to prove the following lemma.

**Lemma.**  Let \(a_1,\dots,a_n\) be distinct nonzero real numbers and let \(k\) be an integer with \(1\le k<n\).  Then there exists a subset \(T\subseteq\{a_1,\dots,a_n\}\) of size \(k\) such that all elementary symmetric sums \(e_1(T),\dots,e_{k-1}(T)\) are nonzero.

*Proof of the lemma.*  We treat two cases.

**Case \(k=2\).**  Since \(n>2\), either there are at least two positive numbers or at least two negative numbers.  Taking those two numbers gives a pair whose sum is nonzero (because they have the same sign) and whose product is nonzero, so both \(e_1\) and \(e_2\) are nonzero.

**Case \(k\ge 3\).**  We consider two subcases according to the size of \(n\).

*Subcase \(n\ge 2k-1\).*  We construct a suitable subset greedily.  Start with the empty set \(S\).  For \(i=1,\dots,k\) we add an element from the remaining numbers such that the new set \(S\cup\{x\}\) has all elementary symmetric sums nonzero.  At the beginning of the \(i\)-th step we have a set \(S\) of size \(i-1\) with all symmetric sums nonzero.  The condition for the new element \(x\) to keep all symmetric sums nonzero is that for every \(j=1,\dots,i-1\) we must have  
\[
x\neq -\frac{e_j(S)}{e_{j-1}(S)},
\]  
because \(e_{j-1}(S)\neq0\) (by the inductive construction) and the coefficient of \(x^{k-j}\) in the product becomes \(e_j(S)+x\,e_{j-1}(S)\).  There are at most \(i-1\) forbidden values.  The number of remaining elements is \(n-(i-1)\).  Since \(n\ge 2k-1\), we have \(n-(i-1) > i-1\) for every \(i\le k\).  Hence there is always an element not among the forbidden ones; we choose it and add it to \(S\).  After \(k\) steps we obtain a set \(T\) of size \(k\) with all elementary symmetric sums nonzero.

*Subcase \(n=2k-2\).*  Because \(n>k\), the numbers cannot all be of the same sign (otherwise we could take any \(k\) of them and be done).  Let \(p\) be the number of positive numbers and \(q\) the number of negative numbers.  Then \(p+q=n=2k-2\).  If \(p\ge k\) or \(q\ge k\), we take \(k\) numbers of that sign and are done.  Hence we must have \(p\le k-1\) and \(q\le k-1\).  Together with \(p+q=2k-2\) this forces \(p=q=k-1\).  So the set consists of exactly \(k-1\) positive numbers \(a_1,\dots,a_{k-1}\) and \(k-1\) negative numbers \(b_1,\dots,b_{k-1}\).

Assume, for contradiction, that every \(k\)-subset has a zero elementary symmetric sum.  Consider the \(k\)-subsets consisting of all positives and one negative, i.e. \(S_b=\{a_1,\dots,a_{k-1},b\}\) for each negative \(b\).  For a fixed positive set, the elementary symmetric sums of \(S_b\) are  
\[
e_j(S_b)=e_j(a)+\,b\,e_{j-1}(a),\qquad j=1,\dots,k-1,
\]  
where \(e_j(a)\) are the elementary symmetric sums of the positives (with \(e_0(a)=1\)).  Since all \(a_i>0\), we have \(e_{j-1}(a)>0\) for every \(j\).  The condition that some \(e_j(S_b)=0\) is equivalent to  
\[
b=-\frac{e_j(a)}{e_{j-1}(a)}
\]  
for some \(j\) (because \(e_{j-1}(a)\neq0\)).  The numbers \(-\frac{e_j(a)}{e_{j-1}(a)}\) are \(k-1\) distinct negative numbers (the ratios are strictly decreasing by Newton’s inequalities for positive numbers).  Hence each negative \(b\) must be one of these numbers.  Since there are exactly \(k-1\) negatives, they are forced to be exactly the set  
\[
\left\{-\frac{e_j(a)}{e_{j-1}(a)}\;\Big|\;j=1,\dots,k-1\right\}.
\]  
In particular, the negatives are completely determined by the positives.

Now consider the \(k\)-subsets consisting of all negatives and one positive, i.e. \(T_a=\{b_1,\dots,b_{k-1},a\}\) for each positive \(a\).  Let \(q_j\) be the elementary symmetric sums of the absolute values of the negatives, i.e. \(q_j=e_j(|b_1|,\dots,|b_{k-1}|)\).  Because the negatives are all negative, the elementary symmetric sums of the negatives themselves are \((-1)^j q_j\).  For the set \(T_a\), the symmetric sums are  
\[
e_j(T_a)=e_j(b)+a\,e_{j-1}(b),\qquad j=1,\dots,k-1,
\]  
where \(e_j(b)\) are the elementary symmetric sums of the negatives.  Since the negatives are distinct and nonzero, we have \(e_{j-1}(b)\neq0\).  The condition that some \(e_j(T_a)=0\) gives  
\[
a=-\frac{e_j(b)}{e_{j-1}(b)}=-\frac{(-1)^j q_j}{(-1)^{j-1}q_{j-1}}=\frac{q_j}{q_{j-1}}.
\]  
Thus each positive \(a\) must be one of the numbers \(\frac{q_j}{q_{j-1}}\) for \(j=1,\dots,k-1\).  Because there are \(k-1\) positives, they are exactly this set.

Now the negatives are \(-\frac{e_j(a)}{e_{j-1}(a)}\), so their absolute values are \(\frac{e_j(a)}{e_{j-1}(a)}\).  Therefore the numbers \(q_j\) are the elementary symmetric sums of the numbers \(\frac{e_j(a)}{e_{j-1}(a)}\).  Consequently, the ratios \(\frac{q_j}{q_{j-1}}\) are the ratios of consecutive elementary symmetric sums of the numbers \(\frac{e_j(a)}{e_{j-1}(a)}\).  In particular, the first ratio is  
\[
\frac{q_1}{q_0}=q_1=\sum_{j=1}^{k-1}\frac{e_j(a)}{e_{j-1}(a)}.
\]  
But \(\frac{e_1(a)}{e_0(a)}=e_1(a)\) is the sum of the positives, so  
\[
\frac{q_1}{q_0}=e_1(a)+\frac{e_2(a)}{e_1(a)}+\cdots+\frac{e_{k-1}(a)}{e_{k-2}(a)}.
\]  
Thus \(\frac{q_1}{q_0}\) is a number that is strictly larger than \(e_1(a)\) because all terms are positive and at least one term is positive (the sum of the positives is positive and there are at least two positives, so \(e_1(a)\) is larger than any individual positive).  However, the set \(\{\frac{q_j}{q_{j-1}}\}\) is supposed to be the set of the positives themselves.  Hence one of the positives must equal \(\frac{q_1}{q_0}\), which is impossible because \(\frac{q_1}{q_0}>e_1(a)>\max\{a_1,\dots,a_{k-1}\}\).  This contradiction shows that our assumption was false; therefore there exists a \(k\)-subset with all elementary symmetric sums nonzero.

∎

Now we apply the lemma to the roots of \(P\).  The lemma gives a subset \(S\) of size \(k\) such that all \(e_1(S),\dots,e_{k-1}(S)\) are nonzero.  The monic polynomial \(Q(x)=\prod_{i\in S}(x-r_i)\) divides \(P(x)\), and its coefficients (up to sign) are these symmetric sums.  Since \(e_k(S)=\prod_{i\in S}r_i\neq0\) (all roots are nonzero), the product of the coefficients of \(Q\) is nonzero.  This contradicts the hypothesis that for every divisor of degree \(k\) the product of its coefficients is zero.  Hence our initial assumption that all roots of \(P\) are real is false.  Therefore \(P\) must have at least one non‑real root. ∎
