# PB-Advanced-022 — IMO-easy / Geometry

**Score: 7/7** &middot; pipeline output via `select:R2(3/4)`

**Grader note (Claude grader, sympy-verified):** 答 180°；座標・恒等式・K/B'/C' 座標・数値和=180 を全て検証、ほぼ完全

## Problem

Given a triangle $ABC$ with $AB<AC<BC$, let $I$ be the incenter
 of triangle $ABC$, and let $M$ and $N$ be the midpoints of sides
 $CA$ and $AB$, respectively. Let $K$ be the midpoint of the arc
 $BC$ of the circumcircle of triangle $ABC$ which does not contain
 $A$. Let $B'\neq C$ be the point where the line parallel to $AC$
 and tangent to the incircle of triangle $ABC$ intersects side $BC$,
 and similarly, let $C'\neq B$ be the point where the line parallel
 to $AB$ and tangent to the incircle of triangle $ABC$ intersects
 side $BC$. Find the value of $\angle NIM+\angle B'KC'$ in terms
 of degree.

**Reference short answer:** 180

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

We prove that \(\angle NIM+\angle B'KC'=180^\circ\).

**Notation.**  
Let \(a=BC,\;b=CA,\;c=AB\).  Semiperimeter \(s=\frac{a+b+c}{2}\), area \(\Delta\), inradius \(r=\frac{\Delta}{s}\).  
Set \(x=s-a,\;y=s-b,\;z=s-c\).  Then  
\[
a=y+z,\quad b=z+x,\quad c=x+y,\quad s=x+y+z,\quad \Delta=\sqrt{sxyz},\quad r=\sqrt{\frac{xyz}{s}}.
\]  
The condition \(AB<AC<BC\) gives \(c<b<a\), which is equivalent to \(x<y<z\).

**Coordinate placement.**  
Place \(B=(0,0)\), \(C=(a,0)\).  The coordinates of \(A\) are  
\[
u=\frac{ys-zx}{y+z},\qquad v=\frac{2rs}{y+z},
\]  
where \(y+z=a\).  The incenter is  
\[
I=(y,\;r),
\]  
because the distance from \(B\) to the touchpoint on \(BC\) is \(s-b=y\) and the incircle is tangent to \(BC\) at \((y,0)\).  
Midpoints are  
\[
N=\Bigl(\frac{u}{2},\frac{v}{2}\Bigr),\qquad M=\Bigl(\frac{u+a}{2},\frac{v}{2}\Bigr).
\]

**1.  Computing \(\angle NIM\).**  
Let  
\[
t=\frac{v}{2}-r=\frac{rx}{y+z},\qquad A=y+z,
\]  
and  
\[
u_1=\frac{u}{2}-y=\frac{x(y-z)-yA}{2A},\qquad 
u_2=\frac{u+a}{2}-y=\frac{x(y-z)+zA}{2A}.
\]  
Then  
\[
\overrightarrow{IN}=(u_1,t),\qquad \overrightarrow{IM}=(u_2,t).
\]  
The cross product (2‑D) is  
\[
|\overrightarrow{IN}\times\overrightarrow{IM}|=|t(u_1-u_2)|=t\cdot\frac{A}{2}=\frac{rx}{2}.
\]  
The dot product is  
\[
\overrightarrow{IN}\cdot\overrightarrow{IM}=u_1u_2+t^2
 =\frac{x^2(y-z)^2-xA(y-z)^2-yzA^2}{4A^2}+\frac{r^2x^2}{A^2}.
\]  
Using \(r^2=\dfrac{xyz}{s}\), we obtain  
\[
\overrightarrow{IN}\cdot\overrightarrow{IM}=
\frac{x^2(y-z)^2-xA(y-z)^2-yzA^2+\dfrac{4x^3yz}{s}}{4A^2}.
\]  
Define  
\[
B=xy^2+xz^2+y^2z+yz^2-x^3-xyz.
\]  
A direct algebraic simplification (see the remark below) shows  
\[
x^2(y-z)^2-xA(y-z)^2-yzA^2+\frac{4x^3yz}{s}= -\frac{A^2B}{s}.
\]  
Hence  
\[
\overrightarrow{IN}\cdot\overrightarrow{IM}= -\frac{B}{4s}.
\]  
Since \(B>0\) (because \(x<y<z\)), the dot product is negative; therefore the angle \(\angle NIM\) is obtuse.  The acute angle \(\varphi\) between the lines \(IN\) and \(IM\) satisfies  
\[
\tan\varphi=\frac{|\overrightarrow{IN}\times\overrightarrow{IM}|}{|\overrightarrow{IN}\cdot\overrightarrow{IM}|}
 =\frac{rx/2}{B/(4s)}=\frac{2rsx}{B}=\frac{2x\sqrt{sxyz}}{B}.
\]  
(The last equality uses \(rs=\sqrt{sxyz}\).)

