# Star-visibility model closure matrix — current authoritative status

Status: **review-only master closure record**.

Updated: **2026-08-27 after PRs #114, #118, #119 and Operational Atmosphere State v2 design PR #120**.

This file does not change runtime, thresholds, `F`, `tau`, atmosphere values, Level-B support, production routing, or any empirical/human validation flag.

Its purpose is to keep one current source of truth separating:

1. computationally strong/closed work;
2. work that can still advance from independent external data;
3. work requiring new empirical human/open-sky evidence;
4. operational atmosphere acquisition/representation/mapping work that must not be confused with parameter fitting.

---

## 0. Global governance

Do not choose or tune any of the following to move Jerusalem, Tishrei, Tammuz, or Taylor toward a desired result:

- `F`;
- transient `tau`;
- AOD;
- aerosol vertical profile;
- aerosol family;
- SSA;
- phase function / asymmetry parameter;
- provider or model cycle;
- sky offset;
- clock/minute offset;
- threshold coefficients;
- interpolation/support rule;
- stop rule.

External atmosphere or psychophysical evidence may select/freeze a candidate **before** target-event scoring.

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

---

# 1. Current GitHub status

## starsvisibility #114 — MERGED

`Route validated Level-B sky + stellar support through exact zenith`

- merged into `main`;
- exact physical 90 deg sky/stellar support is now routed through current main;
- old <=80 deg behavior remains preserved;
- exact-head broad verification passed;
- production/real-sky/human validation claims remain closed.

**Do not reopen the 90 deg sky/stellar computational campaign.**

## starsvisibility #118 — MERGED

`Make Level-B current-main test runnable from clean checkout`

- merged into `main`;
- fixes test/build lifecycle only;
- no scientific/runtime behavior change.

## starsvisibility #119 — MERGED

`Freeze Crumey Eq.34 transient equivalent-background transition diagnostic`

Diagnostic-only baseline now frozen in `main`:

- local threshold maximum near `B = 0.021567318651 cd/m^2`;
- local threshold minimum near `B = 0.047052552759 cd/m^2`;
- threshold drop about `2.600936%`;
- maximum formal local negative adaptation penalty about `-0.028613 mag`;
- existing fail-closed negative-penalty behavior remains the current semantic baseline.

This merge intentionally did **not** authorize a replacement transient mapping.

## starsvisibility #116 — OPEN / DO NOT MERGE YET

`Fix transient negative-penalty topology artifact`

The branch proposes replacing the negative-penalty fail-closed condition with an equilibrium/monotone floor and exposing raw/floored diagnostics.

That proposal predates the merged #119 baseline and is not currently merge-ready.

Before any merge, #116 must be reconciled with current `main`, #119 and issue #117. In particular:

1. characterize actual real Level-B `(physical B, adaptation debt, effective B)` trajectories;
2. complete the #117 scientific decision about the equivalent-background mapping;
3. justify any branch/state/threshold-space replacement from independent psychophysical evidence;
4. preregister the shadow-only acceptance test before changing semantics;
5. rerun the correct full post-decision timing audit;
6. rerun exact-head parity/build on current main.

Until then, retain the current fail-closed guard. Do not merge #116 merely because its older parity/timing tests passed.

## starsvisibility #48 — OLD DRAFT; FOUNDATION PARTLY ALREADY IN MAIN

`Add Level-B runtime integration foundation`

Do **not** re-import or merge this old stack wholesale to obtain atmosphere acquisition.

Current `main` already contains exact PR #48 byte identities for important v1 atmosphere/runtime foundation files, including:

- `atmosphere-state.mjs`;
- `atmosphere-resolver.mjs`;
- `aeronet-atmosphere.mjs`;
- `open-meteo-cams-atmosphere.mjs`;
- associated acquisition tests and Level-B foundation paths.

The current site-wide regression explicitly hash-binds these PR #48-origin files.

Therefore the remaining atmosphere work is **not** to recreate v1. It is to extend the authoritative current-main foundation into a richer reviewed v2 contract.

