#!/usr/bin/env python3
"""
Independent witness verifier for R(2x+y=z;3) = 43.

Verifies that a given 3-coloring of [1,N] contains NO monochromatic
solution to 2x+y=z. No external dependencies beyond Python stdlib.

Usage:
  python3 verify_witness.py <coloring_string> [--verbose]
  
Example:
  python3 verify_witness.py 220000002211111111111111211111112200000022
"""
import sys

def verify(col_str, verbose=False):
    """Returns (valid, violations) where valid is True iff no violations."""
    n = len(col_str)
    # Validate input
    valid_chars = set('012')
    for i, c in enumerate(col_str):
        if c not in valid_chars:
            raise ValueError(f"Invalid color '{c}' at position {i+1}")
    
    violations = []
    checked = 0
    
    for x in range(1, n + 1):
        cx = int(col_str[x - 1])
        for y in range(1, n + 1):
            z = 2 * x + y
            if z <= n:
                checked += 1
                cy = int(col_str[y - 1])
                cz = int(col_str[z - 1])
                if cx == cy == cz:
                    violations.append((x, y, z, cx))
                    if verbose:
                        print(f"  VIOLATION: 2*{x}({cx}) + {y}({cy}) = {z}({cz})")
    
    if verbose:
        print(f"Checked {checked} triples (x,y,z) with 2x+y=z")
    
    return len(violations) == 0, violations

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 verify_witness.py <coloring_string> [--verbose]")
        sys.exit(1)
    
    coloring = sys.argv[1]
    verbose = "--verbose" in sys.argv
    
    print(f"Verifying coloring of length {len(coloring)}: {coloring}")
    
    try:
        valid, violations = verify(coloring, verbose)
        if valid:
            print(f"✓ VERIFIED: Zero monochromatic solutions to 2x+y=z in [1,{len(coloring)}]")
            sys.exit(0)
        else:
            print(f"✗ FAILED: {len(violations)} monochromatic solution(s) found")
            sys.exit(1)
    except ValueError as e:
        print(f"✗ ERROR: {e}")
        sys.exit(2)
