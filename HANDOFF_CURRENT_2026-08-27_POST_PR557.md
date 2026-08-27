# STAR VISIBILITY / MYSTIC — CURRENT NEW-WORKER HANDOFF

**Current status: 2026-08-27, after successful fresh AVPS ordinal-40 authorization review #565; allocation marker not yet posted**

This file is the current standalone handoff for continuing the non-observation computational/scientific work. It supersedes all earlier post-#557/intermediate checkpoints.

---

# 0. READ THIS FIRST — exact current checkpoint

Repository:

- `search-maker/twilight-mystic-experiments`

Current `main`:

- `99ade7798627e67921139697ba1a004fa8a304bb`
- merge commit of PR #563, `Trigger fresh AVPS preauthorization after handoff metadata drift`.

#563 was deliberately **mode-only** and changed no watched file bytes or scientific/control semantics. The watched file

`experiments/aerosol-vertical-profile-sensitivity-v1/build_seed_authorization_proof.py`

kept exact Git blob:

- `98746ba72195454be1b770ef561d14a1473962ea`

while its mode changed `100644 -> 100755`. GitHub compare reported one changed file and `0` additions / `0` deletions / `0` content changes.

Current authorization PR:

- PR #565 — `Review fresh AVPS v1 ordinal 40 authorization candidate`
- state: open / Draft / unmerged
- parent main: `99ade7798627e67921139697ba1a004fa8a304bb`
- authorization head: `338ee82c8e088e929f45782b1f7ac1c3aaaaa533`
- exactly one changed file: `experiments/aerosol-vertical-profile-sensitivity-v1/authorization.json`
- authorization JSON Git blob: `91c2fcfe0536f7289b9da3c597428c546523571a`
- authorization JSON SHA-256: `bec00d3a5609794fbb1078abb2c8ec6cf901318f5e9e80f38c387fab886dae97`

The authorization review has now passed, but **ordinal 40 is not allocated until the exact Issue 60 allocation marker is posted**.

At this checkpoint there is still:

- no allocation marker for this fresh authorization head;
- no dispatch branch for this fresh authorization;
- no consumed marker;
- no AVPS scientific runtime setup;
- no uvspec/MYSTIC science execution;
- no result opening.

---

# 0A. Control history that must not be lost

## #558 — MERGED
`Add current-main AVPS authorization control gate`

Merge commit:

- `608359c645aaa2ff184124ee718c09e971d5e13b`

It bound authorization construction to the exact disabled execution package / AFGL evidence, required a one-file Draft authorization review, and made relevant control-byte changes require a new exact-main preauthorization.

## #559 — MERGED
`Freeze AVPS execution, analysis, and result-opening controls`

Merge commit:

- `107d63a01de96bc359af0ecd8f0129b7232ddcf1`

It froze before scientific identity allocation:

- exact 360-case reconstruction;
- exact 72-CRN grouping;
- fixed OPAC `continental_average` rich optics with state-specific custom tau and fixed AOD;
- 20,000,000 photons/case;
- process-group-safe execution;
- exact member/raw hashing and 8001-node validation;
- exact-360 aggregation before result opening;
- separate primary result-opening action;
- Level-B endpoint through current Crumey Eq.34 full branch with `F=3.14`;
- separate dispatch-transition and science-run guards;
- execution-contract bindings for transport/runtime identities.

No scientific run occurred in #558/#559.

## #561 — CLOSED / UNMERGED failed first ordinal-40 authorization review

Failed head:

- `67844e1dd2523963f2682f186387280dfb930760`

Review run:

- `33109014744`
- attempt `1`
- conclusion `failure`

It failed closed because repository metadata changed between the two repository-global enumerations. This was **not a seed collision** and not a bad scientific authorization document.

No allocation, dispatch, consumed marker, science run, or result opening occurred.

The failed head is permanently preserved at:

- `history/aerosol-vertical-profile-sensitivity-v1-ordinal-40-auth-review-failed-1`

Do not delete/rewrite that history ref.

