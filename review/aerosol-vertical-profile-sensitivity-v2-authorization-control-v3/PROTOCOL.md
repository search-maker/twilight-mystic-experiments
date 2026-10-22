# AVPS v2 authorization-control v3 — metadata-stability recovery

Status: solver-free review/control recovery only. This stage does not allocate/reserve scientific ordinal 41, create an authorization/dispatch identity, apply candidate seeds to tracked cases, install/run libRadtran or MYSTIC, or open results.

## Why v3 exists

PR #601 / control-v2 passed identity, predecessor, exact-byte, artifact-digest, and tracked-tree seed checks, but its attempt-1 dedicated review `33213321554` failed at the two-pass repository-global seed recheck because a snapshot-fenced branch moved between complete enumerations. The handoff branch commit `088c0915c2c38ea06d0bda400e01241c563c6839` was written at `2026-08-28T21:37:46Z`, inside that scan window (`21:37:08Z`–`21:42:46Z`). No materialization or authorization boundary was reached. The #601 repository contract `33213321502` passed.

This recovery therefore changes **no scanner semantics and no scientific/control design**. It creates a fresh attempt-1 review identity and requires repository write-quiet behavior during the global snapshot/fence scan.

## Base and reviewed predecessors

This branch must be one direct child of frozen main `99ade7798627e67921139697ba1a004fa8a304bb` and vendor/reuse exact bytes already reviewed in #599/#600.

Required predecessor evidence:

- #599 preauthorization: head `a4e4700babddf0924135f5cc6ec6bfd21d8c9ec2`, run `33203372878`, contract `33203372798`, artifact `9699064164`, digest `sha256:b1125375bae24638375853d3724c1c96ba1572dc02e1619eff37d9fdca70b92e`.
- #600 disabled control/package: head `8a5d73974b02ba21fc2f010bbd911538e6981de2`, run `33205661865`, artifact `9699546728`, digest `sha256:9badcdc03bbeb181f731352afc48b75c67c14dc95a986fcf32163677d4ea972d`.

The 72 candidate group seeds remain in memory/artifacts only. Canonical seed identity: `02f624d582e9b2caba6b920d65a5e8a8bc8fc1a2693623bc2f73abf5d3f706d2`; canonical rows: `41f70d6a0381db6b569d3f4e17d74bb38b05cf212c2f2e432455a502f73dc670`. Literal seed values must never be committed or written into prose.

## Mandatory live review checks

Before materializing any proposed authorization document as an Actions artifact, the dedicated review must:

1. prove the review head is exactly one direct child of frozen main and the PR is Draft/open/unmerged;
2. bind exact #599/#600 PASS identities;
3. bind all reused prereg/seed/control/renderer/runtime bytes by exact Git blob;
4. repeat the exact-head tracked-tree candidate-seed literal scan;
5. repeat the unchanged two-pass repository-global candidate-seed scan in authorization-recheck mode;
6. re-enumerate the conservative global scientific-ordinal surface and require latest consumed = 40, maximum authoritative observed = 40, next candidate = 41, no v2 authorization/dispatch ref and no exact-looking ordinal-41 Issue #60 marker;
7. remain solver-free throughout.

The repository must remain write-quiet while step 5 is active. Any snapshot-fenced mutation is a correct fail-closed outcome and requires another fresh review identity, not a rerun or weakened scanner.

## Zero-runtime materializer boundary

The builder may emit the proposed `authorization.json` only inside the review artifact. The proposed document may name candidate ordinal 41 and future authorization/dispatch branch names, but the artifact itself is not an allocation/reservation.

It must bind the exact reviewed v3 control head as `exactAuthorizationParentCommit`, exact #599/#600 evidence, exact disabled control package, exact five four-species profile hashes, four-alias runtime identity, 360 cases / 72 CRN groups / 20M photons per case, and fresh candidate seed canonical hashes without serializing seed values.

It must keep dispatch/result/production boundaries closed: `dispatchAuthorized=false`, `automaticDispatch=false`, `resultOpeningAuthorized=false`, `productionAuthorized=false`, `taylorOrJerusalemFitAuthorized=false`.

No `authorization/` or `dispatch/` branch and no Issue #60 ordinal marker is created by this review.

## Later authorization identity

Only after this exact control/materializer review and repository contract both pass may a separate branch `authorization/aerosol-vertical-profile-sensitivity-v2-ordinal-41` be created as one direct child of the reviewed v3 control head. It may change exactly one file: `review/aerosol-vertical-profile-sensitivity-v2-authorization-control-v3/authorization.json`, byte-identical to the verified materializer artifact.

That later authorization PR must target this v3 control branch, remain Draft/open/unmerged, and pass the frozen authorization-review workflow on attempt 1. It may exclude only its own exact authorization ref/PR/runs from self-reservation accounting. Allocation in Issue #60, dispatch, science, and result opening remain still-later separate transitions.