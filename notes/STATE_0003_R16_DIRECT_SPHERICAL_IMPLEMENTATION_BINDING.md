# STATE-0003 R16 — exact direct spherical implementation binding

Scope: POST_V1_NONBLOCKING, wholly NONPROTECTED. This document binds the fast exact/near-exact stellar direct-path evaluator to the pinned libRadtran 2.0.6 source/runtime semantics. It does not authorize production below 5.0 deg and does not claim general NULL-vs-SDISORT equivalence.

## Provenance anchor

- Governing source entity SHA-256: `999e47f4af4b5df6f85a6887fc105fc8f6e1a7cee89a3124f69ac8d8912c8e85`.
- The literal feedstock route is `http://www.libradtran.org/download/libRadtran-2.0.6.tar.gz`.
- Pinned inherited `uvspec` SHA-256: `2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3`.
- R15 independently reproduced the installed `libRadtran_f.a:dpmisc.o` byte-for-byte with the exact conda-forge GCC/GFortran 13.4.0-18 toolchain. Governing/rebuilt object SHA-256: `8ec028a406ac0fea7456d039f144b0edc8e91752d0a0fe9912e0a0fff06fdb1b`.

## Earth radius and vertical geometry

The uvspec input default is `r_earth = 6370.0` km. The actual evaluator interface must consume the `radius` value in the final SDISORT handoff rather than hard-code a different astronomical radius. `GEOFAST` requires `radius` and `ZD` in the same units (km at the Fortran interface), then converts both geometry scales internally to cm.

For `NLYR` atmospheric layers, `ZD(0:NLYR)` is the layer-boundary geometry. In `GEOFAST`, `ZD(lc)` is documented as distance from the bottom surface to the top of layer `lc`, with `ZD(NLYR)=0.0 km`. The routine reverses the vector into increasing altitude as `VZ(i)=ZD(NLYR-i)*1e5` cm. The layer sampling position is governed by `z_lay`: `0.0` bottom, `0.5` midpoint, `1.0` top.

The direct evaluator must therefore use the exact final handoff `NLYR`, `ZD`, `radius`, `VN`, `NREFRAC`, `NEWGEO`, `SPHER`, and `ICHAP` values; it must not rebuild a nominal atmosphere from a separate altitude grid.

## Spherical ray path and top-of-atmosphere termination

`GEOFAST` calls `opathfast`, which computes per-layer geometric path factors before and, where applicable, after the tangent point. `points_of_incidence_fast` defines the top-of-atmosphere sphere as `REA = Re + Z(NLYR)` and analytically finds the ray intersection with that sphere. If the quadratic has no positive intersection it returns `ca=-1`; otherwise the ray begins at the top-of-atmosphere incidence point.

`optical_path_fast` computes the physical path through each crossed layer and cuts a ray when it meets the looking/scattering direction. The source contains explicit metre-scale numerical tolerances for that geometric closure. Those semantics are part of the governing path and should be preserved rather than replaced by an empirical airmass interpolation.

## Chapman assembly — no empirical wavelength interpolation

For the ordinary `BROSZA=0` path used by the current stellar gate and with spherical geometry enabled:

1. `z_lay=0.0`: `GEOFAST` (or `GEOFACPR` for the slow high-refraction branch) computes the first geometric factors.
2. `CHPMAN2(..., DTAUCPR, ...)` forms `CHP1` from the delta-M-scaled layer optical depths.
3. `z_lay=0.5`: geometry is computed again for the midpoint path.
4. `CHPMAN2(..., DTAUC, ...)` forms `CHP2` from the ordinary layer optical depths.
5. For each layer, `TAUP = TAUC(lc-1) + DTAUC(lc)/2`, `CHTAU(lc)=CHP1(lc)`, and `CH(lc)=TAUP/CHP2(lc)`.

