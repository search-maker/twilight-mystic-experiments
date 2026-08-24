# Empirical twilight-radiance source admission v1

## Status

`REVIEW_ONLY_PREVALUE_METHODS_SUBSTANTIALLY_FROZEN_EXTERNAL_PGN_PRODUCT_METADATA_STILL_REQUIRED_NO_TARGET_RADIANCE_OPENED`

This package advances the next unresolved validation layer after ASIV v1: **physical twilight model vs measured real sky**. It does not reopen ASIV ordinal 39, execute MYSTIC, inspect selected target sky-radiance values, fit or retune any model, allocate a scientific ordinal, or authorize production.

The candidate, selection rules, comparison definitions and acceptance budget are frozen before target radiance is opened. The project still keeps three validation layers separate:

1. surrogate vs MYSTIC;
2. MYSTIC/atmosphere vs measured real sky;
3. end-to-end prediction vs human first-seeing.

ASIV v1 advanced layer 1 for aerosol transport. This package prepares layer 2 only.

## Primary candidate and current external blocker

The primary candidate remains Pandonia Global Network Pandora209 at the Izaña Atmospheric Observatory:

- `Pandora209s1`
- `Pandora209s2`

The source remains **promising but not yet strictly admitted**. The irreducible external question is whether the intended Pandora209 L1 type-2 sky-radiance measurements have an independently traceable absolute directional-radiance scale, with exact calibration validity, wavelength validity and uncertainty semantics for the selected spectrometer/time periods.

The public PGN calibration material reviewed so far shows additional Pandora209 spectrometer-2 calibration-analysis activity, but it does not by itself establish a finished operational s2 absolute-radiance calibration/validity binding. Radiance units alone are not treated as proof of independent absolute-radiance traceability.

A metadata-only question set was frozen before target opening in `PGN_METADATA_REQUEST.md`. On 2026-08-24 the user explicitly authorized sending that frozen request to PGN; the dispatch is separately recorded in `PGN_METADATA_REQUEST_DISPATCH.review.json`. No selected target spectrum or target radiance was attached, quoted or opened.

## What is now frozen locally

### 1. Absolute-radiance admission

Strict use requires L1 data type `2 = radiance [W/m2/nm/sr]` plus an acceptable independent absolute-radiance calibration chain and uncertainty definition. Corrected count rate, irradiance, units alone, normalized radiance, or a radiance scale derived by fitting the same class of twilight RT model are not enough for the strict independent gate.

### 2. Exact Level-B support across the complete AOD interval

`exact_aod_interval_support_v1.py` implements `EXACT_PAIRWISE_LOWER_ENVELOPE_V1`.

For fixed geometry/elevation, only normalized AOD varies. Each frozen support-point squared distance is `C_i+(x-a_i)^2`; pairwise distance differences are linear in `x`. The exact maximum nearest-support distance over a closed AOD interval is therefore obtained from the two interval endpoints plus every in-interval pairwise equality crossing. No AOD grid and no target residual are used.

Strict admission requires the entire independently admitted AOD interval to remain inside the physical domain and nearest frozen Level-B training distance `<= 0.60`.

### 3. Independent AOD/QC linkage

The AOD contract uses AERONET V3 Level 2.0 as the quantitative anchor and a value-independent MPLNET temporal/stability bridge where eligible. MPLNET is not treated as statistically independent from AERONET when its AER product is constrained/calibrated using AERONET. The resulting entire AOD550 interval must remain inside `[0.05,0.40]` and exact Level-B support.

Cloud evidence remains fail-closed and complementary rather than outcome-selected. Pandora/model residuals may not choose AOD, aerosol family, time matching or cloud disposition.

### 4. Certified model-set extrema over continuous AOD

`certified_aod_scenario_extrema_v1.py` implements `CERTIFIED_AOD_SCENARIO_EXTREMA_INTERVAL_BNB_V1`.

It binds the exact frozen Level-B v3 and ASIV runtime/model identities, partitions the one-dimensional AOD axis at all model-only k-nearest distance-order crossings and exact-hit points, and applies deterministic outward-enlarged interval branch-and-bound. Default certification tolerance is `1e-4` natural log, approximately `0.00011 mag`, far below the empirical acceptance budget.

The evaluator covers:

- native Level-B baseline;
- continental scenario;
- maritime scenario;
- desert scenario;
- desert-spheroids scenario;
- photopic, scotopic and Johnson-V scalar channels.

It never adapts its search to measured Pandora radiance and does not use epsilon substitution at exact hits.

### 5. Geometry, pairing and the dual-SkyFOV boundary

True per-exposure pointing metadata must be used. The current validated Level-B provider predicts integrated scalar channels for **one sky direction** and does not expose a validated full-spectral directional provider.

Therefore s1 and s2 records with genuinely different true SkyFOV directions cannot simply be stitched into one spectrum and compared with one scalar Level-B direction. Full three-channel strict use requires authoritative common/equivalent pointing or a separately reviewed pre-value compatibility proof. Spectral smoothness or model agreement may not be used to manufacture that equivalence.

The metadata-only s1/s2 hard-splice rule remains available when its calibration/wavelength/pointing prerequisites are satisfied, with no gain/offset fitting and no validation-value-selected crossover.

### 6. Independent s2-only Johnson-V lane

A useful narrower path is now explicit. Generic Pandora-2S s2 coverage contains the complete frozen Bessell Johnson-V passband, 470-700 nm. If the exact Pandora209s2 product is proven independently absolute-radiance calibrated across that range, Johnson-V can be derived from **s2 alone at its own true pointing** without any s1/s2 spectral splice.

That lane may support only the claim:

`PARTIAL_EMPIRICAL_REAL_SKY_JOHNSON_V_ONLY_PASS`

It cannot be promoted to photopic/scotopic validation, full three-channel Level-B validation, human first-seeing validation or production authorization.

### 7. Measurement-channel integration bytes

`MEASUREMENT_CHANNEL_INTEGRATION_BINDING.review.json` reuses the exact already-reviewed pre-opening Level-B measured-sky integrators instead of choosing new weighting after seeing Pandora data:

- `integrate_visual_response.py` Git blob `85646e2412ad2b53e7b08d24bd4f778f99f32e6d`;
- `johnson_v.py` Git blob `4ac7b419f8efec2c87ce71161d945ed0609ee852`;
- Bessell-V passband Git blob `eced08e8e126d59c9e4cfc52fea314711b3cea9c`, raw SHA-256 `20e8d89346b5bc71f848ff3eee054a92e1ba53872fb048ac670151b52dac99a1`.

Pandora W/m2/nm/sr radiance is converted by exactly `x1000` to the mW units expected by the frozen integration functions. No convenient-grid target resampling is introduced. Photopic/scotopic strict use still requires full calibrated 380-780 nm coverage; the missing 380-400 nm portion may not be silently dropped for s2-only use.

### 8. Numeric PASS/FAIL mapping

`SET_VALUED_ACCEPTANCE_GATES.review.json` maps the already-frozen MYSTIC-STATE-0074/0075 empirical error budget onto the current nonprobabilistic model set. The old thresholds were chosen before protected radiance was opened and are bound to the same Level-B v3 model/representation/provider; they were not retuned on real-sky residuals.

For each admitted observation/channel, the central measured value is compared with the complete frozen scenario-by-AOD model set. The primary error is the **certified upper bound on central set miss distance**, not distance to a measurement-uncertainty interval. External measurement/metadata uncertainty is then added positively, preserving the earlier conservative error-budget semantics.

Frozen gates:

- external sigma-log `<= 0.06`;
- equal-session P95 of session-mean conservative set miss `<= 0.20 mag`;
- worst preregistered marginal-stratum/channel P90 `<= 0.25 mag`;
- maximum single observation/channel `<= 0.60 mag`;
- signed set-miss bias upper statistic `<= 0.12` in natural-log domain.

AOD interval uncertainty and aerosol-family structural spread are already represented by the model set and are not added again as independent Gaussian sigma terms. No aerosol-family probabilities are introduced.

### 9. Absolute real-sky background rule

`ASTROPHYSICAL_BACKGROUND_BOUNDARY.review.json` freezes `ABSOLUTE_REAL_SKY_NO_ASTROPHYSICAL_SUBTRACTION_V1` for the present model generation.