## starsvisibility #120 — NEW DRAFT DESIGN

`Design Operational Atmosphere State v2`

Review-only design based on current `main`.

It separates:

- atmosphere acquisition;
- atmosphere representation/provenance;
- physical quality control;
- Level-B consumption/mapping;
- validation of that fast mapping.

No runtime or production behavior is changed by #120.

---

# 2. Solar twilight / MYSTIC / Level-B

## Status

**Direct MYSTIC twilight physics: computationally strong; real-sky validation partial.**

The present evidence does not support a simple large defect in spherical MYSTIC twilight physics as the explanation for the broad timing concern.

Exact-event Level-B vs direct-MYSTIC comparisons do not have one universal sign:

- Tishrei direct MYSTIC was darker than Level-B at the determining directions;
- Tammuz had mixed spatial sign.

Therefore do not add a universal Level-B sky magnitude correction.

Taylor Ann Arbor is one valuable independent real-SQM consistency case for **direct MYSTIC**, not a direct validation of Level-B or human first-seeing.

---

# 3. Taylor — authoritative current interpretation

The current conclusion is **not**:

> We know the exact Taylor atmosphere.

The current conclusion is:

> Direct MYSTIC is broadly consistent with Taylor, and independently constrained aerosol vertical structure removed much of the former onset-region discrepancy.

## Vertical-profile result — #508

In the original-SQM 380–780 nm calculation, total AOD, geometry, pressure, calibration and the other frozen inputs were retained while the normalized aerosol vertical extinction shape was replaced by the independently obtained CAMS shape.

Important onset-region changes:

- Sun `-5.808 deg`: residual about `+0.393 -> +0.087 mag`;
- Sun `-6.134 deg`: residual about `+0.388 -> +0.031 mag`.

No SQM offset or AOD was fitted to Taylor.

This strongly supports a material role for aerosol vertical distribution. It does **not** prove that the exact Taylor atmosphere is known.

## Monte-Carlo numerical uncertainty — #535

Do not use the old broadband `mc.rad.std.spc` as a calibrated between-seed uncertainty estimator.

Empirical single-run scatter from the dedicated multi-seed screen is approximately:

- row1 `0.00264 mag`;
- row5 `0.00517`;
- row9 `0.00709`;
- row13 `0.00801`;
- row17 `0.01100`;
- row21 `0.02630`;
- row24 `0.0704`;
- row25 `0.0906`.

Taylor repeatability remains about `0.06215 mag`.

Thus numerical uncertainty is small through much of the early/middle primary interval and becomes material late. No blanket high-photon rerun of the entire dataset is justified.

## Late residuals / AOD derivative — #529

Six-seed 200k central residuals for rows 23–25 are approximately:

- `+0.08544`;
- `+0.17350`;
- `+0.17696 mag`.

Those late rows are not compelling standalone inconsistencies after the proper partial uncertainty treatment.

The reconverged AOD finite-difference derivative remains **unresolved**. Do not reuse the former large late-row AOD derivative as a precise physical sensitivity.

## CAMS provenance — #536

Same-cycle CAMS spectral column optics were physically sensible around Taylor, approximately:

- AOD550 `0.31–0.32`;
- SSA550 about `0.95`;
- `g550` about `0.71`;
- Angstrom alpha about `1.28`.

But direct forecast00 vertical extinction returned 137 exact zero coefficients at 355/532/1064 nm despite nonzero column AOD. Forecast03 profiles were valid and integrated consistently with column AOD.

Therefore:

- valid column information does not automatically validate a vertical product;
- forecast00 must not be interpreted as a real aerosol-free profile;
- prior-cycle and same-cycle vertical information are not interchangeable without explicit provenance;
- applying column SSA/g uniformly with altitude would be a new approximation and must be labeled as such;
- do not label another run “direct same-cycle full CAMS atmosphere” unless the missing vertical information is genuinely resolved.

## Taylor atmosphere search

Independent atmosphere searches (EarthCARE/ATLID, lidar/ceilometer, AERONET and other independent archives) are a separate lane.

