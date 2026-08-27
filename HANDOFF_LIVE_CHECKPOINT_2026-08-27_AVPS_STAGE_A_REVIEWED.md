# STAR VISIBILITY / MYSTIC — LIVE HANDOFF CHECKPOINT

**Checkpoint: 2026-08-27, after green review of AVPS ordinal-40 Stage A publisher-evidence-only recovery, immediately before any Stage-A activation.**

This is the authoritative live AVPS recovery checkpoint. It supplements the broader project handoff and supersedes the previous pre-Stage-A immediate-action section.

## Frozen live identity

- Repo: `search-maker/twilight-mystic-experiments`
- Live main: `99ade7798627e67921139697ba1a004fa8a304bb`
- Authorization PR #565: Draft/open/unmerged
- Authorization head: `338ee82c8e088e929f45782b1f7ac1c3aaaaa533`
- Authorization parent: `99ade7798627e67921139697ba1a004fa8a304bb`
- Auth review run `33113256151`, attempt 1 SUCCESS
- Preauthorization run `33111875371`, attempt 1 SUCCESS
- Ordinal 40: allocated exactly once and consumed exactly once; never allocate/reuse/re-consume it
- Dispatch branch: `dispatch/aerosol-vertical-profile-sensitivity-v1-ordinal-40` at auth head `338ee82c...`
- No AVPS science run has been allowed to start; results remain closed.

## Immutable failure history

1. Original publisher `33114653044`, attempt 1 failure after actual dispatch push + consumed marker, before publisher evidence/science trigger. Exact successful historical push step: `Actual git push consumes dispatch identity`.
2. Recovery `33117461748`, attempt 1 failure at request bind because request vars were not exported before Python `os.environ` reads.
3. Recovery `33119177406`, attempt 1 failure while binding the original publisher history because the recovery used a stale historical step name. Its request head `4864aa2e7f92ace0b5ea05beb76174508abbd053` is preserved at `history/avps-v1-post-consumption-publisher-recovery-failed-2`.

All three failed before successful publisher-evidence upload and before AVPS science dispatch. Never GitHub Re-run them.

## Downstream science blocker

Frozen science workflow blob `55f48bbdf99aac58a96bd96f6735a4e56b8b466a` calls `preauthorization_surface.build_dispatch_surface(..., post_dispatch=True)` pre-solver. That generic admission path rejects the legitimate one consumed marker and would be expected to fail before solver if current science were dispatched unchanged.

Therefore recovery is split into two stages. Do not activate old template #569 as written.

## #570 — green two-stage recovery contract

PR #570 is Draft/open/unmerged review evidence.
- head `f1588592725fd31c9bf6b653557fd5ce2b108e01`
- contract run `33120120487`, attempt 1 SUCCESS
- frozen execution contract blob `230874923004115ff21f218bb0ce4d2e038d3a98`

Stage A must be read-only and only reconstruct the missing zero-runtime publisher receipt. Stage B is separate and may later repair only science-preflight consumed-state admission while every scientific source/input/seed/case/F/runtime/analysis/result-opening binding remains frozen.

Frozen science remains 360 cases / 72 CRN groups / 5 vertical states / F=3.14 / 20M photons per case / exact OPAC and runtime hashes / no retry-resume-rerun / no Taylor or Jerusalem fitting.

## #571 — green Stage A inactive-template review

PR #571: `Review AVPS Stage A publisher-evidence-only recovery`
- Draft/open/unmerged; never merge, preserve as review evidence
- base/main `99ade7798627e67921139697ba1a004fa8a304bb`
- head `8393e0253270a4895675b8ab0bfac16b501fd59e`
- changed exactly two files: inactive recovery template + regression test
- reviewed template Git blob `0bc9cea6c18e7df50c11992ca653e42a09873621`
- contract run `33120837092`, attempt 1 SUCCESS

Stage A permissions are strictly:
- actions: read
- contents: read
- issues: read
- pull-requests: read

Stage A contains no git push, no Issue-60 POST, no actions write, no science workflow-dispatch endpoint, no uvspec/MYSTIC/libRadtran execution, and no workflow step after the immutable publisher/recovery artifact upload.

It binds:
- #570 exact contract head/run
- #571 exact review head/run
- #565 exact authorization identity
- auth-review/preauthorization artifacts + digests
- exactly one allocation marker and one consumed marker
- dispatch head == authorization head
- all three prior publisher/recovery failures + preserved history refs
- zero workflow runs on the AVPS dispatch branch before Stage A.

Stage-A receipt status is `DISPATCH_PUBLISHED_ZERO_RUNTIME`; recovery status is `POST_CONSUMPTION_PUBLISHER_RECOVERY_PASS_NO_SECOND_CONSUMPTION_NO_SCIENCE_TRIGGER`. Receipt fields were checked against the frozen AVPS science guard publisher requirements.

## Immediate next action

Before activation, re-read live main, #565, #570, #571, Issue-60 markers, status/history refs, dispatch head, and dispatch-branch run count. If and only if they match this checkpoint:

1. build fresh R1 direct child of live main changing only `.github/workflows/avps-v1-dispatch-publisher.yml` to exact reviewed blob `0bc9cea6...`;
2. build fresh R2 child changing only `.github/dispatch-requests/avps-v1.json`, schema 3, binding ordinal 40 + #565 + #570 run/head + #571 run/head;
3. verify R1 and R2 one-file diffs;
4. force-move `status/avps-v1-dispatch-publisher-ordinal-40` to fresh R2, creating a new push-triggered attempt-1 run; never use GitHub Re-run;
5. Stage A success must stop after immutable publisher evidence. Verify exactly one successful publisher run/artifact now exists and zero AVPS dispatch/science runs still exist;
6. only after that success may Stage B review begin.

Results remain closed until a later separately reviewed Stage B enables the frozen science transport, all 360 cases complete, exact aggregate validation passes, and the separate result-opening gate authorizes opening.