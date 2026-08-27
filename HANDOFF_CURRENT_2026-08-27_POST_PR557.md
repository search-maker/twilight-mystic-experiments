# STAR VISIBILITY / MYSTIC — CURRENT NEW-WORKER HANDOFF

**Current status: 2026-08-27, after AVPS ordinal-40 consumption and two fail-closed publisher failures; no AVPS science run yet**

This is the authoritative standalone handoff for the current non-observation computational/scientific work. It supersedes the older post-#557/intermediate checkpoints.

---

# 0. READ THIS FIRST — exact live checkpoint

Repository:

- `search-maker/twilight-mystic-experiments`

Live `main` is still:

- `99ade7798627e67921139697ba1a004fa8a304bb`
- merge commit of PR #563.

**Do not move main while recovering ordinal 40.** The frozen science workflow requires the authorization parent to remain live main.

Current authorization PR:

- PR #565 — `Review fresh AVPS v1 ordinal 40 authorization candidate`
- open / Draft / unmerged
- parent `99ade7798627e67921139697ba1a004fa8a304bb`
- authorization head `338ee82c8e088e929f45782b1f7ac1c3aaaaa533`
- authorization JSON Git blob `91c2fcfe0536f7289b9da3c597428c546523571a`
- authorization JSON SHA-256 `bec00d3a5609794fbb1078abb2c8ec6cf901318f5e9e80f38c387fab886dae97`.

Authorization review run `33113256151`, attempt 1, is **SUCCESS**.

Issue 60 has exactly one allocation marker:

`ORDINAL40_AVPS_V1_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED commit=338ee82c8e088e929f45782b1f7ac1c3aaaaa533 parent=99ade7798627e67921139697ba1a004fa8a304bb pr=565`

and exactly one consumed marker:

`ORDINAL40_AVPS_V1_DISPATCH_CONSUMED`

Therefore ordinal 40 is **allocated and consumed**. Never reuse, retire, reallocate, or re-consume it.

Exact dispatch branch exists and must stay immutable:

- `dispatch/aerosol-vertical-profile-sensitivity-v1-ordinal-40`
- head `338ee82c8e088e929f45782b1f7ac1c3aaaaa533`.

As of the latest readback, there are **zero workflow runs on the dispatch branch**. No AVPS science run has started and no scientific results have been opened.

---

# 0A. Original publisher failure after successful consumption

Original status request head:

- `8708a0f8a2fa86c5c13b27c94517552b0bf7dc2a`

Preserved permanently at:

- `history/avps-v1-dispatch-publisher-ordinal-40-failed-after-consume-1`.

Original publisher run:

- `33114653044`
- attempt `1`
- conclusion `failure`.

It successfully:

1. bound request / authorization / preauthorization / authorization-review identities;
2. passed pre-dispatch guard;
3. performed the actual git push creating the dispatch branch at the authorization head;
4. posted the consumed marker exactly once.

Then it failed in:

- `Mark consumed once and prove post-dispatch state`

with:

`avps_local_global_ordinal.GlobalOrdinalRefusal: ordinal 40 already has consumed marker`

Root cause:

- post-dispatch verification called the generic AVPS failed-authorization-history helper;
- that helper treats any consumed marker as forbidden even though `post_dispatch=True` should accept and validate the one expected current consumed marker.

Because failure occurred after consumption:

- successful publisher evidence upload was skipped;
- science dispatch was skipped.

This is a control-plane failure, not a scientific failure.

---

# 0B. Recovery review history

## PR #566 — CLOSED / UNMERGED, useful fail-closed evidence

`Recover AVPS publisher after consumed post-dispatch verification failure`

Head:

- `4b30062c16e762059156f387cfea95b7752d0c44`.

It tried to review recovery by directly changing the active publisher workflow path.

Execution-control review run:

- `33116226092`.

All Python execution-control and Level-B tests passed, then the frozen execution contract correctly failed closed with:

