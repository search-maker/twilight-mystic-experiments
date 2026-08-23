# Aerosol full phase-function sensitivity v1 — scientific preregistration review

Status: **review only; execution disabled; no seeds, scientific ordinal, authorization, dispatch, solver, or result opening**.

## Why this fresh experiment exists

AFC2 R8 showed that changing the built-in Shettle aerosol family/season at fixed AOD550 changes twilight radiance and Level-B visibility, but the resulting envelope was limited. AOPS v1 then showed that independently changing SSA and asymmetry parameter `g` can produce materially larger and geometry-dependent effects. The verified AOPS report explicitly concludes that AOD550 alone is insufficient and that constant SSA/`g` controls are a sensitivity screen, not a replacement for wavelength-dependent realistic aerosol optical properties or a full angular phase function.

This experiment is the deliberately narrow next step. It does **not** fit aerosol properties to observations. It asks how the same frozen twilight design responds when aerosol states come from internally coherent OPAC mixtures with wavelength-dependent extinction, SSA and angular scattering information.

## Why OPAC is technically appropriate here

libRadtran 2.0.6 documents predefined OPAC mixtures through `aerosol_species_file`, with optical-property files supplied through `aerosol_species_library OPAC`. The official optical-property bundle has been independently byte-bound and overlaid onto the exact locked runtime. A separate attempt-1 resolver audit then proved that all ten documented predefined mixtures parse successfully under the exact locked `uvspec` using `uvspec -c`, the exact augmented data tree and `aerosol_set_tau_at_wvl 550 0.10`.

Runtime/source evidence already frozen before this preregistration:

- exact package: `rubin-libradtran=2.0.6=py312pl5321he9373c2_1`;
- exact `uvspec` SHA-256: `2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3`;
- official `optprop_v2.1.tar.gz` SHA-256: `11daa1f1f4be0fd4ddf7e881ec2005498049674a1540d37b4b1e8f5e16052c7e`;
- exact augmented staged libRadtran data-tree SHA-256: `5d8bbf8e6b91ec3d405dee36f21a94afbb6e5ec6cd67da2dd5dd541738199d80`;
- syntax resolver run `32656619842`, artifact `9497608332`, report SHA-256 `7e051d5b96f5d05ef960d3ea3aba8c6f164b8cb7d61c199ddfe244582d7792a3`;
- all ten documented mixtures returned exit 0 under exactly one process-isolated `uvspec -c` call each; no non-syntax call or scientific solver occurred.

Primary software references:

- libRadtran 2.0.6 User's Guide: https://www.libradtran.org/doc/libRadtran.pdf
- official optical-property download page: https://www.libradtran.org/doku.php?id=download
- OPAC optical-property background: Hess, Koepke & Schult (1998), *Bulletin of the American Meteorological Society* 79, 831–844.

## Five states only

The capability audit proved ten mixtures are available. That is **not** a reason to run all ten. This preregistration deliberately keeps the AOPS five-state cardinality and selects only states needed to answer the new question:

1. `native-rural-ss` — the rural/spring-summer Shettle bridge used by AOPS/R8;
2. `opac-continental-average` — an internally coherent continental OPAC reference;
3. `opac-maritime-clean` — a sea-salt-rich coarse-particle regime contrast;
4. `opac-desert` — mineral dust with the spherical mineral-particle treatment;
5. `opac-desert-spheroids` — the corresponding desert variation with spheroidal mineral-particle optical properties.

`urban` is intentionally omitted from v1. AOPS already established a strong absorption/SSA lever, and AFC2 R8 already contained an urban Shettle family. The fresh information sought here is coherent spectral/angular scattering and, especially, the direct dust-shape comparison.

## Why `desert` versus `desert_spheroids` is the key shape contrast

The OPAC nonspherical-dust extension changes the mineral-particle shape treatment while retaining the underlying mineral size distributions and spectral refractive indices. Published evaluation of that extension reports large angular phase-function differences between spherical and spheroidal mineral particles in the solar range, while the asymmetry parameter can change only slightly. That makes this pair a direct test of the limitation exposed by AOPS: a single `g` cannot encode the complete angular scattering function.

Reference:

- Koepke et al./Gasteiger et al. nonspherical mineral-particle OPAC technical note, *Atmospheric Chemistry and Physics* 15, 5947–5963 (2015): https://acp.copernicus.org/articles/15/5947/2015/

