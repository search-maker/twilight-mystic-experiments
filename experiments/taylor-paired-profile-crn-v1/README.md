# Taylor paired high-photon profile comparison v1 — Issue #828

This package is the preregistered, result-blind experiment requested in Issue #828.

## Frozen scientific question

Compare exactly two cases over Taylor rows 18–27 (geometric Sun altitude about -3.49 to -6.46 deg):

1. the frozen Taylor baseline/default aerosol vertical profile;
2. the already-existing CAMS 532-nm vertically resolved extinction **proxy** from PR #508 / run 33039911540.

The CAMS profile is used because its provenance predates Issue #828 and is independently retrieved. It is **not** selected by Taylor residual fit quality and is **not** claimed to be the exact same-cycle measured atmosphere; PR #536 leaves exact same-cycle vertical extinction unresolved.

## Frozen equality between cases

Per-row total AOD550, geometric solar geometry, pressure, 0.15 surface albedo, AFGL-US atmosphere family, `aerosol_default` spectral/phase family, 380–780 nm ALIS operator, `mc_spectral_is 550`, original Unihedron SQM spectral/angular response, 64-ray quadrature, and Vega calibration are identical. Only the aerosol vertical tau allocation changes.

## Monte Carlo design

- rows: 18–27, no result-dependent row selection;
- 6 independent seed pairs;
- 200,000 photons/ray/case for every row (not only late rows);
- 64 original-SQM rays plus one true-zenith diagnostic ray per case;
- same seed is used for baseline and proxy at a given pair/row/ray (CRN pairing);
- empirical uncertainty is the sample between-pair SD and SE; `mc.rad.std.spc` is not treated as the calibrated between-seed error estimator;
- maximum 7,800 solver calls / 1.56 billion configured photon histories.

Late-row precision is preregistered before results: rows 23–26 must have baseline mean SE <= 0.03 mag, proxy mean SE <= 0.03 mag, and paired delta SE <= 0.03 mag. Failure requires a fresh reviewed continuation identity; it never authorizes reinterpretation or retuning.

## Frozen analysis

The main paired quantity is `proxy model mag - baseline model mag`. The two regional questions are frozen as rows 20–22 (-4.16 to -4.82 deg) and rows 24–26 (-5.48 to -6.13 deg). A regional effect is called numerically resolved only if the two-sided 95% Student-t CI across the six independent pair-level regional means excludes zero.

Agreement with Taylor is reported separately as the change in absolute observed-minus-model residual (`|obs-proxy| - |obs-baseline|`). This is a diagnostic, not a fit. Row 26 is already marked `secondary_moon_background_sensitive`, so Taylor agreement there is descriptive rather than a solar-model validation.

The Koomen/operator diagnostic independently computes true zenith-direction brightness and the fully angularly integrated original-SQM synthetic measurement at identical timestamps. The reported correction is `wide SQM - true zenith`; no constant offset is fit. A predeclared 0.10 mag absolute scale (about 25% of 0.39 mag) is used only to label whether the operator correction is of potentially meaningful scale.

## Boundaries

No offset, AOD, profile, or physical parameter may be fit to Taylor. No result from this experiment may select a production atmosphere, promote a production model, claim the CAMS proxy is exact, or validate human first-seeing/Level-B.
