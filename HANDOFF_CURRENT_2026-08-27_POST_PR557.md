# STAR VISIBILITY / MYSTIC — LIVE CURRENT HANDOFF

**Live refresh: 2026-08-28 — four-species OPAC transport capability #592 PASS; scientific ordinal 41 still unallocated; next gate is exact mixture/RH-to-tau representation.**

The filename is historical. This content is the current computational/scientific checkpoint.

## 1. Immutable baseline

Repository: `search-maker/twilight-mystic-experiments`

Frozen `main`:

`99ade7798627e67921139697ba1a004fa8a304bb`

Frozen main tree:

`2d4bb1df136bff2da93f191e5518b94b3d7fecfc`

Do not move `main` merely to continue this lane.

## 2. Scientific ordinal state

AVPS scientific ordinal 40 is consumed and must never be reused or rerun.

Ordinal-40 execution/evidence recovery reached exact 360/360 cases, but state-specific vertical-profile files differed while solver outputs were byte-identical across states. Therefore the intended profile contrast did not reach effective solver physics.

Authoritative classification:

`EXECUTION/EVIDENCE PIPELINE VALID; SCIENTIFIC VERTICAL-PROFILE CONTRAST NON-INFORMATIVE.`

Do not cite ordinal-40 zero contrast as physical profile insensitivity.

Retained evidence:

- recovered science run `33139545997` SUCCESS, 360/360 cases
- Gate-0 artifact `9676069031`, digest `sha256:70dedcd16209dea74a9ed67a1dc7377c123f1a62fd18741b1e15692702011fc8`
- Phase A `33170006532` SUCCESS
- Phase B result opening `33170855407` SUCCESS

Fresh audits before #592 found no ordinal-41 branch/marker and no replacement-AVPS branch. **Ordinal 41 remains unallocated.** Re-audit Issue #60 and branch namespaces immediately before any future allocation.

## 3. Resolver diagnosis history — consumed identities, never rerun

- v2 / PR #586 — run `33177704575` FAILURE, artifact `9688346720`, unresolved optical-property file before MYSTIC.
- v3 / PR #587 — tested `aerosol/OPAC/optprop/INSO.nc`; run `33180158034` FAILURE, artifact `9689369400`.
- v4 / PR #588 — tested `aerosol/OPAC/INSO.nc`; run `33184511183` FAILURE, artifact `9691137631`, digest `sha256:b538b58a44873eca3eebd64493edf3d9b88991e73ccb48f0d5e71ff1c9f2aee4`.
- path trace / PR #589 — run `33185460954` SUCCESS, artifact `9691518729`, digest `sha256:07fb60de7bef96253eaf29cb9303a83bab7f3f1952431c73a26499357b4d572a`.

The trace directly observed the locked binary attempting:

```text
.../data/aerosol/OPAC/optprop/INSO
```

with **no extension**. This explained the `.nc` failures.

Never GitHub-rerun any of these consumed identities.

## 4. Single-species corrected transport / PR #590 — PASS

PR #590 remains Draft/open/unmerged on review head:

`f0675ec48c637509cd7a5bb9c2a2746507e5bea8`

- dedicated review `33186027699` SUCCESS
- repository contract `33186027637` SUCCESS
- one-shot run `33186446347`, attempt 1 — SUCCESS
- artifact `9691923455`
- digest `sha256:fed6bb961088232e593159c4f50911758802e9209aed86e2a0eef4b403e4d9b7`
- report content SHA-256 `da6d7f66625b63cb5ff4f69845c2953f2a509b3693c82d1f0203900dc7bd21d2`
- status `PASS_TRACE_OBSERVED_ALIAS_REACHES_DISORT_AND_MYSTIC`

Corrected resolver representation:

- official source `aerosol/OPAC/optprop/inso.mie.cdf`
- byte-identical alias `aerosol/OPAC/optprop/INSO`
- SHA-256 `fe10348cbe585315d6e1db382563fdc054204ad35846f371dc9d8abeead36407`

DISORT and MYSTIC LOW/HIGH were finite, same-grid, and non-identical. This proves single-species profile transport only; it does not define realistic `continental_average` composition or scientific effect size.

Do not rerun v5.

## 5. Locked `continental_average` source audit / PR #591 — PASS

PR #591 remains Draft/open/unmerged:

