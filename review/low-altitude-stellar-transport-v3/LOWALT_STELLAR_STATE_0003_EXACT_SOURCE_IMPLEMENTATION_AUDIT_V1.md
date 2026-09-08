# LOWALT-STELLAR-STATE-0003 — exact source/runtime implementation audit v1

Status: `POST_V1_NONBLOCKING / SOURCE_PROVENANCE_RESOLVED / SOLVER_FREE_IMPLEMENTATION_AUDIT`

This audit is isolated from V1 science. It does not lower the authoritative geometric target-altitude floor of `5.0 deg`, does not alter the `>=5.0 deg` v3.2 route, does not open protected results, and does not use Taylor/Jerusalem or LOWALT-STELLAR-STATE-0001 residuals as design input.

## 1. Exact source representation is now recovered

The feedstock source URL is literally:

`http://www.libradtran.org/download/libRadtran-2.0.6.tar.gz`

The fresh result-blind provenance probe on PR #989 used that literal HTTP URL without HTTPS substitution and recorded no redirect. The HTTP entity had `Content-Encoding: x-gzip`, wire size `154147176`, and wire SHA-256:

`64930cc40b6e4a37aa220520974d330fc1563796f466a649b2238131f2d69840`

Decoding that exact wire entity according to HTTP `x-gzip` semantics produced `284387328` bytes with SHA-256:

`999e47f4af4b5df6f85a6887fc105fc8f6e1a7cee89a3124f69ac8d8912c8e85`

which is exactly the source SHA frozen in the successful conda-forge build recipe. The decoded object is a POSIX tar archive rooted at `libRadtran-2.0.6/`.

This resolves the prior apparent `64930...` versus `999e47...` conflict: the former is the HTTP wire representation and the latter is the HTTP-content-decoded representation that conda hashes.

The exact downloader chain is independently source-bound:

- conda `26.1.1`, commit `a0b1779edb6df26600b9aa6f2bc9d466f512b0ed`, writes `Response.iter_content()` chunks to the checksum target;
- Requests `2.32.5`, commit `b25c87d7cb8d6a18a37fa12442b5f883f9e41741`, requests urllib3 streaming with `decode_content=True`;
- urllib3 `2.6.3`, commit `0248277dd7ac0239204889ca991353ad3e3a1ddc`, explicitly treats `x-gzip` as gzip.

Therefore `SOURCE_EQUIVALENT_999=PASS` for the exact source representation. This is a provenance transition only; it is not a scientific transition and does not authorize <5 deg production support.

## 2. Exact runtime binding

The already-recovered unexpired package provenance artifact binds:

- package: `rubin-libradtran-2.0.6-py312pl5321he9373c2_1.conda`;
- package SHA-256: `9090033a39a7e963ecabb31d5cbd264330c64ec1c4cb5f44be2e70f10cbc54c2`;
- installed and packaged `bin/uvspec` SHA-256: `2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3`.

The exact recovered 999 source tree contains the following audited files:

| Source path | SHA-256 |
| --- | --- |
| `src/uvspec_lex.l` | `174755190e50ecc3099c80a29cb71627c0a33a5e2009d1869c23140095658d89` |
| `src/atmosphere.c` | `b900ade7e603260a47fec3efa305577ab6806bbf539021ec028a0c1360099cf8` |
| `src/aerosol.c` | `14843b11440764608ac655226fbe49496da820d76151f9a543a910a445cb5c40` |
| `src/ancillary.c` | `97dc576d1cb8f54c40d733cea3d5a56b49a0e7f8f39aa812e55ba7fbe1a7665f` |
| `src/solve_rte.c` | `c90ed56c331758c71f89397c714cf1cab476dac9e5500ba1ebed0b60b6ad7475` |
| `libsrc_f/dpsdisort.f` | `54448cc9358d32c5be30b5c860006ff0ed05484a58cf3417f05fbc4b6a5efd66` |
| `libsrc_f/dpmisc.f` | `e0d8975408ead1d6fe0c9630c0b2e5a858868334ba6af179d9f94c063955324e` |

## 3. Frozen application input surface

The authoritative LOWALT-STELLAR-STATE-0002 direct renderer already fixes the relevant input semantics:

- AFGLUS atmosphere;
- `source solar`;
- `mol_abs_param crs`;
- 380–780 nm, exact 1 nm wavelength grid;
- `sza = 90 deg - h_geo`;
- `atm_z_grid` begins at the geometric observer elevation and retains all atmosphere levels above it;
- `zout 0`;
- albedo `0.15`;
- `aerosol_default` plus `aerosol_set_tau_at_wvl 550 <AOD550>`;
- `rte_solver sdisort`;
- `sdisort nscat 1`;
- `output_quantity transmittance`;
- `output_user lambda edir`;
- no `nrefrac`, refraction, or `altitude` directive.

