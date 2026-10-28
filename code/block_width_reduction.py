"""Width reduction for block-CNF (generalizes Schuler / CIP06 Lemma 5 from literals to block-literals).

A block-CNF has k blocks of b bits each (block l ranges over D = 2^b values). A clause holds at most
one block-literal per block, written as the set of values for which that literal is TRUE. k-OV with
D vectors per party is the case where every clause has one literal per block: coordinate t gives the
clause OR_l [x_l not in S_l^t], with S_l^t = {u : a^(l)_{u,t} = 1}.

Branching on a clause C with more than w nonconstant literals, with C' its first w of them:
  left:  replace C by C'                    (solutions with C' true)
  right: make every literal of C' false     (solutions with C' false; this restricts w domains)
The two branches have disjoint solution sets, so counts add. Every right branch shrinks w domains by
at least one value each, so the measure sum_l log2|R_l| drops by at least w*log2(D/(D-1)).

This script checks the counts against brute force on random instances and compares the number of
leaves with the CIP-style bound  sum_{r <= rmax} C(m+r, r),  rmax = n / (w*log2(D/(D-1))).
"""
import itertools
import math
import random
import sys


def brute_count(k, D, clauses, domains=None):
    domains = domains or [frozenset(range(D))] * k
    total = 0
    for x in itertools.product(*[sorted(d) for d in domains]):
        if all(any(x[l] in T for l, T in cl.items()) for cl in clauses):
            total += 1
    return total


def simplify(clauses, domains):
    """Drop literals that are constantly false and clauses that are constantly true on the domains.
    Returns None if some clause became empty (no solutions)."""
    out = []
    for cl in clauses:
        new, sat = {}, False
        for l, T in cl.items():
            live = T & domains[l]
            if live == domains[l]:
                sat = True
                break
            if live:
                new[l] = live
        if sat:
            continue
        if not new:
            return None
        out.append(new)
    return out


def count(k, D, clauses, domains, w, stats, depth_r=0):
    clauses = simplify(clauses, domains)
    if clauses is None:
        stats["leaves"] += 1
        return 0
    long_idx = next((i for i, cl in enumerate(clauses) if len(cl) > w), None)
    if long_idx is None:
        stats["leaves"] += 1
        stats["max_r"] = max(stats["max_r"], depth_r)
        return brute_count(k, D, clauses, domains)  # stand-in for a fast w*b-width SAT counter
    C = clauses[long_idx]
    first = sorted(C)[:w]
    rest = clauses[:long_idx] + clauses[long_idx + 1:]
    left = rest + [{l: C[l] for l in first}]
    right_domains = list(domains)
    for l in first:
        right_domains[l] = domains[l] - C[l]  # literal false: x_l avoids its true-set
    return (count(k, D, left, domains, w, stats, depth_r)
            + count(k, D, rest + [{l: T for l, T in C.items() if l not in first}],
                    right_domains, w, stats, depth_r + 1))


def random_kov_instance(k, D, m, density, rng):
    """k-OV style: every clause has one literal per block; literal l is TRUE where a^(l)_{u,t} = 0."""
    clauses = []
    for _ in range(m):
        cl = {}
        for l in range(k):
            ones = {u for u in range(D) if rng.random() < density}
            cl[l] = frozenset(range(D)) - ones
        clauses.append(cl)
    return clauses


def main(seed=1):
    rng = random.Random(seed)
    print(f"{'k':>3} {'D':>3} {'m':>4} {'w':>3} {'count':>8} {'ok':>3} {'leaves':>7} {'bound':>12} {'max_r':>5} {'rmax':>6}")
    for k, D, m, w, dens in [(6, 2, 18, 2, 0.5), (6, 4, 18, 2, 0.5), (5, 4, 20, 3, 0.7),
                             (4, 8, 16, 2, 0.6), (6, 4, 30, 2, 0.8), (3, 16, 12, 1, 0.5)]:
        clauses = random_kov_instance(k, D, m, dens, rng)
        stats = {"leaves": 0, "max_r": 0}
        got = count(k, D, clauses, [frozenset(range(D))] * k, w, stats)
        want = brute_count(k, D, clauses)
        n_bits = k * math.log2(D)
        rmax = n_bits / (w * math.log2(D / (D - 1)))
        bound = sum(math.comb(m + r, r) for r in range(int(rmax) + 1))
        print(f"{k:>3} {D:>3} {m:>4} {w:>3} {got:>8} {'yes' if got == want else 'NO':>3} "
              f"{stats['leaves']:>7} {bound:>12} {stats['max_r']:>5} {rmax:>6.1f}")
        if got != want:
            sys.exit("count mismatch")


if __name__ == "__main__":
    main()
