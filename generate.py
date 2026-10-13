"""Generate sudoku-variant puzzles with exactly one solution.

Usage: python3 generate.py --variant x --count 10 --seed 1 --time-limit 60 --out puzzles_x.json
"""

import argparse
import json
import os
import random
import sys
import time

import solver

PREFIX = {"x": "X", "windoku": "W", "antiknight": "KN", "antiking": "KG"}
MIN_GIVENS = 30


def make_puzzle(variant, rng, deadline, hard_end, min_givens=MIN_GIVENS):
    """One (puzzle, solution) pair, or None. Digging stops at `min_givens` or at `deadline`."""
    try:
        full = solver.fill_random(variant, rng, hard_end)
        cells = list(range(81))
        rng.shuffle(cells)
        grid = list(full)
        n_givens = 81
        for idx in cells:
            if n_givens <= min_givens or time.monotonic() >= deadline:
                break
            keep = grid[idx]
            grid[idx] = "0"
            try:
                count = solver.count_solutions("".join(grid), variant, 2, deadline)
            except solver.SolverTimeout:
                grid[idx] = keep
                break
            if count == 1:
                n_givens -= 1
            else:
                grid[idx] = keep
        puzzle = "".join(grid)
        count, sols = solver.search(puzzle, variant, 2, None, hard_end)
    except solver.SolverTimeout:
        return None
    if count != 1 or sols[0] != full:
        return None
    return puzzle, full


def generate_puzzles(variant, count, seed, time_limit):
    """Return a list of puzzle dicts; fewer than `count` if the time runs out."""
    start = time.monotonic()
    hard_end = start + max(time_limit - 1.0, time_limit * 0.8)
    rng = random.Random("%s:%d" % (variant, seed))
    seen = set()
    puzzles = []
    while len(puzzles) < count:
        now = time.monotonic()
        if now >= hard_end:
            break
        deadline = now + (hard_end - now) / (count - len(puzzles))
        made = make_puzzle(variant, rng, deadline, hard_end)
        if made is None:
            continue
        puzzle, full = made
        if puzzle in seen:
            continue
        seen.add(puzzle)
        puzzles.append({
            "id": "%s-%03d" % (PREFIX[variant], len(puzzles) + 1),
            "variant": variant,
            "givens": puzzle,
            "solution": full,
            "n_givens": sum(1 for ch in puzzle if ch != "0"),
            "solutions_found": 1,
        })
    return puzzles


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate sudoku-variant puzzles with a unique solution.")
    parser.add_argument("--variant", required=True, choices=solver.VARIANTS)
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--time-limit", type=float, default=60.0, help="seconds for the whole run")
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    if args.count < 1 or args.time_limit <= 0:
        parser.error("--count must be at least 1 and --time-limit positive")

    out = args.out
    if out is None:
        name = "puzzles_%s.json" % args.variant
        out = os.path.join("/out", name) if os.path.isdir("/out") else name

    t0 = time.monotonic()
    puzzles = generate_puzzles(args.variant, args.count, args.seed, args.time_limit)
    doc = {
        "variant": args.variant,
        "seed": args.seed,
        "requested": args.count,
        "count": len(puzzles),
        "puzzles": puzzles,
    }
    parent = os.path.dirname(out)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(out, "w") as fh:
        json.dump(doc, fh, indent=1)
    print("generated %d/%d variant=%s seconds=%.1f" % (len(puzzles), args.count, args.variant, time.monotonic() - t0))
    return 0 if len(puzzles) == args.count else 3


if __name__ == "__main__":
    sys.exit(main())
