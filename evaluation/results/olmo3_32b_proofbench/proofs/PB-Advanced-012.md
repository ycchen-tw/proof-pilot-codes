# PB-Advanced-012 — IMO-hard / Number theory

**Score: 6/7** &middot; pipeline output via `select:R0(2/4)`

**Grader note (Claude grader, sympy-verified):** n≥5 正解(最小 2^5=32)、n=2,3,4 と p=2 の代数・mod16 矛盾を検算し成立；Z[i] の単数/互素抽出の記述が粗い軽微な穴のみ

## Problem

Let $p$ be a prime number and $a, b$ be positive integers such that

 \[
 p^{n}=a^{4}+b^{4}
 \]

 for some integer $n \geq 2$. Prove that $n \geq 5$.

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

We prove that if a prime \(p\) and positive integers \(a,b\) satisfy \(p^n=a^4+b^4\) with \(n\ge 2\), then necessarily \(n\ge 5\).

\paragraph{Case \(p=2\).}
Suppose \(2^n = a^4+b^4\). If \(a\) and \(b\) are both odd, then \(a^4\equiv b^4\equiv 1\pmod{16}\), so \(a^4+b^4\equiv 2\pmod{16}\). But \(2^n\equiv 2\pmod{16}\) only for \(n=1\), impossible. If \(a\) and \(b\) have opposite parity, then \(a^4+b^4\) is odd while \(2^n\) is even for \(n\ge 2\), contradiction. Hence \(a\) and \(b\) are both even. Write \(a=2a_1,\;b=2b_1\). Then \(2^n = 16(a_1^4+b_1^4)\), so \(2^{n-4}=a_1^4+b_1^4\). Repeating the argument, after \(k\) steps we obtain \(2^{n-4k}=a_k^4+b_k^4\) with \(a_k,b_k\) not both even (otherwise we could factor out another \(2^4\)). Because they are not both even, they cannot have opposite parity (otherwise the sum would be odd, forcing \(n-4k=0\) and \(a_k^4+b_k^4=1\), impossible). Thus \(a_k\) and \(b_k\) are both odd, so \(a_k^4+b_k^4\equiv 2\pmod{16}\). Consequently \(2^{n-4k}\equiv 2\pmod{16}\), which forces \(n-4k=1\). Hence \(n=4k+1\). The possibility \(k=0\) would give \(a,b\) both odd, which we already ruled out; therefore \(k\ge 1\) and \(n\ge 5\). So for \(p=2\) we have \(n\ge 5\).

\paragraph{Case \(p\) odd.}
Now assume \(p\) is odd and \(p^n=a^4+b^4\) with \(n\ge 2\). We will show that \(n\) cannot be \(2,3,4\); consequently \(n\ge 5\).

\subsubsection*{Reduction to a primitive equation.}
Let \(d=\gcd(a,b)\). Then \(d^4\mid p^n\), so \(d\) is a power of \(p\). Write \(a=p^k a_1,\;b=p^k b_1\) with \(\gcd(a_1,b_1)=1\). Then \(p^{n-4k}=a_1^4+b_1^4\). If \(n-4k\le 4\) we will later show that no such equation exists, so any solution with \(n\ge 2\) must have \(n-4k\ge 5\) or else \(k\ge 1\) and \(n-4k\le 4\) gives a contradiction. Hence for the purpose of ruling out \(n=2,3,4\) we may assume \(\gcd(a,b)=1\) and \(a,b\) are coprime. Moreover, because \(a^4+b^4\) is odd, \(a\) and \(b\) have opposite parity.

\subsubsection*{The case \(n=2\).}
We have \(p^2 = a^4+b^4\). This is the equation \(x^4+y^4=z^2\) with \(x=a,\;y=b,\;z=p\). It is a classical theorem (Fermat’s infinite descent) that this equation has no nontrivial positive integer solutions. A short proof: assume a primitive solution \((a,b,p)\) with \(\gcd(a,b)=1\). Then \((a^2,b^2,p)\) is a primitive Pythagorean triple. Write \(a^2 = m^2-n^2,\; b^2 = 2mn,\; p = m^2+n^2\) with \(m>n,\;\gcd(m,n)=1,\;m,n\) of opposite parity. From \(b^2=2mn\) we obtain \(mn = b^2/2\). Since \(m,n\) are coprime, one of them is a square and the other twice a square. If \(m = u^2,\; n = 2v^2\) then \(a^2 = u^4-4v^4\) and \(p = u^4+4v^4\). Then \((u^2)^2 = a^2 + (2v^2)^2\) gives a primitive Pythagorean triple \((a,2v^2,u^2)\). Parametrising it yields \(a = r^2-s^2,\; 2v^2 = 2rs,\; u^2 = r^2+s^2\) with \(r>s,\;\gcd(r,s)=1\). Then \(v^2 = rs\) implies \(r,s\) are squares: \(r=r_1^2,\; s=s_1^2\). Consequently \(u^2 = r_1^4+s_1^4\), a smaller solution. The other possibility \(m=2u^2,\; n=v^2\) is handled analogously. Hence no primitive solution exists, and therefore \(n=2\) is impossible.

