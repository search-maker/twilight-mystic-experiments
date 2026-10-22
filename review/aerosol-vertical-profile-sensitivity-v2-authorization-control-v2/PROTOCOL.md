# AVPS v2 authorization-control v2

Status: solver-free review/control plane only. This package does not allocate or reserve a scientific ordinal, does not create an authorization or dispatch identity, does not apply candidate seeds to tracked cases, does not install/run libRadtran or MYSTIC, and does not open results.

## Base and reviewed predecessors

This control branch must be a direct child of frozen main `99ade7798627e67921139697ba1a004fa8a304bb` and must vendor/reuse exact bytes already reviewed in #599/#600.

Required predecessor evidence:

- #599 preauthorization: head `a4e4700babddf0924135f5cc6ec6bfd21d8c9ec2`, run `33203372878`, contract `33203372798`, artifact `9699064164`, digest `sha256:b1125375bae24638375853d3724c1c96ba1572dc02e1619eff37d9fdca70b92e`.
- #600 disabled control/package: head `8a5d73974b02ba21fc2f010bbd911538e6981de2`, run `33205661865`, artifact `9699546728`, digest `sha256:9badcdc03bbeb181f731352afc48b75c67c14dc95a986fcf32163677d4ea972d`.

The 72 candidate group seeds remain derived in memory/artifacts only. Their canonical identity is `02f624d582e9b2caba6b920d65a5e8a8bc8fc1a2693623bc2f73abf5d3f706d2`; canonical rows are `41f70d6a0381db6b569d3f4e17d74bb38b05cf212c2f2e432455a502f73dc670`. Literal seed values must never be committed or written into PR/Issue/handoff prose.

## Mandatory live review checks

Before a candidate authorization document may be materialized as an Actions artifact, the dedicated review must:

1. prove this review head has exactly one parent and that parent is frozen main;
2. prove the PR is Draft/open/unmerged and the changed-file universe is exactly the frozen reviewed inputs plus this authorization-control surface;
3. re-bind #599 and #600 exact PR/run/artifact identities;
4. re-run the exact-head tracked-tree candidate-seed literal scan;
5. re-run the two-pass repository-global candidate-seed scan in authorization-recheck mode;
6. re-enumerate the conservative global scientific-ordinal surface and require latest consumed = 40, maximum authoritative observed = 40, and next available candidate = 41, with no v2 authorization/dispatch ref and no exact-looking ordinal-41 Issue #60 marker;
7. remain solver-free (`uvspec` absent) throughout.

## Zero-runtime materializer boundary

The builder may emit a proposed `authorization.json` only inside the review run artifact. The proposed document may name candidate ordinal 41 and future authorization/dispatch branch names, but the artifact itself is not a reservation/allocation.

The candidate document must bind this exact reviewed control head as `exactAuthorizationParentCommit`, the exact #599/#600 evidence, the exact disabled control package, the five exact four-species profile hashes, the four-alias runtime identity, 360 cases / 72 CRN groups / 20M photons per case, and the fresh candidate seed canonical hashes without serializing seed values.

It must keep dispatch/result/production boundaries closed: `dispatchAuthorized=false`, `automaticDispatch=false`, `resultOpeningAuthorized=false`, `productionAuthorized=false`, and `taylorOrJerusalemFitAuthorized=false`.

No branch beginning `authorization/` or `dispatch/` is created by this review.

## Later authorization identity

Only after this control/materializer review and repository contract both pass on the same exact head may a separate branch `authorization/aerosol-vertical-profile-sensitivity-v2-ordinal-41` be created as one direct child of that reviewed control head. That child may change exactly one file: `review/aerosol-vertical-profile-sensitivity-v2-authorization-control-v2/authorization.json`, byte-identical to the verified materializer artifact.

The authorization PR must target this reviewed control branch, remain Draft/open/unmerged, and pass the frozen authorization-review workflow on attempt 1. Its live ordinal check may exclude only its own exact branch/PR/runs as self-reservation; every independent ordinal-41 observation remains a refusal.

Even a successful authorization review does not post the Issue #60 allocation marker and does not dispatch science. Allocation and dispatch remain later separate transitions.