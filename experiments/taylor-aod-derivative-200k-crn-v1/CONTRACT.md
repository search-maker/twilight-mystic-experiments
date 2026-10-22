# Taylor late-primary AOD-derivative 200k CRN audit v1

Status: **review-only; no solver execution authorized by this branch.**

## Purpose

The original Taylor-v1 analysis propagated local CAMS AOD uncertainty through a broadband MYSTIC AOD sweep. Subsequent empirical work established that the broadband ALIS `mc.rad.std.spc` propagation is not a calibrated between-seed uncertainty estimator, and six-seed 200k default-atmosphere means materially changed the late-primary central residuals.

The legacy local AOD derivatives near rows 23-25 therefore require independent numerical reconvergence before they can be used in a renewed Taylor uncertainty budget.

This audit asks only:

> Holding every Taylor-v1 input fixed except total aerosol optical depth, what is the broadband original-SQM magnitude slope between AOD550 = 0.30 and 0.40 at rows 23, 24, and 25, and how stable is that slope across independent common-random-number seed pairs at 200k photons/ray?

No Taylor observed-minus-model residual is read or used for model selection.

## Why AOD 0.30 and 0.40 are frozen

These are not newly chosen favorable perturbations. They are two points from the original preregistered Taylor-v1 AOD sensitivity universe `[0.05, 0.10, 0.15, 0.20, 0.30, 0.40]`. The legacy analyzer used the adjacent sweep points surrounding the frozen late-primary AOD to form its local finite-difference derivative. Reusing exactly 0.30 and 0.40 isolates numerical convergence of the already-declared derivative definition.

The finite-difference magnitude derivative can be computed without any Vega zero point:

`D = [-2.5 log10(Q_0.40 / Q_0.30)] / 0.10` mag per AOD.

## Frozen science universe

Rows: **23, 24, 25** only.

AOD550 conditions: **0.30 and 0.40 only**.

Six independent paired CRN replicates with new seed namespaces:
- replicate 1: `967000000 + row*1000 + rayIndex`;
- replicate 2: `968000000 + row*1000 + rayIndex`;
- replicate 3: `969000000 + row*1000 + rayIndex`;
- replicate 4: `970000000 + row*1000 + rayIndex`;
- replicate 5: `971000000 + row*1000 + rayIndex`;
- replicate 6: `972000000 + row*1000 + rayIndex`.

Within each row/replicate/ray pair, **the same seed is used for AOD 0.30 and AOD 0.40**. Across replicate namespaces all ray seeds are unique and disjoint from the consumed 955-966M Taylor broadband namespaces.

Per condition:
- exact 64-ray Taylor-v1 original-SQM quadrature;
- 200,000 photons/ray;
- exact Taylor-v1 `wavelength 380 780` and `mc_spectral_is 550.0` broadband calculation;
- exact AFGLUS/runtime, row geometry, pressure, albedo, aerosol-default optical family, site elevation treatment, and response tables;
- no `aerosol_file tau`, HRRR, CAMS vertical-profile substitution, or other atmosphere change.

If separately authorized, execution budget is:

`3 rows x 6 replicates x 64 rays x 2 AOD conditions = 2304 solver calls`

or **460.8M configured photon histories**.

No retry/rerun/resume may reuse this science identity after any solver invocation.

## Binding dry preflight

Before solver execution:

1. verify exact reviewed Taylor-v1 renderer/source and exact reviewed libRadtran/MYSTIC runtime hashes;
2. verify rows 23-25, exactly six replicate namespaces 967-972M, and exactly 1152 unique paired ray seeds;
3. prove all new seeds are disjoint from consumed 955-966M namespaces;
4. dry-render all 1152 AOD pairs and prove that within each pair the resolved inputs differ **only** at the line `aerosol_set_tau_at_wvl 550 ...` plus condition `mc_basename`; `mc_photons` and `mc_randomseed` must be identical within the pair;
5. prove there is exactly one `aerosol_default` line, exactly one `aerosol_set_tau_at_wvl 550` line, and no `aerosol_file tau` line;
6. verify the two AOD values are exactly 0.30 and 0.40 for every pair.

Any preflight failure stops the identity.

## Frozen analysis

For each row and replicate compute:

- aggregate original-SQM `Q_0.30` and `Q_0.40`;
- exact paired magnitude difference `deltaMag_0.40_minus_0.30 = -2.5 log10(Q_0.40 / Q_0.30)`;
- finite-difference derivative `D = deltaMag / 0.10` mag/AOD.

Across the six replicates per row report:

- six derivative values;
- sample mean, sample SD, SE, min/max;
- six `deltaMag` values and their sample SD;
- empirical derivative signal-to-between-seed-SD (`abs(mean D)/SD(D)`) descriptively;
- derivative-implied local AOD random uncertainty using the **already-frozen** Taylor-v1 `AOD_SIGMA = 0.049232200070782176`: `abs(mean D) * AOD_SIGMA`;
- numerical SE contribution to that propagated AOD sigma: `SD(D)/sqrt(6) * AOD_SIGMA`.

At ray level, report the six paired log-ratio derivatives and summarize cross-seed SDs to identify whether aggregate instability is broad or dominated by a few rays.

For orientation only, compare the new derivative with the immutable legacy Taylor-v1 derivative recorded in the original analysis artifact. The legacy value is not a fitting target and no acceptance tolerance is defined around it.

## Interpretation boundary

This is a numerical convergence audit of a previously declared AOD finite-difference derivative. It does not fit AOD to Taylor observations, change the frozen row AOD, validate an aerosol vertical profile, alter Level-B/F/tau, or authorize production/human-model changes.

A result that changes the legacy derivative would mean the old AOD uncertainty contribution was numerically unstable; it would not by itself identify the correct physical atmosphere.