If new evidence is found:

1. freeze source/product/cycle/time/distance/quality rules first;
2. archive exact provenance;
3. determine source independence;
4. decide scientifically how the quantity may enter MYSTIC;
5. only then score Taylor residuals.

Never select the source/cycle/profile because it fits Taylor better.

---

# 4. Operational Atmosphere State v2 — major current workstream

Taylor demonstrated operationally that total AOD alone is not enough for maximum-accuracy twilight work.

The project now requires a location/time-dependent physical atmosphere state for requested:

`location + elevation + date + time`.

Draft design lives in `starsvisibility #120`.

## v2 should be able to represent, when available

### Column aerosol

- spectral AOD;
- canonical AOD550;
- Angstrom behavior and uncertainty.

### Vertical aerosol

- extinction profile vs altitude and wavelength;
- backscatter/profile quantities when scientifically useful;
- normalized vertical optical-depth distribution only when legitimately derivable;
- vertical resolution/reference and quality flags.

### Optical properties

- SSA spectrum;
- phase function / asymmetry representation;
- aerosol type/classification provenance;
- vertical applicability of any column optical property.

### Molecular atmosphere

- pressure/profile identity;
- temperature profile where justified;
- Rayleigh/molecular-column identity;
- ozone, water vapor and other admitted absorbers.

### Surface

- ground/source elevation;
- relevant spectral/band albedo information.

### Clouds

- explicit clear/contaminated/unknown status;
- cloud height/optical properties only where separately admissible;
- clear-sky calculations remain fail-closed when cloud contamination is material.

### Provenance / quality

Every material component should retain:

- service provider;
- underlying scientific source;
- product/version/processing level;
- measured/model/forecast/reanalysis/satellite/climatology status;
- valid time;
- model/retrieval cycle and forecast lead;
- source location/elevation;
- spatial/temporal mismatch;
- horizontal/vertical resolution;
- wavelength coverage;
- interpolation;
- native/project quality flags;
- uncertainty;
- fallback/rejection history;
- reproducible artifact/request identity.

Service provider and underlying scientific source must remain distinct. Two APIs republishing CAMS do not create two independent atmosphere constraints.

## Incomplete state is allowed

A state with good AOD but no valid vertical profile is an incomplete state, not an excuse to fabricate a profile.

Downstream consumers must decide whether the available components support the requested claim tier.

## Physical QC is mandatory

Examples:

- negative AOD/extinction -> reject;
- nonzero column AOD + all-zero vertical extinction -> reject vertical component;
- integrated vertical extinction grossly inconsistent with column AOD -> reject or preserve an explicit conflict;
- missing/invalid altitude coordinate -> reject affected component;
- excessive station/grid elevation mismatch -> reject under frozen policy;
- excessive time/space mismatch -> reject under frozen policy;
- stale data -> reject where freshness is required;
- SSA outside `[0,1]` -> reject;
- AOD-only aerosol-family inference -> forbidden;
- column SSA/g used at all heights -> mark as approximation;
- cloud contamination for a trusted clear-sky calculation -> fail closed.

---

# 5. Four separate atmosphere problems — do not collapse them

The project must keep these distinct:

## A. Acquire the actual atmosphere

Find admissible measured/satellite/model/reanalysis/climatological components for the requested location/time.

## B. Represent it faithfully

Store the components, missingness, conflicts, uncertainties, source lineage and space/time mismatch without fabrication.

## C. Feed it into the fast model

Current Level-B is not an arbitrary-profile radiative-transfer engine. A richer atmosphere state does not automatically mean the fast model uses all of it.

A separately validated mapping is needed. Candidate architectures may include:

- parameterized vertical-profile corrections;
- expanded surrogate dimensions;
- a small physically selected aerosol/profile basis;
- hybrid precomputed/direct radiative-transfer tables;
- separate treatment of column optics and normalized profile shape.

No architecture is selected merely by the v2 schema.

## D. Validate the fast mapping

Any new fast atmosphere mapping must be checked against direct MYSTIC on held-out atmosphere states and later against independent real-sky evidence.

