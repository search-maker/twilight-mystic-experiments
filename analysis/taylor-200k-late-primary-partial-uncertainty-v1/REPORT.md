# Taylor late-primary partial uncertainty budget after 200k reconvergence

Status: **analysis-only partial budget**. This is deliberately **not** a renewed Taylor covariance classification.

## What is now on a compatible basis

For rows 23–25 we now have:

1. revised central model values from six independent 200k-photon broadband realizations;
2. empirical numerical SE of the six-run mean;
3. a reconverged model-time derivative using six-seed 200k rows 22–26 and the exact Taylor-v1 `numpy.gradient` definition;
4. the unchanged Taylor dataset repeatability term;
5. the unchanged correlated common systematic term.

The local AOD derivative is **not** on a usable quantitative basis: its six-seed 200k common-random-number mean is smaller than its between-seed SD at every late-primary row. Therefore AOD is marked **UNRESOLVED** and is not silently set to zero.

## Immutable terms

- dataset repeatability random term: `0.0621462261 mag`;
- correlated common systematic: `0.111803398875 mag`;
- revised residuals: row23 `+0.08544`, row24 `+0.17350`, row25 `+0.17696 mag`;
- renewed timing sigma for the unchanged +/-30 s timestamp contract: `0.09544`, `0.09731`, `0.09939 mag`;
- numerical SE of six-run 200k mean: `0.00613`, `0.01852`, `0.02270 mag`.

## Partial random budget

Define, **excluding AOD**:

`partial_random_sigma = sqrt(dataset_repeatability^2 + timing_sigma^2 + numerical_SE_mean^2)`.

| row | revised residual | partial random sigma, AOD excluded | residual / partial sigma | orientation sigma incl. correlated common systematic, AOD excluded | residual / orientation sigma |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 23 | +0.08544 | 0.11405 | 0.75 | 0.15971 | 0.53 |
| 24 | +0.17350 | 0.11694 | 1.48 | 0.16178 | 1.07 |
| 25 | +0.17696 | 0.11940 | 1.48 | 0.16357 | 1.08 |

The fourth column is a genuine partial random budget because it combines independent/random terms already on a defensible numerical basis. The fifth column is shown only as a **per-row orientation**: the `0.111803 mag` common systematic is correlated across rows and must remain a covariance term in any formal multi-row test.

## What the AOD result means

The old local AOD terms cannot be reused:

- row23 legacy derivative `+0.18975` -> six-seed 200k mean `-0.15509 ± 0.40771 mag/AOD`;
- row24 `-1.76174` -> `-0.19133 ± 0.55809`;
- row25 `+3.60325` -> `-0.04576 ± 0.51177`.

The correct conclusion is **not** that AOD contributes exactly zero uncertainty. The derivative is unresolved. A full covariance analysis therefore remains blocked unless a quantitatively useful AOD sensitivity estimator is obtained or a defensible alternative treatment of atmosphere uncertainty is preregistered.

## Scientific interpretation

After numerical reconvergence:

- the former row25 `+0.393 mag` outlier falls to `+0.177 mag`;
- the timing term is stable around `0.10 mag`;
- the former row25 `0.177 mag` AOD uncertainty term was based on an unstable finite-difference slope and is retired;
- even **before** adding any AOD contribution, rows24–25 are only about `1.48` partial-random sigma from the model;
- showing the already-declared correlated common systematic as a marginal per-row orientation reduces those ratios to about `1.07–1.08`.

Thus the late-primary Taylor observations do **not** provide a compelling standalone contradiction of the direct-MYSTIC atmosphere after numerical convergence is handled correctly.

## Why no global `ABSOLUTE_CONSISTENT` label is reissued

A formal Taylor-v1-style global covariance test still needs compatible treatment across the full primary row universe. Rows1–22 retain legacy single-seed broadband numerical estimates; their Monte Carlo variance has not yet been empirically characterized on the same basis. In addition, the late AOD derivative remains unresolved.

The next efficient question is therefore **not** an 800k brute-force rerun of all rows. It is to determine how broadband between-seed variability changes across earlier/brighter Taylor rows, so we know whether rows1–22 require wholesale reconvergence or whether a smaller validated numerical-error model is sufficient.