## #562 — MERGED recovery
`Recover AVPS failed authorization review without consuming ordinal 40`

Merge commit:

- `cd56db1e823a75d617c026fecf359a80e8c64cb7`

It added fail-closed failed-review reuse rules and, crucially, an authorization-head **Actions quiet-window barrier** before repository-global double enumeration.

Reuse is refused if there is any allocation marker, dispatch/consumed evidence, scientific execution, execution-key prior use, competing positive ordinal claim, rerun/non-attempt-1 history, or malformed/multiple failed-history evidence.

No scientific design changed.

## first post-#562 preauthorization failure — explained metadata drift

Run:

- `33110552017`
- exact main then: `cd56db1e823a75d617c026fecf359a80e8c64cb7`
- attempt `1`
- failure at repository-global stability

The scan ran roughly `19:52:48Z–19:58:17Z`; the handoff update commit `471678a0bc12535d8dab70190b7081e835fd8671` was created at `19:57:54Z`, inside the scan window. The tracked-tree scan had passed. No collision/allocation/dispatch/science/result boundary was crossed.

Do not use GitHub Re-run/attempt 2 for that identity.

## #563 — MERGED fresh-trigger

Current main:

- `99ade7798627e67921139697ba1a004fa8a304bb`

Purpose: create a fresh exact-main identity with zero watched-byte changes so a clean attempt-1 preauthorization could run.

---

# 0B. Authoritative fresh exact-main preauthorization — SUCCESS

Run:

- `33111875371`
- exact main: `99ade7798627e67921139697ba1a004fa8a304bb`
- attempt: `1`
- conclusion: **SUCCESS**

Passed:

1. exact attempt-1 main / zero-runtime identity;
2. deterministic control tests;
3. artifact-only candidate ledger;
4. exact-main tracked-tree seed scan;
5. repository-global seed double enumeration;
6. exact-main seed authorization proof;
7. fresh global ordinal proposal/guard;
8. zero-runtime evidence upload;
9. terminal Issue 60 non-allocation checkpoint.

Fresh values:

- latest consumed global scientific ordinal: `39`
- next candidate if separately allocated: `40`
- candidate seed count: `72`
- candidate seed canonical SHA-256: `a2e22b526dfad84d4f23c0ca8b143d028fddc7e55f78deb93a43e194ebd6c35e`
- candidate rows canonical SHA-256: `f22de8a9e30ba106759effb1170a5ca1d1e747cb2ac68293fa232dc7ed6ca683`
- tracked-tree external collision count: `0`
- repository-global collision count: `0`
- repository-global double enumeration stable: `true`

Preauthorization status:

- `PREAUTHORIZATION_SURFACE_CLEAN_NOT_ALLOCATED`

Report SHA-256:

- `12f8c7fe6cc7c5cbf36d320066d4a88e02695b541d2ffb0dae2e820961414175`

Artifact:

- ID `9663132186`
- `vertical-profile-v1-preauthorization-proof`
- digest `sha256:1253612ffe4ba228e319f6b063256abd7340d11eec76981db4cc39a3619b2df6`

Downloaded ZIP SHA-256 was independently verified to match GitHub exactly.

Important flags remained false:

- `scientificOrdinalAllocated`
- `authorizationCreated`
- `dispatchCreated`
- `scientificRuntimeSetupPerformed`
- `scientificExecutionPerformed`
- `solverExecutionPerformed`
- `resultOpeningPerformed`

---

# 0C. Fresh authorization materialization — completed safely

PR #564:

- `Materialize fresh-main AVPS ordinal-40 authorization candidate`
- closed / Draft / **unmerged** after artifact verification
- helper parent: exact main `99ade7798627e67921139697ba1a004fa8a304bb`
- helper head: `b941374e01eb33f5915acf55e58980791052a938`

The helper workflow was byte-identical to the prior reviewed materializer:

- Git blob `d1218ac62cf0e4e47e91859693ce666f66ac9425`

Materializer run:

- `33112908528`
- conclusion: **SUCCESS**

