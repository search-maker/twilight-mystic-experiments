# STAR VISIBILITY / MYSTIC — LIVE HANDOFF CHECKPOINT

**Checkpoint: 2026-08-27, after AVPS post-consumption recovery attempt 2 failed closed and the recovery was split into two reviewed stages.**

This checkpoint supersedes `HANDOFF_LIVE_CHECKPOINT_2026-08-27_PRE_AVPS_RECOVERY2.md` for the live AVPS ordinal-40 control state. The older full project handoff remains useful for broader scientific context, but this file is authoritative for the current recovery sequence.

## 1. Live immutable scientific/control identity

Repository: `search-maker/twilight-mystic-experiments`.

Live `main` remains:
- `99ade7798627e67921139697ba1a004fa8a304bb` (PR #563 merge).

Authorization remains:
- PR #565 Draft/open/unmerged;
- authorization head `338ee82c8e088e929f45782b1f7ac1c3aaaaa533`;
- authorization parent/main `99ade7798627e67921139697ba1a004fa8a304bb`;
- authorization review run `33113256151`, attempt 1 SUCCESS;
- authorization review artifact ID `9663887142`, digest `sha256:3edff7740ca35832bbca0cfcba096aa3d9963d9b6c19044d867a2b3c9f09a47c`;
- preauthorization run `33111875371`, attempt 1 SUCCESS;
- preauthorization artifact ID `9663132186`, digest `sha256:1253612ffe4ba228e319f6b063256abd7340d11eec76981db4cc39a3619b2df6`.

Ordinal 40 is already allocated and consumed exactly once. Issue 60 has exactly one reviewed allocation marker and exactly one `ORDINAL40_AVPS_V1_DISPATCH_CONSUMED` marker. Never allocate, reuse, retire, or re-consume ordinal 40.

Dispatch branch remains:
- `dispatch/aerosol-vertical-profile-sensitivity-v1-ordinal-40`
- head `338ee82c8e088e929f45782b1f7ac1c3aaaaa533`.

As of the latest recovery-control audit there are zero AVPS science runs on that dispatch branch and no scientific result payload has been opened.

## 2. Publisher/recovery failure history — all immutable

### Original publisher — run 33114653044

- request head `8708a0f8a2fa86c5c13b27c94517552b0bf7dc2a`;
- attempt 1 FAILURE;
- actual dispatch push succeeded;
- consumed marker was posted exactly once;
- failure occurred in `Mark consumed once and prove post-dispatch state` because the generic failed-authorization-history helper rejected the now-legitimate consumed marker;
- immutable publisher evidence upload and science dispatch were skipped;
- preserved at `history/avps-v1-dispatch-publisher-ordinal-40-failed-after-consume-1`.

Exact historical step boundary from GitHub:
- `Bind request, authorization, preauthorization and zero-runtime review`: success;
- `Prove dispatch eligible before creating ref`: success;
- `Actual git push consumes dispatch identity`: success;
- `Mark consumed once and prove post-dispatch state`: failure;
- `Stage immutable successful publisher evidence`: skipped;
- `Persist immutable publisher evidence before science trigger`: skipped;
- `Explicitly dispatch attempt-1 science on pushed ref`: skipped.

### Recovery attempt 1 — run 33117461748

- status request head `00805a95dd1d179b544bf8f531a8ed726cf2d0c1`;
- attempt 1 FAILURE;
- failed at the first substantive bind with `KeyError: 'AUTH_PARENT'` because request variables were sourced but not exported before embedded Python read `os.environ`;
- no dispatch push/marker/evidence/science boundary crossed;
- preserved at `history/avps-v1-post-consumption-publisher-recovery-failed-1`.

### Recovery attempt 2 — run 33119177406

- request head `4864aa2e7f92ace0b5ea05beb76174508abbd053`;
- attempt 1 FAILURE;
- the #568 export correction and live run-name correction both passed;
- authorization/preauthorization binding passed;
- failed while proving original publisher history because the reviewed recovery used the stale historical step string `Perform actual git push that consumes dispatch identity` instead of the actual GitHub step name `Actual git push consumes dispatch identity`;
- all later state proof, evidence upload, and science dispatch steps were skipped;
- no science run started;
- preserved at `history/avps-v1-post-consumption-publisher-recovery-failed-2`.

Never GitHub Re-run any of these failed publisher/recovery runs. Any future transition must use a fresh reviewed request head and a new attempt-1 push identity.

## 3. Recovery template review history

### PR #567

Draft/open/unmerged immutable review evidence for inactive template v1. Head `b606dbda29c7beaa58c9bb176d436412ddc0f29e`; reviewed template blob `3470a0d6d2620d43c4c841f17d50d32eb9941ec4`; contract run `33116868465` SUCCESS. Do not activate.

### PR #568

Draft/open/unmerged immutable review evidence for inactive template v2. Head `4837ee4666b5ae9833e2854f89abf83e95994522`; reviewed template blob `a7bc9b36a6a5f064e06adff2ad130503e2044b58`; contract run `33118692013` SUCCESS. It fixed request-variable export and GitHub live publisher run-name binding. Activation became run `33119177406` and failed only on the stale historical step-name binding. Do not reactivate.

### PR #569

`Review AVPS post-consumption recovery template v3 exact step binding`.

- Draft/open/unmerged; keep as immutable review evidence only;
- head `f980458e646c91ad112ed8a7d8114986e50bcb92`;
- contract run `33119530132`, attempt 1 SUCCESS;
- based exactly on #568 reviewed head;
- corrects the original historical push step to `Actual git push consumes dispatch identity` and regression-freezes the audited original publisher boundary.

**DO NOT ACTIVATE #569 AS WRITTEN.** A pre-activation audit found a downstream blocker in the frozen science workflow itself.

## 4. Newly discovered downstream science-preflight blocker

Frozen science workflow at the authorization/dispatch head:
- path `.github/workflows/avps-v1-science.yml`;
- Git blob `55f48bbdf99aac58a96bd96f6735a4e56b8b466a`.

Before solver/runtime case execution, its step `Build live pre-solver seed proof and one-use science guard` calls:

`preauthorization_surface.build_dispatch_surface(..., post_dispatch=True)`.

That generic surface path enters the same failed-authorization-history logic that rejects any consumed marker. Ordinal 40 now legitimately has exactly one consumed marker. Therefore a recovered publisher that simply dispatched the unchanged science workflow is expected to produce a science run that fails pre-solver on the same `GlobalOrdinalRefusal: ordinal 40 already has consumed marker` class of bug.

This is a control-plane admission defect, not a change in the scientific experiment and not a scientific result.

## 5. PR #570 — authoritative two-stage recovery contract

PR #570: `Freeze AVPS ordinal-40 two-stage post-consumption recovery contract`.

- Draft/open/unmerged; review evidence only;
- base/main `99ade7798627e67921139697ba1a004fa8a304bb`;
- head `f1588592725fd31c9bf6b653557fd5ce2b108e01`;
- changed files are review JSON evidence/contract plus regression tests only;
- contract run `33120120487`, attempt 1 SUCCESS.

It binds frozen execution-contract Git blob:
- `230874923004115ff21f218bb0ce4d2e038d3a98`.

Frozen science remains:
- 360 exact cases;
- 72 CRN groups;
- five vertical-profile states/group;
- 24 analysis cells;
- four primary contrasts;
- field factor `F=3.14`;
- `20,000,000` photon histories/case;
- 4 shards × 90 cases;
- max 8 concurrent case jobs;
- no retry/resume/GitHub rerun;
- OPAC archive SHA-256 `11daa1f1f4be0fd4ddf7e881ec2005498049674a1540d37b4b1e8f5e16052c7e`, size `743391266`;
- frozen uvspec/runtime identities;
- existing analysis and result-opening rules;
- no Taylor/Jerusalem scoring or fitting.

### Stage A — publisher-evidence-only recovery

Purpose: create exactly one successful zero-runtime publisher receipt for the already-consumed ordinal, without repeating consumption and **without triggering science**.

Required permissions are read-only:
- actions: read;
- contents: read;
- issues: read;
- pull-requests: read.

Forbidden in Stage A:
- actions write;
- contents/issues write;
- git push;
- Issue-60 POST;
- science workflow dispatch;
- new ordinal/seeds;
- scientific runtime/solver.

It must prove:
- exact one allocation marker;
- exact one consumed marker;
- dispatch head == authorization head;
- all prior publisher runs are terminal attempt-1 failures;
- zero prior AVPS science runs;
- exact authorization-review/preauthorization evidence;
- then persist a zero-runtime publisher/recovery receipt with no second consumption and no science trigger.

### Stage B — separate science-preflight recovery

Only after Stage A successful evidence exists, implement a separately reviewed one-shot science-preflight recovery transport. It may repair only the broken consumed-state admission proof, replacing the generic failed-history path with an explicit exact-one-consumed-state proof.

Stage B must bind and preserve every scientific source/input/seed/case/F/runtime/analysis/result-opening identity. It may not create another ordinal, seed allocation, dispatch push, or consumed marker.

## 6. Immediate next action

1. Implement Stage A **first** as an inactive reviewed template, not an active workflow.
2. Review it with full CI and freeze its exact template blob.
3. Only after green review, build a fresh activation chain from live main that changes the active publisher path to that exact reviewed Stage-A blob and adds one fresh recovery request.
4. Trigger a fresh attempt-1 status push.
5. Stage A success must end after immutable publisher/recovery evidence; **no science dispatch exists in Stage A**.
6. Then design/review Stage B separately against the frozen science workflow and exact execution contract.
7. Results remain closed until eventual science execution completes and the exact-360 aggregate guard verifies every case/hash/runtime/8001-node product and the separate result-opening gate passes.

## 7. Global rule

This recovery exists only to repair orchestration/control admission around an already-authorized, already-consumed frozen experiment. Do not change aerosol profiles, AOD, OPAC optics, seeds, case universe, photon budget, Level-B mapping, F, Taylor/Jerusalem comparison, or acceptance thresholds in order to make recovery work.
