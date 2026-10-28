# Star Plucking: Monotone Lower Bounds for k-List Orthogonal Vectors at Logarithmic Dimension

**Patryk Pilichowski**, University of Antwerp ·
ORCID [0009-0003-8302-6926](https://orcid.org/0009-0003-8302-6926) ·
[Google Scholar](https://scholar.google.com/citations?user=Yjgl4RAAAAAJ&hl=en)

**Report (version 2):** [`paper/ovh-monotone-kov-v2.pdf`](paper/ovh-monotone-kov-v2.pdf). Version 1 (three lists
only) is kept unchanged at [`paper/ovh-monotone-3ov.pdf`](paper/ovh-monotone-3ov.pdf); the changes are listed in
the introduction of version 2.

> [!WARNING]
> **Work in progress: not verified.**
> - **AI-generated:** the proofs, computations and code were produced by Claude (Anthropic, Claude Opus 5.5) in
>   sessions directed by the author, who has not independently verified the mathematics.
> - **No human review:** the main proofs were checked only by AI referee agents of the same model family
>   ([`docs/ai-review-log.md`](docs/ai-review-log.md)).
> - **No formal verification:** nothing is formalized in Lean, and the SAT results have no DRAT certificates.
>
> **Everything here still needs thorough verification. Do not cite these results as established.**

## Summary

**Main claim:** for every fixed k ≥ 2 and ε > 0, every monotone circuit deciding whether k lists of n vectors in
{0,1}^d, with d ≥ c(k, ε)·log n, contain no orthogonal k-tuple needs n^{k−ε} gates. For k = 2 this is a theorem of
[CLSS, arXiv:2607.23799](https://arxiv.org/abs/2607.23799); for k ≥ 3 their bounds need superlogarithmic dimension.

**Other results** (on routes to refuting OVH):
- a conditional algorithm for block-CNF with constant block size;
- a heuristic no-go for linear deformation designs;
- equality ranks of DISJ_k over ℝ: r(1..4) = 2, 2, 3, 4, and r(5) ∈ {4, 5};
- an LP barrier for proving these ranks.

None of this proves or disproves OVH.

## Contents

| path | contents |
|---|---|
| `paper/` | the report (`.tex`, `.pdf`) |
| `code/` | scripts for the computer-assisted claims |
| `data/` | run logs |
| `docs/ai-review-log.md` | AI review verdicts and fixes |
| `SHA256SUMS`, `SHA256SUMS-v1`, `*.ots` | file hashes (current and version 1) and [OpenTimestamps](https://opentimestamps.org) proofs |

## Reproducing

```bash
python3 -m venv .venv && .venv/bin/pip install -r code/requirements.txt
```

| claim | command | log |
|---|---|---|
| Thm 15 (k=3) | `.venv/bin/python -I code/equality_rank_sat.py types 3 2 600 cadical195 8` | `data/sat_k3_r2_types.log` |
| Thm 15 (k=4) | `.venv/bin/python -I code/equality_rank_sat.py types 4 3 600 cadical195 8` | `data/sat_k4_r3_types.log` |
| Prop 16 (k=5) | `.venv/bin/python -I code/equality_rank_sat.py types 5 4 1200 cadical195 8` | `data/sat_k5_r4_types.log` |
| Prop 16, open case | `.venv/bin/python -I code/cube_partition.py run 5 4 DIR --cpu 900` | `data/cubes_k5_r4.log` |
| Prop 17 |
| Thm 15, Prop 16 (upper-bound certificates) | `python3 -I code/verify_certificates.py data/upper_bound_certificates.log` | `data/upper_bound_certificates.log` |
| Thm 1 (Lemmas 8, 13, parameters) | `python3 -I code/general_k_checks.py` | `data/general_k_checks.log` | `.venv/bin/python -I code/fractional_cover.py K [partition]` | `data/fractional_cover_k5*.log` |
| §4.2 (heuristic) | `.venv/bin/python -I code/deformation_nogo.py` | none |
| Thm 14 | `.venv/bin/python -I code/block_width_reduction.py` | none |

The other scripts are helpers; their usage is in their docstrings. The proofs of Theorems 1 and 2 use no code; the last row only sanity-checks finite cases. Theorem numbers refer to version 2.

To verify a timestamp: `pip install opentimestamps-client && ots verify paper/ovh-monotone-kov-v2.pdf.ots`.
Version 1's proofs are `paper/ovh-monotone-3ov.{pdf,tex}.ots` and `SHA256SUMS-v1.ots` (for `SHA256SUMS-v1`, the
file list as of version 1).

## License

© 2026 Patryk Pilichowski. [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); see [`LICENSE`](LICENSE).
