# Aerosol Production / Uncertainty v1 — review-only policy

Status: **REVIEW ONLY; NO ORDINAL 39; NO SOLVER; NO PRODUCTION CHANGE**

This package converts the verified AOPS v1 ordinal 37 and AFPF v1 ordinal 38 findings into a fail-closed decision policy for the next modeling stage. It does not treat those sensitivity experiments as a climatology and does not create a new scientific execution identity.

## Why this policy is needed

AOPS showed that AOD550 alone does not determine twilight aerosol optical behavior and that constant SSA/g endpoints are sensitivity controls rather than a realistic aerosol climatology. AFPF then showed that realistic wavelength-dependent aerosol families and the desert spheroid-vs-sphere phase-function contrast produce geometry-, Sun-depression-, AOD-, and channel-dependent effects. In particular, the preregistered `desert_spheroids_vs_desert` priority contrast changes sign across the 24-cell design surface.

Those findings rule out four tempting shortcuts:

1. no universal aerosol correction;
2. no universal particle-shape/phase-function factor;
3. no choosing one aerosol family from AOD alone;
4. no universal conversion of aerosol magnitude effects into clock minutes.

## Frozen production principle

When the real aerosol family/phase function is not independently validated, production should represent aerosol-model uncertainty as a **set-valued scenario envelope**, not as a probability-weighted average with invented weights.

The review candidate scenario support is the five-state AFPF universe:

- `native-rural-ss`;
- `opac-continental-average`;
- `opac-maritime-clean`;
- `opac-desert`;
- `opac-desert-spheroids`.

This list is an uncertainty/sensitivity support only. It is **not** a claim that these states are equally probable, exhaustive, or valid as location-specific climatological priors. The controlled constant-SSA/g AOPS states are not promoted into production aerosol families.

For a future production implementation, each prediction should preserve an explicit version-bound baseline and, when the aerosol state is unresolved, expose at least: scenario minimum and maximum, the state producing each extremum, the state set evaluated, and a domain/coverage status. A baseline must not be presented as the uniquely true aerosol state.

## Evidence tiers

### Tier 0 — AOD only

AOD without independently validated aerosol-family/phase-function evidence cannot select one family. The only currently defensible policy is a baseline plus an explicit scenario envelope over whatever scenario support is later validated for the production domain.

### Tier 1 — independent regime classification

A continental/maritime/desert-style restriction may be used only after the classifier itself, its mapping into model states, its domain, and its error behavior are independently validated and version-bound. The observed twilight residual may never be used post hoc to pick the family that fits best.

### Tier 2 — direct optical/microphysical constraints

More direct aerosol information may narrow the scenario support only through a separately reviewed forward mapping with retrieval uncertainty propagated. A single retrieved scalar `g` is not accepted as a complete replacement for wavelength-dependent phase-function information.

## What remains unresolved before production activation

This review intentionally leaves the following fail-closed:

- exact production AOD range;
- exact production Sun-depression range;
- exact viewing-geometry domain;
- the transport table/surrogate/evaluator used to obtain all scenario outputs cheaply;
- interpolation and extrapolation rules;
- any external aerosol-family classifier or probabilistic climatological prior;
- empirical twilight-radiance validation against real atmospheric observations;
- final `starsvisibility` integration.

Therefore this package does **not** authorize a production correction.

## Gate for ordinal 39

Ordinal 39 is not allocated here. The next scientific execution should be designed only after review of this policy, and should target the concrete missing production capability — most likely a preregistered production-domain aerosol scenario transport/interpolation validation — rather than automatically repeating AFPF v1.

## Immutable source bindings

- review parent main: `0ee03dd09ca732a6fefe635291880d33cd4a0a97`;
- AOPS ordinal 37 report Git blob: `c7a58d8d7ac0ee2a6f1acbf9368df09b881bbd66`;
- AFPF ordinal 38 report Git blob: `2aac443d60893832c1867657ecd50d9703782ac3`.

No scientific result files are modified by this review package.
