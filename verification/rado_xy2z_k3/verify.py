"""
Independent verification: R(x+y+2=z;3) = 40.

This script encodes the problem as SAT, solves with two independent solvers,
and verifies the results. Requires: pip install python-sat

Run: python3 verify.py
"""

from pysat.solvers import Cadical153, Glucose4
from pysat.formula import CNF

def encode(k, N):
    """Encode: is there a k-coloring of [1,N] with NO monochromatic
    solution to x+y+2=z?  Variables: v(i,c) = (i-1)*k + c + 1
    meaning 'integer i gets color c'."""
    cnf = CNF()
    def V(i, c): return (i-1)*k + c + 1
    
    # Each integer gets at least one color
    for i in range(1, N+1):
        cnf.append([V(i, c) for c in range(k)])
    
    # Each integer gets at most one color (pairwise mutual exclusion)
    for i in range(1, N+1):
        for c1 in range(k):
            for c2 in range(c1+1, k):
                cnf.append([-V(i, c1), -V(i, c2)])
    
    # Forbid monochromatic solutions to x+y+2=z
    sol_count = 0
    for x in range(1, N+1):
        for y in range(1, N+1):
            z = x + y + 2
            if z <= N:
                for c in range(k):
                    cnf.append([-V(x, c), -V(y, c), -V(z, c)])
                sol_count += 1
    
    return cnf, V, sol_count

def verify_coloring(coloring, N):
    """Count monochromatic solutions to x+y+2=z in the given coloring."""
    errors = []
    for x in range(1, N+1):
        for y in range(1, N+1):
            z = x + y + 2
            if z <= N:
                if coloring[x] == coloring[y] == coloring[z]:
                    errors.append((x, y, z, coloring[x]))
    return errors

def main():
    k = 3
    print("=" * 60)
    print("VERIFICATION: R(x+y+2=z; 3)")
    print("=" * 60)
    
    # --- N=39: find coloring ---
    print("\n--- N=39: Searching for 3-coloring ---")
    cnf39, V, n_solutions = encode(k, 39)
    print(f"  CNF: {39*k} variables, {len(cnf39.clauses)} clauses")
    print(f"  Solution triples encoded: {n_solutions}")
    
    with Cadical153(bootstrap_with=cnf39) as solver:
        sat39 = solver.solve()
        print(f"  Cadical153: {'SAT' if sat39 else 'UNSAT'}")
        if sat39:
            model = solver.get_model()
            coloring = {}
            for i in range(1, 40):
                for c in range(k):
                    if V(i, c) <= len(model) and model[V(i, c)-1] > 0:
                        coloring[i] = c
                        break
            errors = verify_coloring(coloring, 39)
            color_str = ''.join(str(coloring[i]) for i in range(1, 40))
            print(f"  Coloring: {color_str}")
            print(f"  Monochromatic violations: {len(errors)}")
            print(f"  Result: {'R >= 40' if len(errors) == 0 else 'FAILED'}")
            print(f"  Palindromic: {color_str == color_str[::-1]}")
    
    # --- N=40: prove UNSAT ---
    print(f"\n--- N=40: Proving no 3-coloring exists ---")
    cnf40, _, n_solutions40 = encode(k, 40)
    print(f"  CNF: {40*k} variables, {len(cnf40.clauses)} clauses")
    print(f"  Solution triples encoded: {n_solutions40}")
    
    with Cadical153(bootstrap_with=cnf40) as solver:
        sat40_cadical = solver.solve()
        print(f"  Cadical153: {'SAT' if sat40_cadical else 'UNSAT'}")
    
    with Glucose4(bootstrap_with=cnf40) as solver:
        sat40_glucose = solver.solve()
        print(f"  Glucose4:   {'SAT' if sat40_glucose else 'UNSAT'}")
    
    if not sat40_cadical and not sat40_glucose:
        print("  Result: R <= 40 (dual-solver UNSAT confirmed)")
    else:
        print("  Result: FAILED — disagreement between solvers")
        return 1
    
    # --- Conclusion ---
    print(f"\n{'=' * 60}")
    if sat39 and not sat40_cadical and not sat40_glucose:
        print("CONCLUSION: R(x+y+2=z;3) = 40 exactly")
        print("  R >= 40: valid 3-coloring of [1,39] found")
        print("  R <= 40: every 3-coloring of [1,40] forces a solution")
        print("  Therefore R >= 41 is FALSE")
    else:
        print("CONCLUSION: Verification inconclusive — review output above")
        return 1
    
    print("=" * 60)
    return 0

if __name__ == "__main__":
    exit(main())
