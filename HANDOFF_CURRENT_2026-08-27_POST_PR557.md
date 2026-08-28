# STAR VISIBILITY / MYSTIC — LIVE CURRENT HANDOFF

**Live refresh: 2026-08-28 — after successful OPAC resolver syscall trace.**

The filename is historical. This is the current computational/scientific checkpoint.

## 1. Immutable baseline

Repository: `search-maker/twilight-mystic-experiments`

Frozen `main`:

`99ade7798627e67921139697ba1a004fa8a304bb`

Do not move `main` merely to continue this lane.

AVPS ordinal 40 is already consumed and must never be rerun/reused. Read-only ledger audit on 2026-08-28 still showed ordinal 40 as the latest consumed ordinal and no ordinal-41 branch. **Do not allocate ordinal 41 until an ordinal-free corrected profile-transport capability passes.**

## 2. Ordinal 40 final scientific classification

Ordinal 40 execution/recovery/result opening completed. The opened LOW/HIGH/reference contrasts were exactly zero, but raw audit proved that the state-specific profile files differed while solver outputs were byte-identical across states. The intended vertical-profile state did not reach effective solver physics.

Authoritative classification:

`EXECUTION/EVIDENCE PIPELINE VALID; SCIENTIFIC VERTICAL-PROFILE CONTRAST NON-INFORMATIVE.`

Never use ordinal 40 as evidence for vertical-profile insensitivity, Taylor/Jerusalem correction, Level-B mapping, or production routing.

Key evidence chain retained:

- recovered 360/360 science run `33139545997` SUCCESS
- Gate-0 artifact `9676069031`, digest `sha256:70dedcd16209dea74a9ed67a1dc7377c123f1a62fd18741b1e15692702011fc8`
- Phase A `33170006532` SUCCESS
- Phase B result opening `33170855407` SUCCESS

## 3. Terminal failed corrective transport identities

### v2 / PR #586

- review head `d90d3bca966d566d328fc1d91fb44f65c58d12b4`
- dedicated review `33172089158` SUCCESS
- repository contract `33172089150` SUCCESS
- one-shot run `33177704575` FAILURE
- artifact `9688346720`
- digest `sha256:adb10217279e27e2ca9101ab92b7a4467805c113438f6c7dc7552d0354938b21`
- failure before MYSTIC: `found neither netcdf nor ASCII optical property files`

### v3 / PR #587

Tested byte-identical official OPAC source

`aerosol/OPAC/optprop/inso.mie.cdf`

as alias

`aerosol/OPAC/optprop/INSO.nc`.

- reviewed head `a396714a851d371a584ed4d4d2bd8e83765d05c4`
- dedicated review `33179715436` SUCCESS
- repository contract `33179715434` SUCCESS
- one-shot run `33180158034` FAILURE
- artifact `9689369400`
- digest `sha256:3549c546cf2517b9d9603f4f7eafcef7ca8a8f37fb59f25fb8721ec4e63b7201`
- same unresolved-property error; MYSTIC never ran

### v4 / PR #588

Tested the same official bytes as alias

`aerosol/OPAC/INSO.nc`.

- reviewed head `7b2a2f7ae14a7777408ab36de65fcc4a91b4a8de`
- dedicated review `33180739737` SUCCESS
- repository contract `33180739633` SUCCESS
- control commit `ded92d780f949165ffd41062c7717bd42f399069`
- request head `1bb66dbedd28b31b5d295729ca2cdc9da927031b`
- one-shot run `33184511183` FAILURE
- artifact `9691137631`
- digest `sha256:b538b58a44873eca3eebd64493edf3d9b88991e73ccb48f0d5e71ff1c9f2aee4`
- pre-alias staged tree `5d8bbf8e6b91ec3d405dee36f21a94afbb6e5ec6cd67da2dd5dd541738199d80`
- post-alias tree `0078cb5ba8aab212d41dfdac1be3a725748733306853fc58c8f591c217914f3e`
- source/alias SHA-256 `fe10348cbe585315d6e1db382563fdc054204ad35846f371dc9d8abeead36407`
- all syntax checks passed; first real DISORT LOW failed with the same unresolved-property error; MYSTIC never ran

