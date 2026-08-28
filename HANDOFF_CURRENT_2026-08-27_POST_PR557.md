# STAR VISIBILITY / MYSTIC — LIVE CURRENT HANDOFF

**Live refresh: 2026-08-28 — PR #596 is the active four-species renderer gate. Initial head `510581558a7cebefd1cba642892160f5d3da69b0` failed closed before reconstruction because `mkdir evidence` was non-idempotent; no renderer/NULL validation ran. The only correction is `mkdir -p evidence` on fresh head `ff8c1eeea0b0307fb799be1d20f6ba836f232331`; fresh review `33192854324` and repo contract `33192854366` are active. Ordinal 41 remains unallocated.**

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

Ordinal-40 recovery reached exact 360/360 cases, but state-specific vertical-profile files differed while solver outputs were byte-identical. Therefore the intended vertical state never reached effective solver physics.

Authoritative classification:

`EXECUTION/EVIDENCE PIPELINE VALID; SCIENTIFIC VERTICAL-PROFILE CONTRAST NON-INFORMATIVE.`

Never cite ordinal-40 zero contrast as physical profile insensitivity.

Retained ordinal-40 evidence:

- recovered science run `33139545997` SUCCESS, 360/360 cases
- Gate-0 artifact `9676069031`, digest `sha256:70dedcd16209dea74a9ed67a1dc7377c123f1a62fd18741b1e15692702011fc8`
- Phase A `33170006532` SUCCESS
- Phase B opening `33170855407` SUCCESS

Fresh branch/Issue-60 audits before the replacement work found no ordinal-41 allocation. **Ordinal 41 remains deliberately unallocated.** Re-audit Issue #60 and all branch namespaces immediately before any later allocation.

## 3. Resolver diagnosis chain — consumed identities, never rerun

- v2 / PR #586 — run `33177704575` FAILURE: unresolved OPAC property before MYSTIC.
- v3 / PR #587 — tested `aerosol/OPAC/optprop/INSO.nc`; run `33180158034` FAILURE.
- v4 / PR #588 — tested `aerosol/OPAC/INSO.nc`; run `33184511183` FAILURE; artifact `9691137631`, digest `sha256:b538b58a44873eca3eebd64493edf3d9b88991e73ccb48f0d5e71ff1c9f2aee4`.
- syscall trace / PR #589 — run `33185460954` SUCCESS; artifact `9691518729`, digest `sha256:07fb60de7bef96253eaf29cb9303a83bab7f3f1952431c73a26499357b4d572a`.

The trace directly observed the locked binary requesting:

```text
.../data/aerosol/OPAC/optprop/INSO
```

with **no extension**. That is the actual resolver representation.

## 4. PR #590 — single-species corrected transport PASS

PR #590 remains Draft/open/unmerged on head:

`f0675ec48c637509cd7a5bb9c2a2746507e5bea8`

- dedicated review `33186027699` SUCCESS
- repo contract `33186027637` SUCCESS
- one-shot run `33186446347` attempt 1 SUCCESS
- artifact `9691923455`
- digest `sha256:fed6bb961088232e593159c4f50911758802e9209aed86e2a0eef4b403e4d9b7`
- report content SHA `da6d7f66625b63cb5ff4f69845c2953f2a509b3693c82d1f0203900dc7bd21d2`
- status `PASS_TRACE_OBSERVED_ALIAS_REACHES_DISORT_AND_MYSTIC`

Correct representation:

- source `aerosol/OPAC/optprop/inso.mie.cdf`
- byte-identical alias `aerosol/OPAC/optprop/INSO`
- SHA `fe10348cbe585315d6e1db382563fdc054204ad35846f371dc9d8abeead36407`

This proves explicit INSO mass-profile transport only. Do not infer scientific effect size or realistic continental composition. Do not rerun v5.

## 5. PR #591 — locked `continental_average` source audit PASS

PR #591 remains Draft/open/unmerged on head:

`2bfae9341075eb04fe4621f4f53d4ab56262c22b`

- audit run `33187119926` SUCCESS
- repo contract `33187119866` SUCCESS
- artifact `9692162280`
- digest `sha256:cdcb0041a5197e31ff24520b3e653119d11c5d4a1c1b4f727e392ba7e719101e`
- exact source `data/aerosol/OPAC/standard_aerosol_files/continental_average.dat`
- SHA `fc39fda0f8ada2d0a0a872b8b62d684cfccd74f7b0655b5af2dcdec51115e469`
- 1075 bytes; 14 numeric rows; 5 columns

Exact species columns:

```text
z(km)  inso  waso  soot  suso
```

