# STAR VISIBILITY / MYSTIC — LIVE CURRENT HANDOFF

**Live refresh: 2026-08-28 — AVPS v2 corrected transport, renderer, scientific preregistration and candidate-seed freshness are all reviewed successfully through PR #598. No candidate seed has been applied to a case, no scientific ordinal has been allocated, and no replacement scientific MYSTIC run is authorized. The next permitted gate is a fresh v2 preauthorization / global-ordinal audit with an authorization-time repeat of seed freshness.**

The filename is historical. This file is the current computational/scientific checkpoint.

## 1. Immutable baseline

Repository: `search-maker/twilight-mystic-experiments`

Frozen `main` remains:

`99ade7798627e67921139697ba1a004fa8a304bb`

Frozen main tree:

`2d4bb1df136bff2da93f191e5518b94b3d7fecfc`

Do not move `main` merely to continue this lane.

## 2. Ordinal 40 is consumed and scientifically non-informative

AVPS v1 scientific ordinal 40 reached exact 360/360 case evidence, but state-specific vertical-profile files differed while solver outputs were byte-identical. The intended vertical state therefore did not reach effective solver physics.

Authoritative classification:

`EXECUTION/EVIDENCE PIPELINE VALID; SCIENTIFIC VERTICAL-PROFILE CONTRAST NON-INFORMATIVE.`

Never rerun/reuse ordinal 40 and never cite its zero contrast as evidence of physical vertical-profile insensitivity.

Retained ordinal-40 evidence:

- recovery science `33139545997` SUCCESS, 360/360 cases
- Gate-0 artifact `9676069031`, digest `sha256:70dedcd16209dea74a9ed67a1dc7377c123f1a62fd18741b1e15692702011fc8`
- Phase A `33170006532` SUCCESS
- Phase B opening `33170855407` SUCCESS
- exact consumed marker remains `ORDINAL40_AVPS_V1_DISPATCH_CONSUMED`

**Ordinal 41 is still unallocated.** Fresh branch searches have found no ordinal-41 ref. Re-audit Issue #60 and all authorization/dispatch branches immediately before any future allocation.

## 3. Resolver diagnosis and corrected transport

Historical consumed identities — never GitHub-rerun:

- PR #586 / v2 run `33177704575` FAILURE
- PR #587 / v3 run `33180158034` FAILURE after testing `aerosol/OPAC/optprop/INSO.nc`
- PR #588 / v4 run `33184511183` FAILURE after testing `aerosol/OPAC/INSO.nc`; artifact `9691137631`, digest `sha256:b538b58a44873eca3eebd64493edf3d9b88991e73ccb48f0d5e71ff1c9f2aee4`
- PR #589 syscall trace `33185460954` SUCCESS; artifact `9691518729`, digest `sha256:07fb60de7bef96253eaf29cb9303a83bab7f3f1952431c73a26499357b4d572a`

The trace directly observed the locked binary requesting:

```text
data/aerosol/OPAC/optprop/INSO
```

with **no extension**.

### PR #590 — single-species transport PASS

- head `f0675ec48c637509cd7a5bb9c2a2746507e5bea8`
- dedicated `33186027699` SUCCESS
- repo contract `33186027637` SUCCESS
- one-shot `33186446347` SUCCESS
- artifact `9691923455`, digest `sha256:fed6bb961088232e593159c4f50911758802e9209aed86e2a0eef4b403e4d9b7`
- report content SHA `da6d7f66625b63cb5ff4f69845c2953f2a509b3693c82d1f0203900dc7bd21d2`

INSO official source/alias SHA:

`fe10348cbe585315d6e1db382563fdc054204ad35846f371dc9d8abeead36407`

Capability only; no effect-size inference.

## 4. Locked `continental_average` composition and four-species capability

### PR #591 — source audit PASS

- head `2bfae9341075eb04fe4621f4f53d4ab56262c22b`
- audit `33187119926` SUCCESS
- repo contract `33187119866` SUCCESS
- artifact `9692162280`, digest `sha256:cdcb0041a5197e31ff24520b3e653119d11c5d4a1c1b4f727e392ba7e719101e`
- `continental_average.dat` SHA `fc39fda0f8ada2d0a0a872b8b62d684cfccd74f7b0655b5af2dcdec51115e469`
- exact columns `z(km) INSO WASO SOOT SUSO`

Official optical-property SHA-256 values:

- INSO `fe10348cbe585315d6e1db382563fdc054204ad35846f371dc9d8abeead36407`
- WASO `b6df493b77019bf5e22456e8fb8858c5a7d502bcc02fe6fc697ebd4844f2d4f5`
- SOOT `44a0d2060101ca52c90ae64f005118dfba256b1f89a3049e1f758c55d634aa02`
- SUSO `ce0e1bba4219c60af0af14d66a280b0d3d25188276eed0951d31594b947cd472`

### PR #592 — four-species transport PASS

- head `18667797a1dd699b6431a6940bac42974c415733`
- dedicated `33188868496` SUCCESS
- repo contract `33188868323` SUCCESS
- one-shot `33189268483` SUCCESS
- artifact `9693056690`, digest `sha256:f1a2cd69420c63d5214f5082ee0844ec822b9aa2f9f8f13a4b52958ee59ae507`
- report content SHA `6f191c0011c67bc3aeb27add17c25f9c81fd356bb47f42141e7783f6ac52e973`
- status `PASS_FOUR_CONTINENTAL_SPECIES_REACH_DISORT_AND_MYSTIC`
- four-alias staged data tree `5e1814dd36cf861fd85477a97607299248f8272268df7bf428d31bbb6aa4354a`

The equal 0.25 species weights used by #592 were synthetic capability witnesses only and are forbidden as a scientific composition rule.

## 5. Exact 550-nm humidity behavior and NULL layer-tau calibration

### PR #593 — OPAC source/RH evidence PASS

Final head `223b592208d3dda24217dabcfca9fd27333e4b84`.

- exact-550 audit `33190220896` SUCCESS
- artifact `9693440701`, digest `sha256:7d8fa290b74f4e15538cd6ff2609f5491caad63258d0aefb8be689f1ce5f8e33`
- report content SHA `7ade25bf8be7c906a5a520fb1c2a13f974ac8ea0fd01e02e35560f2fb1b79a98`
- repo contract `33190220864` SUCCESS

Humidity nodes:

- INSO/SOOT `[0]`
- WASO/SUSO `[0,50,70,80,90,95,98,99] %`

Exact 550-nm extinction anchors:

- INSO RH0 `237.13107624931422`
- SOOT RH0 `9269.498363511553`
- WASO RH0/50 `2911.796533737995` / `3184.312159473288`
- SUSO RH0/50 `3120.3899717768004` / `3005.9625237729356`

### PR #594 — AFGL-US RH NULL audit PASS

- head `e7f968ee70dbecaf5f315bc8b03627ce1628edef`
- run `33190680002` SUCCESS
- artifact `9693619172`, digest `sha256:74813789c2bf2842788de16aba6f3269c9f4efec675f6ee758903e4f6c52f9da`
- report content SHA `fd4e691f14f9cab427f7992acfc0435f50442e65e519520e6edae55c250a7f14`
- repo contract `33190679858` SUCCESS

NULL solver only; no scientific RTE. Runtime nearest-OPAC-RH behavior is directly frozen.

### PR #595 — NULL aerosol-tau calibration PASS

Final head `3fcb6328a18747b5a17d5ae75248c04c288e18f9`.

- calibration `33191517143` SUCCESS
- repo contract `33191517521` SUCCESS
- artifact `9693948772`, digest `sha256:97d431fe31724731a24697233c2154b836159a29299f8f42ea1853ebdf9d266a`
- report content SHA `b3787ecc5baaf0d95ffc1851aad45dbc03a00cded9f5cabb2f3ccb397fa5e709`
- status `PASS_VERBOSE_AEROSOL_SCATTER_PLUS_ABS_IS_LAYER_TAU_AND_AOD_RESCALE_PRESERVES_SHAPE`

Frozen print-precision tolerances:

- AOD sum abs `2.1e-6`
- row-sum vs sum line `7e-5`
- normalized shape max abs `6e-5`
- normalized shape L1 `1.5e-3`

## 6. Frozen scientific question and five independent vertical templates

The question remains unchanged from the pre-ordinal-40 preregistration:

> At fixed total AOD550 and fixed OPAC `continental_average` wavelength-dependent aerosol optical properties/phase function, how much does independently specified normalized aerosol vertical optical-depth shape change twilight radiance and derived Level-B limiting magnitude?

The labels maritime/desert/arctic/antarctic supply vertical-template parameters only; they do **not** switch aerosol microphysics.

Frozen states:

1. `opac-profile-continental-average`: source tau 0.151; H=2 km; Z=8 km; first layer 0.133; free troposphere 0.013; stratosphere 0.005.
2. `opac-profile-maritime-clean`: source tau 0.096; H=2; Z=1; first 0.078; free 0.013; stratosphere 0.005.
3. `opac-profile-desert`: source tau 0.286; H=6; Z=2; first 0.268; free 0.013; stratosphere 0.005.
4. `opac-profile-arctic`: source tau 0.063; H=2; Z=99; first 0.045; free 0.013; stratosphere 0.005.
5. `opac-profile-antarctic`: source tau 0.072; H=10; Z=8; first 0.054; free 0.013; stratosphere 0.005.

