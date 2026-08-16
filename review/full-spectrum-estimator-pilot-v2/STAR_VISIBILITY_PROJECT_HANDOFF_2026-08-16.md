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

---

# 16. 2026-08-16 cumulative update — all material changes since the 2026-08-10 handoff

**Updated snapshot date:** 2026-08-16 (America/New_York)  
**Original handoff preserved:** `STAR_VISIBILITY_PROJECT_HANDOFF_2026-08-10.md`, current Git blob `fde043450b1165aee32ac9e47422c34096c1ca33`. The original file has not been edited. This 2026-08-16 file copies that handoff in full above and appends the cumulative change record below.  
**Current verified public scientific `main` before this handoff-only update:** `001d82678090c4322405eb84c56f816f1eafda5d`.  
**Current control authority:** Issue #60, `MYSTIC-STATE-0071`. A fresh ledger refresh found no `MYSTIC-STATE-0072` before this handoff update.  
**Current scientific boundary:** the selected Level-B v3 model is frozen **training-only**. No protected validation, no fresh-validation generation, no production promotion, and no Worker-B/Worker-C activation are authorized. Ordinal27 is permanently diagnostic-only. Any future validation of a changed model requires a new governance directive and a completely fresh untouched validation source preregistered before any values are opened.

This section supersedes every older “current main”, “current directive”, “next unused ordinal”, “no full-spectrum surrogate exists”, “do not fit yet”, and “exact next engineering step” statement above where the later chronology below has overtaken it. Historical facts and scientific cautions above remain valid unless explicitly superseded here.

## 16.1 Executive state change since 2026-08-10

The project moved through four major phases after the original handoff:

1. the frozen full-spectrum estimator-method pilot was actually taken through one-use screening and independent confirmation infrastructure, including several fail-closed operational identities that produced no science;
2. the public training set was expanded and converted into a stable 13-target spectral representation, then used for a Level-B surrogate campaign;
3. two generations of Level-B models failed training-only readiness, local training-only densification around the identified shape weakness added 14 fresh training geometries, and a densified 58-geometry Level-B v2 model became training-only eligible;
4. a completely fresh protected validation campaign was then executed once and **failed the frozen final Definition of Done by a small localized primary-amplitude miss**, after which a new training-only residual-correction generation selected and materialized a changed model without reusing any protected values.

The most important current distinction is therefore:

- **old Level-B v2 frozen model:** protected fresh-validation verdict exists and is `FAIL_FROZEN_FRESH_DOD_NO_RETUNING`; its ordinal27 values can never become validation again;
- **new Level-B v3 changed model:** selected and materialized using training data only; it has **no protected validation result yet** and may not be validated until new governance freezes a completely fresh untouched source.

## 16.2 Full-spectrum estimator pilot: ordinals 14-17 and what they established

The corrected estimator pilot review package from the original handoff was eventually advanced under later directives. The scientific/operational identity history matters because one-use identities are never rewritten into successes.

### Ordinal 14

- the corrected review package and multiple authorization/transport repairs were published after the original handoff;
- run `31542689486` consumed the ordinal identity but failed at GitHub output transport before scientific case execution;
- no MYSTIC solver execution occurred under that identity;
- the identity remains historical and was never rerun.

### Ordinal 15

- transport was repaired and a new one-use authorization was created;
- run `31544203626` instantiated the intended 44 case jobs, but a shared executor still hard-coded the ordinal14 branch identity;
- all cases refused before syntax checking and before MYSTIC;
- there were zero scientific solver invocations; the ordinal15 identity remains immutable failure evidence.

### Ordinal 16

- the executor branch contract was corrected before the next identity;
- run `31546667072`, attempt1, executed the full frozen 44-case scientific screening campaign;
- all **44/44** case jobs completed successfully with exact fresh seeds `970001-970044`;
- the run's aggregate/postprocess path later refused an output-grid normalization detail, but the scientific case artifacts were already complete and immutable;
- no scientific rerun was performed. Artifact-only postprocessing recovery consumed the original 44 case artifacts;
- postprocess run `31556854044` completed SUCCESS and produced the normalized screening result artifact `9126300230`.

### Independent confirmation / ordinal 17

