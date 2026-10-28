"""Independent check of the equality-rank upper-bound certificates in data/upper_bound_certificates.log.

For each k, the log lists 0/1 matrices E_0, ..., E_{r-1} (rows indexed by x, columns by y, subsets of [k] as bitmasks).
This script checks, without using equality_rank_sat.py, that
  (1) each E is an equality matrix: any two rows have equal or disjoint supports (a disjoint union of all-ones
      blocks with disjoint row and column sets), and
  (2) E_0 + ... + E_{r-1} = DISJ_k entrywise, i.e. the E's partition the ones of DISJ_k.

Usage (from the release root): python3 -I code/verify_certificates.py data/upper_bound_certificates.log
"""
import ast
import re
import sys


def check(k, mats):
    N = 1 << k
    for E in mats:
        assert len(E) == N and all(len(row) == N for row in E)
        supports = [frozenset(y for y in range(N) if row[y]) for row in E]
        for a in supports:
            for b in supports:
                assert a == b or not (a & b), "not an equality matrix"
    for x in range(N):
        for y in range(N):
            assert sum(E[x][y] for E in mats) == (1 if x & y == 0 else 0), f"wrong sum at ({x},{y})"


def main():
    blocks, cur = [], None
    for line in open(sys.argv[1]):
        m = re.match(r"k=(\d+) r=(\d+):", line)
        if m:
            cur = (int(m.group(1)), int(m.group(2)), [])
            blocks.append(cur)
        m = re.match(r"\s+E_\d+ rows: (\[.*\])", line)
        if m and cur is not None:
            cur[2].append([[int(ch) for ch in row] for row in ast.literal_eval(m.group(1))])
    for k, r, mats in blocks:
        assert len(mats) == r, f"k={k}: expected {r} matrices, found {len(mats)}"
        check(k, mats)
        print(f"k={k}: DISJ_{k} is partitioned by {r} equality matrices: OK")


if __name__ == "__main__":
    main()