This is separate from provider acquisition success.

---

# 6. Environment sensitivity program

Before adding new runtime dimensions, use externally defined/preregistered ranges and quantify effects on:

- sky radiance;
- limiting magnitude;
- event timing;
- support/OOD behavior;
- runtime dimensional cost.

Priority dimensions:

1. normalized aerosol vertical profile;
2. spectral AOD / Angstrom behavior;
3. SSA;
4. phase function / `g`;
5. profile x optical-property interactions.

Then audit before promotion:

- pressure/molecular state;
- temperature profile;
- ozone;
- water vapor;
- surface albedo;
- humidity-dependent aerosol optical behavior.

Do not choose sensitivity ranges from Taylor or Jerusalem residuals.

---

# 7. Stellar direct atmospheric transport

## Status: computationally strong for the current question

Matched/native stellar direct-transport differences under ordinary supported geometries are generally seconds-scale in event timing, not a generic several-minute effect.

Low-altitude/red-star cases can be larger and should be reported individually.

Do not confuse stellar direct-beam transport with aerosol effects on twilight **sky scattering**, where vertical aerosol structure has demonstrated a much larger effect in Taylor.

Do not reopen stellar transport as an untargeted place to seek a large correction.

---

# 8. Human point-source threshold / F

Crumey/Blackwell applicability is reasonably supported as a point-source threshold foundation, but modern naked-eye first-seeing is not empirically validated for the project population/task.

Keep `F = 3.14` pending independent human evidence.

Lowering F makes stars visible earlier and therefore cannot repair an already-too-early timing concern.

Do not recalibrate F from Jerusalem or Taylor.

---

# 9. Transient adaptation

## Current status

- runtime exists but is experimental/shadow-only;
- `tau = 30 s` remains experimental, not physiologically calibrated;
- #119 freezes the exact Eq.34 non-monotonic diagnostic;
- #117 remains the governing physical question;
- #116 is not merge-ready.

The key unresolved question is whether waning-adaptation debt should be represented by direct added equivalent luminance through Eq.34, by threshold-space/state-aware mapping, or another externally supported construction.

Current external evidence supports:

- history dependence;
- darkening-rate dependence;
- local-dominant adaptation;
- smaller surrounding-field influence;
- non-universal recovery dynamics.

The current target-direction photopic adaptation-field history is an experimental simplification, not a validated open-sky adaptation kernel.

Do not choose the adaptation field or tau from Jerusalem event times.

---

# 10. Spillmann curves

Exact external dynamic-adaptation fitting remains blocked until reproducible source figure bytes/data are available.

Do not digitize from OCR, prose or guessed coordinates.

If reproducible figure data become available:

1. archive source/provenance;
2. calibrate axes/pixels;
3. digitize reproducibly;
4. quantify digitization error;
5. fit external psychophysical data only;
6. freeze candidate;
7. only afterward run project-event sensitivity.

Do not copy the large laboratory maximum effect directly into natural twilight.

---

# 11. Mesopic / color

The standardized MES2 sensitivity lane is computationally small for the frozen Jerusalem cases:

- Tishrei about `+17.8 s`;
- Tammuz `0 s`.

It is not a broad multi-minute explanation.

Do not activate it as validated human physiology and do not prioritize further Jerusalem color tuning.

---

# 12. Moon

Draft #459 remains incomplete.

ROLO source/MYSTIC contract exists, but remaining work includes:

- finite lunar disk treatment;
- independent spectral cross-check;
- scattered-moonlight validation;
- real-sky validation;
- production authorization.

Do not wire Moon into trusted total sky yet.

---

# 13. Natural night sky

Draft #460 remains incomplete.

Preferred baseline direction remains GAMBONS.

A constant dark-sky floor is forbidden.

Need a provider with explicit location/time/direction/spectral-channel provenance and exclusion of Moon/artificial skyglow, with compatible atmosphere identity.

---

# 14. Artificial skyglow

One zenith SQM or World Atlas value is not sufficient for arbitrary target direction.

