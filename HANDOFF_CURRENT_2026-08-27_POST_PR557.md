# STAR VISIBILITY / MYSTIC — CURRENT NEW-WORKER HANDOFF

**Current status: 2026-08-27, after successful AVPS ordinal-40 Stage A publisher-evidence recovery; Stage B consumed-state science recovery is under review; no AVPS science has run yet**

This file is the current standalone handoff for the non-observation computational/scientific work. It supersedes earlier intermediate handoff checkpoints on this branch.

---

# 0. READ THIS FIRST — exact live checkpoint

Repository:

- `search-maker/twilight-mystic-experiments`

Frozen live `main`:

- `99ade7798627e67921139697ba1a004fa8a304bb`
- merge commit of PR #563.

**Do not move `main` while ordinal-40 recovery/science remains tied to the existing authorization parent.**

## Authorization identity — already allocated and consumed

Authorization PR:

- PR #565 — `Review fresh AVPS v1 ordinal 40 authorization candidate`
- Draft / open / unmerged
- authorization head `338ee82c8e088e929f45782b1f7ac1c3aaaaa533`
- authorization parent/live main `99ade7798627e67921139697ba1a004fa8a304bb`
- authorization JSON Git blob `91c2fcfe0536f7289b9da3c597428c546523571a`
- authorization JSON SHA-256 `bec00d3a5609794fbb1078abb2c8ec6cf901318f5e9e80f38c387fab886dae97`
- successful authorization review run `33113256151`, attempt 1
- review artifact `9663887142`, digest `sha256:3edff7740ca35832bbca0cfcba096aa3d9963d9b6c19044d867a2b3c9f09a47c`.

Issue 60 contains exactly one allocation marker:

`ORDINAL40_AVPS_V1_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED commit=338ee82c8e088e929f45782b1f7ac1c3aaaaa533 parent=99ade7798627e67921139697ba1a004fa8a304bb pr=565`

and exactly one consumed marker:

`ORDINAL40_AVPS_V1_DISPATCH_CONSUMED`

Therefore:

> **Scientific ordinal 40 is allocated and consumed. It must never be reused, retired as unused, reallocated, or consumed again.**

Dispatch branch:

- `dispatch/aerosol-vertical-profile-sensitivity-v1-ordinal-40`
- immutable head `338ee82c8e088e929f45782b1f7ac1c3aaaaa533`.

As of the latest verified readback before Stage B activation:

- zero AVPS science workflow runs exist on that dispatch branch;
- no MYSTIC/uvspec science execution occurred for AVPS ordinal 40;
- no AVPS result has been opened.

---

# 0A. Stage A recovery — COMPLETE

The original publisher successfully consumed the identity but then failed in post-dispatch verification because the generic failed-authorization reuse helper rejected the now-legitimate consumed marker.

Original publisher failure:

- original request/status head `8708a0f8a2fa86c5c13b27c94517552b0bf7dc2a`
- preserved at `history/avps-v1-dispatch-publisher-ordinal-40-failed-after-consume-1`
- run `33114653044`
- attempt 1
- conclusion failure.

It had already:

1. passed pre-dispatch identity/freshness checks;
2. created the dispatch branch at the authorization head;
3. posted the consumed marker exactly once.

Then it failed in post-dispatch validation with:

`avps_local_global_ordinal.GlobalOrdinalRefusal: ordinal 40 already has consumed marker`

This was a control-plane failure after consumption, not a science failure.

Several fail-closed recovery attempts were deliberately preserved while the recovery control was narrowed. Do not rerun those attempts and do not erase their history.

Final Stage A review evidence:

- PR #573 — `Bind fourth fail-closed AVPS Stage A history`
- Draft / open / unmerged
- review head `352f226d87d570a7338bf2730872a7733179da74`
- reviewed Stage-A v3 template blob `821cd234ffd1253905839834d1afeafa91bdcdfd`
- review run `33122607199`, attempt 1, SUCCESS.

Final Stage A activation chain:

- control commit `c580002b0b30c9ee48a4bf7f88edd83c930e0044`
- request/status head `14a2d1272d8e81383e0fb4f830fceef5647d985c`
- status branch `status/avps-v1-dispatch-publisher-ordinal-40`.

Successful Stage A publisher-evidence run:

- run `33123226959`
- attempt 1
- job `98695045355`
- head `14a2d1272d8e81383e0fb4f830fceef5647d985c`
- conclusion **SUCCESS**.

Every Stage-A step succeeded, including:

- exact request/contracts binding;
- exact authorization/preauthorization evidence binding;
- proof of four exact earlier attempt-1 publisher failures;
- proof of exactly one consumption and zero science;
- immutable receipt staging;
- terminal evidence upload.