The primary comparison uses the admitted calibrated **absolute real-sky radiance after normal instrument corrections**, with no validation-specific fitted constant, spectral offset or post-hoc deep-night subtraction. Airglow/zodiacal/integrated-starlight mismatch therefore remains empirical model-form error for this generation. A deterministically selected deep-night observation may be retained as a diagnostic, but it cannot rescue a primary FAIL after opening.

### 10. Complete metadata-only session universe

`SESSION_UNIVERSE_FREEZE_PRECONTRACT.review.json` defines one independent session as one astronomical dawn or dusk transition through Sun depression 2-10.5 degrees. High-cadence rows within one transition do not become independent sessions.

Every metadata-eligible session inside the frozen calibration/product/operation validity windows must be included. The universe is not capped at 40 favorable nights:

- fewer than 40 eligible independent sessions -> `DATA_REQUIRED`;
- 40 or more -> retain all eligible sessions with equal-session aggregation;
- no replacement, outlier deletion or bad-channel deletion after opening.

The pre-opening manifest records immutable object identity, calibration/operation validity, type/unit, pointing, AOD/QC provenance, exact support result and source-lane disposition, but **not** the target spectral array, derived target channels or model residual.

If the provider does not publish a checksum in metadata, the exact provider object identity/header is frozen first; only after separate opening authorization may the object be downloaded, immediately hashed in untouched form, and then parsed.

## Current model-form boundary

The validated sky model remains exactly the current five-axis Level-B v3 representation:

- Sun depression;
- target altitude;
- relative solar azimuth;
- observer elevation;
- AOD550.

The frozen MYSTIC generation uses AFGLUS, surface albedo 0.15, `crs`, `atlas_plus_modtran`, `aerosol_default`, spherical 1D, and 380-780 nm. Water vapor, ozone, local albedo, pressure and detailed aerosol profile are not hidden post-hoc fitting axes. External measurements may be preserved as diagnostics; systematic dependence remains empirical model-form error and may motivate only a new model generation with a genuinely new untouched holdout.

## Claim scope

Izaña is near the high-elevation end of the current 0-2500 m domain. A strict Izaña PASS is valuable high-elevation real-sky evidence but does **not** by itself validate model elevation dependence across the full domain.

A full frozen-domain empirical claim requires independent coverage across all frozen marginal strata, including elevation. A source-scoped or Johnson-V-only result must retain that narrower label.

## Remaining true blockers before target opening

Most locally decidable pre-value method choices are now frozen. The principal remaining blockers are external/product-specific rather than permission to inspect the target radiance:

1. exact Pandora209 absolute sky-radiance traceability and calibration validity for the intended lane, especially s2;
2. exact L1 type-2 uncertainty/covariance and absolute-radiance-valid wavelength/filter semantics;
3. authoritative PGN per-exposure pointing/time fields and their conventions;
4. for full three-channel use, authoritative s1/s2 pairing and proof of directional compatibility with the current single-direction Level-B provider;
5. actual metadata-only enumeration of the complete eligible session universe using the resolved PGN field/product semantics, followed by execution of the already-frozen AOD/support/cloud gates and hashing of that universe;
6. a separately reviewed exact-file opening manifest/authorization.

If s2 absolute-radiance calibration and 470-700 nm validity are confirmed before the full dual-spectrometer questions are resolved, the s2-only Johnson-V lane can proceed independently through items 2, 3, 5 and 6.

## Hard boundaries

This package still authorizes none of the following:

- PGN target `/v1/download` for validation;
- opening selected `LEVEL1.DATA` target arrays;
- deriving target photopic/scotopic/Johnson-V values before opening authorization;
- MYSTIC/scientific execution or a new ordinal;
- ASIV rerun/retry/resume;
- retuning the Level-B or ASIV models;
- fitting AOD/aerosol family/background/pointing to target radiance;
- probability or confidence semantics for the five aerosol scenarios;
- production/UI/default activation;
- claiming human first-seeing validation.

## Next safe transition

While waiting for PGN's metadata reply, no target radiance should be opened. Once the product/calibration/pointing facts are available, bind the exact metadata semantics, construct and hash the complete metadata-only eligible/rejected session universe, execute the frozen support/AOD/QC gates on that universe, and prepare a separate exact-object opening manifest. Only that separately reviewed transition can authorize target-value opening.
