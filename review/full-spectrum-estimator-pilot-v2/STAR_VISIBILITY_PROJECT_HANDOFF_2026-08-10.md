# Star Visibility Project — handoff for a new scientific/engineering owner

**Snapshot date:** 2026-08-10 (America/New_York)  
**Primary objective:** build the most accurate realistically achievable predictor of **naked-eye first visibility of a star during twilight**, while reporting uncertainty honestly and never hiding model limitations behind a single over-precise time.

This document is intended for a new worker who has no prior context. Read it before changing code, opening validation data, or launching new MYSTIC runs.

---


## 0. Critical 2026-08-10 status update — read before older chronology

The full-spectrum salvage audit is now **complete**, so any earlier section that says “acquire the remaining artifacts” is superseded by this update.

- all **166/166** immutable training case artifacts are locally transport-bound and verified against GitHub artifact digests;
- all **39/39** training geometries have been re-integrated from preserved raw spectra into full photopic, full scotopic and Johnson-V channels;
- complete source identities: acquisition manifest `6cc7c93a395b8e4a42ba31d38c7a7d1fb8cf54b0993b80dbb652d29e73a04539`, training dataset `42478d099efea7392f5558716571400dc84ee28de5df1e22f85e8031d2138c41`, admission report `a043fa6c0a5e7ec282d887a4febe01277e0a0a20c82bff65ccb127705b40e0cf`;
- the unchanged full-channel precision gate classifies **24 eligible**, **2 continuation-required** (`train-0014`, `train-0037`) and **13 precision-exhausted** (`0003,0007,0011,0013,0019,0023,0027,0029,0031,0039,0041,0043,0047`);
- `train-0039` and `train-0047` contain preserved exact zero-hit evidence; never replace those zeros with epsilon;
- the large deep-twilight photopic noise is not caused by switching from the old 15-node photopic integral to the full-spectrum integral: their block RSEMs are nearly the same. The dominant issue is Monte-Carlo variance; scotopic additionally exposes target-specific underprecision at `0014` and `0037`;
- a complete descriptive geometry diagnostic finds solar depression overwhelmingly associated with numerical noise (Spearman about `0.9495` with log maximum primary-channel RSEM), but this is descriptive because historical continuation/block count was adaptive;
- **do not fit a new full-spectrum surrogate yet**. Fifteen of 39 training geometries are not full-channel eligible. Do not discard them and do not relax the 8% gate.

A review-only estimator-method pilot is frozen **before any new solver result exists**. The acquisition protocol is `public-tier1-full-spectrum-estimator-pilot-v2`, SHA-256 `7ca0923204452ab203249dfd060dd5fef5465c48a20ba529c0a20748e0152434`. The acquisition design remains exactly 44 proposed fresh cases / 5.6B configured photon histories over nine training-only representative geometries, using fresh seeds 970001-970044. It compares alternate ALIS importance centers from `{500,550,600}` nm against immutable historical evidence and adds 1-nm conventional VROOM diagnostics on four representative geometries. No execution, continuation, fitting, validation opening or production action is authorized.

The initial published review package was opened as Draft PR #109 at commit `bcf815961b3dce7357479662e02f709cbb3cba3e`. Independent review found a **pre-result P0 statistical defect** in analyzer v4: fresh two-block RSEM was compared against historical RSEM after an adaptive 2/4/6/8 blocks. Those are not like-for-like because RSEM mechanically falls with block count. For example, `train-0041` has roughly 40.95% maximum primary-channel RSEM over historical blocks 1-2 but roughly 8.87% after all eight blocks. A fresh 10% two-block method would therefore be a large same-n improvement yet the v4 rule could reject it. No pilot result had been opened, so the analysis was corrected before execution rather than tuned after seeing data.

The replacement screening-analysis protocol is `public-tier1-full-spectrum-estimator-pilot-screening-analysis-v4`, SHA-256 `ad847ecb7f46629787148c572fe0e6d6d26c7eda12837d74de00b28abb64de6f`. It freezes the historical **first two blocks** for every selected geometry/channel and evaluates descriptive variance gain with `(freshTwoBlockRsem / historicalFirstTwoBlockRsem)^2`. Because historical b1/b2 and fresh screening cases use the same two-block count and the same per-block photon histories for every selected geometry, this is a like-for-like nominal variance-efficiency screen. A ratio <=0.5 on every finite historical problem channel is only a screening signal; it is not an inferential claim and still requires four fresh independent confirmation blocks under a separately preregistered confirmation. Full adaptive historical RSEM is context only and is forbidden in the variance-gain threshold.

