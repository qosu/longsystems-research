#!/usr/bin/env python3
"""
CNF generator for R_k(2x+y=z).
Encoding follows Chang, De Loera, Wesley (2022, arXiv:2210.03262) Section 2.1.1.

Variable scheme:
  v_{i,c} = Boolean, true iff integer i receives color c
  DIMACS variable index: (i-1)*k + c + 1   (1-indexed)

Clause types:
  POSITIVE:  v_{i,1} ∨ v_{i,2} ∨ ... ∨ v_{i,k}    for each i ∈ [1,n]
    Ensures every integer has at least one color.

  OPTIONAL (uniqueness):  ¬v_{i,c1} ∨ ¬v_{i,c2}    for each i, c1 < c2
    Ensures at most one color per integer. Not logically required
    but gives 1:1 correspondence with valid colorings.

  NEGATIVE:  ¬v_{x,c} ∨ ¬v_{y,c} ∨ ¬v_{z,c}      for each solution (x,y,z)
    to 2x+y=z with x,y,z ∈ [1,n] and each color c ∈ [0,k-1].
    Forbids monochromatic solutions.

Usage:
  python3 generate_cnf.py N K > output.cnf
"""
import sys

def generate(n, k=3):
    def var(i, c):
        return (i - 1) * k + c + 1

    clauses = []

    # POSITIVE clauses
    for i in range(1, n + 1):
        clauses.append([var(i, c) for c in range(k)])

    # OPTIONAL uniqueness clauses
    for i in range(1, n + 1):
        for c1 in range(k):
            for c2 in range(c1 + 1, k):
                clauses.append([-var(i, c1), -var(i, c2)])

    # NEGATIVE clauses: for each (x,y) with z=2x+y ≤ n, forbid monochrome
    for x in range(1, n + 1):
        for y in range(1, n + 1):
            z = 2 * x + y
            if z <= n:
                for c in range(k):
                    clauses.append([-var(x, c), -var(y, c), -var(z, c)])

    lines = [f"p cnf {n * k} {len(clauses)}"]
    for clause in clauses:
        lines.append(" ".join(str(lit) for lit in clause) + " 0")

    return "\n".join(lines)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 generate_cnf.py N [K=3]", file=sys.stderr)
        sys.exit(1)
    n = int(sys.argv[1])
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    print(generate(n, k))
