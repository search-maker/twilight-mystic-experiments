# AVPS v2 post-consumption recovery2 — dynamic preauthorization review

## Purpose

This is a solver-free review gate after AVPS v2 scientific ordinals 41 and 42 were both consumed by structural pre-runtime failures. It does not allocate a scientific ordinal and does not authorize execution.

The gate binds the fresh 72-group recovery2 candidate seed identity already reviewed by PR #639 and proof artifact `9717283554` (`sha256:0295c1e76e68f4436430a7b01bce5fa1138c15cb4a4061cd227c56620a00b89a`). The candidate seed canonical SHA-256 is `38c074fe01bd6d09fa7dc78af1ad323e2f42b606ca992c2950b8fc1f5b343a9f`; the candidate row canonical SHA-256 is `a88b28dcfaaeb354f294d1705a0f8ddbcd061083f277a038ab8c9dace44d9954`.

## Frozen consumed boundary

- ordinal 41 and its scientific run `33236295233`, dispatch identity, authorization identity, and 72 seeds remain permanently consumed;
- ordinal 42 and its scientific run `33259899524`, dispatch identity, authorization identity, and 72 seeds remain permanently consumed;
- neither failed run may be rerun, retried, resumed, or reused;
- the recovery2 candidate seed set must overlap neither consumed seed set.

The ordinal-42 historical seed ledger is validated only at its native path in a detached worktree of authorization head `e627a689ada0493a8a5b9cdafc4aba0198fbabec`; relocation-based execution is forbidden.

## Review procedure

The pull-request workflow must:

1. bind exact base main, exact branch/head, and exact three-file review scope;
2. verify PR #639's exact-head successful seed-freshness run and proof artifact identity;
3. create a detached ordinal-42 authorization-head worktree and bind the historical seed ledger at its native path;
4. deterministically rebuild the same 72 recovery2 candidate seeds without tracking seed values in Git;
5. repeat exact tracked-tree and repository-global collision checks under a WRITE_QUIET snapshot fence;
6. use the already-reviewed global scientific-ordinal parser to observe all authoritative occupied ordinals;
7. require ordinals 41 and 42 to remain exactly consumed and dynamically propose only `max(observed)+1` as the next available ordinal;
8. refuse if the proposed recovery2 authorization/dispatch branch or an exact-looking Issue #60 marker already exists;
9. freeze an artifact proving the seed and ordinal surfaces; and
10. perform a final repository-global ordinal/head recheck before success.

## PASS meaning

PASS means only that a later, separately reviewed authorization allocation may use the reported next ordinal and the exact recovery2 candidate seed identity. It does **not** create or merge an authorization, create a dispatch ref, apply seeds to cases, execute libRadtran/MYSTIC/uvspec, open AVPS results, admit vertical-profile or richer atmosphere inputs into Level-B, access a protected holdout, use Taylor/Jerusalem residuals, or change production behavior.

No next ordinal is hard-coded in this package. Any later authorization must consume the exact preauthorization proof and must recheck freshness immediately before allocation/dispatch.
