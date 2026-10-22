# AVPS v2 post-consumption recovery1 authorization control v1

Status: **REVIEW ONLY / MATERIALIZE ONE FRESH AUTHORIZATION CANDIDATE / NO ALLOCATION / NO DISPATCH / NO SOLVER**.

## Immutable predecessor evidence

- consumed AVPS-v2 identity: scientific ordinal 41, run `33236295233`, attempt 1; structural failure before scientific solver execution; ordinal/seeds/dispatch/run identity permanently non-reusable;
- frozen repaired science base: public `main` `6f0b3f3c73b23f84951bd7b6a2bad58d00854982` with restored reviewed `rh_audit_dependency.py` Git blob `095ff86f12a79dc312a51f734b0a03bd318f2337`;
- fresh recovery seed review: Draft PR #622, head `3f9a03b913125077a37a3eb56d1c031127bdfd60`, run `33242753388` attempt 1 SUCCESS, artifact `9711902664`, digest `sha256:12934972f2a533c006a11012d2f2374e76873d9982dae0b1d5db656e6097b460`;
- fresh seed identity: 72 candidate CRN-group seeds, candidate canonical SHA-256 `a514212990a94a39d577bd038b631a600e18e4c0f750f781bbd7c99b897228a7`, row canonical SHA-256 `8213e65782b62d0e1a0ea51d620016fdcaa24b348e726f5570c54f7f1155a895`, overlap with consumed ordinal-41 seeds exactly 0;
- dynamic global preauthorization: Draft PR #623, head `752e7c55740cdc0c6033deda71db9bc0dbb7fdf4`, dedicated run `33245550336` attempt 1 SUCCESS, exact-head contract `33245550340` SUCCESS, artifact `9712820519`, digest `sha256:5768dca0f4507c3a345f611ee4a71e1c955d3b1a6c95083add6f7030e55993de`;
- preauthorization report status `PASS_POSTCONSUMPTION_RECOVERY1_PREAUTHORIZATION_SURFACE_CLEAN_NOT_ALLOCATED`, content SHA-256 `3dd8a3729ff29a6d81f8b2e7ff1fb2e5c8e88e39a010d0a1a7ee561999875ebb`, with dynamically observed next available scientific ordinal 42 and `nextOrdinalHardCoded=false`.

## Frozen recovery authorization identity

Subject to a fresh control-review global readback still proving ordinal 42 available, the sole candidate identity is:

- authorization ref: `authorization/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery1-ordinal-42`;
- dispatch ref: `dispatch/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery1-ordinal-42`;
- execution key: `aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery1:numerical:42`;
- case universe: unchanged 360 cases / 72 common-random-number groups / five states per group;
- photon histories: unchanged 20,000,000 per case;
- all physical profile, geometry, atmosphere, spectral, threshold, aggregation, Level-B/result-opening and anti-fitting rules remain byte/semantically inherited from the reviewed AVPS-v2 design; only fresh scientific identity/seeds plus the already-reviewed transport repair differ from the consumed ordinal-41 attempt.

Candidate seed values are never serialized into tracked prose or this control package. They remain deterministically regenerable from the reviewed recovery seed ledger and may be applied in memory only by a separately reviewed fresh execution path after allocation and dispatch.

## Required control review

The dedicated review must remain solver-free and must:

1. bind the exact #622 and #623 attempt-1 SUCCESS runs/artifacts/digests;
2. download and independently verify the #623 preauthorization proof and its self-hash;
3. regenerate the 72 recovery candidate seeds and prove the exact canonical hashes and zero consumed-seed overlap;
4. bind the repaired runtime support byte and unchanged frozen AVPS-v2 physical/runtime identities;
5. perform a fresh conservative repository-global ordinal readback immediately before materialization and require 41 consumed, maximum authoritative ordinal 41, proposed 42 still free, no proposed authorization/dispatch refs and no exact allocation/consumption marker for 42;
6. materialize exactly one proposed `authorization.json` only into the Actions artifact workspace, never the tracked tree;
7. upload a review receipt and candidate authorization artifact with all allocation/dispatch/runtime/result-opening flags false for this control review itself.

## Hard boundary

A PASS control artifact is not allocation. It does not create the authorization ref, Issue #60 allocation marker, dispatch ref, consumed marker, scientific workflow run, solver execution, result opening, Level-B admission, protected holdout access, fitting/model selection, or production change. A separate one-file Draft authorization child and fresh attempt-1 authorization review are mandatory. That review must repeat fresh seed/global-ordinal guards before any allocation marker is written.
