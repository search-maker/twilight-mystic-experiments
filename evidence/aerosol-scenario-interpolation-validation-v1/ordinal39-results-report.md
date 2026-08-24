# ASIV v1 ordinal 39 — verified results report

Status: **PASS — FROZEN SCALAR + LEVEL-B HOLDOUT GATES; REPORT-ONLY EVIDENCE**

This report records the already completed Aerosol Scenario Interpolation Validation v1 holdout experiment. It does not allocate a scientific identity, execute MYSTIC, rerun/retry/resume any scientific job, change the preregistration, retune the selected model after holdout opening, authorize full-spectrum interpolation, or authorize production/starsvisibility mutation.

## Immutable execution identity

- Scientific ordinal: `39`.
- Scientific workflow run: `32748300014`, attempt `1`, terminal `SUCCESS`.
- Authorization/dispatch head: `29c5d23e8aaed535a72202407136737b289c4572`.
- Parent/live main at authorization and execution: `12aa58584f6b07e26f5ac2a4ac3312c28479407a`.
- Authorization PR: `#350`, retained Draft/open/unmerged as the historical authorization identity.
- Case universe: `120/120` cases = `8` fresh holdout geometries × `3` CRN replicates × `5` aerosol states.
- CRN groups: `24`.
- Photon histories: `20,000,000` per case; `2,400,000,000` configured histories total.
- GitHub rerun: `false`.
- Retry: `false`.
- Resume: `false`.
- Post-result retuning: `false`.
- Final analysis artifact ID: `9530075455`.
- GitHub artifact SHA-256: `6ab0002a0285406d5e7cec7337a2879a4593af3e00c023bb66d1782e8a15b0b1`.
- Independently downloaded analysis ZIP SHA-256: `6ab0002a0285406d5e7cec7337a2879a4593af3e00c023bb66d1782e8a15b0b1` — exact match.

Issue #60 terminal marker:

`ASIV-V1-SCIENCE-COMPLETED ordinal=39 run=32748300014 attempt=1 cases=120 groups=24 holdouts=8 scalar_status=PASS_FROZEN_SCALAR_GATES levelb_status=PASS_FROZEN_LEVEL_B_GATES spectral_unresolved_nodes=26634 artifact_id=9530075455 artifact_digest=sha256:6ab0002a0285406d5e7cec7337a2879a4593af3e00c023bb66d1782e8a15b0b1 full_spectrum_pass_claim=false production=false starsvisibility_mutation=false rerun=false retry=false resume=false`

## Frozen model identity

The holdout evaluated the exact training-only selected model frozen before ordinal-39 result opening:

- model: `IDW_COS_4D-k8-p2`;
- family: four-coordinate inverse-distance weighting using Sun depression, target altitude, cosine-relative-azimuth, and AOD;
- neighbors: `8`;
- power: `2`;
- selected-model canonical SHA-256: `0b11a1691bfd2d9e3f073c786044bacedd3e9210bcb0660c76f21c34128a61af`;
- selection source: ordinal-38 AFPF training surface only;
- observer elevation was deliberately not fit, so ordinal 39 directly tests the frozen zero-order elevation-invariance hypothesis on fresh elevated holdouts.

No ordinal-39 holdout value influenced model selection, hyperparameter choice, or the frozen pass/fail thresholds.

## Frozen scalar result — PASS

Status: `PASS_FROZEN_SCALAR_GATES`.

The primary target is the 12 scalar aerosol-vs-native log-contrast fields: four OPAC states relative to native aerosol × three integrated channels (photopic, scotopic, Johnson V). All `96/96` required three-replicate state-vs-native channel rows were finite.

| Frozen scalar criterion | Frozen gate | Ordinal-39 result | Pass |
| --- | ---: | ---: | :---: |
| Aggregate mean absolute log-contrast error | `<= 0.15` | `0.0894573` | yes |
| Median absolute log-contrast error | `<= 0.12` | `0.0632045` | yes |
| P90 absolute log-contrast error | `<= 0.30` | `0.2165602` | yes |
| Worst absolute log-contrast error | `<= 0.50` | `0.2899242` | yes |
| Max over 12 fields absolute mean signed bias | `<= 0.10` | `0.0776673` | yes |
| Mean-error improvement vs nearest ordinal-38 cell | `>= 5%` | `30.706%` | yes |
| Mean-error improvement vs zero-contrast baseline | `>= 10%` | `61.910%` | yes |
| Scenario-envelope endpoint mean absolute log error | `<= 0.15` | `0.0935220` | yes |
| Scenario-envelope endpoint worst absolute log error | `<= 0.45` | `0.2658769` | yes |
| All predictions finite | required | `true` | yes |

Baselines:

- nearest-cell MAE: `0.1290979`;
- zero-contrast MAE: `0.2348581`.

Thus the frozen interpolator materially outperformed both preregistered baselines on the fresh holdout set.

### Elevated-observer test

Each of the four observer-elevation aggregates also passed the preregistered `<= 0.20` scalar-MAE gate:

- `312.5 m`: `0.0924716`;
- `937.5 m`: `0.1448310`;
- `1562.5 m`: `0.0761163`;
- `2187.5 m`: `0.0444101`.

This supports the frozen zero-order elevation-invariance treatment for aerosol log-contrast transport on these eight preregistered fresh geometries. It is not a claim of universal elevation invariance outside this validated holdout/domain.

### Per-holdout scalar behavior

The eight holdout mean absolute log-contrast errors were:

- holdout 01: `0.0294567`;
- holdout 02: `0.0696555`;
- holdout 03: `0.0191647`;
- holdout 04: `0.0532472`;
- holdout 05: `0.1316960`;
- holdout 06: `0.0645521`;
- holdout 07: `0.2251100`;
- holdout 08: `0.1227759`.

Holdout 07 is the hardest scalar geometry, with per-holdout mean error `0.2251100` and worst field error `0.2899242`, but the preregistered gates are aggregate plus elevation-aggregate and global worst-error gates; all of those passed without post-result modification.

## Derived Level-B result — PASS

Status: `PASS_FROZEN_LEVEL_B_GATES`.

The Level-B calculation was not separately fit. It propagated the frozen predicted photopic aerosol contrast through the exact byte-bound human-threshold implementation (`Crumey 2014 eq.34 full branch`, Git blob `bb4cd0ff02159ecffe276022cec9d292c7a434a3`) and compared the resulting predicted state-minus-native limiting-V deltas against direct-MYSTIC state-minus-native deltas.

| Frozen Level-B criterion | Frozen gate | Ordinal-39 result | Pass |
| --- | ---: | ---: | :---: |
| Mean absolute delta error | `<= 0.12 mag` | `0.0363480 mag` | yes |
| Median absolute delta error | `<= 0.10 mag` | `0.0313165 mag` | yes |
| Worst absolute delta error | `<= 0.35 mag` | `0.1483814 mag` | yes |

All `32` holdout/state Level-B rows were evaluated. The worst row was holdout 05, `maritime_vs_native`, with absolute mean delta error `0.1483814 mag`, still well inside the frozen `0.35 mag` maximum.

No universal Sun-depression-to-clock-minute conversion is authorized by this result.

## Required spectral diagnostic — no spectral PASS claim

Status: `COMPLETED_REQUIRED_DIAGNOSTIC_NO_SPECTRAL_PASS_CLAIM`.

The protocol explicitly made full-spectrum interpolation diagnostic rather than a primary pass gate and prohibited epsilon substitution. That boundary matters here:

- total unresolved spectral nodes: `26,634`;
- holdouts 01–06: `0` unresolved nodes;
- holdout 07: `421` unresolved nodes;
- holdout 08: `26,213` unresolved nodes;
- holdouts 07 and 08 both have Sun depression `9.4375°`;
- epsilon substitution performed: `false`.

By aerosol state, unresolved-node totals were:

- continental-average: `6,467`;
- maritime-clean: `6,153`;
- desert: `7,107`;
- desert-spheroids: `6,907`.

Therefore ordinal 39 does **not** validate full-spectrum aerosol interpolation at all wavelength nodes, especially at the deepest tested `9.4375°` Sun depression. The scalar and Level-B PASS must not be reworded as a full-spectrum PASS.

## Scientific interpretation

Within the exact ASIV v1 holdout contract, the training-only `IDW_COS_4D-k8-p2` model successfully transported aerosol-vs-native effects from the ordinal-38 24-cell AFPF surface to eight fresh, structurally disjoint, off-lattice geometries that all used nonzero observer elevation and Sun/AOD values outside the ordinal-38 direct lattice.

The result supports two downstream uses inside the validated computational support:

1. interpolation of the three integrated scalar aerosol-contrast channels under the frozen ASIV coordinate/model definition;
2. propagation of the photopic contrast into the separately bound Level-B limiting-magnitude calculation.

The result does **not** establish:

- full-spectrum interpolation validity;
- aerosol-family climatological probabilities or priors;
- real-sky absolute radiance accuracy;
- empirical naked-eye first-seeing accuracy;
- one universal aerosol correction;
- one universal magnitude-to-clock-minute correction;
- unrestricted extrapolation outside the already frozen Level-B/domain support;
- automatic production deployment or starsvisibility mutation.

## Governance consequence

Ordinal 39 is scientifically terminal and consumed. Its authorization PR `#350` remains an immutable historical Draft/open/unmerged identity and must not be amended, merged, rerun, retried, or reused.

The correct next stage is a separately reviewed **production-integration contract** that encodes the already frozen domain/refusal rules and the now-validated scalar/Level-B interpolator while preserving explicit refusal or coverage-gap behavior outside authorized support. Such an integration package must remain solver-free and must not reinterpret ordinal-39 outcomes as permission for spectral interpolation, climatological weighting, empirical first-seeing validation, or universal clock-minute conversion.

This file is a provenance/reporting addition only. It changes no scientific result, seed, model parameter, threshold, authorization, solver output, production policy, or starsvisibility code.