It resolved the exact successful attempt-1 parent-main preauthorization and materialized a new authorization candidate without allocation/runtime/solver/results.

Artifact:

- ID `9663270438`
- `vertical-profile-v1-authorization-candidate`
- digest `sha256:75d801a98c287924eab032ca215dcf5c5adaec51d326a59b453216a98d977fd9`

Verified authorization bytes:

- SHA-256 `bec00d3a5609794fbb1078abb2c8ec6cf901318f5e9e80f38c387fab886dae97`
- Git blob `91c2fcfe0536f7289b9da3c597428c546523571a`
- parent `99ade7798627e67921139697ba1a004fa8a304bb`
- scientific ordinal `40`
- 72 candidate seeds / 360 cases
- preauthorization run `33111875371`
- preauthorization artifact `9663132186`
- `dispatchAuthorized=false`
- `resultOpeningAuthorized=false`
- `automaticDispatch=false`
- `productionAuthorized=false`
- Taylor/Jerusalem fitting not authorized.

The materializer evidence explicitly proved no allocation branch transition, runtime setup, solver execution, or result opening.

---

# 0D. Fresh one-file authorization review #565 — SUCCESS

PR #565:

- title `Review fresh AVPS v1 ordinal 40 authorization candidate`
- open / Draft / unmerged
- parent `99ade7798627e67921139697ba1a004fa8a304bb`
- head `338ee82c8e088e929f45782b1f7ac1c3aaaaa533`
- one changed file only: `experiments/aerosol-vertical-profile-sensitivity-v1/authorization.json`
- artifact-identical authorization bytes: Git blob `91c2fcfe0536f7289b9da3c597428c546523571a`

Authorization review run:

- `33113256151`
- attempt `1`
- conclusion: **SUCCESS**

The recovery architecture worked as intended:

1. exact one-file Draft authorization identity — PASS;
2. exact successful attempt-1 parent-main preauthorization resolution — PASS;
3. candidate ledger rebuild — PASS;
4. authorization-head tracked-tree seed scan — PASS;
5. **authorization-head Actions metadata quiet window — PASS**;
6. stable authorization-head repository-global seed double enumeration — PASS;
7. live authorization-head seed proof — PASS;
8. exact authorization guard on fresh control surface — PASS;
9. zero-runtime review evidence — PASS.

The quiet-window specifically waited until sibling PR workflows, including the repository-wide non-scientific contract, became terminal before the global scan began. This prevents the race that caused #561 to fail.

Review artifact:

- ID `9663887142`
- name `vertical-profile-v1-authorization-review-ordinal-40`
- GitHub digest `sha256:3edff7740ca35832bbca0cfcba096aa3d9963d9b6c19044d867a2b3c9f09a47c`

Downloaded ZIP digest was independently verified identical.

`authorization-review.json`:

- status `AUTHORIZATION_REVIEW_PASS_ZERO_RUNTIME`
- head `338ee82c8e088e929f45782b1f7ac1c3aaaaa533`
- parent `99ade7798627e67921139697ba1a004fa8a304bb`
- scientific ordinal `40`
- 360 cases / 72 groups
- candidate seed authorization recheck passed
- `ordinalAllocatedReservedOrConsumedByReview=false`
- `dispatchAuthorized=false`
- `resultOpeningAuthorized=false`
- `scientificRuntimeSetupPerformed=false`
- `scientificExecutionPerformed=false`
- `solverExecutionPerformed=false`

`live-seed-authorization-proof.json`:

- status `PASS_CANDIDATE_SEEDS_AUTHORIZATION_RECHECK_NOT_ALLOCATED`
- candidate seed count `72`
- tracked-tree external collisions `0`
- repository-global collisions `0`
- repository-global double enumeration stable `true`
- all collision counters zero `true`
- no post-fence arrivals in branches/pulls/issues/comments/runs/artifacts
- `scientificOrdinalAllocated=false`
- `dispatchCreated=false`
- `scientificExecutionAuthorized=false`
- `solverExecutionAuthorized=false`
- `resultOpeningAuthorized=false`.

