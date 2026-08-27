# STAR VISIBILITY / MYSTIC — CURRENT NEW-WORKER HANDOFF

**Current status: 2026-08-27, after merge of AVPS disabled execution package #557**

This file **supersedes the earlier 2026-08-27 handoff**. It is a standalone handoff for continuing the non-observation computational/scientific work without repeating closed lanes or crossing scientific-control boundaries.

---

# 0. Exact current checkpoint

## `search-maker/twilight-mystic-experiments`

Current relevant `main` checkpoint:

- `d206a098ad6fee1bf6513460d29c949eadb695d1`
- this is the merge commit of PR #557, `Freeze disabled aerosol vertical-profile execution package`.

Exact-main preauthorization rerun triggered automatically by #557:

- workflow run: `33100194996`
- exact main: `d206a098ad6fee1bf6513460d29c949eadb695d1`
- attempt: 1
- status **at handoff creation**: still in progress
- already passed:
  - exact-main checkout identity
  - zero-runtime / attempt-1 proof
  - deterministic preauthorization control tests
  - deterministic candidate-ledger reconstruction
  - exact-main tracked-tree candidate-seed scan
- currently running:
  - repository-global candidate-seed recheck
- still pending:
  - live seed authorization proof
  - fresh global ordinal derivation
  - artifact publication
  - Issue 60 terminal non-allocation checkpoint

**Therefore right now:**

- scientific ordinal 40 is **NOT allocated**;
- the 72 candidate CRN seeds are **NOT allocated or applied to cases**;
- no scientific dispatch exists;
- no AVPS MYSTIC science run has been authorized;
- no AVPS scientific result has been opened.

An earlier exact-main preauthorization run (`33097615139`) had shown ordinal 40 as the next candidate and all 72 candidate seeds fresh with zero tracked-tree/repository-global collisions. That proof was deliberately invalidated by the later merged science/execution package. **Do not use the old proof to authorize execution.**

---

# 1. Project goal

The project predicts when an individual star becomes visible to the human eye during twilight.

Distinct layers include:

1. astronomical geometry;
2. twilight sky radiance;
3. stellar direct atmospheric transmission;
4. aerosol and molecular atmosphere;
5. human point-source threshold;
6. spectral/mesopic effects;
7. transient adaptation;
8. Moon / natural night / artificial sky background.

High-fidelity reference: **MYSTIC / libRadtran**.

Fast application model: **Level-B**.

Central lesson:

> Accurate twilight prediction requires both a validated radiative-transfer model and an independently known atmosphere for the requested place/time.

---

# 2. Global scientific rules — DO NOT VIOLATE

- `F = 3.14` remains the current default.
- transient `tau = 30 s` remains experimental only.
- Do not tune F, tau, AOD, aerosol profile, provider, forecast cycle, sky offset, threshold, interpolation/support, or another environmental parameter to force a desired Jerusalem/Taylor time.
- Do not select an atmospheric dataset/cycle/provider because it minimizes Taylor residuals.
- Freeze external/environmental inputs before target scoring whenever possible.
- No universal magnitude correction.
- No universal minute correction.
- Do not infer aerosol family from AOD alone.
- Do not fabricate missing vertical aerosol structure.
- Missing/invalid material atmosphere data must remain explicit and fail closed or reduce confidence.
- Do not call modeled fields measurements.
- A CAMS republisher is not an independent scientific source from CAMS.
- No `humanFirstSeeingValidated` claim without independent human evidence.
- Taylor mainly validates **direct MYSTIC**, not Level-B or human first-seeing.
- Pandora/Izaña remain unopened unless separately authorized.
- matched-stellar v1 is obsolete.
- Do not reopen the closed 90° MYSTIC/stellar campaign.

---

# 3. Important `starsvisibility` status

## #114 — MERGED
`Route validated Level-B sky + stellar support through exact zenith`

Validated sky + stellar v3.2 support now reaches physical 90° while preserving old <=80° behavior. Do not reopen this campaign.

## #118 — MERGED
Clean-checkout/current-main Level-B test lifecycle fix. Infrastructure only.

