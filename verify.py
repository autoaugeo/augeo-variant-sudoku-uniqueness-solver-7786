"""Re-check puzzle JSON files written by generate.py.

Usage: python3 verify.py puzzles_x.json [more.json ...]

For every puzzle: exactly one solution by exhaustive count (limit 2), and the stored
solution is that solution, satisfies the variant and agrees with the givens.
Exits non-zero on any failure.
"""

import json
import sys

import solver


def check_puzzle(p):
    """Return a list of problems (empty when the puzzle passes)."""
    problems = []
    variant = p.get("variant")
    givens = p.get("givens")
    solution = p.get("solution")
    if variant not in solver.VARIANTS:
        return ["unknown variant %r" % (variant,)]
    if not (isinstance(givens, str) and len(givens) == 81 and set(givens) <= set("0123456789")):
        return ["givens is not an 81-character digit string"]
    if not check_solution_text(solution):
        return ["solution is not an 81-character string of digits 1-9"]
    if not solver.check_solution(solution, variant):
        problems.append("stored solution breaks a %s constraint" % variant)
    if any(g != "0" and g != s for g, s in zip(givens, solution)):
        problems.append("stored solution disagrees with the givens")
    if p.get("n_givens") != sum(1 for g in givens if g != "0"):
        problems.append("n_givens does not match the givens")
    count, sols = solver.search(givens, variant, 2)
    if count != 1:
        problems.append("%d solution(s) found, expected exactly 1" % count)
    elif sols[0] != solution:
        problems.append("the unique solution differs from the stored one")
    return problems


def check_solution_text(s):
    return isinstance(s, str) and len(s) == 81 and set(s) <= set("123456789")


def main(argv):
    if not argv:
        print("usage: verify.py FILE.json [FILE.json ...]")
        return 2
    failed_total = 0
    for path in argv:
        try:
            with open(path) as fh:
                doc = json.load(fh)
            puzzles = doc["puzzles"]
        except (OSError, ValueError, KeyError, TypeError) as exc:
            print("%s: cannot read (%s)" % (path, exc))
            failed_total += 1
            continue
        passed = 0
        failed = 0
        seen = set()
        for p in puzzles:
            problems = check_puzzle(p)
            if p.get("givens") in seen:
                problems.append("duplicate puzzle")
            seen.add(p.get("givens"))
            if problems:
                failed += 1
                print("%s: FAIL %s: %s" % (path, p.get("id"), "; ".join(problems)))
            else:
                passed += 1
        if not puzzles:
            failed += 1
            print("%s: no puzzles" % path)
        print("%s: %d puzzles, %d passed, %d failed" % (path, len(puzzles), passed, failed))
        failed_total += failed
    return 1 if failed_total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
