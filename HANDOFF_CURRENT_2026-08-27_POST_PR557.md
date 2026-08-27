# STAR VISIBILITY / MYSTIC — CURRENT NEW-WORKER HANDOFF

**Current status: 2026-08-27, after AVPS control freeze #559 and during failed-authorization recovery #562**

This file supersedes the older post-#557 checkpoint. It is the current standalone handoff for continuing the non-observation computational/scientific work without repeating closed lanes or crossing scientific-control boundaries.

---

# 0. Exact current checkpoint — read this first

## Repository

`search-maker/twilight-mystic-experiments`

Current `main`:

- `107d63a01de96bc359af0ecd8f0129b7232ddcf1`
- merge commit of PR #559, `Freeze AVPS execution, analysis, and result-opening controls`.

## What is already merged after the older handoff

### #558 — MERGED
`Add current-main AVPS authorization control gate`

Merge commit:

- `608359c645aaa2ff184124ee718c09e971d5e13b`

It bound authorization construction to the exact merged #557 disabled execution package and AFGL evidence, required exact one-file Draft authorization review, and made control-byte changes force a new exact-main preauthorization.

### #559 — MERGED
`Freeze AVPS execution, analysis, and result-opening controls`

Merge commit:

- `107d63a01de96bc359af0ecd8f0129b7232ddcf1`

It froze the remaining AVPS v1 science transport before identity allocation:

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
- execution contract byte-binding all transport/runtime identities.

No scientific run was performed by #558 or #559.

---

# 0A. Fresh exact-main preauthorization that DID pass

After #559 merged, a fresh attempt-1 exact-main preauthorization ran with no repository writes during its critical scan.

Run:

- `33107919037`
- exact main: `107d63a01de96bc359af0ecd8f0129b7232ddcf1`
- attempt: 1
- conclusion: **SUCCESS**

Fresh proof:

- latest consumed global scientific ordinal: `39`
- next candidate if separately allocated: `40`
- candidate CRN seeds: `72`
- tracked-tree candidate-seed collisions: `0`
- repository-global candidate-seed collisions: `0`
- double enumeration stable: `true`
- scientific identity allocated: `false`

Preauthorization artifact:

- ID `9661482182`
- ZIP digest `sha256:25bd8f20ddd45ab606a794bf22183d27634a4d6ae4e30819267aa1c8a79f062e`

Important:

> This proof says ordinal 40 was the fresh next candidate. It did **not** allocate ordinal 40.

There was still no Issue 60 allocation marker, no dispatch branch, no MYSTIC science run, and no result opening.

---

# 0B. Authorization materialization and failed first authorization review

## #560 — CLOSED / UNMERGED helper only

`Materialize current-main AVPS authorization candidate`

- base: exact main `107d63a01de96bc359af0ecd8f0129b7232ddcf1`
- helper head: `db9b0cce0e3f6b2d03991bbdf0c443a1459ac3ee`
- zero-runtime only
- no identity allocation
- no dispatch
- no libRadtran/MYSTIC
- no results

Materializer run passed and produced authorization artifact:

- artifact ID `9661587430`
- digest `sha256:eb912439...` (use GitHub artifact metadata for the complete digest if needed)

The produced `authorization.json` bound the exact fresh preauthorization, frozen 360-case/72-CRN design, 20M photons/case, exact AFGL tau hashes, execution-control workflow bytes, current Level-B identity and `F=3.14`.

It explicitly had:

- `dispatchAuthorized=false`
- `resultOpeningAuthorized=false`
- `productionAuthorized=false`

#560 was intentionally closed unmerged after artifact production.

## #561 — CLOSED / UNMERGED first ordinal-40 authorization candidate

Branch:

- `authorization/aerosol-vertical-profile-sensitivity-v1-ordinal-40`

Head:

- `67844e1dd2523963f2682f186387280dfb930760`

The Git blob of `authorization.json` was verified identical to the materialized artifact before opening the PR.

Authorization review run:

- `33109014744`
- attempt 1
- conclusion: **FAILURE — fail closed**

What passed before failure:

- exact one-file Draft authorization identity;
- direct-child parent identity;
- exact successful parent-main preauthorization resolution;
- candidate ledger rebuild;
- exact authorization-head tracked-tree seed scan.

