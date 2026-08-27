# Taylor primary-interval broadband Monte Carlo screen 50k v1

Status: **review-only; no solver execution authorized by this branch.**

## Purpose

Late-primary Taylor rows 23-25 showed large between-seed broadband ALIS variability, while their legacy integrated `mc.rad.std.spc` uncertainties understated that variability by two to three orders of magnitude. Before reconverging every primary row, screen numerical behavior at six evenly spaced **preselected** primary anchors.

This audit asks only whether empirical 50k between-seed broadband variability is already material earlier in twilight or grows mainly toward the late-primary regime.

No Taylor observed-minus-model residual is used to choose rows or settings.

## Frozen anchor rows

Rows: **1, 5, 9, 13, 17, 21**.

They are a deterministic every-fourth-row index sample across the primary interval, selected before any new seed is run. No row was selected for a favorable or unfavorable residual.

## Frozen execution universe

Six fresh independent default-atmosphere replicates per anchor row at the same 50,000 photons/ray budget used in the completed late-primary 50k reproducibility audit.

Seed bases:
- replicate 1: `979000000`;
- replicate 2: `980000000`;
- replicate 3: `981000000`;
- replicate 4: `982000000`;
- replicate 5: `983000000`;
- replicate 6: `984000000`.

Per-ray seed = `seedBase + row*1000 + rayIndex`.

All new seeds are disjoint from consumed Taylor broadband namespaces 955-978M.

Per row/replicate:
- default Taylor-v1 atmosphere only;
- exact frozen row AOD550, geometry, pressure, AFGLUS/runtime, aerosol-default family, albedo, site/elevation treatment;
- exact original-SQM 64-ray angular response;
- exact `wavelength 380 780` and `mc_spectral_is 550.0` broadband calculation;
- 50,000 photons/ray;
- no HRRR/CAMS profile substitution and no AOD perturbation.

If separately authorized: `6 rows x 6 replicates x 64 rays = 2304 solver calls`, or **115.2M configured photon histories**.

No retry/rerun/resume may reuse the one-shot science identity after any solver invocation.

## Binding dry preflight

Before solver execution:
1. verify exact reviewed Taylor-v1 renderer/source and reviewed libRadtran/MYSTIC runtime hashes;
2. verify exact anchor rows `[1,5,9,13,17,21]`, six replicate namespaces 979-984M, and exactly 2304 unique ray seeds;
3. prove all new seeds are disjoint from consumed 955-978M namespaces;
4. dry-render every new case and prove it is physically/model identical to the corresponding Taylor-v1 default render after normalizing only `mc_randomseed` and `mc_basename` (photon budget remains exactly 50k in both);
5. prove no `aerosol_file tau` or other atmosphere/profile modification is present.

Any preflight failure stops the identity.

## Frozen analysis

For each anchor row report across six seeds:
- six aggregate original-SQM Q values;
- mean, sample SD, SE, CV, min/max;
- magnitude-equivalent empirical single-run SD `(2.5/ln(10))*SD(Q)/mean(Q)`;
- numerical SE of the six-run mean in magnitude units;
- median legacy propagated `QStdConservative` from the six runs and empirical SD / median propagated sigma;
- ray-level six-seed SD / median reported ray sigma summary (median, p90, max).

For orientation, combine these six anchors with the immutable 50k late-primary results at rows23-25 from run `33043770640`, artifact `9634873751`, digest `sha256:f6e36e4310ef5d3c8eb16cd56e0063ad01185e4ebd498ef0789c31609d443a57`, and tabulate empirical magnitude-equivalent SD versus solar depression/model brightness.

No residuals or validation labels enter this analysis.

## Interpretation boundary

This is a numerical screening audit, not a Taylor model validation. It may determine whether full primary-row reconvergence is necessary or whether earlier rows have negligible Monte Carlo contribution relative to the immutable dataset repeatability `0.0621462261 mag`. No global chi-square, atmosphere fit, Level-B/F/tau/production, or human-model conclusion is authorized.