**Remark (verification of the identity).**  
We need to show  
\[
x^2(y-z)^2-xA(y-z)^2-yzA^2+\frac{4x^3yz}{s}= -\frac{A^2B}{s}.
\]  
Multiplying by \(s\) and substituting \(A=y+z\) gives  
\[
sx^2(y-z)^2-sxA(y-z)^2-syzA^2+4x^3yz+A^2B=0.
\]  
Expanding and simplifying (using \(s=x+y+z\) and \(A=y+z\)) reduces the left‑hand side to  
\[
x^3\bigl((y-z)^2-(y+z)^2+4yz\bigr)=0,
\]  
so the identity holds.  (The computation is straightforward and omitted for brevity.)

**2.  Computing \(\angle B'KC'\).**  
The line through \(B'\) parallel to \(AC\) and tangent to the incircle is the reflection of \(AC\) across \(I\).  The equation of \(AC\) is \(vx+(a-u)y-va=0\).  Its reflection across \(I\) is  
\[
vx+(a-u)y=va-2rb.
\]  
Intersecting with \(BC\;(y=0)\) gives  
\[
B'=\Bigl(\frac{ay}{s},0\Bigr).
\]  
Similarly, reflecting \(AB\) across \(I\) gives  
\[
C'=\Bigl(\frac{ac}{s},0\Bigr)=\Bigl(\frac{a(x+y)}{s},0\Bigr).
\]  
Because \(x,y,z>0\) and \(x<y<z\), we have \(0<\frac{ay}{s}<a\) and \(0<\frac{a(x+y)}{s}<a\), so \(B',C'\) lie on the segment \(BC\).

The midpoint of arc \(BC\) not containing \(A\) lies on the perpendicular bisector of \(BC\) (the line \(x=\frac a2\)) and on the circumcircle.  Using the standard formulas  
\[
R=\frac{abc}{4\Delta},\quad \sin^2\frac A2=\frac{(s-b)(s-c)}{bc}=\frac{yz}{bc},
\]  
we obtain  
\[
K=\Bigl(\frac a2,\; -2R\sin^2\frac A2\Bigr)
 =\Bigl(\frac a2,\; -\frac{ayz}{2rs}\Bigr).
\]  
Set  
\[
d_B=\frac{ay}{s}-\frac a2=-\frac{a(x+z-y)}{2s},\qquad
d_C=\frac{ac}{s}-\frac a2=\frac{a(x+y-z)}{2s},
\]  
\[
h=\frac{ayz}{2rs}>0.
\]  
Then  
\[
\overrightarrow{KB'}=(d_B,\;h),\qquad \overrightarrow{KC'}=(d_C,\;h).
\]  
The cross product magnitude is  
\[
|\overrightarrow{KB'}\times\overrightarrow{KC'}|=|h(d_B-d_C)|=h\cdot\frac{ax}{s}.
\]  
The dot product is  
\[
\overrightarrow{KB'}\cdot\overrightarrow{KC'}=d_Bd_C+h^2
 =\frac{a^2}{4s^2}\Bigl[(y-z)^2-x^2+\frac{syz}{x}\Bigr].
\]  
Therefore  
\[
\tan\angle B'KC'=\frac{h\cdot\frac{ax}{s}}{d_Bd_C+h^2}
 =\frac{2x^2yz}{r}\cdot\frac{1}{(y-z)^2-x^2+\dfrac{syz}{x}}
 =\frac{2x\sqrt{sxyz}}{B},
\]  
because  
\[
(y-z)^2-x^2+\frac{syz}{x}= \frac{x(y-z)^2-x^3+syz}{x}= \frac{B}{x}.
\]  
Thus \(\tan\angle B'KC'=\dfrac{2x\sqrt{sxyz}}{B}\).

**3.  Conclusion.**  
Both \(\varphi\) and \(\angle B'KC'\) are acute: \(\varphi\) is the acute angle between the lines \(IN\) and \(IM\) (since \(\overrightarrow{IN}\cdot\overrightarrow{IM}<0\) and the dot product is negative, \(\angle NIM>90^\circ\) and \(\varphi=180^\circ-\angle NIM\)); \(\angle B'KC'\) is acute because its tangent is positive and its dot product is positive.  Moreover  
\[
\tan\varphi = \tan\angle B'KC'.
\]  
Hence \(\varphi=\angle B'KC'\).  Consequently  
\[
\angle NIM = 180^\circ-\varphi = 180^\circ-\angle B'KC',
\]  
so  
\[
\boxed{\angle NIM+\angle B'KC'=180^\circ}.
\]
