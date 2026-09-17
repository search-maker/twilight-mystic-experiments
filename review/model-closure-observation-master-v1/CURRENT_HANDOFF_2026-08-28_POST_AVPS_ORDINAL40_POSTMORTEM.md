# STAR VISIBILITY / MYSTIC — CURRENT HANDOFF

Updated: **2026-08-28 after AVPS ordinal-40 exact360 execution, Phase A aggregation, Phase B preregistered opening, and raw-input postmortem**

Status: **authoritative new-worker handoff / review-only record**. This file does not change production behavior, `F`, transient `tau`, atmosphere selection, Level-B routing, or empirical-validation claims.

---

# 1. Project objective

Build a physically defensible star-visibility model that can predict when a specific star becomes visible under real atmospheric conditions and can support halachic twilight analysis.

The project has two distinct computational layers:

1. **Direct libRadtran/MYSTIC** — high-fidelity radiative transfer used as the physics reference.
2. **Level-B** — the fast operational model used by the star-visibility application.

Do not conflate them. A richer atmosphere can be represented in Operational Atmosphere State v2 without automatically being consumed by Level-B. Direct MYSTIC validation is not automatically Level-B validation, and neither is automatically human first-seeing validation.

Main repositories:

- `search-maker/starsvisibility`
- `search-maker/twilight-mystic-experiments`

---

# 2. Hard scientific rules

These remain binding unless independent evidence justifies a change:

- default human field factor `F = 3.14`;
- transient `tau = 30 s` remains experimental/shadow-only;
- no tuning of `F`, tau, AOD, vertical profile, aerosol family, SSA, phase/g, provider/cycle, SQM offset, time offset, interpolation or stop rules to move Taylor/Jerusalem toward a desired result;
- atmosphere/data-source choice must be independent of target residuals;
- freeze source/time/distance/quality acceptance criteria before target scoring when possible;
- AOD alone must not select aerosol family;
- do not fabricate vertical aerosol structure;
- modeled/forecast/reanalysis fields are not measurements;
- a republisher of CAMS is not an independent scientific source from CAMS;
- clouds fail closed unless independently validated;
- no universal magnitude or minute correction;
- Taylor SQM validates direct MYSTIC sky radiance, not Level-B or human first-seeing;
- Pandora/Izaña remain unopened unless separately authorized;
- old matched-stellar v1 is obsolete;
- richer atmosphere fields must not be claimed to affect Level-B until a validated mapper actually consumes them.

---

# 3. Major already-closed work — do not duplicate

## starsvisibility

- #114 merged — exact zenith Level-B/stellar support.
- #118 merged — clean-checkout Level-B current-main test lifecycle.
- #119 merged — Crumey Eq.34 non-monotonic transient diagnostic frozen.
- #120 merged — Operational Atmosphere State v2 design.
- #121 merged — v2 data/QC/provenance foundation after broad exact-head verification.
- #100 merged — shadow-only five-state aerosol scenario envelope for the already validated scalar/derived Level-B scenario lane.

## Aerosol science already completed

- AOPS ordinal 37 — controlled SSA/scalar-g sensitivity.
- AFPF ordinal 38 — realistic OPAC full phase/family sensitivity.
- ASIV ordinal 39 — scalar/derived Level-B aerosol scenario interpolation/transport validation.

Do not reopen generic SSA/g, generic full phase/family, or the already-closed scalar fast-scenario work from scratch.

## Transient adaptation

- #116 remains open and **must not be merged yet**.
- issue #117 remains the governing science question.
- #119 froze the Eq.34 diagnostic but did not validate a replacement semantic mapping.

Next transient step remains characterization of actual `(physical B, adaptation debt, effective B)` Level-B trajectories, followed by a separately justified psychophysical mapping and preregistered shadow validation.

---

# 4. Taylor Ann Arbor — current authoritative interpretation

Observation case:

