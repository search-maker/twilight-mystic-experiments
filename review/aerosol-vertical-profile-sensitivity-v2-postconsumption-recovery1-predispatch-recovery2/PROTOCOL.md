# AVPS v2 post-consumption recovery1 pre-dispatch recovery2

Status: review-only, zero-runtime, no dispatch.

This package exists only because publisher run `33257846884` attempt 1 failed in the fresh pre-dispatch fence before dispatch publication or scientific execution. The failure was mechanical: the authorization-bound recovery seed ledger was copied out of its native repository path, so its `__file__`-relative repository-root lookup became invalid.

## Frozen identities

- current publication base: `a99f9181072755889cf3fae3f446e036a012f760`
- authorization PR: `#629`
- authorization head: `e627a689ada0493a8a5b9cdafc4aba0198fbabec`
- authorization parent: `a68f603d6da21cd28ab8324da080cc8ad27f9094`
- scientific ordinal: `42`
- execution key: `aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery1:numerical:42`
- recovery seed canonical SHA-256: `a514212990a94a39d577bd038b631a600e18e4c0f750f781bbd7c99b897228a7`
- frozen design: 360 cases, 72 CRN groups, five states, 20,000,000 photon histories per case
- published recovery science workflow SHA-256: `04a178e0cc777e0fc090c8bfc6175ad10b4bec56c6f12048428382ea36217878`
- original failed publisher run: `33257846884`, attempt 1, job `99114571607`

Ordinal 41 and its execution identity/seeds remain permanently consumed historical evidence and must never be reused.

## Only permitted recovery change

Recovery2 must validate the exact authorization-bound seed ledger from a detached checkout/worktree of `AUTH_HEAD`, at its native path:

`review/aerosol-vertical-profile-sensitivity-v2-postconsumption-seed-freshness-v1/seed_ledger.py`

This preserves the ledger's frozen `__file__`-relative root semantics. Recovery2 must not copy or relocate that Python source before calling `validate_ledger()`.

All scientific bytes, cases, geometry, aerosol states, photon counts, seeds, analysis rules, thresholds, result-opening rules, anti-fitting rules, authorization identity and recovery science workflow remain unchanged.

## Required pre-dispatch fence

Before any mutation, the recovery2 publisher must prove all of the following in one fresh attempt-1 run on `main`:

1. publisher run `33257846884` failed in `Fresh zero-runtime pre-dispatch fence`, while ref creation/consumed-marker, evidence upload and science-dispatch steps were skipped;
2. PR #629 remains open/Draft/unmerged at the exact authorization head/parent and its attempt-1 authorization review artifact remains valid;
3. Issue #60 contains exactly one ordinal-42 allocation marker and zero ordinal-42 consumed markers;
4. the ordinal-42 dispatch branch is absent and no recovery science `workflow_dispatch` run exists;
5. the detached authorization worktree is exactly `AUTH_HEAD`, the native recovery seed ledger has Git blob `491d1b6653bea0fcc5275269723a76aa1af52300`, and `validate_ledger()` yields exactly 72 seeds with canonical SHA-256 `a514212990a94a39d577bd038b631a600e18e4c0f750f781bbd7c99b897228a7` and zero overlap with consumed ordinal-41 seeds;
6. fresh tracked-tree and repository-global seed scans report zero collisions;
7. the already-published recovery science workflow remains byte-identical to the reviewed source and this recovery2 publisher is itself bound to a successful attempt-1 solver-free review receipt.

Only after every check passes may recovery2 create the exact dispatch ref pointing to `AUTH_HEAD`, post the exact consumed marker once, upload publisher evidence, and request the already-published recovery science workflow from `main`.

## Review/merge/activation separation

This PR is additive recovery infrastructure only. Its review workflow must be pull-request-only, attempt-1, read-only, and solver-free. Merging this PR alone must not create an activation marker, dispatch branch, consumed marker, workflow dispatch, scientific runtime, result opening, Level-B admission, protected-holdout access, Taylor/Jerusalem scoring, or production change.

After exact-head review and merge, trigger activation remains a separate one-file direct-child gate from the resulting exact `main`, with fresh live no-dispatch/no-consumption/no-science checks. No GitHub Re-run/retry/resume of failed publisher run `33257846884` is permitted.