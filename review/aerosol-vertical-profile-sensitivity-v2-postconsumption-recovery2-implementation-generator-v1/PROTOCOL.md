# AVPS v2 post-consumption recovery2 implementation generator v1

Status: **review-only / zero runtime / artifact-only generated workflow bytes / no dispatch / results closed**.

This package implements the next stage frozen by merged execution-control PR #651. It does **not** place an executable recovery2 science, publisher, or trigger workflow on `main`. Dedicated pull-request CI must deterministically generate those three candidate files only as an artifact and independently prove that the delta from the permanently consumed ordinal-42 recovery1 implementation is limited to the already-reviewed ordinal-43 identity/provenance and native authorization-head seed-transport repair.

## Frozen source and authorization bindings

- exact base main: `db4c2574bcdf839f5112e1ca3c0242ff35b7880f`;
- execution-control blob: `review/avps-v2-recovery2-ordinal43-execution-control-v1/execution-delta.review.json` = Git blob `005d0f2f531d613f24da019382cf66b9867709d1`;
- consumed ordinal-42 science source blob: `7af7f28269ad245b1b9218012707957b048a6875`;
- consumed ordinal-42 publisher source blob: `885abc21c86d3bb0c3777e63b6254520479db34f`;
- consumed ordinal-42 trigger-bridge source blob: `52d60be9c3f219f7fcbc0e692b9c8423cce3a95f`;
- recovery2 authorization PR #647, head `5fd0c82cb14a02ace38a5a7be30b8b075ccae298`, parent `0842dd27f62c4bc2af4b5763ae4dd547ee009fce`;
- authorization review run `33277629404` attempt 1, artifact `9722104370`, digest `sha256:9dac9e9305b78e2ddbceacbc10a19435121b0eeacfe48550d23878359556ae15`;
- ordinal-43 allocation marker comment `5465211169`; ordinal 43 remains allocated but undispatched and unconsumed;
- recovery2 seed ledger blob `d4bdc95e9ed576fa6c70711c81d8097ddab33dbf`, 72 seeds, canonical `38c074fe01bd6d09fa7dc78af1ad323e2f42b606ca992c2950b8fc1f5b343a9f`, rows canonical `a88b28dcfaaeb354f294d1705a0f8ddbcd061083f277a038ab8c9dace44d9954`;
- native seed-transport helper blob `2df2c3fd1ffa78e16f44e6825d67b3e82e903c1e`;
- consumed ordinal-42 historical seed-ledger blob `491d1b6653bea0fcc5275269723a76aa1af52300` at its native historical authorization-head path.

## Allowed candidate delta

The generated recovery2 candidates may change only:

1. fresh ordinal-43 authorization/review/dispatch/execution identities and markers;
2. recovery2 workflow/run/concurrency/artifact names;
3. the recovery2 candidate seed canonical identity;
4. seed validation from the failed relocated-file pattern to the reviewed native authorization-head helper, including native validation of the historical ordinal-42 dependency;
5. uniqueness queries scoped to the fresh recovery2 workflow identity;
6. a fresh pre-dispatch global ordinal/identity check proving ordinal 42 remains the latest consumed/dispatched ordinal while the already reviewed ordinal 43 is the maximum observed allocated identity and remains unconsumed.

The 360-case / 72-common-random-number-group / five-profile-state / 20,000,000-photon-per-case scientific design, exact profiles, geometry, AOD, wavelengths, executor, aggregator, stopping rules, analysis rules, Level-B criterion, and result-opening boundary may not change.

## Required native seed transport

The generated science and publisher workflows must call `native_authorization_seed_transport.py` against detached native worktrees. They must never copy the recovery2 authorization seed ledger to a temporary path and import it there before validation. The helper must prove the authorization ledger at its native path, the consumed ordinal-42 ledger at its native historical path, the exact Git blobs, 72 candidate seeds, both canonical hashes, and zero overlap with consumed ordinal 41/42 seeds before the existing tracked-tree and repository-global scans continue.

## Publication and dispatch boundaries

This review package itself has read-only repository permissions and no libRadtran/MYSTIC/uvspec runtime. Passing CI authorizes only a later, separately reviewed publication PR containing the exact generated candidate bytes. It does not create a dispatch branch, consumed marker, workflow dispatch, solver execution, result opening, Level-B admission, protected holdout access, Taylor/Jerusalem scoring, or production transition. Ordinals 41 and 42, their seeds, runs, and dispatch identities remain permanently non-reusable. Recovery2 results remain closed until the separately frozen result-opening gate is satisfied.
