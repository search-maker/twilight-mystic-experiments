# STAR VISIBILITY / MYSTIC — LIVE CURRENT HANDOFF

**Live refresh: 2026-08-28 — v5 single-species transport PASS; `continental_average` source audit PASS; four-species transport PR #592 under review.**

The filename is historical. This content is the current computational/scientific checkpoint.

## 1. Immutable baseline

Repository: `search-maker/twilight-mystic-experiments`

Frozen `main` remains:

`99ade7798627e67921139697ba1a004fa8a304bb`

Frozen main tree:

`2d4bb1df136bff2da93f191e5518b94b3d7fecfc`

Do not move `main` merely to continue this lane.

## 2. Ordinal 40 is consumed and scientifically non-informative

AVPS ordinal 40 was executed, recovered to 360/360 case artifacts, and opened. Its state contrasts were exactly zero, but raw matched-group audit proved that the intended vertical-profile state did **not** reach effective solver physics: state-specific profile files differed while solver outputs were byte-identical across states.

Authoritative classification:

`EXECUTION/EVIDENCE PIPELINE VALID; SCIENTIFIC VERTICAL-PROFILE CONTRAST NON-INFORMATIVE.`

Never reuse/rerun ordinal 40 and never cite its zero contrast as evidence of vertical-profile insensitivity.

Retained ordinal-40 evidence:

- recovery science run `33139545997` SUCCESS, 360/360 cases
- Gate-0 artifact `9676069031`, digest `sha256:70dedcd16209dea74a9ed67a1dc7377c123f1a62fd18741b1e15692702011fc8`
- Phase A `33170006532` SUCCESS
- Phase B result opening `33170855407` SUCCESS

## 3. Resolver diagnosis chain — terminal identities, never rerun

### v2 / PR #586

- review head `d90d3bca966d566d328fc1d91fb44f65c58d12b4`
- review `33172089158` SUCCESS
- contract `33172089150` SUCCESS
- one-shot run `33177704575` FAILURE
- artifact `9688346720`
- digest `sha256:adb10217279e27e2ca9101ab92b7a4467805c113438f6c7dc7552d0354938b21`
- deterministic transport failed with `found neither netcdf nor ASCII optical property files`; MYSTIC never ran

### v3 / PR #587

Tested byte-identical official `inso.mie.cdf` at failed alias `aerosol/OPAC/optprop/INSO.nc`.

- reviewed head `a396714a851d371a584ed4d4d2bd8e83765d05c4`
- review `33179715436` SUCCESS
- contract `33179715434` SUCCESS
- one-shot run `33180158034` FAILURE
- artifact `9689369400`
- digest `sha256:3549c546cf2517b9d9603f4f7eafcef7ca8a8f37fb59f25fb8721ec4e63b7201`

### v4 / PR #588

Tested the same official bytes at failed alias `aerosol/OPAC/INSO.nc`.

- reviewed head `7b2a2f7ae14a7777408ab36de65fcc4a91b4a8de`
- review `33180739737` SUCCESS
- contract `33180739633` SUCCESS
- control `ded92d780f949165ffd41062c7717bd42f399069`
- request head `1bb66dbedd28b31b5d295729ca2cdc9da927031b`
- one-shot run `33184511183` FAILURE
- artifact `9691137631`
- digest `sha256:b538b58a44873eca3eebd64493edf3d9b88991e73ccb48f0d5e71ff1c9f2aee4`

V2-v4 are terminal consumed capability identities. Do not GitHub-rerun them.

## 4. Resolver syscall trace / PR #589 — diagnostic SUCCESS

PR #589 froze an ordinal-free, LOW-only, no-alias `strace` diagnostic.

- review head `d2f78f8be3fb94e4e64ce4c12901cb3f937ef0b6`
- review `33185082374` SUCCESS
- review artifact `9691331443`, digest `sha256:72f868ded8693f47c4e476391735bb1dfd73aaacca3dfe63fcd2da4bf4f715da`
- contract `33185082300` SUCCESS
- control `28191b88daafc858e96ab098c1df01962211169b`
- request head `a266d1d3705c41519d3930206ca4f918db9cbb9e`
- one-shot diagnostic run `33185460954` SUCCESS
- artifact `9691518729`
- digest `sha256:07fb60de7bef96253eaf29cb9303a83bab7f3f1952431c73a26499357b4d572a`

Critical direct runtime observation:

```text
.../data/aerosol/OPAC/optprop/INSO
```

