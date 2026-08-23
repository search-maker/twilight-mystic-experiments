# AOPS v1 ordinal 37 — verified results report

Status: **REPORT-ONLY EVIDENCE; NO SCIENTIFIC RERUN**

This report records the already completed and independently verified aerosol optical-property sensitivity experiment. It does not allocate a scientific identity, execute MYSTIC, rerun/retry/resume any scientific job, alter the preregistration, or authorize a production correction.

## Immutable execution and recovery chain

- Scientific ordinal: `37`.
- Authorization/dispatch head: `a1895adebf39a5c2c12d80276a119e032fdf090b`.
- Original science workflow run: `32624595188`, attempt 1.
- Original run terminal state: failure **after** all 360 scientific case jobs and frozen scalar/spectral aggregation had completed successfully; the sole failing stage was the cross-repository human-threshold dependency fetch before Level-B propagation.
- GitHub rerun/retry/resume: **none**.
- Analysis-only recovery run: `32646634116`, attempt 1, no solver/runtime/scientific-case execution.
- Recovery artifact ID: `9495160497`.
- Recovery artifact GitHub/downloaded-byte SHA-256: `5c981e9b96fc20f9fe95a93320f8bf4df2c0f1c6a9031f75035df68838348c51`.
- Bound human-threshold Git blob: `bb4cd0ff02159ecffe276022cec9d292c7a434a3`.
- Frozen independent final-analysis verifier SHA-256: `ac37f8e20d160bae870c7bc2ae35323b764f30bcedb1f247eb7d5b7fbb4623ab`.
- Final verifier result: `PASS_AOPS_V1_ORDINAL37_ANALYSIS_ARTIFACT_STRUCTURE_AND_BINDINGS`.
- Verified cardinalities: 360 cases, 72 CRN comparison groups, 24 analysis cells.
- Separately frozen pre-result raw audit: 8 CRN groups, one per Sun-depression × AOD stratum, all five aerosol states per group = 40 original source cases; all downloaded artifact bytes matched GitHub digests and the raw structural audit passed.

## Preregistered result universe

No new pooling, inferential statistics, ranking, or post-hoc cell selection was introduced after result opening.

- Scalar preregistered rows: `648/648`, all `FINITE_THREE_REPLICATES`.
- Level-B preregistered rows: `216/216`, all `FINITE_THREE_REPLICATES`.
- Spectral cell/contrast rows: `216/216`.
- Spectral unresolved-node rows: `40/216`, all at Sun depression 8 degrees.
- Total unresolved spectral nodes: `21,095`.
- Epsilon substitution: **none**.

## Frozen scientific findings

### 1. SSA sensitivity is directionally universal on the preregistered design surface

For both controlled SSA contrasts, increasing SSA from 0.85 to 0.98 brightened the modeled twilight sky in **all 24/24 analysis cells in each of the three scalar channels**:

- `ssa_high_vs_low_at_g060`: 24/24 positive in photopic, 24/24 positive in scotopic, 24/24 positive in Johnson-V effective radiance.
- `ssa_high_vs_low_at_g080`: 24/24 positive in photopic, 24/24 positive in scotopic, 24/24 positive in Johnson-V effective radiance.

The separately bound Level-B human-threshold propagation has the corresponding opposite visibility direction in **all 24/24 cells** for both contrasts: higher SSA produces a negative limiting-magnitude delta, i.e. a brighter twilight background makes the stellar threshold less favorable.

### 2. Asymmetry parameter g does not support one universal correction

Both preregistered g contrasts contain positive and negative cell effects on the frozen design surface:

- `g_high_vs_low_at_ssa085`: mixed sign across cells/channels and mixed sign in Level-B.
- `g_high_vs_low_at_ssa098`: mixed sign across cells/channels and mixed sign in Level-B.

Therefore AOPS v1 does **not** support replacing g sensitivity with one global sign or one global additive/multiplicative correction.

### 3. SSA × g interaction is context-dependent

`ssa_x_g_interaction` changes sign across cells/channels and in Level-B. No universal interaction sign or constant is supported by the preregistered results.

### 4. Native rural spring-summer aerosol is not equivalent to one constant `(SSA, g)` pair

The native-vs-controlled comparisons do not identify a single constant endpoint that reproduces native aerosol behavior over the whole design surface.

A particularly strong directional result is `native_vs_ssa085_g060`: it is scalar-negative in all 24/24 cells in each scalar channel and Level-B positive in all 24/24 cells. Other native-vs-constant contrasts change sign somewhere over the full frozen surface (even where one individual channel can remain one-sign).

## Scientific boundary

AOPS v1 establishes that AOD550 alone is not sufficient to characterize aerosol optical-property sensitivity across this modeled twilight surface. It also establishes that broad constant SSA/g overrides are useful **sensitivity controls**, not a realistic aerosol climatology.

Consequently:

- do not hard-code the AOPS endpoint effects as a universal production correction;
- do not treat constant SSA/g endpoints as a replacement for wavelength-dependent realistic aerosol microphysics/phase-function treatment;
- do not convert Level-B magnitude deltas into universal clock-minute shifts without an explicit date/location solar-depression rate;
- AFC2 R8 and ordinal-37 raw scientific evidence remain immutable.

## Provenance markers

Issue #60 terminal analysis-recovery marker:

`AOPS-V1-ANALYSIS-RECOVERY-COMPLETED ordinal=37 source_run=32624595188 recovery_run=32646634116 attempt=1 cases=360 groups=72 cells=24 artifact_id=9495160497 artifact_digest=sha256:5c981e9b96fc20f9fe95a93320f8bf4df2c0f1c6a9031f75035df68838348c51 solver=false rerun=false retry=false resume=false`

This file is a provenance/reporting addition only. The preregistration, transport identities, scientific cases, seeds, analysis algorithms, and verified result artifact are unchanged.