## #119 — MERGED
`Freeze Crumey Eq.34 transient equivalent-background transition diagnostic`

Frozen diagnostic:

- local maximum near `B = 0.0215673 cd/m²`
- local minimum near `B = 0.0470526 cd/m²`
- threshold drop ≈ `2.6009%`
- maximum formal negative adaptation penalty ≈ `−0.02861 mag`

The current fail-closed behavior remains the frozen diagnostic baseline.

## #116 — STILL OPEN / DO NOT MERGE YET
`Fix transient negative-penalty topology artifact`

#116 changes semantics exactly in the region frozen by #119. Before any merge:

1. reconcile with current main;
2. reconcile with #119 and issue #117;
3. decide scientifically whether the equilibrium-floor behavior is the correct replacement;
4. characterize actual `(physical B, adaptation state/debt, effective B)` trajectories;
5. use external psychophysics for model selection;
6. preregister the semantic decision;
7. run full post-decision timing audit;
8. exact-head parity/build;
9. merge only after the semantic decision itself is reviewed.

The old #116 patch is not merely a software cleanup: it floors negative transient penalties to equilibrium, which is a physiological/model semantic choice.

## #117 — PHYSICAL QUESTION STILL OPEN

Main question:

> Is “physical detection background + equivalent adaptation luminance debt” the correct physical mapping through the Crumey threshold relation?

Do not change production transient semantics until external psychophysical evidence supports the model decision.

---

# 4. Operational Atmosphere State v2 — MERGED FOUNDATION

This was a P0 proposal in the prior handoff; it is now real merged foundation.

## #120 — MERGED
`Design Operational Atmosphere State v2`

Merge commit:

- `0ef878a78f792edc7a484de8ace8a196be1543cb`

Accepted Gate-A design. It establishes:

- component-level provenance;
- service provider != underlying scientific source;
- spectral AOD / canonical AOD550;
- vertical aerosol profiles;
- SSA / phase / asymmetry / aerosol classification;
- molecular / surface / cloud component status;
- explicit present/missing/approximated/rejected/conflict semantics;
- no fabricated vertical structure;
- temporal modes for historical/current/future dates;
- physical cross-component QC;
- explicit atmosphere quality/provenance concept;
- deliberate v2 -> v1 projection;
- Level-B atmosphere consumption as a separate validation problem.

## #121 — MERGED
`Add Operational Atmosphere State v2 foundation`

Merge commit:

- `e0da52eb0a2d5bac333da6572f51df52ea7e676e`

Independent broad exact-head verification:

- exact head: `de44958a62704c3236ff24294c0639b3868803aa`
- run: `33094168008`

Implemented foundation includes:

- typed request/provenance;
- spectral AOD + AOD550;
- vertical aerosol profile representation;
- SSA / phase / g / aerosol classification containers;
- rejection of negative AOD/extinction;
- rejection of malformed/non-monotone profiles;
- rejection of invalid SSA/g;
- rejection of all-zero vertical extinction with matching nonzero column AOD;
- optional preregistered profile-integral/column-AOD conflict policy;
- stable provenance-bearing fingerprint;
- independent-scientific-source counting;
- fallback-history preservation;
- explicit v2 -> v1 projection stating that richer v2 fields are **not yet consumed by current Level-B**.

This is a representation/QC/provenance foundation, **not** a validated arbitrary-profile fast Level-B mapper.

---

# 5. Old Draft PR #48 — disposition

`starsvisibility #48 — Add Level-B runtime integration foundation` remains an old stacked Draft.

Do **not** merge/replay it wholesale.

Audit showed that important v1 atmosphere foundation files are already present in current main, including:

- `atmosphere-state.mjs`
- `atmosphere-resolver.mjs`
- `open-meteo-cams-atmosphere.mjs`
- `aeronet-atmosphere.mjs`
- acquisition tests

Current-main regression also hash-binds important PR #48 files.

Conclusion:

> Continue from current main. Treat #48 as historical/stacked context, not a package to re-import.

---

# 6. Taylor — authoritative scientific interpretation

Observation:

- Ann Arbor, Michigan
- 2025-08-07
- approx `42.256 N, 83.709 W`
- original Unihedron SQM at zenith

The conclusion is **not** “we know the exact Taylor atmosphere.”

The current conclusion is:

> Direct MYSTIC is broadly consistent with Taylor, and much of the old ~6° discrepancy was strongly reduced by using an independently obtained aerosol vertical distribution.

## Key evidence — #508

At Sun depression `−5.808°`:

- old residual: `+0.393 mag`
- CAMS-profile result: `+0.087 mag`

At `−6.134°`:

- old residual: `+0.388 mag`
- CAMS-profile result: `+0.031 mag`

Total AOD, geometry, pressure, calibration and other frozen conditions were retained; no SQM offset or AOD was fitted.

Therefore:

> Knowing only total AOD is not enough for maximum-accuracy twilight prediction. Vertical aerosol placement materially changes twilight scattering as Earth’s shadow removes lower atmospheric layers.

---

# 7. Taylor Monte-Carlo uncertainty — use the newer result

Do not use old broadband `mc.rad.std.spc` as a calibrated uncertainty estimate.

Empirical single-run scatter from the dedicated multi-seed screen:

- row1: `0.00264 mag`
- row5: `0.00517`
- row9: `0.00709`
- row13: `0.00801`
- row17: `0.01100`
- row21: `0.02630`
- row24: `0.0704`
- row25: `0.0906`

Taylor repeatability term:

- about `0.06215 mag`

Implication:

- early/middle interval numerical noise is small;
- late rows become numerically important;
- no blanket high-photon rerun of the entire Taylor dataset is justified.

Late reconverged central residuals rows 23–25:

- `+0.08544`
- `+0.17350`
- `+0.17696 mag`

These late rows are not compelling standalone inconsistencies after proper partial uncertainty treatment.

Most important:

- reconverged AOD finite-difference derivative remains **UNRESOLVED**.

Do not reuse the old large AOD derivative as a precise physical derivative.

---

# 8. Taylor CAMS provenance boundary

Same-cycle spectral columns near Taylor were approximately:

- AOD550 ≈ `0.31–0.32`
- SSA550 ≈ `0.95`
- g550 ≈ `0.71`
- Ångström alpha ≈ `1.28`

But direct forecast00 vertical extinction returned **137 exact zero coefficients** at 355/532/1064 nm despite nonzero column AOD.

Forecast03 produced valid profiles.

Therefore:

- forecast00 all-zero extinction is invalid, not a real aerosol-free atmosphere;
- do not call a run “direct same-cycle full CAMS atmosphere” unless its vertical field is genuinely valid;
- column SSA/g used uniformly with height must be labeled an approximation;
- do not choose forecast03 because it happens to fit Taylor better.

---

# 9. Independent Taylor atmosphere search — separate worker lane

A separate worker is already investigating:

- EarthCARE / ATLID;
- ground lidar / ceilometer;
- AERONET;
- other independent aerosol archives;
- genuinely independent commercial sources.

Do not duplicate this lane.

If genuinely new independent atmosphere evidence is found:

1. freeze source/time/distance/quality rules first;
2. archive provenance;
3. decide scientifically how the source may be used;
4. only afterward perform another Taylor comparison.

Existing HRRR lane:

- #487 owns the HRRR vertical-shape scientific comparison;
- #489 is only a technical 550-nm smoke test.

Do not open a second HRRR lane or turn HRRR smoke mass directly into “measured extinction.”

---

# 10. Generalized aerosol vertical-profile sensitivity v1 — ACTIVE PRINCIPAL LANE

Scientific question:

> At fixed total AOD550 and fixed coherent OPAC rich optical properties / phase function, how much does independently specified normalized aerosol vertical optical-depth shape change twilight radiance and the derived Level-B limiting-magnitude endpoint?

This is **not** a Taylor-fitting experiment.

## #549 — MERGED
`Add reusable aerosol vertical-profile transport foundation`

Merge commit:

- `76e232523f29cfc64d3c50c0b3e922aa59d1dfe7`

Solver-free foundation supports:

- nonnegative profile validation;
- source/target altitude validation;
- remapping/integration;
- explicit outside-support policy;
- observer clipping + renormalization;
- deterministic normalized layer fractions;
- libRadtran lower-bound `aerosol_file tau` convention;
- provenance-sensitive fingerprint.

No MYSTIC/scientific execution.

## #550 — MERGED
`Check OPAC plus custom vertical tau exact-runtime compatibility`

Merge commit:

- `2be138d96d4e6d04b1e58dede27bb3f0130fc42e`

Terminal result:

- `PASS_EXACT_RUNTIME_OPAC_PLUS_CUSTOM_TAU_SYNTAX`

Run:

- `33095258477`
- attempt 1
- SUCCESS

Artifact:

- ID `9656112795`
- digest `sha256:870ee009131c3b6c737dde70bfa4ad7c4a7e85a7d91cd4b4012f2f36e23f2098`

Exact supported composition:

- `aerosol_default`
- `aerosol_species_library OPAC`
- `aerosol_species_file continental_average`
- `aerosol_file tau <custom profile>`
- `aerosol_set_tau_at_wvl 550 <fixed AOD>`

This was parser/capability only, not MYSTIC science.

## #551 — MERGED
`Preregister aerosol vertical-profile sensitivity v1`

Merge commit:

- `b882034629894d2629ec60ef15f46e83635d6f7e`

Terminal:

- preregistration PASS;
- execution still disabled.

Five independently frozen OPAC Table-3/Table-5 vertical templates:

1. Continental average
2. Maritime clean
3. Desert
4. Arctic
5. Antarctic

The labels describe **vertical templates only**. All five use the same rich OPAC `continental_average` optical family so the experiment isolates vertical distribution instead of changing vertical structure and microphysics together.

Frozen design:

- AFGL-US;
- observer elevation 0 m only;
- surface albedo 0.15;
- 380–780 nm;
- reviewed 1-nm grid;
- MYSTIC spherical 1D;
- VROOM;
- MC std evidence;
- 20,000,000 photons per case;
- Sun depression: 2°, 4°, 6°, 8°;
- AOD550: 0.10, 0.30;
- geometries:
  - 10°/30° near-solar;
  - 30°/90° cross-solar;
  - 45°/180° opposite-solar;
- 3 fresh CRN replicates;
- 5 vertical states.

Cardinality:

- 72 CRN groups;
- 360 cases.

Primary endpoints:

- photopic luminance;
- scotopic luminance;
- Johnson-V effective radiance.

Secondary endpoint:

- paired Level-B limiting-magnitude delta through current Crumey Eq.34 threshold path with `F=3.14`.

No universal minute conversion and no adaptive post-result cases.

## #552 — MERGED
`Freeze unseeded aerosol vertical-profile execution skeleton`

Merge commit:

- `79fd4605e02068f0d798181e2b05459d708bfebc`

Frozen before seed allocation:

- exact 360-case universe;
- exact 72 CRN groups;
- all case/group IDs;
- aerosol directive surfaces;
- every case still has:
  - `seed=null`
  - `renderable=false`
  - `executionAuthorized=false`
  - `resultOpeningAuthorized=false`.

---

# 11. Candidate seed / ordinal preauthorization

The 72 candidate seeds are derived deterministically from the frozen group IDs.

Frozen hashes:

- seed canonical SHA-256:
  `a2e22b526dfad84d4f23c0ca8b143d028fddc7e55f78deb93a43e194ebd6c35e`

- candidate-row canonical SHA-256:
  `f22de8a9e30ba106759effb1170a5ca1d1e747cb2ac68293fa232dc7ed6ca683`

Earlier exact-main preauthorization run `33097615139` had proved:

- 72/72 fresh candidate seeds;
- zero internal collisions;
- zero tracked-tree external collisions;
- zero repository-global collisions;
- stable double enumeration;
- next available scientific ordinal = 40;
- no allocation/execution.

That proof is now stale by design because the scientific execution package subsequently changed.

---

# 12. #557 — MERGED DISABLED EXECUTION PACKAGE

PR:

- #557 `Freeze disabled aerosol vertical-profile execution package`

Reviewed head:

- `ce3310232fbf3cf759e83658cc66e96566a83500`

Merge commit / current main checkpoint:

- `d206a098ad6fee1bf6513460d29c949eadb695d1`

Purpose:

> Freeze the complete scientific execution surface before any ordinal or candidate seed is allocated.

It freezes:

- all 360 case science-directive surfaces;
- 120 distinct pre-seed science surfaces (3 replicates share each physical surface);
- exact fixed OPAC-rich + custom-tau + AOD directive order;
- placeholder `mc_randomseed <UNALLOCATED_FRESH_GROUP_SEED>`;
- no real seed value;
- `renderable=false`;
- `executionAuthorized=false`;
- no scientific ordinal;
- no result opening;
- runtime/OPAC identity bindings.

## Exact reviewed-head CI

Run `33100109538`:

- `deterministic-package` — SUCCESS
- `exact-afgl-profile-bundle` — SUCCESS

Preauthorization-control review:

- run `33100109537` — SUCCESS

Scientific preregistration review:

- run `33100109555` — SUCCESS

## Exact AFGL profile-byte freeze

The locked libRadtran package was installed only to read the exact AFGL-US altitude grid.

`runtime_probe --skip-help` recorded:

- `syntaxCheckExecuted=false`
- `scientificSolverExecuted=false`

Neither parser nor MYSTIC was invoked.

Exact normalized tau SHA-256 values:

- continental-average:
  `e6c296951dfae376bf77948aa92828062ba95d7b1e9c28703befa9cffb5bf198`
- maritime-clean:
  `5cbaf5f81f3f36bfcf9b365eaa5d892889da83453c18d58e705b3de9273adc8c`
- desert:
  `3d8891b3b67fa8c8c6fd66861d49e9bfad8c937a176b7001c6c47a5571de21ad`
- arctic:
  `61eed1e73ac8cc6f044b89870a6874f1d21500008c7747830a2a812bbd87919a`
- antarctic:
  `a14460a04afd5154d931b77e55b7adce2ab41aae2e8e4c13afaa0de459aff164`

Exact-head artifacts:

- exact AFGL bundle artifact `9658061526`
  - digest `sha256:2061136f069e9a16fa5c5b3d0991121bb04d7a268d1b7c7f93c60d734d537b48`
- disabled execution package artifact `9658060805`
  - digest `sha256:37cc696d952fdc32430105e1a8749095fb1e5816a03590a1b5d9d6bbbb29c693`

## Critical control change in #557

The exact-main preauthorization path filters were broadened so changes to the actual scientific/execution inputs force a new exact-main proof, including:

- protocol;
- scientific review;
- photon-budget review;
- vertical templates;
- execution skeleton;
- execution package;
- seed ledger;
- freshness/preauthorization controls;
- generic profile transport;
- wavelength grid;
- associated tests/workflows.

This prevents using a seed/ordinal proof tied to an older science package.

---

# 13. CURRENT exact-main preauthorization — IN PROGRESS

After #557 merged, a fresh main push run started automatically:

- run `33100194996`
- exact main `d206a098ad6fee1bf6513460d29c949eadb695d1`
- attempt 1

At handoff creation:

Passed:

- exact main identity;
- zero-runtime boundary;
- deterministic controls;
- candidate ledger reconstruction;
- tracked-tree seed scan.

In progress:

- repository-global candidate-seed recheck.

Pending:

- live seed authorization proof;
- fresh global ordinal derivation;
- preauthorization artifact;
- Issue 60 non-allocation checkpoint.

**Do not create `authorization.json` from the old preauthorization artifact.**

The fresh proof may again yield ordinal 40, but only the new exact-main proof is authoritative.

---

# 14. Authorization-control framework — PARALLEL BRANCH EXISTS, NOT YET ACCEPTED

Parallel branch:

- `review/aerosol-vertical-profile-authorization-control-v1`
- observed head `792f92c93894d5e6158adcb4b1a55d58542c0204`

It contains:

- `.github/workflows/aerosol-vertical-profile-authorization-review.yml`
- `authorization_guard.py`
- `build_authorization.py`
- `execution_design.py`
- authorization-control tests
- preauthorization-surface refresh anchor.

Its architecture is useful:

- exact one-file Draft authorization PR;
- direct child of live main;
- exact parent-main preauthorization artifact;
- authorization-head tracked-tree/global seed recheck;
- zero-runtime authorization review;
- no dispatch;
- no result opening;
- attempt-1 only;
- no casual rerun/retry/resume semantics.

But it predates #557 and is now diverged from the new main.

**Do not merge it wholesale as-is.**

Port/rebuild it from current `main=d206a098...` and additionally bind:

1. the merged disabled execution package;
2. exact 360-case science-surface identity;
3. exact-AFGL profile bytes/evidence;
4. exact runtime/OPAC hashes frozen by #550/#557.

Only after the hardened framework is merged and causes another fresh exact-main preauthorization should the one-file authorization PR be created.

---

# 15. Immediate next work — P0

## P0-A — finish run `33100194996`

Require:

- attempt-1 success;
- exact main `d206a098...`;
- 72 candidate seeds;
- zero tracked-tree collisions;
- zero repository-global collisions;
- stable double enumeration;
- no tracked candidate-seed literals;
- no ordinal allocation;
- no seed application;
- no runtime/MYSTIC;
- fresh next-global-ordinal proposal.

Archive:

- artifact ID;
- artifact digest;
- report SHA;
- Issue 60 checkpoint.

If it fails, diagnose the failure. Do not casually rerun a failed science-control gate.

## P0-B — harden the authorization-control framework on current main

Build from current main, not from the stale branch tip.

Add explicit #557 package/profile/runtime bindings.

Keep authorization review completely zero-runtime.

## P0-C — only afterward allocate the scientific identity

After:

1. current-main preauthorization PASS;
2. hardened authorization-control framework merged;
3. the merge triggers another exact-main preauthorization and that fresh run PASSes;

then create exactly one branch:

`authorization/aerosol-vertical-profile-sensitivity-v1-ordinal-<fresh ordinal>`

Ordinal 40 is only the likely candidate if no other science identity intervenes. Derive it live; do not hard-code it from this handoff.

Authorization PR requirements:

- Draft/open;
- direct child of exact live main;
- exactly one changed file:
  `experiments/aerosol-vertical-profile-sensitivity-v1/authorization.json`;
- authorization-time global seed recheck;
- exact preauthorization artifact binding;
- exact execution package/design binding;
- no automatic dispatch;
- no result opening.

## P0-D — separate dispatch gate

Authorization and execution must remain separate.

The dispatch gate should bind:

- authorization identity;
- fresh global surface;
- exact 360 cases;
- exact 72 CRN seeds;
- exact runtime/AFGL/OPAC/tau bytes;
- exact 20M photons per case;
- exact attempt/retry semantics;
- no post-result parameter changes.

## P0-E — result opening gate

Do not inspect partial/adaptive science results.

Open results only after:

- all expected cases complete;
- exact aggregate/cardinality checks pass;
- artifacts complete;
- seeds/cases/runtime exactly match authorization;
- no post-hoc reruns changed the sample.

---

# 16. AVPS statistical contract

For each reference contrast and CRN replicate retain paired log response.

Report:

- all three replicate contrasts;
- mean;
- sample SD;
- `SE = SD / sqrt(3)`.

Do not add:

- p-values;
- confidence intervals;
- independent-error quadrature;
- epsilon substitutions;
- post-result adaptive cases.

A required nonpositive/nonfinite response is:

- `NUMERICALLY_UNRESOLVED`.

This sensitivity stage does **not** create a production materiality threshold.

It answers:

> How much can normalized vertical profile shape matter over the preregistered controlled range?

It does not answer:

> Which real-world profile should production use at a specific location/time?

---

# 17. After AVPS — fast Level-B atmosphere mapping

This remains a major unsolved problem.

The project must keep separate:

1. acquiring the real atmosphere;
2. representing/QC/provenance;
3. mapping it into Level-B efficiently;
4. validating that fast mapping against high-fidelity radiative transfer.

