# STAR VISIBILITY / MYSTIC — LIVE CURRENT HANDOFF

**Live refresh: 2026-08-28 — this file name is historical, but the content below is the current computational/scientific state.**

**Bottom line:** the old handoff checkpoint saying “Stage B is next / no AVPS result exists” is obsolete. AVPS ordinal 40 was executed through a controlled recovery, its results were opened, and the exact-zero contrast was shown to be scientifically non-informative because the intended vertical-profile state never reached effective solver physics. A corrected solver-capability lane (#586) was then reviewed and activated once; that one-shot capability run failed before any MYSTIC execution because the custom `aerosol_species_file ... INSO` input could not resolve the OPAC optical-property file at runtime. Do not rerun either ordinal 40 or the failed #586 activation identity.

This handoff is intentionally updated in place so a new worker can start from the repository’s actual state rather than replaying the historical Stage-B plan.

---

## 1. Immutable baseline still in force

Repository: `search-maker/twilight-mystic-experiments`

Frozen `main` remains:

`99ade7798627e67921139697ba1a004fa8a304bb`

Do **not** move `main` merely to continue this lane.

The already-consumed AVPS authorization identity remains:

- scientific ordinal: `40`
- authorization PR: #565
- authorization head: `338ee82c8e088e929f45782b1f7ac1c3aaaaa533`
- authorization parent / frozen main: `99ade7798627e67921139697ba1a004fa8a304bb`
- authorization PR remains Draft / open / unmerged
- dispatch branch remains `dispatch/aerosol-vertical-profile-sensitivity-v1-ordinal-40`
- dispatch branch remains pinned to `338ee82c8e088e929f45782b1f7ac1c3aaaaa533`
- Issue #60 still contains exactly one ordinal-40 allocation marker and exactly one ordinal-40 consumed marker

No fresh scientific ordinal may be allocated merely to “retry” ordinal 40.

---

## 2. Historical Stage A / Stage B checkpoint is complete, not pending

The old handoff stopped after Stage-B review PR #574 and incorrectly left activation as the next step. That activation has already occurred.

Stage-B activation identity that was actually used:

- activation/control commit: `37bd2210f05380187c7805563c69737686f53825`
- activation request/status head: `79b95f0ee0fafeb07f3785da91e63598035d4ac1`
- status branch: `status/avps-v1-stage-b-science-recovery-ordinal-40`
- publisher run: `33137501439` — SUCCESS
- publisher artifact: `9672590338`
- publisher artifact digest: `sha256:071310c18d8f504addcc7fe1decadc2b9eea2b00cbc267a1778fffb89a2fb41d`

The first Stage-B science run was:

- run `33137514692`
- attempt `1`
- preflight passed
- case execution then failed/cancelled
- only same-run artifact at that point was preflight artifact `9672728847`
- preflight digest: `sha256:afe5c4c11e7885023b443a49f2babbbe25f763f2486aa4042102c0a300bf16d6`

The demonstrated defect was in the raw-evidence contract, not in ordinal allocation or the frozen science identity: the AVPS executor required diagnostic `syntax-stdout.txt` to be non-empty even when `uvspec` legitimately returned exit 0 with an empty diagnostic stdout stream. Prior repository executors require such diagnostic streams to exist but do not require them to be non-empty; the spectral scientific members remain subject to non-empty checks.

Do **not** GitHub-rerun run `33137514692`.

---

## 3. Ordinal-40 execution recovery was completed successfully

A separately reviewed executor-contract recovery (#576) was used rather than rerunning the failed Stage-B identity.

Authoritative recovery/opening facts currently recorded in master closure PR #539:

- recovery science run `33139545997`, attempt 1 — SUCCESS
- exact `360/360` case artifacts were produced
- Gate-0 metadata artifact `9676069031`
- Gate-0 digest `sha256:70dedcd16209dea74a9ed67a1dc7377c123f1a62fd18741b1e15692702011fc8`
- Gate-0 froze the exact 360 artifact universe before case contents/results were opened

Post-360 protocol was frozen separately under #579 before opening.

Phase A:

- review PR #584
- exact reviewed head `b93c284c8a24296dff9d8aedc265f7a3bdec465a`
- dedicated review run `33169583131` — SUCCESS
- repository contract run `33169583043` — SUCCESS
- one-shot Phase-A run `33170006532`, attempt 1 — SUCCESS
- all 360 ZIP digests matched Gate-0
- frozen aggregator ran exactly once
- results still remained closed at the end of Phase A
- Phase-A artifact `9685308839`
- artifact digest `sha256:68216d6a4982618d8cf9238948f0cbeb651bc9cde7ce53e688b5b1b11d204148`
- analysis-input content hash `c58907c2f838396417edcfe87d306c130b92374b649790ff25537f3ac049bdc8`

Phase B:

- review PR #585
- exact reviewed head `31c09366aafd12ef666f5c747e416df6ba4ead52`
- dedicated review run `33170557531` — SUCCESS
- repository contract run `33170557454` — SUCCESS
- one-shot result-opening run `33170855407`, attempt 1 — SUCCESS
- result artifact `9685531261`
- artifact digest `sha256:e2db9625387a4102cccc616bc2aa351b64aa1df0b14cb22978a810b352e47f04`

Phase B did **not** perform Taylor/Jerusalem residual fitting, Level-B production routing, or production activation.

---

## 4. Critical scientific postmortem: ordinal 40 is NOT a physical null result

The opened primary result contains:

- 24 analysis cells
- 3 primary channels
- 4 alternative-vs-reference contrasts
- 288 summary contrasts total

Every mean contrast was exactly `0.0`; every replicate contrast was exactly `0.0`; every summary sample SD/SE was exactly `0.0`.

**This must not be reported as evidence that aerosol vertical profile is immaterial.**

Raw matched-group audit showed:

- state-specific `case.inp` files really differed at the intended custom tau-profile path;
- the normalized `.tau` files themselves really differed substantially;
- nevertheless `mc.rad.spc`, `mc.rad.std.spc`, `mc.flx.spc`, `mc.flx.std.spc`, and solver stdout were byte-identical between the vertical-profile states;
- all 72 CRN replicate groups showed the same cross-state identity, while different replicates differed from each other, demonstrating that seeds were functioning but the profile state was not affecting solver physics.

Root-cause direction is the aerosol directive composition used by ordinal 40:

```text
aerosol_species_library OPAC
aerosol_species_file continental_average
aerosol_file tau profiles/<state>.tau
aerosol_set_tau_at_wvl 550 <AOD>
```

The intended custom `aerosol_file tau` profile did not survive into effective solver physics when combined with the fixed higher-level species-profile mixture surface.

**Authoritative ordinal-40 classification:**

`EXECUTION/EVIDENCE PIPELINE VALID; SCIENTIFIC VERTICAL-PROFILE CONTRAST NON-INFORMATIVE.`

Never reuse ordinal 40 as:

- a PASS for vertical-profile insensitivity;
- a null scientific result;
- evidence for or against profile materiality;
- a basis for Taylor/Jerusalem correction;
- an identity to rerun after silently changing directives.

---

## 5. Corrective capability lane #586 — reviewed and consumed once

Current corrective PR:

- PR #586 — `Review corrected OPAC species-profile transport capability`
- Draft / open / unmerged
- branch `review/opac-species-profile-transport-capability-v2`
- exact review head `d90d3bca966d566d328fc1d91fb44f65c58d12b4`

The review froze a **solver capability diagnostic only**, not a scientific sensitivity experiment:

- no scientific ordinal
- no Taylor/Jerusalem scoring
- no production mutation
- one synthetic OPAC species: `INSO`
- deliberately different LOW/HIGH synthetic mass-density profiles on exact AFGL-US levels
- LOW: `exp(-z/0.55 km)`
- HIGH: Gaussian centered 8 km, sigma 0.75 km
- same AOD550 `0.10`
- deterministic DISORT first
- only if deterministic transport passed, paired spherical MYSTIC at SZA 96°
- same MYSTIC seed `730194613`
- `500000` photons/profile
- no minimum physical/materiality threshold

Review gates on exact #586 head passed:

- repository-wide contract run `33172089150` — SUCCESS
- dedicated capability review run `33172089158` — SUCCESS

The one-shot activation was then performed:

- status branch `status/opac-species-profile-transport-capability-v2`
- status/request head `5362c7fc17a051baa65fe51c0d2f4f33ea98affe`
- parent/control commit `77d85fe5eb0b83b676ea27f75127513606dba684`
- one-shot execution run `33177704575`, attempt 1 — FAILURE
- evidence artifact `9688346720`
- evidence artifact digest `sha256:adb10217279e27e2ca9101ab92b7a4467805c113438f6c7dc7552d0354938b21`

Do **not** rerun run `33177704575` and do not reuse its one-shot activation identity.

---

## 6. Exact diagnosis of #586 failure from its preserved artifact

The #586 runtime/setup and all `uvspec -c` syntax checks passed.

The failure occurred in the first non-syntax deterministic DISORT LOW execution. MYSTIC was never reached.

Preserved `disort-low-stderr.txt` says:

```text
Error, found neither netcdf nor ASCII optical property files.
Check your aerosol properties and retry!
Error -1 in (function 'read_caoth_prop', file 'cloud.c', line 2854)
Error -1 in (function 'aerosol_species_to_optical_properties', file 'aerosol.c', line 2338)
Error -1 in (function 'setup_aerosol', file 'aerosol.c', line 747)
Error -1 in (function 'uvspec', file 'uvspec.c', line 114)
Error -1 during execution of uvspec
```

The failing aerosol surface was exactly:

```text
aerosol_default
aerosol_species_library OPAC
aerosol_species_file <absolute synthetic-low-inso.dat> INSO
aerosol_set_tau_at_wvl 550 0.100000
```

Therefore the current demonstrated blocker is **OPAC single-species optical-property resolution for a custom species-profile file**, not LOW/HIGH profile construction and not MYSTIC numerical equality.

Important associated runtime evidence already frozen elsewhere in the repository:

- the exact staged OPAC tree really contains the expected INSO optical-property member at `data/aerosol/OPAC/optprop/inso.mie.cdf`;
- that member SHA-256 is `fe10348cbe585315d6e1db382563fdc054204ad35846f371dc9d8abeead36407`;
- exact staged OPAC data-tree identity remains `5d8bbf8e6b91ec3d405dee36f21a94afbb6e5ec6cd67da2dd5dd541738199d80`;
- exact locked `uvspec` SHA-256 remains `2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3`.

The official libRadtran semantics and the repository’s exact archive naming must now be reconciled before another solver capability attempt. In particular, do not assume that passing `uvspec -c` proves the custom species token resolves its runtime optical-property member.

---

## 7. Current active next step

The correct next task is **not** a new 360-case scientific experiment yet.

Required sequence from this checkpoint:

1. preserve #586 as the terminal failed one-shot capability identity;
2. determine the exact libRadtran runtime mapping from a custom `aerosol_species_file <profile> <species-token>` to the staged OPAC `optprop/*.cdf` basename;
3. freeze a fresh solver-capability review identity that corrects only this demonstrated optical-property-resolution defect;
4. require a deterministic LOW/HIGH run to reach real solver output and prove nonidentity at the raw transport level;
5. only after that, require the paired MYSTIC LOW/HIGH raw `mc.rad.spc` outputs to differ on an identical wavelength grid;
6. do not infer any scientific effect size from this capability diagnostic;
7. after a capability PASS, preregister a **replacement vertical-profile sensitivity experiment under a fresh scientific ordinal and fresh immutable seed/case identity**;
8. only after that replacement scientific experiment passes its preregistered gates may vertical-profile Phase-C / Level-B mapping resume.

A historical branch named `review/opac-custom-tau-composition-capability-v1` exists, but it is old and is already behind current `main`; it must not be mistaken for a post-#586 recovery branch.

---

## 8. Hard prohibitions at this checkpoint

Do not:

- rerun ordinal 40;
- reuse ordinal 40 with patched input;
- GitHub-rerun the failed #586 capability execution;
- amend the consumed #586 activation identity and pretend it is the same reviewed run;
- claim the exact-zero ordinal-40 result is physical;
- proceed to Level-B profile mapping from ordinal 40;
- choose a vertical profile/provider/cycle from Taylor or Jerusalem residual fit;
- use target residual direction or magnitude to choose the corrected libRadtran representation;
- move `main` simply to make the recovery easier;
- treat syntax-only `uvspec -c` success as proof of non-syntax runtime optical-property resolution;
- create a production authorization from a capability diagnostic.

---

## 9. Broader retained project state

From the master closure record (#539), still relevant:

- `starsvisibility` #114, #118, #119 are merged;
- `starsvisibility` #116 remains not merge-ready pending #117 transient science;
- old Draft #48 must not be replayed wholesale;
- Operational Atmosphere State v2 design/foundation (#120/#121) are merged, but richer vertical/SSA/phase fields do not automatically affect Level-B;
- generic SSA/g sensitivity (AOPS ordinal 37), full aerosol family/phase-function sensitivity (AFPF ordinal 38), and scalar/derived aerosol scenario transport (ASIV ordinal 39 + `starsvisibility` #100) remain closed for their stated scopes and should not be duplicated;
- Taylor #508 remains evidence that independently constrained aerosol vertical structure can materially alter direct-MYSTIC twilight radiance;
- Taylor atmosphere provenance/uncertainty boundaries #535/#529/#536 remain authoritative;
- acquisition of better independent Taylor-night atmosphere data remains a separate lane and must not be used to select model profiles from residual fit.

Anti-fitting rules remain binding throughout.

---

## 10. Resume checklist for the next worker

Before any write or run:

- [ ] confirm `main == 99ade7798627e67921139697ba1a004fa8a304bb` unless a later handoff explicitly documents an intentional change;
- [ ] confirm #565 remains Draft/open/unmerged and dispatch remains pinned to `338ee82...`;
- [ ] confirm no one has created a newer post-#586 recovery branch/PR while this handoff was being written;
- [ ] read #539 and #586 current bodies/statuses;
- [ ] inspect run `33177704575` artifact `9688346720` rather than rerunning it;
- [ ] keep the next fix capability-only and ordinal-free;
- [ ] prove the exact OPAC property-file resolution path before any scientific preregistration;
- [ ] update this handoff again immediately after a new reviewed recovery identity, activation, PASS/FAIL, or fresh scientific preregistration is created.

---

## 11. Current one-line status

**Ordinal 40 completed but is scientifically non-informative because its vertical-profile contrast never reached solver physics; corrected capability #586 passed review but its one-shot deterministic run failed because custom `INSO` optical properties were not resolved at runtime; next work is a fresh, ordinal-free OPAC species-token/property-path capability correction — not another scientific run yet.**
