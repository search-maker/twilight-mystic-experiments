# STAR VISIBILITY / MYSTIC — LIVE CURRENT HANDOFF

**Live refresh: 2026-08-28 — replacement AVPS v2 is reviewed through #600. PR #601 is preserved as a metadata-fence failure. Fresh recovery PR #602 proved that the unchanged repository-global seed/ordinal audits pass under a write-quiet repository, then failed locally at authorization materialization because `build_authorization.py` computed the repository root with `HERE.parents[2]` instead of `HERE.parents[1]`. No authorization artifact/branch, ordinal allocation, dispatch, solver execution, or result opening occurred. Scientific ordinal 41 remains NOT allocated or reserved.**

The filename is historical. This file is the live computational/scientific checkpoint. Update it at safe checkpoints, but **never move this handoff branch while a repository-global snapshot/fence audit is in progress**.

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

AVPS v1 ordinal 40 reached exact 360/360 execution evidence, but its intended state-specific vertical-profile variation did not reach effective solver physics. State-specific profile inputs differed while solver spectra were byte-identical across states.

Authoritative classification:

`EXECUTION/EVIDENCE PIPELINE VALID; SCIENTIFIC VERTICAL-PROFILE CONTRAST NON-INFORMATIVE.`

Retained evidence:

- recovery science run `33139545997` — SUCCESS, exact 360/360 cases
- Gate-0 artifact `9676069031`, digest `sha256:70dedcd16209dea74a9ed67a1dc7377c123f1a62fd18741b1e15692702011fc8`
- Phase A `33170006532` — SUCCESS
- Phase B opening `33170855407` — SUCCESS
- Issue #60 consumed marker `ORDINAL40_AVPS_V1_DISPATCH_CONSUMED`

Never rerun or reuse ordinal 40, its seeds, case IDs, authorization identity, or dispatch identity. Never cite its exact-zero contrast as physical vertical-profile insensitivity.

---

## 3. Corrected OPAC species-profile transport is established

Historical capability chain:

- #586 / `33177704575` — FAILURE before MYSTIC
- #587 / `33180158034` — FAILURE
- #588 / `33184511183` — FAILURE; artifact `9691137631`
- #589 syscall trace `33185460954` — SUCCESS; artifact `9691518729`

The trace proved that the locked libRadtran binary requests no-extension OPAC optical-property aliases such as `data/aerosol/OPAC/optprop/INSO`.

### #590 — single-species capability PASS

- head `f0675ec48c637509cd7a5bb9c2a2746507e5bea8`
- dedicated `33186027699` SUCCESS
- contract `33186027637` SUCCESS
- one-shot `33186446347` SUCCESS
- artifact `9691923455`

### #591 — exact continental-average source audit PASS

`continental_average.dat` columns are `z(km) INSO WASO SOOT SUSO`.

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
- status `PASS_FOUR_CONTINENTAL_SPECIES_REACH_DISORT_AND_MYSTIC`
- four-alias data tree `5e1814dd36cf861fd85477a97607299248f8272268df7bf428d31bbb6aa4354a`

The equal synthetic weights in #592 were transport witnesses only, not a scientific composition rule.

---

## 4. RH / NULL calibration and corrected renderer

- #593 exact 550-nm/RH source audit PASS — head `223b592208d3dda24217dabcfca9fd27333e4b84`, run `33190220896`, artifact `9693440701`
- #594 AFGL-US RH NULL audit PASS — head `e7f968ee70dbecaf5f315bc8b03627ce1628edef`, run `33190680002`, artifact `9693619172`
- #595 NULL aerosol-tau calibration PASS — head `3fcb6328a18747b5a17d5ae75248c04c288e18f9`, run `33191517143`, contract `33191517521`, artifact `9693948772`

Humidity nodes frozen from OPAC:

- INSO/SOOT `[0]`
- WASO/SUSO `[0,50,70,80,90,95,98,99] %`

