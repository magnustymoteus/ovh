"""SAT search for signed equality-rank decompositions of DISJ_k (follow-up to equality_rank_milp.py).

DISJ_k = sum_rho alpha_rho * E_rho, with each E_rho an equality matrix. The coefficients alpha are fixed per
solver call and enumerated outside the solver.

Encoding, per term rho:
  e[rho, x, y]   the cell bit of E_rho
  s[rho, x1, x2] (x1 < x2) "rows x1 and x2 lie in the same block"
  (e[x1,y] & e[x2,y]) -> s[x1,x2];   s[x1,x2] & e[x1,y] -> e[x2,y];   s[x1,x2] & e[x2,y] -> e[x1,y]
These force: no 2x2 submatrix has exactly three ones, which characterizes equality matrices (their bipartite
graphs are disjoint unions of bicliques). Conversely, every equality matrix satisfies them, with s = "same label".
Per cell (x, y): forbid every bit pattern p in {0,1}^r with sum_rho alpha_rho * p_rho != DISJ_k[x, y].

Usage (from the project root):
  .venv/bin/python -I code/equality_rank_sat.py alphas K R timeout solver jobs   # coefficients in {±1,±2,±1/2}
  .venv/bin/python -I code/equality_rank_sat.py one K R timeout 1,1,1,1 cadical195,kissat404   # race solvers
  .venv/bin/python -I code/equality_rank_sat.py types K R timeout solver jobs    # ALL real coefficients
  .venv/bin/python -I code/equality_rank_sat.py partition K R timeout cadical195,kissat404  # all alpha = 1
"""
import itertools
import multiprocessing as mp
import sys
import time
from fractions import Fraction as F

from pysat.solvers import Solver


def disj(k):
    N = 1 << k
    return [[1 if (x & y) == 0 else 0 for y in range(N)] for x in range(N)]