The confirmation design was preregistered only after screening evidence existed and before confirmation values were opened:

- exactly six candidate method/geometry pairs were mechanically derived from the frozen screening rules;
- exactly four fresh independent confirmation blocks per pair, **24 cases total**;
- fresh seeds `1600000001-1600000024`;
- screening blocks were not allowed to enter the final confirmation precision gate;
- the confirmation result was used only through the preregistered decision layer, not to retune the screening threshold after the fact.

The post-confirmation training-admission decision retained the conservative training evidence boundary:

- 24 historical full-spectrum geometries remained admitted;
- `train-0014` and `train-0037` remained continuation-required at that decision point;
- the 13 precision-exhausted geometries remained refused as precise training labels.

The original estimator pilot therefore did not magically make all historical terminal means precise. Its main durable contribution was a much more audited estimator/variance workflow and a disciplined confirmation boundary.

## 16.3 Fresh training continuation for `train-0014` — ordinal18

A separate fresh-training continuation was frozen for `train-0014` under ordinal18. The source scientific run was `31659053288`.

The downstream path required artifact-only salvage because of post-execution transport/provenance issues; those recoveries did **not** rerun the solver. The successful salvage-v2 run was `31662184272`, with immutable evidence artifact `9166569024`.

The final admission decision was narrow:

- only the four fresh ordinal18 `train-0014` blocks were admitted as additional training evidence;
- status: `FRESH_TRAINING_PRECISION_WITHIN_HISTORICAL_MAXIMUM`;
- `train-0037` remained unresolved/deferred rather than being filled with guessed or reused values;
- no protected holdout evidence was converted into training data.

## 16.4 Level-B / Tier-2 core campaign and first protected validation

The project then moved from estimator-method work to an explicitly bounded Level-B surrogate program.

### Core campaign design

The Level-B/Tier-2 core campaign froze:

- 25 geometries total: 19 training + 6 protected;
- 76 Stage1 cases + 24 Stage2 cases;
- 2.84B configured photon histories in the campaign envelope;
- strict training-first ordering, with protected values unavailable to training/model selection.

A pre-existing-artifact replay over the historical 39-geometry/166-case training source was also performed without new science. Canonical replay run `31699141872` produced artifact `9180525837` (digest begins `sha256:cbfe39fc...`).

### Stage1 source and artifact-only salvage

Several Stage1 operational identities failed before science. The valid scientific source became ordinal20 run `31763376962`; downstream parsing/provenance then required artifact-only salvage rather than any scientific rerun.

Successful salvage run `31767381839` produced evidence artifact `9206827621` (digest begins `sha256:2d829c6e...`) and established:

- complete 78-artifact inventory / 76 case artifacts;
- all 76 one-use source solver executions proven;
- all associated seeds permanently consumed;
- no GitHub rerun/retry/resume of the scientific identity.

### Frozen spectral representation

The first representation attempt refused because 10 resolved nullspace/PCA components exceeded its cap of eight. Rather than discard components after seeing that result, v2 retained all ten under the same frozen variance criterion. A source-binding correction then repaired physical-geometry extraction before final representation acceptance.

Corrected representation run `31771224298`, attempt1, SUCCESS, produced:

- artifact `9208203541`;
- GitHub digest `sha256:2fe50ed674155f440322c92d28877f5c022f0cc5fa13e1e601596a9902482815`;
- frozen representation/package canonical SHA-256 `2491ac91ed924f2ba69b37ea20f48d63f51d41146cd9fe50e0bd63bfb315a763`;
- 13 targets/features: three integrated primary channels plus ten retained PCA/nullspace coefficients;
- canonical 44-record training dataset SHA-256 `bb7908426d9d545f43c082aebbaab1829a486e2962d0b9ee34a5e8bef5390133`.

### Level-B v1 model and protected Stage2 failure

Training-only selection run `31772063894` completed SUCCESS over 23 candidates / 15 folds and selected `ridge-physical-compact`, ridge `0.001`, with model SHA-256 `bcdcc41f2a3af718f00d81a3b41f4ba63674fdc3e29f8562875b0d5401ad493a`.

