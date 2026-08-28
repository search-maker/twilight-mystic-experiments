# STAR VISIBILITY / MYSTIC — CURRENT NEW-WORKER HANDOFF

**Current status: 2026-08-27/28 — AVPS scientific ordinal 40 is allocated and consumed; Stage A recovery is complete; Stage B review is now fully green on exact head `30522faddb0a76b3767652da94ddc41a4cd24ab2`; activation/science has NOT yet been triggered. No AVPS MYSTIC result exists yet.**

This file is the current standalone handoff for the non-observation computational/scientific work. It supersedes earlier checkpoints on this handoff branch.

---

# 0. EXACT LIVE CHECKPOINT — READ FIRST

Repository:

- `search-maker/twilight-mystic-experiments`

Frozen live `main`:

- `99ade7798627e67921139697ba1a004fa8a304bb`

**Do not move main while the ordinal-40 authorization/recovery chain remains tied to this exact parent.**

## AVPS authorization identity

Authorization PR:

- PR #565 — Draft/open/unmerged
- authorization head `338ee82c8e088e929f45782b1f7ac1c3aaaaa533`
- authorization parent `99ade7798627e67921139697ba1a004fa8a304bb`
- authorization JSON Git blob `91c2fcfe0536f7289b9da3c597428c546523571a`
- authorization JSON SHA-256 `bec00d3a5609794fbb1078abb2c8ec6cf901318f5e9e80f38c387fab886dae97`
- authorization review run `33113256151`, attempt 1, SUCCESS
- review artifact `9663887142`
- digest `sha256:3edff7740ca35832bbca0cfcba096aa3d9963d9b6c19044d867a2b3c9f09a47c`.

Preauthorization:

- exact-main run `33111875371`, attempt 1, SUCCESS
- artifact `9663132186`
- digest `sha256:1253612ffe4ba228e319f6b063256abd7340d11eec76981db4cc39a3619b2df6`
- frozen 72 candidate seeds.

Issue 60 contains exactly one allocation marker:

`ORDINAL40_AVPS_V1_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED commit=338ee82c8e088e929f45782b1f7ac1c3aaaaa533 parent=99ade7798627e67921139697ba1a004fa8a304bb pr=565`

and exactly one consumed marker:

`ORDINAL40_AVPS_V1_DISPATCH_CONSUMED`

Therefore:

> **Ordinal 40 is already allocated and consumed. Never reuse, reallocate, retire-as-unused, or consume it again.**

Logical dispatch branch:

- `dispatch/aerosol-vertical-profile-sensitivity-v1-ordinal-40`
- immutable head `338ee82c8e088e929f45782b1f7ac1c3aaaaa533`.

At this checkpoint:

- no AVPS science workflow has yet run on the logical dispatch identity;
- no AVPS MYSTIC/uvspec scientific case has yet executed;
- no AVPS result has been opened.

---

# 0A. STAGE A — PUBLISHER EVIDENCE RECOVERY COMPLETE

The original publisher consumed the identity successfully but then failed during post-dispatch verification because generic failed-authorization-history logic rejected the newly legitimate consumed marker.

Original publisher failure:

- run `33114653044`, attempt 1, failure
- request/status head `8708a0f8a2fa86c5c13b27c94517552b0bf7dc2a`
- no science.

It had already:

1. passed pre-dispatch controls;
2. created the logical dispatch branch at the authorization head;
3. posted the consumed marker exactly once.

Then it failed with:

`GlobalOrdinalRefusal: ordinal 40 already has consumed marker`

This was control-plane-only after consumption.

Final Stage A review:

- PR #573 — Draft/open/unmerged
- review head `352f226d87d570a7338bf2730872a7733179da74`
- reviewed Stage-A template blob `821cd234ffd1253905839834d1afeafa91bdcdfd`
- review run `33122607199`, attempt 1, SUCCESS.

Final Stage A activation:

- control commit `c580002b0b30c9ee48a4bf7f88edd83c930e0044`
- request/status head `14a2d1272d8e81383e0fb4f830fceef5647d985c`
- successful publisher-evidence run `33123226959`, attempt 1
- job `98695045355`
- conclusion SUCCESS.

Stage A artifact:

- id `9667291127`
- name `avps-v1-dispatch-publisher-ordinal-40`
- digest `sha256:0338d418d554c5ceaead8712a1ee860c2ee154d839cfe7c038098607786a0b3f`.

Receipt:

- `DISPATCH_PUBLISHED_ZERO_RUNTIME`

Recovery receipt:

- `POST_CONSUMPTION_PUBLISHER_RECOVERY_PASS_NO_SECOND_CONSUMPTION_NO_SCIENCE_TRIGGER`

Proved:

- no second dispatch push;
- no second allocation or consumed marker;
- no science trigger;
- no scientific runtime;
- no solver.

**Stage A is closed. Do not reopen it.**

---

# 0B. STAGE B — FINAL REVIEW NOW FULLY GREEN

PR:

- PR #574 — `Review AVPS Stage B consumed-state science recovery`
- Draft/open/unmerged
- branch `review/avps-v1-ordinal40-stage-b-science-recovery-control-1`
- exact final green review head `30522faddb0a76b3767652da94ddc41a4cd24ab2`
- base `99ade7798627e67921139697ba1a004fa8a304bb`.

## Narrow repair scope

The frozen science workflow's generic post-dispatch surface builder called failed-authorization reuse logic before the downstream validator could recognize the legitimate one-consumed-marker state.

Stage B repairs **only** that failed-history subproof:

1. prove preserved failed authorization head `67844e1dd2523963f2682f186387280dfb930760`;
2. prove #561 was closed/unmerged;
3. prove auth-review run `33109014744` was attempt-1 failure;
4. prove the failed head itself was never allocated and never ran science;
5. temporarily substitute only that subproof while using the original bound control-surface builder;
6. immediately restore the original helper;
7. call unchanged `freshness.validate_dispatch(..., post_dispatch=True)`;
8. feed the recovered surface to unchanged frozen `science_guard.py` blob `c774be7ea8655854bb85071a9fb260e21498beda`.

The recovery does NOT change scientific inputs, seeds, cases, runtime, F, analysis, or result-opening semantics.

## First live Stage-B review failure — transient GitHub transport only

Old review head:

- `9a3390d27963359c7c39b1762a1b8eec90e24185`.

Run:

- `33130501045`, attempt 1, failure.

Failure occurred while repository-global seed scanning fetched Actions metadata:

`urllib.error.HTTPError: HTTP Error 502: Bad Gateway`

Not a seed collision or scientific refusal.

No GitHub rerun attempt 2 was used.

## Bounded transport retry

The Stage-B **review workflow only** was hardened:

- at most 3 complete scan attempts inside one workflow run attempt;
- retry only HTTP 5xx / network transport exceptions;
- semantic refusal, collision or snapshot failure remains immediately terminal;
- no `gh run rerun` and no workflow run attempt 2.

## Old corrected head proved the science/control logic

Head:

- `8d9bd70d1c666b84588a1e33fff14dd71c81a46e`.

Dedicated review:

- run `33132159457`, attempt 1, SUCCESS.

It passed live 72-seed global recheck + recovered surface + unchanged validator + zero-science proof.

Its repository-wide contract failed only one brittle regression assertion requiring the seed-hash field name literally inside the inactive YAML template, even though the exact frozen `science_guard.py` already performs both canonical hash comparisons.

The regression was corrected to test the **actual enforcement chain**, without changing the science/recovery templates or helper.

## FINAL SAME-HEAD REVIEW RESULTS

Exact head:

- `30522faddb0a76b3767652da94ddc41a4cd24ab2`.

Changes from `8d9bd70d...`:

- test files only;
- no recovery template/helper/contract/scientific source change.

Repository-wide contract:

- run `33132860787`
- attempt 1
- exact head `30522faddb0a76b3767652da94ddc41a4cd24ab2`
- conclusion **SUCCESS**.

Dedicated Stage-B live review:

- run `33132860780`
- attempt 1
- exact head `30522faddb0a76b3767652da94ddc41a4cd24ab2`
- job `98727147108`
- conclusion **SUCCESS**.

Every dedicated-review step passed:

1. Stage-B unit contract;
2. exact frozen authorization checkout;
3. live main/auth/dispatch/Stage-A binding;
4. live 72-seed authorization recheck;
5. recovered post-dispatch freshness surface;
6. unchanged original freshness validator;
7. immutable evidence upload;
8. terminal proof that science still had not started.

Stage-B review artifact:

- id `9671228507`
- name `avps-v1-stage-b-post-consumption-surface-review`
- GitHub digest `sha256:e81157d0e4cf30bd0974013ddf42eee18eb6d576706bd783950d0cb5ae658c15`
- downloaded ZIP SHA-256 independently rechecked equal to the GitHub digest.

The live seed scan required the bounded transport retry because the first internal scan attempt again received GitHub HTTP 502. Internal scan attempt 2 succeeded **within the same workflow run attempt 1**.

Verified artifact evidence:

- successful internal scan attempt = `2`;
- candidate seed count = 72;
- candidate seed canonical SHA-256 = `a2e22b526dfad84d4f23c0ca8b143d028fddc7e55f78deb93a43e194ebd6c35e`;
- candidate row canonical SHA-256 = `f22de8a9e30ba106759effb1170a5ca1d1e747cb2ac68293fa232dc7ed6ca683`;
- repository-global collision count = 0;
- repository-global collision scan passed;
- repository-global double enumeration stable = true;
- post-fence candidate-seed collision count = 0;
- audited branch = logical dispatch branch;
- audited dispatch head matched `338ee82c...`;
- no post-fence arrivals in any audited surface.

Recovered freshness evidence:

- `latestPriorConsumedScientificOrdinal = 39`
- `nextAvailableScientificOrdinal = 40`
- `candidatePriorScientificRunCount = 0`
- `candidateExecutionKeyPriorUseCount = 0`
- `positiveCandidateClaimsExcludingCurrent = 0`
- authorization branch/head exact
- dispatch branch/head exact
- matching authorization markers = 1
- consumed marker count = 1
- candidate seed authorization recheck passed = true
- `originalFreshnessValidateDispatchPassed = true`
- `recoveryRepairScope = FAILED_AUTHORIZATION_HISTORY_SUBPROOF_ONLY`.

**Stage B review is now closed green and activation may be prepared.**

Do not merge #574 merely for activation.

---

# 0C. EXACT REVIEWED STAGE-B ACTIVATION BYTES

These bytes are unchanged by the final test-only review fix:

- inactive recovery publisher template blob:
  `042727fc6efae85bf34b0a6868cb7e2e86a662e6`
- inactive recovery science template blob:
  `cb3735ab0529de79bd75bdb22d3391b8cf92e9f5`
- post-consumption helper blob:
  `efe771b21bd8c8ebbf9e4e998faff39b125af377`.

Activation control commit must be a direct child of frozen main and change exactly three files:

1. `.github/workflows/avps-v1-dispatch-publisher.yml` -> exact reviewed publisher blob
2. `.github/workflows/avps-v1-science.yml` -> exact reviewed recovery-science blob
3. `review/avps-v1-ordinal40-stage-b-science-recovery-v1/post_consumption_surface.py` -> exact reviewed helper blob.

Then a child request commit must change exactly one file:

- `.github/dispatch-requests/avps-v1-stage-b.json`.

No main merge is required or allowed for activation.

The recovery publisher:

- does not create a new ordinal;
- does not push a second logical dispatch ref;
- does not post another Issue-60 marker;
- proves all current state and Stage-A/Stage-B review evidence;
- uploads pre-dispatch Stage-B publisher evidence;
- then makes exactly one `workflow_dispatch` call to the active recovery science workflow on the recovery status ref.

The recovery science workflow:

- preserves logical dispatch identity at the original authorization head;
- performs a fresh repository-global 72-seed recheck before solver;
- builds the reviewed post-consumption freshness surface;
- passes it through the unchanged frozen science guard;
- executes only the exact frozen 360 cases if the guard passes.

Recovery science remains **result-closed**:

- no `aggregate_results`;
- no `open_results`;
- no Level-B result opening;
- terminal target is exact 360 raw case artifacts + metadata-only closure.

A later separate reviewed gate is required to aggregate/open scientific results.

---

# 0D. STAGE-B ACTIVATION REQUEST FIELDS

Frozen request must bind:

- `schemaVersion = 1`
- `stageId = aerosol-vertical-profile-sensitivity-v1-stage-b-science-recovery`
- `status = REQUEST_ONE_SHOT_STAGE_B_SCIENCE_RECOVERY_RAW_CASES_ONLY`
- `scientificOrdinal = 40`
- `authorizationPr = 565`
- `authorizationHead = 338ee82c8e088e929f45782b1f7ac1c3aaaaa533`
- `authorizationParent = 99ade7798627e67921139697ba1a004fa8a304bb`
- `recoveryContractPr = 570`
- `recoveryContractHead = f1588592725fd31c9bf6b653557fd5ce2b108e01`
- `recoveryContractRunId = 33120120487`
- `stageAReviewPr = 573`
- `stageAReviewHead = 352f226d87d570a7338bf2730872a7733179da74`
- `stageAReviewRunId = 33122607199`
- `stageAPublisherRunId = 33123226959`
- `stageAArtifactId = 9667291127`
- `stageAArtifactDigest = sha256:0338d418d554c5ceaead8712a1ee860c2ee154d839cfe7c038098607786a0b3f`
- `stageBReviewPr = 574`
- `stageBReviewHead = 30522faddb0a76b3767652da94ddc41a4cd24ab2`
- `stageBReviewRunId = 33132860780`.

