"""Resumable cube-and-conquer: can the ones of DISJ_k be partitioned into R equality matrices?

Encoding (colouring form): every one (x, y) of DISJ_k gets exactly one of R colours, and every colour class is an
equality matrix ("same block" variables as in equality_rank_sat.py). Colour renaming is broken by requiring the
colours to appear in first-occurrence order along a fixed cell order (restricted growth string). This is sound: any
colouring can be renamed into that form. Coordinate symmetry S_k is used only to reduce the initial cubes, when
the first DEPTH cells form an S_k-invariant set (whole levels of the fooling set: depth 1, k+1, ...).

Cubes are the colour patterns (restricted growth strings) of the first cells in that order. A cube that hits the
CPU limit is split on the next CUBE_STEP cells and its children go back on the queue, so hard regions are refined
adaptively.

Resumable and sleep-safe:
- each cube runs in its own process with an RLIMIT_CPU limit, which counts CPU time only, so suspend time does not count;
- every finished cube is appended to results.jsonl, and a restart skips everything already decided;
- the run can be killed at any time; only the cubes in flight are lost.

Proofs: with --proof, every UNSAT cube writes a DRAT proof (CaDiCaL 1.9.5 via pysat) refuting base.cnf plus the cube's
unit clauses, to proofs/<id>.drat. Check later with drat-trim: build cube_<id>.cnf = base.cnf + units (`emit` mode).

Usage (from the project root):
  .venv/bin/python -I code/cube_partition.py run K R DIR [--jobs J] [--cpu SECONDS] [--depth D] [--proof]
  .venv/bin/python -I code/cube_partition.py status DIR
  .venv/bin/python -I code/cube_partition.py emit DIR CUBE_ID      # writes DIR/cube_<id>.cnf for proof checking
"""
import json
import os
import resource
import signal
import sys
import time
from multiprocessing import Process

CUBE_STEP = 2


def build(k, r):
    N = 1 << k
    # cell order: the fooling pairs (x, ~x) first (no two share a rectangle), then the rest, both by |x|+|y| descending
    full = N - 1
    fooling = sorted(((x, full ^ x) for x in range(N)), key=lambda c: (-bin(c[0]).count("1"), c))
    rest = sorted(((x, y) for x in range(N) for y in range(N) if not x & y and (x | y) != full),
                  key=lambda c: (-bin(c[0] | c[1]).count("1"), c))
    cells = fooling + rest
    nv = 0

    def new():
        nonlocal nv
        nv += 1
        return nv

    col = {(cell, c): new() for cell in cells for c in range(r)}
    cls = []
    for cell in cells:
        cls.append([col[cell, c] for c in range(r)])
        for c1 in range(r):
            for c2 in range(c1 + 1, r):
                cls.append([-col[cell, c1], -col[cell, c2]])
    for c in range(r):
        for x1 in range(N):
            for x2 in range(x1 + 1, N):
                s = new()  # rows x1, x2 in the same block of colour c
                for y in range(N):
                    a = col.get(((x1, y), c))
                    b = col.get(((x2, y), c))
                    if a and b:
                        cls += [[-a, -b, s], [-s, -a, b], [-s, -b, a]]
                    elif a:
                        cls.append([-s, -a])
                    elif b:
                        cls.append([-s, -b])
    # restricted growth: used[i][c] = colour c occurs among cells[0..i]; colour c >= 1 at cell i needs c-1 before it
    cls.append([col[cells[0], 0]])
    prev = {c: (col[cells[0], c] if c == 0 else None) for c in range(r)}
    for i in range(1, len(cells)):
        cur = {}
        for c in range(1, r):
            if prev[c - 1] is None:
                cls.append([-col[cells[i], c]])
            else:
                cls.append([-col[cells[i], c], prev[c - 1]])
        for c in range(r):
            u = new()
            lits = [col[cells[i], c]] + ([prev[c]] if prev[c] else [])
            cls.append([-u] + lits)
            for l in lits:
                cls.append([-l, u])
            cur[c] = u
        prev = cur
    return cells, col, cls, nv


def rgs_extensions(prefix, n_more, r):
    """All restricted-growth extensions of a colour prefix by n_more cells, with at most r colours."""
    out = [list(prefix)]
    for _ in range(n_more):
        nxt = []
        for p in out:
            m = max(p) + 1 if p else 0
            for c in range(min(m + 1, r)):
                nxt.append(p + [c])
        out = nxt
    return [tuple(p) for p in out]


