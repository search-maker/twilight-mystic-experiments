# Twilight surrogate tier-1 execution bridge

This stage is a guarded numerical data-generation experiment for the already frozen `tier-1-provisional` design. It contains exactly 48 geometries and 96 independent ALIS cases, totaling 6.96 billion configured photon histories. Each geometry has two fresh blocks, and the internal 39/9 training/holdout partition remains frozen before execution.

The source must be the successful, first-attempt `Twilight surrogate tier-1 proposal` artifact. The six computational reference anchors are audited but never included in fitting. The per-case ALIS importance reference of 500, 550, or 600 nm is used only for variance reduction; all other physical and runtime inputs remain inherited from the audited MYSTIC pilot contract.

Scientific execution is manual-only, first-attempt-only, duplicate-refusing, non-retrying, and requires a separate one-purpose authorization commit. The active authorization remains disabled in this change. Aggregate and independent audit verify all 96 outputs before the analysis classifies Monte Carlo precision for each geometry.

The analysis does not fit a surrogate and cannot authorize a model or a production default. Additional fresh blocks may later be proposed only for geometries exceeding the predeclared maximum RSEM. Observation validation remains mandatory.