Current Level-B is not a universal arbitrary-profile RT engine.

Possible future architectures to test rather than assume:

- parameterized vertical-profile correction;
- expanded surrogate dimensions;
- small physically selected scenario basis;
- hybrid direct/precomputed tables;
- separate column optics + normalized vertical-shape representation.

Likely environmental sensitivity order after AVPS:

1. spectral AOD;
2. profile × AOD interaction;
3. reuse already-closed SSA/g/full-phase work rather than duplicating it;
4. profile × optical-family interaction if warranted;
5. pressure/molecular state;
6. ozone;
7. water vapor;
8. surface albedo;
9. RH-dependent aerosol behavior.

Do not choose sensitivity ranges from Taylor/Jerusalem residuals.

---

# 18. Already-closed aerosol-optics work — DO NOT DUPLICATE

Scientific ordinals:

- AOPS = 37
- AFPF = 38
- ASIV = 39

These already cover, for their stated scopes:

- controlled SSA/scalar-g sensitivity;
- coherent full OPAC phase-function/aerosol-family sensitivity;
- scalar + derived-Level-B aerosol scenario interpolation;
- shadow aerosol scenario-envelope work (`starsvisibility #100`).

The current missing aerosol physics dimension is specifically **vertical structure and its fast-model consumption**, not generic SSA/g/phase/family sensitivity from scratch.

---

# 19. F / mesopic / stellar / transient summary

## F

Keep `F = 3.14`.

Lower F makes visibility earlier, so it cannot explain an already-too-early prediction concern.

## Mesopic MES2

Review-only Jerusalem effect:

- Tishrei ≈ `+17.8 s`
- Tammuz = `0 s`

Not a broad multi-minute explanation and not validated physiology.

## Stellar direct atmospheric transport

Validated aerosol-family matching of the stellar direct beam generally moves timings by seconds, not several minutes. Do not confuse that with aerosol effects on twilight sky scattering.

## Transient

- #119 diagnostic merged;
- #116 open;
- #117 physical mapping unresolved.

Continue using external psychophysics for model selection, not Jerusalem timing fit.

---

# 20. Moon / natural night / artificial sky

## Moon — #459 Draft/open

ROLO-based lunar extraterrestrial source / MYSTIC contract exists.

Still incomplete:

- finite lunar disk;
- independent spectral cross-check;
- scattered moonlight validation;
- real-sky validation;
- production authorization.

Do not wire Moon into trusted total sky yet.

## Natural night — #460 Draft/open

Preferred baseline direction: GAMBONS.

A constant dark-sky floor is forbidden.

Need a provider with location/time/direction, Johnson-V/photopic/scotopic channels, airglow state/uncertainty, Moon exclusion, artificial-light exclusion and compatible atmosphere identity.

## Artificial skyglow

A single zenith SQM/World Atlas number is insufficient for arbitrary target direction.

Need directional radiance based on calibrated all-sky data or physical propagation of emission inventories. Do not invent an azimuth/altitude correction merely to improve timings.

## Total-sky compositor — #112 merged

Already supports Solar/Moon/Natural/Artificial components in linear physical channels with common atmosphere identity and fail-closed semantics.

Do not rebuild it.

---

# 21. Master closure PR #539

Repository:

- `search-maker/twilight-mystic-experiments`

PR:

- #539 `Record model closure status and exact observation requirements`
- Draft/open

It remains the intended **single authoritative closure record**.

It was refreshed earlier today and already records:

- #114/#118/#119 merged;
- #116 blocked pending #117 science;
- #48 not to be replayed wholesale;
- Operational Atmosphere v2 #120/#121 merged;
- #549 vertical-profile transport merged;
- Taylor #508/#529/#535/#536 authority;
- AOPS/AFPF/ASIV closed scopes;
- vertical structure + fast Level-B consumption as the principal remaining atmosphere gap.

It now needs another refresh to add:

- #550 merged exact-runtime OPAC+custom-tau capability;
- #551 merged preregistration;
- #552 merged 360-case unseeded skeleton;
- preauthorization-control progress;
- #557 merged disabled execution package;
- exact AFGL tau hashes/evidence;
- current run `33100194996`;
- authorization-control parallel branch and required #557 bindings;
- explicit statement that ordinal 40 is not allocated as of this handoff.

Do not allow this handoff to become a competing long-term source of truth. Refresh #539 as milestones close.

---

# 22. Things NOT to do

Do not:

- change `F=3.14` because a Jerusalem time looks wrong;
- select tau from Jerusalem;
- add universal sky or clock offsets;
- choose AOD/profile/provider/cycle from Taylor residuals;
- infer aerosol family from AOD alone;
- fabricate vertical structure;
- hide uncertainty behind `aerosol_default`;
- call modeled data measured;
- treat CAMS forecast00 all-zero extinction as real clear air;
- apply column SSA/g uniformly with altitude without labeling the approximation;
- reuse the old Taylor `+0.393 mag` as the present stable discrepancy;
- reuse the old large AOD derivative as resolved;
- run blanket high-photon Taylor reruns;
- reopen the 90° MYSTIC/stellar campaign;
- rerun generic SSA/g/full-phase sensitivity already covered by ordinals 37–39;
- interpret the five AVPS profile labels as actual site microphysics;
- choose the “best fitting” AVPS profile for Taylor;
- allocate ordinal 40 from the stale preauthorization proof;
- apply candidate seeds before exact-current-main authorization;
- merge the stale authorization-control branch wholesale;
- combine authorization and dispatch;
- use GitHub rerun/retry/resume after scientific dispatch unless separately preregistered;
- inspect partial results and then change cases/photon counts;
- silently treat solar-only sky as total sky;
- enable unfinished Moon/Natural/Artificial providers as trusted production;
- merge #116 merely because old tests passed.

---

# 23. Reporting contract for every new task

Report:

- repository;
- issue/PR;
- branch;
- exact SHA;
- scientific question;
- inputs frozen before scoring;
- whether Taylor/Jerusalem residuals were inspected before parameter selection;
- data provider;
- underlying scientific source;
- measured/modelled/forecast/climatology status;
- exact valid time;
- exact location/grid/station;
- spatial/temporal mismatch;
- vertical coverage;
- spectral coverage;
- uncertainty;
- quality flags;
- workflow/run ID;
- artifact ID/digest;
- result;
- remaining uncertainty;
- whether production changed;
- whether #539 was updated.

For scientific execution also record:

- scientific ordinal;
- authorization parent/head;
- authorization artifact;
- dispatch identity;
- exact seeds;
- exact case count;
- exact runtime hashes;
- exact result-opening gate.

---

# 24. Central scientific conclusion

Current evidence does **not** support a simple large failure of basic spherical MYSTIC twilight physics as the explanation for the timing concern.

Taylor instead demonstrated something operationally crucial:

> The actual atmosphere — especially aerosol vertical structure — can materially change twilight radiance even when total AOD is fixed.

The project should therefore move away from:

> “Which parameter can we tweak to make the time look right?”

and toward:

> “Which physical quantities vary from place to place and night to night, how much do they change the prediction, where can we obtain them independently, and how should Level-B consume them with explicit provenance and uncertainty?”

Immediate path:

1. complete exact-main AVPS preauthorization;
2. harden/merge the authorization-control framework on current main;
3. allocate a fresh science identity only through that gate;
4. separately dispatch the fully frozen 360-case MYSTIC experiment;
5. open results only after complete success;
6. quantify vertical-profile sensitivity;
7. use that result to decide whether/how Level-B needs an explicit vertical-profile dimension;
8. continue independent real-atmosphere acquisition separately.

---

# 25. One-line current status for the next worker

> **The atmosphere-v2 representation foundation and the complete solver-disabled 360-case aerosol vertical-profile science package are now frozen and merged. Exact-main seed/ordinal preauthorization is rerunning on `main=d206a098…`; therefore no scientific ordinal, seed application, dispatch or MYSTIC result exists yet. Finish that proof, then port/harden the authorization-control framework onto current main with explicit #557 bindings before any execution can be authorized.**
