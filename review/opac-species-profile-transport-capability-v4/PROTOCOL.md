# OPAC species-profile transport capability v4

Status: **REVIEW ONLY / INACTIVE / NO SCIENTIFIC ORDINAL / NO TARGET SCORING**

## Why v4 exists

AVPS ordinal 40 is scientifically non-informative because the intended vertical-profile state did not reach effective solver physics. Capability v2 (#586; run 33177704575) corrected the directive hierarchy but failed because the explicit INSO species optical-property file could not be resolved. Capability v3 (#587; run 33180158034) then created a byte-identical alias at `aerosol/OPAC/optprop/INSO.nc`; the alias and runtime-provenance checks passed, but the first real DISORT call failed with the exact same `found neither netcdf nor ASCII optical property files` error. MYSTIC did not run.

The libRadtran `aerosol_species_library` contract defines the selected library as the directory in which each `species_name.nc` is expected. Therefore, for `aerosol_species_library OPAC`, v4 tests only one newly demonstrated resolver correction: place a byte-identical alias at the OPAC library root, `aerosol/OPAC/INSO.nc`, rather than the failed v3 location `aerosol/OPAC/optprop/INSO.nc`.

## Frozen repair

Official source bytes remain exactly:

- source: `aerosol/OPAC/optprop/inso.mie.cdf`
- source SHA-256: `fe10348cbe585315d6e1db382563fdc054204ad35846f371dc9d8abeead36407`
- alias: `aerosol/OPAC/INSO.nc`
- alias must not preexist
- alias must be byte-for-byte identical to source
- no conversion, interpolation, netCDF rewrite, optical-property modification, or target-derived choice is allowed

The official OPAC archive remains frozen at SHA-256 `11daa1f1f4be0fd4ddf7e881ec2005498049674a1540d37b4b1e8f5e16052c7e`.

## Frozen transport question

Everything physical remains unchanged from v2/v3:

- one synthetic OPAC species: `INSO`
- LOW: `exp(-z / 0.55 km)`
- HIGH: Gaussian centered 8.0 km, sigma 0.75 km
- exact AFGL-US altitude grid
- AOD550 = 0.10 for both states
- DISORT first at SZA 80 deg
- MYSTIC second at SZA 96 deg
- wavelength 540-560 nm on the frozen 1-nm grid
- target altitude 30 deg, relative azimuth 90 deg, albedo 0.15
- MYSTIC spherical 1D, VROOM, exactly 500000 photons/profile
- paired seed 730194613

Exact aerosol surface:

```text
aerosol_default
aerosol_species_library OPAC
aerosol_species_file <synthetic-profile-file> INSO
aerosol_set_tau_at_wvl 550 0.100000
```

No `aerosol_file tau/ssa/gg/moments` is permitted.

## PASS / FAIL

PASS requires all of the following in one attempt:

1. exact frozen runtime/archive identities;
2. source and root-level alias byte identity;
3. all syntax checks pass;
4. both real DISORT runs succeed and LOW/HIGH outputs are non-identical;
5. only then both paired MYSTIC runs succeed;
6. both `mc.rad.spc` outputs are non-empty and non-identical;
7. no retry/rerun/resume and no scientific materiality threshold.

Any failure stops the capability lane and is diagnostic only.

## Interpretation boundary

This is an ordinal-free transport capability check only. It does not authorize a scientific vertical-profile conclusion, Taylor/Jerusalem scoring, Level-B mapping, production routing, or any F/transient-tau change. Ordinal 40 must never be reused. A capability PASS would only permit a separately preregistered replacement vertical-profile sensitivity experiment under a fresh scientific ordinal.
