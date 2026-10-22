# Taylor Ann Arbor atmosphere freeze result

This blind atmosphere acquisition was frozen before any Taylor-vs-MYSTIC residual existed.

- AERONET V3 Level-2 direct-sun data: no qualifying rows from Windsor_B or Windsor_M under the preregistered <=75 km, +/-3 h rule.
- Fallback: CAMS Global Atmospheric Composition (`cams_global`), independently sampled at Ann Arbor and four neighboring 0.4-degree cells.
- Frozen primary midpoint AOD550: **0.32** at 2025-08-08 01:00 UTC.
- Spatial sample: center 0.32, east 0.32, north 0.36, south 0.30, west 0.30.
- Spatial standard deviation: 0.0244949 AOD.
- Central-window temporal standard deviation: 0.0427061 AOD.
- Combined local spatial/temporal sigma: **0.0492322 AOD**.
- Separate CAMS North-America model-error envelope: +/-49% (not treated as Gaussian 1-sigma), giving **0.1632..0.4768** around the 0.32 midpoint primary.
- Frozen sensitivity sweep: AOD550 = 0.05, 0.10, 0.15, 0.20, 0.30, 0.40.
- KARB surface observations bracket the SQM interval: 00:53 UTC 23.3 C / dewpoint 18.3 C / MSLP 1019.9 hPa / CLR; 01:53 UTC 21.7 C / dewpoint 18.3 C / MSLP 1020.4 hPa / CLR.

Primary scientific runs should use the already-frozen CAMS time series, not choose AOD from Taylor residuals. The external +/-49% CAMS envelope is retained separately from local spatial/temporal variation.

Provenance: GitHub Actions run 33014181859, artifact 9623780444, artifact digest `sha256:68a8346d3973d4b02e511d3843d669379661e86c21ef4976a33e5bf425f13454`.
