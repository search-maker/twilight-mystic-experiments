# STAR VISIBILITY / MYSTIC — LIVE CURRENT HANDOFF

**Live refresh: 2026-08-28 — replacement AVPS v2 is reviewed through authorization-control/materializer PR #603 FULL PASS. The exact proposed ordinal-41 authorization document exists only in the #603 Actions artifact; scientific ordinal 41 is still NOT allocated or reserved, no authorization/dispatch branch exists, no Issue #60 ordinal-41 marker exists, no scientific solver has run, and no result has been opened.**

The filename is historical. This file is the live computational/scientific checkpoint. Update it only at safe checkpoints. **Never move this handoff branch while a snapshot-fenced repository-global audit is in progress.**

---

## 1. Immutable baseline

Repository: `search-maker/twilight-mystic-experiments`

Frozen main:

`99ade7798627e67921139697ba1a004fa8a304bb`

Frozen main tree:

`2d4bb1df136bff2da93f191e5518b94b3d7fecfc`

Do not move `main` merely to continue this lane.

---

## 2. Ordinal 40 is consumed and retired

AVPS v1 ordinal 40 reached exact 360/360 execution evidence, but the intended state-specific vertical-profile variation did not reach effective solver physics: state-specific profile inputs differed while solver spectra were byte-identical across states.

Authoritative classification:

`EXECUTION/EVIDENCE PIPELINE VALID; SCIENTIFIC VERTICAL-PROFILE CONTRAST NON-INFORMATIVE.`

Key retained evidence:

- recovery science run `33139545997` — SUCCESS, exact 360/360 cases
- Gate-0 artifact `9676069031`, digest `sha256:70dedcd16209dea74a9ed67a1dc7377c123f1a62fd18741b1e15692702011fc8`
- Phase A `33170006532` — SUCCESS
- Phase B opening `33170855407` — SUCCESS
- Issue #60 consumed marker `ORDINAL40_AVPS_V1_DISPATCH_CONSUMED`

Never rerun/reuse ordinal 40, its seeds, case IDs, authorization identity or dispatch identity. Never cite its exact-zero contrast as physical vertical-profile insensitivity.

---

## 3. Corrected OPAC transport and renderer are established

The diagnostic chain #586–#589 proved that the locked libRadtran binary requests no-extension OPAC aliases such as `data/aerosol/OPAC/optprop/INSO`.

Key successful gates:

- #590 single-species capability — head `f0675ec48c637509cd7a5bb9c2a2746507e5bea8`, dedicated `33186027699`, contract `33186027637`, one-shot `33186446347`, artifact `9691923455`
- #592 four-species transport — head `18667797a1dd699b6431a6940bac42974c415733`, dedicated `33188868496`, contract `33188868323`, one-shot `33189268483`, artifact `9693056690`, four-alias data tree `5e1814dd36cf861fd85477a97607299248f8272268df7bf428d31bbb6aa4354a`
- #593 exact 550-nm/RH source audit — run `33190220896`, artifact `9693440701`
- #594 AFGL-US RH NULL audit — run `33190680002`, artifact `9693619172`
- #595 NULL aerosol-tau calibration — run `33191517143`, contract `33191517521`, artifact `9693948772`
- #596 four-species AVPS renderer — head `8adfd4fafa4c039394d12e6f6aff1795b750f4d2`, dedicated `33193123594`, contract `33193123597`, artifact `9694613680`, digest `sha256:5e6942d879326ffc2dc8805d7649086cae32ad2e16aeec19a62cd3b0a89e3e27`, renderer blob `99f61e1daa03cecef055a3773544574738d65082`

Validated scientific representation:

```text
aerosol_default
aerosol_species_library OPAC
aerosol_species_file profiles/<state>.four-species.dat INSO WASO SOOT SUSO
aerosol_set_tau_at_wvl 550 <AOD550>
```

Forbidden old representation:

```text
aerosol_species_file continental_average
aerosol_file tau <state>
```

Exact #596 four-species profile SHA-256 values:

- continental average `ceed598f7681951cd0e6208b267beb5b41a52ab10311f37ce76f925700caff3d`
- maritime clean `487b67bd7dbe89d12d032fdf2b33cab545e16a2e0697170648317f1a76362a67`
- desert `2b4d2e03c6ae3143d9bb05d2da49f57f75172dc1f24d34f7d4a4939bf9952fef`
- arctic `98f2fa5428c830764252fd0a2662b0f5c957fc027ffcb7bdc0a5e500dfd7d3d6`
- antarctic `ee063c6dca68cf9a31d8bb9d993f1fed5cb34c8bb056ac180c97171b5d6b4f19`

