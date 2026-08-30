# AVPS v2 recovery3 — live dynamic preauthorization v2

## Recovery lineage

This is the fresh control identity after immutable failed PR #692 / head `0a1a747d1ade460c3eba92c52cb77cebd6114b8d` / dedicated run `33308955617` attempt 1. That attempt failed before candidate rebuild or any global scan because its review workflow referenced nonexistent Issue-comment ID `5467062055`. The actual ordinal-43 consumed marker is Issue #60 comment `5467301509`, whose body is exactly `ORDINAL43_AVPS_V2_POSTCONSUMPTION_RECOVERY2_DISPATCH_CONSUMED`. No rerun/retry/resume of the failed identity is permitted.

The v2 control also fixes the independently spotted missing `argparse` import in the review helper. Neither correction changes frozen AVPS science, candidate seeds, acceptance rules, or any authorization/result boundary.

## Purpose

This is the fresh solver-free preauthorization gate required after publication of the reviewed recovery3 candidate-seed package on public `main` `384f94c02b892768a9dde6fe17e69a384112ef73`. It rechecks the exact recovery3 candidate-seed and global scientific-ordinal surfaces against live repository state before any new authorization identity may be proposed.

The frozen scientific design is unchanged: 360 cases, 72 common-random-number groups, five independently defined vertical-profile states, 20,000,000 photon histories per case, and the existing geometry, wavelength, optical-property, estimator, aggregation, classification and result-opening rules. Ordinals 41, 42 and 43 and all of their seeds, authorization/dispatch identities and failed attempt-1 runs remain permanently consumed and non-reusable.

The reviewed recovery3 candidate identity remains seed canonical SHA-256 `d2817b1ea4f2bdc8cb1842e565b099b015e4e28c5874482629fadc450069d9bf` and row canonical SHA-256 `b6a519eadacdb99ea53c52d483c8acfeba05829643cb988de21682a53fc47896`. Candidate values remain review/artifact identities only and are not yet scientific authorization inputs.

## Required protected review

The exact-head review must:

1. bind exact base/main `384f94c02b892768a9dde6fe17e69a384112ef73`, exact fresh v2 branch/head, and an exact three-file review-only diff;
2. bind the published recovery3 package bytes and protected proof from PR #689 / run `33305675119` / artifact `9730444904` (`sha256:13f833045d446b813e653ea10f018db98df956e80c51f76eccd9802f0bd47a48`), plus publication PR #691 / merge `384f94c02b892768a9dde6fe17e69a384112ef73`;
3. validate consumed ordinal-41/42/43 run identities and the exact ordinal-43 consumed marker `5467301509`, and validate the ordinal-42 seed ledger only at its native historical authorization-head path;
4. rebuild exactly the same 72 recovery3 candidate seeds and prove zero overlap with consumed ordinal-41/42/43 seed sets;
5. repeat the exact tracked-tree and complete two-pass repository-global seed scan in authorization-recheck mode inside an explicit Issue #60 WRITE_QUIET fence;
6. dynamically derive the next unused global scientific ordinal from the authoritative observation surface, without hard-coding any successor number, and refuse any pre-existing proposed authorization/dispatch ref or matching Issue #60 marker;
7. perform a final unchanged-head/global-ordinal recheck before PASS and emit only a proof artifact with all authorization/runtime/result/Level-B/holdout/production flags false.

The review must fail closed on a seed collision, consumed-identity drift, missing historical native-path binding, snapshot instability, branch/head movement, ordinal-surface drift, or any attempted runtime/authorization transition. A failed protected attempt must not be rerun/retried/resumed.

## Boundary

PASS means only that a separately reviewed fresh authorization-control/allocation gate may consume this proof if another authorization-time recheck still passes. This package does not allocate an ordinal, create authorization or dispatch refs, apply candidate seeds to cases, execute libRadtran/MYSTIC/uvspec, open AVPS numerical results, admit vertical profile/spectral AOD/SSA/phase/family into Level-B, access protected holdouts, use Taylor/Jerusalem residuals, or change production behavior.

Until a successful future AVPS numerical result is opened through its frozen result gate and a separately preregistered component-selective shadow mapper passes held-out direct-MYSTIC validation, `AOD550` remains the only directly consumed validated-v3 aerosol coordinate. Every richer OAS-v2 `newMappingAuthorized` flag remains `false`.
