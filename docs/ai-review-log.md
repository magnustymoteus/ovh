# AI review log: main theorem

Three AI referee agents (Claude, the same model family that wrote the proof) each reviewed the proof of Theorem 1
of `paper/ovh-monotone-3ov.pdf`. Each started without the authoring context, was asked to find errors rather than
confirm, and covered one scope:

1. Lemma 7 (OR gate) and star plucking, conditions (A3)–(A4).
2. Definition 5, normalization, Lemma 6 and the final induction.
3. The distributions, Lemmas 3–4, every use of Lemma 4, and the parameter arithmetic.

Reviewer 1 also checked the use of CLSS Lemma 22 against the CLSS paper (arXiv:2607.23799).

**Verdict:** all three said "stands after minor fixes". None found a serious gap.

## Issues and fixes (all applied)

| issue | reviewers | fix |
|---|---|---|
| No rule for constant children (OR(0, F) read literally gives 1) | 1, 2, 3 | explicit rules for AND/OR with a constant child |
| Constant in Lemma 6 not justified by the written sum | 1, 2, 3 | step 4 drops only petals; total ≤ 20Mδ^t/n |
| Q_u computed before the step-4 drops | 2 | the drops only raise Q_u, so (A4) is preserved |
| Conjunct counts at OR gates only sketched | 2 | stated explicitly (hypothesis of Lemma 6) |
| N(leaf) = leaf not stated | 2, 3 | stated |
| "Dominates µ_{1/2}" justified incorrectly for pairs (not a product) | 3 | proved by an explicit coupling (Lemma 3(iii)) |
| Unstated side conditions on the parameters | 3 | all hold for large n, as the theorem assumes |
| Lemma 7 wording: "failing conjuncts ⊆ chosen triple"; "either other list" | 1 | applied |

## Limitation

All reviewers are AI agents from the same model family as the author model, so their blind spots may be correlated.
**The proof still needs review by a human expert in the approximation method.**