The six protected Stage2 geometries were then frozen before execution: 24 cases / 0.72B configured histories under the unchanged DoD. Ordinal21 refused pre-solver because NumPy was absent in preflight. Ordinal22 became the valid scientific identity:

- run `31774348888`, attempt1;
- **24/24 protected cases SUCCESS**;
- exactly one syntax check and one MYSTIC invocation per case;
- artifact `9209494627`, digest `sha256:20a406cf4f8e45b354a7f6d545ac053b67ad679fd5544229d483b4d55b84f061`;
- final verdict: `FAIL_FROZEN_DOD_NO_RETUNING`.

Key frozen metrics were:

- aggregate primary MALE `0.40468160381500773`;
- aggregate/baseline fraction `0.18348012599573346`;
- shape median per-case NRMSE `0.5678886763739921`;
- shape worst per-case NRMSE `1.691365283709205`;
- worst single coefficient normalized error `3.8246998763188147`;
- photopic median/worst absolute log error `0.36005062057432435 / 1.005071468700431`;
- scotopic `0.32682643210418894 / 0.8827112803775625`;
- Johnson-V `0.3600354648814014 / 0.9991874331164117`.

Support and baseline gates passed, but positive-channel error and worst spectral-shape gates failed. Ordinal22 was permanently opened and became diagnostic-only; its values were excluded from later training/selection/support/threshold decisions.

## 16.5 `MYSTIC-STATE-0068`: two training-only Level-B v2 generations, both fail-closed

Failure analysis was preregistered without using ordinal22 protected values as training evidence.

### Generation 1

- 44 training records;
- 100 candidates x 59 folds;
- activation run `31800232948` SUCCESS;
- **0/100** candidates eligible;
- universal blocker: `looWorstShape`, concentrated at `train-0021`.

### Generation 2

- same 44 training records, with an uncertainty-aware shape treatment frozen before fitting;
- 230 candidates x 59 folds;
- run `31801957517` SUCCESS;
- **0/230** candidates eligible;
- universal blocker: `looWorstUncertaintyAdjustedSingleCoefficient`, concentrated at `train-0036`, PCA coefficient 1;
- best candidate family: `ridge-primary-physical-compact-shape-idw-cos`, primary ridge `0.0001`, shape `k=12`, `p=2`;
- best worst-single coefficient normalized error `3.398892`, still above the frozen `3.0` bound.

`MYSTIC-STATE-0068` therefore terminated without a model rather than relaxing a threshold after failure.

## 16.6 `MYSTIC-STATE-0069`: local training-only densification and the first eligible Level-B v2 model

The next directive authorized a narrowly targeted training-only densification around the diagnosed `train-0036` weakness:

- 14 new training geometries, `train-0101` through `train-0114`;
- ordinal23;
- 28 fresh cases;
- 20M photon histories per case, 560M configured total;
- fresh seeds `2100000101-2100000128`.

Scientific run `31814698818`, attempt1, completed **28/28** cases successfully. Inventory artifact `9224754905` has digest `sha256:83d70c4f55e7b12d7db6d9922b4113657137a38d1167de63587afbf0c1378a23`.

The densified training package then contained exactly 58 training geometries / 166 cases. It deliberately reused the already frozen representation basis instead of refitting the target basis after densification.

Training-fit activation `31827007009` completed SUCCESS over the same Generation-2 model space:

- 230 candidates;
- 73 folds;
- **9/230 eligible**;
- selected `ridge-primary-physical-compact-shape-idw-cos`;
- primary ridge `1e-5`;
- shape IDW `k=4`, `p=1`;
- frozen model canonical SHA-256 `91ae5811e55b3d4ef872ab672f006c4b383c6581a53de67cd018b6eb2666f9a7`;
- model/training artifact `9229229366`;
- artifact digest `sha256:f4c8c68a622f7c6bdc1b9177ad31d22f673becb1f286436d54b876ceece3668a`;
- densified 58-record training dataset canonical SHA-256 `58c977acf84b6ce17717765c2052f7f9fd64e2965e5bf447eba5cc4accb30435`.

This was a **training-only** success. It did not authorize reusing any previously opened protected values.

## 16.7 `MYSTIC-STATE-0070`: completely fresh validation, ordinals24-27, and the terminal Level-B v2 verdict