**Current boundary:** the review authorizes moving to the allocation step, but the review itself did not allocate/reserve/consume ordinal 40.

---

# 1. IMMEDIATE CONTINUATION ORDER

Follow this order exactly.

## Step 1 — post exactly one Issue 60 allocation marker

Now that #565 attempt-1 authorization review is terminal SUCCESS, the next legal boundary is exactly one Issue 60 marker:

`ORDINAL40_AVPS_V1_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED commit=338ee82c8e088e929f45782b1f7ac1c3aaaaa533 parent=99ade7798627e67921139697ba1a004fa8a304bb pr=565`

Before posting, confirm an equivalent positive marker does not already exist.

The marker itself is the allocation boundary.

After it exists, ordinal 40 may be called **allocated/reviewed, not dispatched**.

Do not merge #565 merely to allocate. Keep the authorization PR open/Draft/unmerged unless an explicit reviewed control requires otherwise.

## Step 2 — dispatch is a separate guarded transition

After allocation:

- run/recheck the dedicated dispatch freshness/control surface;
- require the exact authorization head/parent/PR allocation marker;
- use only the reviewed dispatch publisher/guard;
- create the exact dispatch transition branch/commit only through that mechanism;
- create exactly one consumed marker only after the dispatch transition succeeds;
- never substitute GitHub Re-run for a fresh required identity.

No manual dispatch branch bypass.

## Step 3 — scientific execution only after successful dispatch transition

Only after dispatch is correctly reviewed/consumed may the frozen AVPS campaign run.

Frozen execution:

- 360 cases;
- 72 CRN groups;
- five fixed vertical states;
- 20M photons/case;
- exact frozen OPAC/custom-tau/AFGL/runtime identities.

No post-result adaptive cases, tuning, or target-based source/model selection.

## Step 4 — results remain closed until exact aggregate verification

Even after solver execution, do **not** inspect/open scientific result payloads until all of the following pass:

- all 360 cases present;
- all member/raw hashes verify;
- exact runtime identities verify;
- all case/attempt identities verify;
- 8001-node channels/derived quantities verify;
- exact-360 aggregate guard passes.

Primary result opening remains a separate post-aggregate action.

---

# 2. GLOBAL SCIENTIFIC RULES — DO NOT VIOLATE

- `F = 3.14` remains the current default human field factor.
- transient `tau = 30 s` remains experimental only.
- Never tune F, tau, AOD, aerosol profile, provider, forecast cycle, sky offset, threshold, interpolation/support, or other environmental parameters to force a desired Taylor/Jerusalem result.
- Never choose an atmospheric source/cycle/provider because it minimizes target residuals.
- Freeze external/environmental choices before target scoring wherever possible.
- No universal magnitude correction.
- No universal minute correction.
- Do not infer aerosol family from AOD alone.
- Do not fabricate missing vertical aerosol structure.
- Missing/invalid atmosphere data must remain explicit and fail closed or reduce confidence.
- Do not call modeled fields measurements.
- A CAMS republisher is not an independent scientific source from CAMS.
- No `humanFirstSeeingValidated` claim without independent human evidence.
- Taylor primarily validates direct MYSTIC sky radiance, not Level-B or human first-seeing.
- Pandora/Izaña remain unopened unless separately authorized.
- matched-stellar v1 is obsolete.
- Do not reopen the closed exact-zenith/90° MYSTIC-stellar campaign.

---

# 3. AVPS SCIENTIFIC DESIGN — FROZEN

Scientific question:

> At fixed total AOD550 and fixed coherent OPAC rich optical properties/phase function, how much does independently specified normalized aerosol vertical optical-depth shape change twilight radiance and the derived Level-B limiting-magnitude endpoint?

This is **not** a Taylor fit.

Frozen vertical states:

1. Continental average
2. Maritime clean
3. Desert
4. Arctic
5. Antarctic

These labels describe vertical templates only; all five use the same rich OPAC `continental_average` optical family.

