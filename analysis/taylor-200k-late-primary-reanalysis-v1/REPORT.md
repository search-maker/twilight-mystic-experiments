# Taylor late-primary reanalysis using six-seed 200k broadband means

Status: **analysis-only complete**. No MYSTIC solver was executed for this reanalysis and no physical/input parameter was changed.

## Purpose

The original Taylor-v1 validation converted a single broadband ALIS MYSTIC realization per row into original-SQM magnitudes. Later empirical reproducibility work showed that the integrated `mc.rad.std.spc` propagation dramatically understated between-seed broadband variability. A separate frozen 4x photon audit then produced six independent **200,000-photon-per-ray** default-atmosphere realizations for rows 23–25.

This reanalysis asks only:

> What do the already-frozen Taylor residuals become if the legacy single-seed broadband `Q` for rows 23–25 is replaced by the six-seed 200k mean `Q`, while the original Taylor SQM/Vega calibration and every physical input remain unchanged?

Because the SQM magnitude is logarithmic in `Q`, the correction is exact without re-fetching or refitting the zero point:

`m_revised = m_legacy - 2.5 log10(Q_200k_mean / Q_legacy)`.

## Immutable evidence

1. Taylor-v1 analysis recovery: run `33016529095`, artifact `9624747631`, ZIP digest `sha256:242ad28f9a46fa2c90006ff728eeefb8e6c30b3ca583c4f044af4d48f8821dea`.
2. Immutable Taylor-v1 row-Q extraction from the broadband self-replication gate: run `33042326594`, artifact `9634368696`, digest `sha256:ada32fe2e04f3baddd63e5d962e9a78e881728c41f42826e1cb0b85784835c90`.
3. Six-seed 200k photon-scaling analysis: run `33044289555`, artifact `9635082283`, digest `sha256:62b938226602a0e97548ae291c2ce845f064210af9131dc3503e944cbe2601cb`.

## Row results

| row | legacy residual obs-model | model shift from Q estimator | revised residual | empirical numerical SD of one 200k run | numerical SE of six-run mean |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 23 | +0.05896 | -0.02647 | **+0.08544** | 0.01501 | 0.00613 |
| 24 | +0.10401 | -0.06948 | **+0.17350** | 0.04536 | 0.01852 |
| 25 | +0.39321 | +0.21625 | **+0.17696** | 0.05560 | 0.02270 |

The principal change is row 25: the former `+0.3932 mag` late-primary residual falls to **`+0.1770 mag`** when the single-seed estimator is replaced by the higher-photon six-seed mean.

Rows 23 and 24 move in the opposite direction, from `+0.0590/+0.1040` to `+0.0854/+0.1735`. This is exactly why the correction must be treated as numerical convergence rather than as a favorable atmosphere adjustment.

## Central residual metrics only

### Rows 23–25

- mean residual: `+0.18540 -> +0.14530 mag`;
- RMS: `0.23728 -> 0.15134 mag`;
- max absolute residual: `0.39321 -> 0.17696 mag`.

### Primary rows 1–25

Replacing **only** rows 23–25 while leaving rows 1–22 untouched:

- mean residual: `-0.06146 -> -0.06628 mag`;
- RMS: `0.13250 -> 0.11640 mag`;
- MAE: `0.11292 -> 0.10811 mag`;
- max absolute residual: `0.39321 -> 0.17696 mag`.

### Published nominal-SQM submetric rows 8–25

- mean residual: `-0.05252 -> -0.05920 mag`;
- RMS: `0.14012 -> 0.11861 mag`;
- MAE: `0.11455 -> 0.10787 mag`;
- max absolute residual: `0.39321 -> 0.17696 mag`.

## Scientific consequence

The earlier row-25 `+0.393 mag` residual **must not be used as a precise atmosphere diagnostic**. A substantial part of that apparent late rise was numerical single-seed broadband ALIS variability. The better-converged central estimate leaves a much smaller late-primary discrepancy, roughly `0.09–0.18 mag` across rows 23–25.

This weakens any argument that Taylor demanded a large atmosphere correction at the end of the primary solar interval. It is also consistent with the broader project result that no uniform Level-B/direct-MYSTIC sky-darkening bias has emerged.

## What is deliberately NOT recomputed

No new Taylor validation classification is issued here. In particular, this analysis does **not** recompute:

- covariance/reduced chi-square;
- `ABSOLUTE_CONSISTENT` / `ABSOLUTE_INCONSISTENT`;
- shape reduced chi-square / `SHAPE_CONSISTENT`;
- timing uncertainty from the model derivative;
- local AOD derivative or AOD-propagated sigma;
- the old broadband `sigma_mc`.

Reason: those legacy uncertainty/derivative components were themselves produced from broadband ALIS calculations that have not all received the same empirical multi-seed convergence treatment. Reusing them unchanged would mix a corrected central estimator with an uncertainty model now known to be inadequately calibrated.

## Boundary / next decision

The six-run 200k mean is already sufficiently precise to show that the former `+0.393 mag` row-25 outlier was not stable. An immediate 800k brute-force rerun is therefore **not automatically justified** merely to investigate that outlier.

The next numerical work should be targeted: determine which Taylor quantities actually require multi-seed reconvergence for a valid full statistical classification—especially the local time derivative and AOD sensitivity near rows 23–25—rather than rerunning the entire 32-row universe at a uniformly larger photon budget.
