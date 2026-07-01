# PB-Basic-028 — IMO-medium / Geometry

**Score: 7/7** &middot; pipeline output via `select:R0(2/4)`

**Grader note (Claude grader, sympy-verified):** Numerically confirms 4 equal sides and perpendicularly-bisecting diagonals = rhombus; the root d matches equation (10); the bracket identity is verified in sympy (only minor typos).

## Problem

In $\triangle ABC$ the altitudes $BE$ and $CF$ intersect at $H$. A circle $(W)$ is
 externally tangent to the Euler circle $(E)$ of $\triangle ABC$ and also tangent
 to the sides $AB$ and $AC$ at $X$ and $Y$, respectively, with
 $(W)$ being closer to $A$ than the Euler circle. Let $I'$ be the
 incenter of $\triangle AEF$. Prove that $AXI'Y$ is a rhombus.

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

Let \(\angle A = 2\alpha\) (so \(\alpha = \frac{A}{2}\)).  Place \(A\) at the origin and let the internal bisector of \(\angle A\) be the positive \(x\)-axis.  Then the rays \(AB\) and \(AC\) make angles \(-\alpha\) and \(+\alpha\) with the \(x\)-axis.  Write \(AB = c,\; AC = b\).  Hence
\[
B = (c\cos\alpha,\,-c\sin\alpha),\qquad C = (b\cos\alpha,\,b\sin\alpha).
\]
Denote \(a = BC = \sqrt{b^{2}+c^{2}-2bc\cos2\alpha}\) and \(s = \dfrac{a+b+c}{2}\).

---
### 1.  The points \(E,F\) and the incenter \(I'\) of \(\triangle AEF\)

The feet of the altitudes are
\[
E = \text{foot from }B\text{ to }AC,\qquad
F = \text{foot from }C\text{ to }AB.
\]
In the right triangles \(ABE\) and \(ACF\) we have
\[
AE = c\cos A = c\cos2\alpha,\qquad AF = b\cos2\alpha,
\]
and also \(EF = a\cos2\alpha\) (by similarity).  Hence \(\triangle AEF\) is similar to \(\triangle ABC\) with similarity factor \(\cos2\alpha\).  Consequently the incenter \(I'\) of \(\triangle AEF\) is the image of the incenter \(I\) of \(\triangle ABC\) under the homothety with centre \(A\) and factor \(\cos2\alpha\); therefore
\[
I' = \cos2\alpha\cdot I.
\]

The incenter \(I\) of \(\triangle ABC\) lies on the angle bisector, and its distance from \(A\) is
\[
AI = \frac{r}{\sin\alpha} = \frac{\Delta/s}{\sin\alpha}
   = \frac{\frac12bc\sin2\alpha}{s\sin\alpha}
   = \frac{bc\cos\alpha}{s}.
\]
Thus
\[
AI' = AI\cos2\alpha = \frac{bc\cos\alpha\cos2\alpha}{s}
      = \frac{2bc\cos\alpha\cos2\alpha}{a+b+c}. \tag{1}
\]
In coordinates \(I = (AI,0)\), so \(I' = (AI',0)\).

---
### 2.  The circle \((W)\) tangent to \(AB\) and \(AC\)

Let the centre of \((W)\) be \(O_W = (d,0)\) with \(d>0\) (it lies on the bisector).  The distance from \(O_W\) to \(AB\) (the line \(\sin\alpha\,x+\cos\alpha\,y=0\)) is \(d\sin\alpha\); hence the radius is \(r = d\sin\alpha\).  The points of tangency are the feet of the perpendiculars from \(O_W\) to \(AB\) and \(AC\):
\[
X = (d\cos^{2}\alpha,\,-d\sin\alpha\cos\alpha),\qquad
Y = (d\cos^{2}\alpha,\,d\sin\alpha\cos\alpha).
\]
Thus
\[
AX = AY = d\cos\alpha,\qquad
\text{and}\qquad M = \left(d\cos^{2}\alpha,\,0\right)
\]
is the midpoint of \(XY\).  Consequently
\[
AM = d\cos^{2}\alpha. \tag{2}
\]

---
### 3.  The nine‑point circle (Euler circle) of \(\triangle ABC\)

