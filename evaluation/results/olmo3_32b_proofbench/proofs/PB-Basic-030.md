# PB-Basic-030 — IMO-easy / Geometry

**Score: 7/7** &middot; pipeline output via `select:R1(2/4)`

**Grader note (Claude grader, sympy-verified):** W1W2 tangent → W3W4 tangent confirmed numerically to machine precision; the coordinate setup is a general trapezoid with non-parallel legs (also covering parallelograms); a complete proof with verified trigonometric identities.

## Problem

Given a trapezoid $ABCD$ with $AB,CD$ as the two legs. Circle $(W_{1})$ passes through $A,B$, and $(W_{2})$ passes through $C,D$ so that they are tangent to each other. The inscribed angle on circle $W_1$ corresponding to the arc AB on the side opposite to C and D is alpha, and the inscribed angle on circle $W_2$ corresponding to the arc CD on the side opposite to  A and B is beta. Construct $(W_{3})$ passing through $A,B$, $(W_{4})$ passing through $C,D$ such that the inscribed angle on circle W3 corresponding to the arc AB on the side opposite to C and D is $\beta$, and the inscribed angle on circle $W_4$ corresponding to the arc CD on the side opposite to  A and B is b $\alpha$. Prove that $(W_{3}),(W_{4})$ are tangent to each other.

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

**Proof.**  
We place the trapezoid in a coordinate system such that the bases \(AD\) and \(BC\) are horizontal.  Without loss of generality we may take  

\[
A=(0,0),\qquad D=(d,0),\qquad B=(b,h),\qquad C=(c,h),
\]

with \(h>0\).  The condition \(AD\parallel BC\) is satisfied.  Denote the lengths of the legs by  

\[
s_1=AB=\sqrt{b^{2}+h^{2}},\qquad s_2=CD=\sqrt{(d-c)^{2}+h^{2}}.
\]

Define the unit normals that point toward the sides containing the opposite vertices:

\[
\mathbf{n}_1=\frac{(h,-b)}{s_1}\quad(\text{points toward the side containing }C\text{ and }D),\qquad
\mathbf{n}_2=\frac{(-h,\,c-d)}{s_2}\quad(\text{points toward the side containing }A\text{ and }B).
\]

The midpoints of the chords are  

\[
M_{AB}=\left(\frac b2,\frac h2\right),\qquad M_{CD}=\left(\frac{c+d}{2},\frac h2\right).
\]

For a circle through two points, let the chord be \(AB\) and let the inscribed angle on the side opposite to a given side be \(\theta\).  Then the centre lies on the same side as that given side, and the signed distance from the midpoint of the chord to the centre in the direction of the normal pointing toward that side equals \(R\cos\theta\), where \(R\) is the radius of the circle.  (This follows from the central angle: if \(\theta\le90^\circ\) the central angle is \(2\theta\); if \(\theta>90^\circ\) the central angle is \(360^\circ-2\theta\) and the signed distance becomes \(-R\cos\theta\); in both cases the formula \(R\cos\theta\) works with the appropriate sign.)  

Thus the centres and radii of the four circles are  

\[
\begin{aligned}
O_1 &= M_{AB} + \frac{s_1}{2}\cot\alpha\,\mathbf{n}_1, &\quad r_1 &= \frac{s_1}{2\sin\alpha},\\[4pt]
O_2 &= M_{CD} + \frac{s_2}{2}\cot\beta\,\mathbf{n}_2, &\quad r_2 &= \frac{s_2}{2\sin\beta},\\[4pt]
O_3 &= M_{AB} + \frac{s_1}{2}\cot\beta\,\mathbf{n}_1, &\quad r_3 &= \frac{s_1}{2\sin\beta},\\[4pt]
O_4 &= M_{CD} + \frac{s_2}{2}\cot\alpha\,\mathbf{n}_2, &\quad r_4 &= \frac{s_2}{2\sin\alpha}.
\end{aligned}
\]

Set  

\[
\mathbf{U}=M_{AB}-M_{CD}=\left(\frac{b-c-d}{2},\;0\right).
\]

Then  

\[
O_1O_2 = \mathbf{U}+a_1\mathbf{n}_1-b_2\mathbf{n}_2,\qquad
O_3O_4 = \mathbf{U}+a_3\mathbf{n}_1-b_4\mathbf{n}_2,
\]

where  

\[
a_1=\frac{s_1}{2}\cot\alpha,\; b_2=\frac{s_2}{2}\cot\beta,\;
a_3=\frac{s_1}{2}\cot\beta,\; b_4=\frac{s_2}{2}\cot\alpha.
\]

Now compute the squared distances:

\[
\begin{aligned}
|O_1O_2|^2 &= |\mathbf{U}|^2 + a_1^2+b_2^2 + 2a_1(\mathbf{U}\!\cdot\!\mathbf{n}_1) - 2b_2(\mathbf{U}\!\cdot\!\mathbf{n}_2) - 2a_1b_2(\mathbf{n}_1\!\cdot\!\mathbf{n}_2),\\[4pt]
|O_3O_4|^2 &= |\mathbf{U}|^2 + a_3^2+b_4^2 + 2a_3(\mathbf{U}\!\cdot\!\mathbf{n}_1) - 2b_4(\mathbf{U}\!\cdot\!\mathbf{n}_2) - 2a_3b_4(\mathbf{n}_1\!\cdot\!\mathbf{n}_2).
\end{aligned}
\]

We evaluate the needed dot products:

\[
\mathbf{U}\!\cdot\!\mathbf{n}_1 = \frac{h(b-c-d)}{2s_1},\qquad
\mathbf{U}\!\cdot\!\mathbf{n}_2 = -\frac{h(b-c-d)}{2s_2}.
\]

Hence  

\[
2a_1(\mathbf{U}\!\cdot\!\mathbf{n}_1)-2b_2(\mathbf{U}\!\cdot\!\mathbf{n}_2)
= \frac{h(b-c-d)}{2}(\cot\alpha+\cot\beta),
\]

and the same expression appears for the pair \((a_3,b_4)\).  Moreover \(a_1b_2=a_3b_4\), so the cross terms \(-2a_1b_2(\mathbf{n}_1\!\cdot\!\mathbf{n}_2)\) and \(-2a_3b_4(\mathbf{n}_1\!\cdot\!\mathbf{n}_2)\) are equal.  Consequently the difference of the two squared distances is  

\[
|O_1O_2|^2-|O_3O_4|^2 = (a_1^2+b_2^2)-(a_3^2+b_4^2)
= \frac{s_1^2-s_2^2}{4}\,(\cot^2\alpha-\cot^2\beta). \tag{1}
\]

The circles \((W_1)\) and \((W_2)\) are given to be tangent.  Therefore  

\[
|O_1O_2| = r_1+r_2\quad\text{or}\quad |O_1O_2| = |r_1-r_2|,
\]

and squaring gives  

\[
|O_1O_2|^2 = (r_1\pm r_2)^2 = r_1^2+r_2^2\pm 2r_1r_2. \tag{2}
\]

Using (1) and (2),

\[
|O_3O_4|^2 = (r_1^2+r_2^2\pm 2r_1r_2) - \frac{s_1^2-s_2^2}{4}\,(\cot^2\alpha-\cot^2\beta). \tag{3}
\]

Now express the radii in terms of \(s_1,s_2,\alpha,\beta\):

\[
r_1=\frac{s_1}{2\sin\alpha},\; r_2=\frac{s_2}{2\sin\beta},\;
r_3=\frac{s_1}{2\sin\beta},\; r_4=\frac{s_2}{2\sin\alpha}.
\]

We have  

\[
r_1^2+r_2^2 = \frac{s_1^2}{4\sin^2\alpha}+\frac{s_2^2}{4\sin^2\beta},\qquad
r_3^2+r_4^2 = \frac{s_1^2}{4\sin^2\beta}+\frac{s_2^2}{4\sin^2\alpha},
\]

and  

\[
r_1r_2 = r_3r_4 = \frac{s_1s_2}{4\sin\alpha\sin\beta}.
\]

Insert \(r_1^2+r_2^2\) into (3) and write  

\[
\begin{aligned}
|O_3O_4|^2 &= \bigl(r_3^2+r_4^2\bigr) + \frac{s_1^2-s_2^2}{4}\Bigl(\frac{1}{\sin^2\alpha}-\frac{1}{\sin^2\beta}\Bigr) \pm 2r_1r_2
          - \frac{s_1^2-s_2^2}{4}(\cot^2\alpha-\cot^2\beta).
\end{aligned}
\]

The two terms containing \(s_1^2-s_2^2\) cancel because  

\[
\frac{1}{\sin^2\alpha}-\frac{1}{\sin^2\beta} = \cot^2\alpha-\cot^2\beta,
\]

which follows from the identity  

\[
\cot^2\alpha-\cot^2\beta
= \frac{\cos^2\alpha}{\sin^2\alpha}-\frac{\cos^2\beta}{\sin^2\beta}
= \frac{\cos^2\alpha\sin^2\beta-\cos^2\beta\sin^2\alpha}{\sin^2\alpha\sin^2\beta}
= \frac{\sin^2\beta-\sin^2\alpha}{\sin^2\alpha\sin^2\beta}
= \frac{1}{\sin^2\alpha}-\frac{1}{\sin^2\beta}.
\]

Hence  

\[
|O_3O_4|^2 = r_3^2+r_4^2 \pm 2r_3r_4 = (r_3\pm r_4)^2,
\]

so \(|O_3O_4| = r_3\pm r_4\).  This is precisely the condition for the circles \((W_3)\) and \((W_4)\) to be tangent (externally if the sign is \(+\), internally if the sign is \(-\)).  Therefore \((W_3)\) and \((W_4)\) are tangent, as required. ∎
