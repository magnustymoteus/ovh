"""Fractional cover number of DISJ_k by equality submatrices (column generation).

Dual LP: maximize sum of weights w(x, y) over the ones of DISJ_k, subject to every equality matrix E <= DISJ_k
having weight <= 1. Any feasible w with total T proves that every cover (OR) of DISJ_k by equality matrices,
and in particular every partition, uses at least ceil(T) terms. By averaging, w may be taken invariant under
coordinate permutations and transposition, so it depends only on the orbit {|x|, |y|} of the entry.

Separation (the heaviest E for given w) is weighted MaxSAT (RC2), encoded as in max_equality_submatrix.py.
The final certificate is checked with integer weights: an exact MaxSAT optimum B for integer weights W,
total T, gives the bound T / B.

Usage (from the project root): .venv/bin/python -I code/fractional_cover.py K [partition]

With 'partition', weights may be negative: sum_E w(E) = w(DISJ_k) holds exactly for a partition, so the bound is
still valid for partitions (not covers), and the separation must also see non-maximal E (z >= a + b - 1).
"""
import sys
import time
from fractions import Fraction

import numpy as np
from pysat.examples.rc2 import RC2
from pysat.formula import WCNF
from scipy.optimize import linprog


def orbit(x, y):
    a, b = bin(x).count("1"), bin(y).count("1")
    return (min(a, b), max(a, b))


def heaviest_equality_submatrix(k, W):
    """Exact max of sum W[orbit] over the ones of an equality matrix E <= DISJ_k (W: dict orbit -> int >= 0)."""
    N = 1 << k
    nv = 0

    def new():
        nonlocal nv
        nv += 1
        return nv

    e = [[new() for _ in range(N)] for _ in range(N)]
    w = WCNF()
    for x in range(N):
        for y in range(N):
            if x & y or W[orbit(x, y)] == 0:
                w.append([-e[x][y]])
            else:
                w.append([e[x][y]], weight=W[orbit(x, y)])
    for x1 in range(N):
        for x2 in range(x1 + 1, N):
            s = new()
            for y in range(N):
                a, b = e[x1][y], e[x2][y]
                w.append([-a, -b, s])
                w.append([-s, -a, b])
                w.append([-s, -b, a])
    with RC2(w) as rc2:
        model = rc2.compute()
        pos = set(v for v in model if v > 0)
    E = [[1 if e[x][y] in pos else 0 for y in range(N)] for x in range(N)]
    return E


def heaviest_equality_submatrix_milp(k, W, signed=False):
    """Same optimum as heaviest_equality_submatrix, via a small MILP (HiGHS, gap 0).

    Each block R x C of an equality matrix E <= DISJ_k satisfies (union R) & (union C) = 0, so it lies in
    2^S x 2^{~S} with S = union R; blocks with equal S can be merged. So E is: an injective labelling of
    blocks by sets S, rows x assigned to at most one S with x <= S, columns y to at most one S with y & S = 0.
    Variables a[x,S], b[y,S], z[x,y,S] = a AND b (z <= a, z <= b; with negative weights also z >= a + b - 1).
    """
    from scipy.optimize import Bounds, LinearConstraint, milp
    from scipy.sparse import lil_matrix
    N = 1 << k
    a = {(x, S): None for S in range(N) for x in range(N) if x & ~S == 0}
    b = {(y, S): None for S in range(N) for y in range(N) if y & S == 0}
    z = {(x, y, S): None for (x, S) in a for y in range(N) if y & S == 0}
    idx = 0
    for d in (a, b, z):
        for key in d:
            d[key] = idx
            idx += 1
    c = np.zeros(idx)
    for (x, y, S), i in z.items():
        c[i] = -W[orbit(x, y)]
    nrows = (3 if signed else 2) * len(z) + 2 * N
    A = lil_matrix((nrows, idx))
    r = 0
    for (x, y, S), i in z.items():
        A[r, i], A[r, a[x, S]] = 1, -1
        A[r + 1, i], A[r + 1, b[y, S]] = 1, -1
        r += 2
    if signed:
        for (x, y, S), i in z.items():
            A[r, i], A[r, a[x, S]], A[r, b[y, S]] = -1, 1, 1
            r += 1
    for (x, S), i in a.items():
        A[r + x, i] = 1
    for (y, S), i in b.items():
        A[r + N + y, i] = 1
    ub = np.concatenate([np.zeros(2 * len(z)), np.ones(len(z)) if signed else [], np.ones(2 * N)])
    res = milp(c, constraints=LinearConstraint(A.tocsr(), -np.inf, ub), integrality=np.ones(idx),
               bounds=Bounds(0, 1), options={"mip_rel_gap": 0})
    E = [[0] * N for _ in range(N)]
    for (x, y, S), i in z.items():  # read E off the labels: z may be 0 on zero-weight cells
        if res.x[a[x, S]] > 0.5 and res.x[b[y, S]] > 0.5:
            E[x][y] = 1
    return E


