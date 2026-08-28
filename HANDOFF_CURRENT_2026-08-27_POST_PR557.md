# STAR VISIBILITY / MYSTIC — LIVE CURRENT HANDOFF

**Live refresh: 2026-08-28, after terminal OPAC capability v4 failure.**

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
- read-only ledger audit on 2026-08-28 still showed ordinal 40 as the latest consumed ordinal
- no `ordinal-41` branch existed at that audit

Do **not** allocate ordinal 41 until an ordinal-free corrected profile-transport capability actually passes.

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

PR #587 tested a byte-identical resolver alias at:

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

Diagnostic result:

- archive/runtime reconstruction passed
- source-to-alias `cmp` passed
- alias SHA/byte provenance passed
- syntax checks passed
- first real DISORT LOW call failed
- MYSTIC never ran
- `disort-low.err` again said `found neither netcdf nor ASCII optical property files`

Therefore v3 proved that `aerosol/OPAC/optprop/INSO.nc` is not sufficient for the explicit species resolver in the locked binary. Do not rerun v3.

## 5. Capability v4 / PR #588 — terminal failed identity

PR #588:

`Review OPAC library-root species resolver capability v4`

- Draft/open/unmerged
- branch `review/opac-species-profile-transport-capability-v4`
- exact reviewed head `7b2a2f7ae14a7777408ab36de65fcc4a91b4a8de`
- base `main == 99ade7798627e67921139697ba1a004fa8a304bb`
- no scientific ordinal

Review gates on the exact head:

- dedicated review `33180739737`, attempt 1 — SUCCESS
- review artifact `9689567662`
- review artifact digest `sha256:e6f21ab12fe23fea72540e1a7f7a7dad29bb8c66cfca667349c9bb469506d782`
- repository-wide contract `33180739633`, attempt 1 — SUCCESS

Reviewed activation blobs were copied byte-for-byte into a fresh control commit over frozen main:

- inactive workflow blob `156d2822f5ed1b2f2c55055abc88bba054c80cfc`
- builder blob `8ad0c080d6c3c3a56193c30de980075c99faf828`
- activation-support blob `c3a6bdf832dbb78da74e0157c0124b12c53c1c0e`
- activation tree `26c6e817eb163d529acfdd09b5fa3c3a4493f1ec`
- control commit `ded92d780f949165ffd41062c7717bd42f399069`
- status branch `status/opac-species-profile-transport-capability-v4`
- request/status head `1bb66dbedd28b31b5d295729ca2cdc9da927031b`

The request was bound to PR #588, review run `33180739737`, exact review head, and frozen main.

Consumed one-shot execution:

- run `33184511183`, attempt 1 — FAILURE
- artifact `9691137631`
- artifact digest `sha256:b538b58a44873eca3eebd64493edf3d9b88991e73ccb48f0d5e71ff1c9f2aee4`
- MYSTIC did not run

V4 tested only the library-root byte-identical alias:

- source `aerosol/OPAC/optprop/inso.mie.cdf`
- alias `aerosol/OPAC/INSO.nc`
- source/alias SHA-256 both `fe10348cbe585315d6e1db382563fdc054204ad35846f371dc9d8abeead36407`
- alias byte count `1595764`

Runtime provenance proves the alias was actually created:

- pre-alias staged tree `5d8bbf8e6b91ec3d405dee36f21a94afbb6e5ec6cd67da2dd5dd541738199d80`
- post-alias tree `0078cb5ba8aab212d41dfdac1be3a725748733306853fc58c8f591c217914f3e`
- file count increased by exactly one
- locked `uvspec` SHA remained `2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3`

All four `uvspec -c` syntax checks passed. The first real DISORT LOW call immediately failed with the **same** preserved stderr:

```text
Error, found neither netcdf nor ASCII optical property files.
Check your aerosol properties and retry!
Error -1 in (function 'read_caoth_prop', file 'cloud.c', line 2854)
Error -1 in (function 'aerosol_species_to_optical_properties', file 'aerosol.c', line 2338)
Error -1 in (function 'setup_aerosol', file 'aerosol.c', line 747)
Error -1 in (function 'uvspec', file 'uvspec.c', line 114)
Error -1 during execution of uvspec
```

The frozen capability report is `FAILED_BEFORE_REQUIRED_COMPARISONS`; DISORT comparison false, MYSTIC comparison false, no ordinal, no Taylor/Jerusalem use, no production authorization.

**Do not rerun v4.**

## 6. What v3 + v4 now prove

Neither of these byte-identical aliases is sufficient for the locked libRadtran 2.0.6 explicit-species resolver:

1. `aerosol/OPAC/optprop/INSO.nc`
2. `aerosol/OPAC/INSO.nc`

The official user guide's abstract `species_name.nc` contract is therefore not enough to infer the concrete pathname used by this frozen binary/archive combination.

Do **not** guess another alias path and execute it.

The next corrective step must observe the binary's actual file lookup attempts.

## 7. Current active next step: fresh ordinal-free resolver-path trace

No parallel `opac-species-profile-transport-capability-v5` branch existed when checked after v4 failure.

