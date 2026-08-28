# LIVE HANDOFF CHECKPOINT — AVPS STAGE A COMPLETE / STAGE B REVIEW

**Timestamp context: 2026-08-27. This supersedes earlier AVPS Stage-A pending/failure checkpoints for the live ordinal-40 recovery state. Read together with `HANDOFF_CURRENT_2026-08-27_POST_PR557.md`.**

All scientific anti-fitting rules remain unchanged. No Taylor/Jerusalem residual may select atmospheric/scientific parameters. AVPS remains the independently preregistered vertical aerosol profile sensitivity program: 360 cases, 72 CRN groups, 5 states/group, F=3.14, 20,000,000 photon histories/case, exact frozen OPAC/libRadtran/runtime/seed/case identities.

## Immutable scientific identity

- frozen recovery main/authorization parent: `99ade7798627e67921139697ba1a004fa8a304bb`
- authorization PR #565: Draft/open/unmerged
- authorization head: `338ee82c8e088e929f45782b1f7ac1c3aaaaa533`
- authorization JSON blob: `91c2fcfe0536f7289b9da3c597428c546523571a`
- authorization branch: `authorization/aerosol-vertical-profile-sensitivity-v1-ordinal-40`
- dispatch branch: `dispatch/aerosol-vertical-profile-sensitivity-v1-ordinal-40`
- authorization and dispatch refs remain at the exact same head `338ee82c8e088e929f45782b1f7ac1c3aaaaa533`
- exactly one Issue-60 AVPS ordinal-40 allocation marker exists
- exactly one `ORDINAL40_AVPS_V1_DISPATCH_CONSUMED` marker exists
- no second dispatch push or second consumed marker is permitted

## Stage A — COMPLETE

Two-stage recovery contract #570 remains Draft/open/unmerged as immutable review evidence:
- exact head `f1588592725fd31c9bf6b653557fd5ce2b108e01`
- review run `33120120487`, attempt 1, SUCCESS.

The final Stage-A review/activation evidence is Draft PR #573:
- title: `Bind fourth fail-closed AVPS Stage A history`
- exact reviewed head `352f226d87d570a7338bf2730872a7733179da74`
- exact reviewed Stage-A v3 template blob `821cd234ffd1253905839834d1afeafa91bdcdfd`
- review run `33122607199`, attempt 1, SUCCESS
- activation R1 `c580002b0b30c9ee48a4bf7f88edd83c930e0044`
- activation R2/status head `14a2d1272d8e81383e0fb4f830fceef5647d985c`
- Stage-A publisher run `33123226959`, attempt 1, job `98695045355`, SUCCESS
- Stage-A immutable artifact id `9667291127`
- artifact name `avps-v1-dispatch-publisher-ordinal-40`
- artifact digest `sha256:0338d418d554c5ceaead8712a1ee860c2ee154d839cfe7c038098607786a0b3f`

Stage-A receipt readback proves:
- `DISPATCH_PUBLISHED_ZERO_RUNTIME`
- no git push by the recovery run
- no consumed marker posted by the recovery run
- no science workflow dispatch
- no scientific runtime setup
- no scientific execution
- no solver execution
- exactly one allocation marker and one consumed marker
- `dispatchPushRepeated=false`
- `consumedMarkerRepeated=false`
- zero AVPS science through Stage A.

Therefore **Stage A is complete and must not be repeated**. Do not rerun old publisher attempts and do not move the old Stage-A status ref for a new recovery.

## Why Stage B is still required

The frozen original science workflow (`.github/workflows/avps-v1-science.yml`, blob `55f48bbdf99aac58a96bd96f6735a4e56b8b466a`) performs a pre-solver post-dispatch freshness construction. That path delegates into generic AVPS `failed_authorization_history()` written for the earlier failed-authorization reuse phase. It rejects the now-legitimate consumed marker/current dispatch branch before the frozen science guard can run.

This is a control-plane lifecycle mismatch, not a MYSTIC result and not a scientific-parameter defect.

The frozen science guard itself remains blob `c774be7ea8655854bb85071a9fb260e21498beda` and already requires the correct state: successful zero-runtime publisher evidence, exact auth/dispatch head, exactly one allocation marker, exactly one consumed marker, live seed proof, zero prior science, and frozen scientific identity.

## Stage B review — #574

Draft PR #574:
`Review AVPS Stage B consumed-state science recovery`

Exact current review head:
`9a3390d27963359c7c39b1762a1b8eec90e24185`

