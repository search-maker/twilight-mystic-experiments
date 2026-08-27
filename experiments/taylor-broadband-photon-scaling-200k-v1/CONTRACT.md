# Taylor broadband photon-scaling 200k audit v1

Status: **review-only; no solver execution authorized by this branch.**

## Purpose

The completed six-seed 50k broadband Monte Carlo audit (PR #518, run `33043770640`) showed that empirical between-seed variability of the Taylor-v1 original-SQM broadband response is far larger than the existing `mc.rad.std.spc` propagation. Before any further Taylor atmosphere interpretation, test one clean photon-count scaling step on the **default atmosphere only**.

Question frozen before any 200k result:

> If the unchanged Taylor-v1 broadband MYSTIC calculation is increased from 50,000 to 200,000 photons per ray (exactly 4x), how does empirical between-seed variability change?

Under ordinary Monte Carlo square-root scaling, the descriptive reference expectation is `SD_200k / SD_50k = 0.5`. This is **not** an acceptance threshold. The ratio is reported as observed; no post-result tolerance may be invented.

## Immutable 50k reference

Authoritative 50k analysis:
- run `33043770640`, attempt 1;
- head `1097c9d2c07234768028fa6c06a0e0d1a7f43755`;
- analysis artifact `9634873751`;
- artifact ZIP digest `sha256:f6e36e4310ef5d3c8eb16cd56e0063ad01185e4ebd498ef0789c31609d443a57`;
- six independent 50k seeds per row, rows 23-25.

Frozen 50k aggregate empirical sample SDs:
- row23 `0.15223358970187326` (CV `0.021718041314575328`);
- row24 `0.3205384206766346` (CV `0.06488478721678911`);
- row25 `0.293473562056203` (CV `0.08343468537232149`).

These values are reference evidence only; Taylor observed-minus-model residuals are not used.

## Frozen 200k universe

Rows: **23, 24, 25** only.

Six new independent default-only replicates:
- replicate 1 seed base `961000000`;
- replicate 2 seed base `962000000`;
- replicate 3 seed base `963000000`;
- replicate 4 seed base `964000000`;
- replicate 5 seed base `965000000`;
- replicate 6 seed base `966000000`.

Per ray seed = `seedBase + row*1000 + rayIndex`.

All new seeds are disjoint from the consumed 50k namespaces `955000000` through `960000000`.

Each replicate:
- default atmosphere only; **no HRRR condition**;
- exact same 64 original-SQM angular rays;
- 200,000 photons/ray;
- exact Taylor-v1 `380-780 nm` renderer and `mc_spectral_is 550.0` broadband calculation;
- exact frozen row geometry, AOD550, pressure, aerosol-default family, AFGLUS/runtime, albedo, response tables, observer elevation treatment.

Execution budget if separately authorized: `3 rows x 6 replicates x 64 rays = 1152 solver calls`, **230.4M configured photon histories**.

No retry/rerun/resume may reuse this identity after any solver invocation.

## Binding preflight

Before solver execution:
1. verify exact reviewed Taylor-v1 source/runtime identities;
2. verify the 18 row/replicate groups and exactly 1152 unique new ray seeds;
3. prove all new seeds are disjoint from 955-960M namespaces;
4. dry-render every new case and compare it with the frozen 50k Taylor-v1 render after normalizing only these intentionally changed lines:
   - `mc_photons`;
   - `mc_randomseed`;
   - `mc_basename`.
   All remaining input lines must be byte-identical;
5. prove no `aerosol_file tau` line or other atmosphere modification is present.

Any failure stops the identity.

## Frozen analysis

For each row, using the six fresh 200k seeds:
- default Q values;
- sample mean, sample SD, standard error, CV, min/max;
- delta-method magnitude-equivalent empirical SD: `(2.5/ln(10)) * SD(Q)/mean(Q)`;
- median existing per-run propagated Q sigma and empirical SD / median propagated sigma.

Compare to the immutable six-seed 50k analysis:
- `SD_200k / SD_50k`;
- `CV_200k / CV_50k`;
- ratio relative to the ideal square-root reference (`observed SD ratio / 0.5`);
- independent-sample mean difference and its combined standard error, reported descriptively only.

At ray level, compute six-seed 200k sample SD for each of 64 rays and divide by the corresponding 50k six-seed ray sample SD from the immutable analysis artifact; summarize median, p90, maximum.

No pass/fail threshold is applied to these scaling ratios.

## Interpretation boundary

This is a numerical convergence audit only. It does not score Taylor observations, fit AOD, validate HRRR, establish physical MYSTIC bias, change Level-B/F/tau, or authorize production/human-model changes.

A later 800k or other photon-budget experiment, if scientifically warranted after this result, requires a separate preregistered identity.