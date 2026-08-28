# STAR VISIBILITY / MYSTIC — CURRENT NEW-WORKER HANDOFF

**Current status: 2026-08-27/28 — AVPS ordinal 40 is allocated+consumed; Stage A recovery is complete; Stage B live post-consumption surface review passed, but repository-wide contract still blocks activation on one defense-in-depth seed-identity assertion. No AVPS science has run yet.**

This file is the current standalone handoff for the non-observation computational/scientific work. It supersedes earlier intermediate checkpoints on this handoff branch.

---

# 0. READ THIS FIRST — exact live checkpoint

Repository:

- `search-maker/twilight-mystic-experiments`

Frozen live `main`:

- `99ade7798627e67921139697ba1a004fa8a304bb`
- merge commit of PR #563.

**Do not move `main` while ordinal-40 recovery/science remains tied to the existing authorization parent.**

Authorization PR:

- PR #565 — Draft/open/unmerged
- authorization head `338ee82c8e088e929f45782b1f7ac1c3aaaaa533`
- parent/live-main binding `99ade7798627e67921139697ba1a004fa8a304bb`
- authorization JSON Git blob `91c2fcfe0536f7289b9da3c597428c546523571a`
- authorization JSON SHA-256 `bec00d3a5609794fbb1078abb2c8ec6cf901318f5e9e80f38c387fab886dae97`
- authorization review run `33113256151`, attempt 1, SUCCESS
- review artifact `9663887142`
- digest `sha256:3edff7740ca35832bbca0cfcba096aa3d9963d9b6c19044d867a2b3c9f09a47c`.

Preauthorization:

- exact-main run `33111875371`, attempt 1, SUCCESS
- artifact `9663132186`
- digest `sha256:1253612ffe4ba228e319f6b063256abd7340d11eec76981db4cc39a3619b2df6`
- 72 candidate seeds proven fresh at that gate.

Issue 60 contains exactly one allocation marker:

`ORDINAL40_AVPS_V1_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED commit=338ee82c8e088e929f45782b1f7ac1c3aaaaa533 parent=99ade7798627e67921139697ba1a004fa8a304bb pr=565`

and exactly one consumed marker:

`ORDINAL40_AVPS_V1_DISPATCH_CONSUMED`

Therefore:

> **Scientific ordinal 40 is allocated and consumed. Never reuse, reallocate, retire-as-unused, or consume it again.**

Dispatch branch:

- `dispatch/aerosol-vertical-profile-sensitivity-v1-ordinal-40`
- immutable head `338ee82c8e088e929f45782b1f7ac1c3aaaaa533`.

Current hard fact:

- **zero AVPS science workflow runs exist on the logical dispatch branch**;
- no AVPS MYSTIC/uvspec case has been executed yet;
- no AVPS scientific result has been opened.

---

# 0A. Stage A publisher-evidence recovery — COMPLETE

Original publisher:

- run `33114653044`, attempt 1, failure
- request/status head `8708a0f8a2fa86c5c13b27c94517552b0bf7dc2a`
- preserved history ref exists.

The original publisher had already:

1. passed pre-dispatch checks;
2. created the dispatch branch at the authorization head;
3. posted the consumed marker exactly once.

It then failed in post-dispatch verification because generic failed-authorization reuse logic rejected the now-legitimate consumed marker:

`GlobalOrdinalRefusal: ordinal 40 already has consumed marker`

This was a control-plane failure after identity consumption, not a science failure.

Final Stage A review:

- PR #573 — Draft/open/unmerged
- review head `352f226d87d570a7338bf2730872a7733179da74`
- reviewed template blob `821cd234ffd1253905839834d1afeafa91bdcdfd`
- review run `33122607199`, attempt 1, SUCCESS.

Final Stage A activation chain:

- control commit `c580002b0b30c9ee48a4bf7f88edd83c930e0044`
- request/status head `14a2d1272d8e81383e0fb4f830fceef5647d985c`.

Successful Stage A publisher-evidence run:

- run `33123226959`
- attempt 1
- job `98695045355`
- head `14a2d1272d8e81383e0fb4f830fceef5647d985c`
- conclusion **SUCCESS**.

Artifact:

- id `9667291127`
- name `avps-v1-dispatch-publisher-ordinal-40`
- digest `sha256:0338d418d554c5ceaead8712a1ee860c2ee154d839cfe7c038098607786a0b3f`.

Receipt status:

- `DISPATCH_PUBLISHED_ZERO_RUNTIME`

Recovery receipt:

- `POST_CONSUMPTION_PUBLISHER_RECOVERY_PASS_NO_SECOND_CONSUMPTION_NO_SCIENCE_TRIGGER`

Proved:

- no second git push;
- no second consumed marker;
- no second allocation;
- no science dispatch;
- no scientific runtime;
- no solver.

**Stage A is closed. Do not reopen it.**

---

# 0B. Stage B — consumed-state science-preflight recovery

Purpose:

> Repair only the broken generic post-dispatch failed-authorization-history admission subproof, while keeping the original freshness validator, science guard, scientific experiment, seeds, runtime, and result-opening rules frozen.

Current PR:

- PR #574 — `Review AVPS Stage B consumed-state science recovery`
- Draft/open/unmerged
- branch `review/avps-v1-ordinal40-stage-b-science-recovery-control-1`
- frozen base main `99ade7798627e67921139697ba1a004fa8a304bb`.

The Stage-B helper:

1. proves preserved failed authorization head `67844e1dd2523963f2682f186387280dfb930760`;
2. proves #561 was closed/unmerged;
3. proves review run `33109014744` was attempt-1 failure;
4. proves that failed head itself was never allocated and never ran science;
5. substitutes only that failed-history subproof while using the original bound control-surface builder;
6. restores the original helper immediately;
7. calls unchanged `freshness.validate_dispatch(..., post_dispatch=True)`;
8. feeds the recovered surface to unchanged `science_guard.py` blob `c774be7ea8655854bb85071a9fb260e21498beda`.

The scientific recovery transport remains result-closed:

- it may eventually execute only the frozen 360 cases;
- it may create immutable raw case artifacts;
- it may freeze exact-360 artifact metadata;
- it contains no `aggregate_results` call;
- no `open_results` call;
- no Level-B result opening;
- scientific interpretation requires a later separately reviewed gate.

---

# 0C. First Stage-B live review — transport failure only

Original Stage-B review head:

- `9a3390d27963359c7c39b1762a1b8eec90e24185`.

Dedicated review run:

- `33130501045`
- attempt 1
- job `98718644744`
- failure.

All unit/binding checks before the live seed scan passed.

Failure occurred inside repository-global seed scanning while fetching GitHub Actions metadata:

`urllib.error.HTTPError: HTTP Error 502: Bad Gateway`

Interpretation:

- not a seed collision;
- not a freshness refusal;
- not a science-model failure;
- not a solver failure;
- no science started.

No GitHub rerun attempt 2 was used.

---

# 0D. Bounded transport-retry review correction

The Stage-B **review workflow only** was hardened with a bounded transport retry:

- maximum 3 complete scanner attempts;
- all within workflow `run_attempt=1`;
- retry only for HTTP 5xx / transport exceptions;
- collision, snapshot drift, authorization refusal, or any other semantic failure remains terminal immediately;
- no `gh run rerun`;
- no GitHub run attempt 2.

Exact final corrected review head before the next defense-in-depth fix:

- `8d9bd70d1c666b84588a1e33fff14dd71c81a46e`.

Delta from `9a3390d...` was exactly two files:

1. `.github/workflows/avps-v1-stage-b-post-consumption-surface-review.yml`
2. `tests/test_avps_v1_stage_b_post_consumption_surface.py`.

No helper, science, protocol, seed, case, runtime, or result semantics changed.

---

# 0E. Dedicated Stage-B live review on `8d9bd70d...` — SUCCESS

Dedicated run:

- `33132159457`
- attempt 1
- exact head `8d9bd70d1c666b84588a1e33fff14dd71c81a46e`
- job `98724047576`
- conclusion **SUCCESS**.

All substantive steps passed:

1. review unit contract;
2. exact frozen authorization checkout;
3. live main/auth/dispatch/Stage-A identity binding;
4. **live 72-seed authorization recheck — SUCCESS**;
5. recovered post-dispatch freshness surface — SUCCESS;
6. unchanged original freshness validator — SUCCESS;
7. review evidence persistence — SUCCESS;
8. terminal proof of zero science — SUCCESS.

