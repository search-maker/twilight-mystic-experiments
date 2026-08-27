# Star-visibility model closure matrix — current authoritative status

Status: **review-only master closure record**.

Updated: **2026-08-27 after Operational Atmosphere State v2 merge and vertical-profile transport foundation merge**.

This file does not change runtime, thresholds, `F`, `tau`, atmosphere values, Level-B support, production routing, or empirical/human validation flags.

Purpose: keep one current source of truth separating:

1. computationally strong/closed work;
2. already-completed aerosol science that must not be duplicated;
3. remaining atmosphere acquisition/vertical-structure/fast-mapping work;
4. work requiring new empirical real-sky or human evidence.

---

## 0. Global governance — hard rules

Do not choose or tune any of the following to move Jerusalem, Tishrei, Tammuz, or Taylor toward a desired result:

- `F`;
- transient `tau`;
- AOD;
- aerosol vertical profile;
- aerosol family;
- SSA;
- phase function / asymmetry parameter;
- provider or model cycle;
- sky/magnitude offset;
- clock/minute offset;
- threshold coefficients;
- interpolation/support rule;
- stop rule.

Additional hard rules:

- `F = 3.14` remains the current default.
- transient `tau = 30 s` remains experimental only.
- No universal magnitude or minute correction.
- AOD alone must not select aerosol family.
- Missing vertical structure must not be fabricated.
- A modeled/reanalysis/forecast field must not be called a measurement.
- A commercial/API republisher must not be counted as independent evidence from its underlying scientific source.
- Missing/invalid materially important atmosphere information remains explicit and should fail closed or degrade confidence.
- Taylor is principally evidence for direct MYSTIC, not direct Level-B or human-first-seeing validation.
- No `humanFirstSeeingValidated` claim without independent human evidence.
- Pandora/Izaña remain unopened unless separately authorized.
- matched-stellar v1 is obsolete.

External atmosphere or psychophysical evidence may select/freeze a candidate **before** target-event scoring. Target residuals may not select the environmental state used to validate those same targets.

---

# 1. Current GitHub status

## starsvisibility #114 — MERGED

`Route validated Level-B sky + stellar support through exact zenith`

- exact physical 90 deg sky/stellar support is routed through current main;
- old <=80 deg behavior remains preserved;
- exact-head broad verification passed;
- production/real-sky/human validation claims remain closed.

**Do not reopen the 90 deg sky/stellar computational campaign.**

## starsvisibility #118 — MERGED

`Make Level-B current-main test runnable from clean checkout`

Software/test lifecycle only; no scientific/runtime behavior change.

## starsvisibility #119 — MERGED

`Freeze Crumey Eq.34 transient equivalent-background transition diagnostic`

Frozen diagnostic baseline:

- local threshold maximum near `B = 0.021567318651 cd/m^2`;
- local threshold minimum near `B = 0.047052552759 cd/m^2`;
- threshold drop about `2.600936%`;
- maximum formal local negative adaptation penalty about `-0.028613 mag`.

No replacement transient mapping was authorized.

## starsvisibility #116 — OPEN / DO NOT MERGE YET

`Fix transient negative-penalty topology artifact`

The branch proposes an equilibrium/monotone floor when the raw equivalent-background mapping produces a formal negative penalty. That semantic change is not yet scientifically closed.

Before merge:

1. characterize actual real Level-B `(physical B, adaptation debt, effective B)` trajectories;
2. complete issue #117's scientific decision about the equivalent-background mapping;
3. justify any state/threshold-space replacement from independent psychophysical evidence;
4. preregister the shadow-only acceptance test;
5. rerun the correct post-decision timing audit and exact-head build.

Until then, do not merge #116 merely because its older tests passed.

## starsvisibility #48 — OLD DRAFT / DO NOT REPLAY WHOLE STACK

Important v1 foundation files originating in #48 are already in current `main`, including:

- `atmosphere-state.mjs`;
- `atmosphere-resolver.mjs`;
- `aeronet-atmosphere.mjs`;
- `open-meteo-cams-atmosphere.mjs`;
- associated acquisition/runtime tests.

Current site-wide regression hash-binds these authoritative files. Re-importing #48 wholesale would duplicate/stack stale work.

## starsvisibility #120 — MERGED

`Design Operational Atmosphere State v2`

Merge commit: `0ef878a78f792edc7a484de8ace8a196be1543cb`.

This is the accepted Gate-A design contract. It separates atmosphere acquisition, representation/QC, fast-model consumption, and validation.

## starsvisibility #121 — MERGED

