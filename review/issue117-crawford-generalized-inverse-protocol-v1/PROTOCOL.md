# Issue #117 Candidate 4 — Crawford-style generalized inverse protocol v1

Status: **REVIEW ONLY / NO EXECUTION / NO SEMANTIC CHANGE**

This document refines Candidate 4 that was already preregistered in twilight PR #578 before the real-trajectory output in PR #577 was opened. The refinement is constrained by the external equivalent-background literature and the already-frozen Eq.34 topology; it does not use Taylor/Jerusalem residuals or the numerical direction/magnitude of PR #577 to choose the mapping.

## Bound identities

- candidate-universe preregistration: twilight PR #578, head `23f96613d553610f9e75ddd4c8c08d0240c354c6`
- mathematical gate implementation: twilight PR #580, head `813e6746ee9e6986be800a9c6a7d6004aa5026a5`
- `starsvisibility` baseline: `e0da52eb0a2d5bac333da6572f51df52ea7e676e`
- `human-threshold.mjs` Git blob: `bb4cd0ff02159ecffe276022cec9d292c7a434a3`
- frozen Eq.34 topology diagnostic Git blob: `b8474a3afc4c9974208e39b0f1e7eec9a3396f3c`
- F remains `3.14`
- transient state ODE/tau remain unchanged experimental inputs for this candidate comparison

## Literature structure being preserved

Spillmann, Nowlan & Bernholz (1972, DOI `10.1364/JOSA.62.000177`) and Crawford-transform/equivalent-background usage do not define equivalent background as a direct photometric lag. The logical structure is:

1. obtain a threshold elevation/desensitisation under the adapted state;
2. use an inverse steady-state threshold-vs-background relation to find the background that would produce that threshold;
3. interpret the excess over the real background as an equivalent background;
4. combine that equivalent background with the real detection background.

The difficulty here is that the frozen Crumey Eq.34 threshold `T(B)` is not globally monotone in the mesopic transition, so a direct inverse of raw Eq.34 is multivalued/ambiguous. Candidate 4 therefore requires a separately specified monotone steady-state representation before inversion.

## Notation

- `T(B)`: frozen Crumey Eq.34 required point-source illuminance threshold at F=3.14.
- `B_a`: instantaneous broad adaptation-field luminance.
- `B_lag >= B_a`: lagged adaptation-state luminance returned by the unchanged experimental state model in a waning-background history.
- `B_d`: instantaneous local physical detection-background luminance.

For any anchor `a>0`, define the **anchored monotone path envelope**

`M_a(B) = max(T(x) : x in [a,B])`, for `B >= a`.

`M_a` is non-decreasing by construction and preserves the exact equilibrium threshold at the anchor: `M_a(a)=T(a)`.

Define its left/generalized inverse on its attained range:

`G_a(y) = inf { B >= a : M_a(B) >= y }`.

The inverse is defined only for finite `y >= M_a(a)` that is actually attained by the bounded candidate history. It must fail closed outside that range; no extrapolation is allowed.

## Candidate 4 mapping

### Step 1 — adaptation-field threshold state

`T_adapt = M_{B_a}(B_lag)`.

This is the same path-safe threshold-state idea already preregistered for Candidate 2, but applied to the **adaptation field** rather than the local detection field.

### Step 2 — threshold-derived total adaptation background

`B_total,a = G_{B_a}(T_adapt)`.

This is the Crawford-style inverse step. If `M_{B_a}` has a plateau, use the **leftmost** generalized inverse. This yields the minimum steady-state background excursion from `B_a` needed to explain the threshold elevation under the chosen monotone representation.

### Step 3 — equivalent background

`B_eq = max(0, B_total,a - B_a)`.

`B_eq` is therefore derived from threshold elevation, not identified directly with `B_lag-B_a`.

### Step 4 — local detection application

Apply the derived equivalent background to the physical local detection background using the same path-safe threshold representation:

`T4 = M_{B_d}(B_d + B_eq)`.

The physical `B_d` itself is never overwritten or relabelled as an adapted sky measurement.

## Important current-main identity

Current `level-b-transient-contiguous-support.mjs` populates `B_a` and `B_d` from the same photopic Level-B sky value. Under that current condition (`B_a = B_d`) and the definitions above:

- `T_adapt = M_{B_a}(B_lag)`;
- `G_{B_a}(T_adapt)` returns the leftmost point whose anchored envelope attains exactly that threshold state;
- applying the resulting `B_eq` through `M_{B_d}` reproduces the same `T_adapt`.

Therefore **Candidate 4 collapses exactly to Candidate 2 under the current same-field Level-B route** (up to numerical generalized-inverse tolerance). It cannot discriminate the present implementation from Candidate 2. Its value is structural/provenance: it becomes distinct only when `B_a` and `B_d` are genuinely different fields or when an independently validated threshold-state model replaces the provisional envelope.

This identity is a mathematical consequence of the candidate definitions and current same-field code path; it must not be interpreted as psychophysical validation.

## Frozen numerical implementation rules for a future shadow test

A future implementation may exploit the already-frozen Eq.34 stationary topology, but it must not approximate the envelope/inverse with a coarse arbitrary grid.

Required rules:

1. evaluate exact endpoints;
2. include all certified stationary points of `T(B)` inside the interval;
3. construct `M_a(B)` from those analytic/numerically certified extrema and the endpoint;
4. solve generalized-inverse crossings with a bracketed monotone root solver and a preregistered absolute/relative tolerance;
5. if a requested threshold lies on an envelope plateau, return the left boundary of that plateau;
6. fail closed if no finite bracket/crossing is available in the preregistered domain;
7. verify by forward substitution that `M_a(G_a(y))` matches `y` within the frozen threshold tolerance;
8. never use observational residuals to choose a branch/root/tolerance.

## Mathematical acceptance invariants

Candidate 4 must satisfy before any real event-time shadow comparison:

1. equilibrium identity when `B_lag=B_a`;
2. `B_eq >= 0`;
3. no beneficial debt: `T4 >= T(B_d)`;
4. debt monotonicity: increasing `B_lag` with fixed physical inputs cannot lower `T4`;
5. continuity except for mathematically unavoidable flat generalized-inverse plateaus, which must not cause a threshold discontinuity;
6. forward-inverse consistency;
7. exact Candidate-2 equivalence when `B_a=B_d`;
8. physical-sky separation and no-double-counting criterion remain intact.

## External-evidence boundary

The path envelope is a **mathematical monotonic regularization**, not a measured psychophysical steady-state curve. This protocol therefore does not claim that Candidate 4 is physiologically correct merely because its ordering mirrors a Crawford transform.

Before semantic selection, external evidence must still justify either:

- using a monotone regularization of Eq.34 for the inverse; or
- replacing the provisional threshold-state/envelope with a separately validated dynamic threshold model.

If independent evidence cannot discriminate Candidate 2/3/4 under the relevant seconds-to-minutes waning-twilight regime, retain the ambiguity/shadow alternatives rather than selecting from Taylor/Jerusalem fit.

## Hard boundary

This protocol adds no workflow, runs no solver, opens no AVPS artifact, changes no `starsvisibility` source, changes no F/tau/atmosphere, and authorizes no production routing or merge of PR #116.