Thus the replacement AVPS cannot silently substitute INSO-only if it intends to preserve the frozen `continental_average` family.

Official optical-property asset hashes:

- INSO `fe10348cbe585315d6e1db382563fdc054204ad35846f371dc9d8abeead36407`
- WASO `b6df493b77019bf5e22456e8fb8858c5a7d502bcc02fe6fc697ebd4844f2d4f5`
- SOOT `44a0d2060101ca52c90ae64f005118dfba256b1f89a3049e1f758c55d634aa02`
- SUSO `ce0e1bba4219c60af0af14d66a280b0d3d25188276eed0951d31594b947cd472`

## 6. PR #592 — four-species transport capability PASS

PR #592 remains Draft/open/unmerged:

- review head `18667797a1dd699b6431a6940bac42974c415733`
- dedicated review `33188868496` SUCCESS
- review artifact `9692863411`, digest `sha256:7417f68ad2cbc1e77bcf109bc34dd996d27bdf866d73e64c9666e43bc2c13c6e`
- repo contract `33188868323` SUCCESS
- control `d504ec4c6c1e0943e53de6d0038f88104a49c131`
- request head `3e76e70ae81771e10477689df32085da1193659c`
- one push run `33189268483` attempt 1 SUCCESS
- artifact `9693056690`
- digest `sha256:f1a2cd69420c63d5214f5082ee0844ec822b9aa2f9f8f13a4b52958ee59ae507`
- report content SHA `6f191c0011c67bc3aeb27add17c25f9c81fd356bb47f42141e7783f6ac52e973`
- status `PASS_FOUR_CONTINENTAL_SPECIES_REACH_DISORT_AND_MYSTIC`

Four byte-identical no-extension aliases are proven:

- `INSO` 1,595,764 bytes
- `WASO` 7,236,612 bytes
- `SOOT` 163,972 bytes
- `SUSO` 13,693,828 bytes

Pre-alias tree `5d8bbf8e6b91ec3d405dee36f21a94afbb6e5ec6cd67da2dd5dd541738199d80`; post-four-alias tree `5e1814dd36cf861fd85477a97607299248f8272268df7bf428d31bbb6aa4354a`.

DISORT and MYSTIC LOW/HIGH were finite, same-grid and non-identical. The equal 0.25 species weights used in this capability were synthetic transport witnesses only and **must never become the scientific composition rule**.

Do not rerun #592.

## 7. PR #593 — exact OPAC 550-nm/RH source evidence PASS

PR #593 remains Draft/open/unmerged on final head:

`223b592208d3dda24217dabcfca9fd27333e4b84`

Historical initial structure audit on old head `7bb03785...`:

- run `33189832700` SUCCESS
- artifact `9693279123`, digest `sha256:c1de8e1a7cc1ab55a4b8044e5d433a00ac2f579a02c5667714903ae31405e803`
- never rerun it

Final-head evidence:

- generic source audit `33190220721` SUCCESS
- artifact `9693427186`, digest `sha256:ee80b71e8bdb0cd9aaacc29890162fb903f89f6ef6c5ace615094fe94ac60a36`
- exact-550 audit `33190220896` SUCCESS
- artifact `9693440701`, digest `sha256:7d8fa290b74f4e15538cd6ff2609f5491caad63258d0aefb8be689f1ce5f8e33`
- exact-values report content SHA `7ade25bf8be7c906a5a520fb1c2a13f974ac8ea0fd01e02e35560f2fb1b79a98`
- repo contract `33190220864` SUCCESS

All four NetCDFs have:

- wavelength variable `wavelen`, 61 values, units `micrometer`
- exact 0.55 micrometer coordinate at index 6
- extinction variable `ext`, dimensions `[nlam, nhum]`
- extinction units exactly `km^-1 / (g/m^3)`
- `ssa` and `rho` on the same dimensions; `rho` units `g/cm^3`

Humidity nodes:

- INSO/SOOT: `[0]`
- WASO/SUSO: `[0,50,70,80,90,95,98,99] %`

Exact 550-nm extinction coefficients needed by any analytic cross-check:

- INSO RH0: `237.13107624931422`
- SOOT RH0: `9269.498363511553`
- WASO RH0/50: `2911.796533737995` / `3184.312159473288`
- SUSO RH0/50: `3120.3899717768004` / `3005.9625237729356`

Full exact RH-node values remain in artifact `9693440701`.

AFGL-US source SHA remains `dab26290ed81c762ed0c607e5dc2d53393c1462a0c3a528bc5e3f5935191cfb5`.

#593 did not invoke `uvspec` or any solver.

## 8. PR #594 — AFGL-US OPAC RH NULL-solver audit PASS