A new validation source was preregistered from a geometry-only pool before any values were opened:

- six fresh v0070 protected geometries;
- four blocks per geometry;
- 40M photon histories per block;
- 24 cases / 960M configured histories;
- unchanged frozen DoD thresholds.

The operational identity history is important and must not be collapsed into a single apparent run:

### Ordinal24

Run `31840757436`, attempt1, passed preflight and instantiated 24 case jobs, but every case refused before syntax/MYSTIC because the executor branch-suffix contract mismatched. Seeds `2101000001-2101000024` were retired. Zero solver science occurred.

### Ordinal25

Run `31842973699`, attempt1, refused pre-science because duplicate identical Issue-allocation markers violated the exactly-one check. No manifest/cases/solver were created. Seeds `2101000025-2101000048` were retired.

### Ordinal26

Run `31844855497`, attempt1, produced 24 case jobs, all of which refused before syntax/MYSTIC because an artifact path preserved `tmp/o26-manifest.json` while the command expected a flat path. Seeds `2101000049-2101000072` were retired.

### Ordinal27 — the actual fresh protected science

Run `31848052825`, attempt1, branch `dispatch/level-b-v2-densified58-fresh-validation-ordinal27-v1`:

- preflight SUCCESS;
- **24/24 protected case jobs SUCCESS**;
- exactly 24 syntax checks and exactly 24 MYSTIC invocations;
- exactly 960M configured histories;
- seeds `2101000073-2101000096` permanently consumed;
- no rerun, retry, or resume.

The source workflow's overall conclusion was failure only because its evaluator rejected a model-schema compatibility detail **after all protected scientific case artifacts already existed**.

### Evaluation-only recovery, with zero new science

Three additive evaluator recoveries preserved the original 24 case artifacts:

- evaluation v1 run `31849706647` failed a static guard before case-value evaluation;
- v2 run `31850828379` read the immutable 24 case artifacts but failed on legacy flat `shapeFitX` expectations;
- v3 introduced only a virtual compatibility view, `VIRTUAL_SHAPEFITX_TO_FROZEN_NESTED_SHAPE_COORDINATES_ONLY`, mapping the legacy evaluator read to the already frozen nested `model.shape.coordinates`. It did **not** change the serialized model, model hash, predictions, thresholds or evaluation mathematics.

Evaluation-v3 run `31851872896`, attempt1, completed SUCCESS with zero new solver invocations.

Result artifact:

- artifact ID `9237788838`;
- digest `sha256:4f6973c2b7cfb14077fd1f570ae124a44141bde9feb5baf813c1206e73b20533`;
- result canonical SHA-256 `206457a577b40864ad97858d3dc60267eb9a1cc895e4a62d979a7f61aad11c8c`.

### Final Level-B v2 fresh-validation result

Terminal verdict:

`FAIL_FROZEN_FRESH_DOD_NO_RETUNING`

`definitionOfDonePassed=false`.

Most gates passed. The only final threshold breakers were the worst absolute positive-channel log errors at `v0070-holdout-06`:

- Photopic worst absolute log error `0.36638612645471724` vs frozen maximum `0.35`;
- Johnson-V worst absolute log error `0.37019376213640065` vs frozen maximum `0.35`;
- Scotopic worst absolute log error `0.2908053479594406`, pass.

Other frozen metrics:

- aggregate primary MALE `0.1299376252336051`;
- frozen training-mean baseline MALE `3.514589250167299`;
- aggregate/baseline fraction `0.0369709277485043`;
- shape median per-case NRMSE `0.657605639439601`;
- shape worst per-case NRMSE `0.9295224594911778`;
- worst single coefficient normalized error `2.2263546835090593`.

Support, spectral-shape aggregate gates, baseline improvement, uncertainty-normalized error, channel bias and channel median-error gates passed. The model nonetheless failed because the frozen DoD required **all** criteria to pass.

The diagnostic-only postmortem localized the miss to a primary-amplitude underprediction at `v0070-holdout-06`, about 31% low in Photopic and Johnson-V, in a sparse multivariate corner combining deep twilight, high target altitude, high observer elevation and low AOD. Shape itself passed. This is a diagnostic interpretation only — **not** permission to relax the 0.35 threshold and not permission to reuse ordinal27 after retuning.