Immutable Stage A artifact:

- artifact id `9667291127`
- name `avps-v1-dispatch-publisher-ordinal-40`
- digest `sha256:0338d418d554c5ceaead8712a1ee860c2ee154d839cfe7c038098607786a0b3f`.

Receipt status:

- `DISPATCH_PUBLISHED_ZERO_RUNTIME`
- no second git push;
- no second consumed marker;
- no science workflow dispatch;
- no scientific runtime setup;
- no solver execution.

Recovery receipt status:

- `POST_CONSUMPTION_PUBLISHER_RECOVERY_PASS_NO_SECOND_CONSUMPTION_NO_SCIENCE_TRIGGER`

Stage A is therefore **closed successfully**.

Do not reopen Stage A unless new evidence shows the immutable receipt is corrupt.

---

# 0B. Stage B — ACTIVE REVIEW, NO SCIENCE YET

Current review PR:

- PR #574 — `Review AVPS Stage B consumed-state science recovery`
- Draft / open / unmerged
- branch `review/avps-v1-ordinal40-stage-b-science-recovery-control-1`
- current reviewed head `9a3390d27963359c7c39b1762a1b8eec90e24185`
- based directly on frozen main `99ade7798627e67921139697ba1a004fa8a304bb`.

The PR adds exactly seven review/control files and modifies **no existing scientific source file**:

1. `.github/recovery-templates/avps-v1-stage-b-science-recovery-publisher.yml`
2. `.github/recovery-templates/avps-v1-stage-b-science-recovery.yml`
3. `.github/workflows/avps-v1-stage-b-post-consumption-surface-review.yml`
4. `review/avps-v1-ordinal40-stage-b-science-recovery-v1/RECOVERY_CONTROL_CONTRACT.review.json`
5. `review/avps-v1-ordinal40-stage-b-science-recovery-v1/post_consumption_surface.py`
6. `tests/test_avps_v1_stage_b_post_consumption_surface.py`
7. `tests/test_avps_v1_stage_b_recovery_transport.py`.

Exact review blobs recorded in PR #574:

- post-consumption helper `efe771b21bd8c8ebbf9e4e998faff39b125af377`
- inactive recovery publisher template `042727fc6efae85bf34b0a6868cb7e2e86a662e6`
- inactive recovery science template `cb3735ab0529de79bd75bdb22d3391b8cf92e9f5`
- Stage-B live review workflow `88d13f71520091b7becad615f278461248561160`.

## Exact Stage B control repair

The frozen science workflow has a pre-solver defect in generic post-dispatch freshness construction:

- `preauthorization_surface.build_dispatch_surface(..., post_dispatch=True)` calls generic AVPS `failed_authorization_history()`;
- that helper was written for the earlier failed-authorization reuse phase;
- it refuses any consumed marker and dispatch branch before the downstream `freshness.validate_dispatch(..., post_dispatch=True)` can verify that exactly one legitimate current marker/branch exists.

Stage B is intentionally narrower than replacing the science guard.

The new helper must:

1. prove the preserved failed authorization head `67844e1dd2523963f2682f186387280dfb930760` is exactly the closed/unmerged #561 failed-review history;
2. prove failed review run `33109014744` was attempt 1 failure;
3. prove that failed head was never allocated and never ran science;
4. substitute only that failed-history subproof while invoking the original bound control-surface builder;
5. immediately restore the original helper;
6. call the **unchanged** frozen `freshness.validate_dispatch(..., post_dispatch=True)`;
7. feed that resulting surface to the **unchanged** frozen `science_guard.py` blob `c774be7ea8655854bb85071a9fb260e21498beda`.

The recovered surface must still prove:

- latest prior consumed scientific ordinal = 39;
- candidate ordinal = 40;
- zero prior AVPS science runs;
- zero prior execution-key use;
- no unexpected positive ordinal claims;
- authorization branch/head exact;
- dispatch branch/head exact;
- exactly one allocation marker;
- exactly one consumed marker;
- all repository surfaces inspected;
- live 72-seed reauthorization passed.

## Result boundary is stricter during recovery

Even after a later green Stage B activation, recovery transport may only execute the already-frozen 360 cases and create raw immutable case artifacts.

The Stage B recovery transport intentionally contains **no**:

- `aggregate_results` call;
- `open_results` call;
- Level-B result opening.

Its terminal job may only freeze exact-360 artifact metadata without downloading/interpreting scientific case contents.

Aggregate verification and result opening require a later separate reviewed gate.

## Stage B may not change

