# Aerosol scenario interpolation implementation v1 — stdlib review

Status: **training-only implementation review; no holdout opening, ordinal allocation, solver execution, or production authorization**.

This is a fresh review identity after the prior exact implementation head was closed unmerged because generic repository CI did not provide `numpy`. The scientific/model-selection contract is unchanged: the same 17 preregistered candidates, 24-fold leave-one-cell-out selection, fixed metrics, gates, ranking, and no-holdout-use rule are preserved. The implementation is now Python-standard-library only.

`select_model_v1.py` consumes only the exact already-open AFPF ordinal-38 analysis-recovery ZIP bound by the merged ASIV v1 protocol. It verifies the ZIP digest, requires the exact 24-cell/12-field finite training surface, implements deterministic IDW and quadratic ridge, freezes linear quantile semantics, leaves the ridge intercept unpenalized, and materializes a self-hashed evaluator.

The quadratic-ridge solver is a deterministic binary64 Cholesky implementation over the 15-term frozen basis. Observer elevation remains absent from the fitted coordinates; the separately frozen future elevated holdout tests the zero-order elevation-invariance hypothesis.

The review tests use synthetic data only. This review does not run the real ordinal-38 selection and reads no future ordinal-39 holdout outcome. After exact-head review and merge, a separate training-only materialization step may run this exact implementation on the bound ordinal-38 artifact.