Where it failed:

- `Stable authorization-head repository-global seed recheck`

Exact failure reason:

> `snapshot-fenced repository-global metadata changed between two complete enumerations; refuse this audit and start a fresh attempt-1 workflow run`

This was **not a seed collision** and **not a bad authorization document**.

The race happened because sibling pull-request workflows for the same authorization head were being created/completing while the two full repository enumerations were in progress.

Critical boundary:

- NO Issue 60 allocation marker was posted;
- NO dispatch branch was created;
- NO consumed marker exists;
- NO AVPS scientific execution ran;
- NO result was opened;
- ordinal 40 therefore remains unconsumed/unallocated.

#561 is closed and unmerged.

The failed head is deliberately preserved as immutable history at:

- `history/aerosol-vertical-profile-sensitivity-v1-ordinal-40-auth-review-failed-1`

Do not delete this history evidence.

---

# 0C. Active recovery — #562

PR #562:

`Recover AVPS failed authorization review without consuming ordinal 40`

Branch:

- `fix/avps-v1-failed-auth-review-recovery-1`

Latest head at this handoff update:

- `82a3e5390c28f5dbf9078b085c904879ce47d211`

Purpose:

1. preserve the failed #561 head as historical evidence;
2. prove ordinal 40 is reusable only because the failed review was terminal attempt-1, closed/unmerged, and had no allocation/dispatch/science evidence;
3. add an authorization-head Actions quiet-window barrier before the unchanged repository-global double-enumeration audit;
4. keep all scientific design and all seed/case/result rules unchanged.

Recovery refuses reuse if any of these appear:

- allocation marker;
- dispatch branch;
- consumed marker;
- scientific execution run;
- execution-key prior use;
- competing positive ordinal claim;
- rerun/non-attempt-1 authorization review history;
- malformed/multiple failed-history evidence.

The first #562 CI head (`0092d2f...`) had:

- AVPS main-preauthorization review: PASS
- AVPS scientific review: PASS
- current-main authorization-control tests: PASS
- 4/5 failed-authorization recovery tests: PASS
- one recovery test: FAIL because the test searched for the wrong literal `${head}` while the workflow correctly used Python `{head}`.

That test-only typo was fixed in head:

- `82a3e5390c28f5dbf9078b085c904879ce47d211`

No recovery logic changed in that fix.

**Do not merge #562 until all current-head gates pass.**

---

# 1. Immediate continuation order

Follow this order exactly.

## Step 1 — finish #562 review

- wait for current-head PR workflows on `82a3e539...`;
- inspect any failure before merge;
- confirm no scientific/runtime/result boundary was crossed;
- if all gates pass, mark #562 ready and merge with expected-head protection.

## Step 2 — after #562 merge, stop repository writes during exact-main preauthorization

The merge will change `main`, deliberately invalidating the old exact-main preauthorization `33107919037`.

A fresh push-triggered AVPS exact-main preauthorization must pass on the new merge commit.

During its repository-global double enumeration:

> do not create/update branches, PRs, comments, issues, handoffs, or other repository metadata.

Read-only observation is fine.

The new preauthorization must prove again:

- exact new main;
- 72 candidate seeds;
- zero tracked-tree collisions;
- zero repository-global collisions;
- stable double enumeration;
- fresh global ordinal still 40 under the failed-history recovery rules;
- no allocation/dispatch/science/result boundary crossed.

## Step 3 — materialize a new authorization document from the NEW proof

Do not reuse the old `authorization.json` bytes from #561 because its parent/preauthorization bindings point to old main `107d63...`.

Use the merged builder against the new exact-main preauthorization artifact.

A zero-runtime helper/materializer is acceptable, but must not allocate identity or execute science.

## Step 4 — reuse ordinal 40 through a fresh one-file authorization PR

The intended authorization branch name remains:

- `authorization/aerosol-vertical-profile-sensitivity-v1-ordinal-40`

The branch may be moved to the new exact one-file child commit only after the failed #561 head has been preserved under the history ref above and recovery gates are merged.

Open a **new** Draft authorization PR.

Requirements:

- direct child of live main;
- exactly one changed file: `experiments/aerosol-vertical-profile-sensitivity-v1/authorization.json`;
- attempt 1 only;
- authorization-head tracked-tree scan;
- authorization-head repository-global double enumeration;
- sibling-Actions stabilization barrier first;
- zero runtime;
- no marker before review success.

