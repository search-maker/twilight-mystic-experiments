# STAR VISIBILITY / MYSTIC — CURRENT NEW-WORKER HANDOFF

**Current status: 2026-08-27, after AVPS ordinal-40 authorization review success and a partially successful dispatch publisher that consumed the identity but failed before science dispatch**

This is the authoritative standalone handoff for the current non-observation computational/scientific work. It supersedes all earlier post-#557 and intermediate handoffs.

---

# 0. READ THIS FIRST — exact live checkpoint

Repository:

- `search-maker/twilight-mystic-experiments`

Live `main` remains:

- `99ade7798627e67921139697ba1a004fa8a304bb`
- merge commit of PR #563.

Current authorization PR:

- PR #565 — `Review fresh AVPS v1 ordinal 40 authorization candidate`
- open / Draft / unmerged
- parent `99ade7798627e67921139697ba1a004fa8a304bb`
- authorization head `338ee82c8e088e929f45782b1f7ac1c3aaaaa533`
- exactly one changed file: `experiments/aerosol-vertical-profile-sensitivity-v1/authorization.json`
- authorization JSON Git blob `91c2fcfe0536f7289b9da3c597428c546523571a`
- authorization JSON SHA-256 `bec00d3a5609794fbb1078abb2c8ec6cf901318f5e9e80f38c387fab886dae97`

Authorization review:

- run `33113256151`
- attempt `1`
- conclusion **SUCCESS**
- review artifact ID `9663887142`
- artifact digest `sha256:3edff7740ca35832bbca0cfcba096aa3d9963d9b6c19044d867a2b3c9f09a47c`
- status `AUTHORIZATION_REVIEW_PASS_ZERO_RUNTIME`

Allocation marker now exists exactly once in Issue 60:

`ORDINAL40_AVPS_V1_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED commit=338ee82c8e088e929f45782b1f7ac1c3aaaaa533 parent=99ade7798627e67921139697ba1a004fa8a304bb pr=565`

Therefore ordinal 40 is now **allocated/reviewed**.

A dispatch publisher subsequently ran and partially succeeded:

- publisher request branch `status/avps-v1-dispatch-publisher-ordinal-40`
- request head `8708a0f8a2fa86c5c13b27c94517552b0bf7dc2a`
- publisher run `33114653044`
- attempt `1`
- overall conclusion `failure`

But the failure occurred **after** the actual dispatch transition had already succeeded.

The publisher successfully:

1. bound the exact authorization / preauthorization / review identities;
2. passed the pre-dispatch guard;
3. pushed the dispatch ref;
4. posted the consumed marker.

Exact dispatch branch now exists:

- `dispatch/aerosol-vertical-profile-sensitivity-v1-ordinal-40`
- exact head `338ee82c8e088e929f45782b1f7ac1c3aaaaa533`

Issue 60 contains exactly the consumed marker:

`ORDINAL40_AVPS_V1_DISPATCH_CONSUMED`

posted by `github-actions[bot]`.

Therefore ordinal 40 is **consumed**. Never reuse, retire, reallocate, or re-consume it.

The publisher then failed in step:

- `Mark consumed once and prove post-dispatch state`

Exact exception:

`avps_local_global_ordinal.GlobalOrdinalRefusal: ordinal 40 already has consumed marker`

The failure path is:

- `preauthorization_surface.build_dispatch_surface(... post_dispatch=True)`
- bound AOPS `control_surface.build_surface(...)`
- AVPS `global_ordinal.failed_authorization_history(payload, 40)`
- `failed_authorization_history()` currently refuses any consumed marker while inspecting preserved failed authorization history, even though in the post-dispatch state the **single expected consumed marker is the evidence that must be accepted and verified**.

Because this exception happened after branch+marker consumption:

- immutable successful publisher evidence was not uploaded;
- explicit science dispatch step was skipped;
- no science workflow was started by the publisher.

Independent readback confirms:

- query of Actions runs on `dispatch/aerosol-vertical-profile-sensitivity-v1-ordinal-40` returned `0` runs;
- therefore no AVPS science run has occurred on the consumed dispatch identity;
- no scientific results have been opened.

**Current classification:**

> ordinal 40 is validly allocated and consumed; dispatch branch creation succeeded; publisher recovery is required only because post-dispatch control verification incorrectly rejects the expected consumed marker. This is a control-plane recovery, not a scientific failure and not a new scientific identity.

