"""M(k): the largest number of ones a single equality matrix E <= DISJ_k can cover (exact, via MaxSAT RC2).

Any partition of the ones of DISJ_k into p equality matrices has p >= 3^k / M(k), since DISJ_k has 3^k ones.
For k = 5 this decides r_partition(5) = 5 if M(5) <= 60.

Usage (from the project root): .venv/bin/python -I code/max_equality_submatrix.py KMAX
"""
import sys
import time

from pysat.examples.rc2 import RC2
from pysat.formula import WCNF


def max_equality_submatrix(k):
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
            if x & y:
                w.append([-e[x][y]])          # E <= DISJ_k
            else:
                w.append([e[x][y]], weight=1)  # reward each covered one
    for x1 in range(N):  # equality-matrix structure, as in equality_rank_sat.py
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
    return sum(map(sum, E)), E


def is_equality_matrix(E):
    N = len(E)
    for x1 in range(N):
        for x2 in range(x1 + 1, N):
            for y1 in range(N):
                for y2 in range(y1 + 1, N):
                    if E[x1][y1] + E[x1][y2] + E[x2][y1] + E[x2][y2] == 3:
                        return False
    return True


if __name__ == "__main__":
    kmax = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    for k in range(1, kmax + 1):
        t0 = time.time()
        m, E = max_equality_submatrix(k)
        ok = is_equality_matrix(E) and all(not E[x][y] or not (x & y) for x in range(1 << k) for y in range(1 << k))
        print(f"k={k}: M(k)={m}  (3^k={3 ** k}, 2^k={2 ** k}, lower bound on partition rank ceil(3^k/M)="
              f"{-(-3 ** k // m)})  verified={ok}  [{time.time() - t0:.1f}s]", flush=True)
