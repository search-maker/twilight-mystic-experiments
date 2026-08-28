# OPAC species-profile transport capability v3

Status: **REVIEW ONLY / INACTIVE / NO SCIENTIFIC ORDINAL / NO TARGET SCORING**

## Why v3 exists

AVPS ordinal 40 is scientifically non-informative for vertical-profile sensitivity because its state-specific `aerosol_file tau` surface was superseded by a fixed OPAC species-profile surface. Capability v2 (#586) corrected the directive hierarchy to `aerosol_species_file <profile> INSO`, but its one-shot activation run `33177704575` failed before deterministic transport: both DISORT calls returned libRadtran error -4, `uvspec found neither netcdf nor ASCII optical property files`. MYSTIC did not run.

The frozen official OPAC v2.1 archive contains the insoluble optical-property asset at `data/aerosol/OPAC/optprop/inso.mie.cdf`, while the explicit custom-species resolver used by the locked libRadtran build expects the legacy explicit-species filename convention represented here by `INSO.nc`.

V3 tests **only** that resolver mismatch. It does not alter aerosol optical-property bytes.

## Frozen resolver repair

Starting from the exact official OPAC archive already frozen by SHA-256 `11daa1f1f4be0fd4ddf7e881ec2005498049674a1540d37b4b1e8f5e16052c7e`:

- source: `aerosol/OPAC/optprop/inso.mie.cdf`
- alias: `aerosol/OPAC/optprop/INSO.nc`
- the alias must not preexist;
- the alias is created by byte-for-byte copy only;
- source and alias SHA-256 and byte count must be identical;
- the used libRadtran data-tree hash is recomputed **after** alias creation;
- both the pre-alias staged tree hash and post-alias used tree hash are preserved in evidence.

No reformatting, conversion, interpolation, netCDF rewriting, or optical-property change is allowed.

## Frozen transport question

Everything else is unchanged from capability v2:

- one synthetic OPAC species: `INSO`;
- LOW: `exp(-z / 0.55 km)`;
- HIGH: Gaussian centered `8.0 km`, sigma `0.75 km`;
- exact AFGL-US altitude grid;
- AOD550 `0.10` in both profiles;
- DISORT first at SZA 80 deg;
- MYSTIC second at SZA 96 deg;
- 540-560 nm, 1-nm frozen grid;
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
1. exact archive/base/staged-runtime identities pass;
2. byte-identical alias provenance passes;
3. post-alias runtime tree is explicitly recorded and differs from the pre-alias staged tree solely because the reviewed alias was added;
4. all four syntax checks pass;
5. LOW/HIGH DISORT outputs are non-identical on identical wavelength grids;
6. only then both paired MYSTIC runs execute successfully;
7. LOW/HIGH `mc.rad.spc` are non-empty, parse finite on identical grids, and are non-identical;
8. no rerun/retry/resume, no materiality threshold, no target-event comparison.

FAIL at any step means stop and diagnose. It does not support a null profile effect.

## Interpretation boundary

This is a low-level transport capability gate only. **NO SCIENTIFIC ORDINAL** is allocated. It does not authorize a realistic profile prior, a new AVPS experiment, Level-B mapping, Taylor/Jerusalem scoring, aerosol-family selection, production routing, F changes, or transient-tau changes.

If PASS, the next step is a separate replacement vertical-profile sensitivity preregistration under a fresh scientific ordinal. Ordinal 40 must never be reused as scientific vertical-profile evidence.