`contract orchestration blob drift: .github/workflows/avps-v1-dispatch-publisher.yml`

Conclusion:

> recovery bytes must not be reviewed by changing the frozen active publisher path in a PR.

#566 was closed unmerged. No live control/science state changed.

## PR #567 — CURRENT REVIEW, Draft/open/unmerged

`Review inactive AVPS post-consumption publisher recovery template`

Current reviewed head:

- `b606dbda29c7beaa58c9bb176d436412ddc0f29e`.

Files only:

1. `.github/recovery-templates/avps-v1-dispatch-publisher-post-consumption-recovery.yml`
2. `tests/test_avps_v1_post_consumption_publisher_recovery.py`.

The template is inactive because it is outside `.github/workflows`.

Template Git blob:

- `3470a0d6d2620d43c4c841f17d50d32eb9941ec4`.

The active frozen publisher on main remained Git blob:

- `cd8aa5151533133a33c046ad2bed2bd7e2c11089`.

Initial #567 CI failed only because a test regex for a shell `git push` also matched historical prose such as `actual git push`. The template did not change. Test-only fix committed at current head `b606dbda...`.

Final #567 contract run:

- `33116868465`
- conclusion **SUCCESS**.

It passed:

- full unit/artifact audit;
- recovery regression tests;
- estimator-package checks;
- future-authorization proposal check;
- proof that scientific execution remained unauthorized.

**Do not merge #567.** Keep it Draft/open/unmerged as immutable review evidence for the template bytes.

---

# 0C. First activation chain from reviewed template

The recovery design preserves live main and the frozen dispatch branch. It uses a two-commit status-chain:

- R1 direct child of live main: changes only active publisher workflow to the exact reviewed inactive-template blob;
- R2 child of R1: changes only `.github/dispatch-requests/avps-v1.json`;
- only moving the status branch to R2 triggers a fresh attempt-1 publisher.

## R1

Commit:

- `cd4e6ca95d85cc5208a63fc8fd73ed685d4f8178`

Parent:

- `99ade7798627e67921139697ba1a004fa8a304bb`.

Only changed file:

- `.github/workflows/avps-v1-dispatch-publisher.yml`.

Publisher blob verified exactly equal to reviewed template:

- `3470a0d6d2620d43c4c841f17d50d32eb9941ec4`.

## R2

Commit:

- `00805a95dd1d179b544bf8f531a8ed726cf2d0c1`

Parent:

- R1 `cd4e6ca95...`.

Only changed file:

- `.github/dispatch-requests/avps-v1.json`.

Request blob:

- `be8e83956737abd36bbbe3cd37daec3b4d48d4eb`.

The request binds:

- authorization head `338ee82c...`;
- authorization parent `99ade779...`;
- PR #565;
- original failed publisher run `33114653044` / request head `8708a0f8...`;
- recovery review PR #567 / head `b606dbda...`;
- ordinal 40;
- status `RECOVER_ALREADY_CONSUMED_DISPATCH_AND_TRIGGER_SCIENCE`.

Status branch was force-moved to R2:

- `status/avps-v1-dispatch-publisher-ordinal-40`
- head became `00805a95dd1d179b544bf8f531a8ed726cf2d0c1`.

This created a **fresh run identity**, not a GitHub Re-run.

---

# 0D. First post-consumption recovery attempt — FAILURE, no science

Recovery publisher run:

- `33117461748`
- head `00805a95dd1d179b544bf8f531a8ed726cf2d0c1`
- workflow path `.github/workflows/avps-v1-dispatch-publisher.yml`
- event `push`
- run attempt `1`
- conclusion `failure`.

The run failed immediately in the first substantive step:

- `Bind reviewed post-consumption recovery request`.

Exact error:

`KeyError: 'AUTH_PARENT'`

Cause:

- `source request.env` correctly created shell variables such as `AUTH_PARENT`;
- the workflow did **not export** those variables before a Python block read `os.environ['AUTH_PARENT']`;
- therefore the process failed before any later recovery proof.

Boundary proof from job steps:

- checkout: PASS;
- Python setup: PASS;
- bind recovery request: FAIL;
- bind authorization/preauthorization/review: SKIPPED;
- prove original publisher history: SKIPPED;
- prove exact consumed state / no prior science: SKIPPED;
- stage recovery evidence: SKIPPED;
- upload publisher evidence: SKIPPED;
- science workflow dispatch: SKIPPED.

Therefore this recovery attempt did **not**:

- push/recreate/move the dispatch branch;
- post allocation/consumed markers;
- upload successful publisher evidence;
- start AVPS science;
- open results.

**Do not rerun `33117461748`.** Its identity is terminal attempt-1 failure.

Next recovery must use a fresh attempt-1 status-head identity.

---

# 1. IMMEDIATE NEXT ACTION

## 1. Preserve the failed recovery head before moving status again

Preserve:

- `00805a95dd1d179b544bf8f531a8ed726cf2d0c1`

under a dedicated history ref, e.g.:

- `history/avps-v1-post-consumption-publisher-recovery-failed-1`.

Do not delete or rewrite it.

## 2. Fix only the inactive recovery template + tests

The required semantic fix is narrow:

Immediately after `source request.env`, export all request-derived variables before any Python block reads `os.environ`, including at minimum:

- `ORDINAL`
- `AUTH_HEAD`
- `AUTH_PARENT`
- `PR_NUMBER`
- `FAILED_PUBLISHER_RUN_ID`
- `FAILED_PUBLISHER_REQUEST_HEAD`
- `RECOVERY_REVIEW_PR`
- `RECOVERY_REVIEW_HEAD`.

Add a regression test that would fail if a Python `os.environ[...]` read occurs before export.

Also bind the failed first recovery attempt explicitly in the next reviewed recovery if practical:

- run `33117461748`
- head `00805a95...`
- terminal attempt-1 failure;
- failure at first bind step;
- science trigger skipped.

Do not change any scientific/control semantics unrelated to this environment-export bug.

## 3. Re-review the changed inactive template

Update #567 (or a fresh inactive-template Draft if needed), let full CI pass, and freeze the new template blob.

No activation before green review.

## 4. Build a fresh R1/R2 chain from live main

After review success:

- R1: direct child of live main `99ade779...`, only active publisher workflow replaced with exact newly reviewed template blob;
- R2: child of R1, only new recovery request JSON;
- request must bind the current review head and prior failed recovery evidence;
- preserve previous failed status head before moving status;
- force-move status branch to fresh R2 to obtain a new attempt-1 push run.

Never use GitHub Re-run.

## 5. Recovery success conditions before science

A successful recovery publisher must prove:

- live main still `99ade779...`;
- #565 still Draft/open/unmerged at exact auth head;
- exact successful auth review/preauthorization;
- exactly one allocation marker;
- exactly one consumed marker;
- dispatch branch exactly at auth head;
- original publisher consumed then failed before science;
- prior recovery attempt(s) did not cross science boundary;
- zero pre-existing AVPS science runs;
- no successful prior recovery publisher exists;
- recovery run itself is attempt 1.

The recovery publisher must have:

- `contents: read`, not write;
- `issues: read`, not write;
- no `git push` command;
- no Issue 60 marker POST;
- only `actions: write` for the final explicit workflow-dispatch after immutable recovery evidence is uploaded.

## 6. Results remain closed

If science eventually starts, do not inspect/open result payloads before exact aggregate validation:

- all 360 cases present;
- all raw/member hashes verify;
- exact runtime identities verify;
- all case/attempt identities verify;
- 8001-node channels/derived quantities verify;
- exact-360 aggregate guard passes.

Primary result opening remains a separate post-aggregate action.

---