\subsubsection*{The case \(n=3\).}
We have \(p^3 = a^4+b^4\). Factor in the Gaussian integers \(\mathbb Z[i]\):
\[
a^4+b^4 = (a^2+ib^2)(a^2-ib^2)=p^3.
\]
Because \(a,b\) are coprime and of opposite parity, the two factors are coprime in \(\mathbb Z[i]\) (any common divisor would divide \(2a^2\) and \(2b^2\), and since \(p\) is odd, the only possible common divisor is \(1+i\), but \(1+i\) does not divide \(a^2+ib^2\) because its norm would be even while the norm of \(a^2+ib^2\) is odd). Hence each factor is a unit times a perfect cube (since the product is a cube and the factors are coprime). Write
\[
a^2+ib^2 = u\,(x+yi)^3,
\]
where \(u\in\{\pm1,\pm i\}\) is a unit and \(x,y\in\mathbb Z\) satisfy \(x^2+y^2=p\). Because \(\gcd(x,y)=1\), one of \(x,y\) is even and the other odd. We now examine the possible units.

\begin{itemize}
\item If \(u=-1\), then \(a^2 = -(x^3-3xy^2),\; b^2 = -(3x^2y-y^3)\). Both right‑hand sides are non‑positive, impossible for positive squares.
\item If \(u=i\), then \(a^2 = -(3x^2y-y^3),\; b^2 = x^3-3xy^2\). Positivity forces \(3x^2y-y^3<0\) and \(x^3-3xy^2>0\), i.e. \(y^2>3x^2\) and \(x^2>3y^2\), which is impossible.
\item If \(u=-i\), then \(a^2 = 3x^2y-y^3,\; b^2 = -(x^3-3xy^2)\). Positivity forces \(3x^2y-y^3>0\) and \(x^3-3xy^2<0\), i.e. \(y^2<3x^2\) and \(x^2<3y^2\). This is possible, but then \(b^2\) is negative. Hence impossible.
\end{itemize}
Therefore the only possibility is \(u=1\). Thus
\[
a^2 = x^3-3xy^2 = x(x^2-3y^2),\qquad
b^2 = 3x^2y-y^3 = y(3x^2-y^2).
\tag{1}
\]
Since \(a,b\) have opposite parity, we may swap \(a\) and \(b\) so that \(a\) is even and \(b\) is odd. Then from (1) we see that \(x\) must be even and \(y\) odd (if \(x\) were odd, \(a^2\) would be odd). Hence we have \(x\) even, \(y\) odd, \(\gcd(x,y)=1\).

Now let \(d=\gcd(x,x^2-3y^2)\). Any common divisor of \(x\) and \(x^2-3y^2\) divides \(3y^2\); because \(\gcd(x,y)=1\), we get \(d\mid 3\), so \(d=1\) or \(3\). Similarly, let \(e=\gcd(y,3x^2-y^2)\); then \(e\mid 3x^2\) and \(e\mid 3x^2-y^2\) imply \(e\mid y^2\), so \(e\mid y\), and consequently \(e\mid 3\). Thus \(e=1\) or \(3\). We treat the possible cases.

\begin{itemize}
\item \textbf{Case \(d=1,\;e=1\).} Then the two factors of \(a^2\) are coprime, so \(x = u^2\) and \(x^2-3y^2 = v^2\). Hence
\[
u^4 - 3y^2 = v^2.
\]
Similarly, \(y = w^2\) and \(3x^2-y^2 = z^2\) give \(3u^4 - w^4 = z^2\). From the first equation, reducing modulo \(16\): if \(u\) is even, \(u^4\equiv0\pmod{16}\); then \(v^2\equiv -3y^2\pmod{16}\). Because \(y\) is odd, \(y^2\equiv1\) or \(9\pmod{16}\), so \(3y^2\equiv3\) or \(11\pmod{16}\), giving \(v^2\equiv13\) or \(5\pmod{16}\), impossible (squares mod \(16\) are \(0,1,4,9\)). If \(u\) is odd, \(u^4\equiv1\pmod{16}\), then \(v^2\equiv 1-3y^2\pmod{16}\) which yields \(v^2\equiv -2\) or \(-10\equiv14,6\pmod{16}\), also impossible. Hence no solution exists.