- review head `2bfae9341075eb04fe4621f4f53d4ab56262c22b`
- dedicated audit `33187119926` SUCCESS
- repository contract `33187119866` SUCCESS
- artifact `9692162280`
- digest `sha256:cdcb0041a5197e31ff24520b3e653119d11c5d4a1c1b4f727e392ba7e719101e`
- exact source `data/aerosol/OPAC/standard_aerosol_files/continental_average.dat`
- source SHA-256 `fc39fda0f8ada2d0a0a872b8b62d684cfccd74f7b0655b5af2dcdec51115e469`
- 1075 bytes; 14 numeric rows; 5 numeric columns

Exact species columns:

```text
z(km)  inso  waso  soot  suso
```

Therefore a replacement AVPS intended to preserve the original fixed OPAC `continental_average` family cannot silently use INSO alone.

The source file states that libRadtran uses mass concentrations corresponding to OPAC at 50% RH. Separately, libRadtran documentation states that soluble OPAC species have humidity-dependent optical properties and `uvspec` selects properties closest to the background humidity profile. This humidity behavior must be frozen explicitly before scientific execution.

Frozen official asset identities already supported by prior AFPF source/overlay evidence:

- INSO `inso.mie.cdf` — `fe10348cbe585315d6e1db382563fdc054204ad35846f371dc9d8abeead36407`
- WASO `waso.mie.cdf` — `b6df493b77019bf5e22456e8fb8858c5a7d502bcc02fe6fc697ebd4844f2d4f5`
- SOOT `soot.mie.cdf` — `44a0d2060101ca52c90ae64f005118dfba256b1f89a3049e1f758c55d634aa02`
- SUSO `suso.mie.cdf` — `ce0e1bba4219c60af0af14d66a280b0d3d25188276eed0951d31594b947cd472`

## 6. Four-species transport capability / PR #592 — PASS

PR #592:

`Review OPAC continental_average multispecies transport capability`

- Draft/open/unmerged
- review branch `review/opac-continental-average-multispecies-transport-capability-v1`
- exact review head `18667797a1dd699b6431a6940bac42974c415733`
- base frozen main `99ade7798627e67921139697ba1a004fa8a304bb`
- dedicated review `33188868496`, attempt 1 — SUCCESS
- review artifact `9692863411`, digest `sha256:7417f68ad2cbc1e77bcf109bc34dd996d27bdf866d73e64c9666e43bc2c13c6e`
- repository contract `33188868323`, attempt 1 — SUCCESS

Reviewed activation blobs:

- workflow `31dbcfd2d2ccd67b840538898abcd310a22f678f`
- builder `4462d44805d2e447ff9bd046da96aa221659cf74`
- validator `9622eb3418cb19e54e2c7cb26e00bccb652632bc`

Activation identity:

- activation tree `b35b8bd4ca7fec608a0c42c1b5714e686d7cd7f6`
- control commit `d504ec4c6c1e0943e53de6d0038f88104a49c131`
- status branch `status/opac-continental-average-multispecies-transport-capability-v1`
- request head `3e76e70ae81771e10477689df32085da1193659c`
- exactly one push run `33189268483`, attempt 1 — **SUCCESS**
- artifact `9693056690`
- artifact digest `sha256:f1a2cd69420c63d5214f5082ee0844ec822b9aa2f9f8f13a4b52958ee59ae507`
- report content SHA-256 `6f191c0011c67bc3aeb27add17c25f9c81fd356bb47f42141e7783f6ac52e973`
- terminal status `PASS_FOUR_CONTINENTAL_SPECIES_REACH_DISORT_AND_MYSTIC`

Exact no-extension aliases proven byte-identical:

- INSO: `aerosol/OPAC/optprop/INSO`, 1,595,764 bytes, SHA `fe10348cbe585315d6e1db382563fdc054204ad35846f371dc9d8abeead36407`
- WASO: `aerosol/OPAC/optprop/WASO`, 7,236,612 bytes, SHA `b6df493b77019bf5e22456e8fb8858c5a7d502bcc02fe6fc697ebd4844f2d4f5`
- SOOT: `aerosol/OPAC/optprop/SOOT`, 163,972 bytes, SHA `44a0d2060101ca52c90ae64f005118dfba256b1f89a3049e1f758c55d634aa02`
- SUSO: `aerosol/OPAC/optprop/SUSO`, 13,693,828 bytes, SHA `ce0e1bba4219c60af0af14d66a280b0d3d25188276eed0951d31594b947cd472`

