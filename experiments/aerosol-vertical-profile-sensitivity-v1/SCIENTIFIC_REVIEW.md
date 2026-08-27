# Aerosol vertical-profile sensitivity v1 — scientific preregistration review

Status: **REVIEW ONLY — EXECUTION DISABLED — RESULTS NOT OPENED**

## Scientific question

At fixed total AOD550 and fixed wavelength-dependent OPAC `continental_average` optical properties/phase function, how much does independently specified normalized aerosol vertical optical-depth shape change twilight radiance and derived Level-B limiting magnitude?

This is deliberately narrower than “which aerosol model is right for Taylor/Jerusalem?” It is a controlled sensitivity experiment intended to quantify whether vertical structure deserves an explicit fast-model dimension/envelope at all.

## What is already closed and must not be repeated

- AOPS / ordinal 37 already tested controlled SSA and scalar-g sensitivity.
- AFPF / ordinal 38 already tested coherent OPAC full phase-function/aerosol-family sensitivity.
- ASIV / ordinal 39 already validated the current scalar + derived-Level-B aerosol scenario interpolation on a fresh holdout.
- `starsvisibility` PR #100 already integrated the five-state Tier-0 aerosol scenario envelope in shadow-only form.
- `twilight-mystic-experiments` #549 merged generic solver-free vertical-profile transport mechanics.
- #550 proved the exact locked OPAC runtime accepts the intended composition `OPAC rich optics + custom aerosol_file tau + fixed AOD550` under `uvspec -c`.

Therefore this stage varies **only vertical optical-depth distribution**.

## Independent profile source

The vertical templates are frozen from:

Michael Hess, Peter Koepke & Ingo Schult (1998), “Optical Properties of Aerosols and Clouds: The Software Package OPAC”, *Bulletin of the American Meteorological Society*, 79(5), 831–844. DOI: `10.1175/1520-0477(1998)079<0831:OPOAAC>2.0.CO;2`.

Relevant source facts:

- OPAC represents aerosol height dependence by exponential profiles `N(h)=N(0) exp(-h/Z)`.
- Table 3 gives standard 550-nm optical depths. The free-troposphere background contributes `0.013`; the stratospheric background contributes `0.005`.
- Table 5 gives first-layer top `H` and scale height `Z` for standard aerosol types.
- The free troposphere extends to 12 km with scale height 8 km.
- The stratospheric background extends from 12 to 35 km and uses the OPAC homogeneous-layer convention (`Z=99 km`).

The five selected source templates deliberately span documented standard OPAC vertical regimes without consulting Taylor/Jerusalem residuals:

| state | source total tau550 | first-layer H | first-layer Z | derived first-layer tau550 |
|---|---:|---:|---:|---:|
| Continental average | 0.151 | 2 km | 8 km | 0.133 |
| Maritime clean | 0.096 | 2 km | 1 km | 0.078 |
| Desert | 0.286 | 6 km | 2 km | 0.268 |
| Arctic | 0.063 | 2 km | 99 km | 0.045 |
| Antarctic | 0.072 | 10 km | 8 km | 0.054 |

For every state, `first-layer tau = source total tau - 0.013 - 0.005`.

The source-state absolute tau values are used **only to derive relative vertical layer shares**. Each assembled profile is renormalized to unit column optical-depth fractions and the scientific cases then impose exactly `AOD550=0.10` or `0.30`. Thus total AOD is not changing between vertical states.

## Deliberate optical-family cross-combination

All five vertical templates use the same OPAC `continental_average` spectral/phase optical family in the solver.

That means the “maritime/desert/arctic/antarctic” labels describe only the **source vertical template**, not the actual aerosol microphysics in that run. This cross-combination is intentional because changing vertical template and aerosol optical family simultaneously would not isolate vertical structure.

No claim is made that continental-average particles physically have an Antarctic or desert climatological height profile at a real observing site.

## Profile construction

For a source state with first-layer top `H`, scale height `Z`, and first-layer optical-depth share `tau1`:

1. distribute `tau1` over `0..H` proportional to `exp(-h/Z)`;
2. distribute `0.013` over `H..12 km` proportional to `exp(-h/8 km)`;
3. distribute `0.005` over `12..35 km` proportional to `exp(-h/99 km)`;
4. set aerosol tau above 35 km to zero in this controlled template;
5. integrate analytically onto the exact AFGL-US layer grid;
6. normalize all layer optical-depth values to sum to one;
7. render with the merged lower-bound `aerosol_file tau` convention;
8. impose case AOD separately with `aerosol_set_tau_at_wvl 550`.

The source construction is exact with respect to the frozen Table-3/Table-5 numbers; no interpolation or fit to project observations is involved.

## Fixed numerical design

Reuse AOPS/AFPF screen geometry rather than inventing a new target-driven design:

- atmosphere: AFGL-US;
- observer elevation: 0 m only in v1;
- surface albedo: 0.15;
- spectrum: 380–780 nm on the reviewed 1-nm calculation grid;
- MYSTIC spherical 1D + VROOM + MC standard-deviation evidence;
- 20,000,000 photons per case (subject only to pre-seed review; no post-result change);
- Sun depression: 2, 4, 6, 8 deg;
- AOD550: 0.10, 0.30;
- geometries: 10°/30° near-solar, 30°/90° cross-solar, 45°/180° opposite-solar;
- three fresh CRN replicates;
- five vertical states in every CRN group.

Cardinality if later authorized: 72 CRN groups × 5 states = 360 MYSTIC cases.

No seed or scientific ordinal is allocated in this preregistration.

## Why sea level only in v1

Observer elevation changes which part of a vertical aerosol column remains above the observer, creating a profile × elevation interaction. Mixing that interaction into the first vertical-shape screen would obscure the primary question and double the design.

The v1 experiment therefore freezes sea level. If vertical shape is materially important, an elevated-observer interaction must be a separate preregistered experiment using the same frozen vertical states; it may not be added adaptively to this run after results are seen.

## Endpoints

Primary sky endpoints:

- photopic luminance;
- scotopic luminance;
- Johnson-V effective radiance.

Full raw spectral evidence is retained for audit, but this stage makes no full-spectrum production interpolation claim.

Secondary endpoint:

- paired Level-B limiting-magnitude delta through the current Crumey Eq.34 threshold path with `F=3.14`.

No universal minute conversion is allowed.

## Statistical/numerical reporting

For each reference contrast and CRN replicate retain the paired log response. Report:

- all three replicate contrasts;
- mean;
- sample SD;
- SE = SD / sqrt(3).

No p-values, confidence intervals, independent-error quadrature, epsilon substitutions or post-result adaptive cases.

A nonpositive/nonfinite required response is `NUMERICALLY_UNRESOLVED`.

This sensitivity stage does not create a new production materiality threshold. Whether a vertical-profile mapper is warranted is a separate post-analysis design decision and must not mutate this experiment’s cases or reported results.

## Anti-fitting boundary

Forbidden:

- choosing these five profiles because one matches Taylor;
- modifying H/Z/layer optical-depth shares after seeing results;
- changing AOD or the fixed OPAC optical family after seeing results;
- interpreting the best-fitting profile as Taylor’s actual atmosphere;
- turning a sensitivity delta into a universal correction;
- claiming Level-B production validation from this MYSTIC-only screen.

## Required next gate before any science

Before solver execution, a separate authorization review must:

1. hash-bind the exact template generator, generic transport module, OPAC adapter/runtime and protocol;
2. verify all 360 case cards/directive surfaces without executing the scientific solver;
3. independently review whether the existing 20M photon budget remains appropriate;
4. allocate 72 fresh CRN group seeds under the frozen namespace and prove global non-collision;
5. allocate a fresh scientific ordinal;
6. keep the science authorization PR Draft/open/unmerged during execution;
7. open results only after exact aggregate/cardinality success.