class Enc:
    def __init__(self, k, r):
        self.k, self.r, self.N = k, r, 1 << k
        self.nv = 0
        N = self.N
        self.e = [[[self.new() for _ in range(N)] for _ in range(N)] for _ in range(r)]
        self.s = [{} for _ in range(r)]
        for rho in range(r):
            for x1 in range(N):
                for x2 in range(x1 + 1, N):
                    self.s[rho][x1, x2] = self.new()

    def new(self):
        self.nv += 1
        return self.nv

    def structure_clauses(self):
        N = self.N
        for rho in range(self.r):
            e, s = self.e[rho], self.s[rho]
            for x1 in range(N):
                for x2 in range(x1 + 1, N):
                    sv = s[x1, x2]
                    for y in range(N):
                        a, b = e[x1][y], e[x2][y]
                        yield [-a, -b, sv]
                        yield [-sv, -a, b]
                        yield [-sv, -b, a]

    def cell_clauses(self, allowed, target):
        """allowed[t]: the bit patterns (tuples) a cell with target t may take."""
        r, N = self.r, self.N
        bad = {t: [p for p in itertools.product((0, 1), repeat=r) if p not in allowed[t]] for t in (0, 1)}
        for x in range(N):
            for y in range(N):
                for p in bad[target[x][y]]:
                    yield [(-self.e[rho][x][y] if p[rho] else self.e[rho][x][y]) for rho in range(r)]

    def order(self):
        """Global cell-major variable order used by every lex-leader constraint."""
        N = self.N
        return [(x, y, rho) for x in range(N) for y in range(N) for rho in range(self.r)]

    def lex_leq(self, X, Y):
        """Clauses for X <=_lex Y over literal sequences (positions with X_i == Y_i are skipped)."""
        eq = self.new()
        yield [eq]
        for a, b in zip(X, Y):
            if a == b:
                continue
            nxt = self.new()
            yield [-eq, -a, b]
            yield [-eq, a, b, nxt]
            yield [-eq, -a, -b, nxt]
            eq = nxt

    def symmetry_clauses(self, swappable):
        """Lex-leader constraints X <= gX for generators g of the symmetry group of the decomposition:
        adjacent coordinate swaps (DISJ_k is invariant under permuting coordinates on rows and columns at once)
        and swaps of adjacent terms rho, rho+1 when swappable[rho] (the allowed patterns are invariant under the
        swap). One shared variable order keeps them jointly sound."""
        order = self.order()
        X = [self.e[rho][x][y] for x, y, rho in order]
        for i in range(self.k - 1):
            def sw(z, i=i):
                bi, bj = (z >> i) & 1, (z >> (i + 1)) & 1
                return z ^ ((bi ^ bj) << i) ^ ((bi ^ bj) << (i + 1))
            Y = [self.e[rho][sw(x)][sw(y)] for x, y, rho in order]
            yield from self.lex_leq(X, Y)
        for rho in range(self.r - 1):
            if swappable[rho]:
                perm = list(range(self.r))
                perm[rho], perm[rho + 1] = rho + 1, rho
                Y = [self.e[perm[t]][x][y] for x, y, t in order]
                yield from self.lex_leq(X, Y)

    def col_structure_clauses(self):
        """Redundant column-side version of structure_clauses ("columns y1, y2 in the same block"). Implied by
        the row version; added only to strengthen propagation."""
        N = self.N
        for rho in range(self.r):
            e = self.e[rho]
            for y1 in range(N):
                for y2 in range(y1 + 1, N):
                    tv = self.new()
                    for x in range(N):
                        a, b = e[x][y1], e[x][y2]
                        yield [-a, -b, tv]
                        yield [-tv, -a, b]
                        yield [-tv, -b, a]

    def partition_symmetry_clauses(self):
        """Stronger lex-leader set for the all-equal-coefficient case. The group is generated by coordinate
        permutations, term permutations and transposition (DISJ_k is symmetric and transposes of equality
        matrices are equality matrices). We add X <= gX for every coordinate transposition, every term
        transposition, transposition itself, and transposition composed with each coordinate transposition.
        All use the same order as symmetry_clauses, so they are jointly sound."""
        order = self.order()
        X = [self.e[rho][x][y] for x, y, rho in order]

        def swap_bits(z, i, j):
            bi, bj = (z >> i) & 1, (z >> j) & 1
            return z ^ ((bi ^ bj) << i) ^ ((bi ^ bj) << j)

        coord_perms = [lambda z: z] + [lambda z, i=i, j=j: swap_bits(z, i, j)
                                       for i in range(self.k) for j in range(i + 1, self.k)]
        for idx, cp in enumerate(coord_perms):
            if idx:  # coordinate transposition
                yield from self.lex_leq(X, [self.e[rho][cp(x)][cp(y)] for x, y, rho in order])
            # transposition, composed with the coordinate transposition
            yield from self.lex_leq(X, [self.e[rho][cp(y)][cp(x)] for x, y, rho in order])
        for a in range(self.r):
            for b in range(a + 1, self.r):
                perm = list(range(self.r))
                perm[a], perm[b] = b, a
                yield from self.lex_leq(X, [self.e[perm[t]][x][y] for x, y, t in order])




PATTERNS = {}


def patterns(r):
    """Nonzero bit patterns of length r (which terms are 1 in a cell)."""
    if r not in PATTERNS:
        PATTERNS[r] = [p for p in itertools.product((0, 1), repeat=r) if any(p)]
    return PATTERNS[r]


def allowed_from_alphas(alphas):
    r = len(alphas)
    allowed = {0: {(0,) * r}, 1: set()}
    for p in patterns(r):
        val = sum(a * b for a, b in zip(alphas, p))
        if val in (0, 1):
            allowed[int(val)].add(p)
    return allowed


