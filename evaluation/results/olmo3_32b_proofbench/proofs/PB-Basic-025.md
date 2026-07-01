# PB-Basic-025 — IMO-easy / Geometry

**Score: 7/7** &middot; pipeline output via `select:R0(3/4)`

**Grader note (Claude grader, sympy-verified):** MN⊥OI を検証(sympy=0,数値90°)、自己完結なベクトル証明、γ/2=45 で reference 一致

## Problem

Given a triangle $XYZ$ with circumcenter $O$, the incircle of triangle
 $XYZ$ has center $I$. Let $M,N$ on the sides $XY,XZ$
 respectively such that $YM=ZN=YZ$. If $\gamma$ is the angle created
 by two lines $MN,OI$, what is $\frac{\gamma}{2}$ in terms of degree?

**Reference short answer:** 45

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

Let the side lengths of triangle \(XYZ\) be  
\[
a = YZ,\qquad b = ZX,\qquad c = XY.
\]  
The points \(M\) on \(XY\) and \(N\) on \(XZ\) satisfy \(YM = ZN = a\); therefore \(a\le c\) and \(a\le b\).  
If \(a=b=c\) the triangle is equilateral, then \(M=N=X\) and the line \(MN\) is not defined; we exclude this degenerate case (the problem statement implicitly assumes a non‑degenerate configuration).  

Place the circumcenter \(O\) at the origin.  Denote the position vectors of the vertices by  
\[
\vec x = \overrightarrow{OX},\qquad \vec y = \overrightarrow{OY},\qquad \vec z = \overrightarrow{OZ}.
\]  
All have length \(R\) (the circumradius): \(|\vec x|=|\vec y|=|\vec z|=R\).

The incenter \(I\) has barycentric coordinates \((a:b:c)\) with respect to the vertices, so  
\[
\overrightarrow{OI}= \frac{a\vec x + b\vec y + c\vec z}{a+b+c}.
\]  
Thus the vector \(\vec v = a\vec x + b\vec y + c\vec z\) is parallel to \(\overrightarrow{OI}\).

Now express \(M\) and \(N\) using the given lengths.  Since \(M\) lies on \(XY\) with \(YM = a\),  
\[
M = Y + \frac{a}{c}(X-Y) = \frac{a}{c}\,X + \frac{c-a}{c}\,Y,
\]  
so  
\[
\overrightarrow{OM} = \frac{a}{c}\,\vec x + \frac{c-a}{c}\,\vec y.
\]  
Similarly, \(N\) lies on \(XZ\) with \(ZN = a\),  
\[
N = Z + \frac{a}{b}(X-Z) = \frac{a}{b}\,X + \frac{b-a}{b}\,Z,
\]  
so  
\[
\overrightarrow{ON} = \frac{a}{b}\,\vec x + \frac{b-a}{b}\,\vec z.
\]  

Hence  
\[
\overrightarrow{MN} = \overrightarrow{ON}-\overrightarrow{OM}
= \frac{a}{b}\vec x + \frac{b-a}{b}\vec z - \frac{a}{c}\vec x - \frac{c-a}{c}\vec y
= a\Bigl(\frac1b-\frac1c\Bigr)\vec x + \frac{b-a}{b}\vec z - \frac{c-a}{c}\vec y.
\]  
Because \(\frac1b-\frac1c = \frac{c-b}{bc}\), we obtain  
\[
\overrightarrow{MN} = \frac{a(c-b)}{bc}\,\vec x + \frac{b-a}{b}\,\vec z - \frac{c-a}{c}\,\vec y.
\]

Now compute the dot product \(\overrightarrow{MN}\cdot\vec v\).  For any two vertices \(U,V\) with side length \(UV = s\), the law of cosines gives  
\[
\overrightarrow{OU}\cdot\overrightarrow{OV} = \frac{2R^2 - s^2}{2}.
\]  
Thus  
\[
\begin{aligned}
\vec x\cdot\vec v &= aR^2 + b\,\frac{2R^2-c^2}{2} + c\,\frac{2R^2-b^2}{2}
= R^2(a+b+c) - \frac{bc(b+c)}{2},\\[2mm]
\vec y\cdot\vec v &= a\,\frac{2R^2-c^2}{2} + bR^2 + c\,\frac{2R^2-a^2}{2}
= R^2(a+b+c) - \frac{ac(a+c)}{2},\\[2mm]
\vec z\cdot\vec v &= a\,\frac{2R^2-b^2}{2} + b\,\frac{2R^2-a^2}{2} + cR^2
= R^2(a+b+c) - \frac{ab(a+b)}{2}.
\end{aligned}
\]  
Let \(T = a+b+c\).  Substituting these into \(\overrightarrow{MN}\cdot\vec v\),

\[
\begin{aligned}
\overrightarrow{MN}\cdot\vec v &=
\frac{a(c-b)}{bc}\Bigl(R^2T - \frac{bc(b+c)}{2}\Bigr)
+ \frac{b-a}{b}\Bigl(R^2T - \frac{ab(a+b)}{2}\Bigr)
- \frac{c-a}{c}\Bigl(R^2T - \frac{ac(a+c)}{2}\Bigr).
\end{aligned}
\]

The coefficient of \(R^2T\) is  
\[
\frac{a(c-b)}{bc} + \frac{b-a}{b} - \frac{c-a}{c}
= \frac{a(c-b) + c(b-a) - b(c-a)}{bc} = 0.
\]  
The remaining constant terms are  
\[
\frac{a(c-b)}{bc}\Bigl(-\frac{bc(b+c)}{2}\Bigr)
+ \frac{b-a}{b}\Bigl(-\frac{ab(a+b)}{2}\Bigr)
- \frac{c-a}{c}\Bigl(-\frac{ac(a+c)}{2}\Bigr)
= -\frac{a(c-b)(b+c)}{2} - \frac{a(b-a)(a+b)}{2} + \frac{a(c-a)(a+c)}{2}.
\]  
Therefore  
\[
\overrightarrow{MN}\cdot\vec v = \frac{a}{2}\Bigl[-(c-b)(b+c) - (b-a)(a+b) + (c-a)(a+c)\Bigr].
\]  

Now simplify the bracket.  Using \((c-b)(b+c)=c^2-b^2,\;(b-a)(a+b)=b^2-a^2,\;(c-a)(a+c)=c^2-a^2\), we obtain  
\[
-(c^2-b^2) - (b^2-a^2) + (c^2-a^2) = -c^2+b^2 - b^2 + a^2 + c^2 - a^2 = 0.
\]  
Hence \(\overrightarrow{MN}\cdot\vec v = 0\), and because \(\vec v\) is a non‑zero multiple of \(\overrightarrow{OI}\), we conclude  
\[
\overrightarrow{MN}\perp\overrightarrow{OI}.
\]  

Thus the angle \(\gamma\) between lines \(MN\) and \(OI\) is \(90^\circ\), and therefore  
\[
\frac{\gamma}{2}=45^\circ.
\]  

\boxed{45^\circ}