Ordinal27 is permanently diagnostic-only from this point onward.

## 16.8 `MYSTIC-STATE-0071`: training-only residual correction after the fresh protected failure

Because ordinal27 could no longer be used for selection, the next generation was explicitly training-only and excluded ordinal27 values **and geometry coordinates** from model selection.

### Frozen pre-fit design

The Level-B v3 training-only pre-fit eventually froze 145 candidates over the existing 58 training geometries and the same 73 folds:

- one exact frozen-v2 control candidate;
- 144 new residual-IDW primary-correction candidates;
- same targets, shape predictor, representation, training-only readiness gates and no protected records;
- residual definition: truth primary natural-log target minus base compact-ridge primary prediction on the same fit record;
- residual interpolation by deterministic float64 Euclidean IDW;
- candidate dimensions included residual coordinate system, ridge, neighbors, power and shrinkage;
- control complexity rank 7, new family complexity rank 9, so a numeric tie remains control-favoring;
- no randomness and no MYSTIC execution in fit/model selection.

The synthetic implementation review exercised all 145 candidates, reproduced the old control exactly, proved shape invariance and had no network/artifact/solver surface.

### One-use real training fit

A separate activation and one-file Draft authorization were used. Source one-use fit:

- run `31924262989`, attempt1;
- job `95109323854`;
- frozen 145-candidate / 73-fold fit completed;
- independent result audit completed;
- **145/145 candidates were eligible** under the unchanged training-only gates;
- deterministic winner: `resid-V1_IDW_COS_COORDINATES-r1e-05-k6-p1-a1`;
- selected hyperparameters: V1 residual coordinates, compact primary ridge `1e-5`, residual `k=6`, `p=1`, shrinkage `1.0`;
- valid scientific/training-only verdict: `FREEZE_CHANGED_MODEL_TRAINING_ONLY_PENDING_SEPARATE_FRESH_VALIDATION_GOVERNANCE`.

The workflow then failed only in post-selection provenance because its shallow checkout had `fetch-depth: 1` and provenance called `git rev-parse HEAD^`. The valid fit and independent audit had already completed. **Run `31924262989` was never rerun, retried or resumed.**

### Additive selected-model materialization recovery

PR #218 added a deterministic recovery that could materialize **only the already-selected candidate** from the same immutable 58-record training artifact. It contained no candidate enumeration, CV, ranking, selection, protected read or MYSTIC surface.

Operational review bugs were repaired additively before authorization:

- install `numpy==2.3.2` in the review/materialization environment;
- use `gh api --allow-escape-sequences` when reading Actions logs that contain ANSI sequences;
- apply the same log-transport correction proactively to future authorization/materialization preflight paths.

Final exact-head gates for #218:

- dedicated recovery review `31926981492` — SUCCESS;
- repo-wide contract `31926981494` — SUCCESS.

The recovery package merged before separate one-use authorization.

### Materialization authorization and result

One-file Draft PR #219 bound the already selected candidate and passed:

- authorization review `31927234711` — SUCCESS;
- repo-wide contract `31927234712` — SUCCESS.

Issue #60 marker comment `5305773001` was then written and the sole materialization branch was created at the exact authorization head. Materialization run:

- `31927414786`, attempt1 — **SUCCESS**;
- source training artifact `9229229366`, exact 58-record training dataset;
- zero candidate search/enumeration;
- zero CV-fold evaluations;
- zero ranking;
- zero additional MYSTIC solver invocations;
- zero protected-artifact reads;
- `ordinal27ValuesRead=false`.

Frozen output identities:

- artifact ID `9258264586`;
- artifact digest `sha256:a3a4266e95919dccc8248e73f16fc0960dae4254543cbf48677b1f780530bfc7`;
- selected model canonical SHA-256 `c4902eb3c2ba67b12dc4ef2b9cefb67c5963a6abc104708a73b2aab5dd0163b9`;
- model-artifact canonical SHA-256 `d7f77416c782dd6226be0898f722fb880096638156517177cf1252b96b66f015`;
- materialization result SHA-256 `ed2997677b19a81159b1916c30c99c4ec78861fb7cab979d687e66fcf9d710df`;
- provenance SHA-256 `c858143dfa6f8441463e0bb0f3e4b7ef9f09e3b7c3972b3de8df8b2202827ff5`.