Therefore the earlier 502 was truly transient transport noise; no candidate seed collision was found.

Important:

> This successful dedicated review does **not** by itself authorize activation, because the repository-wide contract on the same exact head still failed one regression.

---

# 0F. Repository-wide contract on `8d9bd70d...` — ONE FAILING DEFENSE-IN-DEPTH ASSERTION

Run:

- `33132159464`
- attempt 1
- exact head `8d9bd70d1c666b84588a1e33fff14dd71c81a46e`
- job `98723936574`
- conclusion failure.

The full suite ran 1015 tests:

- only **one failure**;
- 3 skipped;
- all other Stage-B transport/surface tests passed.

Failing test:

`test_avps_v1_stage_b_recovery_transport.AvpsStageBRecoveryTransport.test_exact_science_identity_is_frozen`

Failing assertion:

`self.assertIn("candidateSeedCanonicalSha256", ST)`

where `ST` is the inactive Stage-B recovery science workflow template.

The recovery science template already:

- builds a live seed-authorization proof;
- passes it into the unchanged frozen `science_guard.py`;
- and the unchanged science guard itself explicitly checks both:
  - `candidateSeedCanonicalSha256`
  - `candidateRowsCanonicalSha256`
  against the authorization document.

Nevertheless the repository-wide regression deliberately requires the recovery template itself to carry an explicit seed-identity check as defense in depth.

**Decision: do not weaken the test.**

Next correction:

- add explicit checks in the inactive Stage-B recovery science template, immediately after live seed proof construction, requiring:
  - `candidateSeedCanonicalSha256 = a2e22b526dfad84d4f23c0ca8b143d028fddc7e55f78deb93a43e194ebd6c35e`
  - `candidateRowsCanonicalSha256 = f22de8a9e30ba106759effb1170a5ca1d1e747cb2ac68293fa232dc7ed6ca683`.

This is defense-in-depth only. It must not change:

- candidate seed values;
- seed allocation;
- 360-case universe;
- CRN pairing;
- scientific inputs;
- runtime;
- solver;
- result-opening policy.

After that one template change, require fresh **attempt-1** runs on the new exact PR head for BOTH:

1. dedicated Stage-B post-consumption surface review;
2. repository-wide non-scientific contract.

Do not activate from `8d9bd70d...` because both gates were not green on the same exact head.

---

# 0G. Repository-state safety note

During Stage-B review work a few accidental placeholder commits were briefly created on review/main refs by a file-write tooling glitch. They were immediately removed by ref reset.

Current authoritative state was re-verified:

- live `main` = `99ade7798627e67921139697ba1a004fa8a304bb`;
- authorization/dispatch heads unchanged;
- allocation/consumed marker cardinality unchanged;
- no AVPS science workflow run was created by those placeholder pushes.

Those temporary pushes produced only repository-wide contract activity and did not cross the scientific execution boundary.

Do not treat the abandoned placeholder commit SHAs as scientific/control identities.

---

# 1. AVPS scientific design — FROZEN

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

All five use the same OPAC `continental_average` rich optical family. The labels denote vertical templates only.

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
- geometries:
  - 10° altitude / 30° rel azimuth
  - 30° / 90°
  - 45° / 180°;
- 3 CRN replicates;
- 5 vertical states.

Cardinality:

- 72 CRN groups;
- 360 cases;
- 24 analysis cells;
- four 90-case shards;
- max-parallel 2 per shard;
- max 8 concurrent case jobs.

Primary endpoints:

- photopic luminance;
- scotopic luminance;
- Johnson-V effective radiance.

Secondary:

- paired Level-B limiting-magnitude delta through frozen Crumey Eq.34 path with `F=3.14`.

No universal minute conversion.

No adaptive post-result cases.

---

# 2. AVPS already-merged foundations — DO NOT REBUILD

