# AVPS v2 recovery4 seed/global control trigger bridge v1

Status: **zero-runtime transport only / not activated / no scientific transition**.

## Purpose

The connected GitHub surface used by the autonomous worker can create repository refs/files/PRs but does not expose a direct `workflow_dispatch` action. The already-reviewed recovery4 repository-global control is intentionally manual and requires two exact inputs: current `main` and the matching Issue #60 `WRITE_QUIET_BEGIN` comment id.

This bridge provides only the missing GitHub-native transport. It does not perform seed selection, global scanning, ordinal derivation, authorization, dispatch-ref creation, solver work, result opening, Level-B admission, holdout access, or production change.

## Frozen target

- control workflow: `.github/workflows/avps-v2-recovery4-seed-global-control-v1.yml`
- reviewed control Git blob: `875bd21758a0ac0a2e2aed57bfc428df4e1e9578`
- activation branch: `control-trigger/aerosol-vertical-profile-sensitivity-v2-recovery4-seed-global-control-v1`
- activation marker: `control-triggers/avps-v2-recovery4-seed-global-control-v1.txt`

The activation marker is a one-file child of then-current `main` and must contain exactly:

```text
schema=AVPS_V2_RECOVERY4_SEED_GLOBAL_CONTROL_TRIGGER_V1
main=<exact then-current main>
controlWorkflow=avps-v2-recovery4-seed-global-control-v1.yml
controlBlob=875bd21758a0ac0a2e2aed57bfc428df4e1e9578
fenceBeginCommentId=<exact matching Issue #60 WRITE_QUIET_BEGIN comment id>
```

## Activation sequence

1. Before the fence, verify no relevant queued/in-progress/waiting/requested/pending repository workflow and no unmatched Issue #60 WRITE_QUIET.
2. Re-read newest Issue #60 immediately before posting the exact recovery4 `WRITE_QUIET_BEGIN` bound to current `main`.
3. Under that fence, create exactly one one-file activation child from the same `main` and publish only the exact activation branch above.
4. The bridge independently rebinds branch parent, single changed path, control blob, exact fence comment, absence of a prior matching END, repository workflow quiescence except itself, and absence of any prior workflow-dispatch run of the frozen control.
5. The bridge makes exactly one GitHub Actions API POST, targeting only the frozen control workflow on `main` with `expected_main_sha` and `fence_begin_comment_id` from the marker.
6. The frozen control rechecks quiescence and all global freshness invariants itself. Never GitHub Re-run/retry/resume either identity.
7. Close the matching Issue #60 fence immediately when the exact control run becomes terminal, regardless of PASS/FAIL, then classify the immutable result before any downstream action.

## Scientific boundaries

Recovery4 candidate seeds remain candidates until the frozen control proves repository-global zero collision. A PASS only derives the next unused global scientific ordinal; it does not allocate it and does not apply seeds. Frozen AVPS science remains 360 cases / 72 CRN groups / five profiles / 20,000,000 photons per case. Ordinals 41-44 remain consumed and non-reusable. Taylor/Jerusalem and invalidated low-altitude artifacts are excluded. Every richer OAS-v2 `newMappingAuthorized` flag remains `false`.
