# longsystems-research

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## Purpose

An autonomous research pipeline that searches for and formally verifies
results in combinatorics (Rado numbers), then publishes them only after two
independent checks pass: a machine-checked proof and a human review gate.
The goal is a public archive where every claim can be independently
re-checked by a reader who trusts nothing about this project except the
underlying SAT solver and the Lean 4 kernel — both open-source, both
externally audited, neither controlled by this project.

## How it works

1. An LLM-driven research loop proposes a candidate lower or upper bound
   for a Rado number.
2. **Lower bound** — a SAT solver searches for an explicit witness
   coloring; the witness is checked by the Lean 4 kernel (`by rfl`, with an
   axiom audit confirming only `propext` — no `sorryAx`).
3. **Upper bound** — proven by two independent SAT solvers (CaDiCaL,
   Glucose4) reaching UNSAT agreement, backed by a DRAT certificate anyone
   can verify independently with `cadical --check` or `drat-trim`.
4. A fidelity gate cross-checks that the machine-verified witness actually
   supports the claimed numeric bound before anything is queued for
   publication — this gate has caught and rejected mismatched claims
   during development.
5. Every result is checked against existing literature before publication;
   where a result reproduces prior work, this is stated explicitly, never
   implied as new.
6. A human reviewer approves or rejects each result before it becomes
   public. Nothing is auto-published.

## Verified Results

| Result | Verification | Reference |
|---|---|---|
| R(x+y+2=z;3) = 40 | SAT witness + DRAT UNSAT certificate + Lean 4 kernel proof | Schaal (1995), *Congressus Numerantium* 111, 150–160 |
| R(2x+y=z;3) = 43 | SAT witness + DRAT UNSAT certificate + Lean 4 kernel proof | Chang, De Loera, Wesley (2022), arXiv:2210.03262, Table 3 (a=2,b=1) |

Both results match closed-form values or table entries already published
in the literature. They are independent re-derivations using a different
method (SAT solving + DRAT certificate + Lean 4 kernel proof) than the
original sources, not new mathematical discoveries — see each package's
own README for detail.

Verification packages:
- [`verification/rado_xy2z_k3/`](verification/rado_xy2z_k3/) — R(x+y+2=z;3)=40
- [`verification/rado_2xpyz_3/`](verification/rado_2xpyz_3/) — R(2x+y=z;3)=43

## Repository Structure

- `verification/` — machine-checked mathematical results (Rado numbers)

## Citation

See [`CITATION.cff`](CITATION.cff) for machine-readable citation metadata.

## License

[MIT](LICENSE)
