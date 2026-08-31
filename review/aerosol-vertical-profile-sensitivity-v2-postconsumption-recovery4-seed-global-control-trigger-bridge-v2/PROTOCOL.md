# AVPS v2 recovery4 seed/global control trigger bridge v2

Status: **zero-runtime mechanical correction only / not activated / no scientific transition**.

## Purpose

The first reviewed GitHub-native bridge activation failed closed in run `33346256519` before the target control was dispatched. Issue #60 END `5472447982` established the exact mechanical cause: bridge v1 reconstructed open WRITE_QUIET fences from durable Issue #60 history but recognized matching END references only in the modern `begin=<id>` form. Historical already-closed fences also use `beginComment=<id>` and `begin_comment=<id>`, so v1 falsely classified those historical fences as still open.

This v2 bridge changes only that historical-ledger compatibility. It does not change Recovery4 candidate seeds, frozen AVPS science, the target repository-global control workflow, ordinal logic, authorization, dispatch, result opening, Level-B admission, holdouts or production.

## Frozen target

- target control workflow: `.github/workflows/avps-v2-recovery4-seed-global-control-v1.yml`
- exact reviewed target control Git blob: `875bd21758a0ac0a2e2aed57bfc428df4e1e9578`
- fresh activation branch: `control-trigger/aerosol-vertical-profile-sensitivity-v2-recovery4-seed-global-control-v2`
- fresh activation marker: `control-triggers/avps-v2-recovery4-seed-global-control-v2.txt`
- fresh activation schema: `AVPS_V2_RECOVERY4_SEED_GLOBAL_CONTROL_TRIGGER_V2`

The old activation head `24a6ed4b5d6bc15793162cc3b15df6bb70e9ab97` and run `33346256519` are immutable failed attempt-1 evidence and may never be rerun, retried, resumed or reused.

## Exact fence-history correction

For a comment whose body begins `WRITE_QUIET_END`, bridge v2 recognizes an intended matching BEGIN only from one of these exact durable key forms:

- `begin=<id>`
- `beginComment=<id>`
- `begin_comment=<id>`

If an END contains conflicting identifiers, the bridge fails closed. If an END has no recognized identifier, it does not close any BEGIN. Ordinary comments containing those tokens do not close a fence. After replaying the complete paginated Issue #60 history, the only allowed unmatched BEGIN immediately before dispatch is the exact new Recovery4 global-control fence supplied by the activation marker.

The review fixture must prove all three historical END forms close their intended BEGIN and that a genuinely unmatched BEGIN remains open.

## Activation sequence after merge

1. Verify repository/workflow quiescence and no unmatched Issue #60 WRITE_QUIET.
2. Fresh-read Issue #60 immediately before mutation and post one new exact `WRITE_QUIET_BEGIN | AVPS_V2_RECOVERY4_SEED_GLOBAL_CONTROL_V1 | main=<then-current-main>`.
3. Create exactly one fresh one-file activation child from that same main on the v2 activation branch with exactly:

```text
schema=AVPS_V2_RECOVERY4_SEED_GLOBAL_CONTROL_TRIGGER_V2
main=<exact then-current main>
controlWorkflow=avps-v2-recovery4-seed-global-control-v1.yml
controlBlob=875bd21758a0ac0a2e2aed57bfc428df4e1e9578
fenceBeginCommentId=<exact matching Issue #60 WRITE_QUIET_BEGIN comment id>
```

4. Bridge v2 rebinds exact parent/main, one changed marker path, target control blob, complete Issue #60 fence history, workflow quiescence and absence of any prior target workflow_dispatch run.
5. It repeats those checks immediately before making exactly one Actions API POST to the frozen target control.
6. Never GitHub Re-run/retry/resume either bridge or target-control identity.
7. Close the matching fence immediately when the target control reaches terminal state, then classify immutable evidence before any downstream transition.

## Scientific boundaries

Recovery4 72 candidate seeds remain unapplied/unconsumed until the frozen target control proves live repository-global zero collision. A target-control PASS may dynamically derive the next unused global scientific ordinal but does not allocate it. Frozen AVPS science remains exactly 360 cases / 72 CRN groups / five independently defined profiles / 20,000,000 photons per case. Ordinals 41-44 remain permanently consumed. Taylor/Jerusalem and invalidated low-altitude evidence are excluded. Every richer OAS-v2 `newMappingAuthorized` remains `false`.