### #596 — four-species AVPS renderer FULL PASS

- head `8adfd4fafa4c039394d12e6f6aff1795b750f4d2`
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

## 5. #597 — replacement AVPS v2 preregistration FULL PASS

Stage: `aerosol-vertical-profile-sensitivity-v2`

- head `2bba54c6e78ed99d169887eef51d0c88d812b6f1`
- dedicated `33193778176` SUCCESS
- contract `33193778174` SUCCESS
- artifact `9694863701`
- digest `sha256:7de79aa4d8d9b51ad8ca4b1bdaceedae7ee5df17b3dd79c43c21cdaf9ae9a171`
- skeleton canonical SHA `a8d2d8f59aec01d82d8d98672152d00c11261660b0a69a59e2716c2edabd2b02`

Frozen design:

- five independently selected OPAC Tables 3/5 vertical templates
- fixed continental-average optical family
- AOD550 0.10 / 0.30
- solar depressions 2 / 4 / 6 / 8 deg
- three geometries
- three CRN replicates
- 20,000,000 photons/case
- 72 CRN groups / 360 cases
- fresh `avps-v2-*` case namespace
- fresh v2 group-seed namespace
- exact #596 four-species profiles
- no Taylor/Jerusalem residual-driven selection

The scientific question/screen are unchanged from the intended v1 experiment; only the broken transport representation was corrected.

---

## 6. #598 — candidate-seed freshness FULL PASS

- head `64e7d68bd876a99aa5af49d97bcb53718238b39b`
- dedicated `33194319669` SUCCESS
- contract `33194319698` SUCCESS
- artifact `9695260362`
- digest `sha256:fb4613d654121098c9d247d6ed8b0f0788b26a179b5ff103dc01ed7d50c9f0db`
- candidate count 72
- candidate-set canonical SHA `02f624d582e9b2caba6b920d65a5e8a8bc8fc1a2693623bc2f73abf5d3f706d2`
- candidate-row canonical SHA `41f70d6a0381db6b569d3f4e17d74bb38b05cf212c2f2e432455a502f73dc670`
- repository-global collision count zero

**Never expose the 72 actual seed values.** They remain artifact/in-memory only and must not appear in Git, PR/Issue prose, this handoff, chat, or user-facing documentation.

---

## 7. #599 — preauthorization/global ordinal surface FULL PASS

- head `a4e4700babddf0924135f5cc6ec6bfd21d8c9ec2`
- dedicated `33203372878` SUCCESS attempt 1
- contract `33203372798` SUCCESS attempt 1
- artifact `9699064164`
- digest `sha256:b1125375bae24638375853d3724c1c96ba1572dc02e1619eff37d9fdca70b92e`
- status `PASS_V2_PREAUTHORIZATION_SURFACE_CLEAN_NOT_ALLOCATED`

Final #599 observation:

- latest exact consumed ordinal = 40
- maximum authoritative ordinal = 40
- next available candidate = 41
- ordinal allocated = false
- authorization created = false
- dispatch created = false
- candidate seeds applied = false

---

## 8. #600 — disabled v2 control/package FULL PASS

- branch `review/aerosol-vertical-profile-sensitivity-v2-control-v1`
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

## 9. #601 — terminal metadata-fence failure, no boundary crossed

- branch `review/aerosol-vertical-profile-sensitivity-v2-authorization-control-v2`
- head `c10ec3be3903677c57a0c635e8e9e10658bfbb29`
- parent main `99ade7798627e67921139697ba1a004fa8a304bb`
- tree `7f7713a4e2c519fe14e23fb9afcf19812b95a631`
- dedicated `33213321554` attempt 1 — FAILURE
- repository contract `33213321502` attempt 1 — SUCCESS

It passed identity, predecessor, exact-byte, artifact-digest and tracked-tree seed checks, then correctly failed at the two-pass repository-global candidate-seed scan because repository metadata changed between the two complete enumerations.