The circumcenter \(O\) is obtained by solving \(OA=OB=OC\):
\[
O = \left(\frac{b+c}{4\cos\alpha},\;\frac{b-c}{4\sin\alpha}\right).
\]
Since the orthocenter satisfies \(H = A+B+C-2O\) (because \(O\) is the circumcenter), we have
\[
H = \left(\frac{(b+c)\cos2\alpha}{2\cos\alpha},\;
         -\frac{(b-c)\cos2\alpha}{2\sin\alpha}\right).
\]
The nine‑point centre \(N\) is the midpoint of \(OH\):
\[
N = \left(\frac{(b+c)(1+2\cos2\alpha)}{8\cos\alpha},\;
         \frac{(b-c)(1-2\cos2\alpha)}{8\sin\alpha}\right). \tag{3}
\]
The nine‑point radius is \(R_n = \dfrac{R}{2}\), where \(R = \dfrac{a}{2\sin2\alpha} = \dfrac{a}{4\sin\alpha\cos\alpha}\); hence
\[
R_n = \frac{a}{8\sin\alpha\cos\alpha}. \tag{4}
\]

---
### 4.  Tangency condition for \((W)\) and the nine‑point circle

The circle \((W)\) is externally tangent to the nine‑point circle, so
\[
|O_WN| = r + R_n.
\]
Substituting \(O_W=(d,0)\), the expressions for \(N\) and \(r\) from (3) and (4) gives
\[
(d-N_x)^2 + N_y^2 = (d\sin\alpha + R_n)^2.
\]
Expanding and using \(N_x^2+N_y^2\) leads to
\[
d^{2}\cos^{2}\alpha - 2d\bigl(N_x+\sin\alpha\,R_n\bigr) + \bigl(N_x^{2}+N_y^{2}-R_n^{2}\bigr) = 0. \tag{5}
\]

We compute the two quantities that appear.

\[
\begin{aligned}
N_x+\sin\alpha\,R_n
&= \frac{b+c}{8\cos\alpha}(1+2\cos2\alpha) + \frac{a}{8\cos\alpha} \\
&= \frac{(b+c)(1+2\cos2\alpha)+a}{8\cos\alpha}. \tag{6}
\end{aligned}
\]

Now evaluate \(N_x^{2}+N_y^{2}-R_n^{2}\).  Using (3) and (4),
\[
\begin{aligned}
N_x^{2}+N_y^{2}-R_n^{2}
&= \frac{(b+c)^{2}(1+2\cos2\alpha)^{2}}{64\cos^{2}\alpha}
   + \frac{(b-c)^{2}(1-2\cos2\alpha)^{2}}{64\sin^{2}\alpha}
   - \frac{a^{2}}{64\sin^{2}\alpha\cos^{2}\alpha} \\[2mm]
&= \frac{1}{64\sin^{2}\alpha\cos^{2}\alpha}
   \Bigl[(b+c)^{2}(1+2\cos2\alpha)^{2}\sin^{2}\alpha
         +(b-c)^{2}(1-2\cos2\alpha)^{2}\cos^{2}\alpha
         -a^{2}\Bigr].
\end{aligned}
\]
Set \(t = \cos2\alpha\), so that \(\sin^{2}\alpha = \dfrac{1-t}{2},\; \cos^{2}\alpha = \dfrac{1+t}{2}\).  Substituting and simplifying (expand and collect terms) yields
\[
(b+c)^{2}(1+2t)^{2}\frac{1-t}{2}+(b-c)^{2}(1-2t)^{2}\frac{1+t}{2}-(b^{2}+c^{2}-2bt)
= 8bc\,t\,(1-t^{2}).
\]
Since \(1-t^{2} = \sin^{2}2\alpha = 4\sin^{2}\alpha\cos^{2}\alpha\), we obtain
\[
N_x^{2}+N_y^{2}-R_n^{2} = \frac{bc\cos2\alpha}{2}. \tag{7}
\]

Insert (6) and (7) into (5):
\[
d^{2}\cos^{2}\alpha - 2d\cdot\frac{(b+c)(1+2\cos2\alpha)+a}{8\cos\alpha}
   + \frac{bc\cos2\alpha}{2} = 0. \tag{8}
\]

---
### 5.  Determining the radius of \((W)\)

Multiply (8) by \(8\cos\alpha\):
\[
8\cos^{3}\alpha\,d^{2} - 2d\bigl[(b+c)(1+2\cos2\alpha)+a\bigr]
   + 4\cos\alpha\,bc\cos2\alpha = 0. \tag{9}
\]

We claim that the circle \((W)\) that is closer to \(A\) satisfies
\[
d = \frac{bc\cos2\alpha}{(a+b+c)\cos\alpha}. \tag{10}
\]

