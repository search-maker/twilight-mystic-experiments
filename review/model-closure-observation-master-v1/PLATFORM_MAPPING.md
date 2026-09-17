# Observation requirement -> platform persistence mapping

Status: **review-only integration map.** This document does not open a holdout, change the model, or certify the observation platform as ready.

Purpose: ensure every item in `FIELD_CHECKLIST.md` has either (a) an existing first-class storage path, (b) a structured validation-metadata path in Draft PR #7, or (c) an explicit unresolved implementation/QA blocker.

## Existing first-class platform records

| Requirement | Platform location | Status / boundary |
|---|---|---|
| observer pseudonymous/versioned profile | `observerProfiles` | existing |
| ordinary vision correction | `observerProfiles.visionCorrection` | existing; do not duplicate in validation metadata |
| site latitude/longitude/elevation | `observingSites`, immutable `sessionLocations` | existing |
| location/elevation accuracy + source | `sessionLocations.horizontalAccuracyM`, `altitudeAccuracyM`, `source` | existing |
| session role/mode/protocol version | `sessions` + frozen protocol/model records | existing architecture; final calibration/holdout role policy still governed by validation protocol |
| frozen model run/prediction | `modelRuns`, `modelPredictions` | existing |
| target catalog identity / magnitude / color / spectral type | `targets` | existing |
| explicit observation events | `observationEvents` | existing; PR #5 separately improves device timing path |
| device wall-clock + monotonic ordering | scientific timing subsystem | existing |
| server offset / round-trip / timing uncertainty | clock sync / clock-anchor records; `TimeEvidence` | existing |
| raw/corrected time kept separately | timing subsystem | existing design; do not overwrite raw event time |
| meteorology/AOD/context snapshots | `sessionEnvironment` plus new validation evidence where provenance/event granularity requires it | existing + PR #7 |

## Draft PR #7: append-only validation metadata

PR: `search-maker/stars-observation-platform#7`, branch `review/validation-metadata-contract-v1`.

The dedicated `VALIDATION_METADATA_EVENT` outbox/endpoint stores immutable typed evidence without altering the observation timestamp row.

| FIELD_CHECKLIST requirement | PR #7 metadata path | Notes |
|---|---|---|
| adaptation condition / outdoor exposure state | `ADAPTATION_STATE` | includes continuous exposure, sunglasses/screen state, occlusion |
| screens/flashlights/headlights/controlled bright exposure | `BRIGHT_LIGHT_EVENT` | start/end/category/control; optional measured luminance/spectrum evidence |
| direct/averted/free viewing | `VIEWING_STATE.viewingMode` | structured |
| eye use | `VIEWING_STATE.eyeUse` | structured |
| target-location knowledge / search radius / uncertainty | `VIEWING_STATE` | structured |
| search duration + uncertainty | `VIEWING_STATE` | structured |
| identification/visibility confidence | `VIEWING_STATE` | structured |
| search ease | `VIEWING_STATE.searchEase` | diagnostic; not a physiological parameter by itself |
| reference anchor used | `VIEWING_STATE` | structured |
| gaze method/azimuth/altitude/uncertainty | optional `VIEWING_STATE` fields | added for A1/retinal claims; ordinary H1 does not require eye tracking |
| retinal eccentricity evidence | optional `VIEWING_STATE.retinalEccentricityDeg` + evidence ID | only claim measured eccentricity when measurement/control supports it |
| pupil method/diameter/uncertainty | optional `VIEWING_STATE` fields | required by analysis policy only for physical retinal-illuminance/bleach claims |
| instrument model/serial/FOV/calibration/spectral response/raw hash | `INSTRUMENT_EVIDENCE` | structured |
| target-direction sky measurement | `SKY_EVIDENCE:DIRECTIONAL` | pointing + raw value/unit; optional photopic/SQM derived quantity |
| zenith sky context | `SKY_EVIDENCE:ZENITH` | structured |
| calibrated all-sky frame | `SKY_EVIDENCE:ALL_SKY_FRAME` | frame/hash/calibration + optional masks/HDR provenance |
| spectral sky evidence | `SKY_EVIDENCE:SPECTRAL` | evidence ID + optional response ID |
| AOD provenance | `ATMOSPHERE_EVIDENCE:AOD` | source/time/AOD/Angstrom/grid distance |
| meteorology | `ATMOSPHERE_EVIDENCE:METEOROLOGY` | temperature/pressure/humidity/PM/extinction fields |
| clouds/haze/smoke/dust/artificial-light event evidence | `ATMOSPHERE_EVIDENCE` event kinds | structured top-level event/provenance; detailed raw evidence can remain referenced |
| horizon profile | `SITE_EVIDENCE:HORIZON_PROFILE` | profile evidence ID + optional raw hash |
| local obstruction | `SITE_EVIDENCE:LOCAL_OBSTRUCTION` | azimuth/obstruction altitude + optional uncertainty/class |
| site photograph | `SITE_EVIDENCE:SITE_PHOTO` | hash-bound raw evidence |
| protocol deviation | `PROTOCOL_DEVIATION` | append-only; never erase the raw session |

The database column `metadata_type` is generic text and `payload_json` is versioned JSON, so the new `SITE_EVIDENCE` event class does not require a second migration while v1 is still unmerged. The offline operation kind remains one generic `VALIDATION_METADATA_EVENT`.

## Important things PR #7 does **not** provide

A persistence path is not the same as an acquisition system. The following remain open:

1. **Dark-safe capture UI** — not every metadata field has an observer-facing/technician-facing low-distraction input path yet.
2. **Automatic instrument ingestion** — SQM/all-sky/spectral/AOD evidence may still need device/provider-specific import adapters.
3. **Eye-tracking/pupillometry integration** — optional schema exists, but no claim is made that a supported hardware pipeline exists.
4. **Horizon survey tooling** — schema can persist a profile/obstruction; the calibrated survey/import workflow still has to be implemented/verified.
5. **Full repository QA** — GitHub Actions for `stars-observation-platform` currently fails before the first job step (`steps=null`), including one explicit QA retry. Thus test/typecheck/build have not actually run in Actions.
6. **D1 migration review** — migration must be checked against deployed database state before merge.
7. **Real-device offline/idempotent pilot** — endpoint/outbox retry, crash recovery and read-back identity must be exercised on the actual device/network path.
8. **Final holdout gate** — even a perfectly functioning persistence layer does not authorize opening H1/A1 validation data before model/protocol/analysis freezes are complete.

## Pre-merge data-contract review still needed

Because Actions cannot currently execute tests, PR #7 should remain Draft. In addition to test/typecheck/build once runners work, review whether v1 should reject **unknown payload keys** fail-closed. The current validator checks required/known scientific fields, but a misspelled optional field must not be allowed to create false confidence that evidence was captured. Decide and test the strictness policy before the contract is treated as frozen for final validation.

## Readiness definition

The empirical program is acquisition-ready only when all of these are true:

- required persistence paths exist and are versioned;
- the dark-safe UI/device/import path can actually populate them;
- clock and raw-event preservation are verified on-device;
- instrument calibration/provenance linkage works end-to-end;
- offline/retry/idempotency passes a real-device pilot;
- repository tests/typecheck/build pass;
- pilot sessions demonstrate <=10 s human-state cadence and <=30 s all-sky cadence where required;
- calibration/holdout role separation is enforced;
- the final model/protocol/uncertainty/acceptance rules are frozen before untouched validation is opened.

Until then, the correct status is **protocol and persistence preparation**, not empirical validation complete.
