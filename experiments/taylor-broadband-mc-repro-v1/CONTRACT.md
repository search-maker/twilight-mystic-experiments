# Taylor broadband Monte Carlo reproducibility audit v1

Status: **review-only; no solver execution authorized by this branch.**

## Purpose

The one-shot HRRR broadband science recovery (PR #515, run `33042326594`) completed all six row/replicate jobs but its preregistered fresh-default gate failed 6/6. The failure is numerical/reproducibility evidence, not an atmosphere result.

This audit asks a narrower question before any further Taylor atmosphere interpretation:

> At the frozen Taylor-v1 broadband configuration (`380-780 nm` with `mc_spectral_is 550.0`), what is the empirical **between-seed** variability of (a) the absolute original-SQM broadband response `Q`, and (b) the paired HRRR-shape/default magnitude contrast, when the physical inputs are unchanged?

The existing per-spectrum `mc.rad.std.spc` propagated errors are retained only as diagnostics. They are not assumed to represent between-seed broadband uncertainty.

## Frozen prior evidence

- Taylor-v1 source SHA: `7231bd873859cc8c36fe6749985e0ece193b5de7`.
- Reviewed broadband package parent: `75035d9ea316af574b2fac50f52c43c633b2bdbc`.
- Completed broadband recovery head: `31ea5065b530dd15a9d8b054cce338757c29e9f3`.
- Completed broadband recovery run: `33042326594`.
- Existing seed namespaces retained as immutable evidence only:
  - replicate 1: `955000000 + row*1000 + rayIndex`;
  - replicate 2: `956000000 + row*1000 + rayIndex`.
- Exact existing case artifacts:
  - row23 rep1 `9634362087`, digest `sha256:09425bbac571a8083c30378af48bea446600b7ad6457919fa7515c80ac2f7603`;
  - row23 rep2 `9634364324`, digest `sha256:4f06e87fb39b3f80ed3cf6e6932f05d413620f61064b578711b5ebaa3efc237b`;
  - row24 rep1 `9634358068`, digest `sha256:60c252e31c7a932ff66a37c4e387dff14374f48696d6f8e8cca1d4a7041ff424`;
  - row24 rep2 `9634358076`, digest `sha256:aac46afe41e4cea5477c4ab22e98ddbe41b2022ae7d5b828fd2241c57005b4d4`;
  - row25 rep1 `9634361831`, digest `sha256:3a2ae1bd94c96d67f9bd226d14f7331cdf0a70122cf395f572568e30b9d3c7b8`;
  - row25 rep2 `9634363793`, digest `sha256:6fa06d95fcabda70a4e25783f286dce7738080e7e4180b682efa948ffabb3943`.

## Frozen new universe

Rows: **23, 24, 25** only.

Four additional paired CRN replicates, with no reuse of prior science seeds:

- replicate 3: `957000000 + row*1000 + rayIndex`;
- replicate 4: `958000000 + row*1000 + rayIndex`;
- replicate 5: `959000000 + row*1000 + rayIndex`;
- replicate 6: `960000000 + row*1000 + rayIndex`.

Each replicate retains the exact reviewed paired broadband runner from `75035d...`; only its stage/replicate/seed constants are changed by a thin wrapper before invoking the frozen code.

Per new replicate:
- 64 rays;
- 2 conditions (default and normalized HRRR vertical-shape proxy);
- 50,000 photons/ray/condition;
- same seed within each default/HRRR pair.

New execution budget: `3 rows x 4 replicates x 64 rays x 2 conditions = 1536 solver calls`, or **76.8M configured photon histories**.

No retry/rerun/resume may reuse this new identity after any solver invocation.

## Frozen physical and numerical inputs

Byte-for-byte source identity remains the completed/reviewed broadband package:

- Taylor-v1 renderer and original-SQM operator unchanged;
- `wavelength 380 780` and `mc_spectral_is 550.0` unchanged;
- same AFGLUS/data/runtime hashes;
- same row geometry, AOD550, pressure, day 220, albedo, 64-ray quadrature;
- same HRRR raw profile and normalized shape builder;
- same `aerosol_default` optical family;
- HRRR condition differs from default only by one inserted `aerosol_file tau` line;
- no Taylor observations/residuals are read by the reproducibility analysis.

This is a numerical Monte Carlo audit, not an atmosphere validation run.

## Binding preflight

Before solver execution:

1. verify exact reviewed broadband source blobs from `75035d...`;
2. verify exact HRRR raw artifact/hash and helper source identities;
3. verify exact reviewed libRadtran/MYSTIC runtime hashes;
4. prove the new replicate/seed universe is exactly 768 unique ray seeds (12 row/replicate groups x 64), all in namespaces 957-960;
5. dry-render all `3 x 4 x 64 = 768` paired identities and prove that HRRR differs from default by exactly one `aerosol_file tau` line and `mc_basename` path only;
6. verify the same HRRR HGT/MASSDEN/PRES and COLMD sanity gates already used in the reviewed package.

Any preflight failure stops the identity.

## Frozen analysis

Combine the 4 new replicates with the 2 immutable completed replicates from run `33042326594`, yielding **n=6 independent seeds per row** at the same 50k photon budget.

For each row, report separately:

### Absolute default broadband response
- six `defaultQ` values;
- sample mean, sample SD, standard error, coefficient of variation, min/max;
- six propagated `defaultQStdConservative` values;
- ratio of empirical sample SD to the median propagated sigma.

### Paired HRRR/default contrast
- six `deltaMagHrrrMinusDefault` values;
- sample mean, sample SD, standard error, min/max;
- six propagated `deltaMagIndependentMcSigmaConservative` values;
- ratio of empirical sample SD to the median propagated sigma.

### Ray-level diagnostic
For each row and ray, use all six default `q` values to compute between-seed sample SD and compare it with the median reported per-run `qStdConservative`. Summarize the distribution of those SD/sigma ratios (median, p90, maximum).

No Taylor observed-minus-model residual, SQM zero-point, AOD fitting, F/tau, Level-B, or human model enters this analysis.

## Interpretation boundary

A large empirical between-seed variance would show that the current integrated spectral-std propagation is not a calibrated uncertainty estimator for this ALIS broadband use. It would **not** prove that MYSTIC is biased and would **not** validate or invalidate HRRR atmosphere physics.

After this audit, any photon-budget scaling test must be a separate preregistered identity. No production or scientific Taylor atmosphere conclusion is authorized from this review branch.