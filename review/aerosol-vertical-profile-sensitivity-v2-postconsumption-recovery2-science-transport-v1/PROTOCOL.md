# AVPS v2 post-consumption recovery2 — science transport repair protocol

Status: **PREREGISTERED / ZERO-RUNTIME / NO AUTHORIZATION / NO DISPATCH**

This protocol freezes the next safe recovery gate after the consumed ordinal-42 AVPS v2 recovery execution failed before any scientific runtime. It is a mechanical transport recovery only. It does not change the frozen AVPS v2 scientific design, open any result, or authorize a new scientific execution.

## Immutable failure evidence

- Governing ledger: Issue #60 under `MYSTIC-STATE-0067` unless a later explicit directive supersedes it.
- Publication main immediately before the failed science run: `83fa106956d003b087ac4d13f9d4200fc8a42bf2`.
- Consumed authorization identity: ordinal 42, authorization head `e627a689ada0493a8a5b9cdafc4aba0198fbabec`, authorization PR #629.
- Consumed dispatch branch: `dispatch/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery1-ordinal-42`.
- Consumed execution key: `aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery1:numerical:42`.
- Consumed marker: `ORDINAL42_AVPS_V2_POSTCONSUMPTION_RECOVERY1_DISPATCH_CONSUMED`, Issue #60 comment `5463204358`.
- Failed science workflow run: `33259899524`, attempt 1.
- Failed preflight job: `99119933393`.
- Step `Prove exact one-use dispatch and authorization identity before runtime`: **SUCCESS**.
- Step `Fresh repository-global candidate-seed recheck and one-use guard`: **FAILURE**.
- All downstream profile recovery, matrix, OPAC, case, aggregation and opening jobs/steps were skipped. No `uvspec`/MYSTIC solver execution occurred.

The exact failure is path-context relocation of the authorization-bound seed ledger. The science workflow copied

`review/aerosol-vertical-profile-sensitivity-v2-postconsumption-seed-freshness-v1/seed_ledger.py`

from the authorization head to

`execution-preflight/recovery-seed-ledger.py`

and imported that relocated copy. Its repository-root derivation then resolved one directory above the checkout and attempted to read

`/home/runner/work/twilight-mystic-experiments/review/aerosol-vertical-profile-sensitivity-v2-prereg/build_skeleton.py`,

raising `FileNotFoundError` before any runtime setup or solver work.

The earlier recovery2 publisher fixed the same class of defect correctly by validating the authorization seed ledger at its **native path in a detached authorization-head worktree**. The science workflow retained the older relocation pattern; this protocol applies the same root-stable principle to the science transport.

## Consumed-identity rule

Ordinal 42 is permanently consumed even though its scientific run failed pre-runtime. Therefore:

- never GitHub Re-run/retry/resume run `33259899524`;
- never reuse ordinal 42;
- never reuse its dispatch branch, execution key, authorization head as a new execution identity, or its 72 candidate seeds;
- never reinterpret the failed run as scientific evidence about vertical-profile sensitivity.

Any later scientific recovery requires a **fresh repository-global seed ledger**, a **fresh authorization/execution identity**, and the dynamically verified next unused global scientific ordinal. Ordinal 43 is only an expectation; it MUST NOT be allocated merely because it is numerically next. A fresh global preauthorization scan must prove the actual next unused ordinal at allocation time.

## Frozen scientific design to preserve

A recovery may repair transport only. It must preserve the previously reviewed AVPS v2 scientific design unless a separate preregistration explicitly changes science before results:

- 360 cases total;
- 72 common-random-number groups;
- 5 vertical-profile states per group;
- 20,000,000 photon histories per case;
- the same five independently defined profile states and their validated profile-byte provenance;
- the same geometries, wavelengths, aerosol optical-property/source contracts, estimator/aggregation semantics, classification rules, stopping/budget rules, and closed-result boundary;
- no Taylor/Jerusalem residual use for seed generation, design, thresholds, profile choice, or recovery decisions;
- `resultOpeningAuthorized=false` and `productionAuthorized=false` through execution.

The failed ordinal-42 seed values themselves are NOT part of the preserved scientific design and must be replaced by a fresh preregistered collision-free seed set.

## Required science-transport repair

The corrected science transport must validate the authorization-bound fresh seed ledger without relocating it away from its repository context. The preferred reviewed implementation is:

1. fetch the exact fresh authorization branch/head;
2. create a detached worktree at the exact fresh authorization head;
3. prove the authorization-head parent, authorization file, and seed-ledger blob identities;
4. import/execute the seed ledger from its **native tracked path inside that detached worktree**;
5. prove `relocatedBeforeValidation=false` in machine-readable preflight evidence;
6. emit the canonical candidate-seed ledger from that native validation;
7. run tracked-tree and repository-global collision checks against the current execution repository;
8. refuse before runtime on any path/blob/root/seed/ordinal/marker/run-cardinality drift.

A root-stable mechanism demonstrably equivalent to native-path detached-worktree validation may be proposed, but it must receive a separate exact-head solver-free review before use. Merely copying the ledger to a temporary directory and importing the copy is forbidden.

## Recovery ordering

The following ordering is frozen:

1. review and merge only the mechanical science-transport repair infrastructure;
2. produce and review a fresh candidate-seed proof for the recovery identity;
3. perform a fresh repository-global preauthorization scan, dynamically determining the next unused global ordinal and proving no seed collisions / prior candidate identity;
4. materialize exactly one fresh authorization child with the frozen scientific design and fresh seeds;
5. review that authorization without scientific runtime;
6. only after fresh no-duplication/no-consumption checks, create the one-use dispatch identity and consumed marker;
7. execute the fresh science workflow attempt 1 only;
8. keep results closed until the already-preregistered opening/analysis gate is separately satisfied.

No later step may be performed merely because an earlier artifact exists; every live gate must be rechecked immediately before its mutation.

## Review requirements for the transport repair

Before merge, an exact-head solver-free review must prove at least:

- run `33259899524` attempt 1 is immutable terminal failure and job `99119933393` failed in the documented preflight step;
- all case jobs were skipped and no solver result exists from ordinal 42;
- the proposed transport diff changes no AVPS scientific matrix/profile/optical/estimator/analysis criterion;
- no authorization, dispatch branch, consumed marker, workflow dispatch, solver execution, result opening, Level-B admission, holdout access, Taylor/Jerusalem scoring, or production mutation occurs as part of the repair review;
- the repair removes the relocated-ledger failure mode and binds validation to exact tracked authorization bytes at native repository context;
- ordinal 42 and its seeds remain classified as consumed and unusable.

## Non-authorizations

This protocol does **not** authorize:

- re-execution of ordinal 42;
- allocation of ordinal 43 or any other ordinal without a fresh global scan;
- seed reuse;
- MYSTIC/libRadtran execution;
- viewing or inferring AVPS result values;
- Level-B promotion or richer Operational Atmosphere State consumption;
- protected holdout opening;
- Taylor/Jerusalem fitting or residual-guided model selection;
- production-default changes.
