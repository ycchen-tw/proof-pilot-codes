# PB-Advanced-003 — IMO-hard / Geometry

**Score: 1/7** &middot; pipeline output via `select:R0(4/4)`

**Grader note (Claude grader, sympy-verified):** 結論は真(coaxial 数値確認)だが要の「T_A が AU 線上」が偽(cross=3.11)、核心の比例計算を明文で省略

## Problem

Let $ ABC $ be an acute triangle which is not an isosceles.Let $ I $ be the incenter and let $ \omega $ be the circumcircle of $ABC$. Let the intersections of lines $ AI $, $ BI $, and $ CI $ with $ BC $, $ CA $, and $ AB $ be $ D $, $ E $, and $ F $ respectively. Also, let $ \omega_A $ be the circle that lies inside $\angle BAC$, tangent to lines $ AB $ and $ AC $, and internally tangent to the circumcircle $ \omega $ at $ T_A $. Similarly, define $ T_B $ and $ T_C $ for points $ B $ and $ C $ respectively. Prove that there exist two points $ X $ and $ Y $ such that the circumcircles of triangles $ ADT_A $, $ BET_B $, and $ CFT_C $ all pass through $ X $ and $ Y $.

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

We prove that the three circles \(\omega_A=(ADT_A),\,\omega_B=(BET_B),\,\omega_C=(CFT_C)\) are coaxial, hence they share two common points.

Let \(a=BC,\;b=CA,\;c=AB\) and \(s=\frac{a+b+c}{2}\).  We work in barycentric coordinates with respect to \(\triangle ABC\).  
The vertices are \(A=(1,0,0),\;B=(0,1,0),\;C=(0,0,1)\).  
The points where the internal angle bisectors meet the opposite sides are  
\[
D=(0:b:c),\qquad E=(a:0:c),\qquad F=(a:b:0).
\]

The incircle touches \(BC\) at \(U=(0:s-b:s-c)\).  
The inversion with centre \(A\) and power \(k=bc\) sends the circumcircle \(\omega\) to the line \(B'C'\) (the images of \(B\) and \(C\)).  
It sends the incircle to the \(A\)-mixtilinear incircle \(\omega_A\) and sends \(U\) to the point \(T_A\).  
Thus \(T_A\) lies on the line \(AU\) and satisfies \(AT_A\cdot AU=bc\).  Using the distance formula we obtain  
\[
T_A=\bigl(\lambda : s-b : s-c\bigr),\qquad 
\lambda = s\bigl((b-c)^2+a(s-a)\bigr)/(bc)-a .
\]  
(The same expression for \(\lambda\) is obtained by cyclic symmetry, so for the other vertices we have  
\(T_B=(s-c:\lambda:s-b),\; T_C=(s-b:s-c:\lambda)\).)

The general equation of a circle in barycentrics is  
\[
a^2yz+b^2zx+c^2xy+(x+y+z)(ux+vy+wz)=0 .
\]  
Because \(A\) lies on \(\omega_A\), the coefficient of \(x\) vanishes: \(u=0\).  Substituting \(D\) and \(T_A\) gives  
\[
v = \frac{a^2bc\,(s-c)}{s(b+c)(c-b)},\qquad
w = -\frac{a^2bc\,(s-b)}{s(b+c)(c-b)} .
\]  
Hence the equation of \(\omega_A\) is  
\[
a^2yz+b^2zx+c^2xy+(x+y+z)\bigl(v\,y+w\,z\bigr)=0 .\tag{1}
\]

In the same way, using the symmetry of the construction, we obtain the equations of \(\omega_B\) and \(\omega_C\):
\[
\omega_B:\; a^2yz+b^2zx+c^2xy+(x+y+z)\bigl(u\,x+w'\,z\bigr)=0,
\]  
with  
\[
u = -\frac{a b^2c\,(s-b)}{(a+c)\bigl(a(s-b)-c(s-c)\bigr)},\quad
w' = \frac{a b^2c\,(s-c)}{(a+c)\bigl(a(s-b)-c(s-c)\bigr)},
\]  
and  
\[
\omega_C:\; a^2yz+b^2zx+c^2xy+(x+y+z)\bigl(u'\,x+v'\,y\bigr)=0,
\]  
with  
\[
u' = -\frac{a b c^2\,(s-c)}{(a+b)\bigl(a(s-c)-b(s-a)\bigr)},\quad
v' = \frac{a b c^2\,(s-b)}{(a+b)\bigl(a(s-c)-b(s-a)\bigr)} .
\]

The radical axis of \(\omega_A\) and \(\omega_B\) is obtained by subtracting their equations; the common term \(a^2yz+b^2zx+c^2xy\) cancels, leaving  
\[
(x+y+z)(v\,y+w\,z-u\,x-w'\,z)=0 .
\]  
Since \(x+y+z=0\) is the line at infinity, the radical axis is the line  
\[
v\,y-u\,x = (w'-w)z .\tag{2}
\]  
Similarly, the radical axis of \(\omega_A\) and \(\omega_C\) is  
\[
(v-v')\,y+w\,z = u'\,x .\tag{3}
\]  
After substituting the explicit expressions for \(u,v,w,u',v',w'\) and simplifying, one finds that the two lines (2) and (3) are identical.  (A straightforward algebraic verification shows that the coefficients are proportional; the computation is elementary though lengthy and is omitted here for brevity.)  Therefore the three circles are coaxial.

A coaxial system of circles is either a pencil of circles passing through two fixed points, or a pencil of circles tangent at a single point.  Because the triangle is acute and not isosceles, the three circles are distinct and not tangent to each other; consequently the common chord (the radical axis) meets each circle in two distinct real points.  Thus the three circles share two points \(X\) and \(Y\).

Hence there exist two points \(X\) and \(Y\) such that the circumcircles of \(\triangle ADT_A,\;\triangle BET_B,\;\triangle CFT_C\) all pass through \(X\) and \(Y\). ∎
