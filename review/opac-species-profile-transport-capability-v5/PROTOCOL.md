# OPAC species-profile transport capability v5

Status: **REVIEW ONLY / INACTIVE / NO SCIENTIFIC ORDINAL / NO TARGET SCORING**

## Why v5 exists

AVPS ordinal 40 is scientifically non-informative because the intended vertical-profile state did not reach effective solver physics. Corrective ordinal-free transport capabilities v2, v3, and v4 all failed before deterministic transport with:

`found neither netcdf nor ASCII optical property files`

V3 tested a byte-identical official INSO optical-property alias at `aerosol/OPAC/optprop/INSO.nc`; v4 tested `aerosol/OPAC/INSO.nc`. Both failed.

A separately reviewed syscall diagnostic, PR #589 / run `33185460954`, then observed the locked libRadtran binary directly. Its frozen trace artifact `9691518729` (digest `sha256:07fb60de7bef96253eaf29cb9303a83bab7f3f1952431c73a26499357b4d572a`) showed the binary issuing a failed lookup for:

`data/aerosol/OPAC/optprop/INSO`

**with no extension**, immediately before the known resolver error.

V5 tests only that demonstrated resolver mismatch. It does not alter any optical-property bytes or scientific parameters.

## Frozen resolver correction

Starting from the exact official OPAC source asset:

- source: `aerosol/OPAC/optprop/inso.mie.cdf`
- source SHA-256: `fe10348cbe585315d6e1db382563fdc054204ad35846f371dc9d8abeead36407`
- exact trace-observed alias: `aerosol/OPAC/optprop/INSO`
- no extension is permitted on the alias;
- the alias must not preexist;
- source and alias must be byte-for-byte identical;
- source/alias SHA-256 and byte count must match;
- failed historical aliases `aerosol/OPAC/optprop/INSO.nc` and `aerosol/OPAC/INSO.nc` must remain absent;
- no netCDF rewrite, conversion, interpolation, optical-property modification, or alternate alias is allowed.

## Frozen transport question

Everything else remains exactly the same as v2-v4:

- one synthetic OPAC species: `INSO`;
- LOW: `exp(-z / 0.55 km)`;
- HIGH: Gaussian centered `8.0 km`, sigma `0.75 km`;
- exact AFGL-US altitude grid;
- AOD550 `0.10` in both profiles;
- deterministic DISORT first at SZA 80 deg;
- MYSTIC second at SZA 96 deg only after deterministic transport passes;
- 540-560 nm on the exact frozen 1-nm repository grid;
- target altitude 30 deg, relative azimuth 90 deg, albedo 0.15;
- MYSTIC `mc_spherical 1D`, VROOM, exactly `500000` photons/profile;
- paired seed `730194613`.

Exact aerosol directive surface remains:

```text
aerosol_default
aerosol_species_library OPAC
aerosol_species_file <synthetic-profile-file> INSO
aerosol_set_tau_at_wvl 550 0.100000
```

No `aerosol_file tau/ssa/gg/moments` is allowed.

## PASS / FAIL

PASS requires:

1. exact frozen runtime/archive identities pass;
2. the trace-observed no-extension alias provenance passes;
3. all four syntax checks pass;
4. LOW and HIGH deterministic DISORT both execute successfully;
5. their output grids are identical, values are finite, and outputs are non-identical;
6. only then paired LOW/HIGH spherical MYSTIC runs execute successfully;
7. both `mc.rad.spc` and `mc.rad.std.spc` outputs are non-empty;
8. LOW/HIGH `mc.rad.spc` parse as finite values on identical wavelength grids and are non-identical;
9. no rerun/retry/resume and no scientific materiality threshold.

FAIL at any step means stop and diagnose. It does not support a null profile effect.

## Interpretation boundary

A v5 PASS would prove only that explicit OPAC species mass-density profiles can reach DISORT and MYSTIC solver physics using the exact trace-observed resolver representation. It does **not** establish a scientifically material effect size, realistic climatological prior, Taylor/Jerusalem correction, Level-B mapping, or production authorization.

There is **NO SCIENTIFIC ORDINAL** in v5. Ordinal 41 remains unallocated. Only after v5 PASS may a separate replacement vertical-profile sensitivity experiment be preregistered under a fresh ordinal and fresh immutable case/seed identity.

Ordinal 40 and capability identities v2-v4 must never be reused or rerun.
