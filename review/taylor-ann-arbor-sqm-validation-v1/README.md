# Taylor Ann Arbor SQM real-sky validation v1

## Purpose

Admit Aster G. Taylor's 2025-08-07 Ann Arbor original-SQM twilight series as an **untuned real-sky diagnostic validation case** for the existing libRadtran/MYSTIC radiance stack.

This admission does not fit MYSTIC, AOD, refraction, background, or SQM calibration to the observations. Taylor's measured values are frozen evidence. The primary direct-MYSTIC comparison remains closed until an independent atmosphere is frozen.

## Frozen observation reconstruction

- observer: Aster G. Taylor
- date: 2025-08-07 EDT
- site: 42.256 N, 83.709 W, 262 m
- instrument: original wide-angle Unihedron SQM, zenith-pointing
- dataset 1: 32 measurements
- reconstructed times: 20:30, 20:32, ..., 20:46, **20:47**, 20:48, 20:50, ..., 21:30 EDT
- individual timing uncertainty: about +/-30 s

The row/timestamp map was reconstructed by comparing every CSV `H` against independently computed topocentric solar geometry followed by the XEphem/PyEphem refraction algorithm. Reconstructed apparent altitude matches all 32 CSV H values with RMS 0.000381 deg and maximum absolute discrepancy 0.001028 deg.

Therefore the CSV H column is algorithmically consistent with PyEphem apparent/refracted `sun.alt`. Direct MYSTIC must instead use the separately reconstructed unrefracted geometric topocentric solar-center geometry.

## Independent repeatability

Dataset 1 and dataset 2 overlap over H = -7.9..+2.2 deg. Piecewise-linear interpolation on a 0.05-deg H grid gives RMS night-to-night difference **0.062146 mag/arcsec^2**.

## Koomen diagnostic

Taylor's public code passes PyEphem `sun.alt` directly into the Koomen interpolation. Reconstructing that route produces the large local raw-H residual feature, with maximum residual **1.46081 mag**.

Substituting geometric H is retained only as a diagnostic. It greatly changes the local feature and gives a whole-series shape scatter near the dataset's night-to-night repeatability after one reported constant offset. This is **not** yet called a Koomen correction: the recovered 1952 text defines H as solar altitude but does not explicitly establish apparent/refracted versus geometric/unrefracted convention.

## Original SQM boundary

The final comparison must integrate directional spectral MYSTIC radiance over the original wide-angle SQM angular and spectral response; a single zenith ray, a 60-deg top-hat, generic Johnson V, or generic photopic response is not the final instrument model.

Published instrument facts already established for the forward-model work include effective solid angle 1.532 sr, original wide field roughly 80 deg diameter / HWHM about 42 deg, TSL237S detector, and HOYA CM-500 filtering. The individual Taylor SQM unit's absolute zero point has not been recovered, so absolute synthetic SQM validation is not yet authorized. A later shape-only comparison may use at most one explicitly reported constant magnitude offset for the complete series; it may not vary with time, H, AOD, Moon, or subset.

## Moon and atmosphere

The Moon was already above the horizon and about 98% illuminated. Its disk remained well outside the main direct SQM cone, but lunar scattered light is not thereby zero and must be handled for late data.

Nearest identified AERONET site is Windsor_B, about 51.6 km away; KARB is the nearby surface station. A traceable historical AOD550 for the observation window has not yet been frozen. **No AOD may be selected from Taylor residuals.** After a primary independent atmosphere is frozen, the predeclared sensitivity set is AOD550 = 0.05, 0.10, 0.15, 0.20, 0.30, 0.40.

## Direct-MYSTIC transition

No Taylor MYSTIC result is fabricated in this admission commit. The next scientific transition is to:

1. recover/freeze independent AOD550 and surface meteorology;
2. freeze the original-SQM directional/spectral quadrature bytes;
3. preregister the Taylor direct-MYSTIC case universe, fresh seeds, photon budget, convergence rule and analysis before solver results exist;
4. execute attempt 1 through the current reviewed repository runtime;
5. integrate MYSTIC directional spectra through the SQM operator;
6. report untouched primary comparison first, then the predeclared AOD sensitivity and optional one-offset shape diagnostic;
7. keep lunar/artificial-background diagnostics separate from the solar-only claim.

The repository's recent elevated-site infrastructure smoke has demonstrated successful ALIS and VROOM MYSTIC solver exits; its VROOM structural parser issue is being repaired separately and its low-photon outputs are scientifically unusable. This Taylor admission does not overlap that recovery lane.

## Admitted files

- `AnnArbor.csv` — frozen Taylor source data used here
- `timestamp_mapping.csv` — explicit dataset-1 row/time audit, including the extra 20:47 point
- `measurement_summary.json` — source and dataset1-vs-dataset2 repeatability summary
- `validation_summary.json` — compact reconstruction/Koomen/Moon summary
- `validation_contract.review.json` — scientific role, guardrails and hashes for the admitted payload

Larger derived reconstruction tables, SQM response working tables, Moon-FOV table, plots and comparison tables are intentionally not part of this first admission commit; they remain working evidence until separately published byte-for-byte. No direct Taylor MYSTIC output is present.

## Scientific classification

**REAL-SKY-DATA-ADMITTED / GEOMETRY-RECONSTRUCTED / DIRECT-MYSTIC-NOT-YET-EXECUTED**

This dataset may test the frozen model. It may not tune the model, choose AOD, invent an SQM zero point, or change acceptance rules after observing residuals.