def swappable_for(allowed, r):
    """Term swap rho <-> rho+1 is a symmetry iff it maps the allowed pattern sets to themselves."""
    out = []
    for rho in range(r - 1):
        def sw(p):
            q = list(p)
            q[rho], q[rho + 1] = q[rho + 1], q[rho]
            return tuple(q)
        out.append(all({sw(p) for p in allowed[t]} == allowed[t] for t in (0, 1)))
    return out


def coefficient_vectors(r):
    vals = [F(1), F(-1), F(2), F(-2), F(1, 2), F(-1, 2)]
    out = set()
    for combo in itertools.combinations_with_replacement(vals, r):
        # Prune: a cell with target 1 needs some subset summing to 1.
        if not any(sum(c for c, b in zip(combo, p) if b) == 1 for p in itertools.product((0, 1), repeat=r)):
            continue
        out.add(tuple(sorted(combo, reverse=True)))
    # Plausible ones first: all +1, then +-1, then the rest.
    return sorted(out, key=lambda c: (any(abs(a) != 1 for a in c), sum(a < 0 for a in c)))


# ---- closed types: every real coefficient vector, up to which subset sums equal 0 or 1 ----

def rref(rows, r):
    """Exact reduced row echelon form of augmented rows [p_1..p_r | v]. Returns (rows, pivots) or None if
    the system is inconsistent."""
    M = [list(map(F, row)) for row in rows]
    pivots, i = [], 0
    for c in range(r):
        piv = next((j for j in range(i, len(M)) if M[j][c] != 0), None)
        if piv is None:
            continue
        M[i], M[piv] = M[piv], M[i]
        M[i] = [x / M[i][c] for x in M[i]]
        for j in range(len(M)):
            if j != i and M[j][c] != 0:
                M[j] = [a - M[j][c] * b for a, b in zip(M[j], M[i])]
        pivots.append(c)
        i += 1
    for row in M[i:]:
        if row[r] != 0:
            return None
    return M[:i], pivots


def closure(system, r):
    """For a system {p . alpha = v}, return (Z, O, alpha0): the patterns whose sum is forced to 0 / 1 on the
    solution space, and one solution. None if inconsistent."""
    red = rref([list(p) + [v] for p, v in system], r)
    if red is None:
        return None
    M, pivots = red
    alpha0 = [F(0)] * r
    for row, c in zip(M, pivots):
        alpha0[c] = row[r]
    Z, O = set(), set()
    for p in patterns(r):
        # p . alpha is constant on the solution space iff p lies in the row space of the system.
        in_span = len(rref([row[:r] + [F(0)] for row in M] + [list(p) + [F(0)]], r)[0]) == len(M)
        if in_span:
            val = sum(a * b for a, b in zip(alpha0, p))
            if val == 0:
                Z.add(p)
            elif val == 1:
                O.add(p)
    return frozenset(Z), frozenset(O), alpha0


def canonical(Z, O, r):
    best = None
    for perm in itertools.permutations(range(r)):
        def ap(p):
            return tuple(p[perm[i]] for i in range(r))
        key = (tuple(sorted(ap(p) for p in Z)), tuple(sorted(ap(p) for p in O)))
        if best is None or key < best:
            best = key
    return best


def closed_types(r):
    """All exact types (Z, O) of real coefficient vectors, up to permuting terms, with a witness alpha0."""
    start = closure([], r)
    seen = {canonical(start[0], start[1], r): ([], start)}
    frontier = [([], start)]
    while frontier:
        nxt = []
        for system, (Z, O, _) in frontier:
            for p in patterns(r):
                if p in Z or p in O:
                    continue
                for v in (0, 1):
                    sys2 = system + [(p, v)]
                    cl = closure(sys2, r)
                    if cl is None:
                        continue
                    key = canonical(cl[0], cl[1], r)
                    if key not in seen:
                        seen[key] = (sys2, cl)
                        nxt.append((sys2, cl))
        frontier = nxt
    return [cl for _, cl in seen.values()]


# ---- running ----

