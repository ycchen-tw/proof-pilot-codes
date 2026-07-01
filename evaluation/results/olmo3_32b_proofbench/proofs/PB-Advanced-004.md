# PB-Advanced-004 — IMO-easy / Combinatorics

**Score: 6/7** &middot; pipeline output via `select:R1(2/4)`

**Grader note (Claude grader, sympy-verified):** tree-dual+centroid 分類は正しく定理も数値全通過；M=9n+1 境界の一歩に小さな穴(結論は成立)

## Problem

For a positive integer $n$, a convex $18n+2$-gon $P$ is divided into $18n$ triangles by drawing $18n-1$ diagonals. Prove that we can choose two of these diagonals such that the three parts of $P$ divided by these two diagonals each contain at least $3n$ and at most $9n$ triangles.

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

Let the triangulation of the convex \((18n+2)\)-gon be given.  The dual graph \(T\) has a vertex for each triangle and an edge for every diagonal; it is a tree with \(18n\) vertices.  Each triangle has at most three sides that are diagonals, so every vertex of \(T\) has degree at most \(3\).  The two diagonals we are looking for correspond to two edges of \(T\); after removing them the polygon is divided into three regions, and the number of triangles in each region equals the number of vertices of the corresponding component of \(T\).  Hence we have to find two edges of \(T\) whose removal splits \(T\) into three components each of size between \(3n\) and \(9n\).

---

**Lemma.**  
Let \(H\) be a tree with maximum degree at most \(3\) and with \(M\) vertices, where \(9n\le M\le 12n+1\).  Then there exists an edge \(e\) of \(H\) such that both components of \(H-e\) contain at least \(3n\) vertices (and consequently each contains at most \(9n\) vertices).

*Proof.*  Let \(v\) be a centroid of \(H\).  Because \(\deg(v)\le3\), the components of \(H-v\) are at most three; denote them by \(C_1,\dots,C_k\) (\(k\le3\)) and their sizes by \(s_1,\dots,s_k\).  We have \(\sum s_i = M-1\) and each \(s_i\le M/2\).

*If \(M=9n\):*  Then \(s_i\le 4.5n\).  If every \(s_i\) were \(<3n\), the total would be at most \(3\cdot(3n-1)=9n-3<9n\), contradicting \(\sum s_i = 9n-1\).  Hence some \(s_i\ge3n\).  Let that size be \(s\).  The edge from \(v\) to that component splits \(H\) into two parts of sizes \(s\) and \(9n-s\).  Since \(s\le4.5n\), we have \(9n-s\ge4.5n\ge3n\); also \(9n-s\le9n-3n=6n\le9n\).  Thus both parts lie in \([3n,9n]\).  (If the centroid is an edge, the two components are each at most \(M/2\) and sum to \(M\); for \(M=9n\) they are both at least \(4.5n\ge3n\) and at most \(4.5n\le9n\).)

*If \(9n<M\le12n+1\):*  Suppose every \(s_i\le3n\).  Then the total would be at most \(3\cdot3n=9n\), which is strictly smaller than \(M-1\) (since \(M>9n\)).  Hence some \(s_i\ge3n+1\).  Let that size be \(s\).  Then \(s\le M/2\) and \(M-s\ge M/2\ge4.5n\ge3n\).  Moreover \(M-s\le M-(3n+1)\le(12n+1)-(3n+1)=9n\).  Thus the edge from \(v\) to that component gives two parts each in \([3n,9n]\).  (Again, if the centroid is an edge, the two components are at least \(M/2\) and at most \(M/2\); for \(M\le12n+1\) we have \(M/2\le6n+0.5\le9n\) and \(M/2\ge4.5n\ge3n\).)  ∎

---

Now we work with the dual tree \(T\) (which has \(18n\) vertices and max degree \(\le3\)).  Let \(c\) be a centroid of \(T\).  We distinguish two cases.

**Case 1: The centroid is an edge.**  
Removing this edge splits \(T\) into two components \(A\) and \(B\).  Because the centroid is an edge, each component has at most \(9n\) vertices and their total is \(18n\); hence \(|A|=|B|=9n\).  Apply the Lemma to the tree \(A\) (size \(9n\)) to obtain an edge \(e\) inside \(A\) such that \(A-e\) has two components each of size at least \(3n\) and at most \(9n\).  The three components of \(T\) after removing the centroid edge and \(e\) are these two parts of \(A\) and the whole component \(B\) (size \(9n\)).  All three lie in \([3n,9n]\).  The two diagonals corresponding to these two edges are the desired ones.

**Case 2: The centroid is a vertex \(v\).**  
Let the components of \(T-v\) be \(C_1,C_2,\dots,C_k\) (\(k\le3\) because \(\deg(v)\le3\)).  Denote \(|C_i|=x_i\).  Then each \(x_i\le9n\) (centroid property) and \(\sum x_i = 18n-1\).

*Subcase 2a: \(k=2\).*  Then \(x_1+x_2=18n-1\) and \(x_i\le9n\).  Consequently \(\{x_1,x_2\}=\{9n,\,9n-1\}\).  Remove the edge of \(T\) joining \(v\) to the component of size \(9n\); call this edge \(e_1\).  The remaining tree \(R = v\cup C_2\) has size \(1+(9n-1)=9n\).  Apply the Lemma to \(R\) (size \(9n\)) to obtain an edge \(e_2\) inside \(R\) that splits \(R\) into two parts each of size between \(3n\) and \(9n\).  The three components of \(T\) after removing \(e_1\) and \(e_2\) are the component of size \(9n\) (the one originally attached to \(v\)) and the two parts of \(R\).  All three lie in \([3n,9n]\).

*Subcase 2b: \(k=3\).*  Write \(x_1\le x_2\le x_3\).  Because \(x_1+x_2+x_3=18n-1\) and each \(\le9n\), we have \(x_3\ge6n\) (otherwise the sum would be at most \(3\cdot(6n-1)=18n-3<18n-1\)).  We consider two possibilities.

  (i) \(x_3 = 9n\).  Then \(x_1+x_2 = 9n-1\).  Remove the edge \(e_1\) from \(v\) to \(C_3\).  The rest \(R = v\cup C_1\cup C_2\) has size \(1+(9n-1)=9n\).  Apply the Lemma to \(R\) to obtain an edge \(e_2\) that splits \(R\) into two parts each in \([3n,9n]\).  The three components are \(C_3\) (size \(9n\)) and the two parts from \(R\), all in the required interval.

  (ii) \(x_3 < 9n\).  Then \(6n\le x_3\le 9n-1\) and \(x_1+x_2 = 18n-1-x_3 \ge 9n\).  Remove the edge \(e_1\) from \(v\) to \(C_3\); the remaining tree \(R = v\cup C_1\cup C_2\) has size \(18n-x_3\).  Since \(x_3\ge6n\), we have \(18n-x_3\le12n\); since \(x_3\le9n-1\), we have \(18n-x_3\ge9n+1\).  Thus \(|R|\) lies in \([9n+1,12n]\), which is contained in the range \([9n,12n+1]\) of the Lemma.  By the Lemma, there exists an edge \(e_2\) in \(R\) such that \(R-e_2\) has two components each of size at least \(3n\) and at most \(9n\).  The three components of \(T\) after removing \(e_1\) and \(e_2\) are \(C_3\) (size \(x_3\in[6n,9n-1]\subset[3n,9n]\)) and the two parts of \(R\), all within \([3n,9n]\).

In every case we have produced two diagonals (the edges \(e_1\) and \(e_2\) of the dual tree) whose removal divides the polygon into three regions each containing between \(3n\) and \(9n\) triangles.  ∎