The existing parser defines `mu0 = sin(h_geo)` and `T_los = edir / mu0`; `T_los <= 0`, nonfinite values, or invalid output are `NUMERICALLY_UNRESOLVED`. Positive-epsilon substitution is forbidden.

## 4. Source-equivalence checklist resolution

### 4.1 `EARTH_RADIUS_CONVENTION = PASS`

The recovered `src/uvspec_lex.l` initializes `Input.r_earth = 6370.0` km. `src/solve_rte.c` passes `input.r_earth` into SDISORT. The evaluator must therefore use exactly `6370.0 km` for this identity, not an unrelated Earth-radius macro from another subsystem.

### 4.2 `GEOMETRIC_ANGLE_CONVENTION = PASS`

`src/solve_rte.c` sets `umu0 = cos(sza*pi/180)`. The frozen stellar renderer sets `sza = 90 deg - h_geo`, hence exactly `mu0 = sin(h_geo)` for this path. Refraction is not enabled; the target altitude is topocentric vacuum/geometric.

### 4.3 `LAYER_RADIUS_CONVENTION = PASS`

`atm_z_grid` is accepted from the user in ascending physical altitude but is stored internally in descending atmospheric order. `setup_altitude()` replaces the atmospheric grid with that forced grid. SDISORT's `GEOFAST` reverses the internal descending `zd` array back to an increasing altitude vector, converts altitude km to cm, and uses concentric radii `R_earth + z`.

Thus shell boundaries for the direct-path evaluator are exactly the post-`atm_z_grid` atmospheric levels above the observer, with `R_earth = 6370.0 km`.

### 4.4 `SITE_ALTITUDE_TRUNCATION = PASS`

In `setup_altitude()` the final element of the internal forced descending grid becomes `output->alt.altitude`; atmospheric pressure, temperature, and gas-density profiles are interpolated to the forced grid and the atmosphere is replaced by that grid. For the frozen renderer this bottom level is the observer elevation. The evaluator must consume the already-truncated/regridded column; it must not apply an additional altitude truncation.

### 4.5 `AEROSOL_REBASING_AND_AOD_SCALING = PASS`

For default Shettle aerosol, `src/aerosol.c` uses altitude relative to `output->alt.altitude` unless the explicit MODTRAN-profile mode is selected. Under the frozen forced-grid path, aerosol therefore starts at/rebases to the observer surface. `aerosol_set_tau_at_wvl 550` scales the retained aerosol column above that surface. No separate sea-level aerosol column may be reintroduced by the evaluator.

### 4.6 `SPECTRAL_EXTINCTION_ASSEMBLY = PASS`

In `src/ancillary.c`, per-layer total extinction `output->dtauc[lc]` is assembled as total absorption plus total scattering. For the frozen no-cloud `mol_abs_param crs + aerosol_default` path this includes molecular absorption, Rayleigh scattering, and aerosol absorption/scattering at the current wavelength. The exact-direct evaluator must integrate this unscaled total layer extinction; it must not reconstruct extinction from a fitted broadband coefficient.

### 4.7 `DELTA_M_DIRECT_BEAM_SEMANTICS = PASS`

The source defaults `deltam=on` and `nstr=6`. SDISORT computes delta-M-scaled `DTAUCPR` for diffuse/source calculations, but the returned direct-flux quantity `RFLDIR` is explicitly evaluated with unscaled user optical depth `UTAU`:

`RFLDIR = abs(UMU0) * FBEAM * exp(-UTAU / CH)`.

The frozen `edir` parser divides by `mu0`. Therefore the stellar line-of-sight direct transmission oracle is based on **unscaled total extinction optical depth**, not `DTAUCPR`. Phase moments and delta-M truncation are not inputs to the final direct `edir/mu0` attenuation identity.

### 4.8 `CHAPMAN_GEOMETRY_AND_LAYER_RULE = PASS_WITH_EXACT_SDIRECT_RULE`

For SDISORT the initialization sets spherical geometry on. With `nrefrac=0`, `dpssetdis` calls `GEOFAST`, which computes geometric `ds/dh` factors for concentric spherical layers. `chpman2` forms Chapman optical paths by summing these factors times per-layer optical depths, including a second leg after a tangent point when applicable.

For the direct output actually consumed by the stellar executor, the exact source rule is not merely a generic continuous Chapman integral: SDISORT computes the per-layer effective `CH` using midpoint geometry (`z_lay=0.5`) and unscaled `DTAUC`, then evaluates `RFLDIR` from `UTAU/CH` at each user output level. STATE-0003 must reproduce this exact discrete SDISORT direct-output rule before claiming executable equivalence. A mathematically cleaner shell integral is only a diagnostic until shown equivalent to this source rule.

### 4.9 `TOA_TERMINATION = PASS`

`points_of_incidence_fast()` defines the top of atmosphere as `R_earth + Z(nlyr)`, i.e. the top level of the post-forced atmosphere. `opathfast()` creates an auxiliary 3 km geometry-only segment above the atmosphere when tracing the ray after a tangent point, but stores optical `ds/dh` contributions only for actual modeled atmospheric layers (`k < nlyr`). Therefore there is no extinction extrapolation above the model TOA.

