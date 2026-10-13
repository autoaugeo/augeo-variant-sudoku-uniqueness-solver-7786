"""Bitmask backtracking solver for 9x9 sudoku variants (Python 3 standard library only).

Grids are 81-character strings, row by row, '0' for an empty cell.

Variants (extra constraints on top of rows, columns and 3x3 boxes):
  x           both main diagonals hold the digits 1-9
  windoku     four extra 3x3 regions with 0-based top-left corners
              r1c1, r1c5, r5c1, r5c5 hold the digits 1-9
  antiknight  cells a chess knight move apart hold different digits
  antiking    cells a king move apart (diagonal neighbours included)
              hold different digits
"""

import time

VARIANTS = ("x", "windoku", "antiknight", "antiking")

FULL = 0x1FF
_BITS = [bin(m).count("1") for m in range(512)]
_PEER_CACHE = {}


class SolverTimeout(Exception):
    """Raised when a search passes its deadline."""


def _check_variant(variant):
    if variant not in VARIANTS:
        raise ValueError("unknown variant %r (expected one of %s)" % (variant, ", ".join(VARIANTS)))


def _units(variant):
    units = []
    for r in range(9):
        units.append([r * 9 + c for c in range(9)])
    for c in range(9):
        units.append([r * 9 + c for r in range(9)])
    for br in range(0, 9, 3):
        for bc in range(0, 9, 3):
            units.append([(br + dr) * 9 + bc + dc for dr in range(3) for dc in range(3)])
    if variant == "x":
        units.append([i * 9 + i for i in range(9)])
        units.append([i * 9 + 8 - i for i in range(9)])
    elif variant == "windoku":
        for r0, c0 in ((1, 1), (1, 5), (5, 1), (5, 5)):
            units.append([(r0 + dr) * 9 + c0 + dc for dr in range(3) for dc in range(3)])
    return units


def peers(variant):
    """Return a list of 81 tuples: the cells that may not repeat the digit of each cell."""
    _check_variant(variant)
    if variant in _PEER_CACHE:
        return _PEER_CACHE[variant]
    sets = [set() for _ in range(81)]
    for unit in _units(variant):
        for a in unit:
            for b in unit:
                if a != b:
                    sets[a].add(b)
    if variant == "antiknight":
        deltas = [(1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)]
    elif variant == "antiking":
        deltas = [(dr, dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if (dr, dc) != (0, 0)]
    else:
        deltas = []
    for i in range(81):
        r, c = divmod(i, 9)
        for dr, dc in deltas:
            rr, cc = r + dr, c + dc
            if 0 <= rr < 9 and 0 <= cc < 9:
                sets[i].add(rr * 9 + cc)
    result = [tuple(sorted(s)) for s in sets]
    _PEER_CACHE[variant] = result
    return result


def _parse(grid):
    if not isinstance(grid, str) or len(grid) != 81 or any(ch not in "0123456789" for ch in grid):
        raise ValueError("a grid is an 81-character string of digits 0-9")
    return grid


def search(grid, variant, limit=2, rng=None, deadline=None):
    """Exhaustive backtracking search that stops once `limit` solutions are found.

    Returns (count, solutions) with count <= limit and up to `limit` solution strings.
    `rng` (a random.Random) shuffles the digit order; `deadline` is a time.monotonic()
    value after which SolverTimeout is raised.
    """
    _check_variant(variant)
    _parse(grid)
    if limit < 1:
        raise ValueError("limit must be at least 1")
    pr = peers(variant)
    cand = [FULL] * 81
    done = [False] * 81

    def assign(i, bit, log):
        log.append((i, cand[i]))
        cand[i] = bit
        for p in pr[i]:
            c = cand[p]
            if c & bit:
                log.append((p, c))
                c ^= bit
                cand[p] = c
                if not c:
                    return False
        return True

    for i, ch in enumerate(grid):
        if ch != "0":
            bit = 1 << (int(ch) - 1)
            if not cand[i] & bit:
                return 0, []
            if not assign(i, bit, []):
                return 0, []
            done[i] = True

    state = {"count": 0, "nodes": 0}
    sols = []

    def rec():
        state["nodes"] += 1
        if deadline is not None and not state["nodes"] & 1023 and time.monotonic() > deadline:
            raise SolverTimeout()
        best = -1
        best_n = 10
        for i in range(81):
            if not done[i]:
                n = _BITS[cand[i]]
                if n < best_n:
                    best_n = n
                    best = i
                    if n <= 1:
                        break
        if best < 0:
            state["count"] += 1
            sols.append("".join(str(c.bit_length()) for c in cand))
            return state["count"] >= limit
        if best_n == 0:
            return False
        mask = cand[best]
        bits = [1 << d for d in range(9) if mask >> d & 1]
        if rng is not None:
            rng.shuffle(bits)
        done[best] = True
        stop = False
        for bit in bits:
            log = []
            ok = assign(best, bit, log)
            if ok and rec():
                stop = True
            for idx, old in reversed(log):
                cand[idx] = old
            if stop:
                break
        done[best] = False
        return stop

    rec()
    return state["count"], sols


def count_solutions(grid, variant, limit=2, deadline=None):
    """Number of solutions, counted exhaustively but never beyond `limit`."""
    return search(grid, variant, limit, None, deadline)[0]


def solve(grid, variant):
    """Return the first solution as an 81-character string, or None if there is none."""
    count, sols = search(grid, variant, 1)
    return sols[0] if count else None


def is_unique(grid, variant):
    """True only when the search finds exactly one solution."""
    return count_solutions(grid, variant, 2) == 1


def fill_random(variant, rng, deadline=None):
    """A random full valid grid for the variant, from a randomized DFS driven by `rng`."""
    count, sols = search("0" * 81, variant, 1, rng, deadline)
    if not count:
        raise RuntimeError("no full grid found for variant %s" % variant)
    return sols[0]


def check_solution(grid, variant):
    """True when `grid` is completely filled (digits 1-9) and breaks no constraint."""
    _check_variant(variant)
    if not isinstance(grid, str) or len(grid) != 81 or any(ch not in "123456789" for ch in grid):
        return False
    pr = peers(variant)
    for i in range(81):
        for p in pr[i]:
            if grid[p] == grid[i]:
                return False
    return True