Base:
`main=99ade7798627e67921139697ba1a004fa8a304bb`

The branch adds exactly seven review/control files and modifies **zero existing files**. No frozen scientific source file is changed.

Exact review blobs:
- post-consumption helper: `efe771b21bd8c8ebbf9e4e998faff39b125af377`
- inactive Stage-B publisher template: `042727fc6efae85bf34b0a6868cb7e2e86a662e6`
- inactive Stage-B science template: `cb3735ab0529de79bd75bdb22d3391b8cf92e9f5`
- live Stage-B review workflow: `88d13f71520091b7becad615f278461248561160`

### Narrow repair rule

The Stage-B helper may replace only the `failed_authorization_history` subproof while constructing the post-dispatch surface. It must:
1. re-prove exact preserved failed head `67844e1dd2523963f2682f186387280dfb930760`;
2. re-prove closed/unmerged failed PR #561 and failed attempt-1 auth-review run `33109014744`;
3. prove the failed head itself never received an allocation marker and never ran AVPS science;
4. treat the current successful-head dispatch branch and exactly-one consumed marker as legitimate post-consumption state, not as evidence that the old failed head was used;
5. call the original bound control-surface builder;
6. restore the original helper;
7. call the unchanged `freshness.validate_dispatch(..., post_dispatch=True)`;
8. feed the recovered surface to the unchanged frozen `science_guard.py`.

The recovered surface must still require latest prior scientific ordinal 39, zero prior ordinal-40 science, zero execution-key use, zero unexpected positive ordinal claims, exact auth/dispatch heads, one allocation marker, one consumed marker, and a fresh live 72-seed repository-global recheck.

## Stage B result boundary is intentionally stricter

Even after a future successful Stage-B activation, the recovery transport may only execute the exact frozen 360 cases and produce raw case artifacts. It does **not** include `aggregate_results`, `open_results`, Level-B opening, or scientific interpretation.

If all 360 raw case artifacts are produced, the terminal Stage-B job may freeze only artifact metadata and must explicitly record that case contents/results remain unopened. Aggregate verification and result opening require a later separate review.

## Required checks before any Stage-B activation

#574 must remain Draft/open/unmerged. On its exact reviewed head, require both:
1. generic repository non-scientific contract CI, attempt 1 SUCCESS;
2. dedicated read-only `AVPS Stage B post-consumption surface review`, attempt 1 SUCCESS.

The dedicated live review must bind the exact Stage-A artifact/digest, live one-allocation/one-consumption state, exact auth/dispatch refs, zero prior AVPS science, fresh 72-seed repository-global proof, recovered surface construction, the unchanged post-dispatch validator, and a final proof that review itself started no science.

**Do not activate Stage B if either check fails.** Preserve the failed review head and repair only the demonstrated control defect.

## Future activation shape only after both reviews are green

Re-read all live state first because concurrent repository work has occurred during this recovery.

If still unchanged, build a fresh R1 direct child of frozen main `99ade779...` changing exactly three files:
- `.github/workflows/avps-v1-dispatch-publisher.yml` -> exact reviewed Stage-B publisher template bytes;
- `.github/workflows/avps-v1-science.yml` -> exact reviewed Stage-B science template bytes;
- `review/avps-v1-ordinal40-stage-b-science-recovery-v1/post_consumption_surface.py` -> exact reviewed helper bytes.

Then build one R2 child changing only `.github/dispatch-requests/avps-v1-stage-b.json`, binding exact #570/#573/#574 heads/runs and Stage-A artifact identity.

Only a **new** status branch may be used:
`status/avps-v1-stage-b-science-recovery-ordinal-40`

Do not reuse the old Stage-A status ref. The Stage-B publisher may write no repository refs and no Issue-60 markers; its only write capability is one explicit Actions workflow dispatch after pre-dispatch evidence is uploaded.

The Stage-B science transport must use true `workflow_dispatch`, keep actual recovery transport identity separately, check out the scientific source at exact authorization head `338ee82...`, construct the logical original dispatch identity for the unchanged science guard, and stop after raw-360 metadata closure. No result interpretation/opening is permitted in Stage B.

## Immediate next step

Wait only for the two attempt-1 #574 review checks to reach terminal state. Do not manually rerun. If they pass, perform a fresh live preactivation audit before creating/moving any Stage-B status ref. If either fails, inspect the exact failed step and correct the smallest demonstrated control defect on a new review head.