PR #594 remains Draft/open/unmerged:

- head `e7f968ee70dbecaf5f315bc8b03627ce1628edef`
- NULL audit run `33190680002` attempt 1 SUCCESS
- artifact `9693619172`
- digest `sha256:74813789c2bf2842788de16aba6f3269c9f4efec675f6ee758903e4f6c52f9da`
- report content SHA `fd4e691f14f9cab427f7992acfc0435f50442e65e519520e6edae55c250a7f14`
- repo contract `33190679858` SUCCESS
- status `PASS_RUNTIME_AFGL_RH_AND_NEAREST_OPAC_NODE_PROFILE_FROZEN`

This used `rte_solver null`, not DISORT/MYSTIC. The NULL solver built optical properties/postprocessing only; no scientific RTE solution was produced.

Runtime AFGL RH around the aerosol domain:

- 15 km 2.055% -> nearest OPAC 0%
- 14 km 2.851% -> 0%
- 13 km 6.107% -> 0%
- 12 km 12.552% -> 0%
- 11 km 27.500% -> 50%
- 10 km 28.744% -> 50%
- 9 km 37.131% -> 50%
- 8 km 50.586% -> 50%
- 7 km 48.185% -> 50%
- 6 km 49.197% -> 50%
- 5 km 48.380% -> 50%
- 4 km 50.052% -> 50%
- 3 km 50.735% -> 50%
- 2 km 51.992% -> 50%
- 1 km 49.042% -> 50%
- 0 km 45.907% -> 50%

The preserved verbose output also directly printed libRadtran's internal `rh(atmos)` vs `rh(aerofile)` selection for soluble species, confirming the runtime nearest-RH behavior rather than merely our external nearest-node calculation.

INSO/SOOT are non-swelling in this representation. WASO/SUSO use the humidity-dependent OPAC records.

## 9. PR #595 — NULL verbose aerosol-tau calibration PASS

PR #595 remains Draft/open/unmerged on final head:

`3fcb6328a18747b5a17d5ae75248c04c288e18f9`

Initial head `b3df9abe4219a40a4f86d9385754afa677e5f07b` produced review run `33191270535` which failed **before runtime calibration** because the synthetic parser fixture used an invalid altitude sequence ending at 67 km. No archive reconstruction or calibration cases ran on that failed head. The correction changed only the synthetic unit fixture from 115->67 to 48->0; parser, tolerances, protocol and NULL cases remained frozen.

Final-head runs:

- calibration `33191517143` attempt 1 SUCCESS
- artifact `9693948772`
- digest `sha256:97d431fe31724731a24697233c2154b836159a29299f8f42ea1853ebdf9d266a`
- calibration report content SHA `b3787ecc5baaf0d95ffc1851aad45dbc03a00cded9f5cabb2f3ccb397fa5e709`
- repo contract `33191517521` attempt 1 SUCCESS
- status `PASS_VERBOSE_AEROSOL_SCATTER_PLUS_ABS_IS_LAYER_TAU_AND_AOD_RESCALE_PRESERVES_SHAPE`

Preregistered tolerances were unchanged before runtime:

- target sum abs `2.1e-6`
- row-sum vs printed sum line `7e-5`
- normalized-shape max abs `6e-5`
- normalized-shape L1 `1.5e-3`

Results:

### baseline `continental_average`

- printed aerosol scatter sum `0.108353`
- printed aerosol absorption sum `0.012354`
- printed `scatter+abs = 0.120707`
- sum of six-decimal layer rows `0.120703`

### forced AOD550 = 0.10

- printed scatter `0.089765`
- printed absorption `0.010235`
- printed `scatter+abs = 0.100000`
- layer-row sum `0.100003`

### forced AOD550 = 0.30

- printed scatter `0.269296`
- printed absorption `0.030704`
- printed `scatter+abs = 0.300000`
- layer-row sum `0.299995`
- exact printed 0.30/0.10 ratio `3.0`

Normalized layer-shape differences under rescale:

- baseline vs 0.10: max `2.6935887780132894e-05`, L1 `0.0001694896254676023`
- baseline vs 0.30: max `9.13422512677231e-06`, L1 `8.641326649441662e-05`
- 0.10 vs 0.30: max `2.532712898428713e-05`, L1 `0.00011262316508073799`

Therefore, for this locked 550-nm NULL verbose table, **aerosol `scatter + abs` is calibrated as layer aerosol optical depth**, and `aerosol_set_tau_at_wvl` rescales the column while preserving normalized vertical shape to within the preregistered print-precision tolerances.

This is calibration evidence only. It does not by itself validate any custom AVPS renderer.