### Immutable result binding and current `main`

One-file PR #220 bound the completed training-only model after repo-wide contract run `31927590561` passed SUCCESS. Binding self-hash:

`6f75b1868f4119ec08c2053104e911e8889df9659ba876e669419763767252bf`

PR #220 merged as current pre-handoff-update public `main`:

`001d82678090c4322405eb84c56f816f1eafda5d`

Merged result-binding path:

`review/level-b-v3-training-only-materialization-result-v1/result-v1.json`

Git blob:

`1cc183c20a28f1652fac1412988e82b7c2e56179`

The consumed authorization PRs were then closed as immutable evidence, **Draft and unmerged**:

- #217, one-use Level-B v3 training fit authorization;
- #219, one-use selected-model materialization authorization.

Final Issue #60 training-only checkpoint comment: `5305806435`.

## 16.9 Current governance and one-use identity rules — do not accidentally undo them

The workflow hardening since the original handoff produced durable lifecycle rules that future workers must treat as scientific controls, not bureaucracy:

1. **Scientific identities are one-use.** Never GitHub Re-run, retry or resume a scientific/evaluation identity whose outputs could affect evidence. Operational recovery is additive and gets a new identity.
2. A pre-science refusal can still retire an allocated ordinal or seed block if the frozen authorization policy says that identity was consumed. Do not recycle ordinals24-26 or their seed ranges.
3. Once a scientifically valid protected PASS/FAIL exists, those protected values are diagnostic-only. They cannot become selection data, threshold-tuning data, support-shaping data or “validation again” after retuning.
4. After any model/feature/support/training/hyperparameter change, later validation requires a **completely fresh untouched source**, frozen and preregistered before values are opened.
5. Authorization PRs remain Draft/unmerged through dispatch/evaluation/materialization and are closed afterward as immutable authorization evidence. Do not merge them merely to tidy history.
6. Result-binding and review/evidence PRs may merge only after their deterministic non-scientific contracts pass on the exact head.
7. `MYSTIC-STATE-0071` does **not** authorize protected validation of the newly changed model, new MYSTIC validation generation, threshold/DoD relaxation, production promotion, or Worker-B/Worker-C reactivation.
8. Issue #60 supersedes this handoff. A newer directive must be read in full before any action that this snapshot says is closed.

Explicitly forbidden reuse includes the old fresh-validation science/evaluator identities `31848052825`, `31849706647`, `31850828379`, and `31851872896`.

## 16.10 Current model inventory — distinguish the scientific roles

### Historical exploratory photopic v2

Still historical only. It passed older computational anchors for the obsolete/older target history and is not the current full-spectrum physical model.

### Level-B v1 model

Model SHA `bcdcc41f...`; failed its protected Stage2 DoD. Diagnostic only.

### Level-B v2 densified58 model

Model SHA `91ae5811e55b3d4ef872ab672f006c4b383c6581a53de67cd018b6eb2666f9a7`; trained on 58 geometries and **failed** completely fresh ordinal27 validation. Frozen failed model, useful for diagnostics but not production.

### Level-B v3 changed model — current training-only candidate

Model SHA `c4902eb3c2ba67b12dc4ef2b9cefb67c5963a6abc104708a73b2aab5dd0163b9`; selected only from the 58-record training source, independently audited, deterministically materialized, **not yet protected-validated**. It is the current candidate for any future separately governed fresh validation generation.

Do not call this model “validated” and do not compare it against ordinal27 as though that were a fresh test.

## 16.11 `starsvisibility` application-side changes since the old snapshot

The application repository was inspected for this handoff update but was **not modified**.

PR #24, `science/visibility-v3-blackwell-crumey`, remains:

- open;
- Draft;
- mergeable;
- still intentionally not production-wired.

Its head moved from the old handoff's `805937bab0e42755a02d709b2c5a0cba43f616e9` to:

`e676056d8c896a72bf37dd803becdf07a8cc71da`

