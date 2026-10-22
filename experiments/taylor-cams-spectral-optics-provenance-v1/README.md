# Taylor CAMS spectral optics provenance v1

Status: **retrieval/provenance review only**. This experiment must not read Taylor SQM observations or residuals, must not execute MYSTIC/libRadtran, and must not choose aerosol optical properties according to agreement with Taylor.

## Purpose

The already-open Taylor broadband closure showed that replacing only the default aerosol vertical distribution with an independently retrieved CAMS 532-nm extinction shape materially improves the late-twilight comparison while leaving aerosol spectral SSA/phase-function properties on the frozen `aerosol_default` family. The next precision step is therefore to freeze the same-cycle CAMS spectral aerosol information independently of Taylor before any new radiative-transfer comparison.

## Fixed site and time

- Site: Ann Arbor, Michigan, 42.256 N, 83.709 W.
- Observation interval of interest: 2025-08-08 00:30–01:30 UTC.
- CAMS base forecast cycle: **2025-08-08 00Z**.
- Temporal interpolation must be determined only from forecast lead times and observation timestamp; no interpolation rule may depend on Taylor residuals.

## Retrieval targets

Retrieve, where the CAMS Global Atmospheric Composition Forecasts product exposes them for the same forecast cycle:

1. total aerosol optical depth at available solar/visible wavelengths bracketing the original-SQM response;
2. total absorption aerosol optical depth at available wavelengths, sufficient to derive column-effective SSA as `1 - AAOD/AOD` when both quantities refer to the same wavelength/product definition;
3. total aerosol asymmetry factor at available wavelengths, if exposed by the product;
4. aerosol extinction coefficient vertical profiles at 532 nm and any additional available wavelengths;
5. the model-level pressure/geopotential information required to bind extinction profiles to physical altitude consistently.

Exact dataset variable names and availability must be recorded from the retrieval API response/documentation before any downstream interpretation. Missing variables are a result, not a reason to substitute a favorable external value.

## Frozen analysis questions

Before looking at any Taylor residual after a future solver run, answer:

- How different is same-cycle CAMS AOD550 from the already-frozen Taylor-v1 AOD path?
- What is the spectral AOD slope across the SQM-sensitive band?
- What column-effective SSA values follow from same-cycle AOD/AAOD at available wavelengths?
- Is a wavelength-resolved asymmetry factor directly available? If not, state that limitation explicitly.
- Do extinction-profile shapes differ materially across available extinction-profile wavelengths, or is only the 532-nm vertical shape directly retrievable?

## Scientific boundary

This provenance freeze does **not** establish that column-effective SSA or g is vertically uniform. If a later solver experiment applies a column-effective optical property to all layers, that must be labeled an explicit approximation and compared against alternatives where technically possible.

Likewise, an asymmetry parameter is not a complete phase function. Existing AOPS/OPAC work already shows that `g` effects are geometry-dependent and that richer angular scattering can matter. Therefore a future Taylor rerun should treat CAMS spectral SSA/g as an incremental physical refinement, not as full aerosol-microphysics closure.

## No-fitting rule

No CAMS variable, wavelength subset, forecast cycle, spatial interpolation, vertical smoothing, SSA/g construction, SQM zero-point, or AOD may be selected because it minimizes Taylor residuals. Any alternative must be motivated and frozen independently first.

## Next gate

Only after this retrieval/provenance artifact is reviewed and frozen may a separate preregistered Taylor MYSTIC experiment use the retrieved values and compare against Taylor. That future experiment must report the baseline CAMS-vertical result and every spectral-optics variant side by side; it may not silently replace the baseline.
