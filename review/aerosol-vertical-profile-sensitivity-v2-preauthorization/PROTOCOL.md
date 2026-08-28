# AVPS v2 preauthorization / global-ordinal audit

Status: **REVIEW ONLY / AUTHORIZATION-TIME RECHECK / NO ORDINAL ALLOCATION / NO SOLVER**

## Purpose

This gate follows the fully reviewed replacement scientific preregistration (#597) and the artifact-only candidate-seed freshness review (#598). It performs the mandatory fresh repository-global checks immediately before any separate authorization review is allowed to allocate a scientific ordinal.

It does **not** allocate an ordinal, apply a candidate seed to a case, create an authorization/dispatch identity, invoke libRadtran, or open results.

## Frozen predecessor evidence

- frozen `main`: `99ade7798627e67921139697ba1a004fa8a304bb`
- #597 final head: `2bba54c6e78ed99d169887eef51d0c88d812b6f1`
- #597 dedicated review: `33193778176` attempt 1 SUCCESS
- #597 repository contract: `33193778174` attempt 1 SUCCESS
- #597 artifact: `9694863701`, digest `sha256:7de79aa4d8d9b51ad8ca4b1bdaceedae7ee5df17b3dd79c43c21cdaf9ae9a171`
- #597 skeleton canonical SHA-256: `a8d2d8f59aec01d82d8d98672152d00c11261660b0a69a59e2716c2edabd2b02`
- #598 head: `64e7d68bd876a99aa5af49d97bcb53718238b39b`
- #598 dedicated seed-freshness review: `33194319669` attempt 1 SUCCESS
- #598 repository contract: `33194319698` attempt 1 SUCCESS
- #598 artifact: `9695260362`, digest `sha256:fb4613d654121098c9d247d6ed8b0f0788b26a179b5ff103dc01ed7d50c9f0db`
- candidate seed count: `72`
- candidate-seed canonical SHA-256: `02f624d582e9b2caba6b920d65a5e8a8bc8fc1a2693623bc2f73abf5d3f706d2`
- candidate-row canonical SHA-256: `41f70d6a0381db6b569d3f4e17d74bb38b05cf212c2f2e432455a502f73dc670`

The actual 72 candidate seed values remain artifact/workspace-only and must not be committed, copied into the PR body, or applied to cases here.

## Required checks

1. require this PR to remain Draft/open/unmerged and based on the frozen main;
2. prove this branch descends from the exact #598 head and that the #597/#598 scientific/seed files are byte-identical to their reviewed heads;
3. re-derive the exact 72 candidate values in the workspace only;
4. repeat the exact tracked-tree candidate-literal scan and require zero tracked candidate seed literals;
5. run the bound two-pass repository-global scanner in `authorization-recheck` mode and require zero historical or post-fence candidate collisions;
6. require exactly the already-frozen #598 seed-review proof artifact as prior seed-review evidence;
7. use the already-reviewed conservative repository-global scientific-ordinal observation parser to inspect authorization/dispatch branches, runs, PR heads, artifacts, exact Issue #60 allocation/consumption markers, and positive prose claims;
8. require the latest exact consumed ordinal and the maximum authoritative observed ordinal to remain the same currently consumed value; if any later scientific identity has appeared, fail closed and start a fresh reviewed identity rather than guessing or reusing;
9. require the proposed AVPS-v2 authorization and dispatch branches for the next ordinal to be absent;
10. repeat the ordinal observation audit immediately before artifact upload/checkpoint publication and require the canonical observation surface to be unchanged.

At the checkpoint that caused this review to be opened, ordinal 40 was the latest consumed and maximum authoritative observed ordinal, so 41 is the expected next value. This statement is not an allocation or reservation; the workflow must freshly prove it again.

## PASS meaning

PASS means only:

- candidate seeds remain fresh at this authorization-time review checkpoint;
- the global ordinal surface remains clean;
- a separately reviewed authorization PR may next be constructed using the reported next available ordinal and the artifact-only candidate ledger.

PASS does **not** allocate that ordinal and does **not** authorize scientific execution.

## Hard prohibitions

- no `uvspec`, DISORT, MYSTIC, or NULL solver;
- no candidate seed values tracked in Git or Issue/PR prose;
- no `authorization.json` creation;
- no authorization or dispatch branch creation;
- no Issue #60 allocation/consumption marker;
- no reuse of ordinal 40 or any v1 case/seed identity;
- no Taylor/Jerusalem scoring or residual-guided choice;
- no Level-B/production action;
- no GitHub Re-run if this attempt fails.
