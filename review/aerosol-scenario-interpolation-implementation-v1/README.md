# Aerosol scenario interpolation implementation v1

Status: **training-only implementation review; no holdout opening, ordinal allocation, solver execution, or production authorization**.

`select_model_v1.py` implements the candidate universe, leave-one-AFPF-cell-out selection, metric definitions, deterministic tie-breaking, source-artifact binding, and materialized evaluator required by the merged `aerosol-scenario-interpolation-validation-v1` preregistration.

The implementation may consume only the exact already-open AFPF ordinal-38 analysis-recovery ZIP bound by the protocol. It predicts the 12 integrated-channel state-vs-native log-contrast fields. Observer elevation is deliberately absent from the fitted coordinates; the separately frozen future holdout tests that zero-order invariance hypothesis.

The review tests use synthetic data only. This PR must not run the real ordinal-38 selection or read any future ordinal-39 holdout outcome. After exact-head review and merge, a separate training-only materialization step may run this exact implementation on the bound ordinal-38 artifact. Scientific execution remains a later, separately authorized transition.
