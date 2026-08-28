# STAR VISIBILITY / MYSTIC — LIVE CURRENT HANDOFF

**Live refresh: 2026-08-28 — corrected four-species AVPS renderer (#596) has PASSED. Replacement scientific preregistration AVPS v2 (#597) has passed its dedicated review on fresh head `2bba54c6e78ed99d169887eef51d0c88d812b6f1`; repository contract `33193778174` is still active. No scientific seed is tracked/applied and ordinal 41 remains unallocated.**

The filename is historical. This content is the current computational/scientific checkpoint.

## 1. Immutable baseline

Repository: `search-maker/twilight-mystic-experiments`

Frozen `main`:

`99ade7798627e67921139697ba1a004fa8a304bb`

Frozen main tree:

`2d4bb1df136bff2da93f191e5518b94b3d7fecfc`

Do not move `main` merely to continue this lane.

## 2. Scientific ordinal state

AVPS ordinal 40 is consumed and must never be reused/rerun.

Ordinal-40 recovery reached exact 360/360 cases, but state-specific vertical-profile files differed while solver outputs were byte-identical. Therefore the intended vertical state did not reach effective solver physics.

Authoritative classification:

`EXECUTION/EVIDENCE PIPELINE VALID; SCIENTIFIC VERTICAL-PROFILE CONTRAST NON-INFORMATIVE.`

Never cite ordinal-40 zero contrast as physical vertical-profile insensitivity.

Retained ordinal-40 evidence:

- recovery science run `33139545997` SUCCESS, 360/360 cases
- Gate-0 artifact `9676069031`, digest `sha256:70dedcd16209dea74a9ed67a1dc7377c123f1a62fd18741b1e15692702011fc8`
- Phase A `33170006532` SUCCESS
- Phase B opening `33170855407` SUCCESS

Fresh audits before replacement work found no ordinal-41 allocation. **Ordinal 41 remains deliberately unallocated.** Re-audit Issue #60 and branch namespace immediately before any later allocation.

## 3. Resolver diagnosis chain — consumed identities, never rerun

- PR #586 / v2 run `33177704575` FAILURE: unresolved OPAC property before MYSTIC.
- PR #587 / v3 run `33180158034` FAILURE after testing `aerosol/OPAC/optprop/INSO.nc`.
- PR #588 / v4 run `33184511183` FAILURE after testing `aerosol/OPAC/INSO.nc`; artifact `9691137631`, digest `sha256:b538b58a44873eca3eebd64493edf3d9b88991e73ccb48f0d5e71ff1c9f2aee4`.
- PR #589 syscall trace run `33185460954` SUCCESS; artifact `9691518729`, digest `sha256:07fb60de7bef96253eaf29cb9303a83bab7f3f1952431c73a26499357b4d572a`.

The trace directly observed the locked binary requesting:

```text
.../data/aerosol/OPAC/optprop/INSO
```

with **no extension**.

## 4. PR #590 — single-species corrected transport PASS

PR #590 remains Draft/open/unmerged on head:

`f0675ec48c637509cd7a5bb9c2a2746507e5bea8`

- dedicated review `33186027699` SUCCESS
- repo contract `33186027637` SUCCESS
- one-shot `33186446347` attempt 1 SUCCESS
- artifact `9691923455`
- digest `sha256:fed6bb961088232e593159c4f50911758802e9209aed86e2a0eef4b403e4d9b7`
- report content SHA `da6d7f66625b63cb5ff4f69845c2953f2a509b3693c82d1f0203900dc7bd21d2`
- status `PASS_TRACE_OBSERVED_ALIAS_REACHES_DISORT_AND_MYSTIC`

Correct INSO representation:

- source `aerosol/OPAC/optprop/inso.mie.cdf`
- byte-identical alias `aerosol/OPAC/optprop/INSO`
- SHA `fe10348cbe585315d6e1db382563fdc054204ad35846f371dc9d8abeead36407`

This is transport evidence only; do not infer scientific effect size or realistic composition. Do not rerun v5.

## 5. PR #591 — locked `continental_average` source audit PASS

PR #591 remains Draft/open/unmerged on head:

`2bfae9341075eb04fe4621f4f53d4ab56262c22b`

- audit `33187119926` SUCCESS
- repo contract `33187119866` SUCCESS
- artifact `9692162280`
- digest `sha256:cdcb0041a5197e31ff24520b3e653119d11c5d4a1c1b4f727e392ba7e719101e`
- source `data/aerosol/OPAC/standard_aerosol_files/continental_average.dat`
- SHA `fc39fda0f8ada2d0a0a872b8b62d684cfccd74f7b0655b5af2dcdec51115e469`
- 14 numeric rows; exact columns `z(km) inso waso soot suso`

Official optical-property source hashes:

- INSO `fe10348cbe585315d6e1db382563fdc054204ad35846f371dc9d8abeead36407`
- WASO `b6df493b77019bf5e22456e8fb8858c5a7d502bcc02fe6fc697ebd4844f2d4f5`
- SOOT `44a0d2060101ca52c90ae64f005118dfba256b1f89a3049e1f758c55d634aa02`
- SUSO `ce0e1bba4219c60af0af14d66a280b0d3d25188276eed0951d31594b947cd472`

Thus a scientific replacement that claims fixed `continental_average` may not silently substitute INSO-only.

## 6. PR #592 — four-species transport capability PASS

PR #592 remains Draft/open/unmerged:

- review head `18667797a1dd699b6431a6940bac42974c415733`
- dedicated `33188868496` SUCCESS
- review artifact `9692863411`, digest `sha256:7417f68ad2cbc1e77bcf109bc34dd996d27bdf866d73e64c9666e43bc2c13c6e`
- repo contract `33188868323` SUCCESS
- one-shot `33189268483` attempt 1 SUCCESS
- artifact `9693056690`
- digest `sha256:f1a2cd69420c63d5214f5082ee0844ec822b9aa2f9f8f13a4b52958ee59ae507`
- report content SHA `6f191c0011c67bc3aeb27add17c25f9c81fd356bb47f42141e7783f6ac52e973`
- status `PASS_FOUR_CONTINENTAL_SPECIES_REACH_DISORT_AND_MYSTIC`

Four no-extension aliases are proven together. Pre-alias tree `5d8bbf8e6b91ec3d405dee36f21a94afbb6e5ec6cd67da2dd5dd541738199d80`; post-four-alias tree `5e1814dd36cf861fd85477a97607299248f8272268df7bf428d31bbb6aa4354a`.

The equal-0.25 species weights used by this capability were synthetic transport witnesses only and **must never become the scientific composition rule**. Do not rerun #592.

## 7. PR #593 — exact OPAC 550-nm/RH source evidence PASS

PR #593 final head:

`223b592208d3dda24217dabcfca9fd27333e4b84`

- exact-550 audit `33190220896` SUCCESS
- artifact `9693440701`, digest `sha256:7d8fa290b74f4e15538cd6ff2609f5491caad63258d0aefb8be689f1ce5f8e33`
- report content SHA `7ade25bf8be7c906a5a520fb1c2a13f974ac8ea0fd01e02e35560f2fb1b79a98`
- repo contract `33190220864` SUCCESS

Humidity nodes:

- INSO/SOOT: `[0]`
- WASO/SUSO: `[0,50,70,80,90,95,98,99] %`

Exact 550-nm extinction anchors:

- INSO RH0 `237.13107624931422`
- SOOT RH0 `9269.498363511553`
- WASO RH0/50 `2911.796533737995` / `3184.312159473288`
- SUSO RH0/50 `3120.3899717768004` / `3005.9625237729356`

AFGL-US source SHA `dab26290ed81c762ed0c607e5dc2d53393c1462a0c3a528bc5e3f5935191cfb5`.

#593 invoked no solver.

## 8. PR #594 — AFGL-US OPAC RH NULL audit PASS

- head `e7f968ee70dbecaf5f315bc8b03627ce1628edef`
- run `33190680002` attempt 1 SUCCESS
- artifact `9693619172`
- digest `sha256:74813789c2bf2842788de16aba6f3269c9f4efec675f6ee758903e4f6c52f9da`
- report content SHA `fd4e691f14f9cab427f7992acfc0435f50442e65e519520e6edae55c250a7f14`
- repo contract `33190679858` SUCCESS
- status `PASS_RUNTIME_AFGL_RH_AND_NEAREST_OPAC_NODE_PROFILE_FROZEN`

NULL solver only; no scientific RTE. Runtime nearest OPAC RH behavior is now directly evidenced. INSO/SOOT are non-swelling here; WASO/SUSO use humidity-dependent records.

## 9. PR #595 — NULL aerosol-tau calibration PASS

Final head:

`3fcb6328a18747b5a17d5ae75248c04c288e18f9`

- calibration `33191517143` SUCCESS
- artifact `9693948772`
- digest `sha256:97d431fe31724731a24697233c2154b836159a29299f8f42ea1853ebdf9d266a`
- report content SHA `b3787ecc5baaf0d95ffc1851aad45dbc03a00cded9f5cabb2f3ccb397fa5e709`
- repo contract `33191517521` SUCCESS
- status `PASS_VERBOSE_AEROSOL_SCATTER_PLUS_ABS_IS_LAYER_TAU_AND_AOD_RESCALE_PRESERVES_SHAPE`

Frozen print-precision tolerances:

- target AOD sum abs `2.1e-6`
- row-sum vs sum line `7e-5`
- normalized-shape max abs `6e-5`
- normalized-shape L1 `1.5e-3`

`scatter + abs` in the locked 550-nm verbose NULL table is calibrated as layer aerosol optical depth, and `aerosol_set_tau_at_wvl` preserves normalized vertical shape within these limits.

## 10. Frozen scientific question and five vertical templates

Scientific question, unchanged from the original preregistration:

> At fixed total AOD550 and fixed OPAC `continental_average` wavelength-dependent aerosol optical properties/phase function, how much does independently specified normalized aerosol vertical optical-depth shape change twilight radiance and derived Level-B?

The fixed optical family stays `continental_average` in every state. Maritime/desert/arctic/antarctic labels supply vertical-template parameters only; they do not switch aerosol microphysics.

Frozen states:

1. `opac-profile-continental-average`: total source tau 0.151; H=2 km; Z=8 km; first layer 0.133; free troposphere 0.013; stratosphere 0.005.
2. `opac-profile-maritime-clean`: total 0.096; H=2; Z=1; first 0.078; free 0.013; stratosphere 0.005.
3. `opac-profile-desert`: total 0.286; H=6; Z=2; first 0.268; free 0.013; stratosphere 0.005.
4. `opac-profile-arctic`: total 0.063; H=2; Z=99; first 0.045; free 0.013; stratosphere 0.005.
5. `opac-profile-antarctic`: total 0.072; H=10; Z=8; first 0.054; free 0.013; stratosphere 0.005.

Original target generator remains frozen:

- `experiments/aerosol-vertical-profile-sensitivity-v1/opac_vertical_templates.py`
- Git blob `8e8175ae771438b91fc9543b329175c193a215a4`

Original protocol remains frozen:

- `experiments/aerosol-vertical-profile-sensitivity-v1/protocol.review.json`
- Git blob `5dddbac21e9ac395bd482d0d376577a6e5dd8bb0`

The old effective implementation is permanently forbidden:

```text
aerosol_species_file continental_average
aerosol_file tau <state>
```

## 11. PR #596 — corrected four-species renderer validation PASS

PR #596 remains Draft/open/unmerged on final head:

`8adfd4fafa4c039394d12e6f6aff1795b750f4d2`

Failure history is retained and must not be rerun:

- initial head `510581558a7cebefd1cba642892160f5d3da69b0`, run `33192621988` failed before reconstruction because `mkdir evidence` was non-idempotent; artifact `9694407319`, digest `sha256:78673b59a68b78893898638da243740b2ea904c2bfea72b565dae101f0202cf2`.
- second head `ff8c1eeea0b0307fb799be1d20f6ba836f232331`, run `33192854324` reached and passed all runtime renderer validation but failed only in a static scope check that matched the forbidden-token wording inside its own prose/check; artifact `9694507494`, digest `sha256:9b0e2d636a29bfa171e1feace58ab2bef4e9803b95efb196b5acc381ac25872c`.

Final head changed only that static check. Renderer/protocol/tolerances were unchanged.

Final evidence:

- renderer source blob `99f61e1daa03cecef055a3773544574738d65082`
- dedicated review `33193123594` attempt 1 SUCCESS
- repository contract `33193123597` attempt 1 SUCCESS
- artifact `9694613680`
- digest `sha256:5e6942d879326ffc2dc8805d7649086cae32ad2e16aeec19a62cd3b0a89e3e27`
- report content SHA `20f26c65ce1d01e4514ceea36f2c95ecbf421d05a805b0a3d23e58f1fc9dda24`
- status `PASS_FIVE_FROZEN_AVPS_TEMPLATES_RENDERED_AS_COMMON_SCALAR_FOUR_SPECIES_NULL_TAU_SHAPES`

Validated representation:

```text
aerosol_default
aerosol_species_library OPAC
aerosol_species_file profiles/<state>.four-species.dat INSO WASO SOOT SUSO
aerosol_set_tau_at_wvl 550 <AOD550>
```

`aerosol_file tau` is forbidden.

The renderer first expands locked `continental_average.dat` onto the AFGL grid with lower-bound layer semantics. Explicit expanded four-species baseline versus built-in `continental_average` had exactly:

- max normalized layer-fraction difference `0.0`
- L1 difference `0.0`

It then multiplies all four local species by one common finite nonnegative scalar per layer to reach the independently frozen target layer-tau shape. All five states passed at AOD550 0.10 and 0.30 within the already-frozen #595 tolerances. Worst target error was about `3.92e-5` max layer fraction and `2.79e-4` L1, well inside `6e-5` / `1.5e-3`.

Therefore the previously frozen 29x29 response-matrix fallback is **not needed**.

Exact rendered profile SHA-256 values:

- continental average `ceed598f7681951cd0e6208b267beb5b41a52ab10311f37ce76f925700caff3d`
- maritime clean `487b67bd7dbe89d12d032fdf2b33cab545e16a2e0697170648317f1a76362a67`
- desert `2b4d2e03c6ae3143d9bb05d2da49f57f75172dc1f24d34f7d4a4939bf9952fef`
- arctic `98f2fa5428c830764252fd0a2662b0f5c957fc027ffcb7bdc0a5e500dfd7d3d6`
- antarctic `ee063c6dca68cf9a31d8bb9d993f1fed5cb34c8bb056ac180c97171b5d6b4f19`

#596 is renderer/NULL evidence only. It does not quantify twilight effect size and allocates no ordinal.

## 12. PR #597 — replacement scientific preregistration AVPS v2

A new scientific identity is required because ordinal 40 cannot be repaired in place.

Stage ID:

`aerosol-vertical-profile-sensitivity-v2`

PR #597 is Draft/open/unmerged on branch:

`review/aerosol-vertical-profile-sensitivity-v2-prereg`

Initial reviewed head:

`7ccf942a47d74a4db9afc8e490d600d08c6caed4`

- dedicated run `33193624797` failed **only** in the final static no-solver check because the check searched the workflow for forbidden strings that appeared inside that same assertion.
- all earlier gates on that failed head passed: exact #596 identity/artifact binding, five exact profile-byte hashes, 360-case skeleton construction, fresh case-ID namespace, disjointness from v1/ordinal-40 case IDs, seed count zero.
- no solver, seed allocation or ordinal allocation occurred.
- do not rerun `33193624797`.

Fresh corrected head:

`2bba54c6e78ed99d169887eef51d0c88d812b6f1`

The only change from the failed head is the static review check: it now validates the actual allowed GitHub Actions set and the generated skeleton boundary instead of searching its own text for a solver token. `PROTOCOL.md`, `protocol.review.json` and `build_skeleton.py` remain unchanged.

Fresh dedicated review:

- run `33193778176` attempt 1 — **SUCCESS**
- artifact `9694863701`
- digest `sha256:7de79aa4d8d9b51ad8ca4b1bdaceedae7ee5df17b3dd79c43c21cdaf9ae9a171`
- review receipt content SHA `717411c68c48f34f79c93da3ae8024e3d99a32c78ebe63935d262b3548e62c61`
- skeleton canonical SHA `a8d2d8f59aec01d82d8d98672152d00c11261660b0a69a59e2716c2edabd2b02`
- skeleton file SHA `a1a41d4b5ee07e08dc63d1b1c0eeda963706ca7b1adca8a6d89ffbd036d47bf4`
- 360 cases / 72 CRN groups / 5 states per group
- 120 distinct pre-seed science surfaces
- all case IDs begin `avps-v2-` and are disjoint from v1
- seed count `0`
- scientific ordinal `null`
- solver executed `false`
- scientific execution authorized `false`

Fresh repository contract:

- run `33193778174` on the same head — **currently active**

The scientific question/screen is intentionally unchanged from v1. Only scientific identity and transport representation are replaced.

Fresh future seed namespace is frozen but **not evaluated/applied yet**:

`aerosol-vertical-profile-sensitivity-v2|group-seed|sha256-v1`

No candidate seed literal is tracked by #597.

## 13. Frozen scientific screen for AVPS v2

Unless independently changed before any seed/result allocation, preserve:

- AFGL-US; observer 0 m; albedo 0.15
- wavelengths 380–780 nm; frozen 1-nm calculation grid
- MYSTIC spherical 1D, VROOM, `mc_std`
- 20,000,000 photons/case
- Sun depression 2/4/6/8 deg
- AOD550 0.10/0.30
- geometries alt/azrel 10/30, 30/90, 45/180
- 3 replicates
- 24 analysis cells; 72 CRN groups; 5 states/group; 360 cases
- same **fresh** seed across five states within each CRN group
- primary photopic, scotopic and Johnson-V channels
- paired log alternative/reference contrasts
- retain all three paired replicates; mean/sample SD/SE; no p-values/CIs/epsilon substitution
- no adaptive case addition or post-result rule changes
- full raw spectra retained as evidence; no arbitrary production full-spectrum interpolation claim

## 14. Next permitted gate

Do **not** allocate ordinal 41 merely because #597 dedicated review is green.

Required order:

1. require #597 repository contract `33193778174` to finish SUCCESS on exact head `2bba54c6...`;
2. then create a separate review-only v2 candidate-seed gate;
3. deterministically derive exactly 72 fresh candidate group seeds from the new v2 namespace/group IDs;
4. keep those seeds artifact-only/unapplied during review;
5. scan the exact tracked tree for candidate literals/collisions;
6. run the repository-global two-pass collision audit including branches, workflow metadata, artifacts, PR/issue bodies/comments and Issue #60;
7. require zero collisions and preserve authorization-time recheck requirement;
8. only after seed freshness review, re-audit Issue #60 and branch namespace for latest allocated/consumed ordinal;
9. only then consider a separate authorization review. If 40 is still latest, 41 is the expected next ordinal — but it is not allocated by #597 or the seed review.

The v1 seed derivation safety properties may be reused (signed-32-bit compatible domain, within-ledger uniqueness, repository-global collision scan), but **v1 namespace and seed values may not be reused**.

## 15. Hard prohibitions

Do not:

- rerun/reuse ordinal 40;
- allocate ordinal 41 yet;
- reuse ordinal-40 case IDs, group IDs or seeds;
- GitHub-rerun consumed v2/v3/v4/trace/v5/#592 identities;
- GitHub-rerun #596 failed runs `33192621988` or `33192854324`;
- GitHub-rerun #597 failed run `33193624797`;
- infer scientific materiality/effect size from capability/NULL audits;
- use #592 equal-0.25 mass weights scientifically;
- replace `continental_average` with INSO-only;
- reintroduce `aerosol_file tau` beside explicit species profiles;
- use failed `.nc` aliases;
- alter five template states/AOD/geometry/provider/cycle from Taylor/Jerusalem residual direction or magnitude;
- use ordinal-40 zero contrast to change v2 design;
- proceed to Level-B profile mapping before fresh replacement scientific evidence;
- move `main` for convenience;
- create production authorization from capability/NULL/preregistration evidence alone.

## 16. Broader retained project state

- AOPS ordinal 37, AFPF ordinal 38 and ASIV ordinal 39 remain closed for their stated scopes and should not be duplicated.
- Taylor #508 remains evidence that independently constrained aerosol vertical structure can materially alter direct-MYSTIC twilight radiance.
- Taylor atmosphere provenance/uncertainty boundaries #535/#529/#536 remain authoritative.
- Better independent Taylor-night atmospheric acquisition is a separate lane and must not be used to fit residuals.
- Anti-fitting rules remain binding.

## 17. Resume checklist

- [ ] confirm frozen `main == 99ade7798627e67921139697ba1a004fa8a304bb`;
- [ ] preserve #596 final artifact `9694613680`, digest `sha256:5e6942d879326ffc2dc8805d7649086cae32ad2e16aeec19a62cd3b0a89e3e27`;
- [ ] preserve #596 failed attempts `33192621988` and `33192854324`; never rerun them;
- [ ] preserve #597 failed run `33193624797`; never rerun it;
- [ ] require #597 contract `33193778174` to PASS on exact head `2bba54c6...`;
- [ ] preserve #597 review artifact `9694863701`, receipt SHA `717411c6...`, skeleton SHA `a8d2d8f5...`;
- [ ] only after #597 fully passes, open a separate seed-freshness review with new v2 namespace and no ordinal;
- [ ] keep candidate seeds artifact-only/unapplied during freshness review;
- [ ] perform tracked-tree + repository-global collision audit;
- [ ] re-audit Issue #60/branches immediately before ordinal allocation;
- [ ] allocate ordinal only in a separate authorization review;
- [ ] keep Taylor/Jerusalem residuals closed through design, execution and primary result opening;
- [ ] update this handoff after #597 contract, seed review, ordinal audit/allocation, authorization, dispatch, Gate-0 and result opening.

## 18. One-line live status

**The vertical-profile transport defect is now corrected and runtime-validated: #596 proves all five independently frozen AVPS templates can be represented with explicit INSO/WASO/SOOT/SUSO profiles while preserving the locked continental_average family and target layer-tau shapes. #597 has frozen a fresh 360-case AVPS v2 scientific identity with exact profile hashes, new case namespace and zero seeds/zero ordinal; its dedicated review is SUCCESS and its repository contract is still active. No replacement scientific MYSTIC run is authorized yet.**