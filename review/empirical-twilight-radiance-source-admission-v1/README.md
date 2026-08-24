# Empirical twilight-radiance source admission v1

## Current status

`REVIEW_ONLY_LOCAL_PREVALUE_METHODS_FROZEN_EXTERNAL_PANDORA209_PRODUCT_BINDING_REQUIRED_NO_TARGET_RADIANCE_OPENED`

This package prepares validation layer 2 only:

1. surrogate vs MYSTIC — ASIV already advanced this for aerosol transport;
2. **frozen MYSTIC/atmosphere model vs measured real sky** — this package;
3. end-to-end model vs human first-seeing — separate work.

No selected Pandora target `LEVEL1.DATA`, target per-pixel uncertainty array, derived target channel, or target residual has been opened. No MYSTIC/scientific execution, new ordinal, ASIV rerun/retry/resume, model fitting, UI/default change, or production authorization occurs here.

## Primary source

Primary candidate:

- Izaña Atmospheric Observatory;
- `Pandora209s1`;
- `Pandora209s2`.

The local pre-value methods are now substantially closed. The remaining blockers are Pandora209/current-product facts rather than missing local acceptance algorithms.

The most important unresolved fact is the exact independently traceable **absolute sky-radiance calibration/validity chain for Pandora209 spectrometer 2**. Public calibration material shows real s2 calibration-analysis activity, but the reviewed public metadata has not established the finished operational s2 absolute-radiance binding required by the strict gate. This is a blocker, not a claim that s2 is bad.

## PGN request and provenance

`PGN_METADATA_REQUEST.md` is intentionally preserved as the exact pre-send question artifact. It still says “draft only” because rewriting it after dispatch would destroy the pre-send provenance.

Exact request Git blob at dispatch:

`4dfb2edb4d80c4cf91022016ebb6abe7f4cef036`

The actual send event is separately bound in:

`PGN_METADATA_REQUEST_DISPATCH.review.json`

The request was sent on 2026-08-24 after explicit user authorization. No target spectrum was attached or quoted. A PGN reply may resolve metadata, but a reply cannot authorize target opening by itself.

## Generic PGN Level-1 metadata semantics already resolved

`PGN_L1_GEOMS_METADATA_SEMANTICS.review.json` freezes the generic field semantics already documented by PGN, so these are no longer treated as unknown merely because Pandora209-specific mapping remains unresolved.

Documented generic fields include:

- `DATETIME.START` — measurement start, fractional days since 2000-01-01;
- `DURATION` — seconds;
- `INTEGRATION.TIME` — milliseconds;
- `LEVEL1.DATA.TYPE`:
  - 1 = corrected count rate `[s^-1]`;
  - 2 = radiance `[W/m2/nm/sr]`;
  - 3 = irradiance `[W/m2/nm]`;
- `LEVEL1.DATA`;
- `LEVEL1.UNCERTAINTY`;
- `LEVEL1.UNCERTAINTY.INSTRUMENT`;
- `POINTING.AZIMUTH.ANGLE` / `.MODE`;
- `POINTING.ZENITH.ANGLE` / `.MODE`;
- pointing mode 0 = absolute, 1 = relative to Sun, 2 = relative to Moon;
- `ROUTINE`;
- filterwheel fields whose physical meaning still requires the applicable operation file.

Still unresolved and fail-closed:

- exact current Pandora209 API/archive field mapping;
- exact sign/reference conversion for relative pointing modes;
- true per-spectrometer pointing versus merely commanded/nominal pointing;
- exact operation/filterwheel validity;
- authoritative s1/s2 pairing;
- Pandora209 absolute-radiance calibration validity;
- uncertainty/covariance/common-mode semantics.

## Strict absolute-radiance gate

L1 type `2 = radiance [W/m2/nm/sr]` is necessary but not sufficient.

Strict independent validation additionally requires an independently established absolute directional sky-radiance scale. Units, corrected counts, irradiance calibration, normalized radiance, or a radiance scale obtained by forcing the same class of twilight radiative-transfer model to match the sky are not enough by themselves.

## Exact continuous-AOD Level-B support

