# STAR VISIBILITY / MYSTIC — CURRENT NEW-WORKER HANDOFF

**Current status: 2026-08-27, after AVPS recovery #562, fresh-trigger #563, and successful exact-main preauthorization run 33111875371**

This file is the current standalone handoff for continuing the non-observation computational/scientific work. It supersedes the older post-#557 checkpoint and the intermediate version that still described #562 as active.

---

# 0. Exact current checkpoint — read this first

## Repository

`search-maker/twilight-mystic-experiments`

Current `main`:

- `99ade7798627e67921139697ba1a004fa8a304bb`
- merge commit of PR #563, a **mode-only, exact-blob-preserving** trigger used solely to obtain a fresh attempt-1 AVPS exact-main preauthorization after repository-metadata drift.

No scientific/control file contents changed in #563. The watched file

`experiments/aerosol-vertical-profile-sensitivity-v1/build_seed_authorization_proof.py`

kept exact Git blob:

- `98746ba72195454be1b770ef561d14a1473962ea`

and changed only mode `100644 -> 100755`.

GitHub compare reported:

- one changed file;
- `0` additions;
- `0` deletions;
- `0` content changes.

---

# 0A. AVPS control sequence now merged

## #558 — MERGED
`Add current-main AVPS authorization control gate`

Merge commit:

- `608359c645aaa2ff184124ee718c09e971d5e13b`

It bound authorization construction to the exact merged disabled execution package and AFGL evidence, required exact one-file Draft authorization review, and made control-byte changes force a new exact-main preauthorization.

## #559 — MERGED
`Freeze AVPS execution, analysis, and result-opening controls`

Merge commit:

- `107d63a01de96bc359af0ecd8f0129b7232ddcf1`

It froze before identity allocation:

- exact 360-case reconstruction;
- exact 72-CRN pairing;
- fixed OPAC `continental_average` rich optics + exact state tau + fixed AOD;
- 20M photons/case;
- process-group-safe execution;
- exact raw/member hashing and 8001-node channel validation;
- exact-360 aggregation before any result opening;
- separate primary result opening;
- Level-B endpoint through current Crumey Eq.34 full branch with `F=3.14`;
- separate dispatch-transition and science-run guards;
- execution contract byte-binding transport/runtime identities.

No science was executed by #558/#559.

## #562 — MERGED
`Recover AVPS failed authorization review without consuming ordinal 40`

Merge commit:

- `cd56db1e823a75d617c026fecf359a80e8c64cb7`

This recovery exists because the first ordinal-40 authorization review failed closed from repository-metadata instability, not from a seed collision.

It now:

1. preserves failed authorization heads as auditable immutable history;
2. permits reuse of ordinal 40 only when the prior authorization review was terminal attempt-1, closed/unmerged, and had no allocation/dispatch/science evidence;
3. refuses reuse if there is an allocation marker, dispatch/consumed evidence, science run, execution-key prior use, competing positive claim, rerun history, or malformed/multiple failed-history evidence;
4. adds an authorization-head Actions quiet-window before the unchanged repository-global double enumeration;
5. changes no scientific design, seed values, case universe, atmosphere choice, photon budget, Level-B rule or result rule.

## #563 — MERGED
`Trigger fresh AVPS preauthorization after handoff metadata drift`

Merge commit / current main:

- `99ade7798627e67921139697ba1a004fa8a304bb`

This was mode-only and content-preserving, as described above.

---

# 0B. First ordinal-40 authorization attempt — failed safely and is historical only

## #560 — CLOSED / UNMERGED helper

Zero-runtime materializer on old main. It produced the old authorization artifact but allocated nothing and ran no solver.

## #561 — CLOSED / UNMERGED

First one-file ordinal-40 authorization candidate.

Authorization branch:

- `authorization/aerosol-vertical-profile-sensitivity-v1-ordinal-40`

Failed head:

- `67844e1dd2523963f2682f186387280dfb930760`

Authorization review run:

- `33109014744`
- attempt `1`
- conclusion `failure`

Passed before failure:

- exact one-file Draft identity;
- direct-child parent identity;
- exact parent-main preauthorization resolution;
- candidate ledger rebuild;
- tracked-tree candidate-seed scan.

Failed only at:

- repository-global two-pass stability.

Exact refusal:

> `snapshot-fenced repository-global metadata changed between two complete enumerations; refuse this audit and start a fresh attempt-1 workflow run`

There was:

- no candidate-seed collision finding;
- no Issue 60 allocation marker;
- no dispatch branch;
- no consumed marker;
- no AVPS science run;
- no result opening.

Therefore ordinal 40 was **not consumed and not allocated**.

The failed head is preserved at:

- `history/aerosol-vertical-profile-sensitivity-v1-ordinal-40-auth-review-failed-1`

Do not delete or rewrite this history ref.

---

# 0C. Why the first post-#562 preauthorization failed

After #562 merged at:

- `cd56db1e823a75d617c026fecf359a80e8c64cb7`

push preauthorization run:

- `33110552017`
- attempt `1`

failed closed during repository-global double enumeration.

This failure is fully explained and was **not scientific**:

- repository-global scan ran approximately `19:52:48Z` through `19:58:17Z`;
- the user-requested handoff update commit `471678a0bc12535d8dab70190b7081e835fd8671` was created at `19:57:54Z`;
- that repository-metadata write landed inside the two-pass scan window;
- the tracked-tree scan had passed;
- no candidate-seed collision was reported;
- no ordinal was allocated;
- no dispatch/science/results boundary was crossed.

Do **not** rerun that workflow as attempt 2. The project correctly used a fresh main identity instead.

---

# 0D. Authoritative fresh exact-main preauthorization — SUCCESS

PR #563 created the new exact-main identity without changing watched file bytes.

Fresh push-triggered preauthorization:

- run `33111875371`
- exact main `99ade7798627e67921139697ba1a004fa8a304bb`
- attempt `1`
- conclusion **SUCCESS**

All substantive gates passed:

1. exact attempt-1 main / zero-runtime identity;
2. deterministic control tests;
3. exact artifact-only candidate ledger;
4. exact-main tracked-tree candidate-seed scan;
5. repository-global candidate-seed double enumeration;
6. exact-main seed authorization proof;
7. fresh global ordinal proposal / preauthorization guard;
8. zero-runtime artifact upload;
9. terminal Issue 60 **non-allocation** checkpoint.

Fresh proof values:

- latest consumed global scientific ordinal: `39`
- next if separately allocated: `40`
- candidate seed count: `72`
- candidate seed canonical SHA-256: `a2e22b526dfad84d4f23c0ca8b143d028fddc7e55f78deb93a43e194ebd6c35e`
- candidate rows canonical SHA-256: `f22de8a9e30ba106759effb1170a5ca1d1e747cb2ac68293fa232dc7ed6ca683`
- tracked-tree external collision count: `0`
- repository-global collision count: `0`
- repository-global double enumeration stable: `true`
- audited branch head matches repository head: `true`
- all collision counters zero: `true`

Preauthorization report:

- status `PREAUTHORIZATION_SURFACE_CLEAN_NOT_ALLOCATED`
- report SHA-256 `12f8c7fe6cc7c5cbf36d320066d4a88e02695b541d2ffb0dae2e820961414175`

Artifact:

- ID `9663132186`
- name `vertical-profile-v1-preauthorization-proof`
- GitHub digest `sha256:1253612ffe4ba228e319f6b063256abd7340d11eec76981db4cc39a3619b2df6`
- downloaded ZIP SHA-256 independently rechecked and exactly identical to that digest.

The ZIP contains:

- `candidate-seed-ledger.json`
- `empty-self-ledger-policy.json`
- `freshness.json`
- `global-ordinal-observations.json`
- `preauthorization.json`
- `repository-global-seed-scan.json`
- `seed-authorization-proof.json`
- `tracked-files.nul`
- `tracked-seed-scan.json`

Critical flags remain:

- `scientificOrdinalAllocated=false`
- `authorizationCreated=false`
- `dispatchCreated=false`
- `scientificRuntimeSetupPerformed=false`
- `scientificExecutionPerformed=false`
- `solverExecutionPerformed=false`
- `resultOpeningPerformed=false`

Bottom line:

> ordinal 40 is now freshly proven to be the next available candidate, but it is still **not allocated**.

---

# 1. Immediate continuation order from this exact checkpoint