# 2. PREAUTHORIZATION / AUTHORIZATION EVIDENCE

Fresh exact-main preauthorization:

- run `33111875371`
- attempt 1 success
- main `99ade7798627e67921139697ba1a004fa8a304bb`
- artifact ID `9663132186`
- digest `sha256:1253612ffe4ba228e319f6b063256abd7340d11eec76981db4cc39a3619b2df6`
- latest consumed before AVPS: 39
- candidate ordinal: 40
- 72 seeds
- zero tracked/global collisions
- stable global double enumeration.

#564 zero-runtime materializer:

- run `33112908528` success
- artifact ID `9663270438`
- digest `sha256:75d801a98c287924eab032ca215dcf5c5adaec51d326a59b453216a98d977fd9`.

#565 authorization review:

- run `33113256151` attempt 1 success
- artifact ID `9663887142`
- digest `sha256:3edff7740ca35832bbca0cfcba096aa3d9963d9b6c19044d867a2b3c9f09a47c`
- status `AUTHORIZATION_REVIEW_PASS_ZERO_RUNTIME`.

---

# 3. EARLIER CONTROL HISTORY TO PRESERVE

#558 merged — authorization control:

- `608359c645aaa2ff184124ee718c09e971d5e13b`.

#559 merged — execution/analysis/result-opening controls:

- `107d63a01de96bc359af0ecd8f0129b7232ddcf1`.

#561 closed/unmerged first auth-review failure:

- head `67844e1dd2523963f2682f186387280dfb930760`
- run `33109014744`
- metadata-drift failure only
- preserved at `history/aerosol-vertical-profile-sensitivity-v1-ordinal-40-auth-review-failed-1`.

#562 merged failed-auth-review recovery:

- `cd56db1e823a75d617c026fecf359a80e8c64cb7`
- added failed-head reuse rules + Actions quiet-window.

Post-#562 preauthorization `33110552017` failed only because a handoff metadata write landed inside the two-pass global scan. No collision/allocation/science. Never rerun attempt 2.

#563 merged fresh trigger:

- current main `99ade7798627e67921139697ba1a004fa8a304bb`
- mode-only; watched code blob unchanged.

---

# 4. AVPS SCIENTIFIC DESIGN — FROZEN / NOT A TAYLOR FIT

Question:

> At fixed total AOD550 and fixed coherent OPAC rich optical properties/phase function, how much does independently specified normalized aerosol vertical optical-depth shape change twilight radiance and the derived Level-B limiting-magnitude endpoint?

Five vertical templates:

1. Continental average
2. Maritime clean
3. Desert
4. Arctic
5. Antarctic

All use the same rich OPAC `continental_average` optical family; labels describe vertical shape only.

Frozen design:

- AFGL-US
- observer 0 m
- albedo 0.15
- 380–780 nm, 1-nm grid
- MYSTIC spherical 1D
- VROOM
- MC std evidence
- 20,000,000 photons/case
- Sun depression 2°, 4°, 6°, 8°
- AOD550 0.10 / 0.30
- geometries: 10°/30° near-solar; 30°/90° cross-solar; 45°/180° opposite-solar
- 3 fresh CRN replicates
- 5 states
- 72 CRN groups
- 360 cases.

Primary endpoints:

- photopic luminance
- scotopic luminance
- Johnson-V effective radiance.

Secondary endpoint:

- paired Level-B limiting-magnitude delta via current Crumey Eq.34 full branch, `F=3.14`.

No adaptive post-result cases. No universal minute conversion.

---

# 5. GLOBAL SCIENTIFIC RULES — DO NOT VIOLATE