`exact_aod_interval_support_v1.py`

Algorithm:

`EXACT_PAIRWISE_LOWER_ENVELOPE_V1`

For fixed geometry/elevation only normalized AOD varies. Every frozen support-point squared distance is `C_i + (x-a_i)^2`; nearest-point identity can change only at pairwise equality crossings. The exact maximum nearest support distance over the admitted AOD interval is therefore evaluated at the interval endpoints and every in-interval crossing, not on a grid.

Strict support requires the whole external AOD interval to remain inside the physical AOD domain and nearest frozen Level-B training distance `<= 0.60`.

## Independent AOD/QC linkage

The frozen atmosphere-input path uses:

- AERONET V3 Solar Level 2.0 as the absolute AOD anchor;
- MPLNET as a value-independent temporal/stability bridge, not independent absolute truth when its retrieval/calibration itself depends on sun/lunar photometer constraints;
- conservative interval propagation;
- no AOD fitting from Pandora radiance;
- no clamping back into `[0.05,0.40]`;
- complementary fail-closed MPLNET/SONA cloud evidence.

The final entire AOD interval must remain in `[0.05,0.40]` and pass exact continuous Level-B support.

## Certified full-AOD model-scenario extrema

`certified_aod_scenario_extrema_v1.py`

Algorithm:

`CERTIFIED_AOD_SCENARIO_EXTREMA_INTERVAL_BNB_V1`

The evaluator certifies minima/maxima over the full external AOD interval for:

- native baseline;
- continental;
- maritime;
- desert;
- desert-spheroids;
- photopic, scotopic and Johnson-V scalar channels.

It partitions on model-only neighbor-order crossings/exact hits and uses deterministic interval branch-and-bound. Default certification tolerance is `1e-4` natural-log units, about `0.00011 mag`. Target radiance never controls the search and no epsilon substitution is allowed.

## Measurement-channel integration

`MEASUREMENT_CHANNEL_INTEGRATION_BINDING.review.json` reuses the exact already-reviewed Level-B measured-sky integrators:

- `integrate_visual_response.py` Git blob `85646e2412ad2b53e7b08d24bd4f778f99f32e6d`;
- `johnson_v.py` Git blob `4ac7b419f8efec2c87ce71161d945ed0609ee852`;
- Bessell-V passband Git blob `eced08e8e126d59c9e4cfc52fea314711b3cea9c`;
- Bessell-V raw SHA-256 `20e8d89346b5bc71f848ff3eee054a92e1ba53872fb048ac670151b52dac99a1`.

Pandora type-2 `W/m2/nm/sr` is multiplied by exactly 1000 before these mW-based integrators are applied. Target spectra are integrated on their supplied strictly increasing wavelength grid; no convenient-grid outcome-dependent resampling is introduced.

Photopic/scotopic strict use still requires calibrated 380–780 nm coverage.

Johnson-V requires 470–700 nm.

## Conservative measurement-uncertainty propagation

`MEASUREMENT_UNCERTAINTY_PROPAGATION.review.json` freezes the numerical dispatch before selected target uncertainty arrays are opened.

For a fixed wavelength grid, every primary channel is a linear functional:

`channel = sum_i(w_i * radiance_i)`

If full covariance is documented:

`sigma_channel = sqrt(w^T C w)`

If only per-pixel one-sigma uncertainties are documented and wavelength correlation is not documented, independence is **not** assumed. The conservative maximum-correlation upper bound is:

`sigma_channel_upper = sum_i(abs(w_i) * sigma_i)`

If uncertainty coverage is not known to be one-sigma, the source semantics remain unresolved; no coverage factor is guessed.

For the full s1+s2 lane, documented cross-spectrometer covariance/common scale must be preserved. Unknown cross-spectrometer correlation is not set to zero. The s2-only Johnson-V lane avoids this particular cross-spectrometer uncertainty problem.

The resulting measurement contribution feeds the existing `externalSigmaLog <= 0.06` gate. A row may not be deleted after opening because its uncertainty is inconveniently large.

## Geometry, pairing and dual SkyFOV

Use true per-spectrometer pointing and exact exposure time.

