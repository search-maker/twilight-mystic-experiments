# AOPS v1 ordinal-37 analysis-only recovery control

Status: **review-only / zero solver / zero result opening**.

The AOPS v1 scientific identity is already spent. Source run `32624595188`, attempt 1, exact head `a1895adebf39a5c2c12d80276a119e032fdf090b`, executed the preregistered 360-case matrix successfully. The overall workflow is terminal FAILURE because the aggregate job later attempted to fetch the frozen `starsvisibility` human-threshold module through a cross-repository `GITHUB_TOKEN` API request and received HTTP 404 before Level-B propagation and final analysis-artifact persistence.

That infrastructure failure does **not** authorize another MYSTIC execution. The 360 case artifacts are immutable scientific evidence from ordinal 37 and are the only allowed scientific input to this recovery.

## Exact source identity

- scientific stage: `aerosol-optical-property-sensitivity-v1`
- scientific ordinal: 37
- source workflow run: `32624595188`
- source attempt: 1
- event: `workflow_dispatch`
- source branch: `dispatch/aerosol-optical-property-sensitivity-v1-ordinal-37`
- source head: `a1895adebf39a5c2c12d80276a119e032fdf090b`
- source workflow: `.github/workflows/aops-v1-execution.yml`, Git blob `5fcd451a08462e44bb5d6d72578c8d6620490174`
- source case artifacts: exactly 360 unique unexpired artifacts whose names begin `aops-v1-case-`

No GitHub Re-run, retry, resume, new seed, new case, new ordinal, solver call, or changed scientific design is permitted.

## Recovery is analysis-only

A later reviewed recovery workflow may do only the work that the original aggregate job intended after the cases already existed:

1. enumerate the immutable artifacts of source run `32624595188` and require exactly 360 unique, unexpired `aops-v1-case-*` artifacts;
2. download those exact source-run artifacts and nothing from a newer science run;
3. run the exact frozen `aggregate_results.py` bytes to produce acquisition, scalar and spectral results;
4. fetch the exact frozen public `human-threshold.mjs` bytes from `search-maker/starsvisibility@a422afe5fc4197ab15323bafb15512001e061454` without depending on cross-repository `GITHUB_TOKEN` authorization;
5. verify Git blob SHA-1 `bb4cd0ff02159ecffe276022cec9d292c7a434a3` before use;
6. run the exact frozen Level-B driver with field factor 3.14/full as already preregistered;
7. upload one immutable recovery artifact containing the source artifact metadata plus acquisition/scalar/spectral/Level-B outputs and threshold identity.

The recovery workflow itself must have a new *analysis-recovery* identity, but this is not a new scientific ordinal. Its attempt must be 1 and it may not execute MYSTIC/libRadtran.

## Frozen analysis bytes

The recovery is bound to the scientific bytes that the source run used:

- `aggregate_results.py` — `28ff3f4ea4b6c8e457b30abd234ecb8c4669cbd9`
- `level_b_driver.mjs` — `0dda1975a87f379aa3faeac11559a2e4df258821`
- `level_b_analysis.mjs` — `5dd88576b11a4de51b160935036bde162c94e2c8`
- `analysis-contract.v1.json` — `9be70a7ad33bf4ca166631afadc45e594fe9bd65`
- `protocol.review.json` — `2dc43347482dc629a10f08c978b4278d1ac680d6`
- `execution-contract.review.json` — `23e494aa054425a236abf9b322180fe5576a7d5b`

The source-run checkout and current main contain the same listed analysis blobs; the future recovery must explicitly checkout or otherwise bind the source bytes rather than silently consuming later analysis edits.

## Expected complete outputs

The frozen original workflow required:

- acquisition status `COMPLETE_EXACT_360_CASE_ARTIFACT_UNIVERSE`, count 360;
- scalar status `COMPLETED_PREREGISTERED_AOPS_V1_ANALYSIS`, 24 analysis cells and 72 comparison groups;
- spectral status `COMPLETED_PREREGISTERED_AOPS_V1_SPECTRAL_ANALYSIS`, 24 cells;
- Level-B status `COMPLETED_PREREGISTERED_AOPS_V1_LEVEL_B`, 360 cases, 24 cells, 9 contrasts per cell.

If any of these invariants fail, recovery fails closed. Partial recovery must not be interpreted scientifically.

## Interpretation boundary

Even a successful recovery does not authorize:

- changing endpoints, contrasts, thresholds or statistical rules after seeing recovered values;
- epsilon substitution, p-values or confidence intervals absent from the frozen contract;
- fitting or choosing an atmosphere/observer mapping from Taylor or Jerusalem residuals;
- inventing a universal magnitude or clock-minute correction;
- production activation.

After a complete recovery artifact exists and its identities are independently verified, the recovered AOPS sensitivity may be interpreted together with AVPS v2 and ASIV only within their preregistered boundaries to design a separately reviewed component-selective Level-B shadow mapper.