- observer: Aster G. Taylor;
- date: 2025-08-07;
- location about `42.256 N, 83.709 W`, elevation about 262 m;
- original Unihedron SQM, not SQM-L;
- zenith pointing;
- observations roughly 20:30–21:30 EDT every ~2 minutes;
- timing uncertainty about +/-30 s;
- dataset 1 in `AnnArbor.csv`.

## What Taylor established

Replacing the old simplified aerosol vertical distribution with an independently obtained CAMS vertical extinction **shape** while holding the other frozen quantities substantially reduced the important onset-region MYSTIC–Taylor residuals:

- Sun `-5.808 deg`: about `+0.393 -> +0.087 mag`;
- Sun `-6.134 deg`: about `+0.388 -> +0.031 mag`.

No SQM offset or AOD was fit to Taylor.

Therefore vertical aerosol structure can be materially important. This does **not** prove the exact Taylor atmosphere and does not make Taylor “solved.”

## Taylor numerical uncertainty

Empirical MYSTIC/ALIS multi-seed scatter grows toward late twilight:

- row1 ~`0.00264 mag`;
- row5 ~`0.00517`;
- row9 ~`0.00709`;
- row13 ~`0.00801`;
- row17 ~`0.01100`;
- row21 ~`0.02630`;
- row24 ~`0.0704`;
- row25 ~`0.0906`.

Taylor observational repeatability is about `0.06215 mag`.

Late reconverged residuals were approximately:

- row23 `+0.08544`;
- row24 `+0.17350`;
- row25 `+0.17696 mag`.

Those late rows are not strong standalone evidence of a gross model inconsistency after uncertainty. The AOD finite-difference derivative remains unresolved; do not reuse the old derivative.

## CAMS provenance boundary

Same-cycle column/spectral optics near Taylor were plausible:

- AOD550 ~`0.31–0.32`;
- SSA550 ~`0.95`;
- g550 ~`0.71`;
- Angstrom alpha ~`1.28`.

But forecast00 vertical extinction returned 137 exact zeros despite nonzero AOD, while forecast03 contained a physically usable profile. Therefore do not call a mixed state “same-cycle full CAMS” until the vertical component is genuinely resolved. Column SSA/g applied uniformly with altitude is an explicit approximation.

A separate archival-data lane continues to search EarthCARE/ATLID, ground lidar/ceilometer, AERONET and other independent atmosphere sources. Do not select a source/cycle because it fits Taylor residuals.

---

# 5. Operational Atmosphere State v2

The representation/QC foundation is now largely separated from fast-model consumption.

Current v2 can represent and provenance:

- spectral/column AOD;
- Angstrom information;
- vertical extinction/backscatter/profile shape;
- SSA spectrum;
- phase/g;
- aerosol classification;
- molecular/surface/cloud components;
- component-level provenance, completeness and QC;
- scientific source separately from service provider.

Important fail-closed rules include:

- reject negative AOD/extinction/backscatter;
- reject non-monotone profile geometry;
- reject invalid SSA/g bounds;
- reject nonzero AOD paired with an all-zero matching extinction profile;
- profile-vs-column inconsistency requires an explicit policy, not a hidden tolerance;
- two CAMS republishers count as one underlying source;
- richer v2 components projected to v1 are marked unconsumed rather than silently claimed to affect Level-B.

The principal remaining fast-model atmosphere problem is still how to map validated richer atmosphere dimensions into Level-B.

---

# 6. AVPS ordinal 40 — exact execution history

This was the first generalized preregistered aerosol vertical-profile sensitivity campaign. It was designed to test vertical shape at fixed column AOD and fixed aerosol optical family over an independent small OPAC-derived profile universe.

Frozen design:

- 5 vertical profile states;
- 24 analysis cells;
- 3 replicates per cell;
- 72 CRN groups;
- 360 MYSTIC cases;
- 20M photons/case;
- primary channels: photopic luminance, scotopic luminance, Johnson-V effective radiance;
- reference state: `opac-profile-continental-average`;
- alternatives: maritime-clean, desert, arctic, antarctic;
- no Taylor/Jerusalem scoring;
- no p-values, CI, epsilon substitution, universal degree-to-minute conversion, or result-derived production threshold.

