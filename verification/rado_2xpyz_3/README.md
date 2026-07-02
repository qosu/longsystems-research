# Verification Artifacts: R(2x+y=z; 3) = 43

## Result
The 3-color Rado number for the equation 2x+y=z is **43**.

- Lower bound: N=42 admits a 3-coloring with no monochromatic solution.
- Upper bound: N=43 does NOT admit such a coloring.

## Files

| File | Description |
|------|-------------|
| `generate_cnf.py` | CNF generator (Chang et al. 2022 encoding) |
| `F_42.cnf` | CNF formula for N=42 (126 vars, 1428 clauses) |
| `F_43.cnf` | CNF formula for N=43 (129 vars, 1495 clauses) |
| `F_43.drat` | DRAT unsatisfiability proof for N=43 (16 KB) |
| `witness_N42.txt` | Valid 42-element coloring |
| `verify_witness.py` | Independent Python verifier for any coloring |

## Encoding (Chang, De Loera, Wesley 2022, Section 2.1.1)

Variable v_{i,c} = true iff integer i has color c (c ∈ {0,1,2}).
DIMACS index: (i-1)*3 + c + 1.

Three clause types:
1. POSITIVE: v_{i,0} ∨ v_{i,1} ∨ v_{i,2}  — each i has at least one color
2. OPTIONAL: ¬v_{i,c1} ∨ ¬v_{i,c2}  — at most one color per i
3. NEGATIVE: ¬v_{x,c} ∨ ¬v_{y,c} ∨ ¬v_{z,c}  — for each solution (x,y,z)
   to 2x+y=z with x,y,z ∈ [1,N]

## Reproducing

### Lower bound (N=42 SAT):
```bash
python3 generate_cnf.py 42 3 > F_42.cnf
cadical -q F_42.cnf                    # → SATISFIABLE
python3 verify_witness.py <witness>     # → VERIFIED
```

### Upper bound (N=43 UNSAT):
```bash
python3 generate_cnf.py 43 3 > F_43.cnf
cadical -q F_43.cnf F_43.drat          # → UNSATISFIABLE
drat-trim F_43.cnf F_43.drat           # → VERIFIED
```

## Witness (N=42)
```
220000002211111111111111211111112200000022
```
Structure: 2×2 0×6 2×2 1×14 2×1 1×7 2×2 0×6 2×2

## Solver
- CaDiCaL v1.9.4 (Biere et al. 2020)
- Command: `cadical -q -t 120 F.cnf [F.drat]`
- DRAT proof verified by drat-trim (Heule)

## Reference
Chang, De Loera, Wesley (2022). "Rado Numbers and SAT Computations."
arXiv:2210.03262. Table 3, entry (a=2,b=1): R₃(2x+y=z) = 43.
