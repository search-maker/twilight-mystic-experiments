# Level-B zenith + total-sky expansion v1

Status: REVIEW / PREREGISTRATION ONLY. No scientific execution, surrogate support expansion, production promotion, or claim of empirical validation is authorized by this file.

## 1. Existing scientific boundary

The existing Level-B v3 solar-twilight surrogate remains immutable. Its validated physical design box ends at target altitude 80 deg and it represents clear-sky solar twilight only. The direct MYSTIC infrastructure is capable of zenith viewing, so 80 deg is a surrogate training/validation boundary rather than a radiative-transfer solver boundary.

A simple change from 80 to 90 is forbidden. It would silently extrapolate the frozen v3 surrogate and would retain a coordinate singularity: relative azimuth is undefined at exact zenith while the current v3 representation contains explicit relative-azimuth terms.

## 2. Zenith-safe representation for a future model

For target altitude h and relative azimuth phi in [0,180] deg, represent sky direction by

- vertical = sin(h)
- sunwardHorizontal = cos(h) cos(phi)
- crossSolarHorizontal = cos(h) sin(phi)

At h=90 deg both horizontal coordinates are exactly zero for every phi. Therefore exact zenith is one physical direction and the representation becomes azimuth-invariant by construction. The same coordinates approach that limit continuously as h -> 90 deg.

The future surrogate may add other physical/state variables, but it must not contain any angular feature that remains azimuth-dependent when h=90 deg.

## 3. Computational expansion protocol

The old 5..80 deg v3 package, coefficients, support coordinates, hashes, and PASS evidence remain unchanged.

A new separately identified candidate must be trained/validated using the existing admissible MYSTIC evidence plus fresh zenith-extension calculations. Fresh extension anchors should cover at least h = 82.5, 85, 87.5, and 90 deg across representative solar depression, AOD550, observer elevation, and relative-azimuth conditions. Exact h=90 cases use one canonical relative azimuth in the fit because azimuth is physically undefined there.

Before fitting, reserve independent 80..90 deg holdouts that are not used for model selection, hyperparameter choice, support-radius choice, or correction. Acceptance must include:

1. channel residual gates against fresh direct MYSTIC;
2. continuity across the old/new 80 deg boundary;
3. explicit exact-zenith azimuth-invariance checks;
4. near-zenith convergence checks (azimuthal spread -> 0 as h -> 90 deg);
5. no regression of the previously validated 5..80 deg region beyond a frozen tolerance;
6. explicit support geometry that fails closed outside computational evidence.

No application support may be enlarged to 90 deg before this new candidate passes its frozen computational validation.

## 4. Total-sky component contract

Total sky must be formed in linear physical radiance/luminance channels, never by adding magnitudes or SQM values:

L_total(lambda, direction, time) =
    L_solar_twilight
  + L_lunar_scattered
  + L_natural_night
  + L_artificial_skyglow.

Every component must report its own support, uncertainty, provenance, and atmosphere/source identity. A total-sky consumer must fail closed when a component declared required for that use case is missing or unsupported. Solar-only output must never be labeled complete physical total sky.

### 4.1 Solar twilight

Keep the current Level-B solar-twilight provider as a separate component. Do not refit it merely to absorb missing moon, airglow, zodiacal, stellar, or artificial backgrounds.

### 4.2 Lunar scattered light

A lunar provider requires, at minimum:

- Moon topocentric altitude/azimuth and target-Moon angular separation;
- lunar phase/phase angle and Earth-Moon/Sun-Moon distance effects as required by the adopted extraterrestrial lunar spectral-irradiance model;
- a documented lunar spectral source model with immutable source/version/hash provenance;
- the same admitted atmospheric state used for the solar and stellar paths when atmospheric scattering is evaluated;
- direct MYSTIC/libRadtran scattering calculations or a surrogate independently validated against such calculations;
- separate support and uncertainty; no tuning to the protected Taylor residuals before a frozen validation protocol.

A solar-source radiative-transfer engine may be driven by an externally specified lunar extraterrestrial spectrum only after the source normalization and geometry convention are independently verified. A successful solver run by itself is not lunar-model validation.

### 4.3 Natural night background

Treat physically distinct natural sources explicitly. Candidate terms include airglow, zodiacal light, integrated starlight/Milky Way, and other material diffuse extraterrestrial/atmospheric components. These are not produced automatically by a solar-twilight MYSTIC run.

The first implementation may use an externally sourced directional spectral sky model if its provenance, wavelength/angular domain, units, and uncertainty are frozen. Do not hide natural-night terms in an empirical constant floor when validating twilight shape.

### 4.4 Artificial skyglow

Artificial skyglow is site-, direction-, spectrum-, atmosphere-, and time-dependent. A production-quality provider must therefore be explicitly local/directional. Acceptable future routes include a physically propagated ground-emission inventory or an empirically calibrated directional provider. A single global SQM floor is not a validated physical artificial-light model.

## 5. Validation order

1. Software-only contracts and fail-closed composition.
2. Fresh MYSTIC zenith-extension computational campaign and independent holdouts.
3. Lunar source-model verification, direct-MYSTIC reference campaign, and independent computational validation.
4. Natural-night component source admission and cross-checks.
5. Artificial-skyglow source admission/calibration.
6. Joint total-sky validation against real measured sky with all required components active.
7. Only after the above: reassess human first-seeing timing; do not use human-event residuals to silently compensate for sky-physics errors.

## 6. Taylor Ann Arbor implication

Taylor late rows must remain secondary/descriptive for an absolute total-sky claim until the lunar and other materially required backgrounds are admitted under a frozen protocol. The nearly full Moon makes using solar-only late-twilight predictions as total-sky truth scientifically unsafe.

## 7. Governance

This plan does not allocate an ordinal, seeds, protected holdouts, or execution authorization. Any new direct-MYSTIC campaign must use the repository's existing one-purpose authorization, exact manifest, duplicate-run guard, isolated execution, aggregation, and independent audit machinery. Scientific runs must not be dispatched from this review branch without a separate reviewed authorization transition.