Follow this order exactly.

## Step 1 — materialize a NEW authorization document from artifact 9663132186

Do **not** reuse the old #561 authorization bytes because they bind old main/preauthorization identities.

Build a new `authorization.json` using the merged builder against:

- exact main `99ade7798627e67921139697ba1a004fa8a304bb`;
- preauthorization run `33111875371`;
- artifact `9663132186`;
- artifact digest `sha256:1253612ffe4ba228e319f6b063256abd7340d11eec76981db4cc39a3619b2df6`.

Materialization must remain zero-runtime and must not itself allocate ordinal 40.

## Step 2 — create a fresh one-file ordinal-40 authorization review

Reuse the intended branch identity only under the merged #562 failed-history rules:

- `authorization/aerosol-vertical-profile-sensitivity-v1-ordinal-40`

The new authorization head must be:

- a direct child of live main;
- exactly one changed file: `experiments/aerosol-vertical-profile-sensitivity-v1/authorization.json`;
- a fresh attempt-1 Draft PR;
- derived byte-for-byte from the new materialization;
- zero-runtime.

Before the repository-global authorization scan, the merged quiet-window barrier must settle sibling Actions metadata.

The review must pass:

- one-file/direct-child identity;
- exact successful parent-main preauthorization resolution;
- tracked-tree seed scan;
- repository-global stable double enumeration;
- fresh authorization guard/control surface.

## Step 3 — allocation marker only AFTER review success

Only after a successful new authorization review may exactly one Issue 60 marker be posted:

`ORDINAL40_AVPS_V1_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED commit=<AUTH_HEAD> parent=<AUTH_PARENT> pr=<PR_NUMBER>`

That marker is the allocation boundary.

Before it exists, never say ordinal 40 is allocated.

## Step 4 — dispatch is a separate transition

After allocation:

- run the separate dispatch freshness/control guard;
- create dispatch only through the reviewed publisher/guard;
- require the exact authorization head/parent/PR marker;
- create exactly one consumed marker after the dispatch transition succeeds;
- never use GitHub Re-run as a substitute for a fresh identity.

## Step 5 — science execution only after dispatch authorization

Only after all previous controls pass may the frozen 360-case MYSTIC campaign execute.

No adaptive/tuned cases may be added after results exist.

## Step 6 — results stay closed until exact aggregate validation

Do not inspect/open the scientific result payload until:

- all 360 cases exist;
- artifact/member hashes verify;
- exact runtime identities verify;
- case/attempt identities verify;
- 8001-node channels and derived quantities verify;
- exact-360 aggregate guard passes.

Primary result opening is a separate post-aggregate action.

---

# 2. Global scientific rules — DO NOT VIOLATE

- `F = 3.14` remains the current default.
- transient `tau = 30 s` remains experimental only.
- Never tune F, tau, AOD, aerosol profile, provider, forecast cycle, sky offset, threshold, interpolation/support, or another environmental input to force a desired Taylor/Jerusalem time.
- Never select an atmospheric dataset/cycle/provider because it minimizes a target residual.
- Freeze external/environmental choices before target scoring whenever possible.
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
- Do not reopen the closed exact-zenith / 90° MYSTIC-stellar campaign.

---

# 3. `starsvisibility` — important current scientific/software status

## #114 — MERGED
Validated Level-B sky + stellar support reaches exact zenith / 90° while preserving old <=80° behavior. Closed campaign; do not reopen.

## #118 — MERGED
Clean-checkout/current-main Level-B test lifecycle fix. Infrastructure only.

## #119 — MERGED
Frozen Crumey Eq.34 mesopic non-monotonic diagnostic:

- local maximum near `B = 0.0215673 cd/m²`
- local minimum near `B = 0.0470526 cd/m²`
- threshold drop ≈ `2.6009%`
- maximum formal negative adaptation penalty ≈ `-0.02861 mag`

## #116 — OPEN / DO NOT MERGE YET
It floors negative transient visibility penalties to equilibrium. That is a semantic/physiological model change, not a cleanup.

Before merge:

1. characterize actual `(physical B, adaptation debt, effective B)` trajectories;
2. decide mapping from external psychophysics;
3. preregister semantic criteria;
4. perform a complete post-decision timing audit;
5. exact-head parity/build.

