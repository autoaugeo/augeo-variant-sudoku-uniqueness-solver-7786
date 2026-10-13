"""Plain-assert tests. Run: python3 tests/run_tests.py"""

import os
import random
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import generate
import solver

TESTS = []


def test(fn):
    TESTS.append(fn)
    return fn


def per_variant(fn):
    for v in solver.VARIANTS:
        def bound(v=v):
            fn(v)
        bound.__name__ = "%s[%s]" % (fn.__name__, v)
        TESTS.append(bound)
    return fn


@per_variant
def empty_grid_has_many_solutions(v):
    assert solver.count_solutions("0" * 81, v, limit=2) >= 2, v
    assert not solver.is_unique("0" * 81, v)


@per_variant
def full_grid_checks(v):
    full = solver.fill_random(v, random.Random(7))
    assert solver.check_solution(full, v), v
    assert not solver.check_solution("0" + full[1:], v)
    cells = list(range(81))
    a = 0
    b = next(i for i in cells if full[i] != full[a])
    g = list(full)
    g[a], g[b] = g[b], g[a]
    assert not solver.check_solution("".join(g), v), v
    assert solver.is_unique(full, v)
    assert solver.solve(full, v) == full


@per_variant
def generated_puzzle_is_unique(v):
    puzzles = generate.generate_puzzles(v, 1, 1, 8.0)
    assert len(puzzles) == 1, v
    p = puzzles[0]
    puzzle, full = p["givens"], p["solution"]
    assert p["solutions_found"] == 1
    assert solver.count_solutions(puzzle, v, limit=2) == 1, v
    assert solver.is_unique(puzzle, v)
    assert solver.solve(puzzle, v) == full
    assert solver.check_solution(full, v)
    assert p["n_givens"] == sum(1 for ch in puzzle if ch != "0")
    # Removing every given of a digit pair must reopen the puzzle: swapping the two
    # digits in the solution is another valid grid, so at least 2 solutions exist.
    reopened = False
    for a in "123456789":
        for b in "123456789":
            if a < b:
                relaxed = "".join("0" if ch in (a, b) else ch for ch in puzzle)
                if solver.count_solutions(relaxed, v, limit=2) >= 2:
                    reopened = True
                    break
        if reopened:
            break
    assert reopened, v


@per_variant
def peers_are_symmetric(v):
    pr = solver.peers(v)
    assert len(pr) == 81
    for i in range(81):
        assert i not in pr[i]
        for j in pr[i]:
            assert i in pr[j], (v, i, j)
    assert len(pr[0]) >= 20


@test
def contradictory_givens_have_no_solution():
    grid = "11" + "0" * 79
    for v in solver.VARIANTS:
        assert solver.count_solutions(grid, v) == 0
        assert solver.solve(grid, v) is None


@test
def variant_specific_peers():
    # r4c4 (40) and r0c0 (0) share only the main diagonal
    assert 0 in solver.peers("x")[40] and 0 not in solver.peers("windoku")[40]
    # r1c2 (11) and r3c1 (28) share only a windoku window
    assert 28 in solver.peers("windoku")[11] and 28 not in solver.peers("x")[11]
    # r0c2 (2): r1c4 (13) is a knight move away, r1c3 (12) a diagonal king step
    assert 13 in solver.peers("antiknight")[2] and 13 not in solver.peers("antiking")[2]
    assert 12 in solver.peers("antiking")[2] and 12 not in solver.peers("antiknight")[2]
    assert 12 not in solver.peers("x")[2]


@test
def sample_puzzles_have_exactly_one_solution():
    import json
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "samples", "sample_puzzles.json")
    with open(path) as fh:
        data = json.load(fh)
    puzzles = data["puzzles"]
    assert len(puzzles) == 10
    for p in puzzles:
        v = p["variant"]
        assert v == "x"
        assert solver.count_solutions(p["givens"], v, limit=2) == 1, p["id"]
        assert solver.solve(p["givens"], v) == p["solution"], p["id"]
        assert solver.check_solution(p["solution"], v), p["id"]
        assert all(g in ("0", s) for g, s in zip(p["givens"], p["solution"])), p["id"]


def main():
    start = time.time()
    done = 0
    for fn in TESTS:
        try:
            fn()
        except AssertionError as exc:
            print("FAIL %s: %r" % (fn.__name__, exc))
            import traceback
            traceback.print_exc()
            return 1
        done += 1
    print("OK %d tests (%.1f s)" % (done, time.time() - start))
    return 0


if __name__ == "__main__":
    sys.exit(main())
