# Issue #117 split-field astronomy shadow — preregistration Amendment 1

Status: **FROZEN BEFORE ANY SF-A SHADOW OUTPUT / CORRECTS SPECTRAL-UNIT SEMANTICS / NO RESULT OPENED**

This amendment is part of PR #610 and is frozen before any split-field astronomy shadow output is computed or inspected. It corrects one over-broad statement in `PROTOCOL.md` section 6.

## Why this amendment is necessary

The bound `starsvisibility` Level-B provider at application SHA `e0da52eb0a2d5bac333da6572f51df52ea7e676e` exposes:

- photopic sky luminance in `cd/m2`;
- scotopic sky luminance in `scotopic-cd/m2`;
- Johnson-V radiance;
- no spectral runtime channel.

The frozen Crumey/Blackwell `human-threshold.mjs` equilibrium relation and the exact Candidate 2/3/4 implementations are defined on the project's existing local **photopic-luminance** background coordinate. Candidate 3 and Candidate 4 explicitly evaluate that same equilibrium threshold relation at the adaptation-field state.

Therefore a scotopic luminance value cannot be inserted directly into Candidate 2/3/4 as though `1 scotopic-cd/m2 == 1 photopic-cd/m2`. That would mix different photometric weighting systems while pretending they share the same equilibrium-threshold coordinate, and would amount to inventing an unsourced receptor-to-threshold transform.

## Corrected SF-A spectral rule

For SF-A v1:

1. **`P_PHOTOPIC` is the only mapping-eligible adaptation-state coordinate.**
   - Build `B_a,instant`, `B_a,lagged` and `B_d` in the same existing photopic `cd/m2` coordinate.
   - Run Candidates 2/3/4 only on this coordinate.

2. **`S_SCOTOPIC_DESCRIPTOR` is diagnostic only.**
   - Spatially integrate the bound provider's scotopic channel using the same spatial/gaze geometry where supported.
   - Preserve instantaneous scotopic adaptation-field luminance and the local/field S:P information as descriptors of spectral scene change.
   - Do **not** pass the scotopic scalar through Eq.34, Candidate 2, Candidate 3 or Candidate 4.
   - Do **not** call a first-order scotopic state a validated rod state.

3. **`M_CIE_MESOPIC` remains unavailable in SF-A v1.**
   - It may become mapping-eligible only after an exact normative mesopic model or another independently justified receptor-to-threshold state mapping is preregistered and bound before output.
   - No ad hoc P/S interpolation, S:P coefficient, Purkinje correction or fitted conversion is allowed.

4. **No rod/cone ODE split is authorized.**
   - The scotopic descriptor may motivate a later receptor-specific experiment, but it cannot supply its missing dynamics or threshold semantics.

## Consequential wording override

Where `PROTOCOL.md` says that both P and S arms may have the same first-order log-state mathematics applied as spectral-weighting sensitivity diagnostics, this amendment narrows that statement:

- the candidate-mapping state in SF-A v1 is photopic only;
- scotopic values are instantaneous scene descriptors and S:P-context diagnostics only;
- no candidate ranking or threshold output may be generated from scotopic-coordinate substitution.

Where `PROTOCOL.md` requests a per-history `spectral/tau sensitivity envelope`, SF-A v1 instead reports:

- the candidate/tau envelope for the photopic mapping state;
- separate photopic/scotopic instantaneous field ratios and their spatial/gaze variation as descriptive provenance;
- no scotopic-derived candidate threshold.

## Boundary

This amendment changes no application code, source result, candidate formula, tau, `F`, atmosphere, stellar transport, or production behavior. It prevents an invalid unit/receptor substitution before execution.

`TRANSIENT_VISIBILITY_NEGATIVE_PENALTY` remains the authoritative fail-closed production guard.