## #117 — physical question remains open

Main question:

> Is physical detection background + equivalent adaptation luminance debt the correct mapping through the Crumey threshold relation?

Do not change production transient semantics before this is scientifically resolved.

---

# 4. Operational Atmosphere State v2

## #120 — MERGED design
Established component provenance, spectral AOD, vertical profile, SSA/phase/g, molecular/surface/cloud status, explicit missing/approximated/rejected/conflict semantics, historical/current/future modes, QC, and explicit v2 -> v1 projection.

## #121 — MERGED foundation

Merge commit:

- `e0da52eb0a2d5bac333da6572f51df52ea7e676e`

Implemented the representation/QC/provenance foundation.

Important limitation:

> richer v2 atmospheric fields are not yet generally consumed by the current fast Level-B sky model.

The central remaining engineering/scientific problem is mapping rich physical atmosphere into Level-B and independently validating that mapping against MYSTIC.

---

# 5. Old Draft PR #48

Do not merge/replay wholesale.

Core v1 atmosphere/acquisition files are already on current `starsvisibility` main and current-main regression binds important PR48 files.

Treat #48 as historical context only.

---

# 6. Taylor Ann Arbor — authoritative interpretation

Observation:

- Ann Arbor, Michigan
- 2025-08-07
- approx `42.256 N, 83.709 W`
- original Unihedron SQM at zenith

Current conclusion:

> Direct MYSTIC is broadly consistent with Taylor, and much of the old ~6° discrepancy was strongly reduced by using an independently obtained aerosol vertical distribution.

Key evidence:

At Sun `-5.808°`:

- old residual `+0.393 mag`
- CAMS-profile residual `+0.087 mag`

At Sun `-6.134°`:

- old residual `+0.388 mag`
- CAMS-profile residual `+0.031 mag`

No SQM offset or AOD was fitted.

Interpretation:

> total AOD alone is insufficient for maximum-accuracy twilight prediction; vertical aerosol placement materially changes twilight scattering as Earth shadow removes low layers.

Do not reinterpret this as proof that the exact Taylor atmosphere is known.

---

# 7. Taylor uncertainty and atmosphere provenance boundary

Empirical Taylor single-run MYSTIC scatter:

- row1 `0.00264 mag`
- row5 `0.00517`
- row9 `0.00709`
- row13 `0.00801`
- row17 `0.01100`
- row21 `0.02630`
- row24 `0.0704`
- row25 `0.0906`

Taylor repeatability term:

- about `0.06215 mag`

Late reconverged central residuals rows 23–25:

- `+0.08544`
- `+0.17350`
- `+0.17696 mag`

These late rows are not compelling standalone inconsistencies after uncertainty treatment.

AOD finite-difference derivative remains unresolved.

Approx same-cycle CAMS columns near Taylor:

- AOD550 ≈ `0.31–0.32`
- SSA550 ≈ `0.95`
- g550 ≈ `0.71`
- Ångström alpha ≈ `1.28`

But forecast00 vertical extinction returned 137 exact zero coefficients despite nonzero column AOD; forecast03 had valid profiles.

Therefore:

- forecast00 all-zero extinction is invalid;
- do not call a mixed run `same-cycle full CAMS` unless vertical fields are valid;
- height-uniform column SSA/g must be labeled approximation;
- never select forecast03 because it gives a better Taylor residual.

Independent Taylor atmosphere archive search remains a separate worker lane: EarthCARE/ATLID, lidar/ceilometer, AERONET, etc. Do not duplicate unless explicitly assigned.

HRRR:

- #487 owns scientific vertical-shape comparison;
- #489 is only a technical 550-nm smoke test.

---

# 8. Generalized aerosol vertical-profile sensitivity v1 — active principal lane

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
- observer 0 m only
- albedo 0.15
- 380–780 nm
- reviewed 1-nm grid
- MYSTIC spherical 1D
- VROOM
- MC std evidence
- 20,000,000 photons/case
- Sun depression 2°, 4°, 6°, 8°
- AOD550 0.10, 0.30
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

- paired Level-B limiting-magnitude delta through current Crumey Eq.34 path with `F=3.14`

No universal minute conversion. No adaptive post-result cases.

---

# 9. AVPS build-up and why the control sequence is strict