Do not rerun v2, v3, or v4.

## 4. Resolver path trace / PR #589 — terminal diagnostic SUCCESS

Because v3 and v4 proved that guessing documented `.nc` locations was insufficient, a fresh ordinal-free syscall trace was prereviewed and executed.

PR #589:

`Review OPAC explicit-species resolver path trace v1`

- Draft/open/unmerged
- branch `review/opac-species-resolver-path-trace-v1`
- exact reviewed head `d2f78f8be3fb94e4e64ce4c12901cb3f937ef0b6`
- base frozen main
- no scientific ordinal
- no MYSTIC
- no HIGH solver execution
- no alias creation

Review gates:

- dedicated review `33185082374`, attempt 1 — SUCCESS
- review artifact `9691331443`
- review artifact digest `sha256:72f868ded8693f47c4e476391735bb1dfd73aaacca3dfe63fcd2da4bf4f715da`
- repository contract `33185082300`, attempt 1 — SUCCESS

Activation identity:

- exact inactive-workflow blob `b5cfa601431166660a906fbcd0138bd1f5c7fdd6`
- exact parser blob `072e0f9b07b23566f159e4fed6805bb208203cb7`
- activation tree `d335a19c1e8fb03fdadde1d81b0b4018c29e6a20`
- control commit `28191b88daafc858e96ab098c1df01962211169b`
- status branch `status/opac-species-resolver-path-trace-v1`
- request head `a266d1d3705c41519d3930206ca4f918db9cbb9e`

Consumed one-shot diagnostic:

- run `33185460954`, attempt 1 — diagnostic SUCCESS
- artifact `9691518729`
- artifact digest `sha256:07fb60de7bef96253eaf29cb9303a83bab7f3f1952431c73a26499357b4d572a`
- locked v2 LOW input was used without any alias
- exact v4 archive extractor was reused
- `uvspec` exit code remained `255`, with the expected unresolved-property stderr
- MYSTIC false; HIGH solver false; scientific ordinal false; Taylor/Jerusalem false; production false

### Exact observed lookup — critical new fact

The trace showed the locked binary opening the directory:

`.../data/aerosol/OPAC/optprop`

and then issuing:

```text
newfstatat(..., ".../data/aerosol/OPAC/optprop/INSO", ..., AT_SYMLINK_NOFOLLOW) = -1 ENOENT
```

The frozen parsed candidate list contains exactly one missing property path:

`.../data/aerosol/OPAC/optprop/INSO`

**with no extension.**

Immediately after that missing lookup, `uvspec` exited 255 with `found neither netcdf nor ASCII optical property files`.

This is the first direct runtime evidence of the concrete path expected by the locked binary and explains why aliases at `optprop/INSO.nc` and `OPAC/INSO.nc` did not fix transport.

## 5. Current active next step — transport capability v5

No parallel `opac-species-profile-transport-capability-v5` branch existed at the most recent check.

The next permissible correction is a fresh **review-only, inactive, ordinal-free** transport capability that changes only the demonstrated resolver mismatch:

- official source stays `aerosol/OPAC/optprop/inso.mie.cdf`;
- source SHA-256 stays `fe10348cbe585315d6e1db382563fdc054204ad35846f371dc9d8abeead36407`;
- create exactly one byte-identical alias at the observed pathname `aerosol/OPAC/optprop/INSO` **with no extension**;
- prove source and alias SHA/size equality;
- prove the old v3/v4 aliases do not exist;
- otherwise keep all v2-v4 physics, geometry, profile definitions, seed, photon count, runtime and archive identities unchanged.