The locked binary attempted that pathname **with no extension**, received ENOENT, and then emitted the unresolved-optical-property error. This explains the v3/v4 failures.

Do not rerun the trace identity.

## 5. OPAC single-species transport capability v5 / PR #590 — PASS

PR #590 remains Draft/open/unmerged on exact review head:

`f0675ec48c637509cd7a5bb9c2a2746507e5bea8`

Review gates:

- dedicated review `33186027699`, attempt 1 — SUCCESS
- review artifact `9691708991`, digest `sha256:b60a16626a0e8e1ce39adb50f200fe2e487667e97cf8b2c5198b26f27436fb1f`
- repository contract `33186027637`, attempt 1 — SUCCESS

Activation:

- workflow blob `ec73ff112b209786a2b3b6aa48fe2e4d2cc9e103`
- builder blob `5fd3067d4840dad6c0ff5d68ae76327a05499190`
- validator blob `c68fd7b48f322dcfac3cd39e0227a3aa794ed016`
- control `f41a619368fde6a48005cb3c44b52cee6b4d3a62`
- request head `6f0d61aa3abf7e6e113853fbfc1c74e65d31dac9`
- run `33186446347`, attempt 1 — SUCCESS
- artifact `9691923455`, digest `sha256:fed6bb961088232e593159c4f50911758802e9209aed86e2a0eef4b403e4d9b7`
- report content SHA-256 `da6d7f66625b63cb5ff4f69845c2953f2a509b3693c82d1f0203900dc7bd21d2`
- terminal status `PASS_TRACE_OBSERVED_ALIAS_REACHES_DISORT_AND_MYSTIC`

Exact resolver correction proven by v5:

- source `aerosol/OPAC/optprop/inso.mie.cdf`
- solver alias `aerosol/OPAC/optprop/INSO`
- source/alias SHA-256 `fe10348cbe585315d6e1db382563fdc054204ad35846f371dc9d8abeead36407`
- alias byte count `1595764`
- failed `.nc` aliases absent
- pre-alias tree `5d8bbf8e6b91ec3d405dee36f21a94afbb6e5ec6cd67da2dd5dd541738199d80`
- post-alias tree `346c8f825759d8e975568b14ccbd125f6efcb1126c574c72163b8b948169456c`

DISORT LOW/HIGH: 401 finite same-grid rows, non-identical.

- LOW `c888ca29085b0111ccf36f41e37b78fd205224f1d08c00e65e67b58e4cb59dd1`
- HIGH `cd715c254bd78e00b9c945d0163c17e18b5d1f991d863e4065f7de16f8a09b8f`

MYSTIC LOW/HIGH: 401 finite same-grid radiance rows, non-identical.

- LOW `009877d8afb26ea7682a8b65ed060449fbfa672c37aa35afce8d33d9eb86f18a`
- HIGH `2e5cf494a9cf0da8b27368038f07305b0faa5fa7f099b02430c2340ed5243bb2`

Interpretation boundary: v5 proves single-species explicit mass-density transport only. It does not establish scientific effect size, materiality, realistic `continental_average` composition, or Level-B readiness.

Do not rerun v5.

## 6. Locked `continental_average` source audit / PR #591 — PASS

PR #591:

`Audit locked OPAC continental_average species profile source v1`

- Draft/open/unmerged
- branch `review/opac-continental-average-species-profile-audit-v1`
- exact head `2bfae9341075eb04fe4621f4f53d4ab56262c22b`
- dedicated run `33187119926`, attempt 1 — SUCCESS
- repository contract `33187119866`, attempt 1 — SUCCESS
- artifact `9692162280`
- artifact digest `sha256:cdcb0041a5197e31ff24520b3e653119d11c5d4a1c1b4f727e392ba7e719101e`
- exact source `data/aerosol/OPAC/standard_aerosol_files/continental_average.dat`
- source SHA-256 `fc39fda0f8ada2d0a0a872b8b62d684cfccd74f7b0655b5af2dcdec51115e469`
- 1075 bytes, 23 lines, 14 numeric rows, 5 numeric columns

The exact species-column header is:

```text
z(km)  inso  waso  soot  suso
```

Therefore the replacement scientific AVPS cannot silently substitute single-species INSO if it intends to preserve the original preregistered fixed OPAC `continental_average` optical family.

The source file itself notes that libRadtran expresses mass concentrations corresponding to OPAC at 50% RH rather than copying OPAC number concentrations directly. This source audit is evidence, not authorization for a humidity interpretation.

