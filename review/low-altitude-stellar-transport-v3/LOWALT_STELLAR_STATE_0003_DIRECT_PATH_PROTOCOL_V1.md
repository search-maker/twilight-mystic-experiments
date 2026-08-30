# LOWALT-STELLAR-STATE-0003 — exact-direct-path source audit protocol v1

Status: `POST_V1_NONBLOCKING / RESULT_BLIND / SOLVER_FREE_REVIEW_ONLY`

Authoritative freeze: Issue #60 comment `5471304029`.
Prior terminal capability/runtime result: Issue #60 comment `5471297491`.

## Inherited boundary

- The validated stellar transport seam at geometric target altitude `>= 5 deg` remains MYSTIC-STATE-0081/v3.2 and is not modified here.
- LOWALT-STELLAR-STATE-0001 protected residuals are opened failure evidence and are forbidden as design input.
- LOWALT-STELLAR-STATE-0002 established only that deterministic pseudo-spherical `sdisort` is numerically representable on its fresh tested matrix through `0.30 deg`, and that per-sample invocation is too slow for the present synchronous application budget. Its detailed spectral values are not an accuracy-tuning target here.
- Exact horizon `0 deg` is not supported or assumed.
- Radiative transfer consumes topocentric vacuum/geometric altitude. Apparent/refracted altitude is a separate observational transform. STATE-0003 keeps `sdisort nrefrac 0` semantics and may not double-apply refraction.

## A-priori physical basis

The libRadtran 2.0.6 User Guide, Sec. 2.3.2, defines the pseudo-spherical direct path by replacing the plane-parallel `tau/mu0` term with the spherical Chapman extinction integral

`ch(r0, mu0) = integral[r0..infinity] beta_ext(r,nu) dr / sqrt(1 - ((R+r0)/(R+r))^2 (1-mu0^2))`

and the direct beam as `I_dir = I0 * exp(-ch)`. The same guide states that `rte_solver null` performs optical-property setup without solving the RTE, and documents that the `altitude` option moves the model bottom and truncates the molecular/cloud profiles while default aerosol starts at the model surface.

Authoritative documentation URL: `https://www.libradtran.org/doc/libRadtran.pdf`.

These statements justify auditing a direct-only spherical optical-path evaluator as a scientifically distinct route. They do **not** prove that the prototype below is source-equivalent to the pinned executable.

## Frozen question

Can we reproduce the direct stellar attenuation of the pinned `rubin-libradtran=2.0.6=py312pl5321he9373c2_1`, `rte_solver sdisort`, `sdisort nscat 1`, `nrefrac 0` path by:

1. obtaining the *same* wavelength- and layer-resolved extinction optical properties without the discrete-ordinates solve, and
2. integrating those properties along the same spherical straight ray,

with enough speed for eventual low-altitude application consumption?

If the optical-property preprocessing or Chapman discretization cannot be traced and reproduced, STATE-0003 fails closed. No fitted surrogate is substituted under this identity.

## Source-equivalence checklist — unresolved until traced

Every item is initially `UNRESOLVED`; no scientific equivalence run is authorized until a reviewed artifact resolves or explicitly fail-closes it.

1. `EARTH_RADIUS_CONVENTION`: exact radius/constants used by pinned sdisort.
2. `GEOMETRIC_ANGLE_CONVENTION`: verify `mu0 = cos(SZA) = sin(h_geo)` for the direct stellar mapping.
3. `LAYER_RADIUS_CONVENTION`: exact relationship between libRadtran altitude levels and radial shell boundaries.
4. `CHAPMAN_LAYER_RULE`: interpolation/integration rule for extinction within each layer.
5. `TOA_TERMINATION`: exact top-of-atmosphere boundary and any extrapolation behavior.
6. `SITE_ALTITUDE_TRUNCATION`: exact molecular/cloud truncation and aerosol rebasing semantics for observer elevation.
7. `SPECTRAL_EXTINCTION_ASSEMBLY`: molecular absorption + Rayleigh + aerosol extinction preprocessing on the frozen 380–780 nm grid.
8. `NULL_PREPROCESS_EQUIVALENCE`: prove whether `rte_solver null` uses the same relevant optical-property preprocessing as sdisort for these inputs.
9. `FLOAT_UNDERFLOW_SEMANTICS`: exact fail-closed boundary for nonfinite or zero transmission; no epsilon substitution.
10. `OUTPUT_QUANTITY_SEMANTICS`: prove which sdisort output quantity is the direct transmission oracle used by the existing stellar executor.

## Prototype scope

`lowalt_state_0003_spherical_path.py` implements only the exact Euclidean path length through concentric, piecewise-constant radial extinction shells. For observer radius `r0`, geometric altitude `h>0`, and impact parameter `b=r0*cos(h)`, path length across a shell `[r_lo,r_hi]` above the observer is

`ds = sqrt(r_hi^2-b^2) - sqrt(r_lo^2-b^2)`.

For a shell with vertical optical depth `tau_v` and thickness `dr`, the prototype contribution is `tau_v * ds/dr`.

This is a mathematical geometry primitive, not yet a claim about how sdisort discretizes `beta_ext`. It deliberately refuses `h<=0`, non-monotone layers, negative/nonfinite optical depth, an observer outside the first retained shell, and nonfinite outputs.

## Pre-science review gates

A solver-free review must prove:

- no subprocess/uvspec execution in the prototype;
- no STATE-0001 protected residual values or locations appear;
- no Taylor/Jerusalem/halachic first-seeing targets appear;
- exact 5 deg remains an inherited seam only, not a training target selected from old residuals;
- 0 deg remains refused;
- vertical-ray identity holds (`h=90 deg`: slant tau equals sum of vertical layer tau);
- shell splitting invariance holds for equal extinction coefficient;
- path length is finite/positive for representative positive altitudes;
- transmission refuses underflow instead of replacing it by epsilon.

## Later fresh evidence sequence

Only after the source-equivalence checklist is reviewed may a new nonprotected equivalence/training matrix be frozen. Its coordinates must be fresh and disjoint from opened protected evidence. Model/routing decisions may use that nonprotected set. A wholly fresh unopened protected final matrix must then be frozen before any production support decision. Exact 5 deg seam continuity, multiple observer elevations/AOD states, and fail-closed minimum support remain mandatory.

No protected matrix, support floor, interpolation knot set, formula tolerance, or application routing threshold is selected by this protocol.
