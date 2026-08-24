# ASIV v1 ordinal 39 — verified results report

Status: **PASS — FROZEN SCALAR + LEVEL-B HOLDOUT GATES; REPORT-ONLY EVIDENCE; NO PRODUCTION AUTHORIZATION**

This report records the completed Aerosol Scenario Interpolation Validation v1 (ASIV v1) scientific holdout experiment. It does not allocate another scientific identity, execute MYSTIC, rerun/retry/resume any scientific job, retune the selected interpolation model, change any frozen gate, authorize full-spectrum interpolation, or authorize a production/starsvisibility mutation.

## Immutable execution chain

- Scientific ordinal: `39`.
- Frozen parent/live-main identity at authorization and execution: `12aa58584f6b07e26f5ac2a4ac3312c28479407a`.
- Authorization/dispatch head: `29c5d23e8aaed535a72202407136737b289c4572`.
- Authorization PR: `#350`; preserved Draft/open/unmerged after science completion.
- Scientific workflow run: `32748300014`, attempt `1`, completed `SUCCESS`.
- Verified scientific cardinalities: `8` fresh holdouts × `3` CRN replicates × `5` aerosol states = `120` cases in `24` CRN groups.
- Configured histories: `20,000,000` photons/case = `2,400,000,000` configured histories.
- GitHub rerun: **none**.
- Retry: **none**.
- Resume: **none**.
- Post-result retuning: **none**.
- Final analysis artifact ID: `9530075455`.
- Final analysis artifact GitHub SHA-256: `6ab0002a0285406d5e7cec7337a2879a4593af3e00c023bb66d1782e8a15b0b1`.
- Independently downloaded analysis ZIP SHA-256: `6ab0002a0285406d5e7cec7337a2879a4593af3e00c023bb66d1782e8a15b0b1` — exact match.
- Terminal result status: `PASS_FROZEN_ASIV_SCALAR_AND_LEVEL_B_GATES`.

Issue #60 terminal marker:

`ASIV-V1-SCIENCE-COMPLETED ordinal=39 run=32748300014 attempt=1 cases=120 groups=24 holdouts=8 scalar_status=PASS_FROZEN_SCALAR_GATES levelb_status=PASS_FROZEN_LEVEL_B_GATES spectral_unresolved_nodes=26634 artifact_id=9530075455 artifact_digest=sha256:6ab0002a0285406d5e7cec7337a2879a4593af3e00c023bb66d1782e8a15b0b1 full_spectrum_pass_claim=false production=false starsvisibility_mutation=false rerun=false retry=false resume=false`

## Frozen selected model

The holdout was evaluated with the model selected before any ordinal-39 result opening:

- candidate: `IDW_COS_4D-k8-p2`;
- family: inverse-distance weighting in the frozen four-dimensional `(sun depression, altitude, cos relative azimuth, AOD)` coordinate system;
- neighbors: `8`;
- power: `2`;
- selected-model canonical SHA-256: `0b11a1691bfd2d9e3f073c786044bacedd3e9210bcb0660c76f21c34128a61af`;
- training-only selection run: `32688714382`, attempt 1;
- training-only selection artifact: `9506522699`, SHA-256 `39feb85806f821adbf57228335928a5e0cc65f6a1f50f0120d2e630473d553e7`;
- eligible candidates at frozen selection: `16`.

No ordinal-39 holdout value influenced model selection, model complexity, thresholds, or the definition of done.

## Fresh holdout surface

The eight holdouts were geometry-only selected and structurally off the ordinal-38 AFPF lattice. All were above 0 m observer elevation, all used AOD values outside ordinal-38 `{0.10, 0.30}`, and all used Sun-depression values outside ordinal-38 `{2°, 4°, 6°, 8°}`.

The four tested elevation levels were `312.5`, `937.5`, `1562.5`, and `2187.5 m`, each represented by two holdouts. The four tested Sun-depression levels were `3.0625°`, `5.1875°`, `7.3125°`, and `9.4375°`, each represented by two holdouts.

## Frozen scalar holdout gates — PASS

All scalar gates frozen before holdout opening passed.

| Gate | Frozen limit | Observed | Result |
| --- | ---: | ---: | --- |
| Aggregate mean absolute log-contrast error | `≤ 0.15` | `0.0894573` | PASS |
| Median absolute log-contrast error | `≤ 0.12` | `0.0632045` | PASS |
| P90 absolute log-contrast error | `≤ 0.30` | `0.2165602` | PASS |
| Worst absolute log-contrast error | `≤ 0.50` | `0.2899242` | PASS |
| Max absolute mean signed bias across 12 fields | `≤ 0.10` | `0.0776673` | PASS |
| Mean-error improvement vs nearest ordinal-38 cell | `≥ 5%` | `30.7059%` | PASS |
| Mean-error improvement vs zero contrast | `≥ 10%` | `61.9101%` | PASS |
| Scenario-envelope endpoint mean absolute log error | `≤ 0.15` | `0.0935220` | PASS |
| Scenario-envelope endpoint worst absolute log error | `≤ 0.45` | `0.2658769` | PASS |
| Required finite three-replicate state-vs-native channel rows | `96` | all required predictions finite | PASS |

The nearest-cell baseline MAE was `0.1290979`; the zero-contrast baseline MAE was `0.2348581`.

