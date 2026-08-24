# ASIV v1 execution-core review

This package freezes the scientific transport and postprocessing needed for the already-merged `aerosol-scenario-interpolation-validation-v1` protocol. It is intentionally review-only.

## Frozen future execution shape

If, and only if, a later exact-main preauthorization plus one-file Draft authorization and separate dispatch authorize it, the future scientific run is exactly:

- 8 preregistered fresh holdout geometries;
- 3 common-random-number replicates per geometry;
- 5 aerosol states per geometry/replicate group;
- 24 fresh group seeds total, shared only across the five states within each CRN group;
- 120 cases total;
- 20,000,000 photon histories per case / 2.4 billion configured histories total;
- reference-vroom 1 nm calculation grid, raw MYSTIC 0.05 nm serialized output, 380–780 nm;
- the exact AFPF ordinal-38 OPAC/Shettle aerosol definitions and augmented OPAC data tree;
- the previously validated `atm_z_grid` local-ground elevation representation.

## Result opening and evaluation

No partial result interpretation is permitted. The aggregate requires the exact 120-case artifact universe, attempt 1 only, recomputes the three integrated channels from raw radiance spectra, and reports spectral unresolved-node counts without epsilon substitution.

The frozen selected model remains `IDW_COS_4D-k8-p2` with canonical SHA-256 `0b11a1691bfd2d9e3f073c786044bacedd3e9210bcb0660c76f21c34128a61af`. The scalar evaluator uses the same field ordering and metric implementation as the training-only selector and scores the preregistered nearest-cell and zero-contrast baselines.

The previously preregistered scenario-envelope endpoint thresholds are implemented as follows, before any holdout result is opened: for each holdout and each of the three integrated channels, take the minimum and maximum of the four OPAC-vs-native log contrasts. Compare predicted vs direct minimum and predicted vs direct maximum. This yields exactly 8 × 3 × 2 = 48 endpoint errors.

Derived Level-B is not separately fit. For each holdout replicate, apply the frozen predicted photopic `ln(state/native)` to that replicate's direct-MYSTIC native background, call the exact byte-bound `human-threshold.mjs` full branch with field factor 2.4, and compare predicted vs direct state-minus-native limiting-V delta. The Definition-of-Done is scored over the 32 three-replicate holdout/state mean-delta errors.

## Boundary

This review package:

- allocates no ordinal 39;
- allocates/reserves no scientific seed;
- creates no authorization or dispatch;
- adds no active scientific workflow;
- executes no libRadtran/MYSTIC/uvspec runtime;
- opens no fresh holdout value;
- changes no production or `starsvisibility` behavior.

After this package is reviewed and merged, its merge changes `main`, so the current preauthorization proof on `a994eb430b6f3aa90a2fc724c4fb5f390f613d93` becomes stale by design. A new exact-main ASIV preauthorization must reach terminal success before any ordinal-39 authorization may be considered.
