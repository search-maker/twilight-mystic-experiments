# Taylor Ann Arbor original-SQM direct-MYSTIC validation v1

This is the preregistered scientific execution package for Aster G. Taylor's 2025-08-07 Ann Arbor dataset 1.

## Frozen before solver residuals

- geometry: reconstructed geometric topocentric Sun, 32 timestamps including the extra 20:47 EDT point;
- primary solar subset: rows 1-25, defined only by geometric solar-center altitude > -6 deg;
- published-normal-range submetric: rows 8-25 (Unihedron describes roughly 7-23 mag/arcsec2 as the normal accurate range); this does not replace the 25-row primary;
- atmosphere: AERONET Windsor_B/Windsor_M yielded no qualifying V3 Level-2 rows, so the preregistered fallback is CAMS Global; midpoint AOD550=0.32, per-observation central-cell series 0.33 -> 0.31, local spatial/temporal sigma=0.04923;
- surface pressure: KARB ASOS, about 1020 hPa, time-interpolated/extrapolated from the two bracketing reports;
- AOD sensitivity: 0.05, 0.10, 0.15, 0.20, 0.30, 0.40;
- MYSTIC: direct libRadtran 2.0.6-MYSTIC ALIS, `mc_spherical 1D`, AFGLUS, aerosol_default with frozen AOD, albedo 0.15, day-of-year 220, no Level-B surrogate;
- original SQM forward operator: 8 Gauss-Legendre radial nodes in mu times 8 azimuth nodes = 64 direct MYSTIC directions per timestamp; angular response digitization integrates to 1.534445 sr versus Unihedron's 1.532 sr official effective solid angle;
- spectral operator: published combined SQM response digitization plus manufacturer HOYA CM-500 transmission and Cinzano incidence-angle correction (n=1.55);
- zero point: synthetic Vega system from CALSPEC `alpha_lyr_stis_011.fits`, with the instrument's published factory absolute calibration uncertainty +/-0.10 mag propagated as a common systematic;
- response-digitization systematic allowance: +/-0.05 mag;
- empirical observational random term: 0.062146 mag from Taylor dataset-1 vs dataset-2 repeatability;
- timing: +/-30 s propagated from the untouched MYSTIC curve;
- late rows 26-32 are descriptive only because no validated lunar-scattered-light/background model is included.

No AOD, magnitude offset, spectral response, subset boundary, or acceptance threshold may be changed after solver results. The primary absolute comparison has no fitted offset. One constant offset is calculated only as a labeled shape diagnostic.

The workflow is intentionally `pull_request: opened` only and refuses `GITHUB_RUN_ATTEMPT != 1`, so the scientific identity is not silently rerun.