Runtime tree:

- pre-alias `5d8bbf8e6b91ec3d405dee36f21a94afbb6e5ec6cd67da2dd5dd541738199d80`
- post-four-alias `5e1814dd36cf861fd85477a97607299248f8272268df7bf428d31bbb6aa4354a`

DISORT LOW/HIGH: 401 finite same-grid rows, non-identical.

- LOW `0f0e2e4d2759dd8ec19ef632bdd3a8bef6dd115d6d31b24ac17a975978a04fad`
- HIGH `61651b1abfef92bf6d9e7eea59ea33d0b8035b11e1f99f3787e5169059395c78`

MYSTIC LOW/HIGH: 401 finite same-grid radiance rows, non-identical.

- LOW `91a7dbc68bf3f44be9cc3985556a5b17e1aa668ea8cd9267068d47a11bb63e6e`
- HIGH `1e8a459d3d76135a42696290bd5554e9c0fd27cdb8803add1d3a724cd84210d3`
- LOW std `47e198883bf2750c10d0a42028cc0ae1fa1d5bc396ce0af12c79ed89deb3e1cb`
- HIGH std `65939f05377c1bf3b7cfe6b964dda135d957d7ab352e5d3d5b2278e583cd520a`

Interpretation boundary: #592 proves only that all four `continental_average` component species can be transported together through explicit mass-density profiles into both DISORT and MYSTIC. The synthetic equal 0.25 mass weights were capability-only and are **not** a scientific composition.

Do not rerun #592.

## 7. Current scientific representation problem — next gate, no ordinal yet

The old preregistered scientific question remains:

> At fixed total AOD550 and fixed OPAC `continental_average` wavelength-dependent aerosol optical properties/phase function, quantify sensitivity to independently defined vertical optical-depth shape.

The five independently selected OPAC-derived vertical templates remain:

1. reference `opac-profile-continental-average`: H=2 km, Z=8 km, first-layer tau550 0.133, free-troposphere 0.013, stratosphere 0.005;
2. `opac-profile-maritime-clean`: H=2 km, Z=1 km, first-layer 0.078, free 0.013, stratosphere 0.005;
3. `opac-profile-desert`: H=6 km, Z=2 km, first-layer 0.268, free 0.013, stratosphere 0.005;
4. `opac-profile-arctic`: H=2 km, Z=99 km, first-layer 0.045, free 0.013, stratosphere 0.005;
5. `opac-profile-antarctic`: H=10 km, Z=8 km, first-layer 0.054, free 0.013, stratosphere 0.005.

The old implementation surface is permanently forbidden:

```text
aerosol_species_file continental_average
aerosol_file tau <state>
```

because ordinal 40 proved the custom tau state did not survive precedence.

### Preferred representation principle to review next

The most faithful correction is to preserve the exact **local species ratios as a function of altitude** from the locked `continental_average.dat`, under the same frozen AFGL-US background humidity profile, and vary only the local amount of that mixture to realize each preregistered target tau550 vertical template.

Operationally, at each altitude the four species densities should remain a common nonnegative scalar multiple of the locked standard-mixture vector. This preserves the predefined mixture composition and OPAC humidity-dependent optical lookup at that altitude; it does not invent a new constant 0.25 or column-integrated composition.

However, mass density is not itself optical depth. Because WASO/SUSO optical properties vary with RH and mixture mass-extinction can vary with altitude, the new renderer must **prove**, rather than assume, that the generated species mass profiles realize the intended normalized 550-nm optical-depth fractions.

### Required next evidence before scientific preregistration is final

Create a review/source audit that freezes from the exact official OPAC assets:

- the 550-nm extinction/mass-extinction representation for INSO/WASO/SOOT/SUSO;
- all available RH nodes for soluble species;
- exact interpretation/units used by the locked runtime;
- the frozen AFGL-US background humidity profile or an exact runtime-observed equivalent used to select RH-dependent optics.

Then create/review a renderer that:

1. takes only the already-preregistered five target tau550 templates;
2. preserves the local `continental_average.dat` species ratios at each altitude;
3. uses the frozen/runtime-consistent 550-nm extinction coefficients to choose the common local mass scaling;
4. emits one explicit four-species mass-density profile with no competing `aerosol_file tau`;
5. is independently validated at 550 nm (preferably against `uvspec verbose` optical-property profiles or another exact runtime readback) to reproduce the target normalized vertical tau fractions within a preregistered tight numerical tolerance;
6. keeps `aerosol_set_tau_at_wvl 550` as the separate fixed column-AOD normalization;
7. refuses any Taylor/Jerusalem-driven adjustment.

