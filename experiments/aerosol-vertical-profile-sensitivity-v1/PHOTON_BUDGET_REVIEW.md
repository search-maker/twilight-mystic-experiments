# Aerosol vertical-profile sensitivity v1 — pre-result photon-budget review

Status: **REVIEW ONLY — COMPLETED BEFORE SEED/ORDINAL ALLOCATION — NO SOLVER EXECUTION**

## Question

Is the preregistered `20,000,000` photon history budget per case appropriate for the new vertical-profile sensitivity screen, or should it be changed before any scientific identity/seeds are allocated?

## Relevant prior evidence

The new design deliberately reuses the same 24 analysis-cell geometry/AOD surface and the same 20M-per-case numerical budget used by AOPS ordinal 37 and AFPF ordinal 38.

### AOPS ordinal 37

At 20M photons per case:

- exact 360 cases completed;
- scalar preregistered rows: `648/648`, all `FINITE_THREE_REPLICATES`;
- Level-B preregistered rows: `216/216`, all `FINITE_THREE_REPLICATES`;
- spectral cell/contrast rows: `216/216`;
- spectral rows with unresolved wavelength nodes: `40/216`, all at Sun depression 8°;
- no epsilon substitution.

### AFPF ordinal 38

At 20M photons per case:

- exact 360 cases completed;
- scalar preregistered rows: `504/504`, all `FINITE_THREE_REPLICATES`;
- Level-B preregistered rows: `168/168`, all `FINITE_THREE_REPLICATES`;
- spectral rows with unresolved wavelength nodes: `24/168`;
- all unresolved spectral nodes were confined to Sun depression 8° cross-/opposite-solar cells;
- no epsilon substitution.

## Decision frozen before results

**Retain 20,000,000 photons per case.**

Rationale:

1. The primary endpoints of vertical-profile sensitivity v1 are the same scalar photopic/scotopic/Johnson-V channels that were fully finite over the identical prior design at 20M.
2. The secondary Level-B endpoint was likewise fully finite over the identical prior design at 20M.
3. The known numerical weakness is node-level full-spectrum resolution at the deepest 8° twilight, not the preregistered scalar/Level-B endpoints.
4. The new protocol already retains raw spectrum for audit but explicitly makes **no full-spectrum production interpolation claim** and requires unresolved nodes to remain visible rather than be epsilon-filled.
5. Raising the photon budget without endpoint evidence would add large compute cost and would constitute an unsupported numerical change rather than a targeted convergence action.

Therefore 20M is frozen for the initial 360-case screen.

## What this decision does not mean

- It does not guarantee every 8° wavelength node will be positive/resolved.
- It does not allow hiding unresolved nodes.
- It does not pre-authorize a high-photon rerun if a later contrast is noisy.
- It does not convert MC standard-deviation output into a calibrated between-seed uncertainty estimator.

If a required scalar/Level-B endpoint is `NUMERICALLY_UNRESOLVED`, that is a terminal result for this scientific identity. Any convergence study or higher-photon follow-up must be a separate preregistered identity and may not replace the original result silently.

## Exact software binding reviewed concurrently

The merged generic vertical-profile transport module used by the preregistration is current-main blob:

`af2d4d65371474c38791d79e2fcded696022d88d`

No code/runtime/seed/ordinal change is made by this review.