## Step 5 — allocate only after successful authorization review

Only after the new authorization review is fully successful may one exact Issue 60 marker be posted:

`ORDINAL40_AVPS_V1_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED commit=<AUTH_HEAD> parent=<AUTH_PARENT> pr=<PR_NUMBER>`

The marker itself is the allocation boundary.

Before that marker exists, do not claim ordinal 40 is allocated.

## Step 6 — dispatch remains separate

After allocation marker:

- re-run the dispatch freshness/control checks;
- create the dispatch transition only through the reviewed publisher/guard;
- exactly one consumed marker after successful dispatch transition;
- no manual bypass;
- no rerun as a substitute for fresh attempt-1 identity.

## Step 7 — results remain closed until exact aggregate validation

Even after MYSTIC execution begins, do not inspect/open scientific results until:

- all 360 cases are present;
- all artifact/member hashes verify;
- exact runtime identities verify;
- all attempts/case identities verify;
- derived channels verify;
- aggregate guard passes.

Primary result opening is a separate post-aggregate action.

---

# 2. Global scientific rules — DO NOT VIOLATE

- `F = 3.14` remains the current default.
- transient `tau = 30 s` remains experimental only.
- Do not tune F, tau, AOD, aerosol profile, provider, forecast cycle, sky offset, threshold, interpolation/support, or another environmental parameter to force a desired Jerusalem/Taylor time.
- Do not select an atmospheric dataset/cycle/provider because it minimizes Taylor residuals.
- Freeze external/environmental inputs before target scoring whenever possible.
- No universal magnitude correction.
- No universal minute correction.
- Do not infer aerosol family from AOD alone.
- Do not fabricate missing vertical aerosol structure.
- Missing/invalid atmosphere data must remain explicit and fail closed or reduce confidence.
- Do not call modeled fields measurements.
- A CAMS republisher is not an independent scientific source from CAMS.
- No `humanFirstSeeingValidated` claim without independent human evidence.
- Taylor mainly validates direct MYSTIC, not Level-B or human first-seeing.
- Pandora/Izaña remain unopened unless separately authorized.
- matched-stellar v1 is obsolete.
- Do not reopen the closed 90° MYSTIC/stellar campaign.

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
It floors negative transient visibility penalties to equilibrium. That is a semantic/physiological model change, not a software cleanup.

Before merge:

1. characterize actual `(physical B, adaptation debt, effective B)` trajectories;
2. decide mapping from external psychophysics;
3. preregister semantic criteria;
4. perform complete post-decision timing audit;
5. exact-head parity/build.

## #117 — physical question still open

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

Implemented representation/QC/provenance foundation.

Important limitation:

> richer v2 atmospheric fields are not yet generally consumed by the current fast Level-B sky model.

The remaining engineering/scientific problem is not merely acquiring richer atmosphere data; it is mapping that state into Level-B and validating the mapping independently against MYSTIC.

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

# 7. Taylor Monte Carlo uncertainty

Empirical single-run scatter from the dedicated multi-seed screen:

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

AOD finite-difference derivative remains unresolved. Do not reuse an old large derivative as a precise physical derivative.

---

# 8. Taylor CAMS provenance boundary

Approx same-cycle columns near Taylor:

- AOD550 ≈ `0.31–0.32`
- SSA550 ≈ `0.95`
- g550 ≈ `0.71`
- Ångström alpha ≈ `1.28`

But forecast00 vertical extinction returned 137 exact zero coefficients despite nonzero column AOD; forecast03 had valid profiles.

Therefore:

- forecast00 all-zero extinction is invalid;
- do not call a mixed run `same-cycle full CAMS` unless vertical fields are genuinely valid;
- height-uniform column SSA/g must be labeled approximation;
- never select forecast03 because it gives a better Taylor residual.

Independent Taylor atmosphere archive search is a separate worker lane: EarthCARE/ATLID, lidar/ceilometer, AERONET, etc. Do not duplicate that lane unless explicitly assigned.

HRRR:

- #487 owns the scientific vertical-shape comparison;
- #489 is only a technical 550-nm smoke test.

---