The difference is exactly five commits after the old handoff head. The material additions are concentrated in the scientific reference layer:

- `same-atmosphere-event-model.mjs` now routes compatibility behavior through the canonical chronological event timeline rather than the obsolete endpoint-only monotonic crossing assumption;
- new regression coverage includes multiple visible intervals / entry-exit-re-entry behavior;
- a new experimental shadow-only `transient-adaptation.mjs` models adaptation state in **real clock time** as a first-order log-luminance state with exact interval solutions rather than Euler stepping;
- the adapting-field luminance is explicitly separated from the local detection-background luminance;
- adaptation state is precomputed chronologically and later queried purely, so root refinement cannot mutate observer history depending on query order;
- a new `transient-visibility.mjs` composes the adaptation debt only into the human-threshold layer and leaves MYSTIC sky radiance, stellar extinction and Crumey equations unchanged;
- it explicitly refuses double-counting adaptation when an observer field factor was already calibrated from real twilight first-seeing events that may have absorbed transient adaptation;
- current time constants 20/30/45/60 s are **sensitivity points only**, not observationally validated natural-twilight constants;
- production activation of transient adaptation still requires independent natural-twilight calibration and untouched end-to-end first-seeing validation;
- `MYSTIC_V3_EVENT_TIMING_BOUNDARY.md` now explicitly requires chronological adaptation history and preserves the rule that a sky-radiance validation cannot claim first-visibility event timing by itself.

The application-side scientific architecture remains the same: sky physics, same-atmosphere stellar signal, human threshold/adaptation and chronological event solving must be validated as separable layers before combined production claims.

## 16.12 What is complete now, and what is not

### Complete / immutable evidence

- 166-case historical full-spectrum training salvage and 39-geometry audit;
- estimator screening science under ordinal16 and its artifact-only postprocessing;
- independent estimator confirmation workflow and post-confirmation admission decision;
- ordinal18 fresh `train-0014` training continuation evidence;
- Stage1 Level-B core source/salvage evidence;
- frozen 13-target spectral representation;
- protected ordinal22 Level-B v1 failure;
- two fail-closed Level-B v2 training-only generations under STATE-0068;
- ordinal23 local densification and the eligible densified58 Level-B v2 model;
- completely fresh ordinal27 protected validation and terminal Level-B v2 failure;
- diagnostic-only ordinal27 postmortem;
- Level-B v3 training-only residual-correction fit;
- deterministic materialization and immutable result binding of the selected Level-B v3 changed model.

### Not complete / still closed

- there is **no protected validation result for the Level-B v3 changed model**;
- no `MYSTIC-STATE-0072` was present on the final ledger refresh before this handoff update;
- no fresh untouched validation source for the changed model is currently authorized;
- ordinal27 may not be reused to validate it;
- no DoD/threshold relaxation is authorized;
- no production promotion is authorized;
- Worker-B and Worker-C remain closed;
- measured-sky validation with matched atmosphere remains incomplete;
- same-atmosphere stellar-transmission validation remains incomplete;
- human/adaptation calibration and untouched end-to-end first-seeing validation remain incomplete;
- `starsvisibility` PR #24 remains a scientific/reference branch, not production behavior.

## 16.13 Exact next step from this updated handoff

Before doing anything scientific after reading this file:

1. refresh public Issue #60;
2. identify the highest numbered `MYSTIC-STATE-*` directive and read it in full;
3. verify live public `main`;
4. if no directive newer than `MYSTIC-STATE-0071` exists, **do not invent or dispatch a new protected validation** and do not retune against ordinal27;
5. if a new directive authorizes a validation generation for the Level-B v3 changed model, the source must be completely fresh/untouched and preregistered before any protected value exists, with one-use branch/run/seed identities and no reuse of ordinal27;
6. preserve the current model identity `c4902eb3...`, the exact training artifact `9229229366`, the frozen representation `2491ac91...`, and the result-binding identities unless the new directive explicitly authorizes a changed training generation;
7. continue the application-side measured-sky / stellar-transmission / observer calibration work only within its own evidence boundaries; do not treat successful surrogate-vs-MYSTIC testing as end-to-end human-event validation.

