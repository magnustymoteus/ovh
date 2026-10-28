"""Sanity check of the determinant lemma behind the OV deformation no-go (notes/trackA-03).

Curves p_k(T) = e_k + sum_{rho=1..R} T^rho c_{k,rho} in Q^d (k = 1..d). At each point t in 1..Q, a set
K(t) of coordinates must have p_k(t) in a subspace V(t) of dimension r. Lemma: if such curves exist, then
    sum_t max(|K(t)| - r, 0) <= d*R,
because det[p_1..p_d](T) has degree <= dR, equals 1 at T = 0, and vanishes to order >= |K(t)| - r at t.

For each random or structured instance we find the least feasible R (the curves decouple over k, so
feasibility is one rank test per k) and check the inequality.
"""
import numpy as np

rng = np.random.default_rng(0)


def least_feasible_R(d, Q, K, V, Rmax=40):
    """K[t]: set of k constrained at point t+1; V[t]: d x r basis of V(t)."""
    for R in range(0, Rmax + 1):
        ok = True
        for k in range(d):
            rows, rhs = [], []
            for ti in range(Q):
                if k not in K[ti]:
                    continue
                t = ti + 1.0
                Nt = null_basis(V[ti])  # d x (d-r), columns span V(t)^perp
                if R == 0:
                    rows.append(np.zeros((Nt.shape[1], 0)))
                else:
                    rows.append(np.hstack([Nt.T * t ** rho for rho in range(1, R + 1)]))
                rhs.append(-Nt.T[:, k])
            if not rows:
                continue
            A, b = np.vstack(rows), np.concatenate(rhs)
            if A.shape[1] == 0:
                ok = np.allclose(b, 0)
            else:
                ra = np.linalg.matrix_rank(A, tol=1e-8)
                rab = np.linalg.matrix_rank(np.column_stack([A, b]), tol=1e-8)
                ok = ra == rab
            if not ok:
                break
        if ok:
            return R
    return None


def null_basis(B):
    if B.shape[1] == 0:
        return np.eye(B.shape[0])
    u, s, vt = np.linalg.svd(B.T)
    rank = int((s > 1e-10).sum())
    return vt[rank:].T


def check(d, Q, r, frac, structured):
    K, V = [], []
    for _ in range(Q):
        Kt = set(rng.choice(d, size=max(1, int(frac * d)), replace=False).tolist())
        if structured:  # V(t) spanned by r of the constrained coordinates (cheap for those k)
            basis = sorted(Kt)[:r]
            Vt = np.eye(d)[:, basis] if basis else np.zeros((d, 0))
        else:
            Vt = rng.standard_normal((d, r))
        K.append(Kt)
        V.append(Vt)
    R = least_feasible_R(d, Q, K, V)
    lhs = sum(max(len(Kt) - r, 0) for Kt in K)
    return R, lhs


def main():
    print(f"{'d':>3} {'Q':>3} {'r':>3} {'frac':>5} {'struct':>6} {'R_min':>6} {'sum(|K|-r)+':>12} {'d*R_min':>8} {'lemma':>6}")
    bad = 0
    for d, Q, r, frac, st in [(4, 6, 1, 0.5, False), (4, 6, 1, 0.5, True), (6, 8, 2, 0.5, False),
                              (6, 8, 2, 0.75, True), (8, 6, 2, 1.0, False), (8, 10, 3, 0.5, True),
                              (5, 12, 1, 0.6, False), (6, 12, 2, 1.0, True)]:
        R, lhs = check(d, Q, r, frac, st)
        holds = R is not None and lhs <= d * R
        bad += not holds
        print(f"{d:>3} {Q:>3} {r:>3} {frac:>5} {str(st):>6} {R!s:>6} {lhs:>12} {d * R if R is not None else '-':>8} {'ok' if holds else 'FAIL':>6}")
    print("all consistent with the lemma" if not bad else f"{bad} violations")


if __name__ == "__main__":
    main()