## Frozen main/authorization identity

- parent/main: `99ade7798627e67921139697ba1a004fa8a304bb`;
- authorization PR #565 head: `338ee82c8e088e929f45782b1f7ac1c3aaaaa533`;
- scientific ordinal: `40` — consumed exactly once and must not be reused.

## Original Stage-B execution

Original run `33137514692` passed the scientific/runtime preflight and reached real MYSTIC but failed because the executor required diagnostic stdout/stderr streams to be non-empty. `uvspec -c` may legitimately emit empty diagnostic streams. The run was cancelled through reviewed control run `33138196230`. No valid partial result was opened or reused.

## Recovery

Recovery review PR #576:

- head `9d6f98eeef858e81cb644990ef6b1659083bca0c`;
- dedicated review run `33139327182` SUCCESS;
- repository contract run `33139327179` SUCCESS.

Recovery changed only the transport/evidence rule for four diagnostic files: they must exist and remain hashed but may be zero bytes. Scientific/raw outputs remained mandatory and non-empty.

Recovery run:

- branch `status/avps-v1-stage-b-executor-recovery-ordinal-40`;
- request head `6d0e0e0f1dd1deabaf8bb155ee7e323c5ba8673d`;
- run `33139545997`;
- attempt 1;
- SUCCESS;
- exact 360 case artifacts produced.

Gate-0 metadata artifact:

- ID `9676069031`;
- ZIP digest `sha256:70dedcd16209dea74a9ed67a1dc7377c123f1a62fd18741b1e15692702011fc8`;
- inner metadata SHA-256 `323f458b43a031c50f2c2f74971594801608a5cdf437839c8760b42c19bdb92e`;
- exactly 360 unique case artifacts;
- `caseContentsDownloaded=false`;
- `aggregateResultsCalled=false`;
- `openResultsCalled=false`;
- `scientificInterpretationPerformed=false`.

---

# 7. Post-360 gates — Phase A and Phase B

Protocol PR #579 preregistered the post-360 procedure before any primary result was opened.

## Phase A — closed aggregation

Review PR #584:

- exact head `b93c284c8a24296dff9d8aedc265f7a3bdec465a`;
- dedicated review run `33169583131` SUCCESS;
- repository-wide contract `33169583043` SUCCESS.

One-shot Phase-A run:

- branch `status/avps-v1-post360-phase-a-ordinal-40`;
- request head `17537a2a5d60d7836eb9a1e01169a5bab5c70ea2`;
- run `33170006532`;
- attempt 1;
- SUCCESS.

Phase A verified all 360 source ZIP hashes against Gate-0, independently verified recovery provenance, then ran frozen `aggregate_results.py` once. Results remained closed.

Phase-A output artifact:

- ID `9685308839`;
- digest `sha256:68216d6a4982618d8cf9238948f0cbeb651bc9cde7ce53e688b5b1b11d204148`;
- receipt content hash `c14ef76e6280bdd34172202c63e8a319b4044cdb647e348926c02d03160198e4`;
- acquisition content hash `b3d4ac428ced54e217721507c36e349511ef0b4478f5815af7fe557fed005541`;
- analysis-input content hash `c58907c2f838396417edcfe87d306c130b92374b649790ff25537f3ac049bdc8`;
- analysis-input raw SHA-256 `b1c2d82e53c91606854c6ae0fea4d6e08d959dd3ee26ac080d0ee62ad4a4096b`.

## Phase B — preregistered primary opening

Review PR #585:

- exact head `31c09366aafd12ef666f5c747e416df6ba4ead52`;
- dedicated review run `33170557531` SUCCESS;
- repository contract `33170557454` SUCCESS.

One-shot Phase-B run:

- branch `status/avps-v1-post360-phase-b-ordinal-40`;
- request head `0edd0936ab30a6dbb7d9799302c81758973947b6`;
- run `33170855407`;
- attempt 1;
- SUCCESS;
- frozen result opener called exactly once.

Primary-results artifact:

- ID `9685531261`;
- digest `sha256:e2db9625387a4102cccc616bc2aa351b64aa1df0b14cb22978a810b352e47f04`;
- primary content hash `41424239a6c6630c894c1d3f48cf65d675a454cc3660d275f33442043e3e85e2`;
- raw primary-results SHA-256 `1cf030dad71887e480a4fc81bb4713acc56db0ac659927c37310db8c7f95c85d`;
- no Taylor/Jerusalem scoring;
- no Level-B mapping;
- no production routing.

---

# 8. CRITICAL: ordinal 40 is scientifically non-informative

The opened primary result contains:

- 24 analysis cells;
- 3 primary channels;
- 4 alternative-vs-reference contrasts;
- 288 primary summaries total.

**Every one of the 288 means is exactly `0.0`.**

Also:

- every replicate contrast is exactly `0.0`;
- every sample SD is exactly `0.0`;
- every standard error is exactly `0.0`.

Further audit of the Phase-A analysis input shows that in **72/72 CRN replicate groups**, the derived observables for all five profile states are exactly identical within that replicate, while the three independent replicates differ from one another. Thus the random seeds are functioning, but the profile state does not alter solver output.

This is **not** a physical null result.

---

# 9. Raw-pair audit proving the profile files changed but solver physics did not

Matched group audited:

`dep20-aod10-g02-early-near-low-rep1`

Compared artifacts:

- continental-average artifact ID `9673599809`;
- desert artifact ID `9673619290`.

The input files differ exactly where expected:

- different `mc_basename`;
- different `aerosol_file tau profiles/<state>.tau` path.

`case.inp` SHA-256:

- continental `f9461e543f5a06ff80d8ccd5ceeb6b064013b7d6cef3fc91324a325ceebe573d`;
- desert `f7e19a648e9ce3c7254e1551412ac173d0702615bb5ada208f2bbe4c5b6610d0`.

The actual tau profiles are materially different.

Tau-file SHA-256:

- continental `e6c296951dfae376bf77948aa92828062ba95d7b1e9c28703befa9cffb5bf198`;
- desert `3d8891b3b67fa8c8c6fd66861d49e9bfad8c937a176b7001c6c47a5571de21ad`.

Examples near the ground:

- continental layer share at 1 km ~`0.4129`, at 0 km ~`0.4679`;
- desert layer share at 2 km ~`0.1427`, at 1 km ~`0.2353`, at 0 km ~`0.3880`, with much more optical depth also spread through 3–6 km.

Despite this, the raw solver products are byte-identical between the two states:

- `mc.rad.spc`: `10533cfa0a4f63b9b8a617edc9613e9150e72dd306bb5795d441d2c489d1a54c`;
- `mc.rad.std.spc`: `a2eaa9b3679ca6ceb285f3dc644350599c0a639f86d34bafba3c73d1d52235f3`;
- `mc.flx.spc`: `be511ec2db2387ff20fb45729ca8794e96f5c090a63dd0d52694edb750b0066d`;
- `mc.flx.std.spc`: same `be511ec2...`;
- solver stdout: `be2da8b36f1829aa2098be32dcc34f37c1245db5ab27c81ac09cb76c3814a786`;
- random seed is identical within the CRN group as intended.

Therefore the custom profile bytes were created and referenced, but they did not survive into effective solver aerosol physics.

---

# 10. Root-cause diagnosis: libRadtran aerosol precedence

The current ordinal-40 input uses:

```text
aerosol_default
aerosol_species_library OPAC
aerosol_species_file continental_average
aerosol_file tau profiles/<state>.tau
aerosol_set_tau_at_wvl 550 <fixed AOD>
```

libRadtran documents aerosol configuration as **hierarchical**: parameters lower in the documented hierarchy overwrite values from higher entries. The documented hierarchy places `aerosol_species_file` below / at higher precedence than `aerosol_file tau`.

The same manual also explains that `aerosol_species_file` defines the vertical mass-density profiles of the aerosol species mixture and that default mixtures such as `continental_average` can be invoked directly.

