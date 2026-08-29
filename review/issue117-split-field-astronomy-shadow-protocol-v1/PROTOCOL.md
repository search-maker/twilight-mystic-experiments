# Issue #117 — split-field astronomy shadow preregistration v1

Status: **REVIEW ONLY / PREREGISTERED BEFORE SHADOW OUTPUT / NO SEMANTIC CHANGE / NO PRODUCTION**

This protocol is the next gate after the independent source-reproduction package in PR #607. It freezes the first astronomical split-field *research shadow* before any output from that shadow is computed or inspected.

The purpose is narrow: make the broad adaptation-field history `B_a(t)` physically distinct from the local detection background `B_d(t)`, then determine whether the three mathematically surviving transient mappings remain structurally valid and meaningfully separable. It is **not** an observational fit and cannot select a model from Taylor/Jerusalem agreement.

## 1. Immutable upstream bindings

The implementation MUST bind these exact identities before any shadow output:

- source-reproduction parent: PR #607 head `83979360a21e3e9aa3a85a2dda0f4808ab821018`;
- spatial/dynamic evidence protocol: PR #583 head `f48cc9bd6407be3eb6ed8abcb1ac43dfd25fae59`;
- Candidate 2/3 mathematical implementation: PR #580 head `813e6746ee9e6986be800a9c6a7d6004aa5026a5`;
- Candidate 4 generalized-inverse implementation: PR #582 head `41dbb5202a5a10ccfffa64453b931c8da8037d4a`;
- application repository: `search-maker/starsvisibility`;
- application SHA: `e0da52eb0a2d5bac333da6572f51df52ea7e676e`;
- `scientific-tools/visibility-v3/human-threshold.mjs` blob `bb4cd0ff02159ecffe276022cec9d292c7a434a3`;
- `scientific-tools/visibility-v3/transient-adaptation.mjs` blob `fa57726073974aeab5d52721dfcf1f10b8bf8420`;
- `scientific-tools/visibility-v3/level-b-transient-contiguous-support.mjs` blob `1622f9ff8afb9c184833404ec173e69c32b73fa5`;
- `scientific-tools/visibility-v3/validated-v3-sky-provider.mjs` blob `da8c5995559020865118220d939e58d89e6b98e4`;
- frozen field factor `F=3.14` unchanged.

The validated Level-B provider at that application SHA exposes distinct `photopic` and `scotopic` channels but explicitly reports its `spectral` channel unavailable. This fact constrains the spectral arms below; no missing spectrum may be invented.

## 2. Factor separation — mandatory

Every shadow row MUST keep these quantities separate and named:

1. `B_d(t)`: local physical detection-background luminance at the target/star direction;
2. `B_a,instant(t)`: instantaneous adaptation-field luminance after a frozen spatial operator;
3. `B_a,lagged(t)`: temporal adaptation state propagated only from the corresponding `B_a,instant` history;
4. threshold mapping from `(B_a,instant, B_a,lagged, B_d)` to required point-source signal;
5. gaze/fixation geometry;
6. spectral weighting arm.

Crumey/Blackwell Eq.34 remains the frozen **steady-state local point-source detection threshold**. The shadow does not refit Eq.34, `F`, atmosphere, stellar transport, or sky radiance.

`B_d` is never spatially averaged. It remains the sky-provider value at the target direction. A surrounding adaptation field may change `B_a`; it must not silently replace the local detection background.

## 3. Phase SF-A only — frozen non-observational astronomy geometry ensemble

The first implementation is deliberately a controlled sky-geometry shadow, not a first-seeing event fit. It uses no Taylor/Jerusalem observation or residual and no protected holdout.

For each combination below, build one declining-twilight history over the Level-B domain:

- Sun-centre geometric depression: `2.0°` through `10.5°` inclusive in `0.25°` steps;
- target altitude: `{30°, 45°, 60°}`;
- target relative azimuth from the Sun: `{0°, 45°, 90°, 135°, 180°}`;
- observer elevation: `0 m`;
- AOD550: `{0.05, 0.15, 0.30}`;
- all other atmospheric inputs exactly as required by the bound Level-B provider; no value may be chosen from a transient-output or observation residual.

Target altitude and relative azimuth are held fixed within each SF-A history. These are intentionally controlled astronomical sky geometries, not claims about a realizable stellar track. Their purpose is to expose split-field semantics without target/date selection. Real sidereal tracks require a later separately frozen ledger after SF-A is complete.

All center directions were chosen upstream of output and lie far enough inside the Level-B 5°–80° target-altitude design box to permit a 20° spatial neighborhood in altitude without automatic design-box edge crossing. Individual neighbor samples must still pass the provider's actual support test.

## 4. Spatial adaptation-field arms

### S0 — point/same-field control

`B_a,instant = B_d`.

This is the current conceptual same-field control. It is not eligible as the preferred spatial field after its failure to reproduce Stokkermans E2, but it is required to verify same-field algebraic identities.