`Add Operational Atmosphere State v2 foundation`

Reviewed exact application head: `de44958a62704c3236ff24294c0639b3868803aa`.

Independent broad exact-head verifier:

- repository: `twilight-mystic-experiments`;
- dispatch PR #548, closed unmerged after evidence capture;
- run `33094168008`, attempt 1, SUCCESS;
- job `98594593383`, SUCCESS;
- exact private application SHA hard-gated;
- `uvspec` absent;
- clean-checkout current-main PASS;
- complete `test:level-b-parity` PASS, including `operational atmosphere state v2: PASS`;
- full Pages/sitewide build PASS;
- packaged stellar-v3.2 identity PASS;
- final deployment marker bound to exact application SHA.

Merge commit: `e0da52eb0a2d5bac333da6572f51df52ea7e676e`.

**Important boundary:** v2 can now represent richer atmosphere components, but current Level-B does not yet consume vertical-profile/SSA/phase fields merely because they are present in the state.

## twilight-mystic-experiments #549 — MERGED

`Add reusable aerosol vertical-profile transport foundation`

Merge commit: `76e232523f29cfc64d3c50c0b3e922aa59d1dfe7`.

Dedicated solver-free CI:

- run `33094636459`, SUCCESS;
- job `98596212828`, SUCCESS.

This foundation:

- accepts an independently supplied nonnegative vertical aerosol shape;
- remaps it onto explicit target atmosphere layer edges;
- requires explicit outside-support behavior (`reject`, `zero`, or `edge`);
- normalizes only the transported/above-observer layer distribution;
- renders libRadtran lower-bound `aerosol_file tau` convention;
- keeps total column AOD completely separate;
- records deterministic source identity.

It does **not** select a physical profile or change Level-B.

## twilight-mystic-experiments #550 — OPEN CAPABILITY GATE

`Check OPAC plus custom vertical tau exact-runtime compatibility`

Review/parser-only question:

Can the exact locked libRadtran/OPAC runtime accept one input that keeps a coherent OPAC spectral/phase aerosol family fixed while supplying a custom normalized `aerosol_file tau` vertical profile and separately normalizing AOD550?

Only `uvspec -c` is authorized. No MYSTIC/scientific solver, seed, ordinal, profile selection, Taylor/Jerusalem scoring, or production change.

Do not freeze a new vertical-profile MYSTIC campaign until this capability question is terminal.

---

# 2. Solar twilight / direct MYSTIC / Level-B

## Status

**Direct MYSTIC twilight physics: computationally strong; empirical real-sky validation still partial.**

Existing evidence does not support a simple large universal defect in spherical MYSTIC twilight physics.

Exact-event Level-B vs direct-MYSTIC comparisons do not have one universal sign:

- Tishrei direct MYSTIC was darker than Level-B at determining directions;
- Tammuz had mixed spatial sign.

Therefore do not add a universal Level-B sky correction.

Taylor Ann Arbor is a valuable independent real-SQM consistency case for **direct MYSTIC**, not a direct validation of Level-B or human first-seeing.

---

# 3. Taylor — authoritative interpretation

The current conclusion is not that the exact Taylor atmosphere is known.

The current conclusion is:

> Direct MYSTIC is broadly consistent with Taylor, and independently constrained aerosol vertical structure removed much of the former onset-region discrepancy.

## Vertical-profile finding — #508

In the original-SQM 380–780 nm calculation, total AOD, geometry, pressure, calibration and other frozen inputs were retained while the normalized aerosol vertical extinction shape was replaced by independently obtained CAMS shape information.

Important onset-region changes:

- Sun `-5.808 deg`: residual about `+0.393 -> +0.087 mag`;
- Sun `-6.134 deg`: residual about `+0.388 -> +0.031 mag`.

No SQM offset or AOD was fitted to Taylor.

This proves vertical aerosol distribution can be materially important. It does not prove the exact Taylor atmosphere.

## Numerical uncertainty — #535 / #529

Do not use old broadband `mc.rad.std.spc` as a calibrated between-seed uncertainty estimator.

Empirical single-run scatter grows late:

- row1 about `0.00264 mag`;
- row5 `0.00517`;
- row9 `0.00709`;
- row13 `0.00801`;
- row17 `0.01100`;
- row21 `0.02630`;
- row24 `0.0704`;
- row25 `0.0906`.

Six-seed 200k central residuals rows 23–25 are approximately:

- `+0.08544`;
- `+0.17350`;
- `+0.17696 mag`.

