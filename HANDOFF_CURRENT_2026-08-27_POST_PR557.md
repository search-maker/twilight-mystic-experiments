# STAR VISIBILITY / MYSTIC — LIVE CURRENT HANDOFF

**Live refresh: 2026-08-28, after OPAC capability v3 failure and v4 review creation.**

The filename is historical. This content is the current computational/scientific checkpoint.

## 1. Immutable baseline

Repository: `search-maker/twilight-mystic-experiments`

Frozen `main`:

`99ade7798627e67921139697ba1a004fa8a304bb`

Do not move `main` merely to continue this lane.

AVPS ordinal 40 is already consumed and must never be rerun/reused:

- authorization PR #565: Draft/open/unmerged
- authorization head `338ee82c8e088e929f45782b1f7ac1c3aaaaa533`
- dispatch branch `dispatch/aerosol-vertical-profile-sensitivity-v1-ordinal-40` remains pinned to that head
- Issue #60 contains the intended allocation and consumed markers

## 2. Ordinal 40 final classification

The old checkpoint saying Stage B was next is obsolete. Stage B activation, recovery, result opening, and postmortem are complete.

Key completed chain:

- initial Stage-B control `37bd2210f05380187c7805563c69737686f53825`
- initial Stage-B request/status `79b95f0ee0fafeb07f3785da91e63598035d4ac1`
- publisher run `33137501439` SUCCESS
- first science run `33137514692` failed after preflight because diagnostic `syntax-stdout.txt` was incorrectly required to be non-empty
- separate reviewed recovery produced exact `360/360` cases in run `33139545997` SUCCESS
- Gate-0 artifact `9676069031`, digest `sha256:70dedcd16209dea74a9ed67a1dc7377c123f1a62fd18741b1e15692702011fc8`
- Phase A one-shot `33170006532` SUCCESS, artifact `9685308839`
- Phase B result opening `33170855407` SUCCESS, artifact `9685531261`

Opened ordinal-40 results were exactly zero for every state contrast, but this is **not a physical null result**. Raw audit showed state-specific profile files differed while solver outputs were byte-identical across states. The intended vertical-profile state did not reach effective solver physics.

Authoritative classification:

`EXECUTION/EVIDENCE PIPELINE VALID; SCIENTIFIC VERTICAL-PROFILE CONTRAST NON-INFORMATIVE.`

Never use ordinal 40 as evidence for profile insensitivity, Taylor/Jerusalem correction, Level-B mapping, or production routing.

## 3. Capability v2 / PR #586 — terminal failed identity

PR #586: `Review corrected OPAC species-profile transport capability`

- Draft/open/unmerged
- review head `d90d3bca966d566d328fc1d91fb44f65c58d12b4`
- repository contract `33172089150` SUCCESS
- dedicated review `33172089158` SUCCESS
- no scientific ordinal
- one synthetic OPAC species `INSO`
- LOW `exp(-z/0.55 km)`
- HIGH Gaussian center 8 km, sigma 0.75 km
- AOD550 `0.10`
- deterministic DISORT first, then paired spherical MYSTIC
- MYSTIC seed `730194613`, 500000 photons/profile

Consumed one-shot:

- status branch `status/opac-species-profile-transport-capability-v2`
- control parent `77d85fe5eb0b83b676ea27f75127513606dba684`
- request/status head `5362c7fc17a051baa65fe51c0d2f4f33ea98affe`
- run `33177704575`, attempt 1 — FAILURE
- artifact `9688346720`
- digest `sha256:adb10217279e27e2ca9101ab92b7a4467805c113438f6c7dc7552d0354938b21`

Exact failure before MYSTIC:

`found neither netcdf nor ASCII optical property files`

The custom `aerosol_species_file <profile> INSO` could not resolve the OPAC optical-property asset.

Do not rerun v2.

## 4. Capability v3 / PR #587 — terminal failed identity

The official staged OPAC archive contains:

`data/aerosol/OPAC/optprop/inso.mie.cdf`

SHA-256:

`fe10348cbe585315d6e1db382563fdc054204ad35846f371dc9d8abeead36407`

libRadtran documentation says each species used by `aerosol_species_file` needs `species_name.nc`, e.g. `INSO.nc`, in the selected `aerosol_species_library` directory.

PR #587 tested a byte-identical resolver alias, initially placing it at:

`aerosol/OPAC/optprop/INSO.nc`

Final reviewed v3 head:

`a396714a851d371a584ed4d4d2bd8e83765d05c4`

Review gates:

- dedicated review `33179715436` SUCCESS
- repository contract `33179715434` SUCCESS

Consumed v3 one-shot:

- control commit `4c5aa6d98bdb8c68d4297b8fe5d7845724ce1ea8`
- status/request head `8b1f693652018c3ef936a0c6682508d079a095b8`
- status branch `status/opac-species-profile-transport-capability-v3`
- run `33180158034`, attempt 1 — FAILURE
- artifact `9689369400`
- digest `sha256:3549c546cf2517b9d9603f4f7eafcef7ca8a8f37fb59f25fb8721ec4e63b7201`

Important diagnostic result:

- archive/runtime reconstruction passed
- source-to-alias `cmp` passed
- alias SHA/byte provenance passed
- syntax checks passed
- first real DISORT LOW call failed
- MYSTIC never ran
- `disort-low.err` was again exactly the same unresolved-property error: `found neither netcdf nor ASCII optical property files`