Original target generator:

- `experiments/aerosol-vertical-profile-sensitivity-v1/opac_vertical_templates.py`
- blob `8e8175ae771438b91fc9543b329175c193a215a4`

Original v1 protocol blob:

`5dddbac21e9ac395bd482d0d376577a6e5dd8bb0`

The old effective representation is permanently forbidden:

```text
aerosol_species_file continental_average
aerosol_file tau <state>
```

## 7. PR #596 — corrected four-species renderer PASS

PR #596 remains Draft/open/unmerged on final head:

`8adfd4fafa4c039394d12e6f6aff1795b750f4d2`

Preserved failures — never rerun:

- `33192621988`: failed before reconstruction because `mkdir evidence` was non-idempotent; artifact `9694407319`, digest `sha256:78673b59a68b78893898638da243740b2ea904c2bfea72b565dae101f0202cf2`.
- `33192854324`: all runtime renderer checks passed; failed only in a static self-matching scope check; artifact `9694507494`, digest `sha256:9b0e2d636a29bfa171e1feace58ab2bef4e9803b95efb196b5acc381ac25872c`.

Final evidence:

- renderer blob `99f61e1daa03cecef055a3773544574738d65082`
- dedicated `33193123594` SUCCESS
- repo contract `33193123597` SUCCESS
- artifact `9694613680`
- digest `sha256:5e6942d879326ffc2dc8805d7649086cae32ad2e16aeec19a62cd3b0a89e3e27`
- report content SHA `20f26c65ce1d01e4514ceea36f2c95ecbf421d05a805b0a3d23e58f1fc9dda24`
- status `PASS_FIVE_FROZEN_AVPS_TEMPLATES_RENDERED_AS_COMMON_SCALAR_FOUR_SPECIES_NULL_TAU_SHAPES`

Validated scientific representation:

```text
aerosol_default
aerosol_species_library OPAC
aerosol_species_file profiles/<state>.four-species.dat INSO WASO SOOT SUSO
aerosol_set_tau_at_wvl 550 <AOD550>
```

Baseline explicit four-species vs built-in `continental_average` normalized NULL layer-tau error was exactly zero. All five targets passed at AOD550 0.10 and 0.30. Worst target error was about `3.92e-5` max fraction and `2.79e-4` L1, inside the frozen `6e-5` / `1.5e-3` gates. The 29x29 fallback is therefore unnecessary.

Exact rendered profile SHA-256 values:

- continental average `ceed598f7681951cd0e6208b267beb5b41a52ab10311f37ce76f925700caff3d`
- maritime clean `487b67bd7dbe89d12d032fdf2b33cab545e16a2e0697170648317f1a76362a67`
- desert `2b4d2e03c6ae3143d9bb05d2da49f57f75172dc1f24d34f7d4a4939bf9952fef`
- arctic `98f2fa5428c830764252fd0a2662b0f5c957fc027ffcb7bdc0a5e500dfd7d3d6`
- antarctic `ee063c6dca68cf9a31d8bb9d993f1fed5cb34c8bb056ac180c97171b5d6b4f19`

## 8. PR #597 — AVPS v2 scientific preregistration FULL PASS

Fresh stage:

`aerosol-vertical-profile-sensitivity-v2`

PR #597 is Draft/open/unmerged on branch `review/aerosol-vertical-profile-sensitivity-v2-prereg`.

Initial head `7ccf942a47d74a4db9afc8e490d600d08c6caed4` / run `33193624797` failed only in the final static no-solver self-match; all substantive prereg gates had passed. Never rerun it.

Final head:

`2bba54c6e78ed99d169887eef51d0c88d812b6f1`

- scientific review files unchanged from the initial head
- dedicated `33193778176` SUCCESS
- repo contract `33193778174` SUCCESS
- artifact `9694863701`
- digest `sha256:7de79aa4d8d9b51ad8ca4b1bdaceedae7ee5df17b3dd79c43c21cdaf9ae9a171`
- receipt content SHA `717411c68c48f34f79c93da3ae8024e3d99a32c78ebe63935d262b3548e62c61`
- skeleton canonical SHA `a8d2d8f59aec01d82d8d98672152d00c11261660b0a69a59e2716c2edabd2b02`
- skeleton file SHA `a1a41d4b5ee07e08dc63d1b1c0eeda963706ca7b1adca8a6d89ffbd036d47bf4`
- 360 fresh `avps-v2-*` case identities
- 72 CRN groups
- 5 states/group
- 120 distinct pre-seed science surfaces
- seed count 0
- scientific ordinal null
- no solver/science/result opening

