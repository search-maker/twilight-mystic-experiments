# AFPF v1 ordinal 38 — verified results report

Status: **REPORT-ONLY EVIDENCE; NO SCIENTIFIC RERUN**

This report records the already completed and verified aerosol full phase-function sensitivity experiment. It does not allocate a scientific identity, execute MYSTIC, rerun/retry/resume any scientific job, alter the preregistration, retune any post-result rule, or authorize a production correction.

## Immutable execution and recovery chain

- Scientific ordinal: `38`.
- Authorization/dispatch head: `7c160d1b1d1fbaa534076b7d30c14fcceda0e877`.
- Original science workflow run: `32672764808`, attempt 1.
- Original source aggregate job: `97294103672`.
- Original run terminal state: failure **after** all 360 scientific case jobs, exact-360 scalar/spectral aggregation, and Level-B input construction had completed successfully. The sole failing stage was the cross-repository fetch of the already byte-bound `human-threshold.mjs`, which returned HTTP 404 before Level-B propagation.
- Exact original source universe: 362 jobs = 1 successful preflight + 360/360 successful case jobs + 1 failed aggregate; 361 artifacts = 1 preflight + 360/360 unique case artifacts.
- GitHub rerun/retry/resume of the scientific run: **none**.
- Analysis-only recovery run: `32682787585`, attempt 1, SUCCESS; no solver/runtime/scientific-case execution.
- Recovery request head: `b037c1787109fa9c15f86b58bbda9a166464e3ce`, a one-file direct child of recovery-contract main `e84a838dd3299343fb8b550ccde936c2a04b763e`.
- Recovery artifact ID: `9504775903`.
- Recovery artifact GitHub SHA-256: `fa824ff1e693682ee5b89aa108259452823e1f8f10818d82c34f5d01ba9dac0a`.
- Independently downloaded recovery ZIP SHA-256: `fa824ff1e693682ee5b89aa108259452823e1f8f10818d82c34f5d01ba9dac0a` — exact match.
- Exact source preflight artifact: `9501900123`, SHA-256 `33807259982a4bceae06e079338af1bbbecb60a6024ca4bf94c4267e65d4c1b2`.
- Frozen seeded-design canonical SHA-256: `d2ad0e3ebcea48b2c683ab8a1c255af074cdaaa084c7082ac9345d021c8c9f62`.
- Bound human-threshold Git blob: `bb4cd0ff02159ecffe276022cec9d292c7a434a3`.
- Verified cardinalities: 360 cases, 72 CRN comparison groups, 24 analysis cells, five aerosol states, seven preregistered contrasts.
- Recovery provenance explicitly records: `scientificCaseExecutionPerformed=false`, `solverExecutionPerformed=false`, `githubRerun=false`, `retryPerformed=false`, `resumePerformed=false`.

## Preregistered result universe

No new inferential statistics, weighted pooling, p-values, confidence intervals, epsilon substitution, post-result threshold changes, or universal Sun-depression-to-clock-minute conversion were introduced after result opening. The sign inventories below are descriptive summaries of the already-preregistered cellwise contrasts, not pooled estimators.

- Scalar preregistered rows: `504/504` = 24 cells × 3 primary channels × 7 contrasts; all `FINITE_THREE_REPLICATES`.
- Level-B preregistered rows: `168/168` = 24 cells × 7 contrasts; all `FINITE_THREE_REPLICATES`.
- Spectral cell/contrast rows: `168/168`.
- Spectral rows with one or more unresolved wavelength nodes: `24/168`.
- Total unresolved spectral nodes: `1,026`.
- Every unresolved spectral node occurs at Sun depression `8°`; there are no unresolved spectral nodes at `2°`, `4°`, or `6°`.
- The affected 8° cells are only the cross-solar and opposite-solar geometries at AOD550 `0.1` and/or `0.3`; the near-solar 8° cells have no unresolved spectral nodes.
- Epsilon substitution: **none**.

The scalar contrast values are paired natural-log radiance ratios (`alternative/reference`). The Level-B values are paired limiting-V-magnitude deltas (`alternative - reference`) from the separately byte-bound Crumey full-branch human-threshold implementation.

## Frozen scientific findings

### 1. Priority particle-shape contrast is strongly context-dependent

The preregistered priority contrast is `desert_spheroids_vs_desert`, isolating the OPAC desert particle-shape/angular-scattering change while keeping the two desert states otherwise paired as frozen by the design.

Across the 24 analysis cells, the mean paired scalar log-ratio changes sign:

- photopic luminance: 9 positive / 15 negative;
- scotopic luminance: 8 positive / 16 negative;
- Johnson-V effective radiance: 9 positive / 15 negative;
- Level-B limiting-magnitude delta: 15 positive / 9 negative.

