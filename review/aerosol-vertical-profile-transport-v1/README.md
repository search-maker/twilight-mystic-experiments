# Aerosol vertical-profile transport foundation v1

Status: **REVIEW-ONLY / SOLVER-FREE / NO SCIENTIFIC ORDINAL / NO PRODUCTION AUTHORIZATION**

## Purpose

Provide one reusable, deterministic mechanism for converting an **already independently supplied nonnegative vertical aerosol shape** onto a libRadtran atmosphere layer grid as normalized `aerosol_file tau` layer fractions.

This closes a software-mechanics gap only. It does not decide which physical profile is true, which source should be preferred, or how a fast Level-B model should parameterize vertical structure.

## Why this exists

Taylor HRRR vertical-shape work already demonstrated a technically valid pattern in `experiments/taylor-hrrr-vertical-sensitivity-v3/run_profile_row.py`:

1. validate a source vertical profile;
2. integrate it onto the exact site atmosphere layers;
3. normalize only the above-observer layer distribution;
4. write the layer optical-depth fractions using libRadtran's lower-bound `aerosol_file tau` convention;
5. keep total column AOD separate through `aerosol_set_tau_at_wvl`.

That implementation is Taylor/HRRR-specific. This foundation extracts only the generic transport mathematics and fail-closed behavior. It does **not** import HRRR smoke mass as a universal aerosol optical profile.

## Existing aerosol science that must not be duplicated

The project already completed:

- AOPS v1 / ordinal 37: SSA and scalar-g sensitivity;
- AFPF v1 / ordinal 38: realistic full phase-function / aerosol-family sensitivity;
- ASIV v1 / ordinal 39: fresh-holdout scalar and derived Level-B aerosol-scenario transport;
- starsvisibility PR #100: verified shadow-only five-state aerosol scenario-envelope integration.

Therefore this lane is **not** another SSA/g/phase/aerosol-family campaign and does not reopen those frozen results.

## Frozen software contract

`profile_transport.py`:

- requires a finite, strictly increasing source altitude grid;
- requires finite nonnegative profile values and rejects an all-zero profile;
- requires a finite, strictly increasing target layer-edge grid;
- uses piecewise-linear integration inside source support;
- requires the caller to state behavior below and above source support explicitly: `reject`, `zero`, or `edge`;
- does not silently extrapolate outside source support;
- clips naturally when the target grid begins at observer altitude and renormalizes only the transported above-observer column;
- returns layer fractions summing to one;
- does not accept, infer, fit, rescale, or choose total AOD;
- renders libRadtran `aerosol_file tau` with each layer fraction at the lower layer boundary and zero at the top boundary;
- records a deterministic SHA-256 fingerprint over source profile bytes-as-values plus caller-supplied source identity.

The normalization tolerance (`1e-12`) is purely a numerical invariant on fractions that mathematically sum to one. It is not a scientific profile/AOD consistency tolerance.

## Explicit non-goals

This foundation does not:

- select a profile from Taylor/Jerusalem residuals;
- define a generic boundary-layer/elevated-aerosol profile family;
- convert HRRR smoke mass to calibrated extinction;
- convert lidar backscatter to extinction without an independently justified retrieval;
- derive aerosol family from AOD;
- choose SSA, phase function, or spectral law;
- choose or alter column AOD;
- execute MYSTIC/libRadtran;
- change Level-B;
- authorize production or empirical-real-sky claims.

## Next scientific gate

After this transport mechanism is reviewed, a **separate preregistered scientific design** may define a small set of vertical optical-depth shapes from independent physical sources. The profile universe, source provenance, observer clipping, altitude support, spectral assumptions, geometries, seeds, photon counts and acceptance metrics must be frozen before any result is opened.

Taylor/Jerusalem residuals must not be used to select those profiles or acceptance thresholds.

The scientific question should be narrowly stated:

> At fixed total column AOD and fixed aerosol optical-property family, how much does independently specified normalized aerosol vertical optical-depth shape change twilight sky radiance and derived Level-B quantities across the supported geometry domain?

Only after that sensitivity is quantified should the project decide whether vertical structure warrants a new Level-B dimension, scenario envelope, correction basis, or refusal/uncertainty treatment.
