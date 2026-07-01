# PB-Advanced-028 — IMO-easy / Geometry

**Score: 7/7** &middot; pipeline output via `select:R2(2/4)`

**Grader note (Claude grader, sympy-verified):** Coordinate method fully verified with sympy: D=−2c ⟹ midpoint of XY has x=c=C; self-contained and correct.

## Problem

Let $H$ be the orthocenter of acute triangle $ABC$, let $F$ be
 the foot of the altitude from $C$ to $AB$, and let $P$ be the reflection
 of $H$ across $BC$. Suppose that the circumcircle of triangle $AFP$
 intersects line $BC$ at two distinct points $X$ and $Y$. Prove
 that $C$ is the midpoint of $XY$.

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

We prove the statement using coordinate geometry.  The problem is invariant under similarity transformations, so we may place the triangle conveniently.  Let $B=(0,0)$, $C=(c,0)$ with $c>0$.  Because $\triangle ABC$ is acute, the foot of the altitude from $A$ lies on $BC$ between $B$ and $C$; therefore we can write $A=(a,h)$ with $h>0$ and $0<a<c$.

**Coordinates of the auxiliary points.**  
The foot $F$ of the altitude from $C$ to $AB$:  line $AB$ passes through $B$ and $A$, so its equation is $y=\frac{h}{a}x$.  The line through $C$ perpendicular to $AB$ has slope $-\frac{a}{h}$, equation $y=-\frac{a}{h}(x-c)$.  Solving gives  
\[
F = \left(\frac{a^{2}c}{a^{2}+h^{2}},\;\frac{ahc}{a^{2}+h^{2}}\right).
\]  
Denote $S = a^{2}+h^{2}$.

The orthocenter $H$ is the intersection of the altitudes.  The altitude from $A$ is the vertical line $x=a$.  The altitude from $B$ is perpendicular to $AC$; vector $\overrightarrow{AC}=(c-a,-h)$, so a direction vector for the altitude from $B$ is $(h,c-a)$.  Its parametric form is $(x,y)=t(h,c-a)$.  Intersection with $x=a$ gives $t=a/h$, hence  
\[
H = \left(a,\;\frac{a(c-a)}{h}\right).
\]

The reflection $P$ of $H$ across $BC$ (the $x$-axis) is  
\[
P = \left(a,\;-\frac{a(c-a)}{h}\right).
\]

**Equation of the circumcircle of $\triangle AFP$.**  
Let the circle have equation $x^{2}+y^{2}+Dx+Ey+G=0$ (the constant $G$ is not to be confused with the point $F$).  Because $A$, $F$, $P$ lie on it, we have  
\[
\begin{aligned}
(1)&\quad a^{2}+h^{2}+Da+Eh+G=0,\\[2pt]
(2)&\quad a^{2}+\Bigl(\frac{a(c-a)}{h}\Bigr)^{2}+Da-E\frac{a(c-a)}{h}+G=0,\\[2pt]
(3)&\quad \frac{a^{4}c^{2}}{S^{2}}+\frac{a^{2}h^{2}c^{2}}{S^{2}}+D\frac{a^{2}c}{S}+E\frac{ahc}{S}+G=0.
\end{aligned}
\]

Subtract $(1)-(2)$:  
\[
\bigl(h^{2}-\bigl(\tfrac{a(c-a)}{h}\bigr)^{2}\bigr)+E\bigl(h+\tfrac{a(c-a)}{h}\bigr)=0.
\]  
Factor $h^{2}+\frac{a(c-a)}{h}$:  
\[
\frac{(h^{2}-a(c-a))(h^{2}+a(c-a))}{h^{2}}+E\frac{h^{2}+a(c-a)}{h}=0
\;\Longrightarrow\;
(h^{2}+a(c-a))\Bigl(\frac{h^{2}-a(c-a)}{h^{2}}+E\frac{1}{h}\Bigr)=0.
\]  
Since $h^{2}+a(c-a)>0$ (both terms are non‑negative and not simultaneously zero), we obtain  
\[
\frac{h^{2}-a(c-a)}{h^{2}}+E\frac{1}{h}=0
\;\Longrightarrow\;
E=\frac{a(c-a)-h^{2}}{h}.
\]  
Set $K = a(c-a)-h^{2}$; then $E = K/h$.  (Because $\triangle ABC$ is acute, $K\neq0$; indeed $K=0$ would imply a right angle at $A$, contradicting acuteness.)

Subtract $(3)-(1)$:  
\[
\bigl(x_{F}^{2}+y_{F}^{2}-(a^{2}+h^{2})\bigr)+D(x_{F}-a)+E(y_{F}-h)=0. \tag{4}
\]

Now compute the needed quantities:
\[
\begin{aligned}
x_{F}&=\frac{a^{2}c}{S},\qquad y_{F}=\frac{ahc}{S},\\[2pt]
x_{F}^{2}+y_{F}^{2}&=\frac{a^{2}c^{2}}{S},\\[2pt]
x_{F}-a&=\frac{a(ac-S)}{S}=\frac{aK}{S},\qquad
y_{F}-h=\frac{h(ac-S)}{S}=\frac{hK}{S},\\[2pt]
x_{F}^{2}+y_{F}^{2}-(a^{2}+h^{2})&=\frac{a^{2}c^{2}}{S}-S=\frac{a^{2}c^{2}-S^{2}}{S}
=\frac{(ac-S)(ac+S)}{S}=\frac{K(ac+S)}{S}.
\end{aligned}
\]

Substitute into $(4)$:
\[
\frac{K(ac+S)}{S}+D\frac{aK}{S}+E\frac{hK}{S}=0.
\]  
Because $K\neq0$, we can multiply by $S/K$:
\[
ac+S+Da+Eh=0. \tag{5}
\]

Since $Eh=K$, equation $(5)$ becomes $ac+S+Da+K=0$.  Using $K=ac-S$, we have $ac+S+K=ac+S+(ac-S)=2ac$, hence  
\[
Da=-2ac\quad\Longrightarrow\quad D=-2c \qquad (a>0).
\]

Thus the circumcircle of $\triangle AFP$ has equation  
\[
x^{2}+y^{2}-2c\,x+Ey+G=0.
\]

**Midpoint of $XY$.**  
Line $BC$ is the $x$-axis ($y=0$).  Substituting $y=0$ gives the quadratic  
\[
x^{2}-2c\,x+G=0.
\]  
Its roots are the $x$-coordinates of the two intersection points $X$ and $Y$ (they are distinct by hypothesis).  The sum of the roots is $2c$, so the midpoint of $XY$ has $x$-coordinate $c$.  Since $C=(c,0)$, it follows that $C$ is the midpoint of $XY$.

∎
