"""Enumerate partitions of the ones of DISJ_k into R equality matrices (colourings), with a cap.

Each one (x, y) gets exactly one colour; colour classes must be equality matrices (no 2x2 with exactly three
cells of that colour). Colourings are counted modulo nothing (raw), then reduced modulo
S_k (coordinate permutations acting on rows and columns together) x S_R (colour permutations).

Usage (from the project root): .venv/bin/python -I code/enumerate_partitions.py K R CAP
"""
import itertools
import sys
import time

from pysat.solvers import Solver


def enumerate_partitions(k, r, cap):
    N = 1 << k
    ones = [(x, y) for x in range(N) for y in range(N) if not x & y]
    nv = 0

    def new():
        nonlocal nv
        nv += 1
        return nv

    col = {(x, y, c): new() for (x, y) in ones for c in range(r)}
    cls = []
    for (x, y) in ones:
        cls.append([col[x, y, c] for c in range(r)])
        for c1 in range(r):
            for c2 in range(c1 + 1, r):
                cls.append([-col[x, y, c1], -col[x, y, c2]])
    for c in range(r):
        for x1 in range(N):
            for x2 in range(x1 + 1, N):
                s = new()  # rows x1, x2 in the same block of colour c
                for y in range(N):
                    a = col.get((x1, y, c))
                    b = col.get((x2, y, c))
                    if a and b:
                        cls += [[-a, -b, s], [-s, -a, b], [-s, -b, a]]
                    elif a:
                        cls.append([-s, -a])
                    elif b:
                        cls.append([-s, -b])
    # colour symmetry breaking: first-occurrence order of colours along `ones` is 0, 1, 2, ...
    # (cheap version: cell 0 has colour 0)
    cls.append([col[ones[0][0], ones[0][1], 0]])
    sols = []
    with Solver(name="cadical195", bootstrap_with=cls) as s:
        while len(sols) < cap and s.solve():
            m = set(v for v in s.get_model() if v > 0)
            colouring = tuple(next(c for c in range(r) if col[x, y, c] in m) for (x, y) in ones)
            sols.append(colouring)
            s.add_clause([-col[x, y, c] for (x, y), c in zip(ones, colouring)])
    return ones, sols


def canonical(k, ones, colouring):
    """Lexicographically least relabelled colouring over S_k (coordinates) x colour renaming."""
    pos = {xy: i for i, xy in enumerate(ones)}
    best = None
    for perm in itertools.permutations(range(k)):
        def p(x):
            return sum(1 << perm[i] for i in range(k) if x >> i & 1)
        img = [None] * len(ones)
        for i, (x, y) in enumerate(ones):
            img[pos[p(x), p(y)]] = colouring[i]
        ren, out = {}, []
        for c in img:  # rename colours by first occurrence
            ren.setdefault(c, len(ren))
            out.append(ren[c])
        out = tuple(out)
        if best is None or out < best:
            best = out
    return best


if __name__ == "__main__":
    k, r, cap = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    t0 = time.time()
    ones, sols = enumerate_partitions(k, r, cap)
    classes = {canonical(k, ones, c) for c in sols}
    print(f"k={k} r={r}: {len(sols)} colourings with cell 0 coloured 0 (cap {cap}), "
          f"{len(classes)} classes mod S_{k} x S_{r}  [{time.time() - t0:.1f}s]", flush=True)