---

## 4. Replacement AVPS v2 frozen scientific design — #597 PASS

Stage: `aerosol-vertical-profile-sensitivity-v2`

- head `2bba54c6e78ed99d169887eef51d0c88d812b6f1`
- dedicated `33193778176` SUCCESS
- contract `33193778174` SUCCESS
- artifact `9694863701`
- digest `sha256:7de79aa4d8d9b51ad8ca4b1bdaceedae7ee5df17b3dd79c43c21cdaf9ae9a171`
- skeleton canonical SHA `a8d2d8f59aec01d82d8d98672152d00c11261660b0a69a59e2716c2edabd2b02`

Frozen design:

- five independent OPAC Tables 3/5 vertical templates
- fixed continental-average optical family
- AOD550 0.10 / 0.30
- solar depressions 2 / 4 / 6 / 8 deg
- three geometries
- three CRN replicates
- 20,000,000 photons/case
- 72 CRN groups / 360 cases
- fresh `avps-v2-*` case namespace and fresh group-seed namespace
- exact #596 four-species profiles
- no Taylor/Jerusalem residual-driven selection

The intended scientific question/screen are unchanged from v1; only the broken transport representation was corrected.

---

## 5. #598 candidate-seed freshness PASS

- head `64e7d68bd876a99aa5af49d97bcb53718238b39b`
- dedicated `33194319669` SUCCESS
- contract `33194319698` SUCCESS
- artifact `9695260362`
- digest `sha256:fb4613d654121098c9d247d6ed8b0f0788b26a179b5ff103dc01ed7d50c9f0db`
- 72 candidate group seeds
- candidate-set canonical SHA `02f624d582e9b2caba6b920d65a5e8a8bc8fc1a2693623bc2f73abf5d3f706d2`
- candidate-row canonical SHA `41f70d6a0381db6b569d3f4e17d74bb38b05cf212c2f2e432455a502f73dc670`
- repository-global collision count zero

**Never expose the actual 72 seed values.** They remain artifact/in-memory only and must not appear in Git, PR/Issue prose, this handoff, chat, or user-facing documentation.

---

## 6. #599 preauthorization/global ordinal surface PASS

- head `a4e4700babddf0924135f5cc6ec6bfd21d8c9ec2`
- dedicated `33203372878` SUCCESS attempt 1
- contract `33203372798` SUCCESS attempt 1
- artifact `9699064164`
- digest `sha256:b1125375bae24638375853d3724c1c96ba1572dc02e1619eff37d9fdca70b92e`
- status `PASS_V2_PREAUTHORIZATION_SURFACE_CLEAN_NOT_ALLOCATED`

At #599: latest consumed = 40, authoritative max = 40, next available candidate = 41, and no allocation/authorization/dispatch/seed application existed.

---

## 7. #600 disabled v2 control/package PASS

- head `8a5d73974b02ba21fc2f010bbd911538e6981de2`
- dedicated `33205661865` SUCCESS attempt 1
- repository contract `33205661834` SUCCESS attempt 1
- artifact `9699546728`
- digest `sha256:9badcdc03bbeb181f731352afc48b75c67c14dc95a986fcf32163677d4ea972d`
- status `PASS_DISABLED_V2_CONTROL_PACKAGE_REVIEW_NO_ORDINAL_NO_AUTHORIZATION_NO_SOLVER`

Important reviewed blobs:

- `control_package.py` `62bacf15d145051fcc5259a24c310eac761d0e74`
- `adapter.py` `c245eac2fe5b5d026e46ec4253bc377c5fde97ec`
- `renderer.py` `99f61e1daa03cecef055a3773544574738d65082`
- `rh_audit_dependency.py` `095ff86f12a79dc312a51f734b0a03bd318f2337`
- `runtime_stage.py` `0d3ac10f3ef7d22f0205854233a6c37cbba03f7c`

---

## 8. Preserved failed control-review identities

### #601 — metadata-fence failure

- head `c10ec3be3903677c57a0c635e8e9e10658bfbb29`
- dedicated `33213321554` FAILURE attempt 1
- contract `33213321502` SUCCESS

The two-pass global scan correctly refused because this handoff branch moved during the fenced window. No materialization or boundary crossing occurred. Do not rerun.