### 4.10 `GROUND_OCCULTATION = PASS`

In `opathfast()`, for SZA > 90 deg a tangent point below Earth surface marks the target and all lower levels unreachable (`nfac=-1`). This is a hard geometry/occultation boundary, not a transmission epsilon.

### 4.11 `FLOAT_UNDERFLOW_SEMANTICS = PASS`

The source direct term uses ordinary `exp(-...)`; sufficiently large optical depth may therefore underflow to zero. The existing LOWALT parser classifies nonfinite or nonpositive transmission as `NUMERICALLY_UNRESOLVED` and forbids epsilon substitution. STATE-0003 must preserve that behavior exactly.

### 4.12 `OUTPUT_QUANTITY_SEMANTICS = PASS`

The authoritative stellar executor requests `output_user lambda edir`; the parser divides returned `edir` by `mu0=sin(h_geo)` to recover line-of-sight direct transmission and stores `-ln(T_los)` only for finite positive transmission. The exact-direct evaluator must target this quantity, not diffuse flux, global flux, or an internal delta-M-scaled beam variable.

### 4.13 `NULL_PREPROCESS_EQUIVALENCE = PASS_FOR_FROZEN_OPTICAL_PROPERTIES`

`setup_and_call_solver()` calls `optical_properties()` before the solver dispatch. `SOLVER_NULL` later does nothing in `call_solver()`. For the frozen no-cloud CRS + default-aerosol path, the ordinary `output->dtauc` assembly is therefore the same preprocessing code path used before SDISORT. Solver-specific density-matrix/phase-function branches are not part of the frozen direct-extinction quantity.

This establishes preprocessing equivalence for the needed `dtauc` values, but **not serializer equivalence**.

### 4.14 `STOCK_DTauc_SERIALIZATION = NOT_PASS / NAMED ENGINEERING BLOCKER`

The stock `write_optical_properties` path switches to `SOLVER_NULL` only after optical properties have been computed, but its stock output surface does not provide a precision-preserving serializer for `output->dtauc` under this SDISORT/NULL configuration. Verbose text is not an exact numerical interface.

The next exact-direct implementation step is therefore a narrow source-instrumentation/reference extractor compiled from the recovered 999 tree that serializes the already-computed `output->dtauc` immediately after `optical_properties()` without changing the optical calculations. That extractor is a reference/training instrument only; it is not production routing and may not mutate the >=5 deg V1 path.

## 5. Exact-direct evaluator implementation target

The candidate evaluator must be split into two layers:

1. **optical-property reference layer** — obtain exact wavelength/layer `dtauc` and final post-forced altitude boundaries using the recovered 999 preprocessing; and
2. **direct geometry layer** — reproduce the exact SDISORT `GEOFAST/chpman2/CH/RFLDIR` rule with `R=6370 km`, `nrefrac=0`, the post-forced layer grid, no extinction above TOA, hard ground occultation, and fail-closed underflow.

Only after the source-instrumented reference agrees on the separately frozen fresh nonprotected matrix may an optimized closed-form/shell implementation be accepted as equivalent. No tolerance, support floor, knot set, or formula choice may be selected from protected residuals.

## 6. Current gate state

- `SOURCE_EQUIVALENT_999 = PASS`
- `PACKAGE_UVSPEC_IDENTITY = PASS`
- `EARTH_RADIUS_CONVENTION = PASS`
- `GEOMETRIC_ANGLE_CONVENTION = PASS`
- `LAYER_RADIUS_CONVENTION = PASS`
- `SITE_ALTITUDE_TRUNCATION = PASS`
- `AEROSOL_REBASING_AND_AOD_SCALING = PASS`
- `SPECTRAL_EXTINCTION_ASSEMBLY = PASS`
- `DELTA_M_DIRECT_BEAM_SEMANTICS = PASS`
- `CHAPMAN_GEOMETRY_AND_LAYER_RULE = PASS_WITH_EXACT_SDIRECT_RULE`
- `TOA_TERMINATION = PASS`
- `GROUND_OCCULTATION = PASS`
- `FLOAT_UNDERFLOW_SEMANTICS = PASS`
- `OUTPUT_QUANTITY_SEMANTICS = PASS`
- `NULL_PREPROCESS_EQUIVALENCE = PASS_FOR_FROZEN_OPTICAL_PROPERTIES`
- `STOCK_DTauc_SERIALIZATION = NOT_PASS`
- `FRESH_NONPROTECTED_SOURCE_EQUIVALENCE_MATRIX = FROZEN_SEPARATELY / NOT_EXECUTED`
- `LOWALT_PRODUCTION_SUPPORT = NOT_AUTHORIZED`
- authoritative V1 stellar transport remains `>=5.0 deg`; `<5.0 deg` remains fail-closed in production.