The VROOM 1-nm grid was selected only after a 166-spectrum quadrature audit: worst observed integration loss versus the raw 0.05-nm spectra is about 0.112% photopic, 0.203% scotopic and 0.186% Johnson-V. This makes quadrature error small relative to the historical 5%/8% block-precision gates.

Independent review also found two additional pre-result blockers at the original PR #109 head. First, analyzer v4 treated a case as zero-hit only when all three derived primary channels were exactly zero; screening v4/analyzer v6 now treats an exact zero in **any** primary channel as a fail-closed candidate blocker. Second, the earlier preauthorization guard checked the pilot execution key and exact branch names but did not independently require a fresh global-ordinal check; preauthorization v4 now requires ordinal 14 to remain the next unused global scientific ordinal immediately before authorization.

The original repository Actions check was green but did not execute the review-directory tests because `.github/workflows/contract.yml` discovered only `tests/`. The corrected publication must add an explicit review-package step that runs `review/full-spectrum-estimator-pilot-v2/run_review_checks.py`. The runner freezes seven exact test modules and currently requires **39/39** tests plus compile success. A green generic repository contract check without this exact review-package step is not sufficient evidence for authorization.

The review package is also being hardened for repository portability. Historical preparation scripts that depended on worker-local `/mnt/data` inputs are preserved under `reference/historical-nonportable/` and are not active builders. Current frozen evidence is checked by repository-relative verifier scripts. The active preauthorization contract is v4, SHA-256 `bb9150f573f20ed0f9daf140f2941e6034876b8d51143ff42ffc001fc5335276`; it binds analyzer v6, the screening-analysis v4 protocol, the exact repository-relative review-check runner, and fresh global-ordinal checks. Candidate ordinal 14 remains review-only, not reserved, not authorized and not consumed. The guard now refuses authorization if ordinal 14 has been reserved/authorized/consumed on any reviewed execution surface or if the latest consumed global ordinal is no longer 13.

The exact next engineering step is **not a MYSTIC dispatch and not a merge of the old PR #109 head**. First publish and independently verify the corrected review package on the same Draft PR, rerun safe static/unit CI, and re-review the exact package bytes. Only after a fresh live-main/control-ledger/seed/run/artifact collision check may a separate one-file authorization even be considered.

---
## 1. What the product is trying to predict

The user-facing problem is not merely “sky brightness.” The final system must predict, for a specified observer/site/date/star:

- first naked-eye detection after sunset, or last detection before sunrise;
- potentially more than one visibility window if the star is setting while the sky is darkening;
- a time/depression **distribution or uncertainty window**, not false exact-second certainty;
- explicit out-of-domain / poor-atmosphere-data flags.

The end-to-end chain is:

1. astronomical geometry;
2. directional twilight sky spectral radiance;
3. same-atmosphere stellar transmission/extinction;
4. stellar spectral energy distribution and apparent point-source signal;
5. human visual threshold/adaptation/search protocol;
6. chronological event solver;
7. uncertainty propagation and calibration against real observations.

The project must keep three validation questions separate:

1. **Surrogate vs MYSTIC:** does a fast model reproduce the radiative-transfer solver?
2. **MYSTIC/atmosphere vs real sky:** does the physical atmospheric model reproduce measured directional spectral/photopic/scotopic sky brightness?
3. **End-to-end star visibility vs humans:** does sky + star + eye model predict real first-seeing events?

Passing #1 never proves #2 or #3.

---

## 2. Repository split — do not duplicate these responsibilities again

### A. Public scientific execution repository

`search-maker/twilight-mystic-experiments`

**Role:** source of truth for libRadtran/MYSTIC experiments, immutable raw evidence, execution authorization, provenance/audits, surrogate datasets, model training experiments and computational validation.

Current verified public `main` at this snapshot:

`ae81798f538899b09b6c03c3d6e90ab93458427c`

Issue **#60** is the authoritative control ledger. Current authoritative directive remains **MYSTIC-STATE-0066**; no 0067 was found on the latest refresh.

### B. Application / star-visibility repository

`search-maker/starsvisibility`

