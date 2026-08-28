# STAR VISIBILITY / MYSTIC — LIVE CURRENT HANDOFF

**Live refresh: 2026-08-28 — OPAC vertical-profile transport capability v5 has PASSED.**

The filename is historical. This content is the current computational/scientific checkpoint.

## 1. Immutable baseline

Repository: `search-maker/twilight-mystic-experiments`

Frozen `main` remains:

`99ade7798627e67921139697ba1a004fa8a304bb`

Frozen main tree:

`2d4bb1df136bff2da93f191e5518b94b3d7fecfc`

Do not move `main` merely to continue this lane.

## 2. Ordinal 40 is consumed and scientifically non-informative

AVPS ordinal 40 was executed, recovered to 360/360 case artifacts, and opened. Its state contrasts were exactly zero, but raw matched-group audit proved that the intended vertical-profile state did **not** reach effective solver physics: state-specific profile files differed while solver outputs were byte-identical across states.

Authoritative classification:

`EXECUTION/EVIDENCE PIPELINE VALID; SCIENTIFIC VERTICAL-PROFILE CONTRAST NON-INFORMATIVE.`

Never reuse/rerun ordinal 40 and never cite its zero contrast as evidence of vertical-profile insensitivity.

Retained ordinal-40 evidence:

- recovery science run `33139545997` SUCCESS, 360/360 cases
- Gate-0 artifact `9676069031`, digest `sha256:70dedcd16209dea74a9ed67a1dc7377c123f1a62fd18741b1e15692702011fc8`
- Phase A `33170006532` SUCCESS
- Phase B result opening `33170855407` SUCCESS

## 3. Resolver diagnosis chain — terminal identities, never rerun

### v2 / PR #586

- review head `d90d3bca966d566d328fc1d91fb44f65c58d12b4`
- review `33172089158` SUCCESS
- contract `33172089150` SUCCESS
- one-shot run `33177704575` FAILURE
- artifact `9688346720`
- digest `sha256:adb10217279e27e2ca9101ab92b7a4467805c113438f6c7dc7552d0354938b21`
- deterministic transport failed with `found neither netcdf nor ASCII optical property files`; MYSTIC never ran

### v3 / PR #587

Tested byte-identical official `inso.mie.cdf` at failed alias `aerosol/OPAC/optprop/INSO.nc`.

- reviewed head `a396714a851d371a584ed4d4d2bd8e83765d05c4`
- review `33179715436` SUCCESS
- contract `33179715434` SUCCESS
- one-shot run `33180158034` FAILURE
- artifact `9689369400`
- digest `sha256:3549c546cf2517b9d9603f4f7eafcef7ca8a8f37fb59f25fb8721ec4e63b7201`

### v4 / PR #588

Tested the same official bytes at failed alias `aerosol/OPAC/INSO.nc`.

- reviewed head `7b2a2f7ae14a7777408ab36de65fcc4a91b4a8de`
- review `33180739737` SUCCESS
- contract `33180739633` SUCCESS
- control `ded92d780f949165ffd41062c7717bd42f399069`
- request head `1bb66dbedd28b31b5d295729ca2cdc9da927031b`
- one-shot run `33184511183` FAILURE
- artifact `9691137631`
- digest `sha256:b538b58a44873eca3eebd64493edf3d9b88991e73ccb48f0d5e71ff1c9f2aee4`

V2-v4 are terminal consumed capability identities. Do not GitHub-rerun them.

## 4. Resolver syscall trace / PR #589 — diagnostic SUCCESS

PR #589 froze an ordinal-free, LOW-only, no-alias `strace` diagnostic.

- review head `d2f78f8be3fb94e4e64ce4c12901cb3f937ef0b6`
- review `33185082374` SUCCESS
- review artifact `9691331443`, digest `sha256:72f868ded8693f47c4e476391735bb1dfd73aaacca3dfe63fcd2da4bf4f715da`
- contract `33185082300` SUCCESS
- control `28191b88daafc858e96ab098c1df01962211169b`
- request head `a266d1d3705c41519d3930206ca4f918db9cbb9e`
- one-shot diagnostic run `33185460954` SUCCESS
- artifact `9691518729`
- digest `sha256:07fb60de7bef96253eaf29cb9303a83bab7f3f1952431c73a26499357b4d572a`

Critical direct runtime observation:

```text
.../data/aerosol/OPAC/optprop/INSO
```

The locked binary attempted that pathname **with no extension**, received ENOENT, and then emitted the unresolved-optical-property error. This explains the v3/v4 failures.

Do not rerun the trace identity.

## 5. OPAC species-profile transport capability v5 / PR #590 — PASS