- #549 merged — vertical-profile transport foundation — `76e232523f29cfc64d3c50c0b3e922aa59d1dfe7`
- #550 merged — OPAC + custom tau exact-runtime capability — `2be138d96d4e6d04b1e58dede27bb3f0130fc42e`
- #551 merged — AVPS preregistration — `b882034629894d2629ec60ef15f46e83635d6f7e`
- #552 merged — unseeded 360-case skeleton — `79fd4605e02068f0d798181e2b05459d708bfebc`
- #557 merged — disabled execution package — `d206a098ad6fee1bf6513460d29c949eadb695d1`
- #558 merged — authorization-control framework
- #559 merged — execution/publisher/science controls — `107d63a01de96bc359af0ecd8f0129b7232ddcf1`
- #562 merged — failed-auth recovery/stabilization — `cd56db1e823a75d617c026fecf359a80e8c64cb7`
- #563 merged — mode-only fresh-attempt trigger/current frozen main — `99ade7798627e67921139697ba1a004fa8a304bb`.

Exact normalized tau SHA-256:

- continental average `e6c296951dfae376bf77948aa92828062ba95d7b1e9c28703befa9cffb5bf198`
- maritime clean `5cbaf5f81f3f36bfcf9b365eaa5d892889da83453c18d58e705b3de9273adc8c`
- desert `3d8891b3b67fa8c8c6fd66861d49e9bfad8c937a176b7001c6c47a5571de21ad`
- arctic `61eed1e73ac8cc6f044b89870a6874f1d21500008c7747830a2a812bbd87919a`
- antarctic `a14460a04afd5154d931b77e55b7adce2ab41aae2e8e4c13afaa0de459aff164`.

Exact AFGL profile bundle:

- artifact `9658061526`
- digest `sha256:2061136f069e9a16fa5c5b3d0991121bb04d7a268d1b7c7f93c60d734d537b48`.

---

# 3. Operational Atmosphere State v2 — MERGED FOUNDATION

- #120 merged design — `0ef878a78f792edc7a484de8ace8a196be1543cb`
- #121 merged implementation — `e0da52eb0a2d5bac333da6572f51df52ea7e676e`.

Supports:

- component provenance;
- provider vs underlying scientific source;
- spectral AOD/AOD550;
- vertical aerosol profiles;
- SSA/phase/g/classification containers;
- missing/approximated/rejected/conflict states;
- physical QC;
- explicit v2→v1 projection.

Important:

> Rich v2 fields are represented, but arbitrary richer atmosphere is not yet universally consumed by production Level-B.

AVPS informs whether/how vertical profile requires an explicit fast-model dimension.

---

# 4. Taylor — authoritative interpretation

Taylor Ann Arbor remains a direct-MYSTIC real-sky validation case, not a fitting target.

Key result:

At Sun depression about `−5.808°`:

- old residual `+0.393 mag`
- independently obtained CAMS-profile run `+0.087 mag`.

At `−6.134°`:

- old residual `+0.388 mag`
- CAMS-profile run `+0.031 mag`.

Total AOD and other frozen conditions were retained; no SQM offset or AOD was fitted.

Conclusion:

> Aerosol vertical distribution materially affects twilight radiance. The former ~6° discrepancy was not clean evidence of a gross basic MYSTIC failure.

Do not claim the exact Taylor atmosphere is known.

Do not choose an AVPS profile because it best matches Taylor.

---

# 5. Taylor uncertainty / CAMS boundary

- empirical MYSTIC scatter rises late;
- do not use old broadband `mc.rad.std.spc` as calibrated uncertainty;
- old large AOD finite-difference derivative remains unresolved.

CAMS same-cycle columns approximately:

- AOD550 0.31–0.32
- SSA550 0.95
- g550 0.71
- Ångström alpha 1.28.

But forecast00 vertical extinction returned 137 exact zeros despite nonzero AOD. Treat that profile as invalid, not aerosol-free air.

---

# 6. Independent Taylor atmosphere search — separate lane

Another worker/lane owns:

- EarthCARE / ATLID;
- ground lidar / ceilometer;
- AERONET;
- other independent aerosol archives.

Do not duplicate unless asked.

Freeze source/product/time/distance/quality rules before Taylor scoring.

---

# 7. Closed aerosol-optics work — DO NOT DUPLICATE

Scientific ordinals:

- AOPS = 37
- AFPF = 38
- ASIV = 39
- AVPS = 40.

