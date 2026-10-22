# AVPS v1 post-exact360 aggregation/opening protocol

Status: **REVIEW ONLY / INACTIVE / RESULTS MUST REMAIN CLOSED UNTIL EXACT360 METADATA GATE**

This protocol is frozen while recovery workflow run `33139545997` is still executing and before any AVPS case artifact content is opened. It defines what may happen after the recovery workflow itself emits the exact-360 metadata-only freeze artifact.

## Bound scientific identity

- repository: `search-maker/twilight-mystic-experiments`
- frozen main / authorization parent: `99ade7798627e67921139697ba1a004fa8a304bb`
- authorization PR: #565
- authorization head: `338ee82c8e088e929f45782b1f7ac1c3aaaaa533`
- scientific ordinal: `40`
- failed original science workflow run: `33137514692`
- executor-recovery review PR: #576
- recovery review head: `9d6f98eeef858e81cb644990ef6b1659083bca0c`
- active recovery workflow run: `33139545997`
- recovery request head: `6d0e0e0f1dd1deabaf8bb155ee7e323c5ba8673d`
- original authorized executor blob: `68eb7f6916bae204e60f6a378eae25f9c2bff184`
- recovery executor blob: `3580f7eff61ab06d0b4a7041f7907d871d961b5b`
- frozen aggregator blob: `1f36fc95347b84623db9b77005907929389dc7e8`
- frozen result-opening blob: `4a6842e83cbd1525bf603c5e09e92317a63b6af9`
- frozen analysis blob: `dd2b7fb9cd4cc660338f1694841a0be5b4bf4a4d`
- frozen Level-B analysis blob: `bab47e25b8903be645ed254a4207e2372b5e7853`
- frozen Level-B runner blob: `f199d12dfe856f030dc71055c24bb9188c04d5c5`

No source above may be silently replaced after results are available.

## Gate 0 - recovery workflow must finish by itself

Do not download any `avps-v1-case-*` artifact before all of the following are true:

1. recovery run `33139545997` is terminal `completed/success`, `run_attempt=1`;
2. preflight is `success`;
3. all four matrix shards (`dep2`, `dep4`, `dep6`, `dep8`) are `success`;
4. no GitHub rerun/retry/resume has occurred;
5. workflow-produced artifact `avps-v1-stage-b-executor-recovery-exact360-metadata` exists exactly once and is unexpired;
6. that metadata artifact is the only artifact whose content may be downloaded at Gate 0.

The metadata payload must say exactly:

- `status = EXACT360_RAW_RECOVERY_ARTIFACT_METADATA_FROZEN_RESULTS_UNOPENED`
- `workflowRunId = 33139545997`
- `recoveryOfWorkflowRunId = 33137514692`
- `caseArtifactCount = 360`
- exactly 360 unique case artifact names equal the authorized universe
- `caseContentsDownloaded = false`
- `aggregateResultsCalled = false`
- `openResultsCalled = false`
- `scientificInterpretationPerformed = false`

A later activation request must bind the exact Gate-0 metadata artifact ID and digest. They are intentionally unknown at this preregistration checkpoint and must not be guessed.

## Phase A - exact acquisition and aggregate verification, results still closed

Only after a separately reviewed activation binds the Gate-0 artifact ID/digest may Phase A download the 360 case artifacts.

Before invoking the frozen aggregator, the wrapper must independently verify for **every** case:

### Exact artifact universe

- artifact name is one of the exact 360 names listed in Gate-0 metadata;
- artifact ID, digest and size equal Gate-0 metadata;
- no duplicate/missing/extra case;
- no expired artifact;
- source workflow run ID is `33139545997`.

### Recovery provenance

The frozen aggregator predates the transport recovery and therefore does not itself require all recovery-specific fields. The Phase-A wrapper must require them explicitly before calling it:

- `transportRecovery = true`
- `recoveryOfWorkflowRunId = 33137514692`
- `recoveryReason = EMPTY_DIAGNOSTIC_STREAM_ARTIFACT_CONTRACT_ONLY`
- `authorizedOriginalExecutorGitBlobSha1 = 68eb7f6916bae204e60f6a378eae25f9c2bff184`
- `recoveryExecutorGitBlobSha1 = 3580f7eff61ab06d0b4a7041f7907d871d961b5b`
- `scientificInputsChangedByRecovery = false`
- `seedAllocationChangedByRecovery = false`
- `caseUniverseChangedByRecovery = false`
- `runtimeIdentityChangedByRecovery = false`
- `resultOpeningAuthorizedByRecovery = false`
- `retryPerformed = false`
- `resumePerformed = false`
- `githubRerun = false`
- `workflowRunAttempt = 1`
- `workflowRunId = 33139545997`
- `scientificOrdinal = 40`

The four diagnostic stream members may be zero bytes only because the reviewed recovery permits that exact set:

- `syntax-stdout.txt`
- `syntax-stderr.txt`
- `solver-stdout.txt`
- `solver-stderr.txt`

All scientific/raw members remain required and non-empty as enforced by the recovered executor. The wrapper must not fabricate placeholder bytes for diagnostic streams.

### Frozen aggregate verification

After the recovery-provenance precheck passes for all 360 artifacts, call the frozen `aggregate_results.py` exactly once. It must independently reverify:

- authorization universe/cardinality;
- case static identities and seeds;
- exact workflow/ordinal/attempt identity;
- no retry/resume/rerun;
- execution-contract/design/profile/runtime identities;
- raw-member SHA-256 maps;
- exact AFGL profile hashes;
- exact radiance/std spectral grids;
- recomputation of frozen derived channels;
- exact 360 cases / 72 CRN groups / 24 analysis cells / 5 states per group / 3 replicates.

Phase A may emit only the frozen aggregator's verified analysis-input payload and acquisition audit. It must retain the status that source acquisition is complete while **results are still closed**. No prose or numerical interpretation is permitted at Phase A.

If any identity/hash/cardinality check fails, stop. Do not repair, impute, substitute epsilon, omit a case or continue with a partial universe.

## Phase B - preregistered primary result opening

Only a separately reviewed Phase-B activation may call frozen `open_results.py`, and only on the exact self-hashed Phase-A analysis input.

The frozen opening must retain these policies:

- exact 360 cases;
- exact 72 CRN groups;
- exact 24 analysis cells;
- exact 5 states per group;
- exactly 4 primary alternative-vs-reference contrasts per cell;
- primary channels exactly as frozen by the experiment;
- no p-values;
- no confidence intervals;
- no epsilon substitution;
- no universal conversion of solar-depression difference to minutes;
- no production materiality threshold created from the result;
- no Taylor scoring;
- no Jerusalem observational scoring.

Primary output status must remain the frozen `COMPLETED_PREREGISTERED_AVPS_V1_PRIMARY_ANALYSIS_AFTER_EXACT_360_GATE` contract.

## Phase C - Level-B impact mapping remains shadow-only

Direct MYSTIC profile sensitivity and fast Level-B consumption are separate questions. Any Level-B mapping after the primary MYSTIC analysis must use the already frozen Level-B analysis/runner bytes or a separately reviewed replacement.

Phase C may quantify shadow impact on the star-visibility boundary, but:

- must not choose or tune a mapping from Taylor/Jerusalem residuals;
- must keep the richer vertical aerosol state separate from the current v1 projection until a validated fast mapping exists;
- must report approximation/consumption provenance explicitly;
- must not activate production routing;
- must not turn a diagnostic sensitivity magnitude into a fitted correction.

## Interpretation order frozen before results

When Phase B is eventually opened, interpret in this order only:

1. execution/identity completeness;
2. Monte-Carlo/numerical diagnostics already frozen in the analysis implementation;
3. sign and magnitude of the four preregistered vertical-profile contrasts across the 24 cells and three primary channels;
4. dependence on solar depression, AOD and geometry;
5. replicate consistency;
6. only afterwards, if justified, compare the size of the environmental sensitivity to previously frozen model/observational uncertainty scales.

Do **not** first inspect Taylor residual directions and then decide which profile contrast is relevant.

## Hard boundary

This PR/protocol does not itself download any AVPS case artifact, call the aggregator, call `open_results.py`, open a radiance value, or authorize production. It exists specifically to ensure the post-360 procedure is fixed before the result is seen.
