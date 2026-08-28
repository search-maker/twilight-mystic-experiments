# STAR VISIBILITY / MYSTIC — LIVE CURRENT HANDOFF

**Live refresh: 2026-08-28 — replacement AVPS v2 is reviewed through renderer validation (#596), scientific preregistration (#597), candidate-seed freshness (#598), preauthorization/global-ordinal audit (#599), and disabled control/package review (#600). A fresh solver-free authorization-control/materializer review is now open as Draft PR #601 on exact head `c10ec3be3903677c57a0c635e8e9e10658bfbb29`. Scientific ordinal 41 is still NOT allocated or reserved.**

The filename is historical. This file is the live computational/scientific checkpoint and must be refreshed after every material authorization/dispatch/science/result transition.

---

## 1. Immutable baseline

Repository: `search-maker/twilight-mystic-experiments`

Frozen `main`:

`99ade7798627e67921139697ba1a004fa8a304bb`

Frozen main tree:

`2d4bb1df136bff2da93f191e5518b94b3d7fecfc`

Do not move `main` merely to continue this lane.

---

## 2. Ordinal 40 is consumed and scientifically non-informative

AVPS v1 ordinal 40 reached exact 360/360 execution evidence, but the intended state-specific vertical-profile variation did not reach effective solver physics. State-specific profile inputs differed while the solver spectra were byte-identical across states.

Authoritative classification:

`EXECUTION/EVIDENCE PIPELINE VALID; SCIENTIFIC VERTICAL-PROFILE CONTRAST NON-INFORMATIVE.`

Retained evidence includes:

- recovery science run `33139545997` — SUCCESS, exact 360/360 cases
- Gate-0 artifact `9676069031`, digest `sha256:70dedcd16209dea74a9ed67a1dc7377c123f1a62fd18741b1e15692702011fc8`
- Phase A `33170006532` — SUCCESS
- Phase B opening `33170855407` — SUCCESS
- exact Issue #60 consumed marker: `ORDINAL40_AVPS_V1_DISPATCH_CONSUMED`

Never rerun or reuse ordinal 40, its seeds, case IDs, authorization identity, or dispatch identity. Never cite its exact-zero contrast as physical vertical-profile insensitivity.

---

## 3. Corrected OPAC species-profile transport is established

Historical diagnostic/capability chain:

- #586 / run `33177704575` — FAILURE before MYSTIC
- #587 / run `33180158034` — FAILURE
- #588 / run `33184511183` — FAILURE; artifact `9691137631`, digest `sha256:b538b58a44873eca3eebd64493edf3d9b88991e73ccb48f0d5e71ff1c9f2aee4`
- #589 syscall trace `33185460954` — SUCCESS; artifact `9691518729`, digest `sha256:07fb60de7bef96253eaf29cb9303a83bab7f3f1952431c73a26499357b4d572a`

The trace directly proved that the locked libRadtran binary requests no-extension OPAC optical-property aliases such as:

```text
data/aerosol/OPAC/optprop/INSO
```

### #590 — single-species capability PASS

- head `f0675ec48c637509cd7a5bb9c2a2746507e5bea8`
- dedicated `33186027699` SUCCESS
- contract `33186027637` SUCCESS
- one-shot `33186446347` SUCCESS
- artifact `9691923455`
- digest `sha256:fed6bb961088232e593159c4f50911758802e9209aed86e2a0eef4b403e4d9b7`

### #591 — exact `continental_average` source audit PASS

`continental_average.dat` has exact columns:

`z(km) INSO WASO SOOT SUSO`

Official optical-property SHA-256 values:

- INSO `fe10348cbe585315d6e1db382563fdc054204ad35846f371dc9d8abeead36407`
- WASO `b6df493b77019bf5e22456e8fb8858c5a7d502bcc02fe6fc697ebd4844f2d4f5`
- SOOT `44a0d2060101ca52c90ae64f005118dfba256b1f89a3049e1f758c55d634aa02`
- SUSO `ce0e1bba4219c60af0af14d66a280b0d3d25188276eed0951d31594b947cd472`

### #592 — four-species transport capability PASS

- head `18667797a1dd699b6431a6940bac42974c415733`
- dedicated `33188868496` SUCCESS
- contract `33188868323` SUCCESS
- one-shot `33189268483` SUCCESS
- artifact `9693056690`
- digest `sha256:f1a2cd69420c63d5214f5082ee0844ec822b9aa2f9f8f13a4b52958ee59ae507`
- status `PASS_FOUR_CONTINENTAL_SPECIES_REACH_DISORT_AND_MYSTIC`
- four-alias data tree `5e1814dd36cf861fd85477a97607299248f8272268df7bf428d31bbb6aa4354a`

The equal synthetic weights used in #592 were transport witnesses only and are not the scientific composition rule.

---

## 4. RH / NULL calibration and corrected renderer

### #593 — exact 550-nm/RH source evidence PASS

- head `223b592208d3dda24217dabcfca9fd27333e4b84`
- run `33190220896` SUCCESS
- artifact `9693440701`
- digest `sha256:7d8fa290b74f4e15538cd6ff2609f5491caad63258d0aefb8be689f1ce5f8e33`

Humidity nodes:

- INSO/SOOT `[0]`
- WASO/SUSO `[0,50,70,80,90,95,98,99] %`

### #594 — AFGL-US RH NULL audit PASS

- head `e7f968ee70dbecaf5f315bc8b03627ce1628edef`
- run `33190680002` SUCCESS
- artifact `9693619172`
- digest `sha256:74813789c2bf2842788de16aba6f3269c9f4efec675f6ee758903e4f6c52f9da`

### #595 — NULL aerosol-tau calibration PASS

- head `3fcb6328a18747b5a17d5ae75248c04c288e18f9`
- run `33191517143` SUCCESS
- contract `33191517521` SUCCESS
- artifact `9693948772`
- digest `sha256:97d431fe31724731a24697233c2154b836159a29299f8f42ea1853ebdf9d266a`
- status `PASS_VERBOSE_AEROSOL_SCATTER_PLUS_ABS_IS_LAYER_TAU_AND_AOD_RESCALE_PRESERVES_SHAPE`

### #596 — four-species AVPS renderer PASS

Final head:

`8adfd4fafa4c039394d12e6f6aff1795b750f4d2`

- dedicated `33193123594` SUCCESS
- contract `33193123597` SUCCESS
- artifact `9694613680`
- digest `sha256:5e6942d879326ffc2dc8805d7649086cae32ad2e16aeec19a62cd3b0a89e3e27`
- renderer blob `99f61e1daa03cecef055a3773544574738d65082`
- status `PASS_FIVE_FROZEN_AVPS_TEMPLATES_RENDERED_AS_COMMON_SCALAR_FOUR_SPECIES_NULL_TAU_SHAPES`

Validated scientific representation:

```text
aerosol_default
aerosol_species_library OPAC
aerosol_species_file profiles/<state>.four-species.dat INSO WASO SOOT SUSO
aerosol_set_tau_at_wvl 550 <AOD550>
```

Permanently forbidden old composition:

```text
aerosol_species_file continental_average
aerosol_file tau <state>
```

Exact rendered profile SHA-256 values:

- continental average `ceed598f7681951cd0e6208b267beb5b41a52ab10311f37ce76f925700caff3d`
- maritime clean `487b67bd7dbe89d12d032fdf2b33cab545e16a2e0697170648317f1a76362a67`
- desert `2b4d2e03c6ae3143d9bb05d2da49f57f75172dc1f24d34f7d4a4939bf9952fef`
- arctic `98f2fa5428c830764252fd0a2662b0f5c957fc027ffcb7bdc0a5e500dfd7d3d6`
- antarctic `ee063c6dca68cf9a31d8bb9d993f1fed5cb34c8bb056ac180c97171b5d6b4f19`

---

## 5. Frozen replacement AVPS v2 scientific design — #597 FULL PASS

Stage:

`aerosol-vertical-profile-sensitivity-v2`

PR #597 remains Draft/open/unmerged.

- branch `review/aerosol-vertical-profile-sensitivity-v2-prereg`
- head `2bba54c6e78ed99d169887eef51d0c88d812b6f1`
- dedicated `33193778176` SUCCESS
- contract `33193778174` SUCCESS
- artifact `9694863701`
- digest `sha256:7de79aa4d8d9b51ad8ca4b1bdaceedae7ee5df17b3dd79c43c21cdaf9ae9a171`
- skeleton canonical SHA `a8d2d8f59aec01d82d8d98672152d00c11261660b0a69a59e2716c2edabd2b02`

Frozen scientific design:

- same five independent OPAC Tables 3/5 vertical templates
- fixed `continental_average` optical family
- AOD550 `0.10`, `0.30`
- solar depressions `2,4,6,8 deg`
- three geometries
- three CRN replicates
- `20,000,000` photons/case
- 72 CRN groups
- 360 cases
- fresh `avps-v2-*` case namespace
- fresh v2 group-seed namespace
- exact #596 four-species profiles
- no `aerosol_file tau`
- no Taylor/Jerusalem residual-driven selection

The scientific question/screen are unchanged from the intended v1 question; only the broken transport representation was corrected.

---

## 6. #598 — candidate-seed freshness FULL PASS

PR #598 remains Draft/open/unmerged.

- branch `review/aerosol-vertical-profile-sensitivity-v2-seed-freshness`
- head `64e7d68bd876a99aa5af49d97bcb53718238b39b`
- dedicated `33194319669` SUCCESS
- contract `33194319698` SUCCESS
- artifact `9695260362`
- digest `sha256:fb4613d654121098c9d247d6ed8b0f0788b26a179b5ff103dc01ed7d50c9f0db`
- candidate count: 72 group seeds
- candidate-set canonical SHA `02f624d582e9b2caba6b920d65a5e8a8bc8fc1a2693623bc2f73abf5d3f706d2`
- candidate-row canonical SHA `41f70d6a0381db6b569d3f4e17d74bb38b05cf212c2f2e432455a502f73dc670`
- repository-global collision count: zero

**Critical secrecy/identity rule:** the actual 72 candidate seed values are artifact/in-memory only. Never copy them into tracked Git, PR/Issue prose, this handoff, chat output, or user-facing documentation. They are not applied to scientific cases until a later valid authorization makes that in-memory transition permissible.

---

## 7. #599 — fresh preauthorization/global ordinal surface FULL PASS

PR #599 remains Draft/open/unmerged.

- branch `review/aerosol-vertical-profile-sensitivity-v2-preauthorization`
- head `a4e4700babddf0924135f5cc6ec6bfd21d8c9ec2`
- dedicated `33203372878` SUCCESS, attempt 1
- contract `33203372798` SUCCESS, attempt 1
- artifact `9699064164`
- digest `sha256:b1125375bae24638375853d3724c1c96ba1572dc02e1619eff37d9fdca70b92e`
- status `PASS_V2_PREAUTHORIZATION_SURFACE_CLEAN_NOT_ALLOCATED`

Final live observation at #599:

- latest exact consumed scientific ordinal = 40
- maximum authoritative scientific ordinal observed = 40
- next available candidate = 41
- scientific ordinal allocated = false
- authorization created = false
- dispatch created = false
- candidate seeds applied = false

Issue #60 contains the exact terminal #599 non-allocation checkpoint.

---

## 8. #600 — disabled v2 control/package FULL PASS

PR #600 remains Draft/open/unmerged.

- branch `review/aerosol-vertical-profile-sensitivity-v2-control-v1`
- exact head `8a5d73974b02ba21fc2f010bbd911538e6981de2`
- dedicated `33205661865` SUCCESS, attempt 1
- repository contract `33205661834` SUCCESS, attempt 1
- artifact `9699546728`
- digest `sha256:9badcdc03bbeb181f731352afc48b75c67c14dc95a986fcf32163677d4ea972d`
- status `PASS_DISABLED_V2_CONTROL_PACKAGE_REVIEW_NO_ORDINAL_NO_AUTHORIZATION_NO_SOLVER`

The package freezes:

- exact 360 cases / 72 CRN groups / five states
- candidate seed identity by canonical hashes only; values are not serialized
- exact #596 profile hashes
- exact four-alias OPAC runtime identity
- authorization-gated adapter that can apply group seeds only in memory after a valid future authorization
- no science workflow/dispatch identity
- no solver execution
- no result opening

Important reviewed blobs from #600:

- `control_package.py` `62bacf15d145051fcc5259a24c310eac761d0e74`
- `adapter.py` `c245eac2fe5b5d026e46ec4253bc377c5fde97ec`
- `renderer.py` `99f61e1daa03cecef055a3773544574738d65082`
- `rh_audit_dependency.py` `095ff86f12a79dc312a51f734b0a03bd318f2337`
- `runtime_stage.py` `0d3ac10f3ef7d22f0205854233a6c37cbba03f7c`

---

## 9. Current active gate — #601 authorization-control/materializer review IN PROGRESS

Correct branch:

`review/aerosol-vertical-profile-sensitivity-v2-authorization-control-v2`

It was created directly from frozen main and its single current commit is:

`c10ec3be3903677c57a0c635e8e9e10658bfbb29`

Parent:

`99ade7798627e67921139697ba1a004fa8a304bb`

Tree:

`7f7713a4e2c519fe14e23fb9afcf19812b95a631`

Draft PR:

#601 — `Review AVPS v2 authorization control and zero-runtime materializer`

Current gates created on exact head `c10ec3be...`:

- dedicated authorization-control review `33213321554` — queued at this handoff refresh
- repository contract `33213321502` — queued at this handoff refresh

#601 is solver-free. It binds the exact #599/#600 reviewed bytes and adds:

- `review/aerosol-vertical-profile-sensitivity-v2-authorization-control-v2/PROTOCOL.md`
- `.../build_authorization.py`
- `.../authorization_guard.py`
- `.github/workflows/aerosol-vertical-profile-sensitivity-v2-authorization-control-v2-review.yml`
- `.github/workflows/aerosol-vertical-profile-sensitivity-v2-authorization-review.yml`

The dedicated gate is required to:

1. prove #601 is one direct child of frozen main;
2. bind #599/#600 exact PR/run/artifact identities;
3. prove all reused prereg/seed/control/renderer/runtime bytes are the exact reviewed Git blobs;
4. repeat the exact-head tracked-tree candidate-seed leak scan;
5. repeat the two-pass repository-global seed collision scan;
6. repeat the conservative global-ordinal audit and require consumed/max = 40 and next candidate = 41, with no ordinal-41 authorization/dispatch identity or Issue #60 marker;
7. materialize a proposed `authorization.json` only as an Actions artifact;
8. prove that the authorization document contains no literal candidate seed value;
9. perform a final global-ordinal readback after materialization.

The materializer artifact itself is **not** an allocation or reservation.

### Abandoned non-authoritative branch — do not use

A preliminary branch was accidentally started from #600 head rather than frozen main:

`review/aerosol-vertical-profile-sensitivity-v2-authorization-control-v1`

Its only new commit is:

`7d5c945deb3841af790e7c9ef7a46bebe45ba896`

It contains only a protocol draft. No PR was opened, no authorization/dispatch branch was created, no scientific ordinal was allocated/reserved, no seed was applied and no solver ran. It is historical/abandoned and must not be used as the parent of any authorization identity.

---

## 10. Exact boundary at this checkpoint

At the time of this handoff refresh:

- ordinal 40 = consumed and retired
- ordinal 41 = **not allocated and not reserved**
- no `authorization/aerosol-vertical-profile-sensitivity-v2-ordinal-41` branch exists
- no `dispatch/aerosol-vertical-profile-sensitivity-v2-ordinal-41` branch exists
- no `ORDINAL41_...` allocation/consumption marker exists in Issue #60
- candidate seed values remain artifact/in-memory only
- no AVPS v2 scientific solver run exists
- no AVPS v2 result has been opened
- no Level-B/production mapping from AVPS v2 exists

Issue #60 also contains handoff checkpoint comment `5457950462`, recording #599/#600 completion and the same non-allocation boundary.

---

## 11. Next safe sequence

If and only if both #601 gates finish SUCCESS on exact head `c10ec3be3903677c57a0c635e8e9e10658bfbb29`:

1. record #601 dedicated run, contract, artifact ID/digest and materialized authorization SHA in this handoff;
2. verify the global ordinal surface is still clean after artifact publication;
3. create `authorization/aerosol-vertical-profile-sensitivity-v2-ordinal-41` as **one direct child of the exact reviewed #601 head**;
4. change exactly one file: `review/aerosol-vertical-profile-sensitivity-v2-authorization-control-v2/authorization.json`, byte-identical to the verified #601 materializer artifact;
5. open a Draft authorization PR targeting the exact #601 control branch, not `main`;
6. require attempt-1 authorization review PASS and repository contract PASS;
7. the authorization review must redo seed/global-ordinal checks while excluding only its own exact branch/PR/runs from self-reservation accounting;
8. only after that successful authorization review may the separate Issue #60 allocation transition be considered;
9. dispatch remains a later separate transition; no science may run merely because authorization review passed.

If #601 fails, do not create the authorization branch. Preserve the failed exact head/run and correct only the demonstrated control-plane defect under a fresh review identity.

---

## 12. Scientific/execution invariants for the eventual AVPS v2 run

Retain:

- 360 cases / 72 CRN groups / five states
- AOD550 0.10 and 0.30
- solar depressions 2/4/6/8 deg
- three geometries
- three replicates
- 20M photons/case
- same fresh group seed across all five states within each CRN group
- exact four-species profiles from #596
- no `aerosol_file tau`
- exact locked libRadtran/OPAC identities
- one syntax check + one solver execution per case
- attempt-1 scientific identity
- no GitHub rerun/retry/resume
- raw spectral evidence retained
- exact result universe frozen before opening
- paired CRN contrasts retained by replicate
- no epsilon substitution
- no post-hoc p-values/confidence intervals
- no universal minute conversion
- Taylor/Jerusalem scoring forbidden during this experiment

Do not silently reuse any v1 stage/case/seed/ordinal identity.

---

## 13. Hard prohibitions

Do not:

- rerun/reuse ordinal 40;
- expose the 72 candidate seed values;
- create or move the ordinal-41 authorization branch before #601 FULL PASS;
- post an ordinal-41 allocation marker before the separate authorization review passes;
- create a dispatch branch before the later allocation/dispatch protocol permits it;
- run MYSTIC/uvspec science from #601 or from the authorization review itself;
- use Taylor/Jerusalem residual direction or magnitude to select profiles, AODs, geometries, seeds, gates or thresholds;
- reintroduce `aerosol_file tau` beside `aerosol_species_file`;
- use the old `.nc` OPAC alias guesses;
- infer scientific effect size from capability/NULL runs;
- proceed to Level-B profile mapping before replacement scientific results are validly executed and opened;
- move `main` for convenience;
- use GitHub Re-run on consumed/failed one-shot scientific or capability identities;
- use abandoned branch `review/aerosol-vertical-profile-sensitivity-v2-authorization-control-v1` as an authorization parent.

---

## 14. Broader retained project state

- AOPS ordinal 37, AFPF ordinal 38 and ASIV ordinal 39 remain closed for their stated scopes and should not be duplicated.
- Taylor #508 remains evidence that independently constrained aerosol vertical structure can materially alter direct-MYSTIC twilight radiance.
- Taylor atmosphere provenance/uncertainty boundaries #535/#529/#536 remain authoritative.
- Better independent Taylor-night atmospheric acquisition remains a separate lane and must not be used to fit this profile experiment.
- Anti-fitting rules remain binding throughout.

---

## 15. Resume checklist

Before the next write/transition:

- [ ] confirm `main == 99ade7798627e67921139697ba1a004fa8a304bb`;
- [ ] confirm #596/#597/#598/#599/#600 remain Draft/open/unmerged on their exact reviewed heads;
- [ ] confirm #601 remains Draft/open/unmerged on `c10ec3be3903677c57a0c635e8e9e10658bfbb29`;
- [ ] inspect #601 dedicated run `33213321554` and contract `33213321502`;
- [ ] if #601 is not FULL PASS, do not create an authorization branch;
- [ ] if #601 passes, preserve its exact artifact ID/digest and candidate authorization SHA before any next transition;
- [ ] repeat a live Issue #60/branches/global-ordinal readback before creating the authorization identity;
- [ ] keep actual candidate seed values artifact-only;
- [ ] update this handoff after #601 PASS/FAIL, authorization review, allocation, dispatch, Gate-0, or result-opening transitions.

---

## 16. One-line live status

**AVPS v2 is cleanly reviewed through #600. Draft #601 now reviews the final solver-free authorization-control/materializer surface on exact main-child head `c10ec3be...`; its dedicated and repository-contract gates are pending at this refresh. Ordinal 41 remains unallocated/unreserved, no authorization/dispatch identity exists, and no AVPS v2 science or results have begun.**