---

# 1. IMMEDIATE RECOVERY ORDER — DO NOT DEVIATE

## Step 1 — do NOT repeat any consumed boundary

Absolutely do not:

- post another allocation marker;
- post another consumed marker;
- rerun publisher run `33114653044`;
- push/recreate/move the dispatch branch;
- allocate ordinal 41 as a replacement for this control-plane failure;
- delete the existing dispatch branch;
- merge #565 merely to recover;
- run science manually outside a reviewed recovery path.

Ordinal 40 and its 72 seed identities are already consumed and must remain immutable.

## Step 2 — implement a narrow post-consumption publisher recovery

The recovery must recognize exactly this legitimate state:

- one correct allocation marker for head `338ee82c...`, parent `99ade779...`, PR #565;
- one correct consumed marker;
- exact dispatch branch exists at authorization head `338ee82c...`;
- authorization PR remains Draft/open/unmerged;
- exact authorization review attempt-1 is successful;
- original publisher run `33114653044` is attempt-1, terminal failure;
- original publisher passed its pre-dispatch guard and actual git-push step;
- original publisher failure occurred only after the consumed marker was posted, during post-dispatch verification;
- no science run exists yet;
- no result opening exists;
- no duplicate dispatch/allocation/consumption identity exists.

The recovery must fail closed if any of those facts drift.

## Step 3 — correct post-dispatch control semantics

The concrete bug is that AVPS `failed_authorization_history()` is reused inside the generic bound control surface even for `post_dispatch=True`.

The fix must not weaken preauthorization or authorization-review semantics.

Preferred architecture:

- keep the current strict failed-history function for preauthorization / authorization review / pre-dispatch;
- add an explicit **post-dispatch history verifier** or post-dispatch control mode that allows exactly the already-expected current allocation + dispatch branch + consumed marker while still validating preserved failed-head history;
- do not simply ignore consumed markers globally;
- do not make failed authorization heads reusable after any consumed evidence;
- add tests proving pre-dispatch remains fail-closed and post-dispatch accepts only the exact one-consumed-marker state.

## Step 4 — recovery must preserve evidence before science

A dedicated recovery workflow should:

1. bind current main, authorization head/parent/PR, successful auth review artifact, preauthorization artifact, original publisher request head/run;
2. prove exact dispatch branch head and exactly one consumed marker;
3. prove no AVPS science run exists;
4. run corrected post-dispatch guard;
5. upload immutable recovery/publisher evidence;
6. only then explicitly dispatch the existing frozen AVPS science workflow attempt-1 on the already-consumed dispatch ref.

No second git push and no second consumed marker.

## Step 5 — science/results boundary remains unchanged

If recovery successfully dispatches science:

- use the existing frozen 360-case campaign;
- do not tune/add cases;
- do not open results while cases are running;
- do not inspect scientific payloads before exact aggregate validation.

Results may be opened only after:

- all 360 cases exist;
- all raw/member hashes verify;
- exact runtime identities verify;
- all case/attempt identities verify;
- 8001-node channels / derived quantities verify;
- exact-360 aggregate guard passes.

Primary result opening is a separate post-aggregate action.

---

# 2. CONTROL HISTORY — PRESERVE ALL OF THIS

## #558 — MERGED
`Add current-main AVPS authorization control gate`

Merge commit:

- `608359c645aaa2ff184124ee718c09e971d5e13b`

## #559 — MERGED
`Freeze AVPS execution, analysis, and result-opening controls`

Merge commit:

- `107d63a01de96bc359af0ecd8f0129b7232ddcf1`

Frozen before identity allocation:

- exact 360-case reconstruction;
- exact 72-CRN grouping;
- fixed rich OPAC `continental_average` optics + state-specific custom tau + fixed AOD;
- 20M photons/case;
- process-group-safe execution;
- exact raw/member hashing and 8001-node validation;
- exact-360 aggregation before result opening;
- separate primary result opening;
- current Crumey Eq.34 full Level-B endpoint with `F=3.14`;
- separate dispatch/science guards;
- exact execution-control bindings.

## #561 — CLOSED / UNMERGED failed first authorization review

Failed head:

- `67844e1dd2523963f2682f186387280dfb930760`