Future architecture must use either calibrated directional/all-sky information or physical propagation of emission inventories through the atmosphere.

Do not invent an altitude/azimuth correction to improve event times.

---

# 15. Total sky compositor

Architecture is already merged in #112 and supports Solar/Moon/Natural/Artificial components in common physical channels with atmosphere identity and fail-closed semantics.

Do not rebuild it.

Remaining work is to provide separately admissible component providers.

---

# 16. What not to do next

Do not:

- lower `F` to repair timing;
- choose tau from Jerusalem;
- add universal sky or clock offsets;
- choose AOD/profile/provider/cycle from Taylor residuals;
- choose aerosol family from AOD alone;
- hide missing atmosphere under `aerosol_default`;
- call modeled data measurements;
- count a CAMS republisher as independent CAMS evidence;
- promote HRRR smoke mass directly to calibrated optical extinction;
- treat CAMS forecast00 all-zero extinction as a real aerosol-free profile;
- apply column SSA/g uniformly with height without an explicit approximation flag;
- reuse the former Taylor `+0.393 mag` discrepancy as stable;
- reuse the former large late-row AOD derivative as resolved;
- run blanket high-photon Taylor reruns;
- reopen the 90 deg MYSTIC/stellar campaign;
- merge #116 from its old evidence alone;
- silently treat solar-only sky as total sky;
- enable unfinished Moon/Natural/Artificial providers as trusted production values.

---

# 17. Current priority order

## P0

1. **Keep this #539 closure matrix current** as the single master record.
2. **Review/freeze Operational Atmosphere State v2** in `starsvisibility #120`.
3. **Complete the current-main vs #48 audit** without duplicating foundation already in main.
4. **Reconcile #116 against #119/#117/current main** before any semantic merge.

## P1

5. Run preregistered environmental-dimension sensitivity studies.
6. Design and validate the fast Level-B atmosphere mapping separately from data acquisition.
7. Preserve/close Taylor evidence across #508/#529/#535/#536/#487/#489 without duplicate campaigns.
8. Continue #117 external-physiology/trajectory work.
9. Continue Moon/Natural/Artificial non-observation provider work behind separate gates.

## P2

After the architecture/sensitivities are clear:

- implement richer atmosphere providers;
- add component fusion/fallback only with reviewed compatibility rules;
- add atmosphere confidence/completeness grades;
- implement a validated fast profile/optical-property mapper;
- expand total-sky component providers;
- prepare all for later independent empirical validation.

---

# 18. Reporting contract

Every new scientific/engineering work item should report:

- repository;
- issue/PR;
- branch;
- SHA;
- exact scientific question;
- exact inputs frozen before scoring;
- whether Taylor/Jerusalem residuals were inspected before choosing parameters/source;
- service provider;
- underlying scientific source;
- measured/modelled/forecast/reanalysis/satellite/climatology status;
- exact valid time/cycle;
- exact source location/grid/station;
- spatial/temporal/elevation mismatch;
- vertical coverage/resolution;
- spectral coverage;
- uncertainty;
- quality flags;
- workflow/run ID;
- artifact/digest;
- result;
- remaining uncertainty;
- whether production behavior changed;
- whether this #539 master record needs another update.

---

# 19. Central scientific conclusion

The present evidence does **not** support a simple large error in basic MYSTIC twilight physics as the explanation for the project’s broad timing concern.

Taylor has instead established an operationally crucial lesson:

> Accurate twilight prediction requires both a validated radiative-transfer model and an accurate, independently constrained description of the actual atmosphere for that place and time.

In particular, aerosol vertical structure can materially alter twilight radiance even when total column AOD is held fixed.

The major non-observation objective is therefore:

> **Build a rigorous location/time-dependent environmental state and a separately validated way for Level-B to consume it.**

The project should ask:

> Which physical quantities really vary from place to place and night to night, how much do they change the prediction, where can they be obtained independently, and how can the fast model consume them with explicit uncertainty?

It should not ask:

> Which parameter can we tweak until the desired time or residual appears?