Existing AFPF official-source/runtime-overlay evidence already freezes the relevant optical-property assets:

- INSO `inso.mie.cdf` — `fe10348cbe585315d6e1db382563fdc054204ad35846f371dc9d8abeead36407`
- WASO `waso.mie.cdf` — `b6df493b77019bf5e22456e8fb8858c5a7d502bcc02fe6fc697ebd4844f2d4f5`
- SOOT `soot.mie.cdf` — `44a0d2060101ca52c90ae64f005118dfba256b1f89a3049e1f758c55d634aa02`
- SUSO `suso.mie.cdf` — `ce0e1bba4219c60af0af14d66a280b0d3d25188276eed0951d31594b947cd472`

## 7. Current active gate — PR #592 four-species transport capability

Fresh branch/ordinal audit after v5 found:

- no branch containing ordinal 41;
- no replacement-AVPS branch;
- ordinal 40 remains the latest known consumed scientific ordinal.

**Ordinal 41 remains unallocated.**

PR #592:

`Review OPAC continental_average multispecies transport capability`

- Draft/open/unmerged
- branch `review/opac-continental-average-multispecies-transport-capability-v1`
- exact current review head `18667797a1dd699b6431a6940bac42974c415733`
- base frozen main `99ade7798627e67921139697ba1a004fa8a304bb`
- exactly five new review/inactive files
- no active capability workflow on the review branch
- no scientific ordinal or scientific seed
- no Taylor/Jerusalem scoring
- no Level-B or production mutation

The capability freezes only this question: can the locked runtime resolve and transport one explicit profile binding **all four** species `INSO WASO SOOT SUSO`, using byte-identical no-extension aliases for the four official assets, through DISORT and then MYSTIC?

Synthetic LOW/HIGH profiles deliberately use equal positive mass weight 0.25 for each species only to exercise every dependency. This is **not** the `continental_average` composition and must never be reused as the scientific mixture rule.

Frozen capability settings otherwise retain v5 values: AOD550 0.10, 540-560 nm, DISORT SZA 80 deg, MYSTIC SZA 96 deg, target altitude 30 deg, relative azimuth 90 deg, albedo 0.15, 500000 photons/profile, paired capability seed 730194613.

Review runs created for exact head `18667797...`:

- dedicated review `33188868496` — queued at this handoff refresh
- repository-wide contract `33188868323` — queued at this handoff refresh

### Activation rule

Do **not** activate #592 unless both exact-head runs complete attempt 1 with conclusion `success`, PR #592 remains Draft/open/unmerged on the same head, frozen main remains unchanged, and no parallel multispecies activation appeared.

If both pass, create a fresh one-shot status identity from frozen main containing exactly the reviewed inactive workflow plus reviewed builder and activation validator, then a separate request commit bound to #592 exact head and dedicated review run. Only one push-triggered execution is allowed; never GitHub-rerun it.

PASS requires:

- exact frozen runtime/archive/source identities;
- exact #591 four-species source columns;
- four official source hashes;
- four byte-identical no-extension aliases and no `.nc` aliases;
- syntax success;
- finite same-grid non-identical LOW/HIGH DISORT outputs;
- only then finite same-grid non-identical LOW/HIGH MYSTIC radiance outputs.

A PASS would prove four-species transport readiness only. It would still not freeze the scientific `continental_average` mixture rule or humidity semantics.

## 8. Scientific design after #592 — still review-only before ordinal allocation

Only after a #592 capability PASS may the replacement AVPS scientific preregistration be written.

The original independently selected five OPAC-derived vertical templates remain the starting scientific question:

1. `opac-profile-continental-average` reference: first layer H=2 km, Z=8 km; first-layer tau550 0.133; free troposphere 0.013; stratosphere 0.005.
2. `opac-profile-maritime-clean`: H=2 km, Z=1 km; first-layer tau550 0.078; free troposphere 0.013; stratosphere 0.005.
3. `opac-profile-desert`: H=6 km, Z=2 km; first-layer tau550 0.268; free troposphere 0.013; stratosphere 0.005.
4. `opac-profile-arctic`: H=2 km, Z=99 km; first-layer tau550 0.045; free troposphere 0.013; stratosphere 0.005.
5. `opac-profile-antarctic`: H=10 km, Z=8 km; first-layer tau550 0.054; free troposphere 0.013; stratosphere 0.005.

The old implementation method (`aerosol_species_file continental_average` plus `aerosol_file tau`) is forbidden because ordinal 40 proved it did not transport the intended vertical contrast.