### #602 — root-binding failure after clean global audits

- head `9f4e3a6d99aa4b8b039de631bc5d3dbfed3a7161`
- dedicated `33214102573` FAILURE attempt 1
- contract `33214104529` SUCCESS

#602 proved the unchanged two-pass seed scan and fresh ordinal/live-surface audit PASS under write-quiet conditions, then failed locally because `build_authorization.py` used `HERE.parents[2]` instead of repository root `HERE.parents[1]`. No artifact/authorization/allocation/dispatch/science/result boundary was crossed. Do not rerun.

Non-authoritative abandoned branch `review/aerosol-vertical-profile-sensitivity-v2-authorization-control-v1` / commit `7d5c945deb3841af790e7c9ef7a46bebe45ba896` must never be used as an authorization parent.

---

## 9. #603 — authorization-control/materializer v4 FULL PASS

Draft PR #603:

`Recover AVPS v2 authorization materializer repo-root binding`

- branch `review/aerosol-vertical-profile-sensitivity-v2-authorization-control-v4`
- exact head `b3d562222a38fc9d1ff5d218886afdda72c37fa2`
- parent `99ade7798627e67921139697ba1a004fa8a304bb`
- tree `abe2734f001a38c7e114e2da9854c7a5e2e7e0a3`
- dedicated review `33217110804` — SUCCESS attempt 1
- repository contract `33217110849` — SUCCESS attempt 1
- artifact `9703976307`
- artifact digest `sha256:3c52f6b912e0b9d8743722048af2036626a1c7b1eff1e5f4e39aa106cd8f2dbb`
- candidate `authorization.json` file SHA-256 `7d4c8197785ce80d589bb67aac353c90266c91f1ed296ed22a7dfbbdc317f978`
- candidate document internal content hash `0a0e50a78ba8742088e3f13314513dd359ba479f321ed389f8af37affdbda0fa`
- control-review receipt content SHA `323dba2acc431c3126330b1d3a0527e5d6d5d0c736deab1e230085c72f6ece76`
- live-surface file SHA-256 `72f8648d5f72c203bdeae31a53d6b1b9070be1baac1ac1d5cc56c17f92a2bee6`

All dedicated steps passed, including:

1. exact main-child Draft identity;
2. exact #599/#600 PR/run/contract/artifact bindings;
3. exact reviewed blob bindings;
4. corrected repo-root import check (`ROOT == repository root`, all bound #600 source paths exist);
5. exact-head tracked-tree candidate-seed scan;
6. unchanged two-pass repository-global candidate-seed scan;
7. fresh global ordinal/live-surface audit;
8. authorization materialization;
9. 360-case / 72-group in-memory validation;
10. proof that no literal candidate seed value appears in `authorization.json`;
11. receipt freeze and artifact upload;
12. final global ordinal readback after materialization.

Frozen live surface in the artifact:

- latest consumed scientific ordinal = 40
- global authoritative max = 40
- next available candidate = 41
- repository-global candidate-seed collision count = 0
- double enumeration stable = true
- authorization branch exists = false
- dispatch branch exists = false
- ordinal-41 Issue #60 marker exists = false
- scientific ordinal allocated = false

A fresh post-#603 readback immediately before this handoff update also found no ordinal-41 authorization branch, no ordinal-41 dispatch branch, and no `ORDINAL41_` marker in Issue #60.

### What the proposed document authorizes — and does NOT do

The artifact-only proposed document binds ordinal 41 and permits a later in-memory seed application/scientific execution **only after** the separate authorization identity itself passes review. It still has:

- `dispatchAuthorized=false`
- `automaticDispatch=false`
- `consumed=false`
- `resultOpeningAuthorized=false`
- `productionAuthorized=false`
- `taylorOrJerusalemFitAuthorized=false`
- `githubRerunAllowed=false`
- `retryAllowed=false`
- `resumeAllowed=false`

The existence of this artifact is **not allocation/reservation** and is **not dispatch**.

---

## 10. Exact boundary now

At this checkpoint:

- ordinal 40 = consumed/retired
- ordinal 41 = **not allocated and not reserved**
- no `authorization/aerosol-vertical-profile-sensitivity-v2-ordinal-41` branch exists
- no `dispatch/aerosol-vertical-profile-sensitivity-v2-ordinal-41` branch exists
- no `ORDINAL41_...` marker exists in Issue #60
- candidate seed values remain artifact/in-memory only
- no AVPS v2 scientific solver run exists
- no AVPS v2 result has been opened
- no Level-B/production mapping from AVPS v2 exists

---

## 11. Immediate next safe sequence

1. Recheck the live branch/Issue #60 ordinal surface after this handoff write.
2. Create `authorization/aerosol-vertical-profile-sensitivity-v2-ordinal-41` as **one direct child of exact #603 head `b3d562222a38fc9d1ff5d218886afdda72c37fa2`**.
3. The child must change exactly one file:
   `review/aerosol-vertical-profile-sensitivity-v2-authorization-control-v4/authorization.json`.
4. That file must be byte-identical to #603 artifact `9703976307`, SHA-256 `7d4c8197785ce80d589bb67aac353c90266c91f1ed296ed22a7dfbbdc317f978`.
5. Open a Draft authorization PR targeting `review/aerosol-vertical-profile-sensitivity-v2-authorization-control-v4`, not `main`.
6. Once its repository-global seed scan begins, keep GitHub write-quiet until the authorization-review final readback terminates.
7. Require attempt-1 authorization-review PASS and repository-contract PASS on the same exact authorization head.
8. The authorization review may exclude only its own exact authorization branch/PR/runs from self-reservation accounting. Every independent ordinal-41 observation is a refusal.
9. **Do not post an Issue #60 ordinal-41 allocation marker merely because the branch/PR exists.** Allocation remains a later separate transition after authorization review PASS.
10. Dispatch remains still later. No solver execution may start merely because authorization review passed.

If authorization review fails, preserve that exact attempt-1 identity and correct only the demonstrated defect under a fresh identity. Do not use GitHub Re-run.

---

## 12. Eventual AVPS v2 scientific/execution invariants

Retain:

- 360 cases / 72 CRN groups / five states
- AOD550 0.10 / 0.30
- solar depressions 2 / 4 / 6 / 8 deg
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

---

## 13. Hard prohibitions

Do not:

- rerun/reuse ordinal 40;
- expose actual candidate seed values;
- rerun #601 `33213321554` or #602 `33214102573`;
- change #603 exact reviewed head;
- create dispatch before the later allocation/dispatch protocol permits it;
- post an ordinal-41 allocation marker before authorization review passes;
- mutate repository metadata during a snapshot-fenced global scan;
- run MYSTIC/uvspec science from control or authorization review;
- use Taylor/Jerusalem residual direction or magnitude to select profiles, AODs, geometries, seeds, gates or thresholds;
- reintroduce `aerosol_file tau` beside `aerosol_species_file`;
- infer scientific effect size from capability/NULL runs;
- proceed to Level-B profile mapping before replacement scientific results are validly executed and opened;
- move `main` for convenience.

---

## 14. Resume checklist

- [ ] confirm `main == 99ade7798627e67921139697ba1a004fa8a304bb`;
- [ ] preserve #601/#602 failed attempt-1 identities;
- [ ] confirm #603 remains Draft/open/unmerged at `b3d562222a38fc9d1ff5d218886afdda72c37fa2`;
- [ ] confirm #603 dedicated `33217110804` and contract `33217110849` remain SUCCESS attempt 1;
- [ ] confirm artifact `9703976307`, digest `sha256:3c52f6b912e0b9d8743722048af2036626a1c7b1eff1e5f4e39aa106cd8f2dbb`;
- [ ] confirm candidate authorization SHA-256 `7d4c8197785ce80d589bb67aac353c90266c91f1ed296ed22a7dfbbdc317f978`;
- [ ] live-recheck branches + Issue #60 before creating authorization identity;
- [ ] create only the one-file direct child authorization identity;
- [ ] keep GitHub write-quiet during its fenced global scan;
- [ ] keep candidate seed values artifact-only;
- [ ] update this handoff after authorization PASS/FAIL and after every later allocation/dispatch/Gate-0/result-opening transition.

---

## 15. One-line live status

**AVPS v2 authorization-control/materializer #603 is FULL PASS on exact head `b3d56222…`; artifact `9703976307` contains the exact reviewed proposed authorization (`sha256:7d4c8197…`). Ordinal 41 is still unallocated/unreserved and no authorization/dispatch identity or Issue #60 marker exists. Next safe transition: one-file direct-child Draft authorization PR targeting the exact #603 control branch, followed by a fresh write-quiet authorization review.**