**Role:** source of truth for stellar catalog/SED handling, stellar transmission, human point-source threshold, observer model, chronological visibility event solver, uncertainty presentation and the production/web application.

Scientific PR **#24**, `science/visibility-v3-blackwell-crumey`, is still open/draft/mergeable. Current verified head at this snapshot:

`805937bab0e42755a02d709b2c5a0cba43f616e9`

**Important consolidation decision:** do not keep building a second MYSTIC execution/training engine inside `starsvisibility`. Port useful scientific ideas to the public MYSTIC repository and make the application consume a verified model/package from there.

---

## 3. What was wrong with the original production-style model

The original calculator had broadly reasonable geometry, but the largest scientific uncertainties were in twilight sky brightness, atmospheric extinction, color/mesopic response and observer physiology/adaptation.

Known issues found during review:

- the old twilight curve was a calibration curve, not a physically validated directional dataset;
- the old limiting-magnitude/observer corrections were heuristic;
- a B-V/Purkinje color correction was heuristic rather than spectral;
- scalar extinction used `kV * max(0, X-1)` even though standard Johnson-V catalog magnitudes are effectively zero-airmass references; that convention made stars artificially too bright and could move timing earlier by minutes;
- a hard empirical minimum solar depression of 2.5 deg conflicted with expert observations of very bright stars;
- expert Jerusalem observations often showed the program predicting first visibility later than the real observation by roughly a degree or more of solar depression;
- a single monotonic root assumption was unsafe because a star can set while twilight darkens.

The production UI/default model has intentionally not been switched to unvalidated scientific work.

---

## 4. Human-vision / star-signal work already done in `starsvisibility` PR #24

The private scientific branch contains important work that should be retained on the application side:

- Crumey/Blackwell point-source threshold implementation;
- field-factor based observer criteria rather than arbitrary additive “expert magnitude bonuses”;
- a calibration primitive for estimating an equivalent observer field factor from real first-seeing events;
- explicit warning that Crumey-vs-Tousey/Koomen Table I agreement is **source-family consistency**, not independent human validation;
- same-atmosphere stellar direct transmission work;
- stellar SED contract work (empirical-template direction, not a production blackbody fallback);
- audit of catalog magnitude/extinction reference conventions;
- separation of sky physics, stellar extinction, eye threshold and color/mesopic terms;
- chronological event-solving design that scans time/depression, brackets all sign changes and preserves multiple visibility windows/censoring;
- uncertainty-envelope event solver that can report earliest possible/latest guaranteed under supplied physical bounds without inventing a probability distribution.

### Still required on the human side

The final eye model should be probabilistic and protocol-specific, approximately:

`P(detection | star signal, sky field, adaptation, observer, search protocol)`

It still needs real data for:

- known-position vs search tasks;
- 50% forced-choice vs 90% confident vs “first conscious seen” definitions;
- adaptation field and time history;
- direct/averted vision, binocular use, search time and false positives;
- observer/session random effects;
- expert-observer calibration without arbitrary fixed bonuses.

Human datasets must be split by night/site/observer where possible and must include non-detections/catch trials.

---

## 5. Public MYSTIC Tier-1 evidence that already exists

### Original ordinal-2 source

Scientific run `30952457327` created 96 case artifacts = 48 geometries x b1/b2.

The corrected interpretation distinguishes:

- `executionComplete`: solver/parser produced valid finite output, including a legitimate zero Monte-Carlo estimate;
- `scientificallyEligible`: numerical precision is good enough for the intended scientific use.

The original postprocessing failure did **not** mean the 96 simulations failed. A complete immutable 99-artifact inventory was later committed at:

`evidence/ordinal2-run-30952457327-artifact-manifest.json`

It records artifact ID, name, GitHub digest, downloaded-byte SHA-256, size and case identity. One original block, `train-0047-alis-b1`, was a real all-zero Monte-Carlo estimate and must not be replaced by epsilon.

### Precision-continuation contract

The previously frozen public precision rules are:

- target RSEM: **5%**;
- accepted maximum RSEM: **8%**;
- audited stopping points at 2/4/6/8 blocks;
- zero-hit => no ordinary RSEM calculation; continue if allowed, otherwise exhausted/ineligible.

Continuation runs:

- ordinal 11 / wave 1: run `31052639692`, b3-b4;
- ordinal 12 / wave 2: run `31065046524`, b5-b6;
- ordinal 13 / wave 3: run `31070968611`, b7-b8; this is terminal (no wave after b8).

---

## 6. Existing exploratory photopic surrogate models — useful history, not the final physical target

An isolated branch stack in the public repository trained exploratory photopic models on 39 training records.

### Exploratory v1

The one-time nine-geometry internal holdout was opened exactly once. v1 **failed generalization**:

- mean absolute log error ~0.44373, above allowed ~0.41518;
- 7/9 within factor two;
- all 9 holdout points were outside its training-normalization domain;
- largest errors included `train-0045` (~3.99x) and `train-0030` (~2.91x).

That holdout is now permanently opened and cannot be reused for future model selection/tuning.

### Exploratory v2

A new model v2 was selected using only the 39 training records, not the opened v1 holdout. It used a poly2-cos basis with ridge 0.001 and later **passed a separately frozen, one-time external computational-anchor validation** on five hard anchors.

This is valuable evidence that the geometry/model family can reproduce independent MYSTIC-derived computational anchors.

**However:** it is not observational validation and it is not the final target model, because a major target-definition problem was found afterward.

---

## 7. Critical discovery: the old “photopic” training target discarded a large fraction of the spectrum

The raw Tier-1 ALIS artifacts contain full 380-780 nm radiance spectra (about 8,001 wavelength samples), but the historical photopic target used only 15 selected nodes, roughly 470-660 nm.

A 12-block audit across different geometries/seeds found:

- the old 15-node photopic target captured only about **75.78%-77.55%** of the full photopic integral;
- equivalently the old target was low by roughly **0.276-0.301 mag**;
- a 41-node 10-nm integration reproduced the raw full-spectrum photopic integral to roughly **0.25%-0.37%**.

Therefore the raw MYSTIC simulations are substantially more informative than the target on which the old photopic surrogate was trained.

**Consequence:** do not throw away the raw runs and do not rerun MYSTIC just to fix photopic integration. Re-integrate the existing spectra first.

The new primary derived channels are:

1. full photopic luminance;
2. full scotopic luminance;
3. Johnson-V relative radiance;
4. S/P ratio derived exactly from scotopic/photopic, not fitted independently.

---

## 8. Full-spectrum salvage path now frozen locally

The training-only source ledger is:

`/mnt/data/full-spectrum-training-source-ledger-v2.json`

It contains exactly:

- **166 training case artifacts**;
- **39 training geometries**;
- block distribution: 22 x 2 blocks, 3 x 4 blocks, 1 x 6 blocks, 13 x 8 blocks;
- nine historical internal-holdout geometries excluded from this training ledger.

Key local contracts/tools:

- `full-spectrum-derived-channel-handoff-protocol-v2.json`
- `build_full_spectrum_training_handoff_v2.py`
- `full-spectrum-training-admission-gate-v1.json`
- `build_full_spectrum_training_admission_gate_v1.py`
- `full-spectrum-ordinal11-transport-resolution-v1.json`
- `full-spectrum-deferred-transport-resolution-v1.json`
- `full-spectrum-training-acquisition-readiness-v1.json`

### Provenance rule

Ordinal-11/12/13 postprocessors sometimes normalized case names/hashes. The immutable raw artifact IDs are different. Never substitute a normalized postprocessed case hash for the original `case-result.json` hash.

The v2 ledger separates:

- workflow head SHA;
- execution-source main SHA;
- authorization ref;
- raw case ID/hash;
- normalized audit hash as secondary evidence only.

---

## 9. Full-spectrum acquisition/audit status at this snapshot

Current acquisition-readiness SHA-256:

`956ad8eb8da08cf1a13db10862d562a396f9b3e42c7c1c03a89bfb16ff0a07a9`

Current state:

- frozen universe: **166 cases / 39 training geometries**;
- locally downloaded + transport-bound: **86 cases / 29 complete geometries**;
- still remote: **80 cases**, all belonging to the ten remaining 8-block training geometries;
- remote with exact artifact ID+GitHub digest already resolved locally: **60** continuation cases;
- remote ordinal-2 b1-b2 cases with exact run/name frozen: **20**.

All current local ZIPs were checked against the expected GitHub ZIP digest before their bytes were trusted; case-result/radiance/std-radiance identities are then verified by the handoff builder.