Relevant merged sequence includes:

- #549 reusable aerosol vertical-profile transport foundation
- #550 exact-runtime OPAC + custom tau compatibility
- #551 scientific preregistration
- #552 unseeded execution skeleton
- #557 frozen disabled execution package
- #558 authorization control
- #559 execution/analysis/result-opening control
- #562 failed-authorization reuse + quiet-window recovery
- #563 exact-blob mode-only fresh-preauthorization trigger

The long sequence is deliberate:

> scientific design, case identity, runtime identity, analysis rules, result-opening rules and authorization semantics are frozen before final identity allocation and before MYSTIC results exist.

Do not short-circuit this by manually running the 360 cases.

---

# 10. What AVPS is intended to answer

If the campaign executes successfully, it should quantify vertical-profile sensitivity independently of Taylor/Jerusalem residuals.

It should answer at the frozen geometry/AOD grid:

- how much V-band effective sky radiance changes when only normalized vertical optical-depth shape changes;
- how much photopic/scotopic channels change;
- how much current Level-B limiting magnitude moves under those independent radiance differences;
- whether a fast operational atmosphere mapping needs explicit vertical-profile sensitivity or can safely collapse some profile information in some domain.

It does **not** by itself validate a universal atmosphere-to-Level-B mapping.

---

# 11. Next scientific lanes after AVPS

Priority remains:

1. vertical aerosol profile sensitivity — current AVPS campaign;
2. spectral AOD sensitivity;
3. SSA sensitivity;
4. phase function / g sensitivity;
5. interactions among major aerosol dimensions;
6. then secondary atmosphere effects: pressure/temperature/ozone/water vapor/albedo/RH as warranted.

Provider/data choices and sensitivity ranges must be frozen independently of Taylor/Jerusalem target residuals.

---

# 12. Level-B mapping remains the central unresolved engineering question

Operational Atmosphere v2 can represent richer physical states, but the current fast model does not yet consume arbitrary rich atmosphere with demonstrated predictive equivalence to direct MYSTIC.

Desired end state:

1. acquire the best independently known atmosphere for place/time;
2. represent it without inventing missing components;
3. run direct MYSTIC when high fidelity is required;
4. map the same physical state into fast Level-B;
5. prove the fast mapping on preregistered MYSTIC cases independent of target observations;
6. only then use observational datasets such as Taylor as external validation.

---

# 13. Other later lanes

- Moon: draft/validation work remains later priority.
- Natural night background: draft work remains later priority.
- Artificial skyglow: provider/model still needed.
- Total sky compositor exists, but each component needs valid provenance/domain rules.
- Transient adaptation issue #117 remains scientifically unresolved and must not be silently changed while atmosphere work proceeds.

---

# 14. Reporting contract

Every scientific campaign/report should state explicitly:

- exact commit/head;
- exact frozen protocol;
- exact runtime/data identities;
- whether seeds were preauthorized before use;
- global scientific ordinal and allocation marker if applicable;
- whether MYSTIC ran;
- whether results were opened;
- atmosphere provenance;
- approximations/missing components;
- numerical uncertainty / MC scatter;
- whether the comparison is direct MYSTIC, Level-B, or human first-seeing;
- whether target observations were used for source/model selection.

Never collapse these layers into a vague statement that `the model matches observations`.

---

# 15. Current bottom line

The project is **not finished**, but AVPS has now crossed an important clean checkpoint:

- all scientific/runtime/analysis/result-opening rules are frozen;
- the failed first authorization is preserved and proven unallocated;
- failed ordinal 40 is safely reusable under merged fail-closed rules;
- the handoff-metadata race was identified exactly;
- a content-preserving fresh-main trigger was reviewed and merged;
- a new exact-main attempt-1 preauthorization has passed completely;
- 72 candidate seeds are proven clean;
- ordinal 40 is freshly proven next;
- **nothing has yet been allocated, dispatched, simulated or opened**.

Immediate task from this file:

> materialize a new `authorization.json` from run `33111875371` / artifact `9663132186`, then open a fresh exact one-file Draft authorization review for ordinal 40. Only after that review passes may the Issue 60 allocation marker be created. MYSTIC remains forbidden until the subsequent separate dispatch transition succeeds.