def verify(k, alphas, mats):
    """alphas=None checks an OR (cover) instead of a linear combination."""
    A, N = disj(k), 1 << k
    for x in range(N):
        for y in range(N):
            if alphas is None:
                val = int(any(m[x][y] for m in mats))
            else:
                val = sum(a * m[x][y] for a, m in zip(alphas, mats))
            if val != A[x][y]:
                return False
    for M in mats:  # each is an equality matrix: no 2x2 with exactly three ones
        for x1, x2 in itertools.combinations(range(N), 2):
            for y1, y2 in itertools.combinations(range(N), 2):
                if M[x1][y1] + M[x1][y2] + M[x2][y1] + M[x2][y2] == 3:
                    return False
    return True


def solve_one(k, r, allowed, swappable, solver_name, out, partition=False):
    """Worker process: one SAT instance. Sends ('SAT', mats) or ('UNSAT', None) through `out`.
    partition=True (all coefficients equal) adds redundant column structure and the stronger symmetry set."""
    enc = Enc(k, r)
    with Solver(name=solver_name) as S:
        for c in enc.structure_clauses():
            S.add_clause(c)
        for c in enc.cell_clauses(allowed, disj(k)):
            S.add_clause(c)
        if partition:
            for c in enc.col_structure_clauses():
                S.add_clause(c)
            for c in enc.partition_symmetry_clauses():
                S.add_clause(c)
        else:
            for c in enc.symmetry_clauses(swappable):
                S.add_clause(c)
        res = S.solve()
        if res:
            pos = set(v for v in S.get_model() if v > 0)
            mats = [[[1 if enc.e[rho][x][y] in pos else 0 for y in range(enc.N)] for x in range(enc.N)]
                    for rho in range(r)]
            out.put(("SAT", mats))
        else:
            out.put(("UNSAT", None))


def run_specs(k, r, specs, timeout, jobs):
    """specs: dicts with label, group, allowed, alphas (a witness), solver. Each runs in its own process with a
    hard timeout (the solver's interrupt is unreliable through pysat). When one spec of a group finishes, the
    rest of the group is cancelled (used to race solvers on the same instance). Stops at the first SAT."""
    ctx = mp.get_context("fork")
    pending, running = list(specs), []
    summary = {"sat": None, "unsat": 0, "unknown": 0}
    done_groups = set()
    while pending or running:
        while pending and len(running) < jobs and summary["sat"] is None:
            s = pending.pop(0)
            if s["group"] in done_groups:
                continue
            q = ctx.Queue()
            p = ctx.Process(target=solve_one,
                            args=(k, r, s["allowed"], swappable_for(s["allowed"], r), s["solver"], q,
                                  s.get("partition", False)))
            p.start()
            running.append((p, q, s, time.time()))
        time.sleep(0.2)
        still = []
        for p, q, s, t0 in running:
            dt = time.time() - t0
            if s["group"] in done_groups:
                p.kill()
                p.join()
                continue
            msg = None
            try:
                msg = q.get_nowait()
            except Exception:
                pass
            tag = f"  {s['label']} [{s['solver']}]"
            if msg is not None:
                p.join()
                done_groups.add(s["group"])
                if msg[0] == "SAT":
                    ok = verify(k, s["alphas"], msg[1])
                    print(f"{tag}: SAT [{dt:.1f}s] verified={ok} alphas={[str(a) for a in s['alphas']]}", flush=True)
                    for rho, m in enumerate(msg[1]):
                        print(f"    E_{rho} rows:", ["".join(map(str, row)) for row in m], flush=True)
                    if ok:
                        summary["sat"] = s["label"]
                else:
                    summary["unsat"] += 1
                    print(f"{tag}: UNSAT [{dt:.1f}s]", flush=True)
            elif dt > timeout:
                p.kill()
                p.join()
                summary["unknown"] += 1
                print(f"{tag}: unknown (timeout) [{dt:.1f}s]", flush=True)
            else:
                still.append((p, q, s, t0))
        running = still
        if summary["sat"] is not None:
            for p, *_ in running:
                p.kill()
                p.join()
            running, pending = [], []
    print(f"RESULT k={k} r={r}: {summary}", flush=True)
    return summary