- `F = 3.14` current default.
- transient `tau = 30 s` experimental only.
- Never tune F, tau, AOD, aerosol profile, provider/cycle, sky offset, threshold, interpolation/support, or environment inputs to force Taylor/Jerusalem results.
- Never select source/provider/cycle because it minimizes target residuals.
- Freeze external/environmental choices before target scoring when possible.
- No universal magnitude/minute correction.
- Do not infer aerosol family from AOD alone.
- Do not fabricate missing vertical structure.
- Missing/invalid atmosphere stays explicit / fail-closed or reduced-confidence.
- Do not call modeled fields measurements.
- CAMS republisher is not independent from CAMS.
- No `humanFirstSeeingValidated` without independent human evidence.
- Taylor mainly validates direct MYSTIC sky radiance, not Level-B/human first-seeing.
- Pandora/Izaña remain unopened unless separately authorized.
- matched-stellar v1 obsolete.
- do not reopen the closed exact-zenith/90° MYSTIC-stellar campaign.

---

# 6. LEVEL-B / OPERATIONAL ATMOSPHERE STATUS

Merged in `starsvisibility`:

- #114 exact zenith/90° support;
- #118 clean-checkout Level-B lifecycle;
- #119 frozen Crumey Eq.34 non-monotonic diagnostic;
- #120 Operational Atmosphere State v2 design;
- #121 v2 representation/QC/provenance foundation.

Do not merge #116 yet; #117 remains the underlying transient-adaptation psychophysics question.

Operational Atmosphere v2 can represent richer state, but fast Level-B does not yet generally consume arbitrary rich atmosphere with independently demonstrated predictive equivalence to direct MYSTIC.

Sensitivity priority:

1. vertical aerosol profile — current AVPS
2. spectral AOD
3. SSA
4. phase function/g
5. interactions
6. then pressure/temp/ozone/water vapor/albedo/RH as warranted.

---

# 7. TAYLOR ANN ARBOR — CURRENT INTERPRETATION

Taylor 2025-08-07, Ann Arbor, original Unihedron SQM at zenith.

Direct MYSTIC residual change after independently obtained vertical aerosol structure:

- Sun -5.808°: old +0.393 mag -> CAMS-profile +0.087 mag
- Sun -6.134°: old +0.388 mag -> +0.031 mag.

No SQM offset or AOD was fitted.

Interpretation:

> vertical aerosol placement is a major plausible cause of the old ~6° discrepancy; total AOD alone is insufficient for maximum-accuracy twilight prediction. This does not mean Taylor's exact atmosphere is known.

CAMS caution:

- rough same-cycle AOD550 0.31–0.32, SSA550 ~0.95, g550 ~0.71, Angstrom alpha ~1.28;
- forecast00 vertical extinction had 137 exact zeros despite nonzero AOD;
- forecast03 valid;
- never choose forecast03 because it improves Taylor residuals;
- uniform-height SSA/g must be labeled approximation.

Independent Taylor archive search remains a separate worker lane.

---

# 8. REPORTING CONTRACT

Always report:

- exact commit/head;
- frozen protocol;
- runtime/data identities;
- seed preauthorization status;
- ordinal + allocation/consumed markers;
- whether MYSTIC ran;
- whether results were opened;
- atmosphere provenance/approximations;
- MC/numerical uncertainty;
- whether target observations influenced source/model selection.

Never collapse these into a vague statement that `the model matches observations`.

---

# 9. CURRENT BOTTOM LINE

The AVPS science design and ordinal-40 authorization are valid and frozen. Ordinal 40 has been allocated and consumed exactly once. The dispatch branch is correct and immutable.

The first publisher failed only after consumption; the first reviewed post-consumption recovery attempt then failed much earlier because request-derived shell variables were not exported before Python read `os.environ`. Both failures are control-plane failures. **No AVPS science run exists yet and no results have been opened.**

Immediate task:

> preserve recovery head `00805a95...`, fix/export request variables in the inactive #567 template with regression coverage, obtain a fresh green review and a new template blob, then build a new main→R1→R2 recovery chain and fresh attempt-1 status push. Never rerun prior failed runs, never post another marker or dispatch push, and never open scientific results before exact aggregate validation.
