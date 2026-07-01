# PB-Advanced-023 — IMO-medium / Combinatorics

**Score: 0/7** &middot; pipeline output via `select:R0(4/4)`

**Grader note (Claude grader, sympy-verified):** ルール誤読で答 3001(正解 3)、行1自由+横掃きの1手探索を見落とし下界も誤り、無進展

## Problem

On a table of size $3002\times3001$, a stone is placed on the leftmost cell of the first row. James and Peter play a game on this table. Peter selects $3000$ cells, under the rule that he must choose one from each row except the first and last rows (i.e., the $1$st and $3002$th row), and there must be at most one selected cell in each column. James knows this rule too, but he doesn't know which cells Peter selected. The goal of James is to move the stone to the last row, avoiding the cells selected by Peter. The stone can only move to adjacent cells on the table. If the stone enters a cell selected by Peter, James receives a penalty of 1 point, and the stone returns to its initial position (i.e., the leftmost cell). Find the smallest positive integer $n$ such that there exists a method for James to achieve his goal before receiving a penalty of $n$ points.

**Reference short answer:** 3

## Model proof — OLMo 3 32B (OPD step_200), agentic prove→verify→refine→select

Let the board have rows \(1,2,\dots,3002\) and columns \(1,2,\dots,3001\).  
The stone starts at \((1,1)\).  
Peter selects exactly one cell in each row \(2,3,\dots,3001\) (so \(3000\) cells) with no two in the same column.  
Thus there is exactly one column that contains no selected cell; call it the *safe* column.  

James moves the stone only to adjacent cells (up, down, left, right).  
If the stone ever enters a selected cell, he receives a penalty of \(1\) point and the stone is returned to \((1,1)\).  
His goal is to reach any cell of row \(3002\).  
We are asked for the smallest positive integer \(n\) such that there exists a strategy for James that guarantees success before receiving \(n\) penalty points (i.e., with at most \(n-1\) penalties).

---

### Upper bound: \(n=3001\) works  

James enumerates the columns \(1,2,\dots,3001\) and tries them in this order.  
For each column \(c\) he performs the following attempt:

* From \((1,1)\) move horizontally to \((1,c)\) (row \(1\) has no selected cells, so this is safe).  
* Then move straight down column \(c\), row by row.  

If he reaches row \(3002\) during this attempt, he succeeds.  
If he steps on a selected cell at \((r,c)\), he receives a penalty, the stone resets to \((1,1)\), and he learns that \((r,c)\) is a selected cell.

In the worst case the safe column is the last one tried, i.e. column \(3001\).  
Thus he incurs a penalty for each of the first \(3000\) columns and succeeds on the \(3001\)-st attempt.  
He receives exactly \(3000\) penalties, which is less than \(3001\).  
Hence \(n=3001\) is achievable.

---

### Lower bound: any strategy requires at least \(3000\) penalties in the worst case  

We show that for any deterministic strategy of James (the adversary knows the strategy), Peter can choose the selected cells so that James must incur at least \(3000\) penalties before reaching row \(3002\).  

Consider the rows \(2,3,\dots,3001\).  
The stone must step on every one of these rows at least once in order to eventually reach row \(3002\).  
In each attempt (from the start until a penalty or success), the stone follows a path that eventually steps on a certain set of rows.  

Peter chooses the selected cells adaptively as follows.  
He maintains a set of rows that have already been “hit” (i.e., whose selected cell is known).  
Initially none are hit.  

During an attempt, the stone will step on some rows in increasing order (because to go down it must pass through each row).  
Let \(r\) be the smallest row in \(\{2,\dots,3001\}\) that has **not** yet been hit and that the stone steps on in this attempt.  
(Such an \(r\) exists because the stone eventually steps on all rows, and only finitely many rows have been hit so far.)  

At the moment the stone steps on row \(r\) in this attempt, it is at some column \(c\).  
Because the stone knows all previously hit selected cells (from earlier penalties), it will avoid those columns when moving down.  
Therefore \(c\) cannot be the column of any previously hit selected cell.  

Peter now declares \((r,c)\) to be the selected cell for row \(r\).  
Since the column \(c\) is different from the columns of all previously chosen selected cells, the columns of the selected cells remain distinct.  

Thus each attempt that ends with a penalty reveals exactly one new selected cell.  
After \(3000\) attempts, all rows \(2,\dots,3001\) have been hit, so the stone knows the entire set \(S\) of selected cells.  
At that point he can simply move down the unique safe column (the column that contains no selected cell) and reach row \(3002\) without any further penalty.  

Therefore any strategy must incur at least \(3000\) penalties in the worst case (one penalty per attempt until all rows are hit).  
Consequently, no strategy can guarantee success with at most \(2999\) penalties, so the smallest possible \(n\) must satisfy \(n \ge 3001\).

---

### Conclusion  

We have shown that \(n=3001\) is both achievable and necessary.  
Hence the smallest positive integer with the required property is  

\[
\boxed{3001}.
\]
