# PB-Advanced-005 — IMO-medium / Geometry

**Score: 1/7** &middot; pipeline output via `select:R1(4/4)`

**Grader note (Claude grader, sympy-verified):** 構成が実際は ∠BAC=180−α(数値130°)、θ=π−α が誤り(真値180−2α≈80°)、根本的誤り

## Problem

Let $\angle XYZ$ be an acute angle with $\angle XYZ \ne 60^\circ$, and let $A$ be a point inside $\angle XYZ$. Prove that there exists $D\ne A$ inside $\angle XYZ$ and $\theta\in (0,2\pi )$ satisfying the following condition:

 For points $B$ and $C$ on the rays $\overrightarrow{YX}$ and $\overrightarrow{YZ}$ respectively, then
 \[
 \angle BAC = \angle XYZ \quad \implies \quad \angle BDC = \theta.
 \]

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

We set up a coordinate system with \(Y\) at the origin. Let the ray \(\overrightarrow{YX}\) be the positive \(x\)-axis and the ray \(\overrightarrow{YZ}\) be the ray that makes an acute angle \(\alpha=\angle XYZ\) with the \(x\)-axis (\(\alpha\neq60^\circ\)).  Points on the rays are \(B=(b,0)\) with \(b>0\) and \(C=(c\cos\alpha,\,c\sin\alpha)\) with \(c>0\).  
Let \(A=(x,y)\) be a point inside the angle, so \(x>0,\;y>0\) and \(y/x<\tan\alpha\).

---

### 1.  Concyclicity of \(A,B,C,Y\)

Because \(\angle BYC=\alpha\) and \(\angle BAC=\alpha\), we have \(\angle BAC=\angle BYC\).  
If \(A\) and \(Y\) were on opposite sides of line \(BC\), then the inscribed angle theorem would give \(\angle BAC=180^\circ-\alpha\), contradicting the hypothesis (since \(\alpha\) is acute).  Hence \(A\) and \(Y\) lie on the same side of \(BC\); consequently the four points \(A,B,C,Y\) are concyclic.

---

### 2.  Linear relation between \(b\) and \(c\)

A circle through the origin has equation \(X^2+Y^2+DX+EY=0\).  
Substituting \(B\) gives \(b^2+Db=0\Rightarrow D=-b\).  
Substituting \(C\) gives \(c^2+Dc\cos\alpha+Ec\sin\alpha=0\Rightarrow c-b\cos\alpha+E\sin\alpha=0\Rightarrow E=(b\cos\alpha-c)/\sin\alpha\).  
Substituting \(A\) and multiplying by \(\sin\alpha\) yields  

\[
(x^2+y^2)\sin\alpha-bx\sin\alpha+y(b\cos\alpha-c)=0,
\]

so  

\[
c=\frac{(x^2+y^2)\sin\alpha}{y}+b\,\frac{y\cos\alpha-x\sin\alpha}{y}.
\]

Denote  

\[
p=\frac{y\cos\alpha-x\sin\alpha}{y},\qquad q=\frac{(x^2+y^2)\sin\alpha}{y}.
\]

Because \(A\) lies inside the angle, \(y\cos\alpha-x\sin\alpha<0\), hence \(p<0\); also \(q>0\).  
Thus for every pair \((B,C)\) with \(\angle BAC=\alpha\) we have the affine relation  

\[
c = p\,b + q. \tag{1}
\]

In complex notation (identifying \(\mathbb{R}^2\) with \(\mathbb{C}\)) we have  

\[
B=b,\qquad C=c e^{i\alpha}=(p b+q)e^{i\alpha}=p e^{i\alpha}B+q e^{i\alpha}. \tag{2}
\]

---

### 3.  Construction of a point \(D\)

Define  

\[
M=p e^{i\alpha},\qquad V=q e^{i\alpha}.
\]

Then (2) becomes \(C=MB+V\).  Consider the affine map that sends \(B\) to \(C\).  
Its unique fixed point is  

\[
D=\frac{V}{1-M}=\frac{q e^{i\alpha}}{1-p e^{i\alpha}}. \tag{3}
\]

Since \(p<0\), the denominator is \(1-p e^{i\alpha}=1+|p|e^{i\alpha}\), which has positive real and imaginary parts, so \(D\) is well defined.

**Claim 1.**  \(D\) lies inside \(\angle XYZ\).  

Indeed, \(\arg D = \alpha-\arg(1-p e^{i\alpha}) = \alpha-\arg(1+|p|e^{i\alpha})\).  
The argument of \(1+|p|e^{i\alpha}\) is \(\arctan\!\bigl(|p|\sin\alpha/(1+|p|\cos\alpha)\bigr)\), which lies between \(0\) and \(\alpha\).  Hence \(\arg D\in(0,\alpha)\), so \(D\) is strictly inside the angle.