Thus the attempted combination was conceptually invalid for isolating custom vertical tau while simultaneously using the default OPAC `continental_average` species profile: the fixed `aerosol_species_file continental_average` supplies its own vertical profile and supersedes the custom `aerosol_file tau` profile.

This exactly matches the raw evidence: state-specific tau files differ, but the solver result is identical because every state retains the same `continental_average` species profile.

Official reference: libRadtran User's Guide, aerosol hierarchy / `aerosol_file` / `aerosol_species_file` sections (current guide at `https://www.libradtran.org/doc/libRadtran.pdf`).

## Classification

Ordinal 40 must be classified as:

> **EXECUTION/EVIDENCE PIPELINE VALID; SCIENTIFIC VERTICAL-PROFILE CONTRAST NON-INFORMATIVE DUE TO AEROSOL DIRECTIVE PRECEDENCE.**

Do not report “profile effect = 0.”

Do not use ordinal 40 as evidence for or against vertical-profile materiality.

Do not silently edit and rerun under ordinal 40.

---

# 11. Correct next scientific task

Before a replacement sensitivity campaign, run a **solver-capability diagnostic** whose only purpose is to prove that the chosen libRadtran representation actually changes vertical aerosol structure while keeping the intended optical family fixed.

This diagnostic is not a Taylor/Jerusalem fit and should not use target residuals.

Required acceptance evidence:

1. same geometry, AOD, wavelength grid, photon budget and seed;
2. two deliberately distinct vertical profiles chosen before output inspection;
3. exact input/profile provenance archived;
4. effective aerosol layer optics must demonstrably differ in the intended way;
5. solver raw radiance must not remain byte-identical solely because a higher-precedence directive silently replaced the profile;
6. any new optical-family approximation must be explicitly stated;
7. only after the capability passes may a new 360-style profile-sensitivity design be authorized.

## Candidate representations to evaluate independently

### Candidate A — custom `aerosol_species_file` profiles

Use the OPAC species library as intended, but generate the **mass-density profile file itself** so the vertical distribution is the controlled variable. Keep the species composition/family fixed independently. This is attractive because `aerosol_species_file` then owns the vertical profile rather than competing with `aerosol_file tau`.

Need to verify:

- how to preserve a fixed mixture/species ratio over altitude;
- how to normalize to exact AOD550 independently;
- whether OPAC spectral/full-phase properties remain fixed as intended;
- how to archive the generated mass-density profiles and effective optical-depth verification.

### Candidate B — `aerosol_file explicit`

Construct explicit per-layer spectral optical properties with the desired vertical extinction distribution and fixed SSA/phase family. This gives maximal control but requires a careful generator and independent byte/physics validation.

Do not choose A vs B because one matches Taylor better. Choose based on libRadtran semantics, scientific isolation, auditability and numerical support.

---

# 12. Replacement AVPS rules

A corrected profile-sensitivity campaign must be a **new experiment identity**:

- fresh scientific ordinal;
- fresh immutable authorization;
- fresh case universe and seeds;
- new execution contract binding the corrected representation;
- preregistered profiles/geometries/AODs/endpoints before result opening;
- no reuse of ordinal-40 zero contrasts as priors or acceptance targets;
- no Taylor/Jerusalem scoring during design selection;
- retain CRN pairing, raw spectra, numerical diagnostics and exact artifact provenance;
- retain separate Phase-A aggregation and Phase-B result-opening gates.

Only after a valid generalized vertical-profile sensitivity result exists should Phase C / fast Level-B vertical-profile mapping proceed.

---

# 13. Level-B vertical-profile mapping — currently BLOCKED on corrected MYSTIC sensitivity

Operational Atmosphere State v2 can store vertical aerosol information, but current Level-B still does not consume it.

Possible future mapper architectures remain open:

- parameterized profile correction;
- explicit profile-basis/surrogate dimension;
- scenario/set-valued envelope;
- hybrid precomputed MYSTIC table;
- separate column optics + normalized profile-shape state.

Do not choose an architecture before corrected direct-MYSTIC sensitivity and runtime-cost analysis.

