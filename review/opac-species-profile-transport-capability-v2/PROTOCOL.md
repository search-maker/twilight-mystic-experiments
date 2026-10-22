# OPAC species-profile transport capability v2

Status: **REVIEW ONLY / INACTIVE / NO SCIENTIFIC ORDINAL / NO TARGET SCORING**

## Why this gate exists

AVPS scientific ordinal 40 executed through the full immutable 360-case evidence pipeline, but the preregistered vertical-profile contrast was scientifically non-informative. State-specific `aerosol_file tau` files were genuinely different while raw MYSTIC outputs were byte-identical across the five states within every CRN replicate group.

The root cause is the libRadtran aerosol-description hierarchy. The ordinal-40 surface combined a custom `aerosol_file tau` with the same `aerosol_species_file continental_average` in every state. libRadtran documents `aerosol_species_file` as the higher-precedence mechanism that defines the vertical mass-density profiles of the species mixture. Thus the intended custom tau profile was superseded by the fixed OPAC mixture profile.

This gate does **not** measure scientifically realistic profile sensitivity. Its only purpose is to prove a corrected transport surface in which the vertical profile is actually the input owned by `aerosol_species_file` itself.

Official syntax/semantics reference: libRadtran User's Guide, `aerosol_species_file`, `aerosol_species_library`, `aerosol_set_tau_at_wvl`, and aerosol hierarchy sections: <https://www.libradtran.org/doc/libRadtran.pdf>.

The User's Guide defines the ASCII custom-species syntax as:

```text
aerosol_species_file profile [aero_1 aero_2 ... aero_n]
```

with altitude in km and one mass-density column in g/m3 for every listed species. OPAC species include `INSO`, `WASO`, `SOOT`, `SSAM`, `SSCM`, `MINM`, `MIAM`, `MICM`, `MITR`, and `SUSO`.

## Fixed capability question

Can the exact locked project libRadtran/OPAC runtime distinguish two deliberately different vertical mass-density profiles when:

- the aerosol optical species is exactly the same single OPAC species, `INSO`;
- column AOD550 is reset to exactly `0.10` in both cases with `aerosol_set_tau_at_wvl`;
- geometry, atmosphere, surface, wavelength support, numerical settings and MYSTIC seed are fixed;
- no competing `aerosol_file tau` directive is present?

If yes, the project has a viable low-level primitive for a later scientifically designed vertical-profile experiment. If no, stop and investigate before allocating a new scientific ordinal.

## Why `INSO`

This capability uses one **synthetic, non-climatological** species only. `INSO` is chosen because it is the OPAC insoluble species; unlike the soluble OPAC species, its optical properties are not selected from humidity-growth states. This makes the capability test cleaner when aerosol mass is moved vertically through an atmosphere with changing relative humidity.

This is **not** a claim that INSO is the correct aerosol family for Taylor, Jerusalem, or any site.

## Exact runtime binding

Reuse the same exact runtime surface previously established by the OPAC capability/AFPF lanes:

- conda package: `rubin-libradtran=2.0.6=py312pl5321he9373c2_1`;
- official OPAC archive SHA-256: `11daa1f1f4be0fd4ddf7e881ec2005498049674a1540d37b4b1e8f5e16052c7e`;
- official OPAC archive size: `743391266` bytes;
- base libRadtran data-tree SHA-256: `ad30b49177e9c84e46497d69faf0c75e466996b0d0003f1de210289ae9f847d7`;
- staged OPAC data-tree SHA-256: `5d8bbf8e6b91ec3d405dee36f21a94afbb6e5ec6cd67da2dd5dd541738199d80`;
- `uvspec` SHA-256: `2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3`;
- atmosphere: exact staged `atmmod/afglus.dat`;
- repository wavelength grid: `experiments/aerosol-family-challenge-v2-r8/wavelength-grid-1nm.dat`.

Any drift is a refusal, not a reason to silently update the diagnostic.

## Frozen two-profile synthetic universe

Both profiles are generated on the exact AFGL-US altitude levels and normalized to the same arbitrary integrated mass before the independent AOD rescale. Their absolute mass has no scientific interpretation.

### LOW

```text
shape(z) = exp(-z / 0.55 km)
```

This is deliberately concentrated near the surface.

### HIGH

```text
shape(z) = exp(-0.5 * ((z - 8.0 km) / 0.75 km)^2)
```

This is deliberately concentrated near 8 km.

Both are synthetic capability stress states, selected before execution and unrelated to Taylor/Jerusalem residuals.

## Corrected aerosol surface

Each case must contain exactly:

```text
aerosol_default
aerosol_species_library OPAC
aerosol_species_file <synthetic-profile-file> INSO
aerosol_set_tau_at_wvl 550 0.100000
```

The corrected capability must contain **no** `aerosol_file tau`, `aerosol_file ssa`, `aerosol_file gg`, `aerosol_file moments`, aerosol-family mixture preset, or aerosol-family selection from observations.

## Frozen deterministic DISORT check

Purpose: quickly prove that the custom species-profile surface affects deterministic radiative-transfer physics before MYSTIC is invoked.

- SZA `80 deg`;
- observer elevation `0 m`;
- target sky altitude `30 deg`;
- relative azimuth `90 deg`;
- albedo `0.15`;
- wavelength interval `540–560 nm` on the frozen 1-nm grid;
- AOD550 `0.10`;
- `rte_solver disort`;
- 16 streams;
- same atmosphere/solar spectrum for LOW and HIGH.

PASS requires both syntax checks to succeed and the deterministic DISORT output bytes to be non-identical. Exact identity is a fail-closed result.

No minimum scientific effect size is defined or inferred.

## Frozen MYSTIC transport check

Purpose: prove that the corrected profile reaches the same spherical MYSTIC solver family used by the project.

- SZA `96 deg` (synthetic twilight geometry; not Taylor/Jerusalem);
- observer elevation `0 m`;
- target sky altitude `30 deg`;
- relative azimuth `90 deg`;
- albedo `0.15`;
- wavelength interval `540–560 nm` on the frozen 1-nm grid;
- AOD550 `0.10`;
- `rte_solver mystic`;
- `mc_spherical 1D`;
- `mc_vroom on`;
- `mc_std`;
- exactly `500000` photon histories per profile;
- exact paired seed `730194613` for LOW and HIGH.

PASS requires:

1. both syntax checks succeed;
2. both MYSTIC runs exit successfully without timeout;
3. required `mc.rad.spc` and `mc.rad.std.spc` files are non-empty;
4. LOW and HIGH use the exact same frozen seed;
5. LOW and HIGH `mc.rad.spc` SHA-256 values are **not equal**;
6. numeric spectra parse as finite values on identical wavelength grids;
7. no rerun/retry/resume is used;
8. no scientific materiality threshold is created from the observed difference.

A non-identical result proves only that vertical species-profile control reaches MYSTIC. It does not quantify valid atmospheric sensitivity.

## Hard interpretation boundary

This capability does not authorize or establish:

- a new scientific ordinal;
- any realistic vertical-profile prior;
- Taylor or Jerusalem fitting/scoring;
- the magnitude/sign of real vertical-profile sensitivity;
- a Level-B vertical-profile mapper;
- production routing;
- `F` or transient-tau changes;
- choice of aerosol family for any location.

If PASS, the next step is a **separate preregistration** for a replacement generalized vertical-profile sensitivity study under a fresh scientific ordinal.

If FAIL, stop. Diagnose the libRadtran species-profile/AOD-normalization surface or move to a separately reviewed explicit-layer optical-property representation. Do not reuse ordinal 40.
