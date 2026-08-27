# LIVE HANDOFF CHECKPOINT — AVPS ORDINAL 40 STAGE A v3 REVIEW PENDING

**2026-08-27. This checkpoint supersedes `HANDOFF_LIVE_CHECKPOINT_2026-08-27_AVPS_STAGE_A_V2_REVIEW_PENDING.md` for the immediate AVPS ordinal-40 recovery state.**

Global science remains frozen: no Taylor/Jerusalem fitting, F=3.14, no new ordinal/seed allocation, no scientific-input changes, no manual MYSTIC, no result opening before exact aggregate gates.

## Frozen identity

- live `main`: `99ade7798627e67921139697ba1a004fa8a304bb`;
- authorization PR #565: Draft/open/unmerged, head `338ee82c8e088e929f45782b1f7ac1c3aaaaa533`;
- dispatch branch: `dispatch/aerosol-vertical-profile-sensitivity-v1-ordinal-40` at the same auth head;
- Issue 60 contains exactly one AVPS ordinal-40 allocation marker and exactly one consumed marker;
- dispatch branch still has zero workflow/science runs;
- no AVPS solver run or scientific result opening has occurred.

## Authoritative two-stage contract — #570

Draft PR #570 remains immutable review evidence:

- head `f1588592725fd31c9bf6b653557fd5ce2b108e01`;
- review run `33120120487`, attempt 1 SUCCESS;
- Stage A = strictly read-only publisher-evidence-only recovery;
- Stage B = separately reviewed science-preflight recovery only after Stage A success;
- exact frozen science blocker status: `FROZEN_SCIENCE_WORKFLOW_EXPECTED_TO_REFUSE_PRE_SOLVER_ON_LEGITIMATE_CONSUMED_MARKER`;
- frozen `avps-v1-science.yml` blob: `55f48bbdf99aac58a96bd96f6735a4e56b8b466a`.

#570 freezes the original three publisher/recovery failures that existed when the contract was written.

## Stage A v1 activation failure is now a fourth immutable publisher failure

Stage-A v1 activation head:

`d1f40af924b2228534f4d9701b6e83e6d8c9d250`

Run/job:

- run `33121394201`, attempt 1, failure;
- job `98688849337`, failure;
- failed step: `Bind reviewed Stage-A request and recovery contracts`;
- later Stage-A evidence steps all skipped;
- Actions artifacts: zero;
- no science endpoint existed in that Stage-A workflow.

History ref:

`history/avps-v1-stage-a-publisher-evidence-recovery-failed-1`

points exactly to `d1f40af924b2228534f4d9701b6e83e6d8c9d250`.

## #572 is green but MUST NOT be activated

Draft PR #572:

- head `007dbf8153eade043643f6863cf13fcebc04e94a`;
- contract review run `33121901374`, attempt 1 SUCCESS;
- reviewed template blob `d1b3c4cd40d2f7a5ea6695773fdef2b27839f271`;
- `Prove scientific execution remains unauthorized` passed.

However, final live pre-activation audit correctly found a new deterministic blocker: #572 reconstructs expected publisher history only from the three failures frozen in #570. The live publisher history now contains four prior failures because Stage-A v1 run `33121394201` occurred after #570 was frozen. Therefore activating #572 would fail on `prior publisher run set drift`. #572 was **not** activated after this discovery.

## #573 — Stage A v3 exact-four-failure review

Draft PR #573:

`Bind fourth fail-closed AVPS Stage A history`

Branch:

`review/avps-v1-ordinal40-stage-a-publisher-evidence-only-3`

Current exact head:

`352f226d87d570a7338bf2730872a7733179da74`

Relative to #572, only the same two inactive review files changed:

1. `.github/recovery-templates/avps-v1-stage-a-publisher-evidence-only-recovery.yml`
2. `tests/test_avps_v1_stage_a_publisher_evidence_only_recovery.py`

The v3 request schema is 4. It must bind the exact fourth Stage-A failure by run ID, job ID, head SHA and history ref. The template reconstructs the prior publisher universe as:

- the three exact failures frozen in #570;
- plus Stage-A v1 failure run `33121394201` / job `98688849337` / head `d1f40af...` / preserved history ref.

It requires exactly four unique prior publisher failures and no others, verifies each terminal attempt-1 failure, exact failed step, exact history ref and absence of successful publisher evidence, re-proves exactly one allocation marker + one consumed marker, exact dispatch head, and zero dispatch/science runs.

If all pass, it may emit only:

- `DISPATCH_PUBLISHED_ZERO_RUNTIME`;
- `POST_CONSUMPTION_PUBLISHER_RECOVERY_PASS_NO_SECOND_CONSUMPTION_NO_SCIENCE_TRIGGER`.

It remains read-only and contains no git push, Issue-60 POST, science workflow-dispatch endpoint, libRadtran/MYSTIC setup, solver, or result opening.

## #573 review status at checkpoint creation

Exact review run:

- run `33122607199`;
- attempt 1;
- workflow `.github/workflows/contract.yml`;
- job `98692968493`, `non-scientific-contract`;
- state at checkpoint creation: in progress.

Do not activate until this exact attempt-1 review is terminal SUCCESS including `Prove scientific execution remains unauthorized`.

## If #573 is green

Re-run live preflight. Then create a fresh two-commit activation chain directly from frozen main:

- R1: one-file change only, active `.github/workflows/avps-v1-dispatch-publisher.yml` -> exact reviewed #573 template blob;
- R2: one-file request change only, schema 4, binding #570, exact #573 PR/head/run, and exact fourth Stage-A failure run/job/head/history ref.

Compare main->R1 and R1->R2. Recheck main, #565/#570/#573 identities, markers, dispatch head, four exact prior publisher failures, zero successful ordinal-40 publisher artifact, zero dispatch/science runs. Only then move `status/avps-v1-dispatch-publisher-ordinal-40` once to R2 and permit one attempt-1 Stage-A publisher run.

No GitHub rerun of any failed run.

## Stage B architecture found by read-only audit

The frozen `science_guard.py` is already scientifically/control-wise correct once it receives a valid post-dispatch freshness surface. It independently requires:

- exact Draft/open/unmerged authorization PR;
- exact successful authorization review attempt 1;
- exact successful publisher attempt 1 with `DISPATCH_PUBLISHED_ZERO_RUNTIME`;
- exact one allocation marker and one consumed marker;
- zero-runtime publisher evidence;
- exact authorization/design/runtime bindings.

The blocker occurs **before** that guard succeeds: `preauthorization_surface.build_dispatch_surface(..., post_dispatch=True)` delegates to the generic AOPS control surface, which unconditionally calls AVPS `failed_authorization_history()`. That function rejects the legitimate current consumed marker with `GlobalOrdinalRefusal: ordinal 40 already has consumed marker`.

Therefore the narrow Stage-B repair, if Stage A succeeds, should be:

- do **not** change `science_guard.py`;
- do **not** change scientific cases/seeds/F/photon budget/runtime/result-opening rules;
- replace only the construction of the generic post-dispatch freshness surface with a recovery-specific exact-one-consumed-state proof;
- feed that recovered surface into the same frozen `science_guard.evaluate`;
- re-prove zero prior AVPS science/solver runs and exact Stage-A publisher receipt before solver.

This is consistent with #570's allowed repair: replace only the broken generic post-dispatch consumed-marker admission proof with an explicit exact-one-consumed-state recovery proof.
