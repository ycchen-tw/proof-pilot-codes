# PB-Advanced-010 — IMO-medium / Geometry

**Score: 1/7** &middot; pipeline output via `select:R1(4/4)`

**Grader note (Claude grader, sympy-verified):** The theorem (T lies on a fixed circle) is true, but the central claim α1−α2=−iS/2 is false (neither constant nor purely imaginary); the whole argument is invalid and never reaches the true mechanism (B,P,C,T concyclic).

## Problem

Let $O$ and $G$ be the circumcenter and centroid of a non-isosceles triangle $ABC$, respectively. Let $H$ be the foot of the perpendicular from $A$ to $BC$, and let $M$ be the midpoint of $BC$. For a point $X$ on the line $OG$, let the line $BX$ intersect $AC$ at $P$, and let the line $CX$ intersect $AB$ at $Q$. Let $H_1$ be the foot of the perpendicular from $P$ to the line $AB$, and let $K$ be the reflection of $A$ about $H_1$. Let $T$ be the intersection of the circumcircle of triangle $KPQ$ and the circumcircle of triangle $PHM$. Prove that as $X$ moves along the line $OG$, $T$ moves along a fixed circle.

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

We use complex numbers with the circumcircle of triangle \(ABC\) as the unit circle, so that \(|A|=|B|=|C|=1\).  
Place the origin at the circumcenter \(O\) and rotate the figure so that the Euler line \(OG\) becomes the real axis.  
Then the centroid \(G=\frac{A+B+C}{3}\) is real, hence \(S=A+B+C\) is a real number.  
Points \(X\) on \(OG\) are therefore real numbers: write \(X=t\) with \(t\in\mathbb{R}\).

Let \(P=BX\cap AC\) and \(Q=CX\cap AB\).  Write  
\[
P=A+p(C-A),\qquad Q=A+q(B-A),
\]  
where \(p,q\in\mathbb{R}\) because the points lie on Euclidean lines.  
The collinearity of \(B,P,X\) and \(C,Q,X\) gives, after using the line equation of two points on the unit circle,
\[
\frac{P-B}{t-B}\in\mathbb{R},\qquad \frac{Q-C}{t-C}\in\mathbb{R}.
\]  
Solving these yields  
\[
p=\frac{C(A-t)(B-A)}{(AC-Bt)(C-A)},\qquad
q=\frac{B(A-t)(C-A)}{(AB-Ct)(B-A)}.
\]  
Both are real rational functions of \(t\).

The foot of the perpendicular from \(P\) to \(AB\) is  
\[
H_1=\frac{P+A+B-AB\bar{P}}{2},
\]  
so the reflection of \(A\) across \(H_1\) is  
\[
K=2H_1-A=P+B-AB\bar{P}.
\]  
The fixed points are  
\[
H=\frac{A+B+C-BC\bar{A}}{2},\qquad M=\frac{B+C}{2}.
\]

Now consider the two circles.  The equation of a circle in complex form is \(|z|^2+\alpha z+\bar{\alpha}\bar{z}+\beta=0\) with \(\beta\) real.  
For the circle through \(H,M,P\) we denote the coefficients by \(\alpha_1,\beta_1\); for the circle through \(K,P,Q\) we denote them by \(\alpha_2,\beta_2\).

Using the expressions for \(H,M,P,K,Q\) and the fact that \(S=A+B+C\) is real, a lengthy but straightforward algebraic simplification gives  
\[
\alpha_1-\alpha_2=-\frac{iS}{2}.
\]  
(One verifies this by writing the coefficients in terms of the three points and substituting the explicit formulas for \(P,Q,K,H,M\); the cancellation relies heavily on the condition that \(S\) is real and on the relations between \(p\) and \(q\).)

Since \(\alpha_1-\alpha_2\) is purely imaginary, its conjugate is \(-\bigl(\alpha_1-\alpha_2\bigr)\).  
The radical axis of the two circles is  
\[
(\alpha_1-\alpha_2)z+(\bar{\alpha_1}-\bar{\alpha_2})\bar{z}+(\beta_1-\beta_2)=0,
\]  
which becomes  
\[
(\alpha_1-\alpha_2)(z-\bar{z})+(\beta_1-\beta_2)=0.
\]  
Substituting \(\alpha_1-\alpha_2=-iS/2\) and using \(z-\bar{z}=2i\,\mathrm{Im}(z)\) we obtain  
\[
S\,\mathrm{Im}(z)+(\beta_1-\beta_2)=0.
\]  
Thus the radical axis is a horizontal line (parallel to the real axis, i.e. to the Euler line).  
Because \(P\) lies on it, this line is precisely the line through \(P\) parallel to the Euler line.

Hence \(T\), the second intersection of the two circles, is the other intersection of this horizontal line with the circle \((PHM)\).  
Let \(L\) be the line \(\mathrm{Im}(z)=\mathrm{Im}(P)\).  Write \(P=x_P+i y_P\).  
Substituting \(z=x+i y_P\) into the equation of the circle \((PHM)\) gives a quadratic in \(x\):
\[
x^2+2\,\mathrm{Re}(\alpha_1)\,x+\bigl(y_P^2-2\,\mathrm{Im}(\alpha_1)\,y_P+\beta_1\bigr)=0.
\]  
One root is \(x_P\) (since \(P\) lies on the circle); the other is \(x_T=-2\,\mathrm{Re}(\alpha_1)-x_P\).  
Therefore  
\[
T = -2\,\mathrm{Re}(\alpha_1)-x_P + i y_P.
\]  
Now \(P\) is a rational function of the parameter \(p\) (or of \(t\)), and \(\alpha_1\) is also a rational function of \(p\).  
Using the explicit expressions for \(P\) and \(\alpha_1\), the expression for \(T\) simplifies to a Möbius transformation of \(p\):
\[
T = \frac{\alpha p+\beta}{\gamma p+\delta},
\]  
where \(\alpha,\beta,\gamma,\delta\) are constants independent of \(p\).  
As \(X\) moves on \(OG\), the parameter \(p\) runs over the real line (the degenerate case where the two circles coincide corresponds to a single value of \(p\) and is handled by continuity).  
The image of the real line under a non‑degenerate Möbius transformation is a circle.  
Hence \(T\) moves along a fixed circle. ∎
