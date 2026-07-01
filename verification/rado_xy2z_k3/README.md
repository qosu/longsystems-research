# R(x+y+2=z;3) = 40 — Independent Verification (NOT a new result)

**Correction notice:** an earlier version of this README did not cite prior
literature. `R(x+y+2=z;3) = 40` follows directly from Schaal's 1995 closed-form
formula and is **not a new discovery**. This package is an independent,
machine-checked re-derivation using a different method (SAT + DRAT + Lean 4
kernel proof) than Schaal's original combinatorial argument.

## Result

- Schaal, D. (1995). "A family of 3-color Rado numbers." *Congressus
  Numerantium* 111, 150–160. Proves the closed form:
  **R₃(x+y+c=z) = 13c + 14** for all c ≥ 0.
- For c=2: 13(2)+14 = **40**.
- This package independently re-derives the same value via SAT solving
  (existence witness for N=39, UNSAT certificate for N=40) and formally
  verifies both directions with the Lean 4 kernel (`by rfl`,
  axioms = `[propext]`, no `sorryAx`).

## What this package demonstrates

Not a new mathematical fact — a **method validation**: this pipeline
(SAT witness search + DRAT UNSAT certificate + Lean 4 kernel verification)
correctly reproduces a known, independently-published result. Useful as a
calibration/trust check on the pipeline itself before it is used to report
genuinely new values.

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

## Detail

- N=39: 3-coloring EXISTS (palindromic, 0 violations) → R >= 40
- N=40: 3-coloring IMPOSSIBLE (dual-solver UNSAT + DRAT proof) → R <= 40
- Therefore R(x+y+2=z;3) = 40, matching Schaal (1995).

## Reference

Schaal, D. (1995). "A family of 3-color Rado numbers." Congressus
Numerantium 111, 150–160.
