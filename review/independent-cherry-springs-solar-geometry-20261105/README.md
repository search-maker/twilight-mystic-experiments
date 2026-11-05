# Result-blind published-solar-geometry source audit (2026-11-05)

**Classification: MATERIAL GEOMETRY-METADATA INCONSISTENCY. No model validation.**

**Sources.** Spitschan et al., Scientific Reports 6:26756 (2016), DOI https://doi.org/10.1038/srep26756, Table 1 Rural entries. Mandatory 2017 erratum DOI https://doi.org/10.1038/srep46930: the originally published Supplementary Tables S2/S3 (rural/city spectral data) were INCOMPLETE; corrected files must be authenticated. No measured spectral bytes have been accessed in this audit.

Five Rural-row Table 1 published solar maximum extrema at the first E (evening) or last M (morning) record are compared to true geometric solar altitudes independently computed using pyswisseph 2.10.03 Moshier and an UNVERIFIED local EDT time interpretation. Cherry Springs location approx 41.6646 N, 77.8125 W, 710 m; Philadelphia location approx 39.9526 N, 75.1652 W, 10 m. These are representative city/site coordinates, not verified original instrument GPS.

| Rural date/time (candidate EDT) | Published Table 1 Sun max | Recomputed Philadelphia | Recomputed Cherry Springs |
|---|---:|---:|---:|
| 2014-06-30 18:52:55 (E start) | +16.73° | +16.7115° | +19.0983° |
| 2014-07-01 08:08:23 (M end) | +26.45° | +26.4730° | +24.7706° |
| 2014-07-02 19:38:19 (E start) | +8.52° | +8.5031° | +11.0022° |
| 2014-07-12 19:09:09 (E start) | +13.34° | +13.3274° | +15.7350° |
| 2014-07-14 12:35:07 (E start) | +70.54° | +70.4777° | +68.0848° |

**Five-case RMSE:** Philadelphia 0.032227°; Cherry Springs 2.295828°. Max absolute error: Philadelphia 0.062273°; Cherry Springs 2.482166°. Strong multi-date match to the Philadelphia ephemeris shows a source-annotation/site-geometry discrepancy, NOT proof of where measurements physically occurred or of the original pipeline's cause. Independently verify source instrument GPS, original clocks/timezones, sample-level solar-altitude metadata, and the authors' elevation-calculation convention before using these rural observations as site-accurate twilight evidence.

The rural 2014-07-01 morning sequence has 404 measured spectra per Table 1 and is described as Moon-below-horizon (published Moon alt −41.19° to −16.94°, solar alt −26.94° to +26.45°). Under local EDT, our Cherry Springs Sun extrema are −25.228° / +24.771°, lunar extrema −38.835° / −17.029°. If clocks are interpreted naively as UTC, the Sun is still below horizon at the printed 08:08:23 endpoint and Moon is initially above horizon: incompatible with published descriptions. EDT is favored but NOT authenticated.

**Scientific limits.** Observations are cosine-weighted hemispheric DOWNWELLING SPECTRAL IRRADIANCE (W/m2/nm), NOT directional SKY RADIANCE (W/m2/sr/nm) or visually measured first-star events. Comparison would require a scientifically justified hemisphere angular integral including presently unsupported altitudes; no numeric model validation can be inferred. Corrected full S2 spectral custody, original time metadata, sky transparency/clouds and matched atmosphere are required before any unblinded quantitative comparison. Never retune model to published values or use this data as a protected calibration set. The model remains UNSUPPORTED for precise first-star times at solar depression (10.5,16].

**Reproduce:** python -m py_compile review/independent-cherry-springs-solar-geometry-20261105/spitschan_rural_table1_solar_geometry_audit.py ; python review/independent-cherry-springs-solar-geometry-20261105/spitschan_rural_table1_solar_geometry_audit.py. Local compile and five-case assertions PASS. Exact Git source blob 87e1f0dfc08f6789512186bf9cda60653d53fac3; local script SHA256 71221b0f1018d2c31ad436194715c4977276c3d3a572bd435508bc4af68d9192. No MYSTIC, ordinal/seed, fit, protected, Actions or production action.
