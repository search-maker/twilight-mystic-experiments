# AVPS v2 authorization-control v1

Status: review-only control plane. This stage does **not** allocate/reserve scientific ordinal 41, does not create an authorization/dispatch identity, does not apply candidate seeds to cases, does not install/run libRadtran or MYSTIC, and does not open results.

## Bound predecessors

The gate is a direct descendant of the reviewed disabled control package and must independently bind the exact successful attempt-1 evidence for:

- v2 preauthorization PR #599, head `a4e4700babddf0924135f5cc6ec6bfd21d8c9ec2`, run `33203372878`, artifact `9699064164`, digest `sha256:b1125375bae24638375853d3724c1c96ba1572dc02e1619eff37d9fdca70b92e`;
- v2 disabled control/package PR #600, head `8a5d73974b02ba21fc2f010bbd911538e6981de2`, run `33205661865`, artifact `9699546728`, digest `sha256:9badcdc03bbeb181f731352afc48b75c67c14dc95a986fcf32163677d4ea972d`.

The frozen candidate identity remains 72 CRN group seeds with canonical seed SHA-256 `02f624d582e9b2caba6b920d65a5e8a8bc8fc1a2693623bc2f73abf5d3f706d2` and canonical row SHA-256 `41f70d6a0381db6b569d3f4e17d74bb38b05cf212c2f2e432455a502f73dc670`. Candidate seed literals remain in-memory/artifact-only and are never committed.

## Required live rechecks

Before materializing any proposed authorization document, the review workflow must:

1. repeat the exact tracked-tree candidate-seed literal scan on its own head;
2. repeat the two-pass repository-global candidate-seed collision scan in authorization-recheck mode;
3. re-enumerate the conservative repository-global scientific-ordinal surface and require latest consumed = 40, observed max = 40, next candidate = 41, with neither the proposed v2 authorization nor dispatch branch present and no `ORDINAL41_...` Issue #60 allocation/consumption marker;
4. require all predecessor PR/run/artifact identities to remain exact and unexpired.

## Zero-runtime materializer boundary

`build_authorization.py` may emit a proposed `authorization.json` only into an Actions artifact. The proposed document may name ordinal 41 and the future authorization/dispatch branches, but that artifact is not an allocation or reservation. It must bind the exact current authorization-control head as the future authorization parent and must keep `dispatchAuthorized=false`, `automaticDispatch=false`, `resultOpeningAuthorized=false`, `productionAuthorized=false`, and `taylorOrJerusalemFitAuthorized=false`.

No authorization branch is created by this stage. No Issue #60 ordinal-41 allocation marker is posted by this stage.

## Separate authorization review

Only after this control/materializer review passes may a new branch named `authorization/aerosol-vertical-profile-sensitivity-v2-ordinal-41` be created as a direct child of the exact successful authorization-control head. That branch must change exactly one file: `review/aerosol-vertical-profile-sensitivity-v2-authorization-control-v1/authorization.json`, byte-identical to the verified materializer artifact.

The authorization PR must target the authorization-control branch, remain Draft/open/unmerged, and pass the frozen `aerosol-vertical-profile-sensitivity-v2-authorization-review.yml` workflow on attempt 1. The authorization review repeats the candidate-seed and global-ordinal rechecks while excluding only its own exact authorization ref/PR/runs from self-reservation accounting. Any independent ordinal-41 identity or Issue #60 allocation/consumption marker is a refusal.

Even a successful authorization review does not dispatch science. Allocation in Issue #60 and dispatch remain later, separate transitions.