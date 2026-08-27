# LIVE HANDOFF CHECKPOINT — AVPS ORDINAL 40 STAGE A v2 REVIEW PENDING

**Timestamp context: 2026-08-27. This checkpoint supersedes `HANDOFF_LIVE_UPDATE_2026-08-27_AVPS_SCIENCE_PREFLIGHT_RECOVERY_REQUIRED.md` for the immediate AVPS recovery state while #572 review is pending. Read it together with `HANDOFF_CURRENT_2026-08-27_POST_PR557.md` and the reviewed two-stage contract in PR #570.**

All global scientific rules remain unchanged: no fitting to Taylor/Jerusalem, F=3.14, frozen 360-case / 72-CRN AVPS design, no new ordinal or seed allocation, no result opening, and no manual MYSTIC execution outside reviewed transport.

## Immutable scientific/control identity

- live `main`: `99ade7798627e67921139697ba1a004fa8a304bb`;
- authorization PR #565: Draft/open/unmerged, head `338ee82c8e088e929f45782b1f7ac1c3aaaaa533`;
- ordinal 40 remains allocated exactly once and consumed exactly once;
- dispatch branch `dispatch/aerosol-vertical-profile-sensitivity-v1-ordinal-40` remains at auth head `338ee82c8e088e929f45782b1f7ac1c3aaaaa533`;
- no AVPS science workflow run or solver execution has been authorized by Stage A;
- no AVPS scientific result payload has been opened.

## Authoritative recovery contract

Draft PR #570 remains the two-stage post-consumption recovery contract.

- head: `f1588592725fd31c9bf6b653557fd5ce2b108e01`;
- attempt-1 contract review run: `33120120487`, SUCCESS;
- Stage A: publisher-evidence-only recovery, read-only repository/control permissions, no science trigger;
- Stage B: separate science-preflight recovery only after successful Stage A evidence, with scientific inputs frozen and only the already-consumed control-plane admission repair allowed.

The exact frozen science blocker status in #570 is:

`FROZEN_SCIENCE_WORKFLOW_EXPECTED_TO_REFUSE_PRE_SOLVER_ON_LEGITIMATE_CONSUMED_MARKER`

The frozen science workflow remains blob `55f48bbdf99aac58a96bd96f6735a4e56b8b466a`; its current pre-solver `post_dispatch=True` surface is expected to reject the legitimate consumed marker through `GlobalOrdinalRefusal`. This remains a control-plane blocker, not a scientific/MYSTIC result.

## Stage A v1 review and activation failure

Draft PR #571 remains immutable review evidence.

- reviewed head: `8393e0253270a4895675b8ab0bfac16b501fd59e`;
- review run `33120837092`, attempt 1 SUCCESS;
- reviewed Stage-A template blob: `0bc9cea6c18e7df50c11992ca653e42a09873621`.

A fresh Stage-A activation chain was created from frozen main and activated at request head:

`d1f40af924b2228534f4d9701b6e83e6d8c9d250`

Publisher run `33121394201`, attempt 1, FAILED fail-closed in the first identity/binding step with:

`science blocker evidence drift`

Every later Stage-A evidence step was skipped. The workflow had only read permissions and no science-dispatch endpoint or solver, so this failure did not cross the science/runtime/result boundary.

The failed activation head is preserved at:

`history/avps-v1-stage-a-publisher-evidence-recovery-failed-1`

The exact cause is only a frozen-string mismatch: #571 expected stale status `FROZEN_SCIENCE_PREFLIGHT_EXPECTED_TO_REJECT_LEGITIMATE_CONSUMED_MARKER`, while #570 actually freezes `FROZEN_SCIENCE_WORKFLOW_EXPECTED_TO_REFUSE_PRE_SOLVER_ON_LEGITIMATE_CONSUMED_MARKER`.

## Stage A v2 review — PR #572

New Draft PR #572:

`Correct AVPS Stage A frozen blocker binding`

Exact current head:

`007dbf8153eade043643f6863cf13fcebc04e94a`

It is based exactly on #571 reviewed head and changes only the same two inactive review files. Relative to #571:

- Stage-A template: 2 additions / 2 deletions;
- regression test: 3 additions / 1 deletion.

The two runtime corrections are:

1. bind the exact #570 blocker status `FROZEN_SCIENCE_WORKFLOW_EXPECTED_TO_REFUSE_PRE_SOLVER_ON_LEGITIMATE_CONSUMED_MARKER`;
2. bind the new review branch `review/avps-v1-ordinal40-stage-a-publisher-evidence-only-2` rather than the immutable v1 review branch.

The regression test freezes both corrections and explicitly rejects the old v1 branch binding.

No active workflow, science source, seed, case, F, runtime identity, authorization, marker, dispatch ref, analysis rule, or result-opening rule is changed by #572.

## Review run currently in progress

Exact contract review run for #572 head `007dbf8153eade043643f6863cf13fcebc04e94a`:

- run `33121901374`;
- attempt `1`;
- workflow `.github/workflows/contract.yml`;
- job `98690542830`, `non-scientific-contract`;
- current state at checkpoint creation: in progress in `Run unit and artifact-audit tests`.

Do not prepare/activate a new Stage-A status ref until this exact attempt-1 review is terminal SUCCESS, including `Prove scientific execution remains unauthorized`.

## If #572 review is SUCCESS

1. Record exact terminal run/job result and exact reviewed v2 template blob.
2. Re-prove live main, #565/#570/#572 Draft/open/unmerged identities, exactly one allocation marker and one consumed marker, dispatch head identity, zero AVPS dispatch/science runs, and absence of an existing successful ordinal-40 publisher artifact.
3. Create a **fresh** R1 direct child of frozen main changing only `.github/workflows/avps-v1-dispatch-publisher.yml` to the exact #572 reviewed template blob.
4. Create a fresh R2 child changing only `.github/dispatch-requests/avps-v1.json`, binding #570 and exact #572 head/run.
5. Move the ordinal-40 status ref once to the fresh R2 and allow exactly one new attempt-1 Stage-A publisher-evidence run.
6. On success, verify immutable `DISPATCH_PUBLISHED_ZERO_RUNTIME` and `POST_CONSUMPTION_PUBLISHER_RECOVERY_PASS_NO_SECOND_CONSUMPTION_NO_SCIENCE_TRIGGER` evidence and re-prove zero science runs.
7. Only then begin separately reviewed Stage B science-preflight recovery.

## If #572 review or Stage A v2 activation FAILS

- preserve the exact failed head under a new history ref;
- inspect the exact fail-closed boundary;
- do not GitHub-rerun the failed run;
- do not mutate scientific inputs;
- do not dispatch science.

## Hard prohibitions remain

- no second allocation marker;
- no second consumed marker;
- no second dispatch-branch push;
- no new ordinal or seed allocation;
- no change to frozen `main` during ordinal-40 recovery;
- no rerun of prior failed publisher/recovery runs;
- no Stage B/science dispatch before successful Stage A evidence;
- no manual MYSTIC execution;
- no result opening before exact aggregate/hash/runtime/identity validation.