Frozen case design:

- AFGL-US
- observer 0 m
- albedo 0.15
- 380–780 nm
- reviewed 1-nm grid
- MYSTIC spherical 1D
- VROOM
- MC standard-deviation evidence
- 20,000,000 photons/case
- Sun depression 2°, 4°, 6°, 8°
- AOD550 0.10 and 0.30
- geometries:
  - 10°/30° near-solar
  - 30°/90° cross-solar
  - 45°/180° opposite-solar
- 3 fresh CRN replicates
- 5 vertical states

Cardinality:

- 72 CRN groups
- 360 cases

Primary endpoints:

- photopic luminance
- scotopic luminance
- Johnson-V effective radiance

Secondary endpoint:

- paired Level-B limiting-magnitude delta through current Crumey Eq.34 full path with `F=3.14`.

No universal minute conversion.

---

# 4. `starsvisibility` — important separate unresolved work

## #114 — MERGED
Validated Level-B sky + stellar support through exact zenith/90° while preserving old <=80° behavior. Closed campaign; do not reopen.

## #118 — MERGED
Clean-checkout/current-main Level-B test lifecycle fix. Infrastructure only.

## #119 — MERGED
Frozen Crumey Eq.34 mesopic non-monotonic diagnostic:

- local maximum near `B = 0.0215673 cd/m²`
- local minimum near `B = 0.0470526 cd/m²`
- threshold drop about `2.6009%`
- maximum formal negative adaptation penalty about `-0.02861 mag`.

## #116 — OPEN / DO NOT MERGE YET
It floors negative transient visibility penalties to equilibrium. That is a semantic/physiological model change, not a cleanup.

Before merge:

1. characterize actual `(physical B, adaptation debt, effective B)` Level-B trajectories;
2. decide mapping from external psychophysics;
3. preregister semantic criteria;
4. perform complete post-decision timing audit;
5. exact-head parity/build.

## #117 — physical question still open

> Is physical detection background + equivalent adaptation luminance debt the correct mapping through the Crumey threshold relation?

Do not silently change production transient semantics before this is scientifically resolved.

---

# 5. OPERATIONAL ATMOSPHERE STATE v2 / LEVEL-B MAPPING

## #120 — MERGED design
Established component provenance, spectral AOD, vertical profile, SSA/phase/g, molecular/surface/cloud status, explicit missing/approximated/rejected/conflict semantics, historical/current/future modes, QC, and explicit v2 -> v1 projection.

## #121 — MERGED foundation

Merge commit:

- `e0da52eb0a2d5bac333da6572f51df52ea7e676e`

Important limitation:

> richer v2 atmosphere fields are not yet generally consumed by the current fast Level-B sky model.

The central remaining engineering/scientific problem is:

1. acquire the best independently known atmosphere;
2. represent it without inventing missing components;
3. run direct MYSTIC when high fidelity is needed;
4. map the same state into fast Level-B;
5. validate that mapping on preregistered MYSTIC cases independent of Taylor/Jerusalem target residuals;
6. only then use observations as external validation.

Priority sensitivity sequence remains:

1. vertical aerosol profile — current AVPS
2. spectral AOD
3. SSA
4. phase function / g
5. interactions
6. then pressure/temperature/ozone/water vapor/albedo/RH as warranted.

---

# 6. TAYLOR ANN ARBOR — CURRENT AUTHORITATIVE INTERPRETATION

Observation:

- Ann Arbor, Michigan
- 2025-08-07
- approx `42.256 N, 83.709 W`
- original Unihedron SQM at zenith.

Current direct-MYSTIC conclusion:

> Direct MYSTIC is broadly consistent with Taylor, and much of the previous ~6° discrepancy was strongly reduced by independently obtained aerosol vertical structure.

Key evidence:

At Sun `-5.808°`:

- old residual `+0.393 mag`
- CAMS-profile residual `+0.087 mag`

At Sun `-6.134°`:

- old residual `+0.388 mag`
- CAMS-profile residual `+0.031 mag`.