The current correct state is therefore **ready for a new governance decision, not ready for production and not authorized for another validation by inference**.

## 16.14 Compact identity table for recovery/orientation

- authoritative public ledger: Issue #60
- active directive at this snapshot: `MYSTIC-STATE-0071`
- current pre-handoff-update public main: `001d82678090c4322405eb84c56f816f1eafda5d`
- original 2026-08-10 handoff blob: `fde043450b1165aee32ac9e47422c34096c1ca33`
- frozen representation SHA-256: `2491ac91ed924f2ba69b37ea20f48d63f51d41146cd9fe50e0bd63bfb315a763`
- representation artifact: `9208203541`, digest `sha256:2fe50ed674155f440322c92d28877f5c022f0cc5fa13e1e601596a9902482815`
- densified58 training dataset SHA-256: `58c977acf84b6ce17717765c2052f7f9fd64e2965e5bf447eba5cc4accb30435`
- densified58 training/model artifact: `9229229366`, digest `sha256:f4c8c68a622f7c6bdc1b9177ad31d22f673becb1f286436d54b876ceece3668a`
- failed Level-B v2 model SHA-256: `91ae5811e55b3d4ef872ab672f006c4b383c6581a53de67cd018b6eb2666f9a7`
- fresh ordinal27 science run: `31848052825`, attempt1; **never rerun**
- evaluation-v3 run: `31851872896`, attempt1; **never rerun**
- ordinal27 result artifact: `9237788838`, digest `sha256:4f6973c2b7cfb14077fd1f570ae124a44141bde9feb5baf813c1206e73b20533`
- Level-B v2 terminal result: `FAIL_FROZEN_FRESH_DOD_NO_RETUNING`
- Level-B v3 source training-fit run: `31924262989`, attempt1; valid selection despite later provenance-only workflow failure; **never rerun**
- Level-B v3 selected candidate: `resid-V1_IDW_COS_COORDINATES-r1e-05-k6-p1-a1`
- Level-B v3 materialization run: `31927414786`, attempt1, SUCCESS
- Level-B v3 materialization artifact: `9258264586`, digest `sha256:a3a4266e95919dccc8248e73f16fc0960dae4254543cbf48677b1f780530bfc7`
- current Level-B v3 model SHA-256: `c4902eb3c2ba67b12dc4ef2b9cefb67c5963a6abc104708a73b2aab5dd0163b9`
- model-artifact canonical SHA-256: `d7f77416c782dd6226be0898f722fb880096638156517177cf1252b96b66f015`
- materialization result SHA-256: `ed2997677b19a81159b1916c30c99c4ec78861fb7cab979d687e66fcf9d710df`
- materialization provenance SHA-256: `c858143dfa6f8441463e0bb0f3e4b7ef9f09e3b7c3972b3de8df8b2202827ff5`
- merged Level-B v3 binding path: `review/level-b-v3-training-only-materialization-result-v1/result-v1.json`
- merged binding Git blob: `1cc183c20a28f1652fac1412988e82b7c2e56179`
- result-binding self-hash: `6f75b1868f4119ec08c2053104e911e8889df9659ba876e669419763767252bf`
- consumed Draft authorizations: PR #217 and PR #219, both closed unmerged after use
- final training-only checkpoint comment: `5305806435`
- `starsvisibility` PR #24 current head at this snapshot: `e676056d8c896a72bf37dd803becdf07a8cc71da`, Draft/open/mergeable

## 16.15 Final caution for a new owner

The recent history contains many workflow conclusions marked `failure` that are **not equivalent to failed scientific data**, and several `SUCCESS` review/materialization runs that are **not new scientific evidence**. Always classify a run by what actually executed:

- preflight/transport failure before solver: no scientific value was generated;
- solver case success followed by aggregate/evaluator/provenance failure: scientific artifacts may be valid and immutable, but recovery must consume them without rerunning the science;
- evaluator/materializer success with zero solver calls: operational/review evidence only;
- protected scientific PASS/FAIL: terminal for that frozen model/source under no-retuning governance.

Never collapse those categories. The project has deliberately paid operational complexity to preserve one-use evidence and prevent accidental leakage from opened validation into model selection. Preserve that separation.