V5 must run deterministic LOW/HIGH DISORT first. PASS requires both real solver outputs to exist and differ. Only then may paired MYSTIC LOW/HIGH execute, and PASS additionally requires nonempty, finite, identical-grid but nonidentical `mc.rad.spc` outputs.

A v5 PASS proves only that explicit OPAC species profiles reach solver physics. It does not establish scientific materiality.

Only after such a capability PASS may a replacement AVPS experiment be preregistered under a fresh scientific ordinal (currently expected to be 41, subject to a fresh ledger audit at allocation time).

## 6. Frozen capability parameters — do not drift

- species `INSO`
- LOW `exp(-z/0.55 km)`
- HIGH Gaussian centered 8.0 km, sigma 0.75 km
- exact AFGL-US altitude grid
- AOD550 `0.10`
- DISORT SZA 80 deg
- MYSTIC SZA 96 deg
- wavelength 540–560 nm on exact frozen 1-nm repository grid
- target altitude 30 deg
- relative azimuth 90 deg
- albedo 0.15
- MYSTIC `mc_spherical 1D`, VROOM
- exactly 500000 photons/profile
- paired seed `730194613`
- aerosol directive surface:

```text
aerosol_default
aerosol_species_library OPAC
aerosol_species_file <synthetic-profile-file> INSO
aerosol_set_tau_at_wvl 550 0.100000
```

No `aerosol_file tau` may be reintroduced.

## 7. Hard prohibitions

Do not:

- rerun/reuse ordinal 40;
- allocate ordinal 41 before an ordinal-free transport capability PASS;
- rerun v2 run `33177704575`;
- rerun v3 run `33180158034`;
- rerun v4 run `33184511183`;
- rerun path-trace run `33185460954`;
- amend any consumed one-shot identity and pretend it is the reviewed run;
- introduce any alias other than the exact observed `aerosol/OPAC/optprop/INSO` in v5;
- modify official OPAC optical-property bytes;
- treat syntax-only success as runtime property resolution;
- claim ordinal-40 zero contrast is physical;
- fit Taylor/Jerusalem residuals to choose profile/provider/cycle;
- proceed to Level-B profile mapping before a fresh scientific experiment;
- move `main` merely for convenience;
- create production authorization from a capability diagnostic.

## 8. Broader retained project state

- AOPS ordinal 37, AFPF ordinal 38, and ASIV ordinal 39 are closed for their stated scopes and should not be duplicated.
- Taylor #508 remains evidence that independently constrained aerosol vertical structure can materially alter direct-MYSTIC twilight radiance.
- Taylor atmosphere provenance/uncertainty boundaries #535/#529/#536 remain authoritative.
- Better independent Taylor-night atmosphere acquisition is a separate lane and must not be used to fit residuals.

Anti-fitting rules remain binding.

## 9. Resume checklist

Before any next write/run:

- confirm `main == 99ade7798627e67921139697ba1a004fa8a304bb`;
- preserve trace artifact `9691518729` / digest `sha256:07fb60de7bef96253eaf29cb9303a83bab7f3f1952431c73a26499357b4d572a`;
- confirm #589 remains Draft/open/unmerged on exact reviewed head;
- search again for parallel v5 work;
- create v5 as review-only/inactive first;
- require dedicated exact-head review and repository-wide contract before v5 activation;
- never rerun a consumed activation;
- after v5 PASS, re-audit Issue #60 before allocating the fresh replacement AVPS ordinal;
- update this handoff again after v5 review, activation, PASS/FAIL, or scientific preregistration.

## 10. One-line live status

**Ordinal 40 is scientifically non-informative; v2-v4 are terminal failed transport identities; the reviewed syscall diagnostic #589/run 33185460954 succeeded and directly proved that the locked libRadtran binary attempts `data/aerosol/OPAC/optprop/INSO` with no extension; the next step is an ordinal-free v5 transport capability using a byte-identical official `inso.mie.cdf` alias at exactly that observed path, with no other scientific change.**