No SQM offset or AOD was fitted.

Interpretation:

> total AOD alone is insufficient for maximum-accuracy twilight prediction; vertical aerosol placement can materially change twilight scattering as the Earth shadow removes lower layers.

Do not interpret this as proof that Taylor's exact atmosphere is known.

Taylor single-run Monte Carlo scatter from the dedicated multi-seed screen:

- row1 `0.00264 mag`
- row5 `0.00517`
- row9 `0.00709`
- row13 `0.00801`
- row17 `0.01100`
- row21 `0.02630`
- row24 `0.0704`
- row25 `0.0906`.

Taylor repeatability term:

- about `0.06215 mag`.

Late reconverged residuals rows 23–25:

- `+0.08544`
- `+0.17350`
- `+0.17696 mag`.

These late rows are not compelling standalone inconsistencies after uncertainty treatment.

AOD finite-difference derivative remains unresolved; do not reuse an old large derivative as a precise physical derivative.

---

# 7. TAYLOR CAMS PROVENANCE BOUNDARY

Approx same-cycle columns near Taylor:

- AOD550 about `0.31–0.32`
- SSA550 about `0.95`
- g550 about `0.71`
- Ångström alpha about `1.28`.

But forecast00 vertical extinction returned 137 exact zero coefficients despite nonzero column AOD; forecast03 had valid profiles.

Therefore:

- forecast00 all-zero extinction is invalid;
- do not call a mixed run `same-cycle full CAMS` unless vertical fields are genuinely valid;
- height-uniform column SSA/g must be labeled approximation;
- never choose forecast03 because it improves Taylor residuals.

Independent Taylor atmosphere archive search — EarthCARE/ATLID, lidar/ceilometer, AERONET, etc. — is a separate worker lane. Do not duplicate it unless explicitly assigned.

HRRR:

- #487 owns scientific vertical-shape comparison;
- #489 is only a technical 550-nm smoke test.

---

# 8. OTHER LATER LANES

- Moon: draft/validation remains a later priority.
- Natural night background: draft work remains later priority.
- Artificial skyglow: provider/model still needed.
- Total sky compositor exists, but each component needs valid provenance/domain rules.
- Transient adaptation #117 remains unresolved while atmosphere work proceeds.
- Old Draft PR #48 should not be merged/replayed wholesale; core v1 atmosphere/acquisition files are already on current `starsvisibility` main. Treat #48 as historical context only.

---

# 9. REPORTING CONTRACT

Every scientific campaign/report must state explicitly:

- exact commit/head;
- exact frozen protocol;
- exact runtime/data identities;
- whether seeds were preauthorized before use;
- global scientific ordinal and exact allocation/consumed markers if applicable;
- whether MYSTIC ran;
- whether results were opened;
- atmosphere provenance;
- approximations/missing components;
- numerical uncertainty / MC scatter;
- whether the comparison is direct MYSTIC, Level-B, or human first-seeing;
- whether target observations were used for source/model selection.

Never collapse these layers into a vague statement that `the model matches observations`.

---

# 10. CURRENT BOTTOM LINE

The project is not finished, but the AVPS lane has now passed its fresh exact-main preauthorization and its fresh zero-runtime one-file authorization review.

The failed #561 path was recovered without consuming ordinal 40. The new #565 review passed the quiet-window, stable repository-global double enumeration, live seed proof, and exact authorization guard.

**Exact state at this handoff update:**

- ordinal 40 is still **not allocated** because the allocation marker has not yet been posted;
- no dispatch has occurred;
- no MYSTIC science run has occurred;
- no scientific results have been opened.

Immediate next action:

> verify no duplicate positive allocation marker exists, post exactly one `ORDINAL40_AVPS_V1_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED` marker for head `338ee82c8e088e929f45782b1f7ac1c3aaaaa533` / parent `99ade7798627e67921139697ba1a004fa8a304bb` / PR #565, then continue through the separate dispatch freshness/publisher guard. Do not manually bypass dispatch and do not open results before exact aggregate validation.
