# Star Plucking: A Monotone n^{3−o(1)} Lower Bound for 3-List Orthogonal Vectors

**Patryk Pilichowski**, University of Antwerp ·
ORCID [0009-0003-8302-6926](https://orcid.org/0009-0003-8302-6926) ·
[Google Scholar](https://scholar.google.com/citations?user=Yjgl4RAAAAAJ&hl=en)

**Report:** [`paper/ovh-monotone-3ov.pdf`](paper/ovh-monotone-3ov.pdf)

> [!WARNING]
> **Work in progress: not verified.**
> - **AI-generated:** the proofs, computations and code were produced by Claude (Anthropic, Claude Opus 5.5) in
>   sessions directed by the author, who has not independently verified the mathematics.
> - **No human review:** the main proof was checked only by AI referee agents of the same model family
>   ([`docs/ai-review-log.md`](docs/ai-review-log.md)).
> - **No formal verification:** nothing is formalized in Lean, and the SAT results have no DRAT certificates.
>
> **Everything here still needs thorough verification. Do not cite these results as established.**

## Summary

**Main claim:** every monotone circuit deciding whether three lists of n vectors in {0,1}^d, with d ≥ c(ε)·log n,
contain no orthogonal triple needs n^{3−ε} gates. This extends the two-list theorem of
[CLSS, arXiv:2607.23799](https://arxiv.org/abs/2607.23799) to three lists.

**Other results** (on routes to refuting OVH):
- a block-CNF collapse;
- a no-go for linear deformation designs;
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
| `SHA256SUMS`, `*.ots` | file hashes and [OpenTimestamps](https://opentimestamps.org) proofs |

## Reproducing

```bash
python3 -m venv .venv && .venv/bin/pip install -r code/requirements.txt
```

| claim | command | log |
|---|---|---|
| Thm 10 (k=3) | `.venv/bin/python -I code/equality_rank_sat.py types 3 2 600 cadical195 8` | `data/sat_k3_r2_types.log` |
| Thm 10 (k=4) | `.venv/bin/python -I code/equality_rank_sat.py types 4 3 600 cadical195 8` | `data/sat_k4_r3_types.log` |
| Prop 11 (k=5) | `.venv/bin/python -I code/equality_rank_sat.py types 5 4 1200 cadical195 8` | `data/sat_k5_r4_types.log` |
| Prop 11, open case | `.venv/bin/python -I code/cube_partition.py run 5 4 DIR --cpu 900` | `data/cubes_k5_r4.log` |
| Prop 12 | `.venv/bin/python -I code/fractional_cover.py K [partition]` | `data/fractional_cover_k5*.log` |
| Prop 9 | `.venv/bin/python -I code/deformation_nogo.py` | none |
| Thm 8 | `.venv/bin/python -I code/block_width_reduction.py` | none |

The other scripts are helpers; their usage is in their docstrings. Theorem 1 involves no code.

To verify a timestamp: `pip install opentimestamps-client && ots verify paper/ovh-monotone-3ov.pdf.ots`.

## License

© 2026 Patryk Pilichowski. [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); see [`LICENSE`](LICENSE).