Therefore v3 proved that `aerosol/OPAC/optprop/INSO.nc` is still not the location used by the explicit species resolver. Do not rerun v3.

## 5. Current active corrective lane: v4 / PR #588

The documented library semantics identify `aerosol_species_library OPAC` as the selected library directory in which `INSO.nc` is expected. Therefore v4 tests only the next demonstrated path correction:

- source remains `aerosol/OPAC/optprop/inso.mie.cdf`
- source bytes/hash unchanged
- alias target is now **`aerosol/OPAC/INSO.nc`**
- alias must be byte-for-byte identical
- the failed v3 `aerosol/OPAC/optprop/INSO.nc` must not exist
- all science geometry/profile/AOD/seed/photon parameters remain unchanged

PR #588:

`Review OPAC library-root species resolver capability v4`

- Draft/open/unmerged
- branch `review/opac-species-profile-transport-capability-v4`
- exact current review head `7b2a2f7ae14a7777408ab36de65fcc4a91b4a8de`
- base `main == 99ade7798627e67921139697ba1a004fa8a304bb`
- changed files: 5 review/inactive-control files only
- no active v4 workflow exists on this branch
- no scientific ordinal allocated

Dedicated solver-free v4 review:

- run `33180739737`, attempt 1 — SUCCESS
- artifact `9689567662`
- artifact digest `sha256:e6f21ab12fe23fea72540e1a7f7a7dad29bb8c66cfca667349c9bb469506d782`

Repository-wide contract on the same exact head:

- run `33180739633`, attempt 1 — **IN PROGRESS at this handoff refresh**

### Critical activation rule

Do **not** activate v4 until run `33180739633` is completed with conclusion `success` on exact head `7b2a2f7ae14a7777408ab36de65fcc4a91b4a8de` and attempt 1.

If it passes, create a fresh one-shot status identity from frozen `main`, containing exactly:

1. active workflow copied byte-identically from `.github/recovery-templates/opac-species-profile-transport-capability-v4.yml`;
2. `review/opac-species-profile-transport-capability-v4/build_inputs.py` from the reviewed head;
3. `review/opac-species-profile-transport-capability-v4/activation_support.py` from the reviewed head.

Then create a separate request commit for stage `opac-species-profile-transport-capability-v4`, bound to PR #588, exact review head, and successful dedicated review run `33180739737`.

Only one push-triggered v4 execution is allowed. Never GitHub-rerun it.

## 6. v4 interpretation boundary

A v4 PASS requires:

- exact frozen runtime/archive identities;
- byte-identical root-level alias provenance;
- syntax checks pass;
- LOW/HIGH deterministic DISORT outputs both exist and differ;
- only then paired MYSTIC runs execute;
- LOW/HIGH `mc.rad.spc` both exist and differ.

A PASS would prove only that explicit OPAC species mass-density profiles can reach solver physics using this frozen representation. It does **not** establish a scientifically material effect size.

Only after a capability PASS may a replacement vertical-profile sensitivity experiment be preregistered under a **fresh scientific ordinal and fresh immutable case/seed identity**.

## 7. Hard prohibitions

Do not:

- rerun/reuse ordinal 40;
- rerun v2 run `33177704575`;
- rerun v3 run `33180158034`;
- amend a consumed one-shot identity and pretend it is the reviewed run;
- activate v4 before both exact-head gates are green;
- treat syntax-only success as runtime property resolution;
- claim ordinal-40 zero contrast is physical;
- select profiles/provider/cycle from Taylor/Jerusalem residual direction or magnitude;
- proceed to Level-B profile mapping before a fresh scientific experiment;
- move `main` merely for convenience;
- create production authorization from a capability diagnostic.

## 8. Broader retained project state

Still authoritative from the master closure track:

- generic SSA/g sensitivity (AOPS ordinal 37), full aerosol family/phase-function sensitivity (AFPF ordinal 38), and scalar/derived aerosol scenario transport (ASIV ordinal 39) are closed for their stated scopes and should not be duplicated;
- Taylor #508 remains evidence that independently constrained aerosol vertical structure can materially change direct-MYSTIC twilight radiance;
- Taylor atmosphere provenance/uncertainty boundaries #535/#529/#536 remain authoritative;
- acquiring better independent Taylor-night atmosphere data is a separate lane and must not be used to fit residuals.

Anti-fitting rules remain binding.

## 9. Resume checklist

Before any next write/run:

- confirm `main == 99ade7798627e67921139697ba1a004fa8a304bb`;
- confirm PR #588 remains Draft/open/unmerged on head `7b2a2f7ae14a7777408ab36de65fcc4a91b4a8de`;
- confirm dedicated review `33180739737` remains attempt-1 SUCCESS;
- fetch final state of repository contract `33180739633`;
- search for any newer parallel v4/v5 work before creating an activation or successor;
- if contract is not SUCCESS, diagnose/fix under a new exact review head and re-review; do not activate;
- if v4 is activated, preserve its evidence artifact regardless of PASS/FAIL and never rerun;
- update this handoff immediately after contract completion, v4 activation, v4 PASS/FAIL, or creation of a successor capability/scientific preregistration.

## 10. One-line live status

**Ordinal 40 is scientifically non-informative; v2 and v3 are terminal failed capability identities; PR #588 v4 now tests the libRadtran-documented OPAC library-root alias `aerosol/OPAC/INSO.nc`, its dedicated solver-free review has passed, and activation is blocked only on the still-running repository-wide contract `33180739633`.**