Demonstrated cause: this handoff branch moved via commit `088c0915c2c38ea06d0bda400e01241c563c6839` at `2026-08-28T21:37:46Z`, inside the scan window (~`21:37:08Z`–`21:42:46Z`).

Therefore #601 proves a **review-time repository metadata mutation**, not a seed collision and not a scanner defect. No live-surface report, materialization, artifact, authorization branch, ordinal marker, seed application, solver or result was produced. Do not rerun `33213321554`.

---

## 10. #602 — metadata-stability recovery passed; materializer path bug remains

Draft PR #602:

`Recover AVPS v2 authorization control after metadata-fence failure`

- branch `review/aerosol-vertical-profile-sensitivity-v2-authorization-control-v3`
- head `9f4e3a6d99aa4b8b039de631bc5d3dbfed3a7161`
- parent main `99ade7798627e67921139697ba1a004fa8a304bb`
- tree `d644d36faeeed8dbd8c21618a6100cfb3122d586`
- dedicated run `33214102573`, attempt 1 — **FAILURE**
- repository contract `33214104529`, attempt 1 — **SUCCESS**

Important result: after opening #602 the repository was kept write-quiet while the fenced audit ran.

Dedicated steps 1–8 passed, then:

- step 9 `Fresh unchanged two-pass repository-global candidate-seed recheck` — **SUCCESS**
- step 10 `Build fresh ordinal and seed live surface` — **SUCCESS**
- step 11 `Materialize and validate authorization candidate in artifact only` — **FAILURE**

This proves that the unchanged two-pass scanner succeeds when the repository remains stable. The #601 failure was therefore correctly diagnosed as metadata movement, and the scanner must not be weakened.

### Exact #602 local defect

`review/aerosol-vertical-profile-sensitivity-v2-authorization-control-v3/build_authorization.py` contains:

```python
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CONTROL_DIR = ROOT / "review/aerosol-vertical-profile-sensitivity-v2-control-v1"
```

For a file located at `<repo>/review/<authorization-control-dir>/build_authorization.py`, the repository root is `HERE.parents[1]`, not `HERE.parents[2]`.

Required minimal correction:

```python
ROOT = HERE.parents[1]
```

The #600 disabled package itself does contain `candidateSeedValuesIncluded: false`; there is no evidence of a seed leak. The wrong root caused bound-source loading to look one directory above the repository and therefore made the materializer fail before a candidate authorization could be completed.

### #602 boundary outcome

Because materialization failed:

- no authorization-control artifact was uploaded
- no proposed `authorization.json` is authoritative
- no authorization branch exists
- no Issue #60 ordinal-41 marker exists
- no candidate seed was applied to tracked case state
- no libRadtran/MYSTIC scientific execution occurred
- no result was opened

Do not rerun `33214102573`. Preserve #602 as terminal attempt-1 evidence that the global snapshot/ordinal surfaces were clean but the materializer had a local path-binding defect.

---

## 11. Non-authoritative abandoned preliminary branch

Do not use `review/aerosol-vertical-profile-sensitivity-v2-authorization-control-v1`.

Its only new commit is `7d5c945deb3841af790e7c9ef7a46bebe45ba896`. It was mistakenly started from #600 head instead of frozen main and contains only a protocol draft. No PR, ordinal, authorization, dispatch, seed application or solver execution was created.

---

## 12. Exact boundary at this checkpoint

- ordinal 40 = consumed/retired
- ordinal 41 = **not allocated and not reserved**
- no `authorization/aerosol-vertical-profile-sensitivity-v2-ordinal-41` branch exists
- no `dispatch/aerosol-vertical-profile-sensitivity-v2-ordinal-41` branch exists
- no `ORDINAL41_...` allocation/consumption marker exists in Issue #60
- candidate seed values remain artifact/in-memory only
- no AVPS v2 scientific solver run exists
- no AVPS v2 result has been opened
- no Level-B/production mapping from AVPS v2 exists