Review run:

- `33109014744`
- attempt `1`
- failure caused by repository metadata drift during the global double enumeration.

No allocation/dispatch/science occurred for this failed head.

Preserved immutable history ref:

- `history/aerosol-vertical-profile-sensitivity-v1-ordinal-40-auth-review-failed-1`

Never delete/rewrite it.

## #562 — MERGED failed-review recovery

Merge commit:

- `cd56db1e823a75d617c026fecf359a80e8c64cb7`

Added:

- rigorous failed-head reuse proof;
- authorization-head Actions quiet-window before global scan.

No science semantics changed.

## first post-#562 preauthorization failure

Run:

- `33110552017`
- exact main `cd56db1e...`
- failed because the handoff update commit `471678a0...` landed inside the two-pass scan window.

No collision/allocation/science. Do not rerun attempt 2.

## #563 — MERGED fresh exact-main identity

Current main:

- `99ade7798627e67921139697ba1a004fa8a304bb`

Mode-only trigger; watched blob bytes unchanged.

---

# 3. FRESH PREAUTHORIZATION / AUTHORIZATION EVIDENCE

## exact-main preauthorization — SUCCESS

Run:

- `33111875371`
- exact main `99ade7798627e67921139697ba1a004fa8a304bb`
- attempt `1`
- success.

Artifact:

- ID `9663132186`
- digest `sha256:1253612ffe4ba228e319f6b063256abd7340d11eec76981db4cc39a3619b2df6`
- status `PREAUTHORIZATION_SURFACE_CLEAN_NOT_ALLOCATED`
- report SHA-256 `12f8c7fe6cc7c5cbf36d320066d4a88e02695b541d2ffb0dae2e820961414175`.

Fresh proof:

- latest consumed before AVPS: 39;
- candidate ordinal: 40;
- 72 candidate seeds;
- zero tracked collisions;
- zero repository-global collisions;
- stable double enumeration.

## #564 zero-runtime materializer — CLOSED / UNMERGED

Run:

- `33112908528`
- success.

Artifact:

- ID `9663270438`
- digest `sha256:75d801a98c287924eab032ca215dcf5c5adaec51d326a59b453216a98d977fd9`.

Authorization bytes:

- SHA-256 `bec00d3a5609794fbb1078abb2c8ec6cf901318f5e9e80f38c387fab886dae97`
- Git blob `91c2fcfe0536f7289b9da3c597428c546523571a`.

## #565 fresh authorization review — SUCCESS

Head:

- `338ee82c8e088e929f45782b1f7ac1c3aaaaa533`

Run:

- `33113256151`
- attempt `1`
- success.

Artifact:

- ID `9663887142`
- digest `sha256:3edff7740ca35832bbca0cfcba096aa3d9963d9b6c19044d867a2b3c9f09a47c`.

Passed:

- exact one-file Draft identity;
- exact parent-main preauthorization;
- tracked-tree seed scan;
- Actions quiet-window;
- stable repository-global double enumeration;
- live seed proof;
- exact authorization guard;
- zero-runtime review evidence.

The review itself did not consume the identity; consumption occurred only afterward through the publisher.

---

# 4. AVPS SCIENTIFIC DESIGN — FROZEN / NOT A TAYLOR FIT

Scientific question:

> At fixed total AOD550 and fixed coherent OPAC rich optical properties/phase function, how much does independently specified normalized aerosol vertical optical-depth shape change twilight radiance and the derived Level-B limiting-magnitude endpoint?

Vertical templates:

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
- 380–780 nm
- 1-nm grid
- MYSTIC spherical 1D
- VROOM
- MC std evidence
- 20,000,000 photons/case
- Sun depression 2°, 4°, 6°, 8°
- AOD550 0.10 / 0.30
- geometries 10°/30° near-solar, 30°/90° cross-solar, 45°/180° opposite-solar
- 3 fresh CRN replicates
- 5 states
- 72 CRN groups
- 360 cases.

Primary endpoints:

- photopic luminance
- scotopic luminance
- Johnson-V effective radiance.

Secondary endpoint:

- paired current-Level-B limiting-magnitude delta via Crumey Eq.34 full branch, `F=3.14`.

No universal minute conversion. No adaptive post-result cases.

---