def specs_from_alphas(alpha_list, solvers):
    out = []
    for alphas in alpha_list:
        label = "alphas=" + ",".join(str(a) for a in alphas)
        for sv in solvers:
            out.append({"label": label, "group": label, "allowed": allowed_from_alphas(alphas),
                        "alphas": alphas, "solver": sv})
    return out


def specs_from_types(r, solver):
    out, trivial = [], 0
    for Z, O, alpha0 in closed_types(r):
        if not O:  # no pattern sums to 1: cells of DISJ with value 1 are unsatisfiable
            trivial += 1
            continue
        allowed = {0: set(Z) | {(0,) * r}, 1: set(O)}
        label = "type Z=" + "".join("".join(map(str, p)) + " " for p in sorted(Z)).strip() + \
                " | O=" + " ".join("".join(map(str, p)) for p in sorted(O))
        out.append({"label": label, "group": label, "allowed": allowed, "alphas": alpha0, "solver": solver})
    return out, trivial


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "alphas":  # alphas K R timeout solver jobs
        k, r, tl, sv, jobs = int(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4]), sys.argv[5], int(sys.argv[6])
        specs = specs_from_alphas(coefficient_vectors(r), [sv])
        print(f"k={k} r={r}: {len(specs)} coefficient vectors, timeout={tl}s, jobs={jobs}", flush=True)
        run_specs(k, r, specs, tl, jobs)
    elif mode == "one":  # one K R timeout a1,a2,... solver1,solver2,...  (races the solvers)
        k, r, tl = int(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4])
        alphas = [F(a) for a in sys.argv[5].split(",")]
        solvers = sys.argv[6].split(",")
        print(f"k={k} r={r}: alphas={sys.argv[5]} racing {solvers}, timeout={tl}s", flush=True)
        run_specs(k, r, specs_from_alphas([alphas], solvers), tl, len(solvers))
    elif mode == "partition":  # partition K R timeout solver1,solver2,...  (all alpha = 1, stronger encoding)
        k, r, tl = int(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4])
        solvers = sys.argv[5].split(",")
        specs = specs_from_alphas([[F(1)] * r], solvers)
        for s in specs:
            s["partition"] = True
        print(f"k={k} r={r}: partition into {r} equality matrices, strong symmetry breaking, "
              f"racing {solvers}, timeout={tl}s", flush=True)
        run_specs(k, r, specs, tl, len(solvers))
    elif mode == "cover":  # cover K R timeout solver1,...  (OR of R equality matrices, overlaps allowed)
        k, r, tl = int(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4])
        solvers = sys.argv[5].split(",")
        allowed = {0: {(0,) * r}, 1: set(patterns(r))}
        specs = [{"label": f"cover r={r}", "group": "cover", "allowed": allowed, "alphas": None,
                  "solver": sv, "partition": True} for sv in solvers]
        print(f"k={k} r={r}: cover by {r} equality matrices, racing {solvers}, timeout={tl}s", flush=True)
        run_specs(k, r, specs, tl, len(solvers))
    elif mode == "types":  # types K R timeout solver jobs  (covers all real coefficient vectors)
        k, r, tl, sv, jobs = int(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4]), sys.argv[5], int(sys.argv[6])
        specs, trivial = specs_from_types(r, sv)
        print(f"k={k} r={r}: {len(specs) + trivial} closed types up to term permutation "
              f"({trivial} trivially infeasible), timeout={tl}s, jobs={jobs}", flush=True)
        run_specs(k, r, specs, tl, jobs)
    else:
        sys.exit(f"unknown mode {mode}")