PR #590:

`Review trace-grounded OPAC species-profile transport capability v5`

- Draft/open/unmerged
- branch `review/opac-species-profile-transport-capability-v5`
- exact reviewed head `f0675ec48c637509cd7a5bb9c2a2746507e5bea8`
- base `main == 99ade7798627e67921139697ba1a004fa8a304bb`
- no scientific ordinal
- no Taylor/Jerusalem scoring
- no Level-B or production mutation

Review gates:

- dedicated review `33186027699`, attempt 1 — SUCCESS
- review artifact `9691708991`
- review digest `sha256:b60a16626a0e8e1ce39adb50f200fe2e487667e97cf8b2c5198b26f27436fb1f`
- repository contract `33186027637`, attempt 1 — SUCCESS

Exact reviewed activation blobs:

- inactive workflow `ec73ff112b209786a2b3b6aa48fe2e4d2cc9e103`
- builder `5fd3067d4840dad6c0ff5d68ae76327a05499190`
- activation/output validator `c68fd7b48f322dcfac3cd39e0227a3aa794ed016`

Activation identity:

- tree `9a245be370c687a24d25444c2ec7976e34955b71`
- control commit `f41a619368fde6a48005cb3c44b52cee6b4d3a62`
- status branch `status/opac-species-profile-transport-capability-v5`
- request head `6f0d61aa3abf7e6e113853fbfc1c74e65d31dac9`

Consumed one-shot capability:

- run `33186446347`, attempt 1 — **SUCCESS**
- artifact `9691923455`
- artifact digest `sha256:fed6bb961088232e593159c4f50911758802e9209aed86e2a0eef4b403e4d9b7`
- capability-report content SHA-256 `da6d7f66625b63cb5ff4f69845c2953f2a509b3693c82d1f0203900dc7bd21d2`
- terminal status `PASS_TRACE_OBSERVED_ALIAS_REACHES_DISORT_AND_MYSTIC`

Exact resolver correction proven by v5:

- official source `aerosol/OPAC/optprop/inso.mie.cdf`
- exact solver-observed alias `aerosol/OPAC/optprop/INSO`
- source and alias SHA-256 both `fe10348cbe585315d6e1db382563fdc054204ad35846f371dc9d8abeead36407`
- alias byte count `1595764`
- byte-identical true
- failed v3/v4 `.nc` aliases absent
- pre-alias data tree `5d8bbf8e6b91ec3d405dee36f21a94afbb6e5ec6cd67da2dd5dd541738199d80`
- post-alias data tree `346c8f825759d8e975568b14ccbd125f6efcb1126c574c72163b8b948169456c`

Deterministic DISORT proof:

- LOW/HIGH both executed successfully
- 401 finite numeric rows each
- identical wavelength grid within pair
- LOW SHA-256 `c888ca29085b0111ccf36f41e37b78fd205224f1d08c00e65e67b58e4cb59dd1`
- HIGH SHA-256 `cd715c254bd78e00b9c945d0163c17e18b5d1f991d863e4065f7de16f8a09b8f`
- outputs non-identical

Paired spherical MYSTIC proof:

- LOW/HIGH both executed successfully
- `mc.rad.spc` and `mc.rad.std.spc` non-empty
- 401 finite radiance rows each
- identical wavelength grid within pair
- LOW `mc.rad.spc` SHA-256 `009877d8afb26ea7682a8b65ed060449fbfa672c37aa35afce8d33d9eb86f18a`
- HIGH `mc.rad.spc` SHA-256 `2e5cf494a9cf0da8b27368038f07305b0faa5fa7f099b02430c2340ed5243bb2`
- LOW/HIGH radiance outputs non-identical

**Interpretation boundary:** v5 proves only that corrected explicit OPAC species vertical profiles now reach both DISORT and MYSTIC solver physics. It does not establish scientific effect size or materiality, and it does not authorize Level-B or production.

Do not rerun v5.

## 6. Frozen transport representation for the replacement scientific AVPS

Any replacement scientific vertical-profile experiment must use the now-proven representation:

```text
aerosol_default
aerosol_species_library OPAC
aerosol_species_file <state-specific species profile> INSO
aerosol_set_tau_at_wvl 550 <frozen AOD>
```

and the runtime overlay must provide the byte-identical official optical-property asset at:

`data/aerosol/OPAC/optprop/INSO`

No `.nc` alias and no competing `aerosol_file tau` may be introduced.

## 7. Current active next step — replacement scientific vertical-profile sensitivity preregistration

A fresh scientific experiment is now permitted, but **ordinal 40 must not be reused**.

Required order:

1. re-audit Issue #60 and all authorization/dispatch branches for the latest allocated/consumed ordinal immediately before allocation;
2. confirm no parallel replacement-AVPS work has already allocated the next ordinal;
3. freeze a new review-only scientific preregistration using the corrected v5 representation;
4. preserve the original anti-fitting boundary: no Taylor/Jerusalem residual direction or magnitude may choose profile states, AODs, geometry, gates, or thresholds;
5. use a fresh scientific ordinal and fresh immutable seed/case identity;
6. use preregistered LOW/HIGH/reference profile states whose scientific meaning is specified independently of target residuals;
7. require preauthorization review before scientific dispatch;
8. execute once; no rerun/reuse after consumption;
9. freeze all raw artifacts before result opening;
10. only after the replacement experiment passes its preregistered scientific gates may Phase-C / Level-B vertical-profile mapping resume.

At the last read-only ledger audit, ordinal 40 was the latest consumed ordinal and no ordinal-41 branch existed. Therefore **41 is the expected next ordinal, but it must be freshly re-audited before allocation.**

## 8. Frozen capability parameters retained as implementation evidence

The v5 capability itself used:

- species `INSO`
- LOW `exp(-z/0.55 km)`
- HIGH Gaussian centered 8.0 km, sigma 0.75 km
- exact AFGL-US altitude grid
- AOD550 `0.10`
- DISORT SZA 80 deg
- MYSTIC SZA 96 deg
- wavelength 540–560 nm on frozen repository grid
- target altitude 30 deg
- relative azimuth 90 deg
- albedo 0.15
- MYSTIC `mc_spherical 1D`, VROOM
- 500000 photons/profile
- paired seed `730194613`

These values prove transport capability only. They are **not automatically the scientific design** of the replacement AVPS; that design must be independently preregistered before opening any new scientific results.

## 9. Hard prohibitions

Do not:

- rerun/reuse ordinal 40;
- reuse any ordinal-40 case/seed identity with patched inputs;
- GitHub-rerun v2 `33177704575`, v3 `33180158034`, v4 `33184511183`, trace `33185460954`, or v5 `33186446347`;
- amend a consumed one-shot identity and pretend it is the reviewed run;
- infer a scientific effect size from the v5 capability run;
- select scientific profile states/provider/cycle using Taylor/Jerusalem residual fit;
- reintroduce `aerosol_file tau` beside `aerosol_species_file`;
- use either failed `.nc` alias;
- proceed to Level-B profile mapping before replacement scientific evidence;
- move `main` for convenience;
- create production authorization from a capability PASS alone.

## 10. Broader retained project state

- AOPS ordinal 37, AFPF ordinal 38, and ASIV ordinal 39 remain closed for their stated scopes and should not be duplicated.
- Taylor #508 remains evidence that independently constrained aerosol vertical structure can materially alter direct-MYSTIC twilight radiance.
- Taylor atmosphere provenance/uncertainty boundaries #535/#529/#536 remain authoritative.
- Better independent Taylor-night atmosphere acquisition is a separate lane and must not be used to fit residuals.
- Anti-fitting rules remain binding.

## 11. Resume checklist

Before the next scientific write/allocation:

- [ ] confirm `main == 99ade7798627e67921139697ba1a004fa8a304bb`;
- [ ] preserve v5 artifact `9691923455` and digest `sha256:fed6bb961088232e593159c4f50911758802e9209aed86e2a0eef4b403e4d9b7`;
- [ ] confirm #590 remains Draft/open/unmerged on `f0675ec48c637509cd7a5bb9c2a2746507e5bea8`;
- [ ] re-audit Issue #60 and branch namespace for fresh ordinal allocation;
- [ ] search for parallel replacement-AVPS work before creating it;
- [ ] preregister science first; do not allocate/dispatch by improvisation;
- [ ] use the v5 no-extension resolver representation exactly;
- [ ] keep target residuals closed while selecting scientific design/gates;
- [ ] update this handoff after preregistration review, ordinal allocation, authorization, dispatch, execution, Gate-0, and result opening.

## 12. One-line live status

**Ordinal 40 remains scientifically non-informative, but the root cause is now fixed and proven: trace #589 showed the locked binary expects `data/aerosol/OPAC/optprop/INSO` with no extension, and reviewed capability v5/#590/run 33186446347 passed in both DISORT and MYSTIC with finite same-grid LOW/HIGH outputs that differ. The next permitted step is a fresh anti-fitted replacement vertical-profile sensitivity preregistration under a newly audited scientific ordinal (expected 41), not reuse of ordinal 40 and not Level-B promotion yet.**
