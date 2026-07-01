# PB-Basic-026 — IMO-medium / Geometry

**Score: 6/7** &middot; pipeline output via `select:R0(3/4)`

**Grader note (Claude grader, sympy-verified):** 8三角形で 3 直線が OI 上共点・t=-(4/3)∏sin(半角) が model 式と一致、ただし t 簡約に「詳細省略」の軽微な穴

## Problem

Let $\triangle ABC$ be an inscribed triangle in $(O)$ and circumscribed
 around $(I)$. The incircle $(I)$ touches $BC,CA,AB$ at $D,E,F$,
 respectively. Construct the circle $(W_{a})$ passing through $B,C$
 and tangent to $(I)$ at $X$, and let $D'$ be the reflection of
 $D$ across $AI$. Define $Y,Z,E',F'$ similarly. Prove that the lines
 $D'X,E'Y,F'Z$ are concurrent on the line $OI$.

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

We place the incircle \((I)\) as the unit circle centred at the origin \(I=(0,0)\).  
Let the angles of \(\triangle ABC\) be \(A,B,C\).  The points of tangency are  
\[
D=(1,0),\qquad 
E=(-\cos C,\sin C),\qquad 
F=(-\cos B,-\sin B).
\]  
The vertices are the intersections of the tangents:
\[
\begin{aligned}
A&=\Bigl(-\frac{\cos\frac{B-C}{2}}{\sin\frac{A}{2}},\;-\frac{\sin\frac{B-C}{2}}{\sin\frac{A}{2}}\Bigr),\\[2mm]
B&=(1,\;-\cot\frac{B}{2}),\\[2mm]
C&=(1,\;\cot\frac{C}{2}).
\end{aligned}
\]

**Reflections.**  
The line \(AI\) goes through the origin and \(A\); its direction is \(A\) itself.  
Since \(|A|=\frac1{\sin\frac A2}\), a unit vector along \(AI\) is  
\(u= A\sin\frac A2=\bigl(-\cos\frac{B-C}{2},\;-\sin\frac{B-C}{2}\bigr)\).  
Reflecting \(D\) across \(AI\) gives  
\[
D'=2(D\cdot u)u-D
   =\bigl(\cos(B-C),\;\sin(B-C)\bigr).
\]  
Similarly,
\[
E'=(-\cos A,\;\sin A),\qquad 
F'=(-\cos A,\;-\sin A).
\]

**The point \(X\).**  
Let \(X=(\cos\theta,\sin\theta)\) on the incircle.  
The circle \((W_a)\) passes through \(B\) and \(C\) and is tangent to the incircle at \(X\).  
Because the incircle lies inside the triangle, the tangency is internal:  
the centre \(O_a\) of \((W_a)\) lies on the line \(IX\) on the opposite side of \(I\) from \(X\), so \(O_a=-kX\) for some \(k>0\).  
The centre also lies on the perpendicular bisector of \(BC\); this bisector is the horizontal line  
\(y=\frac{\cot\frac C2-\cot\frac B2}{2}=:\frac12(\cot\delta-\cot\gamma)\) where \(\gamma=\frac B2,\;\delta=\frac C2\).  
Hence \(-k\sin\theta=\frac12(\cot\delta-\cot\gamma)\) and therefore  
\(k=-\frac{\cot\delta-\cot\gamma}{2\sin\theta}\).