Before status-ref activation, re-read live state and require:

- main still `99ade779...`;
- #565, #570, #573, #574 Draft/open/unmerged at exact heads;
- one allocation marker;
- one consumed marker;
- logical dispatch head = authorization head;
- zero prior AVPS science runs;
- reviewed template/helper blobs exact.

---

# 1. AVPS SCIENTIFIC DESIGN — FROZEN

Experiment:

- Aerosol Vertical-Profile Sensitivity v1 (AVPS v1)
- scientific ordinal 40.

Question:

> At fixed total AOD550 and fixed coherent OPAC rich optical family, how much does independently specified normalized aerosol vertical optical-depth shape change twilight radiance and the derived Level-B limiting-magnitude endpoint?

This is **not** a Taylor-fitting experiment.

Vertical states:

1. continental average
2. maritime clean
3. desert
4. arctic
5. antarctic.

All five use the same OPAC `continental_average` rich optical family.

Frozen design:

- AFGL-US
- observer 0 m
- surface albedo 0.15
- 380–780 nm
- reviewed 1-nm grid
- MYSTIC spherical 1D
- VROOM
- MC standard-deviation evidence
- 20,000,000 photons/case
- Sun depression 2°, 4°, 6°, 8°
- AOD550 0.10, 0.30
- geometries 10°/30°, 30°/90°, 45°/180°
- 3 CRN replicates
- 5 vertical states.

Cardinality:

- 72 CRN groups
- 360 cases
- 24 analysis cells
- four 90-case shards
- max parallel 2 per shard
- max 8 concurrent case jobs.

Primary endpoints:

- photopic luminance
- scotopic luminance
- Johnson-V effective radiance.

Secondary:

- paired Level-B limiting-magnitude delta through frozen Crumey Eq.34 with `F=3.14`.

No adaptive post-result cases and no universal minute conversion.

---

# 2. MERGED AVPS FOUNDATIONS — DO NOT REBUILD

- #549 vertical-profile transport — `76e232523f29cfc64d3c50c0b3e922aa59d1dfe7`
- #550 OPAC + custom tau capability — `2be138d96d4e6d04b1e58dede27bb3f0130fc42e`
- #551 preregistration — `b882034629894d2629ec60ef15f46e83635d6f7e`
- #552 unseeded 360-case skeleton — `79fd4605e02068f0d798181e2b05459d708bfebc`
- #557 disabled execution package — `d206a098ad6fee1bf6513460d29c949eadb695d1`
- #558 authorization controls
- #559 execution/publisher/science controls — `107d63a01de96bc359af0ecd8f0129b7232ddcf1`
- #562 failed-auth recovery/stabilization — `cd56db1e823a75d617c026fecf359a80e8c64cb7`
- #563 frozen main — `99ade7798627e67921139697ba1a004fa8a304bb`.

Exact normalized tau SHA-256:

- continental average `e6c296951dfae376bf77948aa92828062ba95d7b1e9c28703befa9cffb5bf198`
- maritime clean `5cbaf5f81f3f36bfcf9b365eaa5d892889da83453c18d58e705b3de9273adc8c`
- desert `3d8891b3b67fa8c8c6fd66861d49e9bfad8c937a176b7001c6c47a5571de21ad`
- arctic `61eed1e73ac8cc6f044b89870a6874f1d21500008c7747830a2a812bbd87919a`
- antarctic `a14460a04afd5154d931b77e55b7adce2ab41aae2e8e4c13afaa0de459aff164`.

Exact AFGL bundle:

- artifact `9658061526`
- digest `sha256:2061136f069e9a16fa5c5b3d0991121bb04d7a268d1b7c7f93c60d734d537b48`.

---

# 3. OPERATIONAL ATMOSPHERE STATE V2 — MERGED FOUNDATION

- #120 design — `0ef878a78f792edc7a484de8ace8a196be1543cb`
- #121 foundation — `e0da52eb0a2d5bac333da6572f51df52ea7e676e`.

Supports provenance, provider/source separation, spectral AOD, vertical profiles, SSA/phase/g/classification containers, explicit missing/rejected/conflict states and physical QC.

Important:

> Rich v2 atmosphere is represented, but arbitrary rich fields are not yet universally consumed by production Level-B.

AVPS informs whether/how vertical profile needs an explicit fast-model dimension.

---

# 4. TAYLOR — AUTHORITATIVE INTERPRETATION

Taylor Ann Arbor remains a direct-MYSTIC validation case, not a fitting target.

