# Low-altitude stellar transport protocol v1 — pre-execution freeze

Status: **FROZEN BEFORE ANY TARGET-ALTITUDE <5 DEG SOLVER RESULT**

Lane: target/star geometric altitude above the local geometric horizon. This is not observer-site elevation.

Authoritative inheritance checkpoint: Issue #60 comment `5467154006`.
Base public main for this review package: `6820eee40186f22cd4df503380c475146c284fda`.

## Immutable inheritance

1. `MYSTIC-STATE-0077` is immutable representation-FAIL evidence entirely inside the >=5 deg development domain. Exact gate: run `31988825068`, job `95268545799`, artifact `9274892119`; 432 Pickles/Johnson-V comparisons; RMS `0.0063601882169680435 mag`; max absolute extinction error `0.02627247081962647 mag`, above the frozen `0.025 mag` maximum. It is not a solver failure and is forbidden as a tuning/acceptance set here.
2. `MYSTIC-STATE-0081` v2 is the fresh repair that validated the >=5 deg domain. Its fresh 576-comparison gate passed (max about `0.0075203570 mag`, RMS about `0.0013362205 mag`). Later v3/v3.2 extend the upper endpoint to 90 deg. Existing >=5 deg assets and runtime semantics are protected and are not modified by this lane.
3. No scientific <5 deg stellar-transport execution is inherited. Until fresh evidence passes, `<5 deg` remains unsupported/fail-closed.

## Geometry and atmosphere contract

- Radiative-transfer target altitude is topocentric vacuum/geometric altitude `h_geo`.
- Source zenith angle is exactly `sza = 90 deg - h_geo`.
- The deterministic reference solver is `sdisort`, with pseudo-spherical direct-beam attenuation. `1/sin(h)` is not asserted to be exact geometry and is not extrapolated below 5 deg.
- Refraction is not enabled in the RT input. Apparent/refracted altitude remains a separate observational geometry transform and must not be double-applied.
- Observer elevation remains a separate axis. The local atmosphere is truncated with `atm_z_grid` beginning at the geometric site height; output remains local `zout 0`.
- Preserve AFGL US, `mol_abs_param crs`, `aerosol_default`, AOD550 and albedo 0.15. Richer AVPS aerosol-profile science is explicitly out of scope.
- Preserve the exact 380..780 nm inclusive 1-nm spectral domain and the full atmospheric column.

## Phase A: deterministic numerical-capability screen

This phase determines only whether the exact existing direct-transmission estimator remains numerically representable. It does not validate interpolation, photometry, human visibility or production support.

Frozen candidate target altitudes, deg:

`0.25, 0.5, 1, 2, 3, 4, 5`

Frozen endpoint atmosphere states:

- observer elevation m: `0, 2500`
- AOD550: `0.05, 0.40`

The Cartesian product contains exactly 28 cases. `5 deg` is a seam/control only; it never replaces or rewrites the validated 5-deg runtime row.

Exact horizon (`0 deg`) is excluded from v1. The inherited direct-flux estimator divides `edir` by `mu0=sin(h)`, and therefore requires `mu0>0`. Horizon support requires a separate pre-result endpoint method if ever attempted.

### Frozen failure semantics

A Phase-A case is numerically eligible only if all of the following hold on its single authorized attempt:

- solver exit code is 0;
- exactly one intended `uvspec` execution occurred;
- exact output wavelength grid is 380..780 nm / 1 nm;
- `mu0` is finite and strictly positive;
- every derived direct transmission is finite and strictly in `(0,1]`.

Zero, negative, NaN, infinity, missing output, parser failure or underflow is `NUMERICALLY_UNRESOLVED`, never a physical zero and never replaced by epsilon. No retry, rerun or photon/precision change is permitted under the same protected execution identity.

The provisional numerical lower bound is the lowest frozen candidate altitude for which all four endpoint atmosphere states pass and every higher candidate altitude passes. A non-monotone altitude pass/fail pattern blocks interpretation and requires a fresh diagnosis protocol rather than cherry-picking a floor.

**No Phase-A solver execution is authorized by this file or by its review PR.** A fresh solver-free exact-head review must pass first; execution then requires a separately controlled one-shot identity after a live Issue #60 fence check.

## Phase B: representation preparation

Frozen lower-altitude training-knot universe, deg:

`0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0`

Only the contiguous suffix at or above the independently determined Phase-A numerical floor can later be eligible.

Candidate A is dense interpolation of direct optical depth `tau=-ln(T)` against geometric altitude itself. Candidate B is eligible only if an exact Chapman/pseudo-spherical direct-path coordinate can be extracted or derived from the pinned libRadtran runtime/source and independently verified before model-selection values are read. Plain empirical `csc(h)` extrapolation below 5 deg is not a candidate.

Model-selection/training and final protected validation must be disjoint. Final protected coordinates must be frozen and mechanically collision-checked against 0077/0081/v3/v3.2 protected coordinates before any protected result is opened. Taylor, Jerusalem, desired halachic first-seeing times and 0077 residual directions are forbidden selection inputs.

Preserve observer-elevation and AOD axes, 380..780 nm spectra, Pickles/Johnson-V consequence and full-column convention. Existing >=5 deg runtime bytes/semantics remain authoritative; any future asset is an additive lower extension joining at exactly 5 deg.

Unless a separately reviewed pre-result protocol freezes something stricter, the fresh final Johnson-V representation gate retains `max |delta A_V| <= 0.025 mag` and `RMS <= 0.010 mag`, with no post-result relaxation.

## Application contract

Until a fresh protected lower-altitude validation passes and explicitly establishes a minimum supported **geometric** target altitude, `starsvisibility` must continue to refuse `<5 deg` at the stellar-transport seam. Apparent/refracted altitude may be displayed/used observationally but cannot substitute for RT geometric altitude. Horizon obstruction, terrain and clouds remain separate providers/blockers.

## Review-only package

The companion `low_altitude_phase_a.py` may build the frozen 28-case ledger, render deterministic `sdisort` inputs and exercise parser/refusal logic. Its CLI has no solver-execution code path. The review test suite must prove that property before any scientific execution package is drafted.