`CHPMAN2` is a direct sum over crossed layers: before the tangent point it accumulates `FAC(lc,j)*DTAUC(j)`; after the tangent point it adds the corresponding `FAC_2*DTAUC` terms. If no pre-tangent path exists and `zenang>90 deg`, the source uses `CHP=1e20`. The geometric FAC/NFAC structures are wavelength-independent for fixed geometry/refraction, but wavelength dependence enters exactly through the per-wavelength `DTAUC`/`DTAUCPR`; no compact empirical interpolation is governing.

If `ICHAP=0`, the source explicitly overrides the spherical Chapman result with plane-parallel `CH=UMU0`. STATE-0003 therefore must fail closed unless the handoff shows the intended spherical branch (`SPHER` true and `ICHAP` governing the Chapman path); it must not silently substitute one branch for the other.

## Wavelength optical-depth assembly and aerosols

The direct evaluator boundary is the final SDISORT pre-dispatch handoff. It consumes the already assembled per-wavelength layer quantities, especially `DTAUC`, `SSALB`, `DTAUC_MD`/related scaled optical-depth state, `UTAU`, `FBEAM`, and `UMU0`, together with the exact geometry arrays.

Aerosol, molecular, and gaseous contributions are therefore inherited from the common upstream libRadtran preprocessing that produced the final `DTAUC`/`SSALB`. STATE-0003 must not independently reconstruct aerosol extinction from a raw aerosol profile. This also preserves the exact wavelength assembly used by the pinned runtime.

## Observer altitude / profile truncation

Observer/output placement is inherited from the final handoff rather than re-derived. The governing layer set is the supplied `NLYR`/`ZD`/`DTAUC`; output optical depth is supplied as `UTAU`, and `LAYRU` locates each output level inside the final optical-depth mesh. Any upstream observer-altitude or aerosol-profile truncation is consequently carried into the evaluator by those final arrays. A separate replacement truncation rule is not authorized by this binding unless independently proven equivalent.

## Delta-M and direct attenuation

When delta-M is disabled, `DTAUCPR=DTAUC` and `TAUCPR=TAUC`. When it is enabled, the source constructs `TAUCPR`/`DTAUCPR` from the truncation moment and single-scattering albedo. User output optical depth is similarly mapped to `UTAUPR` for the transformed diffuse/direct bookkeeping.

The reflected/direct unscaled beam output is nevertheless computed from the ordinary user optical depth and spherical `CH`:

`RFLDIR(LU) = abs(UMU0) * FBEAM * exp(-UTAU(LU) / CH(LAYRU(LU)))`.

The Fortran single-precision wrapper promotes its REAL*4 inputs to REAL*8, calls `dpsdisort`, then rounds `DPRFLDIR` back to REAL*4 only at the outer return. Any strict equivalence gate therefore should capture/compare `CHP2`, `CH`, and pre-REAL4 `DPRFLDIR`, not infer internal equality from the final float32 value alone.

## Absorption cutoff and underflow semantics

`ABSCUT` is exactly `400.D0`. `LYRCUT` becomes true only when accumulated absorption optical depth reaches/exceeds 400, thermal emission is off (`NOPLNK`), and `NLYR>1`; output levels below the computational cutoff are then zeroed. Otherwise the direct beam uses ordinary double-precision `DEXP` with no additional empirical underflow clamp. Exact-zero behavior from `FBEAM<=0`, layer cutoff, or floating-point underflow must be preserved.

## NULL vs SDISORT preprocessing

General NULL-vs-SDISORT preprocessing equivalence is **NOT ASSUMED and NOT YET PROVEN**. The governing STATE-0003 interface is the actual final SDISORT pre-dispatch handoff. A NULL-produced handoff may be used only after a separate named equivalence proves that all direct-path-relevant fields are identical under the tested configuration.

## Fresh nonprotected continuation gate

R16 freezes ten wholly fresh identities: eight development rows and two audit rows. The audit rows must remain unopened until all eight development rows pass the frozen contract. R12 development identities `0001/0002` are consumed and forbidden to rerun/reuse; R12 audit `0007/0008` remains sealed. No protected residual, Taylor/Jerusalem fit, or post-result retuning may influence formula, grid, tolerance, or support floor.

Production remains unchanged: geometric target altitude below 5.0 deg is fail-closed.
