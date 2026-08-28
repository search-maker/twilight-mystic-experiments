# STAR VISIBILITY / MYSTIC — LIVE CURRENT HANDOFF

**Live refresh: 2026-08-28 — replacement AVPS v2 is now reviewed through preregistration, renderer validation, candidate-seed freshness, and the fresh preauthorization/global-ordinal gate (#599). The live surface proves ordinal 40 is still the latest consumed/max authoritative scientific ordinal and 41 is the next available value, but ordinal 41 is NOT allocated or reserved. The next safe step is an ordinal-free v2 control/execution-package review before any authorization identity is created.**

The filename is historical. This file is the current computational/scientific checkpoint.

---

## 1. Immutable baseline

Repository: `search-maker/twilight-mystic-experiments`

Frozen `main` remains:

`99ade7798627e67921139697ba1a004fa8a304bb`

Frozen main tree:

`2d4bb1df136bff2da93f191e5518b94b3d7fecfc`

Do not move `main` merely to continue this lane.

---

## 2. Ordinal 40 is consumed and scientifically non-informative

AVPS v1 scientific ordinal 40 reached exact 360/360 case evidence, but state-specific vertical-profile files differed while solver outputs were byte-identical. The intended vertical state therefore did not reach effective solver physics.

Authoritative classification:

`EXECUTION/EVIDENCE PIPELINE VALID; SCIENTIFIC VERTICAL-PROFILE CONTRAST NON-INFORMATIVE.`

Never rerun/reuse ordinal 40 and never cite its zero contrast as physical vertical-profile insensitivity.

Retained evidence:

- recovery science `33139545997` SUCCESS, exact 360/360 cases
- Gate-0 artifact `9676069031`, digest `sha256:70dedcd16209dea74a9ed67a1dc7377c123f1a62fd18741b1e15692702011fc8`
- Phase A `33170006532` SUCCESS
- Phase B opening `33170855407` SUCCESS
- exact consumed marker: `ORDINAL40_AVPS_V1_DISPATCH_CONSUMED`

Ordinal 40 and every ordinal-40 seed/case identity are retired forever.

---

## 3. OPAC resolver diagnosis and corrected transport

Historical consumed capability identities — never GitHub-rerun:

- PR #586 / v2 run `33177704575` FAILURE before MYSTIC
- PR #587 / v3 run `33180158034` FAILURE after testing `aerosol/OPAC/optprop/INSO.nc`
- PR #588 / v4 run `33184511183` FAILURE after testing `aerosol/OPAC/INSO.nc`; artifact `9691137631`, digest `sha256:b538b58a44873eca3eebd64493edf3d9b88991e73ccb48f0d5e71ff1c9f2aee4`
- PR #589 syscall trace `33185460954` SUCCESS; artifact `9691518729`, digest `sha256:07fb60de7bef96253eaf29cb9303a83bab7f3f1952431c73a26499357b4d572a`

The trace directly observed the locked binary requesting:

```text
data/aerosol/OPAC/optprop/INSO
```

with **no extension**.

### PR #590 — single-species transport capability PASS

- head `f0675ec48c637509cd7a5bb9c2a2746507e5bea8`
- dedicated `33186027699` SUCCESS
- repo contract `33186027637` SUCCESS
- one-shot `33186446347` SUCCESS
- artifact `9691923455`
- digest `sha256:fed6bb961088232e593159c4f50911758802e9209aed86e2a0eef4b403e4d9b7`
- report content SHA `da6d7f66625b63cb5ff4f69845c2953f2a509b3693c82d1f0203900dc7bd21d2`

INSO official source/alias SHA:

`fe10348cbe585315d6e1db382563fdc054204ad35846f371dc9d8abeead36407`

Capability only; no scientific effect-size inference.

---

## 4. Locked `continental_average` composition and four-species capability

### PR #591 — source audit PASS

- head `2bfae9341075eb04fe4621f4f53d4ab56262c22b`
- audit `33187119926` SUCCESS
- repo contract `33187119866` SUCCESS
- artifact `9692162280`
- digest `sha256:cdcb0041a5197e31ff24520b3e653119d11c5d4a1c1b4f727e392ba7e719101e`
- `continental_average.dat` SHA `fc39fda0f8ada2d0a0a872b8b62d684cfccd74f7b0655b5af2dcdec51115e469`
- exact columns `z(km) INSO WASO SOOT SUSO`

Official optical-property SHA-256 values:

- INSO `fe10348cbe585315d6e1db382563fdc054204ad35846f371dc9d8abeead36407`
- WASO `b6df493b77019bf5e22456e8fb8858c5a7d502bcc02fe6fc697ebd4844f2d4f5`
- SOOT `44a0d2060101ca52c90ae64f005118dfba256b1f89a3049e1f758c55d634aa02`
- SUSO `ce0e1bba4219c60af0af14d66a280b0d3d25188276eed0951d31594b947cd472`

### PR #592 — four-species transport capability PASS

- head `18667797a1dd699b6431a6940bac42974c415733`
- dedicated `33188868496` SUCCESS
- repo contract `33188868323` SUCCESS
- one-shot `33189268483` SUCCESS
- artifact `9693056690`
- digest `sha256:f1a2cd69420c63d5214f5082ee0844ec822b9aa2f9f8f13a4b52958ee59ae507`
- report content SHA `6f191c0011c67bc3aeb27add17c25f9c81fd356bb47f42141e7783f6ac52e973`
- status `PASS_FOUR_CONTINENTAL_SPECIES_REACH_DISORT_AND_MYSTIC`
- post-four-alias data tree `5e1814dd36cf861fd85477a97607299248f8272268df7bf428d31bbb6aa4354a`

The equal 0.25 species weights used by #592 were synthetic transport witnesses only and must never become the scientific composition rule.

---

## 5. Exact 550-nm humidity behavior and layer-tau calibration

### PR #593 — OPAC 550-nm/RH source evidence PASS

Final head `223b592208d3dda24217dabcfca9fd27333e4b84`.

- exact-550 audit `33190220896` SUCCESS
- artifact `9693440701`
- digest `sha256:7d8fa290b74f4e15538cd6ff2609f5491caad63258d0aefb8be689f1ce5f8e33`
- report content SHA `7ade25bf8be7c906a5a520fb1c2a13f974ac8ea0fd01e02e35560f2fb1b79a98`
- repo contract `33190220864` SUCCESS

Humidity nodes:

- INSO/SOOT `[0]`
- WASO/SUSO `[0,50,70,80,90,95,98,99] %`

### PR #594 — AFGL-US RH NULL audit PASS

- head `e7f968ee70dbecaf5f315bc8b03627ce1628edef`
- run `33190680002` SUCCESS
- artifact `9693619172`
- digest `sha256:74813789c2bf2842788de16aba6f3269c9f4efec675f6ee758903e4f6c52f9da`
- report content SHA `fd4e691f14f9cab427f7992acfc0435f50442e65e519520e6edae55c250a7f14`
- repo contract `33190679858` SUCCESS

NULL solver only; no scientific RTE. Runtime nearest-OPAC-RH behavior is frozen directly.

### PR #595 — NULL aerosol-tau calibration PASS

Final head `3fcb6328a18747b5a17d5ae75248c04c288e18f9`.

- calibration `33191517143` SUCCESS
- repo contract `33191517521` SUCCESS
- artifact `9693948772`
- digest `sha256:97d431fe31724731a24697233c2154b836159a29299f8f42ea1853ebdf9d266a`
- report content SHA `b3787ecc5baaf0d95ffc1851aad45dbc03a00cded9f5cabb2f3ccb397fa5e709`
- status `PASS_VERBOSE_AEROSOL_SCATTER_PLUS_ABS_IS_LAYER_TAU_AND_AOD_RESCALE_PRESERVES_SHAPE`

Frozen print-precision tolerances:

- AOD sum abs `2.1e-6`
- row-sum vs sum line `7e-5`
- normalized shape max abs `6e-5`
- normalized shape L1 `1.5e-3`

---

## 6. Frozen scientific question and five independent vertical templates

Scientific question:

> At fixed total AOD550 and fixed OPAC `continental_average` wavelength-dependent aerosol optical properties/phase function, how much does independently specified normalized aerosol vertical optical-depth shape change twilight radiance and derived Level-B limiting magnitude?

The maritime/desert/arctic/antarctic labels supply vertical-template parameters only. They do **not** switch aerosol microphysics.

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

Permanently forbidden old effective representation:

```text
aerosol_species_file continental_average
aerosol_file tau <state>
```

---

## 7. PR #596 — corrected four-species renderer PASS

PR #596 remains Draft/open/unmerged on final head:

`8adfd4fafa4c039394d12e6f6aff1795b750f4d2`

Preserved failures — never rerun:

- `33192621988`: failed before reconstruction from a control-plane mkdir defect; artifact `9694407319`.
- `33192854324`: runtime renderer checks passed; failed only in static self-match; artifact `9694507494`.

Final evidence:

- renderer blob `99f61e1daa03cecef055a3773544574738d65082`
- dedicated `33193123594` SUCCESS
- repo contract `33193123597` SUCCESS
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

Baseline explicit four-species vs built-in `continental_average` normalized NULL layer-tau error was exactly zero. All five targets passed at AOD550 0.10 and 0.30; worst target error was about `3.92e-5` max fraction and `2.79e-4` L1, inside the frozen gates.

Exact rendered profile SHA-256 values:

- continental average `ceed598f7681951cd0e6208b267beb5b41a52ab10311f37ce76f925700caff3d`
- maritime clean `487b67bd7dbe89d12d032fdf2b33cab545e16a2e0697170648317f1a76362a67`
- desert `2b4d2e03c6ae3143d9bb05d2da49f57f75172dc1f24d34f7d4a4939bf9952fef`
- arctic `98f2fa5428c830764252fd0a2662b0f5c957fc027ffcb7bdc0a5e500dfd7d3d6`
- antarctic `ee063c6dca68cf9a31d8bb9d993f1fed5cb34c8bb056ac180c97171b5d6b4f19`

---

## 8. PR #597 — replacement AVPS v2 scientific preregistration FULL PASS

Fresh stage:

`aerosol-vertical-profile-sensitivity-v2`

PR #597 remains Draft/open/unmerged on branch `review/aerosol-vertical-profile-sensitivity-v2-prereg`.

Final head:

`2bba54c6e78ed99d169887eef51d0c88d812b6f1`

- dedicated `33193778176` SUCCESS
- repo contract `33193778174` SUCCESS
- artifact `9694863701`
- digest `sha256:7de79aa4d8d9b51ad8ca4b1bdaceedae7ee5df17b3dd79c43c21cdaf9ae9a171`
- receipt content SHA `717411c68c48f34f79c93da3ae8024e3d99a32c78ebe63935d262b3548e62c61`
- skeleton canonical SHA `a8d2d8f59aec01d82d8d98672152d00c11261660b0a69a59e2716c2edabd2b02`

Frozen design:

- 5 independent OPAC Tables 3/5 vertical templates
- fixed `continental_average` optical family
- AOD550 `0.10`, `0.30`
- sun depressions `2,4,6,8 deg`
- 3 geometries
- 3 CRN replicates
- `20,000,000` photons/case
- 72 CRN groups
- 360 cases
- fresh `avps-v2-*` case IDs
- fresh seed namespace `aerosol-vertical-profile-sensitivity-v2|group-seed|sha256-v1`

Review state remains:

- seed count `0`
- scientific ordinal `null`
- no solver execution
- no result opening

The only mechanics correction from v1 is the validated four-species representation. The scientific question/screen remain unchanged.

---

## 9. PR #598 — candidate-seed freshness FULL PASS

PR #598 remains Draft/open/unmerged on branch:

`review/aerosol-vertical-profile-sensitivity-v2-seed-freshness`

Head:

`64e7d68bd876a99aa5af49d97bcb53718238b39b`

- dedicated review `33194319669` attempt 1 SUCCESS
- repo contract `33194319698` attempt 1 SUCCESS
- artifact `9695260362`
- digest `sha256:fb4613d654121098c9d247d6ed8b0f0788b26a179b5ff103dc01ed7d50c9f0db`
- candidate seed count `72`
- candidate-seed canonical SHA `02f624d582e9b2caba6b920d65a5e8a8bc8fc1a2693623bc2f73abf5d3f706d2`
- candidate-row canonical SHA `41f70d6a0381db6b569d3f4e17d74bb38b05cf212c2f2e432455a502f73dc670`
- tracked-tree candidate collisions `0`
- repository-global candidate collisions `0`
- two-pass global enumeration stable

The actual 72 candidate seed values are artifact/workspace-only. **Do not copy them into Git, PR/Issue prose, handoff text, chat output, or user-facing documentation.**

Inherited #597 workflow on the #598 branch failed immediately on branch-binding, as designed; no scientific/seed operation ran in that inherited failure.

Issue #60 contains the exact #598 non-allocation freshness checkpoint.

---

## 10. PR #599 — fresh preauthorization/global-ordinal audit FULL PASS

PR #599:

`Review AVPS v2 preauthorization and global ordinal surface`

Remains Draft/open/unmerged.

- branch `review/aerosol-vertical-profile-sensitivity-v2-preauthorization`
- exact head `a4e4700babddf0924135f5cc6ec6bfd21d8c9ec2`
- base `main == 99ade7798627e67921139697ba1a004fa8a304bb`
- dedicated run `33203372878`, attempt 1 — **SUCCESS**
- repo contract `33203372798`, attempt 1 — **SUCCESS**
- proof artifact `9699064164`
- artifact digest `sha256:b1125375bae24638375853d3724c1c96ba1572dc02e1619eff37d9fdca70b92e`
- preauthorization report content SHA `31db5d10eeff3a18f6d41af3a665818b0b53b1d6187d93263f5988c4229385cd`
- status `PASS_V2_PREAUTHORIZATION_SURFACE_CLEAN_NOT_ALLOCATED`

Authorization-time seed recheck:

- candidate seed count `72`
- global collision count `0`
- two-pass enumeration stable `true`
- post-fence arrivals: all tracked categories `0`
- stable-context SHA `011d0728c004271d8a941642d35c1870c2967425c75e813aa2abca6d9ec5f1c4`
- snapshot-fence SHA `844402c551c910525b07a634841b0bed40b2073463b4f392ddd57713a4047486`

Fresh global scientific-ordinal report:

- authoritative observation count `432`
- ordinal-observation canonical SHA `3c50dc3b6be77189d862e08a04501bd398169314321f8c6e85e07d92e2d279d8`
- latest exact consumed scientific ordinal `40`
- maximum authoritative observed ordinal `40`
- next available scientific ordinal **if separately allocated later** `41`
- proposed future authorization branch `authorization/aerosol-vertical-profile-sensitivity-v2-ordinal-41`
- proposed future dispatch branch `dispatch/aerosol-vertical-profile-sensitivity-v2-ordinal-41`

All final report flags remain false:

- `scientificOrdinalAllocated=false`
- `authorizationCreated=false`
- `dispatchCreated=false`
- `candidateSeedsAppliedToCases=false`
- `scientificExecutionAuthorized=false`
- `solverExecutionAuthorized=false`
- `resultOpeningAuthorized=false`
- `scientificRuntimeSetupPerformed=false`
- `levelBAuthorized=false`
- `productionAuthorized=false`

The workflow performed a fresh global ordinal readback after building the report, uploaded the proof, then performed another final global readback before publishing the terminal non-allocation checkpoint.

Issue #60 exact checkpoint was published by GitHub Actions at 2026-08-28 19:38:18 UTC:

`AEROSOL-VERTICAL-PROFILE-V2-PREAUTHORIZATION`

with audited head `a4e4700b...`, run `33203372878`, attempt 1, PASS status, `latest_consumed=40`, and non-allocation flags.

Inherited #597/#598 workflows on #599 may appear failed because they refuse the wrong branch name at their initial binding step. Those are expected refusal runs and are **not** #599 gates; no candidate/solver work occurs in them.

**Interpretation:** #599 proves that 41 is currently available to a later, separately reviewed authorization step. It does not reserve or allocate 41.

---

## 11. Current next gate — ordinal-free v2 control/execution-package review

Do **not** create the ordinal-41 authorization branch yet.

Reason: the corrected v2 scientific preregistration, rendered profiles and candidate ledger are reviewed, but the v2 authorization/dispatch/science control package itself has not yet been independently reviewed as an exact immutable byte surface.

Required next sequence:

1. fresh-search PRs/branches to ensure no parallel v2 control review exists;
2. create a new **ordinal-free control review** from frozen main, not from an authorization identity;
3. port the already-proven AVPS v1 360-case orchestration/analysis safety pattern, but replace only the identity/profile mechanics required by v2;
4. bind exact #596 rendered-profile artifact/head/run/digest and profile SHA-256 values;
5. bind exact #597 preregistration head/run/contract/artifact/skeleton hash;
6. bind exact #598 candidate-ledger canonical hashes and proof artifact without exposing actual seed values in Git;
7. bind #599 preauthorization proof and require it to remain Draft/open/unmerged / attempt-1 SUCCESS;
8. freeze control material capable of constructing a future exact authorization ledger, dispatch guard, preflight, 360-case execution, raw-evidence contract, aggregation and closed-result workflow;
9. keep all activation/dispatch workflows inactive in review (for example under a recovery/inactive template path) and prohibit workflow_dispatch/manual execution;
10. review repository-wide contract plus dedicated control tests on one exact head;
11. only after that control review passes may a separate authorization identity allocate ordinal 41.

### Control architecture requirement

Prefer a two-commit future allocation architecture:

- reviewed **control parent** over frozen main containing only exact reviewed control bytes;
- one direct-child **authorization commit** adding the immutable authorization document / applying the artifact-only candidate ledger;
- authorization branch creation itself is an authoritative reservation and must therefore happen only after the control parent has passed review and a fresh final ordinal/seed audit still says 41 is available.

Do not create a branch beginning `authorization/` or `dispatch/` merely to prepare controls; those names are authoritative global-ordinal surface.

---

## 12. v2 control package: science and execution invariants to preserve

The control review must preserve the #597 science exactly:

- stage `aerosol-vertical-profile-sensitivity-v2`
- 72 CRN groups / 360 cases
- 5 vertical states per group
- AOD550 0.10/0.30
- sun depressions 2/4/6/8 deg
- 3 frozen geometries
- 3 replicates
- 20M photons/case
- same fresh group seed across all five states within each group
- corrected four-species explicit profile surface only
- no `aerosol_file tau`
- no target-residual selection

Reuse AVPS v1 orchestration/analysis safeguards where scientifically unchanged, including:

- exact case/group cardinality refusal
- one syntax check and one solver execution per case
- process-group-safe timeout
- attempt-1-only scientific identity
- no GitHub rerun/retry/resume
- raw spectral evidence retained
- exact result universe frozen before opening
- paired CRN contrasts retained by replicate
- no epsilon substitution
- no p-values/confidence intervals created post hoc
- no universal minute conversion
- Taylor/Jerusalem scoring forbidden during this experiment

Do not silently reuse v1 stage IDs, v1 case IDs, v1 seed namespace, ordinal-40 seed values, authorization refs, or old custom-tau directives.

---

## 13. Hard prohibitions at this checkpoint

Do not:

- rerun/reuse ordinal 40;
- create ordinal 41 authorization/dispatch before v2 control review passes;
- expose/copy the 72 candidate seed values from #598/#599 artifacts into tracked Git or prose;
- modify candidate seed values after results exist;
- use Taylor/Jerusalem residual direction or magnitude to choose vertical states, AODs, geometries, seeds, gates or thresholds;
- reintroduce `aerosol_file tau` beside `aerosol_species_file`;
- use failed `.nc` OPAC aliases;
- infer science effect size from #590/#592 capability runs;
- infer production materiality from NULL renderer validation;
- proceed to Level-B profile mapping before replacement scientific results are validly executed/opened;
- move `main` for convenience;
- use GitHub Re-run on any consumed/failed one-shot scientific or capability identity.

---

## 14. Broader retained project state

- AOPS ordinal 37, AFPF ordinal 38 and ASIV ordinal 39 remain closed for their stated scopes and should not be duplicated.
- Taylor #508 remains evidence that independently constrained aerosol vertical structure can materially alter direct-MYSTIC twilight radiance.
- Taylor atmosphere provenance/uncertainty boundaries #535/#529/#536 remain authoritative.
- Better independent Taylor-night atmospheric acquisition remains a separate lane and must not be used to fit the renderer/profile experiment.
- Anti-fitting rules remain binding throughout.

---

## 15. Resume checklist

Before the next write:

- [ ] confirm `main == 99ade7798627e67921139697ba1a004fa8a304bb`;
- [ ] confirm #596/#597/#598/#599 remain Draft/open/unmerged on the exact heads above;
- [ ] confirm #599 run `33203372878` and contract `33203372798` remain attempt-1 SUCCESS;
- [ ] preserve #599 artifact `9699064164`, digest `sha256:b1125375bae24638375853d3724c1c96ba1572dc02e1619eff37d9fdca70b92e`;
- [ ] confirm the Issue #60 #599 checkpoint remains exact and unique;
- [ ] search for parallel v2 control work before creating it;
- [ ] do not create an authorization/dispatch branch while merely preparing controls;
- [ ] keep candidate seed values artifact-only;
- [ ] after any control-review PASS/FAIL, authorization allocation, dispatch, Gate-0, or result-opening transition, update this handoff immediately.

---

## 16. One-line live status

**AVPS v2 is now cleanly reviewed through corrected four-species transport/renderer, full scientific preregistration (#597), 72-candidate repository-global seed freshness (#598), and fresh authorization-time seed + global-ordinal preauthorization (#599). #599 proves ordinal 40 is still latest consumed/max authoritative and 41 is the next available value, but 41 is NOT allocated. Next: build and review an ordinal-free v2 control/execution package; only after that passes may a fresh final audit allocate ordinal 41 in a separate authorization identity.**
