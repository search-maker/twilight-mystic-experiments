# Aerosol production domain v1

Status: **review-only domain freeze; no production or scientific authorization**.

This package separates two domains that must not be conflated after AOPS v1 and AFPF v1:

1. the **target operational computational domain** already validated for the exact Level-B v3 surrogate; and
2. the much smaller **direct AFPF aerosol evidence domain** on which all five aerosol scenarios were actually run.

The Level-B v3 package supports the physical box Sun depression 2.0–10.5 deg, target altitude 5–80 deg, relative azimuth 0–180 deg, observer elevation 0–2500 m, AOD550 0.05–0.40, and wavelengths 380–780 nm, subject to its frozen nearest-support-distance <= 0.60 rule. That computational support does **not** imply that the aerosol-family/phase-function scenario envelope has been validated throughout the same box.

AFPF ordinal 38 directly evaluated only 24 cells: four Sun depressions (2, 4, 6, 8 deg) x two AOD values (0.10, 0.30) x three viewing geometries, all at observer elevation 0 m. Those exact cells are classified `DIRECT_AEROSOL_EVIDENCE`.

Any point that passes the Level-B v3 computational support rule but is not one of those 24 cells is classified `AEROSOL_COVERAGE_GAP`. At such a point the future system may not silently interpolate the five-state aerosol envelope, copy the nearest AFPF cell, or present the baseline as if aerosol uncertainty were bounded. A baseline can only be reported with an explicit aerosol-uncertainty coverage-gap flag until a separately validated transport/interpolation layer exists.

Points outside the validated Level-B box or its support-distance rule are `BASE_MODEL_OOD` and must fail closed.

## Why this matters for ordinal 39

This review makes the next scientific target specific. Ordinal 39, if later preregistered and separately authorized, should not repeat AFPF v1. It must validate aerosol-scenario transport/interpolation into the coverage gaps that matter for the intended operational box. In particular, a frozen future design must include off-lattice viewing geometry, observer elevation above zero, AOD values beyond only 0.10/0.30, and Sun depressions beyond only 2/4/6/8 while staying inside the already validated computational domain.

The exact ordinal-39 matrix, interpolation method, acceptance thresholds, independent holdout points, seeds, authorization and dispatch are **not** frozen or allocated here. They must be preregistered before any new result is opened.

## Spectral boundary

AFPF full-spectrum output has an explicit numerical limitation at Sun depression 8 deg in cross-solar/opposite-solar cells. Scalar and Level-B rows were finite for all 24 cells, but the affected 8-deg full-spectrum scenario envelope may not be described as uniformly resolved. No epsilon substitution is allowed.

## Bound sources

- aerosol uncertainty policy v1;
- Level-B v3 computationally validated surrogate package;
- AFPF v1 frozen protocol;
- AFPF ordinal-38 verified results report.

No MYSTIC/uvspec execution, new artifact opening, scientific ordinal allocation, starsvisibility mutation, production correction, rerun, retry or resume is authorized by this package.