Issue #60 checkpoint comment `5457950462` records #599/#600 completion and the non-allocation boundary before #601.

---

## 13. Immediate next safe sequence

1. Preserve #601 and #602 exact failed heads/runs; do not rerun them.
2. Create a **fresh authorization-control recovery review identity directly from frozen main**.
3. Keep the #599/#600 reviewed bytes, seed/ordinal scanners and all scientific/control semantics unchanged.
4. Make the single demonstrated materializer correction `ROOT = HERE.parents[1]`, plus only the fresh branch/path/blob identity updates required for the new review.
5. Open the fresh Draft PR.
6. Once its repository-global snapshot/fence scan begins, keep GitHub write-quiet:
   - do not update this handoff;
   - do not post Issue/PR comments;
   - do not create/move branches;
   - do not otherwise mutate repository metadata until the scan terminates.
7. Require fresh attempt-1 dedicated review PASS and repository-contract PASS on the same exact head.
8. Only after full PASS, preserve its artifact ID/digest and proposed authorization SHA in this handoff and re-audit the live ordinal surface.
9. Only then create a separate one-file Draft ordinal-41 authorization identity as a direct child of the exact reviewed recovery-control head.
10. Authorization review, Issue #60 allocation, dispatch, science and result opening remain separate later transitions.

If the fresh recovery fails at another local control/materializer defect, preserve that exact identity and correct only the demonstrated defect under another fresh attempt-1 identity. Do not weaken the global scanner.

---

## 14. Eventual AVPS v2 scientific/execution invariants

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

## 15. Hard prohibitions

Do not:

- rerun/reuse ordinal 40;
- expose actual candidate seed values;
- GitHub-rerun #601 `33213321554` or #602 `33214102573`;
- create ordinal-41 authorization/dispatch identity before a fresh recovery-control review fully passes;
- update this handoff or otherwise mutate repository metadata during a repository-global snapshot/fence scan;
- post an ordinal-41 allocation marker before authorization review passes;
- run MYSTIC/uvspec science from control or authorization review;
- use Taylor/Jerusalem residual direction or magnitude to select profiles, AODs, geometries, seeds, gates or thresholds;
- reintroduce `aerosol_file tau` beside `aerosol_species_file`;
- infer scientific effect size from capability/NULL runs;
- proceed to Level-B profile mapping before replacement scientific results are validly executed and opened;
- move `main` for convenience.

---

## 16. Resume checklist

Before the next transition:

- [ ] confirm `main == 99ade7798627e67921139697ba1a004fa8a304bb`;
- [ ] confirm #596/#597/#598/#599/#600 remain on their exact reviewed heads;
- [ ] preserve #601 head `c10ec3be3903677c57a0c635e8e9e10658bfbb29` and #602 head `9f4e3a6d99aa4b8b039de631bc5d3dbfed3a7161` as failed evidence;
- [ ] do not rerun either failed dedicated review;
- [ ] create the fresh control recovery from frozen main with only the `parents[2] -> parents[1]` fix and fresh identity bindings;
- [ ] once its CI begins the global scan, make no GitHub writes until the scan terminates;
- [ ] if recovery passes, preserve artifact ID/digest and candidate authorization SHA before authorization identity creation;
- [ ] repeat a live Issue #60/branches/global-ordinal readback before allocation-bearing steps;
- [ ] keep candidate seed values artifact-only;
- [ ] update this handoff after recovery PASS/FAIL and after every later authorization/allocation/dispatch/Gate-0/result-opening transition.

---

## 17. One-line live status

**AVPS v2 is reviewed through #600. #601 is terminal metadata-fence failure evidence. #602 proved the unchanged global seed/ordinal audits pass under write-quiet conditions, then failed locally because the materializer used the wrong repo-root parent index. Ordinal 41 remains unallocated/unreserved. Next: fresh main-child control recovery with the single `HERE.parents[1]` path fix, unchanged scanners, and write-quiet GitHub during the fenced audit.**