- scientific ordinal;
- authorization head/parent;
- seed allocation or seed values;
- 360-case universe;
- 72 CRN groups;
- 5 vertical states/group;
- vertical profiles;
- AOD values;
- OPAC family;
- wavelength grid;
- geometry;
- 20,000,000 photons/case;
- MYSTIC/libRadtran runtime identity;
- `F = 3.14`;
- analysis contrasts;
- result-opening rules;
- Taylor/Jerusalem fitting policy.

## Before any Stage B activation

Require BOTH on exact #574 head:

1. repository-wide non-scientific contract CI SUCCESS;
2. `.github/workflows/avps-v1-stage-b-post-consumption-surface-review.yml` SUCCESS, attempt 1.

The dedicated review must live-check:

- exact Stage A artifact;
- exactly one allocation marker;
- exactly one consumed marker;
- zero science;
- exact current auth/dispatch refs;
- live repository-global 72-seed freshness;
- recovered post-consumption surface;
- unchanged original post-dispatch freshness validator;
- unchanged science guard boundary;
- terminal proof that science still did not start during review.

If either review fails:

> Do not activate. Preserve the failed review head and correct only the demonstrated control defect on a new reviewed head.

---

# 1. AVPS scientific design remains frozen

Experiment:

- Aerosol Vertical-Profile Sensitivity v1 (AVPS v1)
- scientific ordinal 40.

Question:

> At fixed total AOD550 and fixed coherent OPAC rich optical family, how much does independently specified normalized aerosol vertical optical-depth shape change twilight radiance and the derived Level-B limiting-magnitude endpoint?

This is **not** a Taylor-fitting experiment.

Frozen vertical states from OPAC-derived templates:

1. continental average
2. maritime clean
3. desert
4. arctic
5. antarctic.

All five use the same rich OPAC `continental_average` optical family. The labels identify vertical templates only; they do not assert site aerosol microphysics.

Frozen design:

- AFGL-US;
- observer 0 m;
- surface albedo 0.15;
- 380–780 nm;
- reviewed 1-nm grid;
- MYSTIC spherical 1D;
- VROOM;
- MC standard-deviation evidence;
- 20,000,000 photons/case;
- Sun depression 2°, 4°, 6°, 8°;
- AOD550 0.10, 0.30;
- three geometries:
  - altitude 10°, relative azimuth 30°;
  - altitude 30°, relative azimuth 90°;
  - altitude 45°, relative azimuth 180°;
- 3 CRN replicates;
- 5 vertical states.

Cardinality:

- 72 CRN groups;
- 360 cases;
- 24 analysis cells;
- four 90-case shards;
- max-parallel 2/shard;
- maximum 8 concurrent case jobs.

Primary endpoints:

- photopic luminance;
- scotopic luminance;
- Johnson-V effective radiance.

Secondary:

- paired Level-B limiting-magnitude delta through the frozen current Crumey Eq.34 path with `F=3.14`.

No universal minute conversion.

No adaptive post-result cases.

---

# 2. AVPS already-merged foundation — DO NOT REBUILD

## #549 — MERGED
Reusable aerosol vertical-profile transport foundation.

Merge commit:

- `76e232523f29cfc64d3c50c0b3e922aa59d1dfe7`.

## #550 — MERGED
Exact-runtime capability gate proving OPAC coherent optical family + custom `aerosol_file tau` + fixed AOD can coexist.

Merge commit:

- `2be138d96d4e6d04b1e58dede27bb3f0130fc42e`.

Capability run:

- `33095258477`
- artifact `9656112795`
- digest `sha256:870ee009131c3b6c737dde70bfa4ad7c4a7e85a7d91cd4b4012f2f36e23f2098`.

## #551 — MERGED
AVPS preregistration.

Merge commit:

- `b882034629894d2629ec60ef15f46e83635d6f7e`.

## #552 — MERGED
Unseeded 360-case / 72-group execution skeleton.

Merge commit:

- `79fd4605e02068f0d798181e2b05459d708bfebc`.

## #557 — MERGED
Disabled AVPS execution package.

Merge commit:

- `d206a098ad6fee1bf6513460d29c949eadb695d1`.

Exact normalized tau hashes:

- continental average `e6c296951dfae376bf77948aa92828062ba95d7b1e9c28703befa9cffb5bf198`
- maritime clean `5cbaf5f81f3f36bfcf9b365eaa5d892889da83453c18d58e705b3de9273adc8c`
- desert `3d8891b3b67fa8c8c6fd66861d49e9bfad8c937a176b7001c6c47a5571de21ad`
- arctic `61eed1e73ac8cc6f044b89870a6874f1d21500008c7747830a2a812bbd87919a`
- antarctic `a14460a04afd5154d931b77e55b7adce2ab41aae2e8e4c13afaa0de459aff164`.