Fresh future seed namespace:

`aerosol-vertical-profile-sensitivity-v2|group-seed|sha256-v1`

## 9. PR #598 — AVPS v2 candidate-seed freshness FULL PASS

PR #598 is Draft/open/unmerged on branch:

`review/aerosol-vertical-profile-sensitivity-v2-seed-freshness`

Exact head:

`64e7d68bd876a99aa5af49d97bcb53718238b39b`

This branch is a child of the exact #597 PASS head. It does not change the preregistered scientific screen.

Candidate seeds are **artifact-only**. The 72 numeric values are not tracked in Git, are not copied into PR prose, and have not been applied to cases.

Frozen candidate identities:

- candidate count 72
- seed canonical SHA `02f624d582e9b2caba6b920d65a5e8a8bc8fc1a2693623bc2f73abf5d3f706d2`
- candidate-row canonical SHA `41f70d6a0381db6b569d3f4e17d74bb38b05cf212c2f2e432455a502f73dc670`
- all 72 values unique
- all within the scanner-visible signed-32-bit-compatible domain
- all within-ledger collision counters zero

Final evidence:

- dedicated freshness run `33194319669` attempt 1 SUCCESS
- repo contract `33194319698` SUCCESS
- artifact `9695260362`
- artifact digest `sha256:fb4613d654121098c9d247d6ed8b0f0788b26a179b5ff103dc01ed7d50c9f0db`
- `seed-freshness-proof.json` raw SHA `d418db61cd4e7d54a7772d0793d686eb486fc06b4880411043384bc8fddb093e`
- repository-global scan raw SHA `fabc299c0fc9ce35b7a5cfce32385e82e42cd1ed88688b4d938d591e3fb3b170`
- tracked-tree scan raw SHA `a7e48442156bc4ab37513e6ec622540e3027bc236946ed9c3d520c93566a3cd7`
- status `PASS_CANDIDATE_SEEDS_FRESH_REVIEW_ONLY_NOT_ALLOCATED`

Freshness results:

- tracked files audited: 1681
- tracked candidate-seed literals: 0
- tracked-tree external collisions: 0
- repository-global collisions: 0
- repository-global post-fence candidate collisions: 0
- repository-global collision surface scan PASS
- double enumeration stable: true
- audited branch head matched expected head: true
- prior proof-artifact count: 0; proof identity fresh: true
- stable context SHA `d682872b7688a5d96ef7771646311b8701504eaf66885773f295cbe00a6ea45a`
- snapshot fence SHA `6c71c44a2d3aa15491d1ad85a621e0d8b871ccdcb7ae97a7a9c385505799523b`
- post-fence arrivals: zero for branches, runs, artifacts, PRs, issues, issue comments, PR review comments, commit comments and Issue #60 comments
- authorization-time freshness recheck remains required

Issue #60 non-seed checkpoint:

- comment `5455637794`
- records hashes/counts/artifact identity only, not seed values

Expected stacked-review noise:

- run `33194319621` (`Review aerosol vertical-profile sensitivity v2 preregistration`) FAILED only because #598's head branch is the seed-freshness branch rather than the preregistration branch; the workflow stopped at its branch-identity gate and all substantive prereg steps were skipped.
- This is not a seed/science failure and must not be rerun or hidden.

#598 does **not** apply seeds, allocate an ordinal, create authorization/dispatch, or run a solver.

## 10. Frozen AVPS v2 scientific screen

Preserve unless independently changed before any seed/result allocation:

- AFGL-US, observer 0 m, albedo 0.15
- wavelengths 380–780 nm, frozen 1-nm grid
- MYSTIC spherical 1D, VROOM, `mc_std`
- 20,000,000 photons/case
- Sun depression 2/4/6/8 deg
- AOD550 0.10/0.30
- geometries alt/azrel 10/30, 30/90, 45/180
- 3 replicates
- 24 analysis cells, 72 CRN groups, 5 states/group, 360 cases
- same fresh seed across five states within each CRN group
- primary photopic, scotopic and Johnson-V channels
- paired log alternative/reference contrasts
- retain all three paired replicates; mean/sample SD/SE
- no p-values, confidence intervals, epsilon substitution, adaptive case addition or post-result rule changes
- full raw spectra retained as evidence; no arbitrary production full-spectrum interpolation claim