### S2 — source-compatible ALF primary spatial arm

Use the Stokkermans/Murdoch target-centred two-Gaussian sensitivity frozen before source reproduction:

`w(theta) = 0.9935 exp[-theta^2/(2*0.67^2)] + 0.0065 exp[-theta^2/(2*3.9^2)]`,

where `theta` is **great-circle angular separation in degrees** from the operator centre.

For astronomy, integrate physical sky luminance over a spherical cap of radius `20°`, using explicit solid-angle weights. Normalize the discrete weights to unit mass only after every required sky sample is known to be valid. The 20° numerical cap is fixed before output from the source kernel itself: in the corresponding planar radial Gaussian mixture, the omitted mass beyond 20° is approximately `3.53e-7`; it is a numerical truncation, not a fitted field radius.

A mandatory numerical convergence check repeats representative integrations with 16° and 20° caps. If the absolute relative change in `B_a,instant` exceeds `1e-3`, that row/history is `SPATIAL_INTEGRATION_NOT_CONVERGED` and is not interpreted. The 16° result may never replace the 20° result because it happens to improve another metric.

### S1 — whole-cap uniform-weight control

Uniform solid-angle average over the same valid 20° cap. This is a control corresponding to a simple local/area average, not a promoted physiological model.

### S3 — Uchida-local control

Uniform solid-angle average inside a target-centred `12.4°` radius, preserving the exact radius from the independently frozen Uchida–Ohno geometry. Its Stokkermans transfer failure remains preserved; this arm is a control, not a candidate promoted by the new shadow.

### Missing-scene / horizon rule

No spatial arm may zero-fill, extrapolate, mirror, or silently renormalize around missing sky samples. If any quadrature point required by its frozen footprint is outside the bound provider's validated support, cloud-unsupported, below the modeled sky domain, or otherwise unavailable, that arm/history is **refused**. This is especially important near a real horizon, where unmodeled terrestrial luminance could contribute to visual adaptation. A later real-track protocol must model the visible scene or restrict its geometry; it may not pretend missing ground is black sky.

## 5. Gaze / eccentricity arms

Alexander et al. (2021) independently places peak faint-star detection roughly in an `8°–14°` retinal-eccentricity band. It does not supply a natural eye-movement probability distribution and does not identify an adaptation-field radius.

SF-A therefore freezes:

- `G_TARGET`: S2/S1/S3 operator centred on the target direction; this is the primary source-compatible transfer because Stokkermans ALF was target-centred;
- `G_FIX_8`, `G_FIX_11`, `G_FIX_14`: research sensitivity controls with operator centre displaced from the target by exactly 8°, 11° or 14°;
- for every displaced arm, four deterministic fixation orientations relative to the target-to-Sun great-circle direction: `toward_sun`, `away_from_sun`, `cross_plus90`, `cross_minus90`.

The four directions form an **envelope only**. They are not averaged with an invented probability distribution, and no direction may be selected because it gives a preferred astronomy answer.

Crucially, this protocol introduces **no eccentricity correction to the Crumey steady-state point-source threshold**. Alexander constrains where faint-star detection can peak, but does not justify an immediate multiplicative correction to this project's threshold law. `B_d` therefore remains at the target point in all gaze arms; only the adaptation-field centre is varied in the fixation-centred controls.

## 6. Spectral weighting arms

The bound Level-B provider exposes both photopic and scotopic scalar sky channels from the same frozen physical sky model.

Execute these as separate sensitivity arms:

- `P_PHOTOPIC`: spatially integrate the provider's photopic `cd/m2` channel;
- `S_SCOTOPIC`: spatially integrate the provider's scotopic `scotopic-cd/m2` channel.

For both arms, the same first-order log-state mathematics may be applied only as a **spectral-weighting sensitivity diagnostic**. Using the same tau with the scotopic scalar is not to be described as a validated rod ODE.

`M_CIE_MESOPIC` is **not execution-eligible in SF-A v1**. The bound provider says spectral runtime is unavailable, and this repository state does not bind an exact normative CIE mesopic implementation. Do not manufacture a mesopic scalar by interpolating P/S or by using a convenient S:P formula. A later addendum may enable a mesopic arm only after its exact normative algorithm/tables and provenance are frozen before its outputs.

No separate rod/cone temporal states are authorized.

## 7. Temporal state arms

Use the current first-order log10 state equation without modification:

`da/dt = (log10(B_a,instant) - a) / tau`.

Run every eligible spatial/spectral history at all four preregistered sensitivity values:

`tau = {20, 30, 45, 60} s`.

No tau is primary, fitted, averaged, or selected from shadow output. The independent evidence establishes only order-of-magnitude plausibility for a one-state sensitivity study, not natural-twilight calibration.

Initialization/prehistory must be identical across mapping Candidates 2/3/4 for a given spatial/spectral/tau arm. If a corresponding prehistory cannot be constructed from the same split-field definition and supported sky samples, refuse the history rather than importing the old point-field prehistory as though it were equivalent.