Exact AFGL profile bundle artifact:

- `9658061526`
- digest `sha256:2061136f069e9a16fa5c5b3d0991121bb04d7a268d1b7c7f93c60d734d537b48`.

## #558 — MERGED
Authorization-control framework.

## #559 — MERGED
AVPS execution / publisher / science / analysis control package.

Merge commit:

- `107d63a01de96bc359af0ecd8f0129b7232ddcf1`.

## #562 — MERGED
Failed-authorization ordinal-reuse recovery + Actions stabilization control.

Merge commit:

- `cd56db1e823a75d617c026fecf359a80e8c64cb7`.

## #563 — MERGED
Mode-only fresh-attempt trigger; no content change.

Merge commit/current frozen main:

- `99ade7798627e67921139697ba1a004fa8a304bb`.

---

# 3. Operational Atmosphere State v2 — MERGED FOUNDATION

## #120 — MERGED
Operational Atmosphere State v2 design.

Merge commit:

- `0ef878a78f792edc7a484de8ace8a196be1543cb`.

## #121 — MERGED
Operational Atmosphere State v2 data/QC/provenance foundation.

Merge commit:

- `e0da52eb0a2d5bac333da6572f51df52ea7e676e`.

It supports:

- component-level provenance;
- service provider vs underlying scientific source;
- spectral AOD / AOD550;
- vertical aerosol profiles;
- SSA / phase / g / classification containers;
- explicit missing/approximated/rejected/conflict state;
- negative-value and malformed-profile rejection;
- all-zero extinction + nonzero matching AOD rejection;
- stable provenance fingerprint;
- explicit v2 -> v1 projection.

Important:

> Rich vertical/SSA/phase fields are represented, but arbitrary richer v2 fields are **not yet generally consumed by production Level-B**.

AVPS is part of determining whether/how vertical profile needs a new fast-model dimension.

---

# 4. Taylor — current authoritative interpretation

Taylor Ann Arbor remains a direct-MYSTIC real-sky validation case, not a parameter-fitting target.

Key result:

At Sun depression about `−5.808°`:

- old residual `+0.393 mag`
- independently obtained CAMS-profile run `+0.087 mag`.

At `−6.134°`:

- old residual `+0.388 mag`
- CAMS-profile run `+0.031 mag`.

Total AOD and other frozen conditions were retained; no SQM offset or AOD was fitted.

Scientific interpretation:

> Aerosol vertical distribution materially affects twilight radiance. A large part of the former ~6° discrepancy was not evidence of a gross basic MYSTIC failure.

Do not say the exact Taylor atmosphere is known.

Do not choose an AVPS profile because it best matches Taylor.

---

# 5. Taylor uncertainty / CAMS boundary

Empirical multi-seed MYSTIC scatter rises late in twilight. Early/middle rows are much better converged than the final rows.

Do not use old broadband `mc.rad.std.spc` as a calibrated uncertainty estimate.

Do not reuse the old large Taylor AOD finite-difference derivative: it remains unresolved.

CAMS same-cycle column quantities around Taylor were approximately:

- AOD550 ~0.31–0.32
- SSA550 ~0.95
- g550 ~0.71
- Ångström alpha ~1.28.

But direct forecast00 vertical extinction returned 137 exact zero coefficients despite nonzero column AOD. Treat that profile as invalid, not aerosol-free reality.

Forecast03 produced usable profiles, but do not call a substituted cycle `same-cycle full CAMS atmosphere` unless scientifically justified in advance.

---

# 6. Independent Taylor atmosphere search — separate lane

A separate worker/lane owns:

- EarthCARE / ATLID;
- ground lidar / ceilometer;
- AERONET;
- other independent aerosol archives.

Do not duplicate unless explicitly asked.

If a new Taylor atmosphere source is found:

1. freeze source/product/time/distance/quality rules first;
2. archive exact provenance;
3. determine whether measured/retrieved/modelled;
4. determine independence from CAMS/HRRR;
5. freeze mapping;
6. only then inspect Taylor residual.

---

# 7. Previously closed aerosol-optics campaigns — DO NOT DUPLICATE

Scientific ordinals already used:

- AOPS = 37
- AFPF = 38
- ASIV = 39
- AVPS = 40.

AOPS/AFPF/ASIV already address, for their scopes:

- SSA/scalar-g sensitivity;
- coherent full OPAC phase-function / aerosol-family sensitivity;
- scalar + derived-Level-B scenario interpolation;
- fast aerosol-family scenario envelope.

