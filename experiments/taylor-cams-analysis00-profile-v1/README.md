# Taylor CAMS 00Z analysis / 03Z forecast profile v1

Status: retrieval-only atmospheric provenance diagnostic. It does **not** read Taylor SQM values or residuals and does **not** execute MYSTIC/libRadtran.

## Scientific question

The Taylor-v1 total AOD has now been independently confirmed against the direct ADS CAMS 2025-08-08 00Z forecast cycle. However, the model-level `aerosol_extinction_coefficient_532nm` forecast field at lead 0 is all zero, while lead 3 is nonzero. CAMS documentation allows an API `analysis`, lead 0 retrieval.

Retrieve the 2025-08-08 00Z **analysis** extinction profile and the same-cycle 00Z **forecast lead 3 / valid 03Z** profile, using the same exact Ann Arbor interpolation and ECMWF 137-level height reconstruction for both. Retrieve matching direct AOD532/AOD550 for each endpoint and compare integrated extinction with direct AOD532.

## Frozen use boundary

If both endpoint profiles are valid and internally consistent, they may later define a **normalized vertical-shape interpolation** for Taylor rows 23–25. A later MYSTIC shape-only sensitivity must keep each Taylor-v1 row's already-frozen AOD550, geometry, surface pressure, aerosol optical-property family, spectral range, and original-SQM angular/spectral response unchanged.

This retrieval does not authorize choosing a new total AOD, tuning to Taylor residuals, changing F/tau/Level-B, or treating CAMS extinction532 as a full wavelength-dependent aerosol optical model.
