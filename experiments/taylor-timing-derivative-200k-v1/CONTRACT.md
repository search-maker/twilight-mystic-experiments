# Taylor late-primary timing-derivative 200k reconvergence v1

Status: **review-only; no solver execution authorized by this branch.**

## Purpose

Taylor-v1 propagated the stated +/-30 s observation-time uncertainty through the model curve using `numpy.gradient(model_mag, timestamp)` over all 32 rows. Later work established that the legacy broadband ALIS central values and `mc.rad.std.spc` uncertainty were not numerically converged at the late-primary rows.

Rows 23-25 now have immutable six-seed, 200,000-photon default-atmosphere broadband results. To reconstruct the **same Taylor-v1 gradient definition** at rows 23-25 without changing the method, the only missing neighboring central values are row 22 and row 26:

- derivative at row23 uses rows22 and24;
- derivative at row24 uses rows23 and25;
- derivative at row25 uses rows24 and26.

This audit therefore adds only rows22 and26 at the same 200k/six-seed numerical standard, then re-evaluates the legacy time derivative exactly.

No Taylor residual is used to select rows, seeds, or settings.

## Frozen new solver universe

New rows: **22 and 26 only**.

Six new independent default-only replicates:
- replicate 1: `973000000 + row*1000 + rayIndex`;
- replicate 2: `974000000 + row*1000 + rayIndex`;
- replicate 3: `975000000 + row*1000 + rayIndex`;
- replicate 4: `976000000 + row*1000 + rayIndex`;
- replicate 5: `977000000 + row*1000 + rayIndex`;
- replicate 6: `978000000 + row*1000 + rayIndex`.

All new seeds are disjoint from consumed Taylor broadband namespaces 955-972M.

Per row/replicate:
- default Taylor-v1 atmosphere only;
- exact frozen row AOD550, geometry, pressure, albedo, AFGLUS/runtime, aerosol-default family, observer elevation treatment;
- exact original-SQM 64-ray angular response;
- exact `wavelength 380 780` and `mc_spectral_is 550.0` broadband calculation;
- 200,000 photons/ray;
- no HRRR/CAMS vertical-profile substitution and no AOD perturbation.

If separately authorized: `2 rows x 6 replicates x 64 rays = 768 solver calls`, or **153.6M configured photon histories**.

No retry/rerun/resume may reuse the one-shot science identity after any solver invocation.

## Immutable existing 200k evidence

Rows 23-25 come only from the completed default-only 200k scaling run:
- run `33044289555`, attempt 1;
- analysis artifact `9635082283`;
- ZIP digest `sha256:62b938226602a0e97548ae291c2ce845f064210af9131dc3503e944cbe2601cb`;
- six independent replicates at 200k photons/ray.

The exact underlying row/replicate artifacts from that run may be downloaded by run/name identity for replicate-level derivative diagnostics. They must not be regenerated.

The original Taylor-v1 analysis recovery remains the immutable source for timestamps, observations, the original Vega/SQM zero point, and the legacy timing derivative:
- run `33016529095`;
- artifact `9624747631`;
- digest `sha256:242ad28f9a46fa2c90006ff728eeefb8e6c30b3ca583c4f044af4d48f8821dea`.

## Binding dry preflight

Before any new solver call:

1. verify exact reviewed Taylor-v1 renderer/source and exact reviewed libRadtran/MYSTIC runtime hashes;
2. verify new row universe exactly `[22, 26]`, six replicate namespaces 973-978M, exactly 768 unique new ray seeds, all disjoint from consumed 955-972M namespaces;
3. dry-render all 768 new cases and prove that, relative to the corresponding Taylor-v1 default render, the only intentionally changed runtime-identity lines are `mc_photons`, `mc_randomseed`, and `mc_basename`; every physical/model line must be unchanged;
4. prove there is no `aerosol_file tau` and no AOD override other than each row's already-frozen primary AOD.

Any failure stops the science identity.

## Frozen central analysis

Build a five-row sequence `[22,23,24,25,26]` using the **six-seed 200k mean Q** at every row.

Convert each mean Q to original-SQM magnitude using the exact Vega synthetic-SQM zero point already stored in the immutable Taylor-v1 analysis artifact. No new zero point is fit or fetched.

Use the original UTC timestamps and compute:

`dmdt = numpy.gradient(model_mag, unix_timestamp)`

on those five rows. Because rows23-25 are interior points, this reproduces the same local nonuniform-grid finite-difference formula Taylor-v1 used on the full 32-row sequence.

For rows23-25 report:
- six-seed-mean model magnitude;
- `dmag/dt` in mag/s and mag/min;
- renewed timing sigma `abs(dmag/dt) * 30 s`;
- legacy Taylor-v1 timing sigma;
- new-minus-legacy timing sigma.

## Frozen empirical numerical diagnostic

For each replicate index 1..6, construct one five-row realization using replicate `i` at rows22-26. The row seeds are independent even though replicate labels are aligned; alignment is only a deterministic way to create six independent multi-row realizations and introduces no common-random-number claim across time.

Apply the same `numpy.gradient` to each realization. Report the six derivative/timing-sigma values per target row, sample SD and SE across realizations.

This replicate diagnostic measures numerical variability of the derived timing term; it is not an observer timing uncertainty and is not added silently to the +/-30 s contract.

## Interpretation boundary

This audit reconverges only the existing Taylor-v1 **model time derivative** used to propagate the already-declared +/-30 s timestamp uncertainty. It does not change the timestamp uncertainty itself, fit Taylor observations, modify atmosphere/AOD, alter Level-B/F/tau, or authorize production/human-model changes.

A full Taylor statistical reclassification remains blocked until every uncertainty component used in that classification is placed on a mutually compatible numerical basis.