\item \textbf{Case \(d=3,\;e=1\).} Then \(x=3x_1^2\) and \(x^2-3y^2=3y_1^2\) (we rename \(y_1\) for clarity). Then \(a^2 = 9x_1^2 y_1^2\) and \(b^2 = y(3x^2-y^2)\). From \(e=1\) we obtain \(y = w^2\) and \(3x^2-y^2 = z^2\). Substituting \(x=3x_1^2\) gives
\[
27x_1^4 - w^4 = z^2.
\]
Consider this equation modulo \(4\). If \(x_1\) is odd, then \(27x_1^4\equiv 3\pmod{4}\), \(w^4\equiv1\pmod{4}\) (since \(w\) is odd because \(y\) is odd), so \(z^2\equiv 2\pmod{4}\), impossible. If \(x_1\) is even, write \(x_1=2x_2\). Then \(27x_1^4 = 27\cdot16x_2^4 = 432x_2^4 \equiv 0\pmod{16}\). Since \(w\) is odd, \(w^4\equiv1\pmod{16}\), so \(z^2\equiv -1\equiv15\pmod{16}\), impossible. Thus no solution.

\item \textbf{Case \(d=1,\;e=3\).} Then \(y=3y_1^2\) and \(3x^2-y^2=3z^2\). From \(d=1\) we have \(x = u^2\) and \(x^2-3y^2 = v^2\). Substituting \(y=3y_1^2\) gives
\[
u^4 - 27y_1^4 = v^2.
\]
If \(u\) is odd, then \(u^4\equiv1\pmod{4}\), \(27y_1^4\equiv3\pmod{4}\), so \(v^2\equiv2\pmod{4}\), impossible. If \(u\) is even, write \(u=2u_1\). Then \(u^4=16u_1^4\), so \(16u_1^4 - 27y_1^4 = v^2\). Modulo \(16\) we have \(v^2\equiv -27y_1^4\pmod{16}\). Since \(y_1\) is odd, \(y_1^4\equiv1\pmod{16}\), so \(v^2\equiv -27\equiv5\pmod{16}\), impossible. Hence no solution.

\item \textbf{Case \(d=3,\;e=3\).} Then \(x=3x_1^2\), \(y=3y_1^2\). But then \(\gcd(x,y)\ge 3\), contradicting \(\gcd(x,y)=1\). Hence this case cannot occur.
\end{itemize}
All possibilities lead to contradictions, so \(n=3\) is impossible.

\subsubsection*{The case \(n=4\).}
We have \(p^4 = a^4+b^4\). Again factor in \(\mathbb Z[i]\):
\[
a^4+b^4 = (a^2+ib^2)(a^2-ib^2)=p^4.
\]
As before, the two factors are coprime. Since \(p\) is odd, \(p\equiv1\pmod{4}\) (otherwise \(p\) remains prime in \(\mathbb Z[i]\) and the factors would be units times powers of \(p\), forcing \(b=0\)). Write \(p = \pi\overline{\pi}\) with \(\pi = x+yi\), \(x^2+y^2=p\), \(\gcd(x,y)=1\), one of \(x,y\) even. Then \(a^2+ib^2 = u\pi^4\) for some unit \(u\). The units \(\pm1,\pm i\) can be eliminated by swapping \(a,b\) and possibly using the conjugate, as argued: if \(u=-1\) then both real and imaginary parts are negative; if \(u=i\) then after swapping \(a\) and \(b\) and taking the conjugate we obtain \(a'^2+ib'^2 = (x-yi)^4\) with \(x'=y,\;y'=x\), and if \(x<y\) we can rename variables to have the representation with \(x>y\) and \(u=1\). Hence we may assume \(u=1\) and \(x>y\). Thus
\[
a^2 = x^4-6x^2y^2+y^4,\qquad b^2 = 4xy(x^2-y^2).
\tag{2}
\]
Both are positive, so \(x>y\). Observe that
\[
a^2 + (2xy)^2 = (x^2-y^2)^2.
\]
Hence \((a,2xy,x^2-y^2)\) is a primitive Pythagorean triple (since \(\gcd(x,y)=1\) and \(x,y\) have opposite parity). Therefore there exist coprime integers \(m>n\) of opposite parity such that
\[
a = m^2+n^2,\quad 2xy = 2mn,\quad x^2-y^2 = m^2-n^2.
\]
From \(2xy=2mn\) we get \(xy=mn\). Together with \(x^2-y^2=m^2-n^2\) this implies \(\{x,y\}=\{m,n\}\). Because \(x>y\) and \(m>n\), we have \(x=m,\;y=n\). Consequently \(a = m^2+n^2 = x^2+y^2 = p\). Then \(p^4 = a^4+b^4\) gives \(b^4 = p^4 - a^4 = 0\), so \(b=0\), contradicting \(b>0\). Hence \(n=4\) is impossible.

\subsubsection*{Conclusion for odd \(p\).}
We have shown that \(n=2,3,4\) cannot occur for an odd prime \(p\). Therefore \(n\ge 5\).

\paragraph{Final statement.}
Combining the two cases, we have proved that for every prime \(p\) and positive integers \(a,b\) with \(p^n = a^4+b^4\) and \(n\ge 2\), it necessarily follows that \(n\ge 5\). ∎