### Twenty-nine complete geometries already classified by the frozen multi-channel gate

Current result: **24/29 eligible**, **2 continuation-required**, **3 precision-exhausted**.

The two new full-spectrum continuation requirements are important because the historical photopic-only campaign stopped them after b1-b2:

- `train-0014` — photopic/Johnson-V RSEM about 5.3%-5.5%, but scotopic RSEM about **11.4%**;
- `train-0037` — photopic about 7.0%, Johnson-V about 6.0%, but scotopic about **15.1%**.

They therefore need fresh independent blocks under a separately preregistered continuation if the strict <=8% full-spectrum gate is retained. Existing b1-b2 evidence must remain immutable; do not simulate missing b3+ values or reuse old seeds.

Already confirmed precision-exhausted / not eligible:

- `train-0003` — 8 blocks; RSEM about 16.0% photopic/Johnson-V and 19.5% scotopic;
- `train-0007` — 8 blocks; RSEM about 41%-43% in all three channels;
- `train-0047` — 8 blocks, multiple zero-hit blocks, ordinary RSEM intentionally null.

Current partial handoff dataset SHA-256: `19cef64e28e9e4e89ab8c442096b900668e4b43e5ae333f751ea069ace81aea6`.
Current acquisition-manifest SHA-256: `4e3f1f6f2d709361fecaff84d8d186a8af0242ba631c364adf95a51c26e22094`.

### Important interpretation

Full-spectrum ALIS precision is strongly geometry-dependent. Some geometries are adequate after 2-4 blocks, while several difficult/deep geometries remain far above the 8% bound even after 8 blocks.

This means a future worker must **not simply train on all terminal means as if they were equally precise labels**.

---

## 10. Deep/rare-event problem already demonstrated

`train-0047` is the clearest example:

- 3/8 blocks are zero-hit;
- nonzero blocks differ by orders of magnitude;
- a single block contributes about 98% of the integrated signal in the diagnostic;
- effective independent-block count is only about 1.03-1.04 of 8;
- normalized spectral-shape correlations can become negative (about -0.50 in the diagnostic);
- S/P varied enormously across blocks.

`train-0007` now shows that severe underconvergence can also occur without the same zero-hit pattern: ~42% RSEM after all 8 blocks.

Therefore “just add more identical ALIS blocks” is not automatically the optimal use of compute. Before authorizing large additional runs at the difficult end of the domain, investigate estimator/variance-reduction strategy.

Existing repository infrastructure includes conventional reference/VROOM and ALIS-vs-reference diagnostics that can be reused for this purpose.

---

## 11. What must NOT be claimed at this stage

Do not say any of the following:

- “the star visibility model is validated”;
- “MYSTIC-v3 has been run” — the private v3 design was not executed as a full campaign;
- “the full-spectrum surrogate exists” — it has not yet been fitted;
- “model v2 is the final physical sky model” — it passed computational anchors for the older photopic target;
- “the internal holdout is still untouched” — the old v1 photopic holdout was opened once and failed; it cannot serve as fresh independent validation for a new full-spectrum model;
- “five external anchors prove real-sky accuracy” — they are computational MYSTIC-derived anchors, not observations;
- “train-0047 should be replaced by a tiny epsilon” — zero is valid Monte-Carlo evidence and its uncertainty must be represented honestly;
- “an expert observer gets +X magnitudes” without calibration;
- “a single crossing time is guaranteed”;
- “we know the time to the nearest second.”

---

## 12. Highest-priority roadmap from here

### P0 — finish the 166-case full-spectrum acquisition and 39-geometry admission audit

Do this before fitting anything.

For every case:

1. bind exact source run/head/authorization/artifact ID/name/GitHub digest;
2. verify downloaded ZIP digest;
3. verify the unique `case-result.json` raw SHA (when prebound) and content self-hash;
4. verify radiance and std-radiance hashes;
5. compute full photopic/scotopic/Johnson-V from the raw spectrum;
6. aggregate only complete geometry block histories;
7. classify each channel and geometry with the already frozen gate.

Current remaining remote count: **80** (ten complete 8-block geometries).

### P1 — decide how to handle exhausted/noisy full-spectrum geometries, before model fitting

After all 39 are classified, choose and preregister one of two scientifically defensible paths:

**Strict eligible-domain model:** train only on numerically eligible labels and explicitly shrink/fragment the supported domain. This is clean but may lose important deep-twilight regions.

**Uncertainty-aware model:** include noisy/exhausted labels only under a predeclared likelihood/measurement-error/censoring/noisy-label treatment using the observed block distributions. Do not invent weights after looking at holdout outcomes.

For the deepest failures, run an estimator diagnostic first (ALIS importance wavelength/design, multiple importance wavelengths if supported, conventional/VROOM cross-check, photon scaling). New compute should be targeted to uncertainty reduction, not blindly repeated.

### P2 — freeze a new full-spectrum surrogate-selection protocol before fitting

Only after P0/P1.

Requirements:

- full-spectrum targets fixed;
- input features/domain fixed;
- candidate model families and regularization fixed;
- weighting/uncertainty model fixed;
- training-only CV folds fixed;
- numerical solver for fitting stable/reproducible (QR/robust least squares preferred to unscaled normal equations);
- no use of previously opened holdout outcomes for selection.

### P3 — obtain genuinely independent validation for the new target

The old holdout/anchors were opened for the old photopic target/model history. Treat them as historical diagnostics, not fresh validation of the new full-spectrum target.

Create a new untouched computational validation set or new MYSTIC cases **after** freezing the new full-spectrum model protocol.

Then separately validate against measured sky.

### P4 — real atmospheric/sky validation

Ideal field data should include, at the same time and direction:

- calibrated spectral or multiband radiance;
- photopic/scotopic-effective brightness;
- independent AOD550 (and preferably Angstrom exponent / aerosol microphysics information);
- clouds/thin-cloud QC;
- temperature/pressure/humidity;
- observer/site elevation and horizon;
- exact sun/star geometry.

A single zenith SQM value is not enough for directional twilight validation. Historical Koomen measurements are useful diagnostics but lack matched AOD. ARM SASZE is spectrally valuable but its zenith-only geometry is outside the old 5-80 deg frozen target-altitude domain, so it was not admitted as a formal v2 holdout.

### P5 — same-atmosphere star signal

Use wavelength-resolved stellar transmission in the same atmosphere used for the sky, with empirical stellar SEDs. Correct/refine:

- zero-airmass catalog magnitude conventions;
- aerosols/extinction spectrum;
- refraction near horizon;
- variables, binaries, peculiar/reddened stars;
- planets as a separate extended-source problem.

### P6 — probabilistic human detection and end-to-end real first-seeing validation

Collect/curate observations with known protocol and non-detections. Calibrate observer/session effects, adaptation and search behavior. Then evaluate event timing with no tuning on the final test set.

### P7 — production integration

Only after sky, star and human layers have independent evidence. Production output should show median/interval/probability or quality class, atmosphere-data quality and OOD warnings, not a deceptive exact timestamp.

---

## 13. Recommended exact next engineering actions

1. Treat the **166/166, 39/39 full-spectrum audit as closed evidence**. Do not reacquire or rerun those cases unless a cryptographic/provenance defect is discovered.
2. Keep Draft PR #109 review-only. Any head that still contains analyzer v4's adaptive-history variance-gain comparison, channel-specific zero fail-open behavior, missing global-ordinal freshness checks, or CI that does not execute the exact review-package runner must not be merged or used for authorization. Publish the corrected screening-analysis v4/analyzer v6/preauthorization-v4 package and re-run only non-scientific review checks.
3. Preserve the acquisition design exactly: 44 cases, nine training geometries, 5.6B configured histories, seeds 970001-970044, the same methods/geometries/photon counts/runtime, exact zero policy, broad gross-mean ratio screen and four-fresh-block confirmation boundary. The analysis correction must not become a hidden acquisition redesign.
4. For screening variance gain, compare fresh n=2 only with the frozen historical first-two n=2 baseline at the same per-block photon count. Report final adaptive 2/4/6/8-block historical RSEM as context only. Never use it in the variance-gain threshold.
5. Keep the pilot training-only. Previously opened internal holdout values and external computational anchors are forbidden for estimator selection.
6. Immediately before any future authorization, refresh Issue #60 and live `main`, rerun repository-global key/branch/run/artifact/seed collision checks, and independently prove that global scientific ordinal 14 is still the next unused ordinal with zero reservation/authorization/run/terminal-artifact evidence. Candidate ordinal 14 is not reserved by the review package.
7. If screening nominates a method, preregister a separate confirmation before opening confirmation values. Use exactly four fresh independent confirmation blocks; screening blocks may not enter the final confirmation precision gate.
8. If severe/zero-hit cases remain unstable, do not brute-force hundreds of identical blocks. Diagnose the estimator/rare-event mechanism and compare independent numerical methods.
9. Only after every training geometry has an explicit scientifically justified treatment should model-selection/fitting be frozen and executed. A future full-spectrum model needs **new independent validation** because the historical holdout/anchors have already been opened for other targets/models.
10. Continue separately toward measured-sky validation with independent AOD/cloud/glare metadata, then human first-seeing validation. Production integration comes last.