`targetAltitudeDeg = 90 - truePointingZenithAngleDeg`

Relative solar azimuth is folded to `[0,180]` only after the target and Sun are expressed in the same absolute azimuth convention.

Pairing must be metadata-only. Brightness, spectral shape, or model agreement may not choose s1/s2 pairs.

The current validated Level-B provider predicts integrated scalar channels for **one sky direction**. Therefore two materially different true s1/s2 SkyFOV directions cannot silently be stitched into one strict single-direction measurement. Full three-channel use requires authoritative common/equivalent pointing or a separately reviewed pre-value directional-compatibility proof.

When full dual-spectrometer use is otherwise admissible, the frozen hard metadata midpoint splice uses no overlap gain/offset fit and no target-smoothness-selected crossover.

## s2-only Johnson-V lane

If exact Pandora209s2 absolute-radiance validity covers 470–700 nm, a strict Johnson-V comparison can proceed from s2 alone at its own true pointing, without s1/s2 stitching.

Maximum possible claim after a terminal PASS:

`PARTIAL_EMPIRICAL_REAL_SKY_JOHNSON_V_ONLY_PASS`

This does not validate photopic/scotopic, full elevation dependence, human first-seeing, or production.

## Absolute real-sky background rule

`ASTROPHYSICAL_BACKGROUND_BOUNDARY.review.json` freezes:

`ABSOLUTE_REAL_SKY_NO_ASTROPHYSICAL_SUBTRACTION_V1`

The primary comparison uses admitted calibrated absolute real-sky radiance after normal instrument corrections. No validation-specific deep-night subtraction, fitted constant, or fitted spectral offset is allowed. Deep-night evidence may remain diagnostic only.

Omitted airglow/zodiacal/integrated-starlight terms therefore remain empirical model-form error for the current generation rather than being removed after seeing residuals.

## Nonprobabilistic set-valued comparison and numeric gates

The complete frozen five-state aerosol scenario set is evaluated over the full external AOD interval. The native baseline remains separately reportable. No scenario probabilities are assigned and nearest scenario is diagnostic only.

Frozen numerical gates inherited from the pre-opening 0074/0075 accuracy budget are:

- external sigma-log `<= 0.06`;
- equal-session P95 session-mean conservative set miss `<= 0.20 mag`;
- worst frozen marginal-stratum/channel P90 `<= 0.25 mag`;
- maximum single observation/channel `<= 0.60 mag`;
- signed set-miss bias upper statistic `<= 0.12` natural-log units.

AOD interval and aerosol-family spread are already represented by the model set and are not added again as independent Gaussian sigma terms. ASIV computational validation error is not converted into empirical measurement confidence.

## Complete metadata-only universe

`METADATA_UNIVERSE_CONTRACT.review.json` and `SESSION_UNIVERSE_FREEZE_PRECONTRACT.review.json` freeze the universe before target opening.

One astronomical dawn or dusk transition is one independent session.

Every metadata-eligible session in the applicable frozen validity windows is retained, alongside rejected rows and their frozen rejection reasons.

- fewer than 40 eligible independent sessions: `DATA_REQUIRED` for terminal PASS;
- 40 or more: retain all eligible sessions;
- never trim to the 40 best nights;
- never select by target brightness, residual, nearest aerosol scenario, or post-opening convenience.

The normalized universe contains metadata, external atmosphere/QC, calibration/operation identity, exact support results, and hashes — not selected `LEVEL1.DATA`, target uncertainty values, integrated observed channels, or target residuals.

## Exact-object opening contract already frozen

`TARGET_OPENING_MANIFEST_CONTRACT.review.json`

Validator:

`validate_target_opening_manifest_v1.py`

The validator requires:

- exact dataset freeze ID and lane;
- canonical hashes of every pre-value binding;
- exact nonempty object list;
- source object/provider path identity;
- site/instrument/spectrometer/exposure identity;
- metadata hash;
- calibration and operation binding IDs;
- explicitly named protected arrays;
- canonical object ordering;
- no target outcome/statistics/residual fields;
- no self-authorization.

Allowed v1 lanes are:

- `PANDORA209_S2_JOHNSON_V_ONLY_V1`;
- `PANDORA209_S1S2_THREE_CHANNEL_V1`.

The pre-value manifest must say `targetOpeningAuthorized=false`. Opening requires a **separate reviewed authorization artifact bound to the exact manifest canonical SHA-256**.

Post-opening object substitution, threshold changes, AOD/family fitting, pointing-convention changes, s1/s2 re-pairing, stitch changes, or primary background-rule changes are forbidden.

## Secondary sources frozen before primary opening

`SECONDARY_SOURCE_CANDIDATES.review.json` preserves the fallback inventory before any Izaña target opening.

Important examples:

- Jeonju / Pandora241: public s1+s2 archive is visible, but strict continuous AOD/QC and finished s2 absolute-radiance binding are not proven;
- Seoul-KU / Pandora235: favorable aerosol context and public spec2 calibration activity, but the reviewed public target archive did not surface s2;
- Yongin / Pandora232: useful low-elevation/AERONET context, but reviewed public target archive did not surface s2.

No fallback is admitted yet.

A fallback may replace Izaña only because Izaña fails a **pre-value source-admission prerequisite**. It may not be chosen because opened Izaña residuals look unfavorable.

## Current frozen model-form boundary

The current Level-B v3 real-sky test keeps exactly the model that exists:

- runtime axes: Sun depression, target altitude, relative solar azimuth, observer elevation, AOD550;
- AFGLUS;
- albedo 0.15;
- `crs`;
- `atlas_plus_modtran`;
- `aerosol_default`;
- spherical 1D;
- 380–780 nm.

Water vapor, ozone, local albedo, pressure, and detailed aerosol profile are not hidden post-hoc fitting axes. External measurements may be retained as diagnostics. If they explain failure, that failure is preserved and a new model generation requires a new untouched holdout.

## Remaining true blockers before target opening

The remaining work is now source/product specific:

1. prove the exact Pandora209s2 independently traceable absolute sky-radiance calibration/validity chain; for the three-channel lane also bind s1;
2. bind current type-2 uncertainty coverage/covariance, common absolute-scale uncertainty, and calibrated wavelength/filter validity;
3. bind exact current archive/API mapping for time, duration, type, routine, filterwheel and pointing; resolve true per-spectrometer pointing and the exact conversion of relative modes;
4. for the full lane, prove authoritative s1/s2 pairing and directional compatibility;
5. instantiate the already-frozen complete metadata universe, execute the frozen AOD/cloud/support filters, and hash all eligible/rejected classifications;
6. bind Pandora209 uncertainty semantics to the already-frozen propagation dispatch;
7. instantiate the already-frozen exact-object opening manifest;
8. separately review/authorize that exact manifest hash.

If s2 is independently valid over 470–700 nm before the full dual-spectrometer questions are resolved, the Johnson-V-only lane can proceed without s1 pairing.

## Claim scope

Izaña is near the upper end of the current 0–2500 m elevation domain. Even a strict three-channel Izaña PASS is source-scoped/high-elevation evidence, not by itself validation of elevation dependence across the entire domain.

## Hard boundaries

This package still authorizes none of the following:

- PGN target `/v1/download` for validation;
- opening selected `LEVEL1.DATA` values;
- opening selected `LEVEL1.UNCERTAINTY` or `LEVEL1.UNCERTAINTY.INSTRUMENT` values;
- deriving target photopic/scotopic/Johnson-V before exact-object authorization;
- MYSTIC/scientific execution or a new ordinal;
- ASIV rerun/retry/resume;
- retuning Level-B or ASIV;
- fitting AOD, aerosol family, background, pointing, pairing, stitch, source selection, or thresholds to target radiance;
- probability/confidence semantics for the five aerosol scenarios;
- production/UI/default activation;
- claiming human first-seeing validation.

## Next safe transition

Wait only for the remaining Pandora209/current-product metadata facts; do not invent additional scientific thresholds. Once those facts are bound, instantiate the already-frozen metadata universe and exact-object manifest, review their hashes, and create a separate opening authorization. Only then may the protected target arrays be opened once and evaluated under the frozen terminal rules.