## Scalar-radiance boundary

The OPAC netCDF assets contain angular scattering information and phase-matrix data. This experiment does **not** introduce a new polarization endpoint. It keeps the existing scalar MYSTIC twilight-radiance calculation and tests the richer angular scattering function consumed by that scalar configuration. Claims must therefore be phrased as scalar-radiance/visibility sensitivity to the richer OPAC angular-scattering treatment, not as a validation of polarized radiative transfer.

## Frozen physical/numerical design

Everything outside the aerosol state is inherited unchanged from AOPS/R8:

- Sun depression: 2, 4, 6, 8 degrees;
- AOD550: 0.10, 0.30;
- geometries: near-solar 10° altitude / 30° relative azimuth, cross-solar 30° / 90°, opposite-solar 45° / 180°;
- observer elevation: 0 m;
- AFGL US atmosphere; its humidity profile is part of the frozen context because OPAC hygroscopic species can be humidity dependent;
- surface albedo: 0.15;
- 3 replicates;
- 20,000,000 photon histories per case;
- `reference-vroom-1nm` calculation, 380–780 nm, existing 0.05-nm serialized raw output contract;
- all five states in a CRN group share one fresh seed;
- all states, including the native bridge, must use the same exact augmented data tree so data-path/runtime identity is not confounded with aerosol state.

Thus: 24 analysis cells × 3 replicates × 5 states = **360 cases**, 72 CRN groups and 7.2 billion configured photon histories.

## Exact aerosol surfaces

Native bridge:

```text
aerosol_default
aerosol_haze 1
aerosol_vulcan 1
aerosol_season 1
aerosol_set_tau_at_wvl 550 <AOD550>
```

Each OPAC state:

```text
aerosol_default
aerosol_species_library OPAC
aerosol_species_file <mixture>
aerosol_set_tau_at_wvl 550 <AOD550>
```

No `aerosol_modify ssa` or `aerosol_modify gg` is permitted. Native Shettle directives and OPAC species directives may never be mixed in one case.

## Preregistered contrasts

For photopic luminance, scotopic luminance, Johnson-V effective radiance, and nodewise raw spectrum:

- continental-average versus native;
- maritime-clean versus native;
- desert versus native;
- desert-spheroids versus native;
- maritime-clean versus continental-average;
- desert versus continental-average;
- **desert-spheroids versus desert** — the priority particle-shape contrast.

Each scalar/spectral contrast is the replicate-paired natural-log ratio `ln(Y_alternative/Y_reference)`. Retain all three paired replicate values and report mean, sample SD and SE=SD/sqrt(3). No independent-error quadrature, p-values or confidence intervals.

The already-bound Level-B human-threshold model is a preregistered secondary endpoint. For the same seven contrasts, report alternative limiting-V magnitude minus reference limiting-V magnitude. No universal conversion to clock minutes is allowed.

Nonpositive/nonfinite required responses are `NUMERICALLY_UNRESOLVED`; no epsilon substitution and no dropping an unresolved replicate to summarize the remainder.

## What a future result may and may not establish

This experiment can establish sensitivity across the selected coherent OPAC states and can directly quantify the modeled spherical-versus-spheroidal dust effect over the frozen twilight surface. It cannot establish how frequently those states occur at a site, cannot infer a real observation's aerosol mixture without independent aerosol evidence, and cannot by itself validate same-atmosphere reality.

A later same-atmosphere validation still requires independent measured aerosol state/AOD/humidity provenance rather than fitting the aerosol state to the same sky or star-visibility observations being validated.

## Execution boundary

This preregistration creates **no candidate seeds** and no execution identity. Before any solver call, a later review must separately provide and freeze:

- executable analysis implementation matching the frozen analysis contract;
- exact adapter/executor/runtime-overlay reconstruction and refusal tests;
- 72 fresh CRN seeds under the new namespace plus repository-global freshness proof;
- fresh monotonic scientific ordinal;
- one-file Draft authorization review and separate dispatch;
- attempt-1-only execution with no GitHub rerun/retry/resume;
- result opening only after the exact 360-case universe and frozen aggregate succeed.

No post-result state replacement, adaptive case addition or contrast redesign is permitted inside v1.