# 5. GLOBAL SCIENTIFIC RULES — DO NOT VIOLATE

- `F = 3.14` remains current default.
- transient `tau = 30 s` remains experimental only.
- Never tune F, tau, AOD, aerosol profile, provider/cycle, sky offset, threshold, interpolation/support, or other environment inputs to force Taylor/Jerusalem results.
- Never select source/provider/cycle because it minimizes target residuals.
- Freeze external/environmental choices before target scoring when possible.
- No universal magnitude/minute correction.
- Do not infer aerosol family from AOD alone.
- Do not fabricate missing vertical structure.
- Missing/invalid atmosphere info must remain explicit / fail closed or lower confidence.
- Do not call modeled fields measurements.
- CAMS republisher is not independent from CAMS.
- No `humanFirstSeeingValidated` without independent human evidence.
- Taylor mainly validates direct MYSTIC sky radiance, not Level-B or human first-seeing.
- Pandora/Izaña remain unopened unless separately authorized.
- matched-stellar v1 obsolete.
- do not reopen the closed exact-zenith/90° MYSTIC-stellar campaign.

---

# 6. `starsvisibility` / LEVEL-B UNRESOLVED WORK

Merged:

- #114 exact zenith/90° validated support;
- #118 clean-checkout Level-B test lifecycle;
- #119 frozen Crumey Eq.34 non-monotonic diagnostic;
- #120 Operational Atmosphere State v2 design;
- #121 v2 representation/QC/provenance foundation.

Do not merge #116 yet. #117 remains the underlying psychophysics question for transient adaptation.

Operational Atmosphere v2 can represent rich physical state, but current fast Level-B still does not generally consume arbitrary rich atmosphere with demonstrated predictive equivalence to direct MYSTIC.

Sensitivity priority:

1. vertical aerosol profile — current AVPS
2. spectral AOD
3. SSA
4. phase function/g
5. interactions
6. pressure/temp/ozone/water vapor/albedo/RH as warranted.

---

# 7. TAYLOR ANN ARBOR — CURRENT INTERPRETATION

Taylor 2025-08-07, Ann Arbor, original Unihedron SQM at zenith.

Direct MYSTIC residual improvement from independently obtained aerosol vertical structure:

- Sun -5.808°: old +0.393 mag -> CAMS-profile +0.087 mag
- Sun -6.134°: old +0.388 mag -> +0.031 mag.

No SQM offset or AOD was fitted.

Conclusion:

> vertical aerosol placement is a major plausible driver of the old ~6° discrepancy; total AOD alone is insufficient for maximum-accuracy twilight prediction. This does not mean the exact Taylor atmosphere is known.

CAMS provenance caution:

- same-cycle columns roughly AOD550 0.31–0.32, SSA550 ~0.95, g550 ~0.71, Angstrom alpha ~1.28;
- forecast00 vertical extinction had 137 exact zeros despite nonzero AOD;
- forecast03 valid;
- never choose forecast03 because it improves Taylor residuals;
- uniform-height SSA/g must be labeled approximation.

Independent Taylor archive search remains a separate worker lane.

---

# 8. REPORTING CONTRACT

Always record:

- exact commit/head;
- frozen protocol;
- runtime/data identities;
- seed preauthorization status;
- global ordinal + allocation/consumed markers;
- whether MYSTIC ran;
- whether results were opened;
- atmosphere provenance and approximations;
- MC/numerical uncertainty;
- whether target observations influenced source/model selection.

Never collapse these into a vague claim that `the model matches observations`.

---

# 9. CURRENT BOTTOM LINE

The AVPS scientific design is frozen and its authorization chain is valid. Ordinal 40 has now crossed the allocation and dispatch-consumption boundaries exactly once.

The actual dispatch branch exists at the exact reviewed authorization head, but the publisher failed afterward because the post-dispatch control path incorrectly treats the expected consumed marker as forbidden failed-history evidence. Science was therefore **not dispatched** and no results exist/opened.

Immediate task:

> build a narrow reviewed post-consumption recovery that accepts only the exact existing ordinal-40 allocation/dispatch/consumed state, proves the original publisher failure occurred after successful push+marker, proves no science run exists, preserves immutable recovery evidence, and then dispatches the already-frozen science workflow exactly once without another push, marker, ordinal, seed allocation, or manual bypass.
