"""Brute-force checks for Section 3 (Theorem 1, every fixed k) of paper/ovh-monotone-kov-v2.pdf.

Adapted from the scripts of the AI referees (docs/ai-review-log.md). Exact arithmetic throughout.

1. Lemma 8 (domination), one coordinate: for k <= 8, every |S|, every pattern of S, and |Y| <= 5, the law of Y given
   S dominates mu_{1/2}^{|Y|} on every up-set iff |S| + |Y| <= k - 1. Two coordinates jointly: k = 3..6, |Y| <= 2.
   Also the scalar inequality 1 - b/(m+1) >= 2^{-b} for integers 0 <= b <= m <= 60.
2. Lemma 13 (reveal order), k = 2..6: over all pairs of side shapes (core, ordered link) whose union is the chosen
   k-tuple, every confining set depends only on already revealed elements, and exactly k-1 (same core) or k-2
   (distinct cores) non-core elements are charged. The number of shape pairs is at most (e * k!)^2.
3. Parameters of Section 3, k = 2..7 and several epsilon: the exponent inequalities, A_k = 2k^2 2^k, and the bound
   on c.

Usage (from the release root): python3 -I code/general_k_checks.py
"""
import itertools
from fractions import Fraction as Fr
from math import ceil, comb, e, factorial


# ---------- 1. Lemma 8 ----------
def upsets(m):
    """All up-sets of {0,1}^m as bitmasks over the 2^m points (point index = bits of the pattern)."""
    if m == 0:
        return [0b0, 0b1]
    prev, half = upsets(m - 1), 1 << (m - 1)
    return [f0 | (f1 << half) for f0 in prev for f1 in prev if f0 & ~f1 == 0]


def law_one_coord(k, S, Spat, Y):
    """One coordinate of D0: the zero goes to a uniform one of the k chosen vectors. Law of Y's bits given S = Spat."""
    out, tot = {}, Fr(0)
    for z in range(k):
        bits = [0 if i == z else 1 for i in range(k)]
        if tuple(bits[i] for i in S) != Spat:
            continue
        key = tuple(bits[i] for i in Y)
        out[key] = out.get(key, 0) + Fr(1, k)
        tot += Fr(1, k)
    return {key: v / tot for key, v in out.items()} if tot else None


def _prod(res, L):
    """Product of two independent laws on bit tuples."""
    new = {}
    for a, pa in res.items():
        for b, pb in L.items():
            new[a + b] = new.get(a + b, 0) + pa * pb
    return new


def dominates(law, nbits, ups):
    nu = [Fr(0)] * (1 << nbits)
    for p, pr in law.items():
        nu[sum(b << i for i, b in enumerate(p))] += pr
    for U in ups:
        if sum(nu[i] for i in range(1 << nbits) if U >> i & 1) < Fr(bin(U).count("1"), 1 << nbits):
            return False
    return True


def check_lemma8():
    ups = {m: upsets(m) for m in range(6)}
    for k in range(2, 9):
        for s in range(k):
            for m in range(1, min(k - s, 5) + 1):
                S, Y = list(range(s)), list(range(s, s + m))
                ok = all(dominates(L, m, ups[m])
                         for Spat in itertools.product([0, 1], repeat=s)
                         if (L := law_one_coord(k, S, Spat, Y)) is not None)
                assert ok == (s + m <= k - 1), (k, s, m, ok)
    for k in range(3, 7):
        for s in range(k):
            for m in (1, 2):
                if s + m > k - 1:
                    continue
                S, Y = list(range(s)), list(range(s, s + m))
                for P1 in itertools.product([0, 1], repeat=s):
                    for P2 in itertools.product([0, 1], repeat=s):
                        L1, L2 = law_one_coord(k, S, P1, Y), law_one_coord(k, S, P2, Y)
                        if L1 is not None and L2 is not None:
                            assert dominates(_prod(_prod({(): Fr(1)}, L1), L2), 2 * m, ups[2 * m]), (k, s, m)
    assert all(Fr(m + 1 - b, m + 1) >= Fr(1, 2 ** b) for m in range(1, 61) for b in range(m + 1))
    print("Lemma 8: one coordinate k<=8, |Y|<=5: holds iff |S|+|Y|<=k-1; two coordinates k<=6: OK; scalar: OK")


# ---------- 2. Lemma 13 reveal order ----------
def sides(k):
    for size in range(1, k):
        for J in itertools.combinations(range(k), size):
            for c in J:
                for order in itertools.permutations([x for x in J if x != c]):
                    yield c, order


def check_reveal():
    for k in range(2, 7):
        pairs = 0
        for c, o in sides(k):
            for c2, o2 in sides(k):
                if set(o) | {c} | set(o2) | {c2} != set(range(k)):
                    continue
                pairs += 1
                revealed, charged = {c, c2}, 0
                for chain_core, chain in ((c, o), (c2, o2)):
                    for i, x in enumerate(chain):
                        assert chain_core in revealed and all(y in revealed for y in chain[:i])
                        if x not in revealed:
                            revealed.add(x)
                            charged += 1
                assert revealed == set(range(k))
                assert charged == (k - 1 if c == c2 else k - 2)
        assert pairs <= (e * factorial(k)) ** 2
        print(f"Lemma 13, k={k}: {pairs} shape pairs <= (e*k!)^2 = {(e * factorial(k)) ** 2:.0f}; reveal order OK")


# ---------- 3. Parameters ----------
def check_params():
    for k in range(2, 9):
        need = max(max((k - 1) * comb(k - 1, r - 1) + ((k - 1) ** 2 * comb(k - 2, r - 2) if r >= 2 else 0),
                       2 * (k - 1) * comb(k - 1, r - 1)) for r in range(1, k))
        assert need <= 2 * k * k * 2 ** k, k
    for k in range(2, 8):
        for eps in (Fr(1, 2), Fr(1, 10), Fr(99, 100)):
            t = ceil(16 * (k + 1) ** 2 / eps)
            M, dlt, th, eta = eps / 8, -eps / 16, eps / (8 * (k - 1)), Fr(-(k + 1), t)  # exponents of n
            assert -dlt * t >= (k + 1) ** 2
            assert th - eta <= eps / (4 * (k - 1))
            assert 2 * M + (k - 1) * (th - eta) <= eps / 2
            assert max(M - 1 + dlt * t, M - 1 + eta * t, 2 * M + (k - 1) * (th - eta) - k) <= -k + eps / 2
            assert (k + 1) * (2 * t) ** k <= (k + 1) * (33 * (k + 1) ** 2 / eps) ** k
    print("Parameters: A_k = 2k^2 2^k suffices (k<=8); exponent inequalities and c bound hold (k<=7)")


if __name__ == "__main__":
    check_lemma8()
    check_reveal()
    check_params()
