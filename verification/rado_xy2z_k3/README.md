# R(x+y+2=z;3) = 40 — Verification Package

This package provides independently verifiable artifacts proving that the
3-color Rado number for x+y+2=z is exactly 40, refuting the claim R >= 41.

## Contents

- `verify.py` — Self-contained Python script (requires `pip install python-sat`)
- `rado_xy2z_n40.cnf` — DIMACS CNF encoding (120 vars, 2269 clauses)
- `rado_xy2z_n40.drat` — DRAT unsatisfiability proof (CaDiCaL-generated)

## Quick verification

```bash
python3 verify.py
```

## Independent DRAT check

```bash
cadical rado_xy2z_n40.cnf rado_xy2z_n40.drat --check
# exit code 20 = UNSAT confirmed
```

## Result

- N=39: 3-coloring EXISTS (palindromic, 0 violations) → R >= 40
- N=40: 3-coloring IMPOSSIBLE (dual-solver UNSAT + DRAT proof) → R <= 40
- Therefore R(x+y+2=z;3) = 40 < 41