# 9. Generalized aerosol vertical-profile sensitivity v1 — active principal lane

Scientific question:

> At fixed total AOD550 and fixed coherent OPAC rich optical properties/phase function, how much does independently specified normalized aerosol vertical optical-depth shape change twilight radiance and the derived Level-B limiting-magnitude endpoint?

This is not a Taylor fit.

Frozen states:

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

# 10. AVPS merged build-up before authorization

Relevant merged sequence includes:

- #549 reusable aerosol vertical-profile transport foundation
- #550 exact-runtime OPAC + custom tau compatibility
- #551 scientific preregistration
- #552 unseeded execution skeleton
- subsequent control/profile/evidence work
- #557 frozen disabled execution package
- #558 authorization control
- #559 execution/analysis/result-opening control

The purpose of the long control sequence is deliberate:

> all scientific design, case identity, runtime identity, analysis rules, result-opening rules, and authorization semantics must be frozen before fresh seeds/ordinal are finally allocated and before MYSTIC results exist.

Do not short-circuit this by manually running the 360 cases.

---

# 11. What AVPS is intended to answer

If the campaign executes successfully, the result should quantify vertical-profile sensitivity independently of Taylor/Jerusalem residuals.

It should answer, at the frozen geometry/AOD grid:

- how much V-band effective sky radiance changes when only normalized vertical optical-depth shape changes;
- how much photopic/scotopic channels change;
- how much current Level-B limiting magnitude would move under those independent radiance differences;
- whether a fast operational atmosphere mapping needs explicit vertical-profile sensitivity or can safely collapse some profile information in some domain.

It does **not** by itself validate a universal atmosphere-to-Level-B mapping.

---

# 12. Next scientific lanes after AVPS

Priority remains:

1. vertical aerosol profile sensitivity — current AVPS campaign;
2. spectral AOD sensitivity;
3. SSA sensitivity;
4. phase function / g sensitivity;
5. interactions among major aerosol dimensions;
6. then secondary atmosphere effects: pressure/temperature/ozone/water vapor/albedo/RH as warranted.

Provider/data choices and sensitivity ranges must be frozen independently of Taylor/Jerusalem target residuals.

---

# 13. Level-B mapping remains the central unresolved engineering question

Operational Atmosphere v2 can represent richer physical states, but the current fast model does not yet consume arbitrary rich atmosphere with demonstrated predictive equivalence to direct MYSTIC.

The desired end state is:

1. acquire the best independently known atmosphere for place/time;
2. represent it without inventing missing components;
3. run direct MYSTIC when high fidelity is required;
4. map the same physical state into fast Level-B;
5. prove the fast mapping on preregistered MYSTIC cases independent of target observations;
6. only then use observational datasets such as Taylor as external validation.

---

# 14. Other later lanes

- Moon: draft/validation work remains later priority.
- Natural night background: draft work remains later priority.
- Artificial skyglow: provider/model still needed.
- Total sky compositor exists, but components must each have valid provenance/domain rules.
- Transient adaptation issue #117 remains scientifically unresolved and should not be silently changed while atmosphere work proceeds.

---

# 15. Reporting contract

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
- whether any target observations were used for source/model selection.

Never collapse these layers into one vague statement that `the model matches observations`.

---

# 16. Current bottom line

The project is **not finished**, but the AVPS lane is much closer to a clean scientific execution than at the post-#557 checkpoint.

What is now frozen:

- AVPS scientific design;
- 360-case universe;
- 72-CRN structure;
- profile transport;
- OPAC/custom-tau syntax;
- disabled package;
- authorization control;
- execution control;
- aggregate verification;
- result-opening rules;
- Level-B endpoint rule with `F=3.14`.

What happened at #561:

> authorization review failed safely because repository metadata changed during the double enumeration. It did not discover a seed collision and did not allocate or execute anything.

What #562 is doing:

> preserve that failure as auditable history, reuse ordinal 40 only under fail-closed proof, and prevent sibling Actions creation from racing the next authorization-head snapshot.

Immediate task:

> finish #562 gates, merge only if clean, run a new exact-main preauthorization with repository writes frozen, rebuild authorization from that new proof, then perform a fresh one-file ordinal-40 authorization review. Do not post an allocation marker or dispatch anything before that review passes.
