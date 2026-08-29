# Issue #117 — independent source reproduction v1

Status: **RESEARCH / SOURCE-REPRODUCTION ONLY / NO ASTRONOMY OUTPUT / NO SEMANTIC CHANGE**

Parent protocol: PR #583, exact parent head `f48cc9bd6407be3eb6ed8abcb1ac43dfd25fae59`.

Application model checked for the dynamic gate: `search-maker/starsvisibility` main `e0da52eb0a2d5bac333da6572f51df52ea7e676e`, `scientific-tools/visibility-v3/transient-adaptation.mjs` blob `fa57726073974aeab5d52721dfcf1f10b8bf8420`.

No Taylor/Jerusalem residual, event time, or desired astronomy answer is used anywhere in this package.

## SR-SPATIAL-1 — Stokkermans E2 ordering

Primary source: Stokkermans, Vogels & Heynderickx (2016), *The effect of spatial luminance distribution on dark adaptation*, Journal of Vision 16(8):11, DOI `10.1167/16.8.11`.

The source uses a 20° x 20° visible field, display black level `0.0065 cd/m^2`, and a target 4.3° left/right of center. Experiment E2 compares:

- `Bar9`: two full-width horizontal bars, 2° thick, ±9° from target, `42 cd/m^2`;
- `Bar2.7`: same geometry at ±2.7°, `5.1 cd/m^2`;
- `Square`: 2° x 2° centered square, 4.3° from target, `101 cd/m^2`.

The source reports equal calculated target veiling luminance of about `0.07 cd/m^2`; `Bar9` gave significantly shorter adaptation time than `Square` (`p<0.001`) and `Bar2.7` (`p=0.039`), while `Square` vs `Bar2.7` was not significant (`p=0.215`). The preregistered directional target is therefore only: both near-structure conditions must produce greater adaptation load than far `Bar9`.

### Numerical definition

`stokkermans-spatial-audit.mjs` integrates on the source angular field with an equal-angular midpoint grid, checking the qualitative classification independently at 0.02° and 0.04° resolution. The `S2_ALF` kernel is the frozen target-centred two-Gaussian control from the source:

`w(r)=0.9935 exp(-r^2/(2*0.67^2)) + 0.0065 exp(-r^2/(2*3.9^2))`,

normalized to unit discrete mass on the 20° x 20° source field so a uniform field is an exact luminance identity. The source target-veiling condition (`0.07 cd/m^2`) is reported separately and is **not** silently added to external physical luminance.

### Spatial result

Fine-grid external-physical adaptation loads (`cd/m^2`):

| arm | Bar9 | Bar2.7 | Square | source ordering? |
|---|---:|---:|---:|---|
| `S0_POINT` | 0.0065 | 0.0065 | 0.0065 | **FAIL / tie** |
| `S1_SOURCE_VISIBLE_AREA` | 8.4052 | 1.0252 | 1.0164 | **FAIL / reversed by global brightness** |
| `S2_ALF` | 0.2211 | 0.3325 | 0.4268 | **PASS** |
| `S3_UCHIDA_LOCAL` (unweighted 12.4° radius) | 7.1940 | 1.0995 | 1.2249 | **FAIL in this geometry** |

The pass/fail classification is identical at 0.04° resolution.

This is a meaningful independent narrowing: a target-centred distance-weighted local field of the Stokkermans/Murdoch type reproduces the frozen source ordering without parameter fitting; point-only, whole-field average, and a transplanted unweighted 12.4° circle do not. The `S3` failure **does not refute Uchida–Ohno in its own peripheral-task geometry**; it rejects treating that unweighted circle as a universal transferable operator for this different E2 geometry.

This result still does **not** prove that `S2_ALF` is the correct astronomy adaptation field. It promotes it only to the primary independently source-compatible spatial control for the later split-field shadow. Ocular glare remains a separate research factor.

Run:

`node review/issue117-source-reproduction-v1/stokkermans-spatial-audit.mjs`

## SR-DYNAMIC-1 — Spillmann waning-background ordering

Primary source: Spillmann, Nowlan & Bernholz (1972), *Dark adaptation in the presence of waning background luminances*, JOSA 62(2):177–181, DOI `10.1364/JOSA.62.000177`.

The source varies a spatially uniform adapting background continuously downward by 7 log10 units over 3.5, 7, 14, or 21 minutes and reports that transient sensitivity lags stationary sensitivity, with the lag depending on decline rate/history. These source durations were frozen in PR #583 before this audit.

### Exact state equation tested

The current project state is first-order in log10 luminance:

`da/dt = (x-a)/tau`, with `x=log10(B_a)`.

For a linear decline `x(t)=x0-r*t`, define `delta=a-x`. With initial lag `delta0`, the exact solution is:

`delta(t) = r*tau*(1-exp(-t/tau)) + delta0*exp(-t/tau)`.

The audit independently evaluates both this closed form and the exact interval formula used by current `transient-adaptation.mjs`, requiring agreement below `1e-12` log10 unit.

### Dynamic result

All frozen `tau = 20, 30, 45, 60 s` sensitivity arms reproduce the **source-level qualitative rate ordering without fitting**: 3.5 min leaves more lag than 7 min, which leaves more than 14 min, which leaves more than 21 min. Larger tau leaves more lag; stationary equilibrium is an exact identity; explicit positive initial lag survives exactly as `delta0*exp(-t/tau)`, so pre-exposure histories remain structurally distinct.

End-of-ramp state lag (`a-x`, log10 units):

| decline duration | tau 20 s | tau 30 s | tau 45 s | tau 60 s |
|---:|---:|---:|---:|---:|
| 3.5 min | 0.666648 | 0.999088 | 1.485895 | 1.939605 |
| 7 min | 0.333333 | 0.500000 | 0.749934 | 0.999088 |
| 14 min | 0.166667 | 0.250000 | 0.375000 | 0.500000 |
| 21 min | 0.111111 | 0.166667 | 0.250000 | 0.333333 |

These are state diagnostics, **not measured threshold deviations**. They are not used to fit tau or select a mapping.

Spillmann is spatially uniform, so `B_a=B_d`; consequently it cannot discriminate Candidates 2/3/4 under the preregistered same-field construction. It gates temporal-state direction/history and equivalent-background provenance only.

Run:

`node review/issue117-source-reproduction-v1/spillmann-log-ramp-audit.mjs`

## Combined conclusion / current boundary

Two independent prerequisites now pass at the qualitative source level:

1. **spatial:** `S2_ALF` reproduces the Stokkermans near-vs-far ordering without tuning, while the frozen control arms preserve their failures;
2. **temporal:** the current one-state log10 dynamics reproduce Spillmann rate/history direction without fitting tau.

This still does not select Candidate 2 vs 3 vs 4, validate a rod/cone temporal split, calibrate tau for natural twilight, or authorize production. PR #116 remains ineligible as a final physiological solution and `TRANSIENT_VISIBILITY_NEGATIVE_PENALTY` remains fail-closed.

The next permitted stage is **not Taylor/Jerusalem scoring**. It is to freeze the remaining split-field astronomy shadow inputs first: gaze/eccentricity arms, spectral adaptation controls, exact `B_a` spatial construction using the source-compatible arm plus preserved controls, tau sensitivity arms, Candidates 2/3/4, metrics, and refusal rules. Only after that separate preregistration may astronomy shadow outputs be opened.