def symmetry_representatives(k, prefixes, cells):
    """Keep one prefix per orbit of S_k (coordinate permutations) followed by colour renaming.

    Sound only when the prefix cells form an S_k-invariant set: any solution X maps to sigma(X), renamed to
    restricted-growth form, which is again a solution, and its prefix is the canonical image of X's prefix.
    """
    import itertools
    D = len(prefixes[0])
    pos = {cells[i]: i for i in range(D)}
    perms = []
    for perm in itertools.permutations(range(k)):
        def p(x):
            return sum(1 << perm[i] for i in range(k) if x >> i & 1)
        img = [pos.get((p(x), p(y))) for (x, y) in cells[:D]]
        if None in img:
            return prefixes  # prefix cells are not S_k-invariant: no reduction
        perms.append(img)

    def canon(prefix):
        best = None
        for img in perms:
            moved = [None] * D
            for i, j in enumerate(img):
                moved[j] = prefix[i]
            ren = {}
            out = tuple(ren.setdefault(c, len(ren)) for c in moved)
            if best is None or out < best:
                best = out
        return best
    return sorted({canon(p) for p in prefixes})


def cube_id(prefix):
    return "c" + "".join(map(str, prefix))


def verify_colouring(k, r, colouring):
    N = 1 << k
    for c in range(r):
        E = [[int(colouring.get((x, y)) == c) for y in range(N)] for x in range(N)]
        for x1 in range(N):
            for x2 in range(x1 + 1, N):
                for y1 in range(N):
                    for y2 in range(y1 + 1, N):
                        if E[x1][y1] + E[x1][y2] + E[x2][y1] + E[x2][y2] == 3:
                            return False
    return all(((x, y) in colouring) == (not x & y) for x in range(N) for y in range(N))


def solve_cube(k, r, prefix, cpu, proof_path, out_path):
    resource.setrlimit(resource.RLIMIT_CPU, (int(cpu), int(cpu) + 5))  # SIGXCPU kills us when CPU time runs out
    from pysat.solvers import Solver
    cells, col, cls, _ = build(k, r)
    units = [[col[cells[i], c]] for i, c in enumerate(prefix)]
    t0 = time.process_time()
    with Solver(name="cadical195", bootstrap_with=cls + units, with_proof=proof_path is not None) as s:
        sat = s.solve()
        res = {"id": cube_id(prefix), "prefix": list(prefix), "cpu": round(time.process_time() - t0, 2)}
        if sat:
            m = set(v for v in s.get_model() if v > 0)
            colouring = {cell: c for (cell, c), v in col.items() if v in m}
            res["status"] = "SAT"
            res["verified"] = verify_colouring(k, r, colouring)
            res["colouring"] = [[cell[0], cell[1], c] for cell, c in colouring.items()]
        else:
            res["status"] = "UNSAT"
            if proof_path:
                with open(proof_path, "w") as f:
                    f.write("\n".join(s.get_proof()) + "\n")
    with open(out_path, "w") as f:
        json.dump(res, f)


def load_results(d):
    done = {}
    p = os.path.join(d, "results.jsonl")
    if os.path.exists(p):
        with open(p) as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line)
                    done[rec["id"]] = rec
    return done


