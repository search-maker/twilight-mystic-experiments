# Aerosol vertical-profile sensitivity v2 — replacement scientific preregistration

Status: **REVIEW ONLY / EXECUTION DISABLED / SEEDS UNALLOCATED / ORDINAL UNALLOCATED / RESULTS CLOSED**

## Why this is a new scientific identity

AVPS v1 scientific ordinal 40 completed its evidence pipeline but was scientifically non-informative because the state-specific `aerosol_file tau` files did not reach effective solver physics. It is permanently consumed and cannot be repaired in place, rerun, or reused under patched inputs.

AVPS v2 therefore receives a fresh stage/case/seed namespace. It preserves the original independently preregistered scientific question and screen, but replaces the defective transport representation with the four-species representation validated by PR #596.

No ordinal-40 result direction, magnitude, or Taylor/Jerusalem residual is used to select the v2 profiles, AODs, geometries, photon budget, endpoints, thresholds, or gates.

## Frozen predecessor evidence

- frozen main `99ade7798627e67921139697ba1a004fa8a304bb`
- original AVPS v1 protocol blob `5dddbac21e9ac395bd482d0d376577a6e5dd8bb0`
- original scientific review blob `a92152a3cd3ab01b940460ec40fb8e4f1952f504`
- original OPAC template generator blob `8e8175ae771438b91fc9543b329175c193a215a4`
- renderer validation PR #596 final head `8adfd4fafa4c039394d12e6f6aff1795b750f4d2`
- #596 renderer blob `99f61e1daa03cecef055a3773544574738d65082`
- #596 dedicated run `33193123594`, attempt 1 SUCCESS
- #596 repository contract `33193123597`, attempt 1 SUCCESS
- #596 artifact `9694613680`, digest `sha256:5e6942d879326ffc2dc8805d7649086cae32ad2e16aeec19a62cd3b0a89e3e27`
- #596 report content SHA `20f26c65ce1d01e4514ceea36f2c95ecbf421d05a805b0a3d23e58f1fc9dda24`
- #596 baseline explicit-vs-built-in normalized NULL layer-tau error: exactly zero

The validated simple common-scalar renderer passed all five states at AOD550 0.10 and 0.30. The preregistered 29x29 response-matrix fallback is therefore not selected.

## Scientific question — unchanged from v1

At fixed total AOD550 and fixed wavelength-dependent OPAC `continental_average` optical properties/phase function, how much does independently specified normalized aerosol vertical optical-depth shape change twilight radiance and derived Level-B limiting magnitude?

## Corrected fixed optical-family representation

Every case uses exactly:

```text
aerosol_default
aerosol_species_library OPAC
aerosol_species_file profiles/<state>.four-species.dat INSO WASO SOOT SUSO
aerosol_set_tau_at_wvl 550 <AOD550>
```

The staged runtime must expose the exact official byte-identical no-extension OPAC assets at:

- `data/aerosol/OPAC/optprop/INSO`
- `data/aerosol/OPAC/optprop/WASO`
- `data/aerosol/OPAC/optprop/SOOT`
- `data/aerosol/OPAC/optprop/SUSO`

The four-alias staged data-tree SHA is `5e1814dd36cf861fd85477a97607299248f8272268df7bf428d31bbb6aa4354a`.

`aerosol_file tau` is forbidden. INSO-only is forbidden. The synthetic equal-0.25 mixture used by #592 is forbidden as science.

## Exact five rendered profile bytes

The five states are the same independent OPAC Tables 3/5 vertical templates selected before ordinal 40. Their corrected four-species rendered files are now byte-bound:

- `opac-profile-continental-average`: `ceed598f7681951cd0e6208b267beb5b41a52ab10311f37ce76f925700caff3d`
- `opac-profile-maritime-clean`: `487b67bd7dbe89d12d032fdf2b33cab545e16a2e0697170648317f1a76362a67`
- `opac-profile-desert`: `2b4d2e03c6ae3143d9bb05d2da49f57f75172dc1f24d34f7d4a4939bf9952fef`
- `opac-profile-arctic`: `98f2fa5428c830764252fd0a2662b0f5c957fc027ffcb7bdc0a5e500dfd7d3d6`
- `opac-profile-antarctic`: `ee063c6dca68cf9a31d8bb9d993f1fed5cb34c8bb056ac180c97171b5d6b4f19`

A future science package must regenerate these exact bytes from the exact #596 renderer/runtime evidence and fail closed on any SHA drift.

## Frozen scientific screen — unchanged

- AFGL-US atmosphere
- observer elevation 0 m
- surface albedo 0.15
- 380–780 nm on the frozen 1-nm grid
- MYSTIC spherical 1D, VROOM, `mc_std`
- 20,000,000 photon histories per case
- Sun depression 2, 4, 6, 8 deg
- AOD550 0.10 and 0.30
- geometries: 10°/30° near-solar, 30°/90° cross-solar, 45°/180° opposite-solar
- three fresh CRN replicates
- five vertical states per CRN group
- 72 CRN groups, 360 cases

The 20M budget is deliberately preserved rather than adapted after ordinal-40 result opening.

## Fresh identity and seeds

Stage ID: `aerosol-vertical-profile-sensitivity-v2`.

All group IDs and case IDs must begin with `avps-v2-` and be disjoint from the v1/ordinal-40 case universe.

Future seed namespace, frozen now but **not evaluated or allocated in this review**:

`aerosol-vertical-profile-sensitivity-v2|group-seed|sha256-v1`

A later seed review must preserve the old safety properties — 72 unique signed-32-bit-compatible seeds, same fresh seed across all five states within each CRN group, repository-global collision scan — while deriving entirely new values from the v2 namespace/group IDs.

## Endpoints and reporting — unchanged

Primary sky channels:

- photopic luminance
- scotopic luminance
- Johnson-V effective radiance

Primary comparisons are paired log alternative/reference contrasts against `opac-profile-continental-average`. Retain all three CRN-paired replicate contrasts; report mean, sample SD and `SE=SD/sqrt(3)`. No p-values, confidence intervals, independent-error quadrature, epsilon substitution, adaptive case addition, or post-result gate changes.

Full spectra remain retained audit evidence only; no arbitrary full-spectrum production interpolation claim is created.

Secondary Level-B limiting-magnitude deltas remain separately downstream and cannot be used to select or alter this science design.

## Anti-fitting boundary

Forbidden:

- selecting/changing profiles from Taylor/Jerusalem residuals;
- changing H/Z/layer shares after results;
- changing AOD, geometry, optical family, renderer or thresholds after results;
- interpreting a best-matching vertical state as the actual Taylor atmosphere;
- converting sensitivity into a universal time correction;
- promoting Level-B or production from this preregistration.

## This PR does not authorize science

This review allocates:

- no scientific ordinal;
- no candidate or scientific seed;
- no authorization/dispatch branch;
- no solver run;
- no result opening.

After this exact tracked-tree preregistration and its repository contract pass, the next gates are: fresh v2 seed derivation + repository-global collision review, fresh Issue-60/branch ordinal audit, then a separate authorization review. Ordinal 41 is expected only if that later audit still finds 40 as latest consumed; it is not allocated here.
