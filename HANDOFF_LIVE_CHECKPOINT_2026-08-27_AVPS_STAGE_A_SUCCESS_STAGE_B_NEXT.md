# LIVE HANDOFF CHECKPOINT — AVPS ORDINAL 40 STAGE A SUCCESS; STAGE B NEXT

**2026-08-27. This checkpoint supersedes `HANDOFF_LIVE_CHECKPOINT_2026-08-27_AVPS_STAGE_A_V3_REVIEW_PENDING.md` for the immediate AVPS ordinal-40 recovery state.**

Global science remains frozen: no Taylor/Jerusalem fitting, F=3.14, no new ordinal/seed allocation, no scientific-input changes, no manual MYSTIC, no result opening before exact aggregate gates.

## Frozen identity

- live `main`: `99ade7798627e67921139697ba1a004fa8a304bb`;
- authorization PR #565: Draft/open/unmerged, head `338ee82c8e088e929f45782b1f7ac1c3aaaaa533`;
- dispatch branch `dispatch/aerosol-vertical-profile-sensitivity-v1-ordinal-40` remains at auth head `338ee82c8e088e929f45782b1f7ac1c3aaaaa533`;
- Issue 60 still contains exactly one ordinal-40 allocation marker and exactly one consumed marker;
- post-Stage-A live readback: dispatch branch has zero workflow runs;
- no AVPS science/solver/result-opening boundary has yet been crossed.

## Authoritative recovery contract — #570

Draft PR #570 remains immutable:

- head `f1588592725fd31c9bf6b653557fd5ce2b108e01`;
- review run `33120120487`, attempt 1 SUCCESS;
- Stage A = publisher-evidence-only recovery;
- Stage B = separately reviewed science-preflight recovery;
- allowed Stage-B repair: replace only the broken generic post-dispatch consumed-marker admission proof with an explicit exact-one-consumed-state recovery proof;
- frozen science workflow blob `55f48bbdf99aac58a96bd96f6735a4e56b8b466a`;
- scientific cases/seeds/F/photon budget/runtime/result-opening rules remain frozen.

## Stage A v3 review — #573

Draft PR #573 remains immutable review evidence:

- head `352f226d87d570a7338bf2730872a7733179da74`;
- reviewed Stage-A template blob `821cd234ffd1253905839834d1afeafa91bdcdfd`;
- contract review run `33122607199`, attempt 1 SUCCESS;
- contract job `98692968493`, SUCCESS;
- all gates passed including `Prove scientific execution remains unauthorized`.

## Stage A v3 fresh activation chain

Built without R1/R2 branch refs, directly from frozen main:

- R1 `c580002b0b30c9ee48a4bf7f88edd83c930e0044`: changes only `.github/workflows/avps-v1-dispatch-publisher.yml` to exact reviewed #573 template blob;
- R2 `14a2d1272d8e81383e0fb4f830fceef5647d985c`: child of R1, changes only `.github/dispatch-requests/avps-v1.json`, schema 4, binding #570/#573 and exact fourth Stage-A failure history.

`main -> R1` and `R1 -> R2` each proved a single-file delta.

The status ref was moved once to R2.

## Stage A v3 execution SUCCESS

Publisher run:

- run `33123226959`;
- attempt 1;
- job `98695045355`;
- head `14a2d1272d8e81383e0fb4f830fceef5647d985c`;
- conclusion **SUCCESS**.

All relevant steps succeeded:

1. exact Stage-A v3 request/contracts binding;
2. exact authorization/preauthorization evidence binding;
3. proof of four exact prior publisher failures, one consumption and zero science;
4. immutable Stage-A v3 receipt staging;
5. terminal immutable publisher evidence upload.

Immutable artifact:

- id `9667291127`;
- name `avps-v1-dispatch-publisher-ordinal-40`;
- GitHub digest `sha256:0338d418d554c5ceaead8712a1ee860c2ee154d839cfe7c038098607786a0b3f`;
- independently downloaded ZIP SHA-256 matched the GitHub digest exactly.

`dispatch-publisher.json` verified:

- status `DISPATCH_PUBLISHED_ZERO_RUNTIME`;
- run ID `33123226959`, attempt 1, success;
- prior failed publisher IDs `[33114653044, 33117461748, 33119177406, 33121394201]`;
- `actualGitPushPerformedByThisRun=false`;
- `currentConsumedMarkerPostedByThisRun=false`;
- `scienceTriggerMode=NONE_STAGE_A_EVIDENCE_ONLY`;
- science workflow dispatch/runtime/execution/solver all false.

`post-consumption-stage-a-recovery.json` verified:

- status `POST_CONSUMPTION_PUBLISHER_RECOVERY_PASS_NO_SECOND_CONSUMPTION_NO_SCIENCE_TRIGGER`;
- allocation marker count 1;
- consumed marker count 1;
- no repeated dispatch push;
- no repeated consumed marker;
- science-run count before/during Stage A = 0;
- science/runtime/solver all false.

Post-success live readback again confirmed one allocation marker, one consumed marker, and zero workflow runs on the AVPS dispatch branch.

**Stage A is complete.**

## Stage B narrow architecture

Read-only source audit shows the frozen `science_guard.py` is already the correct final authorization gate once it receives a valid post-dispatch freshness surface. It independently requires the exact authorization PR/review, exact successful publisher attempt 1 and `DISPATCH_PUBLISHED_ZERO_RUNTIME`, exact one allocation marker + one consumed marker, zero-runtime publisher evidence, and frozen design/runtime identities.

The blocker occurs earlier: `preauthorization_surface.build_dispatch_surface(..., post_dispatch=True)` delegates to the generic AOPS control surface, which calls AVPS `failed_authorization_history()`; that generic helper refuses the legitimate current consumed marker with `GlobalOrdinalRefusal: ordinal 40 already has consumed marker`.

Therefore Stage B must:

- leave `science_guard.py` unchanged;
- leave scientific cases/seeds/F/photon budget/runtime/result-opening unchanged;
- replace only the generic post-dispatch freshness construction with a recovery-specific exact-one-consumed-state proof;
- bind the successful Stage-A artifact id/digest/run/head exactly;
- prove exactly one allocation marker and one consumed marker and zero prior AVPS science/solver runs;
- feed the recovered freshness surface into the same frozen `science_guard.evaluate` before any runtime/solver setup;
- remain fail-closed on every identity/history discrepancy.

No Stage-B activation is permitted until its inactive implementation receives a fresh attempt-1 review proving the scientific execution remains unauthorized during review.
