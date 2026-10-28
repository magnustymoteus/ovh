"""Check the eight-square identity (Anthropic ETH paper, eq. 12) on all 4096 settings:
2[x=v][y=u] = [x^y^u^v=0] * (s(x,y)s(v,u) + s(x,u)s(v,y)),  s(p,q) = (-1)^phi(p,q)."""
from itertools import product

def phi(p, q):
    s = sum(p[k] * q[kk] for k in range(3) for kk in range(k, 3))
    s += q[0]*p[1]*p[2] + p[0]*q[1]*p[2] + p[0]*p[1]*q[2]
    return s % 2

def sigma(p, q):
    return -1 if phi(p, q) else 1

B3 = list(product((0, 1), repeat=3))
bad = 0
for x, y, u, v in product(B3, repeat=4):
    lhs = 2 * (x == v) * (y == u)
    xor0 = all((a ^ b ^ c ^ d) == 0 for a, b, c, d in zip(x, y, u, v))
    rhs = xor0 * (sigma(x, y) * sigma(v, u) + sigma(x, u) * sigma(v, y))
    bad += lhs != rhs
print("settings checked:", len(B3) ** 4, "failures:", bad)