**Claim 2.**  For every admissible pair \((B,C)\) we have  

\[
C-D = M(B-D). \tag{4}
\]

*Proof.*  From (3) we have \(V = D(1-M)\).  Then  

\[
C-D = MB+V-D = MB + D(1-M)-D = MB - MD = M(B-D). \quad\blacksquare
\]

Therefore the directed angle from \(\overrightarrow{DB}\) to \(\overrightarrow{DC}\) equals \(\arg M = \arg(p e^{i\alpha}) = \alpha+\pi\) (because \(p<0\)).  Consequently the (undirected) angle \(\angle BDC\) is the smaller angle between the rays, which is \(\pi-\alpha\).  Thus  

\[
\angle BDC = \pi-\alpha \qquad\text{(independent of }B\text{ and }C\text{)}.
\]

---

### 4.  When \(A\) is not on the angle bisector

If \(A\) does **not** lie on the internal bisector, then \(D\neq A\).  (Indeed, if \(D=A\) then from (3) we obtain \(p=-1\) and \(q=2x\); substituting the expressions of \(p,q\) shows that this forces \(y/x=\tan(\alpha/2)\), i.e. \(A\) is on the bisector.)  
Thus for every \(A\) not on the bisector, the point \(D\) defined by (3) is inside the angle, different from \(A\), and satisfies  

\[
\angle BAC=\alpha\;\Longrightarrow\; \angle BDC=\pi-\alpha.
\]

---

### 5.  When \(A\) lies on the angle bisector

Suppose \(A\) is on the bisector.  Then \(y/x=\tan(\alpha/2)\).  From the formulas for \(p,q\) we get \(p=-1\) and \(q=2x\).  Equation (1) becomes \(c=2x-b\).  For any \(b>0\) with \(b<2x\) we obtain a pair \((B,C)\) with \(\angle BAC=\alpha\)?  Let us check the side condition.

For such a pair, compute the signed distance of \(Y\) and \(A\) from the line \(BC\).  The line through \(B=(b,0)\) and \(C=(c\cos\alpha,c\sin\alpha)\) has equation  

\[
f(X,Y)=Y(c\cos\alpha-b)-Xc\sin\alpha+bc\sin\alpha.
\]

For \(Y=(0,0)\) we have \(f(Y)=bc\sin\alpha>0\).  
For \(A=(x,y)\) we substitute \(c=2x-b\) and \(y=x\tan(\alpha/2)\):

\[
\begin{aligned}
f(A) &= y(c\cos\alpha-b)-xc\sin\alpha+bc\sin\alpha \\
&= x\tan(\alpha/2)\bigl((2x-b)\cos\alpha-b\bigr)-x(2x-b)\sin\alpha+b(2x-b)\sin\alpha \\
&= -2x^2\tan(\alpha/2)+2xb\sin\alpha-b^2\sin\alpha \\
&= \sin\alpha\left(-2x^2/(1+\cos\alpha)+2xb-b^2\right).
\end{aligned}
\]

The quadratic in \(b\): \(b^2-2xb+2x^2/(1+\cos\alpha)\) has discriminant  

\[
4x^2-\frac{8x^2}{1+\cos\alpha}=4x^2\!\left(1-\frac{2}{1+\cos\alpha}\right)\le 0,
\]

so it is always positive.  Hence \(f(A)<0\) for every admissible \(b\).  Thus \(A\) and \(Y\) lie on opposite sides of \(BC\), which contradicts the requirement that they must be on the same side for \(\angle BAC\) to equal \(\alpha\).  Consequently **no** points \(B,C\) on the rays satisfy \(\angle BAC=\alpha\).

Therefore the hypothesis “\(\angle BAC=\alpha\)” is never true, and the implication  

\[
\angle BAC=\alpha\;\Longrightarrow\;\angle BDC=\theta
\]

is vacuously true for **any** choice of \(D\) and \(\theta\).  In particular we can choose \(D\) to be the midpoint of \(YA\) (which lies inside the angle and is different from \(A\)) and \(\theta=\pi/2\).  This satisfies the required condition.

---

### 6.  Conclusion

In every case there exists a point \(D\neq A\) inside \(\angle XYZ\) and an angle \(\theta\in(0,2\pi)\) such that whenever \(B,C\) are points on the rays \(\overrightarrow{YX},\overrightarrow{YZ}\) with \(\angle BAC=\angle XYZ\), we have \(\angle BDC=\theta\).  For \(A\) not on the bisector we may take \(D\) as the fixed point (3) and \(\theta=\pi-\angle XYZ\); for \(A\) on the bisector the implication is vacuously true, so any \(D\neq A\) (e.g. the midpoint of \(YA\)) and any \(\theta\) (e.g. \(\pi/2\)) work.  ∎