The replacement must separately freeze how the exact four-species `continental_average` mixture is mapped into each independently defined vertical template, including an explicit humidity/mixture interpretation, before seed or ordinal allocation. Do not derive that rule from Taylor/Jerusalem residuals.

Original frozen science screen to preserve unless changed **before** seeds/results with independent justification:

- AFGL-US, observer 0 m, albedo 0.15
- wavelengths 380-780 nm, 1 nm calculation grid
- MYSTIC spherical 1D, VROOM, standard output
- 20M photons/case
- sun depression 2, 4, 6, 8 deg
- AOD550 0.10 and 0.30
- three geometries: alt/azrel 10/30, 30/90, 45/180
- 3 replicates
- 24 cells, 72 CRN groups, 5 states/group, 360 cases
- same fresh CRN seed across five states within each group
- photopic/scotopic/Johnson-V primary channels
- paired log alternative/reference primary contrasts
- mean, sample SD and SE over three paired replicates; no p-values/CIs/epsilon substitution
- no adaptive case addition or post-result rule change

Only after review-only scientific preregistration and transport representation are frozen should Issue #60 and all branch namespaces be re-audited again and a fresh scientific ordinal (currently expected 41) be allocated in a separate authorization review.

## 9. Hard prohibitions

Do not:

- rerun/reuse ordinal 40;
- allocate ordinal 41 before the replacement scientific preregistration is frozen and reviewed;
- reuse any ordinal-40 case/seed identity with patched inputs;
- GitHub-rerun v2 `33177704575`, v3 `33180158034`, v4 `33184511183`, trace `33185460954`, or v5 `33186446347`;
- amend a consumed one-shot identity and pretend it is the reviewed run;
- infer scientific effect size from capability runs;
- use the #592 synthetic equal 0.25 mass weights as a scientific `continental_average` composition;
- select scientific profile states/mixture/humidity/provider/cycle using Taylor/Jerusalem residual fit;
- reintroduce competing `aerosol_file tau` beside the explicit species profile;
- use failed `.nc` aliases;
- proceed to Level-B profile mapping before replacement scientific evidence;
- move `main` for convenience;
- create production authorization from a capability PASS alone.

## 10. Broader retained project state

- AOPS ordinal 37, AFPF ordinal 38, and ASIV ordinal 39 remain closed for their stated scopes and should not be duplicated.
- Taylor #508 remains evidence that independently constrained aerosol vertical structure can materially alter direct-MYSTIC twilight radiance.
- Taylor atmosphere provenance/uncertainty boundaries #535/#529/#536 remain authoritative.
- Better independent Taylor-night atmosphere acquisition is a separate lane and must not be used to fit residuals.
- Anti-fitting rules remain binding.

## 11. Resume checklist

- [ ] confirm `main == 99ade7798627e67921139697ba1a004fa8a304bb`;
- [ ] confirm #590 remains Draft/open/unmerged on `f0675ec48c637509cd7a5bb9c2a2746507e5bea8`;
- [ ] confirm #591 remains Draft/open/unmerged on `2bfae9341075eb04fe4621f4f53d4ab56262c22b`;
- [ ] confirm #592 remains Draft/open/unmerged on `18667797a1dd699b6431a6940bac42974c415733`;
- [ ] fetch final attempt-1 conclusions for #592 dedicated review `33188868496` and repo contract `33188868323`;
- [ ] search again for parallel #592/multispecies status work before activation;
- [ ] activate only if both exact-head gates are green, and only once;
- [ ] preserve the #592 artifact regardless of PASS/FAIL and never rerun the consumed identity;
- [ ] after capability PASS, preregister the actual four-species scientific mixture/humidity mapping before any ordinal or seed allocation;
- [ ] re-audit Issue #60/branches immediately before later allocation;
- [ ] keep Taylor/Jerusalem residuals closed throughout design and gating;
- [ ] update this handoff after #592 review completion, activation/result, scientific preregistration, ordinal allocation, authorization, dispatch, Gate-0 and result opening.

## 12. One-line live status

**Ordinal 40 remains scientifically non-informative. The no-extension resolver fix is proven for INSO by v5, #591 proves the locked `continental_average` source actually binds INSO/WASO/SOOT/SUSO, and #592 is now the active ordinal-free gate testing all four species together through DISORT→MYSTIC. Ordinal 41 remains unallocated; scientific preregistration and Level-B work are still blocked until multispecies transport and then the actual fixed-mixture/humidity mapping are separately frozen.**
