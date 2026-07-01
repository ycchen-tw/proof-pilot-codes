# PB-Basic-027 — IMO-easy / Geometry

**Score: 7/7** &middot; pipeline output via `select:R0(4/4)`

**Grader note (Claude grader, sympy-verified):** 複数の鋭角三角形で XO·DE=0 を検証、E·B=|E|² 補題を正しく証明、X≠C も処理した完全な座標証明

## Problem

Given an acute triangle $ABC$, let $D$ and $E$ be the feet of
 the altitudes from $B$ to $AC$ and $C$ to $AB$, respectively.
 Let $E_{1}$ and $E_{2}$ be the reflections of $E$ with respect
 to $AC$ and $BC$, respectively. If $X$ (not equal to $C$) is an
 intersection point of the circumcircle of $\triangle CE_{1}E_{2}$
 and $AC$, and $O$ is the circumcenter of $\triangle CE_{1}E_{2}$,
 prove that $XO$ is perpendicular to $DE$.

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

We prove that \(XO\perp DE\) using coordinate geometry.

Place the triangle in a coordinate system with \(C\) at the origin and \(AC\) on the positive \(x\)-axis.  
Since \(\triangle ABC\) is acute, we may write  
\[
C=(0,0),\qquad A=(a,0)\;(a>0),\qquad B=(b\cos\theta,\,b\sin\theta)\;(b>0),
\]  
where \(0<\theta<90^\circ\) (because \(\angle ACB\) is acute).  
The foot \(D\) of the altitude from \(B\) to \(AC\) is simply the projection onto the \(x\)-axis:  
\[
D=(b\cos\theta,0).
\]

Let \(E\) be the foot from \(C\) to \(AB\).  Write the line \(AB\) as \(A+t(B-A)\).  
Because \(CE\perp AB\), the parameter \(t\) satisfies  
\[
t=-\frac{A\cdot(B-A)}{|B-A|^2}.
\]  
Compute  
\[
|B-A|^2 = a^2+b^2-2ab\cos\theta =: d,
\]  
\[
A\cdot(B-A)=a(b\cos\theta-a)=-a(a-b\cos\theta).
\]  
Hence  
\[
t=\frac{a(a-b\cos\theta)}{d}.
\]  
Therefore  
\[
E = A+t(B-A)=\Bigl(a+\frac{a(a-b\cos\theta)}{d}(b\cos\theta-a),\;
\frac{a(a-b\cos\theta)}{d}\,b\sin\theta\Bigr)
\]  
\[
= \Bigl(a-\frac{a(a-b\cos\theta)^2}{d},\;
\frac{ab\sin\theta(a-b\cos\theta)}{d}\Bigr).
\]  
Set  
\[
x_E = a-\frac{a(a-b\cos\theta)^2}{d},\qquad
y_E = \frac{ab\sin\theta(a-b\cos\theta)}{d}.
\]  
Note that \(a-b\cos\theta>0\) because the triangle is acute, so \(y_E>0\).  
Denote \(r=|E|^2=x_E^2+y_E^2\).

Now reflect \(E\) across \(AC\) (the \(x\)-axis):  
\[
E_1=(x_E,-y_E).
\]  
Reflect \(E\) across \(BC\).  Since \(BC\) passes through the origin, the reflection across the line with unit direction \(u=(\cos\theta,\sin\theta)\) is  
\[
E_2 = 2(E\cdot u)u-E.
\]  
Because \(B=b\,u\), we have \(E\cdot u = \frac{E\cdot B}{b}\).  Let \(\lambda = \frac{2(E\cdot u)}{b} = \frac{2(E\cdot B)}{b^2}\).  Then  
\[
E_2 = \lambda B - E = (\lambda b\cos\theta - x_E,\; \lambda b\sin\theta - y_E).
\]  
Because reflection preserves distance from the origin, \(|E_2|^2=|E|^2=r\).

**Circumcircle of \(\triangle CE_1E_2\).**  
Since \(C\) is the origin, the circle can be written as  
\[
x^2+y^2+Px+Qy=0
\]  
for some real numbers \(P,Q\).  Substituting \(E_1\) and \(E_2\) gives  
\[
\begin{aligned}
r+Px_E - Qy_E &=0, \tag{1}\\[2mm]
r+Px_{E_2}+Qy_{E_2} &=0. \tag{2}
\end{aligned}
\]

From (1) we have \(Px_E - Qy_E = -r\).

