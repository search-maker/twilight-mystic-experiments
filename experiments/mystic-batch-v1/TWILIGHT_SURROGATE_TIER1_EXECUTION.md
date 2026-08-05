# Twilight surrogate tier-1 execution bridge

This stage is a guarded numerical data-generation experiment for the already frozen `tier-1-provisional` design. It contains exactly 48 geometries and 96 independent ALIS cases, totaling 6.96 billion configured photon histories. Each geometry has two fresh blocks, and the internal 39/9 training/holdout partition remains frozen before execution.

The source must be the successful, first-attempt `Twilight surrogate tier-1 proposal` artifact. The six computational reference anchors are audited but never included in fitting. The per-case ALIS importance reference of 500, 550, or 600 nm is used only for variance reduction; all other physical and runtime inputs remain inherited from the audited MYSTIC pilot contract.

Scientific execution is manual-only, first-attempt-only, duplicate-refusing, non-retrying, and requires a separate one-purpose authorization commit. The active authorization remains disabled in this change. Aggregate and independent audit verify all 96 outputs before the analysis classifies Monte Carlo precision for each geometry.

The analysis does not fit a surrogate and cannot authorize a model or a production default. Additional fresh blocks may later be proposed only for geometries exceeding the predeclared maximum RSEM. Observation validation remains mandatory.

## Version 2 numerical-result semantics

Aggregation schema v2 separates execution completion from scientific eligibility. A case whose one allowed syntax check and one allowed solver execution both succeed, do not time out, and produce finite parseable outputs is execution-complete. A stochastic all-zero photopic estimator with an all-zero selected and raw spectrum is preserved as `NUMERICAL_ZERO_HIT_UNDERCONVERGED`; it is not relabeled as a crash and is never replaced, retried, or converted to a small positive number.

A zero-hit geometry is `ADAPTIVE_CONTINUATION_REQUIRED`, and the batch is `SCIENTIFICALLY_INELIGIBLE` while remaining `COMPLETED` at the execution layer. CV/RSEM is not computed for a group containing a zero-hit block; the report emits the zero-hit count/fraction, raw values, nonzero-block distribution, and an explicit `NOT_COMPUTED_ZERO_HIT_PRESENT` reason. All unaffected geometries continue through statistics and precision classification.

The independent audit derives zero-hit state from the raw radiance and standard-radiance files, re-hashes the resolved input, spectra, runtime report, and case result, and independently checks seeds, blocks, roles, photon accounting, and per-geometry statistics. Any crash, timeout, missing/malformed file, nonfinite value, identity drift, duplicate seed/block, or hash mismatch remains a structural or execution failure. Surrogate handoff refuses every dataset with a zero-hit or other unresolved continuation geometry.
