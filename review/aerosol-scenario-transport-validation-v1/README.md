# Aerosol scenario transport validation v1 (ASTV v1)

Status: **review-only preregistration; no scientific ordinal allocated; no solver or result opening authorized**.

ASTV v1 is the proposed next computational experiment after AOPS v1, AFPF v1, the aerosol uncertainty policy, and the production-domain freeze. It asks a narrower question than AFPF: whether the five directly evaluated aerosol scenarios can be transported/interpolated across the already validated Level-B computational domain without pretending that AOD alone identifies the aerosol family.

## Frozen new geometry design

The new design has 24 off-lattice geometries inside the frozen Level-B domain. They are the first 24 points of the existing deterministic five-dimensional Halton construction, rescaled to the current operational box and checked against the existing Level-B support-distance limit. The same five coordinates are used as the existing surrogate: Sun depression, target altitude, cosine-relative-azimuth coordinate, observer elevation, and AOD550.

Six geometries are fresh validation holdouts: Halton indices `1, 6, 8, 21, 23, 24`. Their selection is geometry-only: among feasible six-point subsets, the frozen rule covers all ten existing boundary strata, requires every holdout to remain within 0.60 of the historical-plus-new aerosol-transfer training set, then maximizes pairwise separation. No new MYSTIC value or prediction is used to select them.

The remaining 18 new geometries are transport-training points. Together with the already-opened 24 AFPF cells, the transfer model has 42 training geometries per aerosol alternative state.

## Scientific cases

Each new geometry has the same five aerosol states as AFPF and three CRN replicates. One fresh seed is shared by all five states within a geometry x replicate group. Seed values are not allocated by this preregistration.

The training stage is 18 x 5 x 3 = 270 cases. Cases at Sun depression <=8 deg use 20M photons; deeper cases through the 10.5-deg operational limit use 50M. The frozen maximum training budget is 7.65B histories.

The six holdouts are 90 additional cases and 2.25B additional histories. They execute only if the training-only readiness gate passes. Thus the maximum experiment is 360 new cases and 9.90B histories, but a training failure terminates the ordinal without executing/opening the fresh holdout.

## Frozen transfer model

For each non-native aerosol state, ASTV models a 13-dimensional transfer relative to `native-rural-ss`:

- three paired natural-log ratios for the frozen positive integrated channels; and
- ten paired differences in the frozen normalized Level-B nullspace-PCA coordinates.

The transfer interpolator is fixed before science: vector-valued inverse-distance weighting in the exact existing `V1_IDW_COS_COORDINATES`, `k=6`, power `1`. There is no candidate family search, no hyperparameter selection, and no holdout-driven tuning. The native transfer is exactly zero by definition.

The historical AFPF raw artifacts are training-only and may not count as fresh validation. Before any new authorization, a zero-solver compatibility review must reacquire all 360 bound historical case artifacts by their frozen acquisition manifest, verify every digest, and prove that the absolute spectra can be projected into the frozen 13-target Level-B representation without epsilon substitution.

## Frozen gates

Before holdout execution, leave-one-geometry-out evaluation over the 42 training geometries must pass the already frozen Level-B v3 thresholds: absolute mean signed log bias <=0.08, median absolute log error <=0.15, worst absolute log error <=0.35, median shape NRMSE <=0.75, worst shape NRMSE <=1.25, and worst single normalized shape-coefficient error <=3.0.

Training-only maximum absolute LOO error per aerosol state and primary channel becomes the fixed interpolation padding, and that padding itself may not exceed 0.35. If training readiness fails, the experiment ends without holdout execution and without retuning.

If training passes, the six fresh holdouts are evaluated twice: transfer-isolated (direct native MYSTIC plus interpolated transfer) and end-to-end (frozen Level-B v3 native surrogate plus interpolated transfer). Both must pass the same primary and shape gates. The training-calibrated primary-channel envelope must contain 100% of direct holdout state values and cannot be widened from holdout results.

Level-B limiting-magnitude errors are reported and must remain finite. This preregistration does not invent a new magnitude-error threshold because no separate pre-existing frozen Level-B magnitude-error tolerance was found; the pass/fail gate stays on the validated sky-representation inputs and exact byte-bound human-threshold propagation.

## Closed boundary

Even a PASS authorizes only a separate review of a computational aerosol-transfer package. It does not authorize production, aerosol probabilities, equal scenario weights, empirical real-sky validity, a starsvisibility change, or a universal clock-minute correction.

Before any science: this preregistration must merge under exact-head non-scientific CI; historical AFPF compatibility and the analysis/transport implementation must pass separate zero-solver review; 72 fresh CRN seeds must pass collision review; fresh repository-global preauthorization must prove the next ordinal; then a one-file Draft authorization and a separate dispatch are required. GitHub rerun/retry/resume remain forbidden.