def run(k, r, d, jobs, cpu, depth, proof):
    os.makedirs(os.path.join(d, "tmp"), exist_ok=True)
    if proof:
        os.makedirs(os.path.join(d, "proofs"), exist_ok=True)
    cfg = {"k": k, "r": r}
    cfgp = os.path.join(d, "config.json")
    if os.path.exists(cfgp):
        assert json.load(open(cfgp)) == cfg, "DIR belongs to another (k, r)"
    else:
        json.dump(cfg, open(cfgp, "w"))
        cells, col, cls, nv = build(k, r)
        with open(os.path.join(d, "base.cnf"), "w") as f:
            f.write(f"p cnf {nv} {len(cls)}\n")
            for c in cls:
                f.write(" ".join(map(str, c)) + " 0\n")
    done = load_results(d)
    # queue: start from the depth-D cubes; replace decided/split cubes by their status/children
    queue, stack = [], symmetry_representatives(k, rgs_extensions((), depth, r), build(k, r)[0])
    while stack:
        p = stack.pop()
        rec = done.get(cube_id(p))
        if rec is None:
            queue.append(p)
        elif rec["status"] == "SAT":
            print(f"SAT already found in cube {rec['id']} (verified={rec.get('verified')})")
            return
        elif rec["status"] == "SPLIT":
            stack += rgs_extensions(p, CUBE_STEP, r)
    queue.sort(key=lambda p: (len(p), p))
    resf = open(os.path.join(d, "results.jsonl"), "a")
    running = {}
    stats = {"UNSAT": sum(1 for v in done.values() if v["status"] == "UNSAT"), "SPLIT": 0, "SAT": 0}
    print(f"k={k} r={r}: {len(queue)} open cubes, {stats['UNSAT']} already UNSAT; jobs={jobs}, cpu={cpu}s", flush=True)
    t0 = time.time()
    while queue or running:
        while queue and len(running) < jobs:
            p = queue.pop(0)
            cid = cube_id(p)
            out = os.path.join(d, "tmp", cid + ".json")
            if os.path.exists(out):
                os.remove(out)
            pp = os.path.join(d, "proofs", cid + ".drat") if proof else None
            pr = Process(target=solve_cube, args=(k, r, p, cpu, pp, out))
            pr.start()
            running[cid] = (pr, p, out)
        time.sleep(0.5)
        for cid, (pr, p, out) in list(running.items()):
            if pr.is_alive():
                continue
            pr.join()
            del running[cid]
            if os.path.exists(out) and pr.exitcode == 0:
                rec = json.load(open(out))
                os.remove(out)
            else:  # killed by the CPU limit (SIGXCPU/SIGKILL): split it
                rec = {"id": cid, "prefix": list(p), "status": "SPLIT", "cpu": cpu, "exit": pr.exitcode}
                if proof and os.path.exists(os.path.join(d, "proofs", cid + ".drat")):
                    os.remove(os.path.join(d, "proofs", cid + ".drat"))
                queue += rgs_extensions(p, CUBE_STEP, r)
            resf.write(json.dumps(rec) + "\n")
            resf.flush()
            stats[rec["status"]] += 1
            print(f"[{time.time() - t0:7.0f}s] {cid}: {rec['status']} ({rec['cpu']}s)  "
                  f"UNSAT={stats['UNSAT']} SPLIT={stats['SPLIT']} open={len(queue) + len(running)}", flush=True)
            if rec["status"] == "SAT":
                print(f"*** SAT: a partition of DISJ_{k} into {r} equality matrices, verified={rec['verified']} ***",
                      flush=True)
                for pr2, _, _ in running.values():
                    pr2.kill()
                return
    print(f"ALL CUBES UNSAT: DISJ_{k} has no partition into {r} equality matrices "
          f"(modulo trusting the solver{'' if proof else '; rerun with --proof for DRAT certificates'})", flush=True)


def status(d):
    done = load_results(d)
    cnt = {}
    for v in done.values():
        cnt[v["status"]] = cnt.get(v["status"], 0) + 1
    cpu = sum(v["cpu"] for v in done.values())
    print(f"{d}: {cnt}, total CPU {cpu / 3600:.2f} h")


def emit(d, cid):
    cfg = json.load(open(os.path.join(d, "config.json")))
    rec = load_results(d)[cid]
    cells, col, cls, nv = build(cfg["k"], cfg["r"])
    units = [[col[cells[i], c]] for i, c in enumerate(rec["prefix"])]
    with open(os.path.join(d, f"cube_{cid}.cnf"), "w") as f:
        f.write(f"p cnf {nv} {len(cls) + len(units)}\n")
        for c in cls + units:
            f.write(" ".join(map(str, c)) + " 0\n")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.default_int_handler)
    mode = sys.argv[1]
    if mode == "run":
        k, r, d = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
        opts = sys.argv[5:]

        def opt(name, default):
            return type(default)(opts[opts.index(name) + 1]) if name in opts else default
        run(k, r, d, opt("--jobs", 4), opt("--cpu", 300), opt("--depth", 6), "--proof" in opts)
    elif mode == "status":
        status(sys.argv[2])
    elif mode == "emit":
        emit(sys.argv[2], sys.argv[3])
