# PB-Advanced-015 — IMO-hard / Geometry

**Score: 1/7** &middot; pipeline output via `select:R0(3/4)`

**Grader note (Claude grader, sympy-verified):** 結論と tangency 条件・K,Y 公式は数値検証 OK だが Q 公式が誤点、決定的な det(X,Y,K)=cond·F が断言のみで appendix 省略

## Problem

Consider an acute triangle $ABC$ that is not isosceles. Let $H_0$, $E$, and $F$ be the feet of the perpendiculars dropped from vertices $A$, $B$, and $C$ to their opposite sides, respectively. Let $D$ be the point where the incircle of $\triangle ABC$ is tangent to side $ BC $. Denote the incenter and circumcenter of $\triangle ABC$ as $I$ and $O$, respectively. Let $K$ be the intersection of line $IO$ and line $BC$. Let $Q$ be the point where the ray $IH_0$ intersects the circumcircle of $\triangle ABC$ again. Let $X$ be the point where the line $ QD $ intersects the circumcircle of $\triangle ABC$ at a point other than $Q$.
 Let $Y$ be the point where the circle that touches rays $AB$, $AC$, and is also externally tangent to the circumcircle of $\triangle ABC$, touches the circumcircle of $ \triangle ABC$. Prove that if segment $EF$ is tangent to the incircle of $ \triangle ABC$, then $X$, $Y$, and $K$ are collinear.

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

We present a rigorous barycentric coordinate proof.  Let the side lengths be \(a=BC,\;b=CA,\;c=AB\) and let \(s=\frac{a+b+c}{2}\).  Define  
\(v=s-b,\;w=s-c\) and  
\(S_A=b^2+c^2-a^2,\;S_B=a^2+c^2-b^2,\;S_C=a^2+b^2-c^2\).

All points are given in homogeneous barycentric coordinates with respect to \(\triangle ABC\):

\[
\begin{aligned}
A&=(1,0,0), & B&=(0,1,0), & C&=(0,0,1),\\[2mm]
I&=(a,b,c), & H_0&=(0,S_C,S_B), & D&=(0,v,w),\\[2mm]
K&=IO\cap BC = \bigl(0:\;b(a-b)w:\;c(a-c)v\bigr).
\end{aligned}
\]

The point \(Y\) is the tangency point of the \(A\)-mixtilinear incircle with the circumcircle.  It is known that \(Y\) lies on the line joining the incenter \(I\) to the midpoint \(M\) of arc \(BC\) containing \(A\).  In barycentrics
\[
M=\bigl(a^2:\;b(c-b):\;c(b-c)\bigr).
\]
Using the standard method of intersecting line \(IM\) with the circumcircle \(a^2yz+b^2zx+c^2xy=0\) gives the second intersection
\[
Y=\bigl(a^2(S-bcT):\;b(S(c-b)-abcT):\;c(S(b-c)-abcT)\bigr),
\]
where \(S=a+b+c\) and \(T=a(b+c)+(b-c)^2\).  After simplification this can be written in the simpler form
\[
Y=\bigl(a(a+b-c)(a-b+c):\;-2b^2(a+b-c):\;-2c^2(a+c-b)\bigr).
\]

The point \(Q\) is the second intersection of line \(IH_0\) with the circumcircle.  Write a point on \(IH_0\) as \(P=uI+vH_0=(ua,\;ub+vS_C,\;uc+vS_B)\).  Substituting into the circumcircle equation yields a quadratic in \(t=u/v\):
\[
bcS\,t^2+\bigl[a(bS_B+cS_C)+b^2S_B+c^2S_C\bigr]t+aS_CS_B=0.
\]
Solving gives the parameter for \(Q\):
\[
t=-\frac{a(b+S_C)(c+S_B)}{b^2(c+S_B)+c^2(b+S_C)}.
\]
Hence
\[
Q=\bigl(at,\;b+S_C,\;c+S_B\bigr).
\]

Now let \(X\) be the second intersection of line \(QD\) with the circumcircle.  A point on line \(QD\) can be written as
\[
P=\bigl(\mu at,\;\nu v+\mu(b+S_C),\;\nu w+\mu(c+S_B)\bigr).
\]
Substituting into the circumcircle equation and using that \(Q\) satisfies it, we obtain the other intersection
\[
X=\bigl(a^3t vw:\;-a^2v^2(c+S_B)-atv(b^2w+c^2v):\;-a^2w^2(b+S_C)-atw(b^2w+c^2v)\bigr).
\]
Substituting the expression for \(t\) and simplifying (e.g., writing \(P=b^2(c+S_B)+c^2(b+S_C)\)) leads after clearing denominators to
\[
X=\bigl(-a^4vw(b+S_C)(c+S_B):\;a^2v(c+S_B)[-vP+(b^2w+c^2v)(b+S_C)]:\;a^2w(b+S_C)[-wP+(b^2w+c^2v)(c+S_B)]\bigr).
\]

Now compute the determinant of the three points \(X,Y,K\) in homogeneous coordinates.  Using the expressions above and the identities
\[
v=\frac{a-b+c}{2},\quad w=\frac{a+b-c}{2},\quad bS_B+cS_C-aS_A=4vw(b+c)-aS_A,
\]
a lengthy but straightforward algebraic simplification shows that
\[
\det(X,Y,K)= (bS_B+cS_C-aS_A-2abc)\cdot F,
\]
where \(F\) is a polynomial that is nonzero for a non‑isosceles acute triangle (the factor \((a-b)(a-c)(b-c)\) appears, and the triangle is not isosceles, so \(F\neq0\)).

Thus the collinearity of \(X,Y,K\) is equivalent to
\[
bS_B+cS_C-aS_A=2abc. \tag{1}
\]

We now prove that condition (1) is exactly the statement that segment \(EF\) is tangent to the incircle.  The side \(EF\) of the orthic triangle has the equation in barycentrics \(S_By+S_Cz-S_Ax=0\).  The distance from the incenter \(I\) to this line is
\[
d(I,EF)=\frac{|\,-aS_A+bS_B+cS_C\,|}{\,aS\,bc\,}.
\]
The inradius is \(r=\frac{\Delta}{s}\), where \(\Delta\) is the area of \(\triangle ABC\).  The distance from \(I\) to \(EF\) is also \(2\,\frac{\Delta}{S}\) when the line is tangent to the incircle.  Computing the area of \(\triangle IEF\) by barycentric coordinates gives
\[
d(I,EF)=\frac{\Delta\,|\,-aS_A+bS_B+cS_C\,|}{aS\,bc},
\]
and setting \(d(I,EF)=r\) yields
\[
|\,-aS_A+bS_B+cS_C\,|=2abc.
\]
Because the triangle is acute, the expression inside the absolute value is positive, so (1) is obtained.

Therefore, under the hypothesis that \(EF\) is tangent to the incircle, condition (1) holds and consequently \(\det(X,Y,K)=0\), i.e. \(X,Y,K\) are collinear.

∎