The reconverged AOD finite-difference derivative remains unresolved. Do not reuse the former large late-row derivative as precise physical sensitivity. Do not blanket-rerun all Taylor rows at high photons.

## CAMS provenance boundary — #536

Same-cycle CAMS column/spectral optics near Taylor were plausible, approximately:

- AOD550 `0.31–0.32`;
- SSA550 about `0.95`;
- `g550` about `0.71`;
- Angstrom alpha about `1.28`.

But forecast00 direct vertical extinction returned 137 exact zero coefficients despite nonzero column AOD. Forecast03 profiles were valid and integrated consistently with column AOD.

Therefore:

- valid column information does not validate a vertical component automatically;
- all-zero forecast00 vertical extinction must not be interpreted as real aerosol-free air;
- prior-cycle and same-cycle profiles are not interchangeable without explicit provenance;
- column SSA/g applied uniformly with altitude is a new approximation and must be labeled;
- another run must not be called “direct same-cycle full CAMS atmosphere” unless the vertical information is genuinely resolved.

## Independent Taylor atmosphere search

EarthCARE/ATLID, ground lidar/ceilometer, AERONET and other genuinely independent archives remain valuable.

Before scoring any new Taylor result:

1. freeze source/product/cycle/time/distance/quality rules;
2. archive exact provenance;
3. determine source independence;
4. decide scientifically how the quantity enters MYSTIC;
5. only then inspect residuals.

Never choose a source/cycle/profile because it fits Taylor better.

---

# 4. Aerosol optical-property / family science — ALREADY COMPLETED, DO NOT DUPLICATE

The older handoff incorrectly left SSA/phase/family sensitivity as generic future work. That is stale.

## AOPS v1 — ordinal 37 — CLOSED FOR CONTROLLED SSA/g SENSITIVITY

At fixed AOD, controlled SSA and scalar-g sensitivity was executed over the frozen geometry/AOD design.

Key interpretation:

- increased SSA brightened the twilight sky in all tested cells and made Level-B visibility less favorable;
- scalar-g effects were geometry/context dependent;
- interactions were not universal.

This is a controlled sensitivity result, not a climatological aerosol prior.

Do not rerun a generic constant-SSA/constant-g screen.

## AFPF v1 — ordinal 38 — CLOSED FOR FULL OPAC PHASE/FAMILY SENSITIVITY

Realistic wavelength-dependent OPAC aerosol-family/full-phase-function challenge was completed.

Key interpretation:

- family/phase effects are materially geometry dependent;
- full phase-function behavior cannot be reduced to one universal scalar `g` correction;
- OPAC states are physical scenario states, not probabilities for a location.

Do not reopen a generic phase-function/family campaign.

## ASIV v1 — ordinal 39 — CLOSED FOR CURRENT SCALAR/DERIVED LEVEL-B SCENARIO TRANSPORT

Fresh holdout interpolation validation passed the frozen scalar and derived Level-B gates.

Representative Level-B error metrics:

- mean absolute error about `0.03635 mag`;
- median about `0.03132 mag`;
- worst about `0.14838 mag`.

Full-spectrum aerosol interpolation was **not** validated by ordinal 39 and remains outside the claim.

## starsvisibility PR #100 — MERGED SHADOW-ONLY SCENARIO ENVELOPE

The five-state Tier-0 aerosol scenario envelope is already implemented and exact-head verified in shadow-only form.

It preserves:

- native baseline;
- exact five-state scenario enumeration;
- no aerosol-family probabilities;
- no single-family selection from AOD alone;
- fail-closed OOD behavior;
- Level-B recomputation from scenario photopic background;
- production/UI activation false.

Therefore the remaining aerosol problem is **not** “how do we model SSA/phase/family at all?”

The primary new physical gap is **vertical aerosol structure**, together with richer real-atmosphere acquisition and a validated fast mapping that can consume it.

---

# 5. Operational Atmosphere State v2 — CURRENT FOUNDATION

The merged v2 state can represent, when available:

### Column aerosol

- spectral AOD;
- canonical AOD550;
- Angstrom behavior and uncertainty.

### Vertical aerosol

- extinction/backscatter/profile quantities;
- altitude/reference/resolution;
- quality and provenance;
- normalized optical-depth shape only when legitimately derivable.

### Optical properties

- SSA spectrum;
- phase-function/asymmetry representation;
- aerosol classification;
- vertical applicability of column properties.

### Molecular/surface/cloud state

- pressure/temperature/profile identity;
- ozone/water vapor/other admitted absorbers;
- surface elevation/albedo;
- explicit cloud status and provenance.