def is_equality_le_disj(E):
    N = len(E)
    if any(E[x][y] and x & y for x in range(N) for y in range(N)):
        return False
    for x1 in range(N):
        for x2 in range(x1 + 1, N):
            for y1 in range(N):
                for y2 in range(y1 + 1, N):
                    if E[x1][y1] + E[x1][y2] + E[x2][y1] + E[x2][y2] == 3:
                        return False
    return True


def counts(k, E, orbits):
    N = 1 << k
    c = dict.fromkeys(orbits, 0)
    for x in range(N):
        for y in range(N):
            if E[x][y]:
                c[orbit(x, y)] += 1
    return [c[o] for o in orbits]


def fractional_cover(k, scale=10 ** 4, max_iter=500, signed=False):
    """signed=True: fractional PARTITION bound; weights may be negative (valid only for partitions)."""
    N = 1 << k
    orbits = sorted({orbit(x, y) for x in range(N) for y in range(N) if not x & y})
    size = counts(k, [[int(not x & y) for y in range(N)] for x in range(N)], orbits)
    # initial pool: the maximal rectangles 2^S x 2^{~S}
    pool = []
    for S in range(N):
        E = [[int((x & ~S) == 0 and (y & S) == 0) for y in range(N)] for x in range(N)]
        pool.append(counts(k, E, orbits))
    best_cert = None
    for it in range(max_iter):
        res = linprog(-np.array(size, float), A_ub=np.array(pool, float), b_ub=np.ones(len(pool)),
                      bounds=[(-4, 4) if signed else (0, None)] * len(orbits), method="highs")
        w = res.x
        W = {o: int(round(wi * scale)) for o, wi in zip(orbits, w)}
        E = heaviest_equality_submatrix_milp(k, W, signed)
        assert is_equality_le_disj(E)
        c = counts(k, E, orbits)
        B = sum(ci * W[o] for ci, o in zip(c, orbits))
        T = sum(si * W[o] for si, o in zip(size, orbits))
        bound = Fraction(T, B)
        if best_cert is None or bound > best_cert[0]:
            best_cert = (bound, W, B, T)
        print(f"it {it}: LP value {-res.fun:.5f}, separation {sum(ci * wi for ci, wi in zip(c, w)):.5f}, "
              f"certified bound {float(bound):.5f}  [{time.time() - t0:.1f}s]", flush=True)
        if sum(ci * wi for ci, wi in zip(c, w)) <= 1 + 1e-7:
            break
        pool.append(c)
    return best_cert, orbits


if __name__ == "__main__":
    k = int(sys.argv[1])
    signed = len(sys.argv) > 2 and sys.argv[2] == "partition"
    t0 = time.time()
    (bound, W, B, T), orbits = fractional_cover(k, signed=signed)
    print(f"k={k}: certified fractional {'partition' if signed else 'cover'} bound {bound} = {float(bound):.5f}; integer weights "
          f"{ {o: W[o] for o in orbits} }, max equality-submatrix weight B={B}, total T={T}")