### Elevation-stratified scalar gate

Every frozen elevation-level aggregate was required to have mean absolute log-contrast error `≤ 0.20`:

- `312.5 m`: `0.0924716` — PASS;
- `937.5 m`: `0.1448310` — PASS;
- `1562.5 m`: `0.0761163` — PASS;
- `2187.5 m`: `0.0444101` — PASS.

Thus the preregistered zero-order elevation-invariance hypothesis for aerosol log-contrast survived this exact elevated holdout set under the frozen scalar gates. This is a validation only on these tested geometries and elevations, not a universal proof of elevation independence.

### Per-holdout diagnostic

The highest holdout mean scalar error occurred at `asiv-holdout-07`: mean `0.2251100`, worst field `0.2899242`. This does not violate the preregistered definition of done because the frozen per-elevation aggregate and global gates, rather than a per-holdout-mean cap, are controlling.

## Derived Level-B holdout gates — PASS

Level-B was not separately fit. The frozen prediction propagated the predicted **photopic** aerosol-vs-native log contrast through the exact byte-bound human-threshold implementation and compared predicted state-minus-native limiting-V-magnitude deltas against direct-MYSTIC deltas.

Bound human-threshold identity:

- model: `Crumey 2014 eq.34 full branch`;
- field factor: `2.4`;
- human-threshold Git blob: `bb4cd0ff02159ecffe276022cec9d292c7a434a3`.

All three frozen Level-B gates passed across `32` holdout/state rows:

| Gate | Frozen limit | Observed | Result |
| --- | ---: | ---: | --- |
| Mean absolute delta error | `≤ 0.12 mag` | `0.0363480 mag` | PASS |
| Median absolute delta error | `≤ 0.10 mag` | `0.0313165 mag` | PASS |
| Worst absolute delta error | `≤ 0.35 mag` | `0.1483814 mag` | PASS |

No epsilon substitution was used. No universal clock-minute conversion is authorized by this experiment.

## Required spectral diagnostic — NO FULL-SPECTRUM PASS CLAIM

The spectral diagnostic completed as required, but ASIV v1 explicitly did **not** preregister a full-spectrum interpolation pass gate. The correct status is therefore:

`COMPLETED_REQUIRED_DIAGNOSTIC_NO_SPECTRAL_PASS_CLAIM`

- Spectral contrast-replicate rows: `96`.
- Rows containing one or more unresolved wavelength nodes: `24/96`.
- Total unresolved wavelength nodes: `26,634`.
- Holdouts `01` through `06`: `0` unresolved nodes.
- `asiv-holdout-07` (`Sun depression 9.4375°`): `421` unresolved nodes.
- `asiv-holdout-08` (`Sun depression 9.4375°`): `26,213` unresolved nodes.
- Epsilon substitution: **none**.
- Full-spectrum interpolation pass claim: **false**.

The concentration of unresolved nodes at the deepest fresh Sun-depression level is an explicit numerical/scientific boundary. It must not be hidden by scalar or Level-B success.

## Scientific finding

On eight fresh, unopened, off-lattice holdout geometries with elevated observers and off-lattice AOD values, the training-only frozen `IDW_COS_4D-k8-p2` model successfully transported the four OPAC-family-vs-native aerosol contrast fields according to every preregistered **integrated scalar** and **derived Level-B** acceptance gate.

The scalar result is materially better than both preregistered non-eligible baselines: approximately `30.7%` lower mean absolute error than nearest-cell transport and `61.9%` lower mean absolute error than assuming zero aerosol contrast.

The derived Level-B error was substantially inside all frozen thresholds, with mean error about `0.0363 mag` and worst row about `0.1484 mag`.

This supports using the frozen interpolator as a validated transport mechanism for the exact scalar integrated channels and derived Level-B aerosol-contrast calculation **within the experiment's stated support and governance boundary**.

## Scientific and production boundary

A PASS here validates only the scope preregistered for ASIV v1:

- scalar integrated photopic, scotopic, and Johnson-V aerosol-vs-native contrast transport;
- the derived Level-B limiting-magnitude aerosol-contrast transport using the exact bound human-threshold model;
- the exact fresh holdout surface and the stated Level-B-supported geometry domain.

It does **not** validate:

- full-spectrum aerosol interpolation;
- aerosol-family climatological probabilities or weights;
- a universal aerosol family or universal correction;
- real-sky radiance accuracy against field observations;
- human first-seeing time as an empirical fact;
- a universal Sun-depression-to-clock-minute conversion;
- unrestricted extrapolation outside the declared production-domain contract;
- production deployment or mutation of `starsvisibility`.

`productionAuthorized=false` and `starsvisibilityMutationAuthorized=false` remain controlling.

## Next governance step

The next step is not another scientific rerun and not immediate production mutation. The validated ordinal-39 result should first be preserved as report-only evidence on `main` after ordinary exact-head non-scientific CI. Any production integration must be a separate reviewed change that preserves the existing domain contract, explicit aerosol scenario-envelope semantics, interpolation/extrapolation refusal behavior, spectral limitation, and the distinction between modeled Level-B contrast and empirical human first-seeing validation.

This report adds provenance and interpretation only. It changes no scientific result, seed, holdout, threshold, model, runtime, protocol, or production authorization.