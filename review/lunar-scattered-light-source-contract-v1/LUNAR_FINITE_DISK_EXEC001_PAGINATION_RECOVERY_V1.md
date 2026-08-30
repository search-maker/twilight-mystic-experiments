# Lunar finite-disk exec001 pagination recovery v1

Status: `PREREGISTERED_SOLVER_FREE_RECOVERY_AFTER_PRE_SOLVER_CONTROL_FAILURE`

This document freezes the recovery boundary after the first one-shot 550 nm finite-lunar-disk execution identity failed in its snapshot-fence release control before any solver-bearing shard could start. It does not reinterpret or tune any lunar radiance result because no finite-disk scientific output exists from the consumed execution.

## 1. Immutable consumed execution evidence

- consumed workflow run: `33303099872`, attempt 1 only;
- execution head: `b73d5cf4a58aee3b3e8794b396b79bbd3463f680`;
- execution branch: `execution/lunar-finite-disk-transfer-kernel-sensitivity-v1-exec001`;
- authorization head: `72916c8c98cba2454c73e09b30915be3af609a07`;
- final preflight job: `99234734783`, conclusion `success`;
- final preflight artifact: `9729769639`;
- final preflight artifact digest: `sha256:50b9acdf55ebe3188a3f7762c79e0365a9b5c58d5bf2c1b877244b340c9773b8`;
- final preflight status: `PASS_LUNAR_FINITE_DISK_EXEC001_FINAL_PREFLIGHT_GLOBAL_SCAN_NO_SOLVER`;
- snapshot-fence release job: `99236492237`;
- WRITE_QUIET BEGIN comment: `5467776090`;
- machine-readable matching END comment: `5467875147`.

The immutable final preflight established that the then-frozen 198 replacement candidates were collision-free in the exact tracked tree and repository-global surface immediately before solver authorization. It explicitly performed no libRadtran/MYSTIC runtime, consumed no scientific case result, and opened no finite-disk output.

## 2. Terminal control defect

The consumed execution workflow implemented its read-only fence release with the single request:

`https://api.github.com/repos/${repo}/issues/60/comments?per_page=100`

and did not follow pagination. Issue #60 already contains more than 600 comments, and GitHub returns the oldest comments on the first page. Therefore the current WRITE_QUIET END comments are unreachable to that frozen barrier even though the correct release exists in the authoritative ledger.

This is classified as:

`EXEC001_CONSUMED_PRE_SOLVER_SNAPSHOT_BARRIER_PAGINATION_FAILURE`

It is an execution-control failure, not a finite-disk scientific failure and not evidence for or against the central-collimated approximation.

## 3. One-use boundary

Run `33303099872` is consumed. It MUST NOT be GitHub Re-run, retried, resumed, or otherwise reused. Branch/execution identity `lunar-finite-disk-transfer-kernel-sensitivity-v1-exec001` MUST NOT be treated as a fresh one-shot identity.

Even though no solver-bearing shard started and the old candidates were not scientifically consumed, the recovery MUST conservatively use a fresh candidate-seed universe and a fresh repository-global freshness/authorization chain. This prevents any ambiguity about disclosure/reservation or one-use semantics.

No old replacement candidate may silently become the recovery candidate merely because the first run failed before solver execution.

## 4. Scientific design remains frozen

The recovery does not change the already-reviewed finite-disk sensitivity experiment:

- wavelength: 550 nm;
- six frozen Moon/target/elevation geometries;
- 33 source directions per geometry;
- 198 directional cases total;
- physical lunar angular radius derived from the frozen 384400 km observer-Moon distance and 1737.4 km lunar reference radius;
- 5,000,000 photon histories per directional case;
- full disk-integrated frozen ROLO irradiance used only as a transfer-kernel source probe;
- target remains fixed in the original Moon-center frame;
- no resolved lunar surface brightness weights are admitted;
- no extra lunar solid-angle multiplication is admitted;
- the 550 nm evaluator remains descriptive: center/min/max/ringwise response plus its already-frozen Monte-Carlo-expanded descriptive envelope;
- no result-dependent point-source adequacy threshold may be introduced after opening the 550 nm result;
- the 450/650/750 nm follow-on remains mandatory for all six geometries before any broadband finite-disk adequacy claim.

No Taylor or Jerusalem residual may be used to choose geometry, source weights, thresholds, seeds, or recovery logic.

## 5. Required corrected snapshot-fence semantics

A replacement execution may be authorized only after a solver-free review proves all of the following:

1. the release scanner enumerates **all** Issue #60 comment pages, not only the first page;
2. the implementation uses an auditable full-pagination mechanism, for example `gh api --paginate --slurp "repos/$GITHUB_REPOSITORY/issues/60/comments?per_page=100"`, followed by explicit page flattening;
3. a regression check proves that the exact historical machine-readable END `5467875147`, which is beyond page 1, is absent from the first-page-only result and present in the fully paginated result;
4. matching requires the exact recovery BEGIN comment id, exact execution head, exact workflow run id, and exact recovery marker;
5. malformed, mismatched, duplicate-ambiguous, or absent matching END fails closed before any solver-bearing job;
6. every solver-bearing job depends on the release barrier;
7. the release barrier itself has no scientific runtime and cannot produce or inspect lunar radiance results;
8. the short-lived WRITE_QUIET fence is closed only after the final repository-global candidate scan has reached its immutable terminal guard state; the solver remains blocked until the matching END is observable through the fully paginated reader.

## 6. Fresh recovery identity and seed chain

Before any replacement solver run:

- create a new review/authorization lineage; do not mutate the consumed execution branch into a replacement;
- dynamically choose a fresh one-shot execution identity (nominally a new `exec002`-class identity, but the exact unused identity must be verified at authorization time rather than inferred from naming alone);
- generate a fresh candidate-seed universe without publishing candidate literals before the freshness proof policy permits it;
- perform exact tracked-tree and repository-global collision scans under the same or stricter exclusion policy as the consumed preflight;
- bind the candidate canonical hash, row hash, authorization head, runtime identity, and preflight artifact before solver execution;
- perform a final pre-solver repository-global recheck under a fresh WRITE_QUIET snapshot fence;
- no GitHub Re-run/retry/resume is permitted for the replacement scientific workflow either.

The recovery may not treat the old preflight PASS as freshness evidence for newly generated recovery candidates. It may be retained only as immutable evidence that exec001 itself failed after its seed/global preflight and before solver execution.

## 7. Result-opening and claim boundary

This recovery protocol performs no uvspec/libRadtran/MYSTIC calculation and opens no finite-disk result.

A future replacement execution may open results only through the already-frozen finite-disk evaluator after all case shards complete and immutable artifacts are bound. Any execution-control failure before solver remains a control failure; it must not be converted into a scientific pass/fail.

At every recovery stage:

- `finiteDiskAdequacyValidated=false`;
- `atmosphericScatteredMoonlightValidated=false`;
- `roloAbsoluteSourceValidated=false` unless separately established by its own source-validation lane;
- `physicalTotalSkyValidated=false`;
- `productionAuthorized=false`.

## 8. Exact next action

Run the solver-free recovery review that (a) re-verifies the immutable exec001 preflight/control failure, (b) proves the page-1 versus fully paginated Issue #60 regression on the already-existing END, (c) verifies this protocol contains no scientific runtime or result-opening surface, and (d) emits a review receipt. Only after that review passes may a separate fresh-seed/fresh-identity recovery authorization be constructed.