After a candidate mapper exists, validate it on held-out direct-MYSTIC atmosphere states before any production claim.

---

# 14. Other parallel lanes

## Independent Taylor atmosphere

Continue EarthCARE/ATLID, lidar/ceilometer, AERONET and other truly independent archival atmosphere searches. Freeze product/time/distance/QC before target residual scoring.

## HRRR

Vertical-shape comparison is already owned by the HRRR lane; do not convert smoke mass directly to calibrated extinction and do not duplicate the technical-smoke path as science.

## Moon / natural night / artificial skyglow

Remain important but secondary. No constant universal dark-sky floor and no scalar artificial-light value should be promoted into directional radiance without its own validation.

## Human visibility / F

Keep `F=3.14` pending independent human evidence. Lowering F would make predicted visibility earlier and cannot fix an already-too-early concern.

---

# 15. Immediate priority order

## P0 — freeze ordinal-40 postmortem

1. Keep #584 and #585 Draft/open/unmerged as review evidence.
2. Keep Phase-A/Phase-B one-shot artifacts immutable.
3. Record ordinal 40 as non-informative, not as a null physical result.
4. Preserve raw matched-pair evidence proving tau input changed while solver outputs were identical.

## P1 — libRadtran capability correction

5. Build a separately reviewed diagnostic for the aerosol directive-precedence problem.
6. Compare scientifically valid ways to control vertical profile while keeping optical family fixed.
7. Require a raw-level proof that vertical profile actually reaches the solver.

## P2 — replacement generalized MYSTIC sensitivity

8. Preregister the corrected experiment under a fresh ordinal.
9. Allocate fresh immutable CRN seeds only after review.
10. Execute once and preserve exact raw artifacts.
11. Aggregate/open through separate gates.

## P3 — fast model

12. Only if corrected sensitivity is material, design Level-B vertical-profile mapping.
13. Validate on held-out direct MYSTIC.
14. Keep production/default routing false pending empirical real-sky evidence.

## Parallel

15. Continue independent Taylor atmosphere acquisition.
16. Continue #117 transient-mapping science.
17. Continue Moon/natural/artificial lanes as capacity permits.

---

# 16. Do NOT do next

Do not:

- claim ordinal 40 proves vertical structure is irrelevant;
- reuse ordinal 40 or its zero contrasts as a scientific PASS;
- rerun ordinal 40 after silently deleting `aerosol_species_file`;
- choose a corrected representation based on Taylor/Jerusalem fit;
- lower F;
- tune transient tau;
- tune AOD/profile/provider/cycle/offset;
- infer aerosol family from AOD;
- fabricate vertical structure;
- call modeled fields measurements;
- count CAMS republishers as independent evidence;
- reuse the old Taylor AOD derivative;
- reopen generic SSA/g/full-family science already closed by ordinals 37–39;
- imply richer v2 atmosphere already affects Level-B;
- merge #116 before #117 science;
- begin Phase-C Level-B profile mapping from invalid ordinal-40 zero results.

---

# 17. Central current conclusion

There is still no evidence here of a gross basic failure of spherical MYSTIC twilight physics.

Taylor remains strong evidence that knowing the **actual vertical aerosol structure** can materially improve twilight prediction.

The generalized ordinal-40 campaign successfully demonstrated that the project's execution/evidence machinery can carry a full 360-case MYSTIC study through immutable recovery, exact artifact freezing, aggregation and preregistered result opening. But it also exposed a crucial scientific-interface mistake:

> the custom `aerosol_file tau` profile was superseded by the fixed higher-precedence `aerosol_species_file continental_average`, so all five nominal profile states produced the same effective aerosol physics.

Therefore the immediate modeling task is now narrower and clearer:

> **Correct and independently validate the libRadtran representation that isolates vertical aerosol shape at fixed optical family, then repeat the generalized sensitivity experiment under a fresh scientific identity.**

Only after that valid MYSTIC result exists should the project decide whether and how Level-B should consume vertical aerosol structure.
