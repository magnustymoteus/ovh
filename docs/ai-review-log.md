# AI review log

## Three lists (Theorem 1 of version 1 = Theorem 2 of version 2)

Three AI referee agents (Claude, the same model family that wrote the proof) each reviewed the proof of Theorem 1
of `paper/ovh-monotone-3ov.pdf`. Each started without the authoring context, was asked to find errors rather than
confirm, and covered one scope:

1. Lemma 7 (OR gate) and star plucking, conditions (A3)–(A4).
2. Definition 5, normalization, Lemma 6 and the final induction.
3. The distributions, Lemmas 3–4, every use of Lemma 4, and the parameter arithmetic.

Reviewer 1 also checked the use of CLSS Lemma 22 against the CLSS paper (arXiv:2607.23799).

**Verdict:** all three said "stands after minor fixes". None found a serious gap.

### Issues and fixes (all applied)

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

### Limitation

All reviewers are AI agents from the same model family as the author model, so their blind spots may be correlated.
**The proof still needs review by a human expert in the approximation method.**

## Every fixed k (Theorem 1 of version 2)

Three new AI referee agents, under the same setup, each covered one scope of the general-k proof:

1. Frames, normalization (deepest-first stages, switch-offs, enforcement, drops), invariant (I), Lemma 11.
2. Lemma 13 (OR gate): the excluded events, the minimal pair, the chains, the reveal order, the union over shapes.
3. Global structure: Lemmas 8 and 4, the induction, size bounds, parameters, and the relation to CLSS.

**Verdict:** all three said "stands after minor fixes". None found a gap in the argument.

**Brute-force checks by the referees:**
- Lemma 8 with exact fractions for k ≤ 8;
- the reveal order and charged-element counts in Lemma 13 for k ≤ 6;
- the parameter arithmetic for k ≤ 7.

### Issues and fixes (all applied)

| issue | reviewers | fix |
|---|---|---|
| Size constant A_k too small for k ≥ 5 | 1, 3 | A_k := 2k²·2^k |
| Number of shapes in Lemma 13 undercounted (true: 36, 792, 23640, 951120 for k = 3..6) | 2, 3 | bound (e·k!)² |
| Confining sets must be small on every sample, not only on the event | 2 | S := H if Q = 1, else ∅ |
| 1-slot sides have no assigned core | 2, 3 | the vector itself, which lies in T, is the core; empty chain |
| Parameter t failed δ^t ≤ n^{−(k+1)} at k = 2 (author self-check); ε_1 exponent wrong at k = 2 | 1, 3 | t := ⌈16(k+1)²/ε⌉; exponent min(ε/16, ε/(8(k−1))) |
| Frames created by new slots with another core; re-created dropped slots | 1 | frames defined per stage; stated |
| Normal form (ANDs before ORs on each slot) used implicitly | 1, 3 | Lemma 10 |
| Union over (stage, frame) events implicit in Lemma 11 and (x2) | 1, 2 | stated |
| Saturation of switched conjuncts, definition of failing pairs | 2, 3 | stated |
| Lemma 8 proof: "equality at both endpoints" false for m ≥ 2 | 3 | convexity argument |
| Corollary quantifier: fixed c does not give n^{k−o(1)} | 3 | "for every ε there is c"; n^{k−o(1)} for d = ω(log n) |
| **Version 1 misdescribed CLSS** ("k ≥ 3 only at d = n^{Ω(1)}", "a case they leave open"); their Cor 13 reaches d = n^{o(1)} for infinitely many n | 3 | corrected in version 2, checked against the CLSS text |
| **Version 1's unbalanced-OV corollary is probably not new** (the direct two-list argument likely gives it) | 3 | withdrawn in version 2 |

### Limitation

As above, all reviewers come from the author model's family. **Version 2 still needs human expert review**, especially
of the reveal order in Lemma 13 and invariant (I), and a check of the literature after July 2026.

## One further AI read of version 2 (Claude Opus 5.5, maximum effort)

A single further reviewer read Sections 2–3 line by line and found **no gap** in Theorems 1 and 2. It reran
Lemma 8 (exact coupling LP, k ≤ 8), the parameters (k ≤ 10), the shape count, r(1) = r(2) = 2 and the k = 2
fractional cover. It asked for exposition fixes, which are applied in the version-2 text:

| issue | fix |
|---|---|
| k = 3 normalization did not say that B_{u} is created when absent or dropped | stated in step 3 |
| The reveal order in the OR-gate lemma was prose | Lemma 12 (sequential confinement), and E ∖ 𝒳 ⊆ ∪ E_σ stated |
| "Fixed rule" and "canonical" choices not specified | greedy in a fixed order, cores in the lowest-numbered list; a Determinism paragraph |
| Lemma 11 mixed "switched" (fixed) with firing at the sample | "no indicator on J fires at the chosen values" |
| Missing basics: "for all large n" in the abstract, the circuit model, an undefined leaf index | added |
| Notation clashes (C, c, t, s, and Section 4 symbols) | circuit Φ with size \|Φ\|, h-conjuncts B′, contents γ_i, core map core(J), constants Λ_k, confining sets R, coordinate j; Section 4 has its own notation |
| Theorem 14 assumed #q-SAT for all q "as claimed" | restated for decision; (H) is ¬ETH via sparsification [IPZ01]; unproved remarks after it removed |
| The deformation "Proposition" has undefined terms | demoted to a heuristic (§4.2) |
| r(5) ≤ 5 and the 0/1 searches not attributed to Williams | attributed; explicit certificates for r(1..5) upper bounds added, with an independent checker |
| "After the refutation of ETH" treats preprints as settled | "claimed" throughout |
| Missing related work | Lin, arXiv:2608.08578 (non-monotone AC⁰, n^{Ω(k)}), checked on arXiv |
| [Raz85] cited for the monotone/general gap | the logical-permanent paper [Raz85b] cited instead |
| Brute-force checks had no scripts in `code/` | `code/general_k_checks.py`, `code/verify_certificates.py` |

This reviewer is the same model family again, so its agreement is correlated evidence, not independent verification.
