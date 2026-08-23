# AFPF v1 preauthorization metadata-instability recovery

This file records zero-runtime control-plane failures and intentionally provides one additive main change from which a fresh exact-main preauthorization attempt may start after merge.

## Failed exact-main attempt 1

- exact main: `1b4a78bfd7bc416d0a42fd99251a95f0a120f8a0`
- workflow: `AFPF v1 fresh preauthorization audit`
- run: `32667188805`
- attempt: `1`
- job: `97262352641`
- conclusion: `failure`
- failing step: `Stable repository-global authorization-time candidate-seed recheck`
- exact terminal refusal: `snapshot-fenced repository-global metadata changed between two complete enumerations; refuse this audit and start a fresh attempt-1 workflow run`

All preceding checks in that run passed: exact attempt-1 main/zero-runtime surface and exact tracked-tree candidate-seed scan. All later steps were skipped. No preauthorization proof artifact or Issue 60 success marker was produced by the failed run.

## Failed exact-main attempt 2 after final science-transport hardening

- exact main: `90bfdd177f394d5065243f4fad6595a41ef66bf4`
- workflow: `AFPF v1 fresh preauthorization audit`
- run: `32669676567`
- attempt: `1`
- job: `97268441269`
- conclusion: `failure`
- failing step: `Stable repository-global authorization-time candidate-seed recheck`
- exact terminal refusal: `snapshot-fenced repository-global metadata changed between two complete enumerations; refuse this audit and start a fresh attempt-1 workflow run`

The second failure occurred after the exact-main/zero-runtime guard and tracked-tree candidate-seed scan both passed. The repository-global enumeration began at `2026-08-23T22:08:49Z` and refused at `2026-08-23T22:12:07Z` because the snapshot-fenced metadata was not stable across the two complete enumerations. No collision was reported, no seed was reused, and all proof/ordinal/allocation steps after the global scan were skipped.

A metadata-only observer subsequently confirmed exactly one matching preauthorization run for `90bfdd177f394d5065243f4fad6595a41ef66bf4`, run `32669676567`, attempt 1, completed with conclusion `failure`. The observer read no candidate seed values, scientific runtime, or scientific result artifacts and performed no rerun or retry.

## Preserved boundary

Neither failed run allocated a scientific ordinal, created an authorization document, created a dispatch identity, installed a scientific runtime, invoked a syntax check or solver, or opened scientific results. Scientific ordinal 38 therefore remains proposal-only and unallocated.

This recovery changes no frozen physics, case universe, seed derivation, analysis rule, runtime binding, publisher contract, or science transport. It does not relax the two-pass repository-global stability requirement. After this evidence file is merged, repository writes must stop until the new exact-main preauthorization attempt reaches a terminal state. A successful attempt must still prove exact tracked-tree and repository-global seed freshness, stable double enumeration, zero collisions, and a fresh next global ordinal before any authorization may be created.