At Sun depression about `−5.808°`:

- old residual `+0.393 mag`
- independently obtained CAMS-profile run `+0.087 mag`.

At `−6.134°`:

- old residual `+0.388 mag`
- CAMS-profile run `+0.031 mag`.

No AOD or SQM offset was fitted.

Conclusion:

> Aerosol vertical distribution materially affects twilight radiance; the old ~6° discrepancy was not clean evidence of a gross MYSTIC failure.

Do not claim exact Taylor atmosphere knowledge and do not choose an AVPS profile based on Taylor residuals.

CAMS forecast00 vertical extinction returned 137 exact zeros despite nonzero AOD; treat that as invalid profile data, not real aerosol-free air.

Taylor AOD finite-difference derivative remains unresolved.

---

# 5. OTHER ACTIVE/OPEN WORK

Separate Taylor atmosphere archival worker owns EarthCARE/ATLID, lidar/ceilometer, AERONET and other independent archives. Do not duplicate.

Closed aerosol-optics scientific ordinals:

- AOPS 37
- AFPF 38
- ASIV 39
- AVPS 40.

Do not restart generic SSA/g/full-phase/family work already covered by 37–39.

Transient adaptation:

- #119 merged diagnostic
- #116 open/do not merge
- #117 physical mapping unresolved.

Keep `F=3.14`.

Moon #459 / Natural #460 remain incomplete; artificial skyglow directional provider still needed; total-sky compositor #112 already merged.

---

# 6. MASTER CLOSURE PR #539

#539 remains the intended long-term source of truth.

After the Stage-B activation/science step reaches a stable terminal checkpoint, refresh #539 with:

- Stage A success
- Stage-B initial 502 failure
- bounded transport retry
- final same-head Stage-B dual-green reviews
- Stage-B review artifact `9671228507`
- science run identity/status if science starts
- later exact-360/result-opening gate status.

Do not mutate #539 during any live repository-global seed scan.

---

# 7. IMMEDIATE NEXT ACTIONS

## P0-A — build Stage-B activation chain atomically

From exact frozen main `99ade779...`:

1. create direct-child control commit changing exactly the three reviewed files to blobs `042727fc...`, `cb3735ab...`, `efe771b2...`;
2. verify compare is exactly those three files;
3. create child request commit changing exactly `.github/dispatch-requests/avps-v1-stage-b.json` with the frozen request fields above;
4. verify compare from control->request is exactly one file;
5. create/move only the intended Stage-B status ref after final live-state recheck.

## P0-B — before status-ref activation

Re-prove:

- frozen main exact;
- #565/#570/#573/#574 Draft/open/unmerged at exact heads;
- one allocation marker;
- one consumed marker;
- dispatch head = authorization head;
- zero AVPS science runs;
- Stage A artifact exact;
- Stage B review run/artifact exact;
- reviewed activation blobs exact.

## P0-C — publisher/science

Publisher should create pre-dispatch evidence and issue one workflow-dispatch call only.

If science workflow starts:

- no GitHub rerun/retry/resume of the scientific run;
- live seed global recheck must pass pre-solver;
- recovered freshness must pass unchanged science guard;
- execute exactly frozen 360 cases.

## P0-D — recovery result boundary

Even if all 360 cases finish, do **not** open/interpret results in Stage B.

First terminal science target:

> exact 360 immutable raw case artifacts + metadata-only closure.

Then create a separate reviewed aggregate/result-opening gate.

---

# 8. ABSOLUTE DO-NOT LIST

Do not:

- move live main during this authorization lifecycle;
- reuse/reallocate ordinal 40;
- post second allocation/consumed markers;
- recreate logical dispatch identity;
- create new AVPS seeds;
- alter case universe, CRN pairing, vertical profiles, AOD, OPAC optics, geometry, wavelengths, photons, runtime or F;
- tune anything from Taylor/Jerusalem residuals;
- weaken the repository-global 72-seed audit;
- convert bounded 5xx transport retry into semantic retry;
- use GitHub scientific rerun/retry/resume;
- open partial results;
- aggregate or interpret Stage-B raw outputs inside the recovery run;
- merge Draft review PRs merely for activation;
- merge #116 before #117 is scientifically resolved.

---

# 9. ONE-LINE LIVE STATUS

> **AVPS ordinal 40 is allocated+consumed; Stage A is complete; Stage B is now fully reviewed and dual-green on exact head `30522fad...`, with fresh 72-seed global proof and zero collisions; no AVPS science has run yet, and the next action is the exact three-file + one-request activation chain that may trigger the first frozen 360-case MYSTIC recovery run while keeping results closed.**