AOPS/AFPF/ASIV already cover their generic SSA/g/full-phase/family/interpolation scopes.

Do not restart those generic campaigns.

---

# 8. Transient adaptation — unresolved

- #119 merged frozen diagnostic
- #116 open — do not merge
- #117 scientific mapping unresolved.

Need external psychophysics + actual Level-B trajectory characterization before semantic change.

---

# 9. Human threshold / F / mesopic

Keep:

- `F = 3.14`.

Lower F makes visibility earlier and cannot fix an already-too-early concern.

MES2 effect previously small:

- Tishrei ~+17.8 s
- Tammuz 0 s.

Do not recalibrate from Taylor/Jerusalem.

---

# 10. Moon / natural / artificial sky

- Moon #459 Draft/incomplete
- Natural #460 Draft/incomplete
- artificial skyglow still needs directional provider
- total-sky compositor #112 already merged.

Do not promote incomplete components to trusted production.

---

# 11. Master closure PR #539

#539 remains the long-term closure source of truth.

Do not mutate it during a repository-global freshness scan.

After Stage B reaches a stable terminal checkpoint, update it with:

- Stage A success run/artifact;
- Stage-B 502 attempt;
- bounded transport retry correction;
- dedicated Stage-B live PASS;
- repository-wide regression correction and final exact-head gate status;
- science run identity if/when science actually begins;
- exact-360 metadata/result-opening gates later.

---

# 12. IMMEDIATE NEXT ACTIONS

## P0-A — close the one repository-contract regression

On PR #574:

1. change only the inactive recovery science template;
2. immediately after building `live-seed-authorization-proof.json`, explicitly assert the frozen candidate seed and row canonical hashes;
3. do not change helper, seeds, science guard, scientific design, runtime, cases, or result opening;
4. compare against `8d9bd70d...` and require the intended minimal delta.

## P0-B — fresh exact-head review

On the new exact PR head require BOTH:

- dedicated Stage-B review SUCCESS, attempt 1;
- repository-wide non-scientific contract SUCCESS, attempt 1.

Do not use GitHub rerun attempt 2.

Do not update this handoff while the repository-global seed scan is actively running.

## P0-C — only after both gates are green

Verify the exact dedicated review artifact and re-read live state:

- main still `99ade779...`;
- #565 Draft/open/unmerged;
- Stage-A and Stage-B review PRs exact;
- allocation marker count = 1;
- consumed marker count = 1;
- dispatch head = authorization head;
- zero prior science;
- scientific hashes unchanged.

Then create a separate activation chain from frozen main using exact reviewed inactive templates.

Do not merge #574 merely to activate it.

## P0-D — if Stage-B science finally starts

- one-shot only;
- no rerun/retry/resume of scientific attempt;
- exact 360 frozen cases;
- exact 72 frozen CRN seeds;
- exact runtime/OPAC/tau profile identity;
- first terminal target = immutable raw 360 artifacts + metadata-only closure.

Do **not** open results in that recovery science run.

Aggregate verification and result opening come in a separate later reviewed gate.

---

# 13. ABSOLUTE DO-NOT LIST

Do not:

- move live main during this authorization lifecycle;
- reuse/reallocate ordinal 40;
- post second allocation/consumed markers;
- recreate dispatch identity;
- create new AVPS seeds;
- alter case cardinality, CRN pairing, profiles, AOD, optics, wavelength grid, geometry, photons, runtime, F, or analysis contrasts;
- choose parameters from Taylor/Jerusalem residuals;
- weaken the 72-seed global collision audit;
- convert the 502 transport retry into semantic retry;
- use GitHub run attempt 2 for scientific authorization/review identity;
- open partial results;
- aggregate/interpret Stage-B raw results inside the recovery science workflow;
- merge review PRs merely for activation;
- merge #116 before #117 is resolved.

---

# 14. One-line live status

> **AVPS ordinal 40 is already allocated and consumed; Stage A zero-runtime publisher recovery is complete; the Stage-B consumed-state surface itself has now passed a live exact-head review with a fresh 72-seed global recheck, but activation remains blocked until one repository-wide defense-in-depth regression is fixed and both gates pass on the same new exact head; no AVPS MYSTIC science has run yet.**
