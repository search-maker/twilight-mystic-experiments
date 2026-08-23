# AFPF v1 preauthorization metadata-instability recovery

This file records a zero-runtime control-plane failure and intentionally triggers a fresh main-bound preauthorization attempt after merge.

## Failed exact-main attempt

- exact main: `1b4a78bfd7bc416d0a42fd99251a95f0a120f8a0`
- workflow: `AFPF v1 fresh preauthorization audit`
- run: `32667188805`
- attempt: `1`
- job: `97262352641`
- conclusion: `failure`
- failing step: `Stable repository-global authorization-time candidate-seed recheck`
- exact terminal refusal: `snapshot-fenced repository-global metadata changed between two complete enumerations; refuse this audit and start a fresh attempt-1 workflow run`

All preceding checks in that run passed: exact attempt-1 main/zero-runtime surface and exact tracked-tree candidate-seed scan. All later steps were skipped. No preauthorization proof artifact or Issue 60 success marker was produced by the failed run.

## Preserved boundary

The failed run allocated no scientific ordinal, created no authorization document, created no dispatch identity, installed no scientific runtime, invoked no syntax check or solver, and opened no scientific results. The next global ordinal remains proposal-only until a fresh exact-main preauthorization attempt succeeds and is independently verified.

This recovery changes no frozen physics, case universe, seed derivation, analysis rule, runtime binding, publisher contract, or science transport. After this file is merged, repository writes must stop until the new exact-main preauthorization attempt reaches a terminal state.
