# Taylor CAMS same-cycle forecast00/forecast03 vertical profile v2

Status: **retrieval/reconstruction only; no Taylor SQM residuals and no libRadtran/MYSTIC execution.**

This is a new identity after PR #505 failed closed because the ADS `type=analysis` product returned no 532-nm aerosol-extinction messages. It does not rescue or reinterpret #505.

## Frozen source identity

### Aerosol-extinction bytes

Use only the already-existing same-cycle CAMS forecast artifact that was retrieved before this v2 result:

- artifact ID: `9633131426`
- artifact ZIP SHA-256: `e3341e1391de71ea85591ec92caf9552b2729b924425523abedc98608077bb84`
- file: `cams_2025-08-08_00Z_lead0-3_aerext532_geopotential_ml1-137.grib`
- dataset/cycle: CAMS Global Atmospheric Composition forecast, base `2025-08-08 00Z`, lead hours `0` and `3`
- known structural evidence before this v2: 274 `aerext532` records = 137 levels x 2 leads, units `m**-1`.

The two geopotential carrier messages in that artifact are not used to infer full-level heights.

### Direct column AOD evidence

Use only the independent same-cycle AOD cross-check artifact:

- run: `33040267228`
- artifact ID: `9633609512`
- artifact ZIP SHA-256: `79a430bd0a0d09ad81daa25f1271487f233dbc1a519a284b3c48bbb1ee8eb061`
- exact Ann Arbor bilinear values already established independently:
  - lead 0: AOD532 `0.3379003423329441`, AOD550 `0.32390820667147624`
  - lead 3: AOD532 `0.2912631035534665`, AOD550 `0.27895676622763277`.

These AOD values are used only as an internal profile-integral sanity check. This v2 does not revise Taylor-v1 AOD.

## Frozen thermodynamic reconstruction

Retrieve from the same CAMS forecast cycle, base `2025-08-08 00Z`, lead hours `0` and `3`, model levels `1..137`:

- temperature;
- specific humidity;
- geopotential;
- logarithm of surface pressure.

Use GRIB hybrid `pv` A/B coefficients plus the ECMWF hydrostatic model-level algorithm to reconstruct all 137 full-level geopotential heights. Bilinearly sample the four 0.4-degree native nodes around Ann Arbor (`42.256 N`, `83.709 W`) consistently for extinction and thermodynamic fields.

For each lead, anchor height above the model surface to the observer site elevation 262 m:

`siteAnchoredAltitude = 262 m + (fullLevelGeopotentialHeight - nativeSurfaceGeopotentialHeight)`.

No Taylor brightness value is read in this reconstruction.

## Pre-result acceptance gate

Each endpoint (`forecast00`, `forecast03`) must independently satisfy all of:

1. exactly 137 extinction levels, with level universe `1..137`;
2. exactly 137 temperature levels and 137 specific-humidity levels;
3. finite nonnegative extinction values with at least one strictly positive level;
4. finite strictly increasing reconstructed full-level heights after sorting;
5. finite positive surface pressure and direct AOD532;
6. integrated 532-nm extinction column consistent with the independently frozen direct CAMS AOD532:
   `0.95 <= integratedTau532 / directAOD532 <= 1.05`.

If either endpoint fails, v2 fails closed. No tolerance widening, smoothing, alternate cycle, alternate endpoint, layer deletion, or profile rescaling is permitted after the result is opened.

## Output

If the gate passes, preserve:

- all 274 site-sampled 137-level endpoint rows with extinction, height, pressure, T and q;
- endpoint AOD532/AOD550 provenance;
- integrated tau532 and ratio to direct AOD532;
- peak extinction and height;
- tau fractions below 0.5, 1, 2, 3, 5 and 10 km AGL;
- exact source and generated-file hashes.

A PASS only makes the profile eligible for a separately frozen vertical-shape MYSTIC diagnostic. It does not authorize MYSTIC execution, Taylor residual scoring, atmosphere replacement, Level-B change, F/tau change, production promotion, or human first-seeing claims.
