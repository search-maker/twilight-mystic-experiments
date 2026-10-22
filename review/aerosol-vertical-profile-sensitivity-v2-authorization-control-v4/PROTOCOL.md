# AVPS v2 authorization-control v4 — materializer root-binding recovery

Status: solver-free control/review only. This stage does not allocate or reserve scientific ordinal 41, create an authorization/dispatch identity, apply candidate seed values to tracked cases, install/run libRadtran or MYSTIC, or open results.

## Why v4 exists

PR #601 failed closed because repository metadata changed during the two-pass global seed scan. PR #602 then kept the repository write-quiet and proved the unchanged global seed scan and fresh ordinal audit both PASS, but materialization failed locally because the builder used `HERE.parents[2]` instead of the repository root `HERE.parents[1]`.

v4 changes no scientific design and does not weaken any scanner. It retains the exact #602 authorization-core logic byte-for-byte as `build_authorization_core.py` (Git blob `6905eb13c06f99775f044ae7b3c05aaf8543edb7`) and adds a small wrapper that binds `ROOT = HERE.parents[1]`, the exact #600 control directory, and exact reviewed source blobs before invoking the frozen core. The later authorization guard uses the same corrected repository-root rule.

## Frozen predecessors

- frozen main `99ade7798627e67921139697ba1a004fa8a304bb`
- #599 head `a4e4700babddf0924135f5cc6ec6bfd21d8c9ec2`, run `33203372878`, contract `33203372798`, artifact `9699064164`, digest `sha256:b1125375bae24638375853d3724c1c96ba1572dc02e1619eff37d9fdca70b92e`
- #600 head `8a5d73974b02ba21fc2f010bbd911538e6981de2`, run `33205661865`, contract `33205661834`, artifact `9699546728`, digest `sha256:9badcdc03bbeb181f731352afc48b75c67c14dc95a986fcf32163677d4ea972d`
- candidate seed canonical SHA `02f624d582e9b2caba6b920d65a5e8a8bc8fc1a2693623bc2f73abf5d3f706d2`
- candidate row canonical SHA `41f70d6a0381db6b569d3f4e17d74bb38b05cf212c2f2e432455a502f73dc670`

Literal candidate seed values remain artifact/in-memory only and must never be committed or written into PR/Issue/handoff prose.

## Mandatory v4 review

The v4 Draft PR must be one direct child of frozen main and must pass, on attempt 1:

1. exact main-child/Draft/open/unmerged identity;
2. exact #599/#600 PR/run/artifact bindings;
3. exact reviewed Git-blob bindings for prereg, seed, renderer, control, runtime, frozen authorization core, wrapper and guard;
4. exact-head tracked-tree candidate-seed literal scan;
5. the unchanged two-pass repository-global seed scan in authorization-recheck mode;
6. a fresh conservative global ordinal audit requiring latest consumed = 40, authoritative max = 40, next candidate = 41, and no ordinal-41 authorization/dispatch ref or Issue #60 marker;
7. materialization of the proposed `authorization.json` only into an Actions artifact;
8. proof that the document contains no literal candidate seed value and reconstructs exactly 360 cases / 72 CRN groups in memory;
9. artifact upload followed by a final global ordinal readback;
10. no `uvspec`, libRadtran, MYSTIC, result opening, Level-B or production transition.

The repository must remain write-quiet while the snapshot-fenced global scan runs. A metadata movement is a fail-closed outcome requiring another fresh review identity, not a rerun.

## Materializer boundary

The artifact-only proposed document may name candidate ordinal 41 and the future authorization/dispatch branch names. It is not an allocation or reservation. It must keep `dispatchAuthorized=false`, `automaticDispatch=false`, `resultOpeningAuthorized=false`, `productionAuthorized=false`, and `taylorOrJerusalemFitAuthorized=false`.

## Later authorization identity

Only after the exact v4 control head and its repository contract both PASS may `authorization/aerosol-vertical-profile-sensitivity-v2-ordinal-41` be created as one direct child of that exact reviewed v4 head. That child may change exactly one file: `review/aerosol-vertical-profile-sensitivity-v2-authorization-control-v4/authorization.json`, byte-identical to the verified v4 artifact.

The authorization PR must target the v4 control branch, remain Draft/open/unmerged, and pass the frozen attempt-1 authorization-review workflow. It may exclude only its own exact authorization branch/PR/runs from self-reservation accounting. Issue #60 allocation, dispatch, science, and result opening remain separate later transitions.