Do not start generic SSA/g/phase/aerosol-family work again from scratch.

The active missing atmosphere dimension is specifically vertical structure and its fast-model consumption.

---

# 8. Transient adaptation — still unresolved

## #119 — MERGED
Frozen Crumey Eq.34 non-monotonic diagnostic.

## #116 — OPEN / DO NOT MERGE
Proposed equilibrium floor for negative transient penalty.

## #117 — OPEN SCIENTIFIC QUESTION
Need external psychophysics and actual Level-B trajectory characterization before changing semantics.

Do not merge #116 merely because old tests passed.

---

# 9. F / mesopic / human threshold

Keep:

- `F = 3.14`.

Lower F makes stars visible earlier, so it cannot fix an already-too-early concern.

MES2 effect previously found small:

- Tishrei about +17.8 s
- Tammuz 0 s.

Do not recalibrate human threshold from Taylor or Jerusalem.

---

# 10. Moon / natural night / artificial sky

Moon #459 and Natural #460 remain Draft/incomplete.

Artificial skyglow still needs a directional radiance provider.

Total-sky compositor #112 is already merged; do not rebuild it.

No unfinished background provider may be silently promoted to trusted production.

---

# 11. Master closure PR #539

PR #539 remains the intended long-term master closure record.

It should be refreshed after AVPS Stage B reaches a stable terminal checkpoint. Do not mutate it during a repository-global freshness scan.

Once safe, record at minimum:

- Stage A successful recovery run/artifact;
- PR #574 Stage B review;
- whether Stage B review/activation passed or failed;
- exact science-run identity if science eventually starts;
- exact-360 result-opening gate if science eventually completes.

Do not let transient handoffs compete permanently with #539.

---

# 12. Immediate next actions

## P0 — finish Stage B review

1. Watch exact #574 head `9a3390d27963359c7c39b1762a1b8eec90e24185`.
2. Require repository-wide non-scientific contract SUCCESS.
3. Require Stage-B post-consumption surface review SUCCESS, attempt 1.
4. Verify dedicated review artifact and live receipt.
5. Reconfirm zero AVPS science runs before activation.

If any check fails:

- do not rerun GitHub attempt 2;
- preserve failed head/history;
- correct only the demonstrated control defect in a new Draft review.

## P0 — if Stage B review passes

Build a fresh activation chain from frozen main without merging the review PR:

- copy only the exact reviewed inactive recovery publisher/science template bytes into activation control commits;
- keep the actual authorization/dispatch branch at the original authorization head;
- do not create a new ordinal, new allocation marker, new consumed marker, or new seed set;
- require one-shot attempt-1 workflow history;
- perform live seed repository-global recheck before solver;
- pass recovered post-consumption surface to the unchanged science guard.

Before triggering science, re-prove:

- `main` unchanged;
- #565 Draft/open/unmerged;
- #574 Draft/open/unmerged;
- Stage A artifact exact;
- exactly one allocation marker;
- exactly one consumed marker;
- zero prior science;
- authorization head = dispatch head;
- all scientific hashes unchanged.

## P0 — if science starts

Do not use GitHub rerun/retry/resume.

Run exactly the frozen 360 cases with the frozen 72 CRN seeds and runtime identity.

During recovery, do not open results automatically.

First terminal science target is only:

> exact 360 immutable case artifacts + metadata freeze.

Then create a separate review for aggregate verification and result opening.

---

# 13. Absolute DO-NOT list

Do not:

- move live main while current authorization parent must stay live;
- reuse or reallocate ordinal 40;
- post a second allocation marker;
- post a second consumed marker;
- push a second dispatch branch identity;
- create new AVPS seeds;
- change any AVPS scientific parameter during recovery;
- change F=3.14;
- change AOD/profile/SSA/phase based on Taylor;
- change case cardinality;
- change photon histories;
- change runtime identity;
- open partial results;
- alter cases after seeing outputs;
- use GitHub rerun/retry/resume after a scientific attempt;
- merge Draft review PRs simply to activate recovery;
- merge #116 before #117 science is resolved;
- claim Taylor proves exact atmosphere knowledge;
- claim v2 rich atmosphere is already universally consumed by Level-B.

---

# 14. One-line live status

> **AVPS scientific ordinal 40 is already allocated and consumed, Stage A has successfully reconstructed valid zero-runtime publisher evidence without repeating consumption, and Stage B PR #574 is now reviewing the narrow consumed-state freshness repair needed before any first AVPS MYSTIC science run; no AVPS science result exists yet.**
