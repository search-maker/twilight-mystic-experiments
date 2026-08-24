# Aerosol scenario interpolation validation v1

Status: **review-only preregistration; no ordinal allocated; no solver execution authorized**.

This package freezes the first fresh validation of aerosol-scenario transport away from the exact AFPF ordinal-38 lattice. Ordinal 38 is training evidence only. The future holdout contains eight geometry-only selected, structurally fresh points. Every point is inside the frozen Level-B physical box and at normalized nearest-training distance 0.30-0.60; every point has observer elevation above zero, a Sun depression not equal to 2/4/6/8 degrees, and an AOD550 not equal to 0.10/0.30.

The proposed production form is not an absolute aerosol surrogate. It predicts four paired aerosol-vs-native log-contrast fields in each of the three integrated channels and applies them to the separately validated native/base radiance. One global interpolation specification is selected by leave-one-cell-out cross-validation on the already-open 24-cell AFPF training surface. Ordinal-39 outcomes may not influence candidate selection, model parameters, thresholds, holdout identities, or replacement points.

Because ordinal-38 aerosol training has only observer elevation 0 m, elevation is deliberately excluded from the fit. The fresh holdout tests the explicit zero-order elevation-invariance hypothesis at 312.5, 937.5, 1562.5, and 2187.5 m. Failure leaves aerosol production blocked and requires elevation-dependent aerosol training rather than post-hoc retuning on the opened holdout.

The future scientific envelope, if separately authorized, is 8 geometries x 5 aerosol states x 3 CRN replicates = 120 MYSTIC cases at 20M histories/case = 2.4B configured histories. No GitHub rerun/retry/resume is permitted.

A PASS is intentionally narrow: integrated photopic/scotopic/Johnson-V aerosol log-contrast transport and derived Level-B only. Full-spectrum aerosol interpolation remains unvalidated; all spectral unresolved-node diagnostics must be reported and no epsilon substitution is permitted. Production deployment, aerosol climatological weighting, real-sky validation, human first-seeing validation, and starsvisibility mutation remain closed.