Thus the spheroidal-vs-spherical desert phase-function effect does **not** support one global sign, one global additive correction, or one global multiplicative correction.

The geometry dependence is concrete rather than marginal:

- at Sun depression `2°`, both near-solar cells are scalar-negative, while all cross-solar and opposite-solar cells are scalar-positive in all three primary channels;
- at `8°`, five of six cells are scalar-negative in all three primary channels, with only the near-solar AOD550 `0.1` cell positive;
- at `4°`, some cells even change sign between scotopic and photopic/Johnson-V channels, demonstrating wavelength/channel dependence in addition to geometry dependence.

The largest-magnitude priority scalar effect on the frozen surface occurs at `8°`, opposite-solar, AOD550 `0.3`: photopic `-0.0722003`, scotopic `-0.0207465`, Johnson-V `-0.0925010`; the corresponding Level-B delta is `+0.0315376` mag. The strongest positive priority scalar cell is near `6°`, opposite-solar, AOD550 `0.1`: photopic `+0.0122431`, scotopic `+0.0140157`, Johnson-V `+0.0140438`; Level-B is `-0.008210` mag. These are cellwise preregistered effects, not universal corrections.

### 2. Realistic aerosol family choice materially changes the modeled twilight field

The frozen OPAC-family-vs-native comparisons show large, structured differences rather than equivalence to the native rural spring-summer bridge:

- `continental_vs_native`: scalar-positive in 23/24 cells in each primary channel; Level-B negative in 23/24 cells;
- `maritime_vs_native`: scalar-positive in 23/24 cells in each primary channel; Level-B negative in 23/24 cells;
- `desert_vs_native`: scalar-positive in 19/24 cells in each primary channel; Level-B negative in 18/24 cells;
- `desert_spheroids_vs_native`: scalar-positive in 18/24 cells in each primary channel; Level-B negative in 18/24 cells.

The near-uniform continental/native and maritime/native directions are strong on this frozen surface, but neither is literally universal because each has one reversed cell. The desert-family comparisons are more visibly mixed.

### 3. OPAC aerosol families are not interchangeable with one another

The preregistered OPAC-vs-OPAC contrasts likewise retain geometry dependence:

- `desert_vs_continental`: scalar-negative in 21/24 photopic cells and 22/24 scotopic/Johnson-V cells; Level-B positive in 21/24 cells;
- `maritime_vs_continental`: scalar-positive in 21/24 photopic cells and 20/24 scotopic/Johnson-V cells; Level-B negative in 21/24 cells;
- `desert_spheroids_vs_desert`: mixed sign as detailed above.

Therefore one aerosol label or one scalar asymmetry parameter cannot stand in for the wavelength-dependent phase-function/microphysical differences over the complete frozen twilight geometry.

### 4. Spectral numerical limitation is confined to the deepest tested twilight

All 1,026 unresolved wavelength nodes occur at Sun depression `8°`, distributed across 24 spectral contrast×cell rows and only four analysis cells: cross-solar AOD550 `0.1`, cross-solar AOD550 `0.3`, opposite-solar AOD550 `0.1`, and opposite-solar AOD550 `0.3`.

This boundary must remain explicit. Scalar and Level-B summaries are fully finite across all 24 cells, but the 8° full-spectrum output is not uniformly resolved at every wavelength node for every contrast. No epsilon replacement was used to hide the nonpositive/unresolved nodes.

## Scientific boundary

AFPF v1 establishes, on the preregistered MYSTIC surface, that realistic wavelength-dependent aerosol phase functions and particle-shape treatment can materially change twilight radiance and star-visibility thresholds, and that the direction and size of the effect depend on Sun depression, viewing geometry, AOD, wavelength/channel, and aerosol family.

Consequently:

- do not hard-code the AFPF endpoint effects as a universal production correction;
- do not replace the priority spheroid-vs-sphere result with one global particle-shape factor;
- do not collapse realistic aerosol families into one universal constant-`g` substitute;
- do not convert Level-B magnitude deltas into universal clock-minute shifts without an explicit date/location solar-depression rate;
- retain the 8° unresolved spectral-node boundary in any downstream use;
- ordinal-38 raw scientific case artifacts and the verified recovery artifact remain immutable.

## Provenance marker

Issue #60 terminal analysis-recovery marker:

`AFPF-V1-ANALYSIS-RECOVERY-COMPLETED ordinal=38 source_run=32672764808 recovery_run=32682787585 attempt=1 cases=360 groups=72 cells=24 contrasts=7 artifact_id=9504775903 artifact_digest=sha256:fa824ff1e693682ee5b89aa108259452823e1f8f10818d82c34f5d01ba9dac0a solver=false rerun=false retry=false resume=false`

This file is a provenance/reporting addition only. The preregistration, transport identities, scientific cases, seeds, analysis algorithms, Level-B model binding, and verified result artifact are unchanged.
