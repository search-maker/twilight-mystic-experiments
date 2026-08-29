# Issue #117 split-field SF-A — Amendment 5 / provider-support and quadrature gate

Status: **FROZEN BEFORE ANY SF-A SKY-LUMINANCE OR CANDIDATE-THRESHOLD OUTPUT / SUPPORT-ONLY PREFLIGHT COMPLETED**

This amendment binds the exact Level-B support rule and freezes the numerical quadrature-selection gate before any SF-A luminance, adaptation-state, or Candidate 2/3/4 output is opened.

## 1. Exact bound provider support

Bound application identity remains `search-maker/starsvisibility@e0da52eb0a2d5bac333da6572f51df52ea7e676e`.

Exact provider/runtime identities:

- `validated-v3-sky-provider.mjs` Git blob `da8c5995559020865118220d939e58d89e6b98e4`;
- `validated-v3-primary-runtime-v1.json` Git blob `5790ccb2c289de082a2851d96e4c3c660a1c4985`;
- runtime raw SHA-256 `6a927bd702ebbf1b1913ebe51731f3b92f967f2ae95edf090280b8370ea091e4`;
- `58` frozen support coordinates;
- exact support rule `PHYSICAL_DESIGN_BOX_AND_NEAREST_V1_IDW_COS_TRAINING_DISTANCE_LE_0.60`;
- maximum nearest frozen-training distance `0.60` in the provider's five-dimensional normalized coordinate.

No sky-radiance prediction is needed to evaluate this support predicate.

## 2. Local detection-background support preflight

Across the `45 × 35 = 1,575` frozen base geometry/time rows, the undisplaced local target direction `B_d` is provider-supported in `1,568` rows and unsupported in `7` rows.

The seven exact unsupported local rows are preserved in `SF_A_PROVIDER_SUPPORT_PREFLIGHT_RESULT_v1.json`. They are not rescued by adjusting AOD, geometry, time grid, or support radius.

Because `B_d` is mandatory for every mapping candidate, any spatial/gaze row sharing one of those base-time rows is refused regardless of adaptation-field support.

## 3. Support-only spatial audit at two resolutions

The existing 1° annular cap grid remains an **audit resolution**, not a luminance-convergence claim.

At that resolution, after exact `B_d`, design-box, and nearest-training-distance checks:

- `48,365 / 63,000` spatial/gaze rows are support-valid;
- `14,635` are refused;
- complete 35-row histories: `854 / 1,800`.

By spatial arm:

| arm | supported rows | refused rows | complete histories |
|---|---:|---:|---:|
| S0_POINT | 1,568 | 7 | 41 / 45 |
| S1_WHOLE_CAP | 14,552 | 5,923 | 229 / 585 |
| S2_ALF | 14,552 | 5,923 | 229 / 585 |
| S3_UCHIDA_LOCAL | 17,693 | 2,782 | 355 / 585 |

A second **support-only** audit refines the cap grid to 0.5°. It opens no luminance. S1 and S2 have identical footprint geometry, so they have identical support classification at a fixed quadrature.

At 0.5°:

- S1/S2: `14,487 / 20,475` rows support-valid; `222 / 585` complete histories;
- S3: `17,675 / 20,475` rows support-valid; `353 / 585` complete histories;
- S2 `G_TARGET`, the primary source-compatible spatial/gaze transfer, retains `20 / 45` complete histories at both 1° and 0.5° audit resolutions.

The 0.5° check therefore identifies a real nearest-support boundary effect beyond the nominal 5°–80° altitude footprint: 65 additional S1/S2 rows and 18 additional S3 rows are rejected relative to the 1° audit.

These are input/support facts only; no candidate behavior was inspected.

## 4. Frozen final luminance-quadrature refinement ladder

No full SF-A luminance execution may start until this numerical gate passes.

Use the same deterministic annular spherical-cap construction and exact ring solid-angle accounting already frozen by Amendment 2, with radial-step ladder:

- `Q0 = 1.0°`;
- `Q1 = 0.5°`;
- `Q2 = 0.25°`;
- `Q3 = 0.125°` only if required by the rule below.

The refinement set is selected only from support-complete histories and is fixed without using luminance values:

- every Q1-complete history for S1, S2 and S3;
- the five fixed Sun depressions `{2°,4°,6°,8°,10.5°}`;
- both instantaneous provider channels `photopic` and `scotopic` where supported;
- all frozen gaze arms represented by those complete histories.

S1 and S2 may reuse identical provider sample evaluations but must apply their own frozen spatial weights.

### Resolution acceptance

For each refinement-set integration and each channel, compute

`eps = abs(B_a,coarse - B_a,fine) / B_a,fine`.

- `Q1` is eligible as the full-grid luminance quadrature only if **every** `Q1 -> Q2` comparison has `eps <= 5e-4`.
- If any `Q1 -> Q2` comparison fails, Q1 is rejected globally; evaluate `Q2 -> Q3` on the same frozen refinement set.
- `Q2` is eligible only if every `Q2 -> Q3` comparison has `eps <= 5e-4`.
- If Q2 also fails, classify `SPATIAL_QUADRATURE_NOT_CONVERGED` and do not open the full SF-A candidate comparison. Do not invent a further refinement after seeing values.

The `Q0 -> Q1` comparison is diagnostic only and cannot rescue a failed finer gate.

### 16° / 20° ALF truncation gate

At the selected full-grid resolution, every frozen S2 refinement-set row must also be repeated at the preregistered `16°` and `20°` caps. Preserve the original protocol criterion:

`abs(B_a,16 - B_a,20) / B_a,20 <= 1e-3`.

A row failing this cap-truncation criterion is `SPATIAL_INTEGRATION_NOT_CONVERGED` and is not interpreted. The 16° value never replaces the 20° value.

## 5. Support must be re-evaluated at the selected final quadrature

A quadrature can be numerically converged yet unsupported. Therefore, after the resolution gate selects Q1 or Q2, rerun the exact provider-support predicate on **every required quadrature point** at that selected resolution before evaluating any sky luminance for the full shadow.

- If Q1 is selected, the 0.5° support-only ledger already supplies this support classification.
- If Q2 is selected, a fresh 0.25° support-only ledger must be frozen first.

No clipping, missing-point interpolation, edge shrinking, or partial-footprint renormalization is allowed.

## 6. Coverage-classification correction

The original protocol allowed `INSUFFICIENT_SUPPORTED_SPLIT_FIELD_COVERAGE` but did not freeze a numerical adequacy threshold before this support preflight. No post-support numerical threshold will now be invented.

Therefore SF-A v1 may:

- report exact support/refusal counts and conditional structural results on valid histories;
- declare a candidate structural failure if the frozen invariant fails on a valid row;
- report split-field separability conditional on the supported subset.

It may **not** turn the observed support fraction into a post-hoc claim of grid-wide representativeness or a coverage pass/fail threshold. A later protocol may define such an adequacy criterion only before inspecting its own support ledger.

## 7. Boundary

This amendment opens no Level-B luminance, no adaptation state, no Candidate 2/3/4 threshold, no Taylor/Jerusalem residual, and no protected holdout. It changes no `starsvisibility` application behavior and authorizes no production path.

PR #116 remains non-final and `TRANSIENT_VISIBILITY_NEGATIVE_PENALTY` remains fail-closed.