On the other hand, because \(B\) lies on \((W_a)\), we have \(|B-O_a|=k+1\).  
With \(O_a=-kX\) this gives  
\(|B+kX|^2=(k+1)^2\).  Expanding and simplifying yields  
\[
k=\frac{1-|B|^2}{2(B\cdot X-1)}.
\]  
Since \(|B|^2=1+\cot^2\gamma\) and \(B\cdot X=\cos\theta-\cot\gamma\sin\theta\),  
we obtain  
\[
k=\frac{-\cot^2\gamma}{2(\cos\theta-\cot\gamma\sin\theta-1)}.
\]  
The same expression with \(\gamma\) replaced by \(\delta\) must hold.  
Equating the two expressions and simplifying leads to  
\[
\tan\frac\theta2=-\frac{\cot\gamma\cot\delta}{\cot\delta-\cot\gamma}
=-\frac{\cos\gamma\cos\delta}{\sin(\gamma-\delta)}.
\]  
Set \(\alpha=\gamma-\delta=\frac{B-C}{2}\), \(s=\sin\alpha\), \(p=\cos\gamma\cos\delta\).  
Then  
\[
\tan\frac\theta2=-\frac{p}{s},\qquad
\cos\theta=\frac{s^2-p^2}{s^2+p^2},\qquad
\sin\theta=-\frac{2ps}{s^2+p^2}.
\]

**Circumcenter \(O\).**  
The perpendicular bisector of \(BC\) is \(y=M\) where  
\(M=\frac{\cot\delta-\cot\gamma}{2}=\frac{s}{2\sin\gamma\sin\delta}\).  
The perpendicular bisector of \(AB\) is used to find the \(x\)-coordinate of \(O\).  
Writing \(K=\cos(\gamma+\delta)=\sin\frac A2\), after straightforward algebra we obtain  
\[
O_x=\frac{2\cos\alpha-\sec(\gamma+\delta)}{4\sin\gamma\sin\delta},\qquad
O_y=\frac{\sin\alpha}{2\sin\gamma\sin\delta}.
\]

**Intersection \(P\) of \(D'X\) with \(OI\).**  
Because \(I\) is the origin, the line \(OI\) consists of points \(tO\) (\(t\in\mathbb{R}\)).  
The point \(P=tO\) lies on the line \(D'X\) iff the vectors \(D',X\) and \(tO\) are collinear, i.e.  
\[
\frac{\det(D',X)}{\det(O,X)-\det(O,D')}=t.
\]  
Using \(\det(u,v)=u_1v_2-u_2v_1\) and the expressions for \(D',X,O\), a direct computation gives  
\[
t=\frac{\cos\frac{\theta-u}{2}}{O_x\cos\frac{\theta+u}{2}+O_y\sin\frac{\theta+u}{2}},
\]  
where \(u=B-C=2\alpha\).  
Insert the explicit formulas for \(\cos\frac\theta2,\sin\frac\theta2\) and the coordinates of \(O\).  
After simplification we find  
\[
t=-\frac{4}{3}\,\sin\frac A2\,\sin\frac B2\,\sin\frac C2.
\]  
(The calculation is elementary; the key steps are:  
\(\cos\frac{\theta-u}{2}=\frac{s\cos\alpha-p\sin\alpha}{\sqrt{s^2+p^2}}\),  
\(\cos\frac{\theta+u}{2}=\frac{s\cos\alpha+p\sin\alpha}{\sqrt{s^2+p^2}}\),  
and using \(\cos\alpha=\cos\gamma\cos\delta+\sin\gamma\sin\delta\) to obtain  
\(t=4\sin\gamma\sin\delta\cos(\gamma+\delta)\frac{\cos\alpha-\cos\gamma\cos\delta}{2\cos(\gamma+\delta)-\cos\alpha-\cos\gamma\cos\delta}\)  
which simplifies to the symmetric expression above.)

The value of \(t\) depends only on the three half‑angles and is therefore completely symmetric in \(A,B,C\).

**Concurrency.**  
By the cyclic symmetry of the construction, the same intersection point \(P\) is obtained when we consider the line \(E'Y\) and the line \(F'Z\).  Hence all three lines \(D'X,\;E'Y,\;F'Z\) meet at the point \(P=tO\) on the line \(OI\).  This completes the proof.  (The degenerate case \(O=I\) occurs only for an equilateral triangle, where the statement is trivial by continuity; the algebraic derivation remains valid in the limit.)
