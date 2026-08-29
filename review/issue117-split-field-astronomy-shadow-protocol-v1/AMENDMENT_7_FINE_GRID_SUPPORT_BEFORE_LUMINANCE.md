# Issue #117 split-field SF-A — Amendment 7 / fine-grid support before luminance

Status: **FROZEN BEFORE Q1/Q2 SKY-LUMINANCE OUTPUT / SUPPORT-SEMANTICS CLARIFICATION ONLY**

This amendment closes one implementation ambiguity in Amendment 5 before any Q1/Q2 photopic or scotopic luminance is evaluated. It does not inspect a candidate threshold, Taylor/Jerusalem, a protected holdout, or any SF-A luminance value.

## 1. Why this clarification is required

Amendment 5 freezes the refinement set from histories that are complete on the Q1 = 0.5° support grid and requires Q1→Q2 = 0.25° numerical comparisons. A finer quadrature can contain directions that the coarser grid did not sample. If one of those newly exposed directions is outside the exact bound Level-B support, there is no valid fine-grid integral against which the coarser integral can be certified.

A coarse grid therefore must not be declared numerically converged by silently dropping a Q2-unsupported row, clipping the footprint, renormalizing surviving points, or treating missing fine-grid support as a numerical-error value.

## 2. Frozen support-before-value order

For the already-frozen Amendment-5 refinement set:

1. Build the exact Q2 quadrature directions for every Q1-complete refinement row.
2. Apply the exact bound provider support predicate to **every required Q2 direction before evaluating either provider luminance channel**.
3. If every required Q2 direction is supported, and the mandatory local `B_d` row is supported, that row is `Q1_Q2_SUPPORT_COMPLETE` and becomes eligible for the already-frozen photopic/scotopic Q1→Q2 numerical comparison.
4. If any required Q2 direction is unsupported, that row is `REFINEMENT_FINE_GRID_SUPPORT_GAP`; preserve the first failing direction and exact support reason. Do not evaluate a luminance integral for that row merely because Q1 happened to miss the gap.

The refinement set is not narrowed after this check. A fine-grid support gap is not converted into a smaller post-hoc comparison set.

## 3. Resolution-selection consequence

Q1 = 0.5° can be selected as the full SF-A quadrature only if **both** conditions hold over the complete frozen refinement set:

- every row is `Q1_Q2_SUPPORT_COMPLETE`; and
- every already-frozen Q1→Q2 luminance comparison for both channels satisfies `eps <= 5e-4`.

If the support-completeness condition fails, classify the Q1 gate as `Q1_REJECTED_FINE_GRID_SUPPORT_GAP`. This is a support/refusal result, not `SPATIAL_QUADRATURE_NOT_CONVERGED`, and no candidate output may be opened from Q1.

Because a Q2-unsupported row cannot supply the Q2 integral required by the frozen ladder, SF-A v1 does **not** delete that row and continue to a result-dependent subset. Instead the refinement gate stops with `REFINEMENT_SET_FINE_GRID_SUPPORT_INCOMPLETE`. A later protocol may define a different coverage ledger only before inspecting its own outputs.

If Q1 is support-complete but fails the numerical `5e-4` criterion, proceed exactly as Amendment 5 requires: perform a support-only Q3 = 0.125° precheck on the same frozen refinement rows before any Q2→Q3 luminance evaluation. Any Q3 support gap analogously stops the ladder as `REFINEMENT_SET_Q3_SUPPORT_INCOMPLETE`; only an all-supported Q3 set may be used to test Q2 numerically.

## 4. Channel and refusal semantics

Provider support is geometric/runtime support and is evaluated once per direction; photopic and scotopic values are not consulted to decide support. After support passes, both channels must still be finite and positive for a numerical comparison. A channel failure is preserved as a channel-level refusal and cannot be substituted from the other channel.

No zero fill, interpolation, mirroring, clipping, footprint shrinking, partial renormalization, result-dependent history removal, or tolerance change is allowed.

## 5. Boundary

This amendment changes no scientific model, candidate formula, `F`, tau, atmosphere, gaze arm, support radius, quadrature tolerance, or production behavior. It only makes the missing-scene rule logically consistent with the preregistered fine-grid convergence gate before values are opened.

PR #116 remains non-final. `TRANSIENT_VISIBILITY_NEGATIVE_PENALTY` remains the authoritative fail-closed production guard.
