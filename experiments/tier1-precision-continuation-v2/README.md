# Tier-1 precision continuation preparation v2

This package prepares, but does not authorize or dispatch, a bounded additive continuation of the execution-complete ordinal-2 Tier-1 evidence from run `30952457327`, attempt 1, source head `c9679a515c5f4538345d0d83252bcd8e37eb7b7e`.

The historical workflow failed because its then-current post-processing treated the valid zero estimator in `train-0047-alis-b1` as a structural failure. The immutable historical result remains a failure. The corrected schema-v2 interpretation is distinct: all 96 cases executed, the aggregate is `COMPLETED` and `SCIENTIFICALLY_INELIGIBLE`, the independent audit passed, and the numerical dataset requires continuation. No historical artifact is rewritten. The package binds the exact reviewed corrected dataset, aggregate, audit, original plan seed universe, and full continuation geometry projection; caller-recomputed substitute hashes are refused. Exact replay inputs used by the contract tests are preserved under `evidence/ordinal2-corrected-v2`.

## Frozen universe and budget

The recovered per-geometry analysis selects exactly 20 geometries:

- 50 million photons/block: `train-0009`, `train-0017`, `train-0033`, `train-0041`, `train-0046`;
- 100 million photons/block: `train-0003`, `train-0011`, `train-0013`, `train-0019`, `train-0029`, `train-0035`, `train-0045`;
- 200 million photons/block: `train-0007`, `train-0015`, `train-0023`, `train-0027`, `train-0031`, `train-0039`, `train-0043`, `train-0047`.

Roles are immutable: `train-0015`, `train-0035`, and `train-0045` remain internal holdout; the other 17 remain surrogate-training. No stopped or unresolved holdout may enter fitting.

Continuation is evaluated only after complete independently audited two-block waves: blocks 3-4, 5-6, and 7-8. `validate_proposal` reconstructs the exact frozen case universe before use. `audit_wave` independently recomputes each photopic estimator from the 15 raw selected-node radiances, binds every case result and the aggregate, and must pass before `analyze_waves` can make a stopping decision. A full wave is at most 40 cases and 5.1 billion configured photon histories. The absolute continuation cap is 120 cases, 15.3 billion configured/attempted photon histories, and eight total blocks per geometry. Dispatch consumes its identity, seeds, and configured budget even when execution fails.

All 120 potential seeds are frozen in `package.py` before observing any continuation result. The proposal verifies uniqueness and no overlap with the bound 96-seed ordinal-2 source universe.

## Stopping and zero rules

Every decision preserves blocks 1-2 and every completed continuation block. There is no replacement, selective deletion, epsilon substitution, or threshold change.

- With no zero block, RSEM `<= 0.05` is `PRECISION_TARGET_MET` and stops.
- With no zero block, `0.05 < RSEM <= 0.08` is `PRECISION_ACCEPTED` and stops.
- With no zero block, RSEM `> 0.08` continues at blocks 4 or 6 and becomes `PRECISION_CONTINUATION_EXHAUSTED` at block 8.
- Any exact zero estimator must agree with an all-zero raw selected-node spectrum. Its RSEM remains null. It continues through block 8 and then becomes `PRECISION_CONTINUATION_EXHAUSTED_ZERO_HIT`.

Both exhausted states are execution-complete but scientifically ineligible. Missing, duplicated, unplanned, malformed, nonfinite, hash-drifted, timed-out, or nonzero-exit evidence is instead `STRUCTURAL_OR_EXECUTION_FAILURE`; it is never numerical exhaustion.

`train-0047` therefore cannot become scientifically eligible under this protocol because its preserved source block is zero. The continuation is a bounded diagnosis. A zero-aware alternative estimator would require a separate preregistration.

## Authorization boundary

Every wave requires a separate future one-purpose authorization commit, the next verified unused monotonic ordinal, a fresh execution key, exact-head `workflow_dispatch`, and attempt 1. GitHub Re-run and automatic continuation are forbidden. This package allocates no ordinal or execution key and enables no authorization, dispatch, surrogate fit, Tier-2 work, or production promotion.
