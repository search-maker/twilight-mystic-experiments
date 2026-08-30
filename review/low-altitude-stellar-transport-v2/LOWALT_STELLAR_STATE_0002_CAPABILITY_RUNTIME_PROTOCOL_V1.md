# LOWALT-STELLAR-STATE-0002 capability/runtime protocol v1

Status: **POST_V1_NONBLOCKING / RESULT-BLIND / CAPABILITY-AND-LATENCY ONLY**. This package authorizes no protected result opening, no compact representation selection, no application support change, and no scientific claim below the current validated 5 deg geometric target-altitude floor.

Authoritative freezes: Issue #60 comments `5470357109` (successor theory/runtime freeze) and `5470368706` (application call-volume/exact-route budget freeze). Issue #60 remains the live control ledger and Issue #668 remains the dashboard.

## Inheritance and protected boundaries

The authoritative production seam remains MYSTIC-STATE-0081/v3.2 at geometric target altitude >=5 deg. LOWALT-STELLAR-STATE-0001 established that direct pseudo-spherical `sdisort` is numerically viable below 5 deg but its compact representation failed its protected accuracy gate. Its opened protected residual values, pattern, signs, ranking, and near-pass/fail locations are sealed from this successor design. MYSTIC-STATE-0077 residuals, Taylor/Jerusalem residuals, and desired halachic first-seeing times are likewise forbidden selection inputs.

An earlier unmerged STATE-0002 adaptive-grid draft branch is not admitted by this protocol and supplies no training grid, protected matrix, support floor, or successor evidence. This package implements only the later frozen 20-case capability/runtime plan from the two Issue #60 comments above.

## Geometry and atmosphere

Radiative transfer consumes topocentric vacuum/geometric target altitude `h_geo`. Source zenith angle is `90 deg - h_geo`. Apparent/refracted altitude remains a separate observational transform and is never fed back into this RT seam. Observer elevation remains an atmosphere-truncation axis implemented by `atm_z_grid` beginning at the geometric site height with local `zout 0`; it is not target altitude and is not replaced by the libRadtran `altitude` directive.

The pinned deterministic reference is pseudo-spherical `sdisort` with AFGL-US atmosphere, `mol_abs_param crs`, `aerosol_default`, AOD550 via `aerosol_set_tau_at_wvl 550`, surface albedo 0.15, and 380..780 nm at 1 nm. Runtime identity is `rubin-libradtran=2.0.6=py312pl5321he9373c2_1`, `uvspec` SHA-256 `2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3`.

Direct output remains `output_quantity transmittance` / `output_user lambda edir`; for `h_geo>0`, line-of-sight transmission is `T_los = edir / sin(h_geo)`. Finite exact optical depth may be stored as `tau_los = -ln(T_los)`. Zero, negative, nonfinite, or missing transmission is `NUMERICALLY_UNRESOLVED`. Epsilon substitution is forbidden. Exact 0 deg remains outside this state because the inherited estimator is singular there; 0 deg support is not implied by any positive-altitude result.

## Frozen fresh capability matrix

Fresh target geometric altitudes are exactly `0.30, 0.70, 1.40, 2.90, 4.60 deg`; observer elevations exactly `0, 2500 m`; AOD550 exactly `0.05, 0.40`. The Cartesian product is exactly 20 fresh capability spectra. These altitude values are disjoint from the opened STATE-0001 protected altitude axes and its lower training altitude knots. Exact 5 deg is inherited seam/control only and is not fresh successor training evidence.

The capability matrix is not model-selection evidence. Its values may establish numerical representability and timing/cost only. They may not select or tune a compact formula, interpolation coordinate, knots, support floor, protected matrix, or Johnson-V acceptance threshold.

## Frozen timing contract

After one non-science runtime/help/hash verification step, execute exactly three independent warm process invocations for each of the 20 fresh coordinates, hence exactly 60 timed spectra. Repetition 1 is the sole capability spectrum for that coordinate; repetitions 2 and 3 are timing-only. No failed invocation may be retried, resumed, or GitHub Re-run under the same scientific identity.

Report median, p95, max, total wall time over the 60 warm invocations plus per-altitude summaries. Environment installation/setup time is reported separately. Project serial exact-transport wall time for 2,049 and 108,597 evaluations as `N * measured median` and `N * measured p95`; those projections do not make per-sample remote `sdisort` eligible.

## Practical exact-route freeze

The current `starsvisibility` browser transport seam is synchronous and geometry-at-a-time. An ordinary timeline has 2,049 base transport evaluations before refinement, and the documented seven-day annual sampling implies 108,597 base evaluations for one target before refinement. Therefore `PER_SAMPLE_REMOTE_SDISORT` is architecturally ineligible independent of measured solver speed.

An exact cache is exact only for exact-key hits. The key must bind exact geometric target altitude, observer elevation, AOD550, pinned atmosphere/runtime/wavelength identity. Quantization, rounding, nearest-neighbor lookup, or interpolation is not an exact cache hit. A miss fails closed unless a separately reviewed exact solver service is invoked. A future remote exact design may be studied only as batched/reorchestrated execution that preserves all requested and refinement geometries.

## Review/execution ordering

This controller is solver-free. It materializes and self-tests the frozen 20-case and 60-invocation contracts but cannot execute `uvspec`. A later one-shot execution implementation must be separately reviewed and bound to this exact protocol/controller identity. Immediately before every repository mutation, and again after CI or another long operation, the newest Issue #60 ledger must be re-read and any WRITE_QUIET or newer invalidation/recovery directive must supersede local state. Before actual solver dispatch, critical-path Actions must again be checked; this POST-V1 lane yields to AVPS/Atmosphere, ARM real-sky validation, Human Vision V1, Moon/Total-Sky V1, and end-to-end V1 integration.

No protected matrix exists under this package. No <5 deg production support is claimed.