If `B_a,lagged < B_a,instant` at any evaluated waning-twilight row, mark `NEGATIVE_ADAPTATION_DEBT_UNSUPPORTED` and do not clamp it to zero for the comparison. Positive-debt candidate definitions are not silently extended into a brightening-state rule.

## 8. Threshold-mapping candidates — exact frozen definitions

Candidate 1 / PR #116 endpoint floor is retained only as a historical diagnostic and is **not eligible for promotion**.

The surviving comparison set is exactly:

### C2 — path envelope

For local detection `B_d` and a direct debt endpoint `B_d + (B_a,lagged - B_a,instant)`, require the maximum frozen Eq.34 threshold over the path, including the certified local threshold maximum at `B=0.021567318651181808 cd/m2` if crossed. Use the exact PR #580 implementation semantics.

### C3 — adaptation-threshold ratio

Compute the path-envelope threshold over `B_a,instant -> B_a,lagged`, divide by the equilibrium threshold at `B_a,instant`, and multiply the local equilibrium threshold at `B_d` by that ratio. Use exact PR #580 semantics.

### C4 — threshold-derived equivalent background / generalized inverse

Compute the adaptation-field path-envelope threshold over `B_a,instant -> B_a,lagged`; invert the anchored monotone-envelope relation with the exact left generalized inverse frozen in PR #582; infer the non-negative equivalent-background amount relative to `B_a,instant`; add that amount to `B_d`; then evaluate the local anchored path-envelope threshold. Use exact PR #582 semantics and tolerances.

No candidate formula may be edited after SF-A output is seen. No candidate may receive candidate-specific `B_a`, tau, atmosphere, or gaze inputs.

## 9. Preregistered metrics

For every non-refused row, preserve the full provenance and report:

- `B_d`, `B_a,instant`, `B_a,lagged`, and positive adaptation debt;
- spatial arm, centre/gaze arm, orientation, spectral arm, tau, atmosphere and geometry identities;
- equilibrium local Eq.34 threshold;
- C2, C3 and C4 required illuminance thresholds;
- pairwise threshold ratios and pairwise magnitude-equivalent differences `2.5*log10(T_i/T_j)`;
- whether a candidate crosses the certified Eq.34 local maximum;
- same-field identity residuals in S0;
- counts of better-than-local-equilibrium violations;
- counts of stronger-debt monotonicity violations on frozen local synthetic perturbation checks around each state;
- per-history max absolute and median absolute pairwise candidate differences;
- per-history spatial/gaze/spectral/tau sensitivity envelopes;
- refusal counts and exact refusal reasons.

Numerical equality tolerance for identities is relative threshold error `1e-12`, matching the upstream mathematical gates. A pairwise magnitude difference may be reported as nonzero when it exceeds numerical propagation noise, but **no magnitude cutoff is a scientific acceptance or winner threshold** in SF-A.

## 10. Interpretation frozen before output

SF-A can produce only these conclusions:

1. `STRUCTURAL_FAIL_<candidate>` if a surviving candidate violates the preregistered no-better-than-equilibrium/debt-monotonicity invariants under valid split-field inputs;
2. `SPLIT_FIELD_SEPARABLE` if C2/C3/C4 produce reproducibly non-identical valid thresholds beyond numerical tolerance;
3. `SPLIT_FIELD_EFFECT_NUMERICALLY_NEGLIGIBLE_IN_THIS_GRID` if they remain numerically indistinguishable on the frozen grid;
4. `INSUFFICIENT_SUPPORTED_SPLIT_FIELD_COVERAGE` if refusal rules leave inadequate valid histories.

**SF-A cannot declare a psychophysical winner from the size or sign of the candidate differences.** Candidate 4 remains the primary historical-equivalent-background candidate by independent provenance only; Candidate 3 remains the threshold-ratio structural control and Candidate 2 the path-envelope control.

If all three survive structurally and are separable, the next scientific discriminator is independent split-field/dynamic human evidence or a separately preregistered physical stellar-track shadow. It is not Taylor/Jerusalem residual minimization.

## 11. Hard anti-fitting and production boundary

SF-A must not load, parse, copy, rank against, or use:

- Taylor first-seeing/SQM residuals or event times;
- Jerusalem first-seeing residuals or desired event times;
- any protected holdout value;
- any target answer chosen after seeing a shadow output.

It may not change `F`, Eq.34, atmosphere, stellar transmission, tau values, Gaussian widths/weights, gaze offsets, spectral channel definitions, or mapping formulas after outputs.

It adds no production route, does not modify `starsvisibility`, does not authorize MYSTIC/uvspec execution, does not authorize PR #116 merge, and does not replace the current fail-closed behavior.

`TRANSIENT_VISIBILITY_NEGATIVE_PENALTY` remains authoritative until a replacement survives the complete independent-evidence -> preregistered-shadow -> later validation chain.
