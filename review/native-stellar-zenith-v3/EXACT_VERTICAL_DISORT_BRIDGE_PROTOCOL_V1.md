# Exact-vertical DISORT bridge protocol v1

## Purpose

The frozen SDISORT 2.0.6 executable cannot evaluate exact source zenith angle 0 deg (`umu0=1.0`). The preregistered epsilon-selection path has now returned `NO_SELECTION_UNDER_PREREGISTERED_PROTOCOL`; therefore no positive source zenith angle may be substituted for physical zenith.

This protocol tests a different numerical representation of the same physical direct-stellar problem: use plane-parallel DISORT only at **exact physical zenith**. For a vertical ray, atmospheric curvature does not change the geometric path through a horizontally stratified atmosphere, so the plane-parallel and spherical direct paths coincide. All non-zenith stellar transport remains on the existing SDISORT method unless a later separately gated method revision is validated.

## Frozen diagnostic universe

No protected stellar holdout is opened. The diagnostic uses only four atmosphere corners already used for the training-only epsilon diagnostic:

- observer elevation 0 m, AOD550 0.05
- observer elevation 0 m, AOD550 0.40
- observer elevation 2500 m, AOD550 0.05
- observer elevation 2500 m, AOD550 0.40

At every corner execute exactly five fresh direct-transmission spectra on the existing 380..780 nm / 1 nm grid:

1. `rte_solver disort`, SZA 0 deg
2. `rte_solver disort`, SZA 0.5 deg
3. `rte_solver disort`, SZA 1.0 deg
4. `rte_solver sdisort`, SZA 0.5 deg, `sdisort nscat 1`
5. `rte_solver sdisort`, SZA 1.0 deg, `sdisort nscat 1`

Total fresh solver calls: **20**.

All other atmospheric and spectral directives remain identical to the native stellar MYSTIC-STATE-0081 contract: AFGLUS, `mol_abs_param crs`, the same `atm_z_grid` site-elevation treatment, `zout 0`, surface albedo 0.15, `aerosol_default`, the requested AOD550, `output_quantity transmittance`, and `output_user lambda edir`.

## Direct-beam identities tested

For a plane-parallel direct beam with source-direction cosine `mu = cos(SZA)`, direct irradiance satisfies

`edir = mu * exp(-tau_vertical / mu)`

under the transmittance normalization. Therefore for the two nonzero DISORT diagnostic angles the independently reconstructed vertical optical depth is

`tau_vertical_reconstructed = -mu * ln(edir / mu)`.

At SZA 0, `mu=1`, so exact vertical optical depth is

`tau_vertical_exact = -ln(edir)`.

The diagnostic also compares SDISORT and DISORT at the same 0.5- and 1.0-degree SZAs. This does **not** use either positive SZA as a replacement for zenith; it is only a numerical/geometry bridge check near zenith.

## Frozen gates

Every one of the 20 fresh spectra must:

- return code 0;
- contain exactly 401 wavelength rows, 380 through 780 nm inclusive;
- have finite direct transmission strictly in `(0,1]` after the appropriate `edir/mu` normalization;
- preserve exact runtime/package/data/input identities.

Across all four atmosphere corners and both 0.5- and 1.0-degree comparison angles:

1. **Plane-parallel vertical reconstruction gate**: maximum absolute wavelength-by-wavelength difference between reconstructed DISORT vertical optical depth and exact `DISORT@0deg` vertical optical depth must be `<= 5e-6`.
2. **Near-zenith solver bridge spectral gate**: maximum absolute wavelength-by-wavelength difference in line-of-sight optical depth between SDISORT and DISORT at the same SZA must be `<= 5e-6`.
3. **Johnson-V photometric gate**: for frozen Pickles library numbers 1, 26, and 45, the maximum absolute difference in Johnson-V extinction magnitude for each of the two comparisons above must be `<= 1e-4 mag`.

These tolerances are frozen before solver execution. The spectral tolerance is deliberately far tighter than the eventual 0.025/0.010 mag stellar LUT acceptance gates while allowing for the seven-significant-digit text precision of the current `uvspec` spectral output. The photometric gate is the same strict scale used by the already-frozen epsilon-convergence protocol.

## Decision rule

The diagnostic returns `EXACT_VERTICAL_DISORT_BRIDGE_DIAGNOSTIC_PASS` only if every spectrum and every frozen gate passes. Otherwise it returns `..._FAIL` with the failing metrics preserved.

A PASS authorizes only drafting a separate v3.2 computational method in which:

- exact physical 90 deg uses `DISORT@SZA=0` for the direct stellar endpoint;
- all target altitudes below 90 deg retain the existing SDISORT method;
- the previously frozen 100 training coordinates, 64 protected holdout coordinates, Pickles/Johnson-V assets, interpolation coordinate, and 0.025/0.010 mag acceptance gates remain unchanged.

A PASS does **not** itself authorize opening the 64 protected holdouts, changing production code, claiming empirical real-sky validation, or claiming human first-seeing validation. Those require separately frozen steps.

A FAIL forbids use of this bridge and leaves the protected holdouts closed.