Only after that representation is frozen/reviewed should the replacement AVPS science protocol be finalized.

## 8. Original science screen to preserve unless independently changed before seeds/results

- AFGL-US, observer 0 m, albedo 0.15
- wavelength 380–780 nm; 1-nm calculation grid; expected raw 0.05-nm output support
- MYSTIC spherical 1D, VROOM, standard deviation output
- 20M photons/case
- sun depression 2, 4, 6, 8 deg
- AOD550 0.10 and 0.30
- geometries: alt/azrel 10/30, 30/90, 45/180
- 3 replicates
- 24 cells; 72 CRN groups; 5 states/group; 360 cases
- same fresh CRN seed across five states within each group
- primary photopic, scotopic and Johnson-V channels
- paired log alternative/reference primary contrasts
- mean, sample SD and SE over 3 paired replicates; no p-values/CIs/epsilon substitution
- no adaptive case addition or post-result rule change
- full spectra retained for evidence; no arbitrary full-spectrum production interpolation claim

Do not allocate seeds or ordinal while the representation/RH mapping remains open.

## 9. Hard prohibitions

Do not:

- rerun/reuse ordinal 40;
- allocate ordinal 41 yet;
- reuse ordinal-40 seeds/cases with patched inputs;
- GitHub-rerun v2/v3/v4/trace/v5/#592 consumed one-shots;
- infer materiality/effect size from capability runs;
- use #592 equal 0.25 synthetic mass weights as science;
- silently replace `continental_average` by INSO-only;
- reintroduce competing `aerosol_file tau` beside explicit species profiles;
- use failed `.nc` aliases;
- choose composition/RH/profile/provider/AOD/geometry from Taylor or Jerusalem residual direction/magnitude;
- proceed to Level-B profile mapping before fresh replacement scientific evidence;
- move `main` merely for convenience;
- create production authorization from capability evidence.

## 10. Broader retained project state

- AOPS ordinal 37, AFPF ordinal 38 and ASIV ordinal 39 are closed for their stated scopes and should not be duplicated.
- Taylor #508 remains evidence that independently constrained aerosol vertical structure can materially alter direct-MYSTIC twilight radiance.
- Taylor atmosphere provenance/uncertainty boundaries #535/#529/#536 remain authoritative.
- Better independent Taylor-night atmospheric acquisition is a separate lane and must not be used to fit residuals.
- Anti-fitting rules remain binding.

## 11. Resume checklist

- [ ] confirm frozen `main == 99ade7798627e67921139697ba1a004fa8a304bb`;
- [ ] confirm PRs #590/#591/#592 remain Draft/open/unmerged on their exact reviewed heads;
- [ ] preserve #592 artifact `9693056690`, digest `sha256:f1a2cd69420c63d5214f5082ee0844ec822b9aa2f9f8f13a4b52958ee59ae507`;
- [ ] search for parallel mixture/RH/renderer work before creating the next review branch;
- [ ] freeze exact OPAC 550-nm/RH optical-property source semantics and AFGL-US humidity selection;
- [ ] review and validate the explicit four-species renderer against target tau550 profiles without any scientific ordinal;
- [ ] only then finalize replacement AVPS preregistration;
- [ ] re-audit Issue #60 and branch namespaces immediately before future ordinal allocation;
- [ ] allocate fresh 72-group CRN seeds only after tracked-tree scientific freeze and global collision audit;
- [ ] keep Taylor/Jerusalem residuals closed throughout design, execution and result opening;
- [ ] update this handoff after each source audit, renderer validation, preregistration review, ordinal allocation, authorization, dispatch, Gate-0 and result opening.

## 12. One-line live status

**The solver-transport problem is now solved: #592 proves all four locked `continental_average` species (INSO/WASO/SOOT/SUSO) reach DISORT and MYSTIC through byte-identical no-extension OPAC aliases. Ordinal 41 is still deliberately unallocated. The next blocker is scientific representation, not transport: freeze the exact OPAC/RH 550-nm mass-to-extinction mapping and validate a four-species renderer that preserves local `continental_average` composition while realizing the five preregistered tau550 vertical templates.**