### Provenance/QC

Every material component may retain service provider, underlying scientific source, product/version, source type, valid time, cycle/lead, source location/elevation, space/time mismatch, resolution, wavelength coverage, interpolation, quality flags, uncertainty, fallback/rejection history and reproducible identity.

A partially known atmosphere is a valid **incomplete** state. It is not permission to fabricate missing components.

---

# 6. Four atmosphere problems — keep separate

## A. Acquire the atmosphere

Find the best admissible measured/satellite/model/reanalysis/climatological components for requested location/elevation/date/time.

## B. Represent it faithfully

Store provenance, uncertainty, missingness and conflicts without fabrication.

## C. Map it into the fast model

Current Level-B is not an arbitrary-profile radiative-transfer engine. A rich v2 state does not automatically mean all fields affect the prediction.

## D. Validate that fast mapping

Any richer mapper must be checked against direct MYSTIC on held-out atmosphere states and later against independent real-sky evidence.

Do not call provider acquisition success a Level-B physical validation.

---

# 7. Remaining vertical-profile program — PRIMARY CURRENT PHYSICS GAP

Taylor established that vertical aerosol shape can matter materially. The project now has generic, tested transport mechanics (#549), but not yet a generalized independently preregistered vertical-profile MYSTIC sensitivity campaign.

The next sequence is:

1. close #550 exact-runtime capability for fixed OPAC optics + custom `aerosol_file tau`;
2. select a deliberately small vertical-profile universe from independent published/standard physical profiles — **not Taylor/Jerusalem residuals**;
3. freeze geometry/AOD/profile states, spectrum, observer elevation, CRN groups, photon budget, endpoints and acceptance/reporting rules before opening results;
4. execute direct MYSTIC profile-shape isolation at fixed total AOD and fixed optical-property family;
5. quantify effect on photopic/scotopic/Johnson-V sky channels and derived Level-B limiting magnitude;
6. only if material, design a fast Level-B vertical-profile mapper or set-valued profile envelope;
7. validate that mapper against held-out direct-MYSTIC states.

A good scientific question is:

> At fixed total column AOD and fixed aerosol spectral/phase optical properties, how much does independently specified normalized aerosol vertical optical-depth shape change twilight radiance and derived Level-B quantities across the supported geometry domain?

Do not infer the answer from Taylor alone.

---

# 8. Spectral aerosol transport boundary

ASIV ordinal 39 validated scalar and derived Level-B scenario transport, not arbitrary full-spectrum aerosol interpolation.

Current scalar/Level-B shadow scenario envelope does not require a full-spectrum production claim.

If a future feature needs full spectrum or color-sensitive aerosol outputs from arbitrary real atmosphere states, that requires a separate frozen spectral validation program. Do not silently promote current scalar ASIV PASS into a full-spectrum PASS.

---

# 9. Stellar direct atmospheric transport

Status: **computationally strong for the current question**.

Matched/native stellar direct-transport differences under ordinary supported geometries are generally seconds-scale in event timing, not a generic several-minute effect.

Low-altitude/red-star cases can be larger and should be reported individually.

Do not confuse stellar direct-beam transport with aerosol effects on twilight **sky scattering**, where vertical structure has demonstrated a much larger Taylor effect.

Do not reopen stellar transport as an untargeted place to seek a large correction.

---

# 10. Human point-source threshold / F

Crumey/Blackwell remains a reasonable threshold foundation, but modern naked-eye first-seeing is not empirically validated for the project population/task.

Keep `F = 3.14` pending independent human evidence.

Lowering F makes stars visible earlier and cannot repair an already-too-early concern.

Do not calibrate F from Jerusalem or Taylor.

---

# 11. Transient adaptation

Status: **runtime exists; experimental/shadow-only; physiological mapping open**.

- #119 freezes Eq.34 non-monotonic diagnostics;
- #117 governs the unresolved physical mapping question;
- #116 is not merge-ready;
- `tau=30 s` remains experimental, not calibrated.

External evidence supports history dependence, rate dependence, local-dominant adaptation, smaller surrounding-field influence and non-universal dynamics.

Current target-direction adaptation history is an experimental simplification, not a validated open-sky adaptation kernel.

Do not select tau or adaptation-field semantics from Jerusalem timing.

---

# 12. Spillmann / dynamic-adaptation curves

Exact external curve fitting remains blocked until reproducible source figure bytes/data are available.

Do not digitize from OCR/prose/guessed coordinates.

If reproducible data become available:

1. archive exact source/provenance;
2. calibrate axes/pixels;
3. digitize reproducibly with uncertainty;
4. fit/select only against external data;
5. freeze candidate mapping before project-event sensitivity.

---

# 13. Moon / natural night sky / artificial skyglow

These remain important but secondary to the current vertical-atmosphere/fast-mapping work.

- Moon PR #459 remains non-production; finite disk, spectral and real-sky validation remain.
- Natural-sky PR #460 remains non-production; no universal dark-sky floor.
- Artificial skyglow requires directional physical radiance, not a single SQM/World-Atlas scalar.
- Total-sky compositor foundations already exist; do not rebuild the compositor.

---

# 14. Remaining empirical gates

Even perfect computational atmosphere mapping does not close:

- independent twilight-radiance validation across multiple nights/sites/atmospheres;
- human first-seeing calibration/validation;
- transient adaptation in real open-sky search behavior;
- late/total-sky validation once Moon/airglow/zodiacal/integrated-starlight/artificial light matter.

Keep calibration/training and final holdout evidence separate.

---

# 15. Current priority order

## P0 — current active gate

1. Finish #550 exact-runtime OPAC + custom-tau syntax capability.
2. If PASS, close/merge the capability evidence only; if FAIL, diagnose the directive-composition boundary before any science.

## P1 — next scientific design

3. Preregister a small independent vertical-profile shape universe.
4. Freeze all numerical/scientific rules before result opening.
5. Do **not** allocate seeds/ordinal until review and runtime surface are fixed.

## P2 — direct MYSTIC vertical-profile isolation

6. Execute once under fresh immutable scientific identity.
7. Quantify sky-channel and derived Level-B sensitivity.
8. Preserve raw spectrum/numerical uncertainty and CRN-paired contrasts.

## P3 — fast model only if justified

9. If vertical-profile sensitivity is material, design a Level-B mapper/profile-envelope basis.
10. Validate on held-out direct-MYSTIC states before application integration.
11. Keep production/default false pending empirical real-sky evidence.

## Parallel non-duplicative work

12. Continue independent Taylor atmosphere search (EarthCARE/ATLID/lidar/AERONET/etc.).
13. Continue #117 transient mapping science.
14. Continue Moon/natural/artificial providers when capacity permits.

---

# 16. Do NOT do next

Do not:

- lower `F`;
- tune tau from Jerusalem;
- fit AOD/profile/provider/cycle to Taylor;
- add universal sky or time offsets;
- infer aerosol family from AOD;
- fabricate vertical structure;
- label modeled fields measurements;
- count CAMS republishers as independent evidence;
- convert HRRR smoke mass directly to calibrated aerosol extinction;
- accept all-zero CAMS extinction as aerosol-free air;
- apply column SSA/g vertically without labeling the approximation;
- reuse the old Taylor `+0.393 mag` discrepancy as current truth;
- reuse the old Taylor AOD derivative;
- blanket-rerun Taylor at high photons;
- reopen zenith work;
- rerun generic SSA/g sensitivity (AOPS already did it);
- rerun generic full phase/family sensitivity (AFPF already did it);
- rebuild basic aerosol-family interpolation (ASIV + starsvisibility #100 already did it);
- imply ASIV scalar PASS is full-spectrum validation;
- merge #116 before #117 science;
- imply Atmosphere State v2 richer fields already affect Level-B;
- activate Moon/natural/artificial components as trusted production defaults without their own gates.

---

# 17. Central current conclusion

The project is not presently showing evidence of a gross basic failure of spherical MYSTIC twilight physics.

The main operational lesson from Taylor is stronger and more useful:

> Accurate twilight prediction requires both a sound radiative-transfer model and sufficiently accurate knowledge of the real atmosphere, including vertical aerosol structure when it is material.

The project has now moved beyond merely identifying that problem:

- v1 atmosphere acquisition exists in current main;
- Operational Atmosphere State v2 design is merged;
- Operational Atmosphere State v2 data/QC/provenance foundation is merged and broad exact-head verified;
- general aerosol SSA/g/full-phase/family sensitivity and scalar fast-family interpolation are already closed for their stated scopes;
- generic vertical-profile transport mechanics are merged and CI-verified.

The principal remaining computational atmosphere problem is now narrow and explicit:

> **Quantify independently defined aerosol vertical-profile sensitivity at fixed column AOD and fixed rich optical properties, then build and validate a fast Level-B vertical-profile mapping only if that sensitivity justifies one.**

Production/default claims still require independent real-sky validation, and actual observer-visibility claims still require human evidence.