Create a fresh **review-only, inactive, ordinal-free** diagnostic identity whose only purpose is to record the actual filesystem lookup attempted by the locked `uvspec` binary around the first deterministic DISORT execution.

Recommended diagnostic surface:

- keep the exact v4 synthetic LOW profile and directive surface unchanged;
- keep the exact frozen base runtime and OPAC archive identities;
- do not run MYSTIC;
- do not allocate a scientific ordinal;
- run exactly one deterministic DISORT LOW invocation under `strace` (or an equivalently exact syscall/file-open tracer);
- capture only file-resolution syscalls needed to identify candidate optical-property pathnames, e.g. `openat`, `open`, `stat`, `newfstatat`, `access`;
- preserve command exit code, stderr, and trace as artifact evidence even when uvspec fails;
- terminal success for this diagnostic means the trace unambiguously identifies the attempted optical-property pathname(s); it does **not** require solver success and is not a scientific PASS;
- do not use target residuals, Taylor, Jerusalem, Level-B, or production state.

Only after the exact attempted pathname is known may a separate fresh reviewed transport-capability identity test the minimal path/format correction.

## 8. Frozen capability parameters that must not drift

For any successor transport capability after the resolver-path diagnostic:

- species `INSO`
- LOW `exp(-z/0.55 km)`
- HIGH Gaussian center 8.0 km, sigma 0.75 km
- exact AFGL-US altitude grid
- AOD550 `0.10`
- DISORT SZA 80 deg
- MYSTIC SZA 96 deg only after deterministic transport works
- wavelength 540–560 nm on the exact frozen 1-nm repository grid
- target altitude 30 deg
- relative azimuth 90 deg
- albedo 0.15
- MYSTIC `mc_spherical 1D`, VROOM
- 500000 photons/profile
- paired seed `730194613`
- exact aerosol directives:

```text
aerosol_default
aerosol_species_library OPAC
aerosol_species_file <synthetic-profile-file> INSO
aerosol_set_tau_at_wvl 550 0.100000
```

No `aerosol_file tau` may be reintroduced.

## 9. Hard prohibitions

Do not:

- rerun/reuse ordinal 40;
- allocate ordinal 41 before an ordinal-free transport capability passes;
- rerun v2 run `33177704575`;
- rerun v3 run `33180158034`;
- rerun v4 run `33184511183`;
- amend a consumed one-shot identity and pretend it is the reviewed run;
- guess a third OPAC alias path and execute it without observing the binary lookup first;
- treat syntax-only success as runtime property resolution;
- claim ordinal-40 zero contrast is physical;
- select profiles/provider/cycle from Taylor/Jerusalem residual direction or magnitude;
- proceed to Level-B profile mapping before a fresh scientific experiment;
- move `main` merely for convenience;
- create production authorization from a capability diagnostic.

## 10. Broader retained project state

Still authoritative from the master closure track:

- generic SSA/g sensitivity (AOPS ordinal 37), full aerosol family/phase-function sensitivity (AFPF ordinal 38), and scalar/derived aerosol scenario transport (ASIV ordinal 39) are closed for their stated scopes and should not be duplicated;
- Taylor #508 remains evidence that independently constrained aerosol vertical structure can materially change direct-MYSTIC twilight radiance;
- Taylor atmosphere provenance/uncertainty boundaries #535/#529/#536 remain authoritative;
- acquiring better independent Taylor-night atmosphere data is a separate lane and must not be used to fit residuals.

Anti-fitting rules remain binding.

## 11. Resume checklist

Before any next write/run:

- confirm `main == 99ade7798627e67921139697ba1a004fa8a304bb`;
- confirm PR #588 remains Draft/open/unmerged on reviewed head `7b2a2f7ae14a7777408ab36de65fcc4a91b4a8de`;
- preserve v4 artifact `9691137631` / digest `sha256:b538b58a44873eca3eebd64493edf3d9b88991e73ccb48f0d5e71ff1c9f2aee4`;
- search again for parallel post-v4/v5 work before creating anything;
- create only an inactive resolver-path diagnostic first;
- require its exact-head dedicated review and repository-wide contract before activation;
- never GitHub-rerun a consumed diagnostic activation;
- after trace evidence identifies the concrete lookup, freeze a separate minimal corrected transport capability under another fresh review identity;
- only after deterministic DISORT and paired MYSTIC both prove LOW/HIGH nonidentity may a replacement scientific AVPS experiment be preregistered with a fresh ordinal (currently expected next ordinal 41, subject to a fresh ledger audit at allocation time);
- update this handoff after each new reviewed identity, activation, PASS/FAIL, or scientific preregistration.

## 12. One-line live status

**Ordinal 40 is scientifically non-informative; v2, v3, and v4 are terminal failed ordinal-free capability identities; v4 proved that even a byte-identical `aerosol/OPAC/INSO.nc` alias is not resolved by the locked binary, so the next permitted step is a fresh review-only syscall/path-trace diagnostic to observe exactly which optical-property pathname `uvspec` attempts before any further transport fix or ordinal 41 allocation.**
