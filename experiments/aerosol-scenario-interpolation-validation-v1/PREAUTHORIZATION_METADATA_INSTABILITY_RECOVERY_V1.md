# ASIV v1 preauthorization metadata-instability recovery

This file records a zero-runtime control-plane failure and intentionally provides one additive ASIV-path main change from which a fresh exact-main preauthorization attempt may start after merge.

## Failed exact-main attempt 1

- exact main: `0e3e190b9914eee1cfe338657646256b2de2221c`
- workflow: `ASIV v1 fresh preauthorization audit`
- run: `32690085847`
- attempt: `1`
- job: `97322074335`
- conclusion: `failure`
- failing step: `Stable repository-global authorization-time candidate-seed recheck`
- exact terminal refusal: `snapshot-fenced repository-global metadata changed between two complete enumerations; refuse this audit and start a fresh attempt-1 workflow run`

All preceding checks passed: exact attempt-1 main/zero-runtime surface, deterministic 24-candidate seed ledger, and exact tracked-tree candidate-seed scan. The failure was the proven repository-global scanner's fail-closed response to metadata movement during its two complete enumerations; it was not a reported seed collision.

All later steps were skipped: repository-wide fresh holdout geometry collision audit, exact-main seed/geometry proof, global ordinal proposal/guard, evidence upload, and Issue #60 terminal checkpoint. No preauthorization proof artifact or success marker was produced by the failed run.

A temporary metadata-only observer PR #346 independently identified the unique target run and the failing step, then was closed unmerged. Observer run `32690302348` produced artifact `9507033546` with GitHub digest `sha256:e31c2276d626f3c29979781edc79034f6df826b2ba131e161fde26576b310e8e`. The observer performed no scientific runtime, solver, ordinal allocation, seed reservation, authorization, dispatch, rerun/retry/resume, holdout opening, or Issue #60 write.

## Preserved boundary

The failed run allocated no scientific ordinal, reserved no scientific seed, created no authorization document, created no dispatch identity, installed no scientific runtime, invoked no syntax check or solver, and opened no holdout or other scientific result. Scientific ordinal 39 therefore remains unallocated.

This recovery changes no frozen physics, 8-geometry holdout source, 5-state/3-replicate/120-case universe, seed derivation, training-selected model, evaluator, acceptance threshold, runtime binding, or future transport. It does not relax the two-pass repository-global stability requirement.

After this evidence-only file is merged, repository writes must stop until the new exact-main preauthorization attempt reaches terminal state. A successful fresh attempt must still prove deterministic 24-seed identity, exact tracked-tree and repository-global seed freshness, stable double enumeration, zero seed collisions, repository-wide zero holdout-geometry collisions, latest consumed ordinal 38, and fresh next global ordinal 39 before any separate authorization proposal may be created.