## 10. Frozen scientific question and five vertical templates

The scientific question remains exactly the independently preregistered one:

> At fixed total AOD550 and fixed OPAC `continental_average` wavelength-dependent aerosol optical properties/phase function, how much does independently specified normalized aerosol vertical optical-depth shape change twilight radiance and derived Level-B?

The fixed optical family stays **continental_average in every state**. The labels maritime/desert/arctic/antarctic provide vertical-template parameters only; they do not switch aerosol microphysics.

Frozen states:

1. `opac-profile-continental-average`: total source tau 0.151; H=2 km; Z=8 km; first layer 0.133; free troposphere 0.013; stratosphere 0.005.
2. `opac-profile-maritime-clean`: total 0.096; H=2; Z=1; first 0.078; free 0.013; stratosphere 0.005.
3. `opac-profile-desert`: total 0.286; H=6; Z=2; first 0.268; free 0.013; stratosphere 0.005.
4. `opac-profile-arctic`: total 0.063; H=2; Z=99; first 0.045; free 0.013; stratosphere 0.005.
5. `opac-profile-antarctic`: total 0.072; H=10; Z=8; first 0.054; free 0.013; stratosphere 0.005.

Shared profile rules:

- first layer: state H/Z exponential
- free troposphere from H to12 km: tau 0.013, scale 8 km
- stratosphere 12–35 km: tau 0.005, scale 99 km
- above35 km: zero
- normalize to unit column shape before case AOD is imposed separately
- target grid: exact AFGL-US atmosphere levels

Original template generator remains frozen:

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

because ordinal 40 proved the custom tau state lost the intended solver-physics contrast.

## 11. Current gate — PR #596 explicit four-species renderer validation, still no ordinal

PR #596 is Draft/open/unmerged:

- branch `review/avps-four-species-renderer-validation-v1`
- initial head `510581558a7cebefd1cba642892160f5d3da69b0`
- initial review run `33192621988` attempt 1 — FAILURE before runtime reconstruction
- failed step: `Reconstruct exact locked runtime and frozen OPAC archive`
- exact cause: `mkdir: cannot create directory ‘evidence’: File exists`
- failure artifact `9694407319`, digest `sha256:78673b59a68b78893898638da243740b2ea904c2bfea72b565dae101f0202cf2`
- no lower-bound baseline validation, five-state renderer validation, DISORT or MYSTIC ran on that head
- do not rerun the failed head/run

Fresh correction:

- current head `ff8c1eeea0b0307fb799be1d20f6ba836f232331`
- only change from the failed head: `mkdir evidence` -> `mkdir -p evidence`
- renderer code, protocol, exact #595 dependency blob, original AVPS template blob and all tolerances are unchanged
- fresh renderer review `33192854324` is active
- fresh repo contract `33192854366` is active
- ordinal 41 remains unallocated

Frozen renderer representation under test:

- expand exact `continental_average.dat` onto the exact AFGL grid using lower-bound layer semantics, zero at/above35 km;
- first require the explicit expanded four-species profile at AOD550=0.10 to reproduce built-in `aerosol_species_file continental_average` normalized NULL layer-tau shape within the already-frozen #595 print-precision limits;
- only after that baseline gate, use for each active layer `common_scalar = frozen_target_layer_tau_fraction / expanded_standard_layer_tau_fraction`;
- multiply INSO/WASO/SOOT/SUSO in that layer by the same finite nonnegative scalar, preserving the local standard species ratios;
- emit one explicit four-species `aerosol_species_file` profile per frozen AVPS state;
- never use `aerosol_file tau`;
- keep `aerosol_set_tau_at_wvl 550 0.10/0.30` as separate column normalization;
- validate all five states at AOD550 0.10 and0.30 with actual NULL/verbose layer-tau output.

Frozen PASS tolerances are unchanged from #595:

- AOD sum abs <= `2.1e-6`
- row-sum vs printed sum line <= `7e-5`
- target normalized-shape max abs <= `6e-5`
- target normalized-shape L1 <= `1.5e-3`
- the same shape limits for 0.10 vs0.30 rescale comparison

If the lower-bound/common-scalar construction fails the actual runtime NULL table, do **not** relax tolerances or clip scientific states post hoc. Preserve the failure and fall back to the already-preregistered 29x29 NULL response-matrix construction below. If it passes, the matrix is unnecessary complexity and the simpler runtime-validated representation becomes the renderer evidence.

### Frozen fallback only if the simple runtime gate fails scientifically

A response-matrix renderer may then:

1. build 29 NULL/verbose local-standard-mixture basis profiles over the active below-35-km nodes;
2. parse layer tau with the already calibrated `scatter+abs` parser;
3. solve the deterministic square response system for each frozen target vector;
4. require finite nonnegative solutions and a preregistered condition-number/numerical-zero policy;
5. validate all five rendered states again at AOD550 0.10 and0.30 against the unchanged target/tolerances.

This fallback may be selected only because the simple representation fails its independent runtime validation, never from Taylor/Jerusalem residual behavior.

## 12. Original scientific screen to preserve unless independently changed before seeds/results

- AFGL-US, observer 0 m, albedo 0.15
- wavelengths 380–780 nm; 1-nm calculation grid
- MYSTIC spherical1D, VROOM, MC standard-deviation output
- 20M photons/case
- sun depression 2/4/6/8 deg
- AOD550 0.10/0.30
- geometries: alt/azrel 10/30, 30/90, 45/180
- 3 replicates
- 24 cells; 72 CRN groups; 5 states/group; 360 cases
- same **fresh** seed across five states within each CRN group
- primary photopic, scotopic and Johnson-V channels
- paired log alternative/reference contrasts
- retain all 3 paired replicates; mean/sample SD/SE; no p-values/CIs/epsilon substitution
- no adaptive case addition or post-result rule changes
- full raw spectra retained as evidence; no arbitrary production full-spectrum interpolation claim

No scientific seeds or ordinal may be allocated while the corrected representation is still under validation.

## 13. Hard prohibitions

Do not:

- rerun/reuse ordinal 40;
- allocate ordinal 41 yet;
- reuse ordinal-40 case/seed identities;
- GitHub-rerun v2/v3/v4/trace/v5/#592 consumed one-shot identities;
- GitHub-rerun #596 failed run `33192621988`;
- infer scientific materiality/effect size from capability/NULL audits;
- use #592 equal-0.25 mass weights scientifically;
- replace `continental_average` with INSO-only;
- reintroduce competing `aerosol_file tau` beside the explicit species profile;
- use failed `.nc` aliases;
- change the five template states from Taylor/Jerusalem residual direction or magnitude;
- choose mixture/RH/AOD/geometry/provider/cycle from those residuals;
- proceed to Level-B profile mapping before fresh replacement scientific evidence;
- move `main` for convenience;
- create production authorization from capability/NULL evidence.

## 14. Broader retained project state

- AOPS ordinal 37, AFPF ordinal 38 and ASIV ordinal 39 remain closed for their stated scopes and should not be duplicated.
- Taylor #508 remains evidence that independently constrained aerosol vertical structure can materially change direct-MYSTIC twilight radiance.
- Taylor atmosphere provenance/uncertainty boundaries #535/#529/#536 remain authoritative.
- Better independent Taylor-night atmospheric acquisition is a separate lane and must not be used to fit residuals.
- Anti-fitting rules remain binding.

## 15. Resume checklist

- [ ] confirm frozen `main == 99ade7798627e67921139697ba1a004fa8a304bb`;
- [ ] confirm PRs #590–#596 remain Draft/open/unmerged on their final/current evidence heads;
- [ ] preserve #595 artifact `9693948772`, digest `sha256:97d431fe31724731a24697233c2154b836159a29299f8f42ea1853ebdf9d266a`;
- [ ] preserve #596 failed attempt `33192621988` and artifact `9694407319`; never rerun it;
- [ ] inspect fresh #596 review `33192854324` and contract `33192854366` on exact head `ff8c1eee...`;
- [ ] if #596 PASS, freeze its artifact/report and rewrite/review the 360-case execution skeleton to use exact explicit four-species profiles and no `aerosol_file tau`;
- [ ] if #596 fails on runtime renderer physics, preserve that head/results and move to the frozen 29x29 NULL response-matrix fallback without relaxing target/tolerances;
- [ ] only after tracked-tree science freeze re-audit Issue #60 and branches;
- [ ] allocate 72 fresh CRN group seeds with repository-global collision audit;
- [ ] allocate the fresh scientific ordinal only in a separate authorization review;
- [ ] keep Taylor/Jerusalem residuals closed throughout design/execution/result opening;
- [ ] update this handoff after renderer review/result, execution-package review, seed freeze, ordinal allocation, authorization, dispatch, Gate-0 and result opening.

## 16. One-line live status

**Source, four-species transport, exact 550-nm/RH behavior and NULL layer-tau calibration are proven through #595. PR #596 is now testing the corrected explicit four-species renderer against the actual runtime NULL table. Its initial head failed only on non-idempotent `mkdir evidence` before any renderer validation; the fresh head changes only that control-plane line and is under review. Ordinal 41 remains unallocated and no replacement scientific MYSTIC run is authorized yet.**