## 11. Current next step — v2 preauthorization / global-ordinal audit

**No ordinal has been allocated yet.**

Next gate must be separate and review-only. It must:

1. bind exact #597 PASS and exact #598 seed-freshness PASS identities;
2. rebuild the 72 candidate seeds artifact-only from the frozen v2 namespace/group IDs;
3. repeat repository-global seed freshness in authorization-recheck mode against the current exact head;
4. re-read Issue #60 and all authorization/dispatch identity surfaces;
5. conservatively derive the latest globally observed/consumed scientific ordinal;
6. require that there is no newer live allocation/reservation/dispatch identity;
7. if and only if ordinal 40 is still the latest consumed and no higher identity exists, report **candidate next ordinal = 41**;
8. do not post an allocation marker, create an authorization branch or apply seeds during this preauthorization gate;
9. freeze exact intended authorization/dispatch branch names, execution key, candidate-seed hashes, profile hashes, runtime tree and 360-case design in an artifact;
10. require a later separate one-file authorization review before any ordinal allocation or science.

Candidate seeds may be included only inside immutable review/authorization artifacts where needed; do not track the numeric values in Git prose/source.

## 12. Hard prohibitions

Do not:

- rerun/reuse ordinal 40;
- allocate ordinal 41 before the fresh preauthorization/ordinal audit and separate authorization review;
- reuse ordinal-40 case IDs, group IDs or seeds;
- GitHub-rerun consumed v2/v3/v4/trace/v5/#592 identities;
- GitHub-rerun #596 failed runs `33192621988` or `33192854324`;
- GitHub-rerun #597 failed run `33193624797`;
- GitHub-rerun #598 stacked branch-identity failure `33194319621`;
- infer scientific effect size/materiality from capability/NULL/prereg/seed audits;
- use #592 equal-0.25 mass weights scientifically;
- replace `continental_average` with INSO-only;
- reintroduce competing `aerosol_file tau`;
- use failed `.nc` aliases;
- alter profiles/AOD/geometry/provider/cycle from Taylor/Jerusalem residual direction or magnitude;
- use ordinal-40 zero contrast to tune AVPS v2;
- proceed to Level-B profile mapping before fresh replacement scientific evidence;
- move `main` for convenience;
- create production authorization from review evidence alone.

## 13. Broader retained state

- AOPS ordinal 37, AFPF ordinal 38 and ASIV ordinal 39 remain closed for their stated scopes.
- Taylor #508 remains evidence that independently constrained aerosol vertical structure can materially alter direct-MYSTIC twilight radiance.
- Taylor atmosphere provenance/uncertainty boundaries #535/#529/#536 remain authoritative.
- Better independent Taylor-night atmospheric acquisition is a separate lane and must not be used to fit residuals.
- Anti-fitting rules remain binding.

## 14. Resume checklist

- [ ] confirm `main == 99ade7798627e67921139697ba1a004fa8a304bb`;
- [ ] preserve #596 final artifact `9694613680` and failed-attempt history;
- [ ] preserve #597 artifact `9694863701`, receipt SHA `717411c6...`, skeleton SHA `a8d2d8f5...`;
- [ ] preserve #598 artifact `9695260362`, digest `sha256:fb4613d654121098c9d247d6ed8b0f0788b26a179b5ff103dc01ed7d50c9f0db`;
- [ ] preserve #598 candidate hashes `02f624d5...` / `41f70d6a...` and Issue #60 checkpoint `5455637794`;
- [ ] keep candidate seed numbers untracked/unapplied;
- [ ] open a separate v2 preauthorization review with authorization-time seed recheck and fresh global ordinal audit;
- [ ] only after preauthorization PASS create a separately reviewed authorization identity;
- [ ] allocate ordinal only after that authorization review succeeds and all fresh checks still pass;
- [ ] keep Taylor/Jerusalem residuals closed throughout design, execution and primary result opening;
- [ ] update this handoff after preauthorization, authorization/ordinal allocation, dispatch, Gate-0 and result opening.

## 15. One-line live status

**The ordinal-40 transport defect is now corrected and independently validated. AVPS v2 has a fresh 360-case scientific identity with exact four-species profile bytes (#597) and a fresh 72-seed candidate set that is clean across the tracked tree and repository-global two-pass audit (#598), but those seeds remain artifact-only/unapplied and ordinal 41 remains unallocated. The active next gate is a zero-runtime v2 preauthorization/global-ordinal audit with authorization-time seed freshness recheck; no replacement scientific MYSTIC run is authorized yet.**