## 14. Review-package entry points for a new worker

The current repository review surface lives under `review/full-spectrum-estimator-pilot-v2/`. Start with these files, in this order:

- `STAR_VISIBILITY_PROJECT_HANDOFF_2026-08-10.md` - this document.
- `full-spectrum-estimator-pilot-preregistration-v2.json` - frozen acquisition design; 44 cases / 5.6B histories.
- `full-spectrum-estimator-pilot-screening-analysis-preregistration-v4.json` - corrected pre-result same-n screening rules.
- `full-spectrum-estimator-pilot-execution-manifest-v4.json` - frozen runtime/case/artifact contract; review-only.
- `rendered-review-v5/renderer-review-report.json` and the 44 saved input pairs - exact reviewed input surface.
- `normalize_full_spectrum_estimator_pilot_results_v6.py` - fail-closed raw artifact normalizer; no result exists yet.
- `analyze_full_spectrum_estimator_pilot_v6.py` - corrected descriptive screening analyzer.
- `full-spectrum-estimator-pilot-preauthorization-contract-v4.json` and `full_spectrum_estimator_pilot_preauthorization_guard_v4.py` - review-time fail-closed authorization boundary; they require exact-head CI, fresh global-ordinal evidence, seed/runtime/renderer identity and do not authorize execution.
- `verify_full_spectrum_estimator_pilot_execution_manifest_v4.py`, `verify_full_spectrum_estimator_pilot_acquisition_contract_v4.py`, `verify_full_spectrum_estimator_pilot_seed_collision_audit_v4.py`, `verify_full_spectrum_estimator_pilot_identity_collision_audit_v4.py` - repository-relative verification of frozen evidence. The seed/identity audit verifiers verify the **frozen review evidence only**; a fresh live-GitHub collision audit is still mandatory immediately before authorization.
- `full-spectrum-training-admission-complete-v1.json` - immutable 39-geometry full-spectrum precision state used to freeze the first-two screening baseline.
- `reference/` - superseded protocols/analyzers/guards retained for provenance. `reference/historical-nonportable/` contains old worker-local preparation utilities and must not be treated as active build tooling.

The safe review test suite is frozen by `run_review_checks.py`: seven exact test modules, currently **39 tests**, plus compile success. It covers protocol invariance, exact physical directive surfaces, artifact contracts, channel-specific zero refusal, same-n/non-degradation analyzer regression, global-ordinal and exact-CI preauthorization refusal behavior, portability and frozen-evidence verifiers. No review test may invoke MYSTIC/libRadtran/uvspec.

### Control ledger

Public repository Issue #60 remains the authority. At this snapshot the latest directive is still `MYSTIC-STATE-0066`; any newer directive supersedes this document. Refresh it before every authorization/dispatch transition.

---

## 15. Definition of success

The goal is **not** the smallest residual on one historical table. The desired final system is the most accurate model that can survive independent tests and state its uncertainty.

A credible production model should eventually demonstrate:

- numerically stable and reproducible surrogate behavior against high-quality radiative-transfer truth;
- measured-sky validation across relevant twilight geometry and atmospheric states;
- same-atmosphere stellar extinction and spectral color handling;
- independently calibrated human detection behavior;
- end-to-end first-seeing timing residuals on untouched observer sessions;
- uncertainty intervals with empirical coverage;
- explicit OOD behavior for clouds, haze, unusual aerosol, horizon/glare, unsupported stars or missing atmospheric measurements.

When forced to choose between a slightly better-looking number and a scientifically auditable uncertainty/failure state, choose the latter. That is the path to the most accurate model rather than the most confident-looking model.