Now compute the quantities that appear in (2).  Using \(\lambda b = 2(x_E\cos\theta+y_E\sin\theta)\) (because \(E\cdot B = b(x_E\cos\theta+y_E\sin\theta)\)), we obtain  
\[
\begin{aligned}
y_{E_2}+y_E &= \lambda b\sin\theta = 2(x_E\cos\theta+y_E\sin\theta)\sin\theta,\\[2mm]
x_Ey_{E_2}+y_Ex_{E_2} &= x_E(\lambda b\sin\theta-y_E)+y_E(\lambda b\cos\theta-x_E)\\
&= \lambda b(x_E\sin\theta+y_E\cos\theta)-2x_Ey_E\\
&= 2(x_E\cos\theta+y_E\sin\theta)(x_E\sin\theta+y_E\cos\theta)-2x_Ey_E.
\end{aligned}
\]  
Solving the linear system (1),(2) for \(P\) (Cramer’s rule) gives  
\[
P = \frac{(-r)y_{E_2} - (-y_E)(-r)}{x_E y_{E_2} - (-y_E)x_{E_2}}
= -\frac{r(y_{E_2}+y_E)}{x_E y_{E_2}+y_E x_{E_2}}.
\]  
Insert the expressions above:  
\[
P = -\frac{r\cdot 2(x_E\cos\theta+y_E\sin\theta)\sin\theta}
{2(x_E\cos\theta+y_E\sin\theta)(x_E\sin\theta+y_E\cos\theta)-2x_Ey_E}
= -\frac{r(x_E\cos\theta+y_E\sin\theta)\sin\theta}
{(x_E\cos\theta+y_E\sin\theta)(x_E\sin\theta+y_E\cos\theta)-x_Ey_E}.
\]  
Simplify the denominator:  
\[
\begin{aligned}
(x_E\cos\theta+y_E\sin\theta)(x_E\sin\theta+y_E\cos\theta)
&= x_E^2\cos\theta\sin\theta + x_Ey_E\cos^2\theta + x_Ey_E\sin^2\theta + y_E^2\sin\theta\cos\theta\\
&= (x_E^2+y_E^2)\sin\theta\cos\theta + x_Ey_E(\cos^2\theta+\sin^2\theta) = r\sin\theta\cos\theta + x_Ey_E.
\end{aligned}
\]  
Hence the denominator becomes \(r\sin\theta\cos\theta + x_Ey_E - x_Ey_E = r\sin\theta\cos\theta\).  Therefore  
\[
P = -\frac{r(x_E\cos\theta+y_E\sin\theta)\sin\theta}{r\sin\theta\cos\theta}
= -\frac{x_E\cos\theta+y_E\sin\theta}{\cos\theta}.
\]

Now we prove the key identity  
\[
x_E\cos\theta+y_E\sin\theta = \frac{r}{b}. \tag{3}
\]  
Because \(E\) is the foot from the origin to \(AB\), we have \(E\cdot(B-A)=0\).  Write \(E = A + t(B-A)\) with the \(t\) found above.  Then  
\[
E\cdot B = E\cdot(A + t(B-A)) = E\cdot A + tE\cdot(B-A)=E\cdot A.
\]  
Moreover,  
\[
|E|^2 - E\cdot B = E\cdot(E-B) = E\cdot\bigl(A+t(B-A)-B\bigr) = E\cdot\bigl((1-t)(A-B)\bigr).
\]  
Since \(E = (1-t)A + tB\), we have \(E\cdot((1-t)(A-B)) = (1-t)(E\cdot A - E\cdot B)=0\).  Thus \(|E|^2 = E\cdot B\).  But \(E\cdot B = b(x_E\cos\theta+y_E\sin\theta)\), so  
\[
x_E\cos\theta+y_E\sin\theta = \frac{r}{b}.
\]  
Consequently  
\[
P = -\frac{r}{b\cos\theta}.
\]  
From (1) we then obtain  
\[
-\frac{r}{b\cos\theta}\,x_E - Q y_E = -r
\;\Longrightarrow\; Q y_E = r - \frac{r x_E}{b\cos\theta} = \frac{r(b\cos\theta - x_E)}{b\cos\theta},
\]  
so  
\[
Q = \frac{r(b\cos\theta - x_E)}{y_E\,b\cos\theta}.
\]

**Point \(X\) and circumcenter \(O\).**  
The circle meets the \(x\)-axis (\(AC\)) at points satisfying \(y=0\): \(x(x+P)=0\).  The two intersections are \(C=(0,0)\) and  
\[
X = (-P,0) = \left(\frac{r}{b\cos\theta},\,0\right).
\]  
The circumcenter \(O\) of \(\triangle CE_1E_2\) is the centre of the circle, so  
\[
O = \left(-\frac{P}{2},\,-\frac{Q}{2}\right) = \left(\frac{r}{2b\cos\theta},\,-\frac{Q}{2}\right).
\]  
Hence  
\[
\overrightarrow{XO} = O-X = \left(-\frac{r}{2b\cos\theta},\,-\frac{Q}{2}\right).
\]  
The vector \(\overrightarrow{DE}\) is  
\[
\overrightarrow{DE} = (x_E - b\cos\theta,\; y_E).
\]  
Now compute the dot product:  
\[
\begin{aligned}
\overrightarrow{XO}\cdot\overrightarrow{DE}
&= \left(-\frac{r}{2b\cos\theta}\right)(x_E - b\cos\theta) + \left(-\frac{Q}{2}\right)y_E \\
&= -\frac{r(x_E - b\cos\theta)}{2b\cos\theta} - \frac{Q y_E}{2}.
\end{aligned}
\]  
Substituting \(Q y_E = \dfrac{r(b\cos\theta - x_E)}{b\cos\theta}\) yields  
\[
-\frac{Q y_E}{2} = -\frac{r(b\cos\theta - x_E)}{2b\cos\theta} = \frac{r(x_E - b\cos\theta)}{2b\cos\theta}.
\]  
Therefore the two terms cancel:  
\[
\overrightarrow{XO}\cdot\overrightarrow{DE} = 0.
\]  
Thus \(XO \perp DE\).  

The point \(X\) is distinct from \(C\) because \(r>0\) and \(\cos\theta>0\), so \(X\neq C\).  The triangle is acute, so all quantities are well‑defined and no degenerate cases occur.  This completes the proof.