Substitute (10) into (9).  Let \(S = a+b+c\).  Then
\[
\begin{aligned}
8\cos^{3}\alpha\left(\frac{bc\cos2\alpha}{S\cos\alpha}\right)^{2}
&= \frac{8bc^{2}\cos^{2}\alpha\cos^{2}2\alpha}{S^{2}},\\[2mm]
-2\cdot\frac{bc\cos2\alpha}{S\cos\alpha}\bigl[(b+c)(1+2\cos2\alpha)+a\bigr]
&= -\frac{2bc\cos2\alpha}{S\cos\alpha}\bigl[(b+c)(1+2\cos2\alpha)+a\bigr],\\[2mm]
+4\cos\alpha\,bc\cos2\alpha &= 4bc\cos\alpha\cos2\alpha.
\end{aligned}
\]

Multiply the whole equation by \(S^{2}\cos\alpha\) and divide by \(2bc\cos2\alpha\) (positive):
\[
4bc\cos^{2}\alpha - S\bigl[(b+c)(1+2\cos2\alpha)+a\bigr] + 2\cos^{2}\alpha\,S^{2} = 0. \tag{11}
\]

Now \((b+c)(1+2\cos2\alpha)+a = S + 2(b+c)\cos2\alpha\).  Hence (11) becomes
\[
4bc\cos^{2}\alpha - S^{2} - 2S(b+c)\cos2\alpha + 2\cos^{2}\alpha S^{2}
= 4bc\cos^{2}\alpha - 2S(b+c)\cos2\alpha + S^{2}(2\cos^{2}\alpha-1).
\]
Since \(2\cos^{2}\alpha-1 = \cos2\alpha\), we have
\[
4bc\cos^{2}\alpha - 2S(b+c)\cos2\alpha + S^{2}\cos2\alpha
= \cos2\alpha\bigl[4bc\cos^{2}\alpha - 2S(b+c) + S^{2}\bigr].
\]

Now \(S^{2} - 2S(b+c) = (a+b+c)^{2} - 2(a+b+c)(b+c) = a^{2} - (b+c)^{2}\).  Therefore
\[
4bc\cos^{2}\alpha - 2S(b+c) + S^{2}
= 4bc\cos^{2}\alpha + a^{2} - (b+c)^{2}.
\]
By the law of cosines, \(a^{2} = b^{2}+c^{2}-2bc\cos2\alpha = (b+c)^{2} - 4bc\cos^{2}\alpha\).  Consequently the bracket vanishes, so (11) holds.  Thus (10) satisfies (9).

The quadratic (9) in \(d\) has two positive roots (the constant term is positive).  Their product is
\[
\frac{4\cos\alpha\,bc\cos2\alpha}{8\cos^{3}\alpha} = \frac{bc\cos2\alpha}{2\cos^{2}\alpha}.
\]
Hence the other root is
\[
d_{1} = \frac{bc\cos2\alpha}{2\cos^{2}\alpha} \cdot \frac{S\cos\alpha}{bc\cos2\alpha}
       = \frac{S}{2\cos\alpha} = \frac{a+b+c}{2\cos\alpha}.
\]
We have \(S \ge 2\sqrt{bc}\) (by AM–GM), so
\[
d_{1} \ge \frac{2\sqrt{bc}}{2\cos\alpha} = \frac{\sqrt{bc}}{\cos\alpha},
\qquad
d_{0} \le \frac{bc\cos2\alpha}{2\sqrt{bc}\cos\alpha} = \frac{\sqrt{bc}\cos2\alpha}{2\cos\alpha}
\le \frac{\sqrt{bc}}{2\cos\alpha} < d_{1}.
\]
Thus \(d_{0}\) is the smaller root.  The problem states that \((W)\) is closer to \(A\) than the Euler circle, which means its centre is nearer to \(A\); therefore \(d = d_{0}\).  Consequently
\[
r = d\sin\alpha = \frac{bc\cos2\alpha\sin\alpha}{(a+b+c)\cos\alpha}.
\]

---
### 6.  The relation \(AI' = 2\,AM\)

From (1) and (10) we obtain
\[
AM = d\cos^{2}\alpha = \frac{bc\cos2\alpha\cos\alpha}{a+b+c},
\qquad
AI' = \frac{2bc\cos\alpha\cos2\alpha}{a+b+c} = 2\,AM.
\]
Moreover, \(M\) is the midpoint of \(XY\) by construction, so \(M\) is also the midpoint of \(AI'\).  Hence the diagonals \(XY\) and \(AI'\) of quadrilateral \(AXI'Y\) bisect each other.

---
### 7.  \(AXI'Y\) is a rhombus

In our coordinate system, the points \(X\) and \(Y\) have the same \(x\)-coordinate (\(d\cos^{2}\alpha\)), so \(XY\) is vertical; the segment \(AI'\) lies on the \(x\)-axis (the angle bisector).  Therefore \(XY \perp AI'\).  The diagonals of quadrilateral \(AXI'Y\) are perpendicular and bisect each other; thus \(AXI'Y\) is a rhombus.

∎
