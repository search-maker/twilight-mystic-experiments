# Native stellar zenith v3.2 — exact-zenith endpoint training protocol

Stage ID: `native-stellar-zenith-v3.2-endpoint-training-v1`

This protocol is frozen before the 25 exact-zenith training outputs are opened. It replaces only the invalid v3.1 exact-90 solver convention. It does not open the 64 protected holdouts.

## Why v3.2 is required

The frozen SDISORT 2.0.6 runtime does not provide a trustworthy exact-zenith numerical endpoint. Exact `umu0=1` is unsupported, and the independently preregistered epsilon-selection protocol produced `NO_SELECTION`: the smallest usable tested SZA did not satisfy the frozen geometric approximation bound. A separate tilted SDISORT↔DISORT bridge also failed its preregistered solver-agreement gate and remains a failure; v3.2 does not claim tilted solver interchangeability.

An independent exact-vertical optical-column diagnostic subsequently passed on four fresh training-axis atmosphere states using deterministic `DISORT` at exact `sza=0°`. Official analysis-only recovery2 run `33041830554` passed:

- max `|tau_direct - tau_verbose_column| = 8.630205807602653e-06 <= 1e-05`;
- max Johnson-V consequence `2.0522918572907223e-06 mag <= 1e-04 mag`;
- max selected-stdout vs final-stderr direct-flux difference `5.000000002919336e-08 <= 1e-07`;
- zero solver executions in that analysis recovery.

Source result artifact: ID `9634148868`, digest `sha256:aa5b0b4a5b705bdcefd29c35113f331aa667b8dca9a2b228d44aa52ec864ca78`.

## Frozen v3.2 endpoint method

For physical target altitude exactly `90°` only:

1. use deterministic `rte_solver disort` at exact `sza 0.00000000`;
2. use `number_of_streams 16`;
3. retain AFGLUS, the existing `atm_z_grid` elevated-site representation, local `zout 0`, albedo 0.15, `aerosol_default`, and the frozen AOD550 knot;
4. use the packaged explicit solar source `solar_flux/atlas_plus_modtran`;
5. request direct transmittance and `verbose` optical properties;
6. validate the complete 8001-row 0.05-nm direct-output grid and select its exact integer-nm nodes 380..780;
7. cross-check those 401 selected nodes against the 401 final stderr `flux_dir[lu=0]` values;
8. compute `tau_90(lambda) = -ln(T_90(lambda))`;
9. independently sum the already-validated verbose per-layer optical properties and compare them with `tau_90`.

This exact-vertical DISORT method is used **only** for the exact 90° training knot. It does not replace SDISORT at any non-zenith altitude.

## Frozen training composition

The v3.2 training LUT retains exactly the original four new altitude knots:

`82.5, 85.0, 87.5, 90.0 deg`.

Atmosphere axes remain:

- observer elevation: `0, 500, 1250, 2000, 2500 m`;
- AOD550: `0.05, 0.10, 0.20, 0.30, 0.40`.

### 75 non-zenith training spectra — immutable reuse

Do not rerun them. Reuse the 75 successfully parsed v3.1 training cases at 82.5°, 85°, and 87.5° from:

- source run `33035467761`;
- dispatch `2a6f6eadb003ea70c99e0c306f232a6233650a0e`;
- artifact ID `9631872858`;
- artifact digest `sha256:dd8cbf6c00fdcf34041fb61e43d0f97d43646a5d2bdaf5a2ef899ed1a40f078b`.

The source artifact must contain exactly 25 successful `CASE_EXECUTED_AND_PARSED` cases at each of 82.5°, 85°, 87.5°, plus the preserved failed first 90° case. Every reused case must verify its stored input/stdout/stderr hashes and frozen physical coordinate. No source non-zenith spectrum may be regenerated.

### 25 exact-zenith training spectra — new execution

Run exactly the 5 elevations × 5 AOD knots at physical 90°. These are training coordinates already frozen by v3/v3.1; no new coordinate is introduced.

Every exact-90 case must individually pass, without threshold relaxation:

- stdout↔stderr direct-flux max absolute difference `<= 1e-7`;
- max spectral `|tau_direct - tau_verbose_column| <= 1e-5`;
- max Johnson-V consequence across frozen Pickles representatives 1/26/45 `<= 1e-4 mag`;
- exact 401-node wavelength identity;
- finite positive transmission and nonnegative optical depth;
- zero configured cloud optical depth.

Any case failure blocks LUT assembly and holdout authorization.

## LUT assembly — unchanged interpolation contract

The source v2 LUT is immutable through 80° and must remain byte-value identical for all 675 old spectra.

Append the 100 new training spectra in the already-frozen order:

1. 25 × 82.5° reused SDISORT;
2. 25 × 85.0° reused SDISORT;
3. 25 × 87.5° reused SDISORT;
4. 25 × exact 90° DISORT vertical endpoint.

The interpolation contract remains exactly:

- interpolate direct optical depth, not magnitude;
- altitude coordinate `csc(h) = 1/sin(h)`;
- linear observer elevation;
- linear AOD550.

No new fitted coefficient, smoothing parameter, blending width, or post-result tuning is permitted.

## Pre-holdout structural seam gates

These gates use training knots only and do not substitute for the protected 88.4375° holdout.

For every elevation × AOD atmosphere and every wavelength:

1. runtime interpolation at 87.5° must reproduce the immutable 87.5° source knot within `1e-12` optical depth;
2. runtime interpolation at 90° must reproduce the new exact-vertical 90° knot within `1e-12` optical depth;
3. `tau_90 >= 0`;
4. physical endpoint ordering must hold with numerical slack only: `tau_90 <= tau_87.5 + 1e-10`;
5. dense probes inside 87.5°..90° must remain finite, nonnegative, and between the two endpoint optical depths, proving no interpolation overshoot or discontinuity;
6. the first 675 v2 spectra must remain exactly unchanged.

For diagnostic reporting only, not as an acceptance threshold, report the difference between the exact-90 endpoint and the linear-csc extrapolation from the 85° and 87.5° knots. No pass/fail threshold may be invented from that residual after results are seen.

## Protected holdout boundary

The 64 protected coordinates remain unchanged and unopened:

- altitude: `80.9375, 83.4375, 85.9375, 88.4375 deg`;
- 4 fresh elevation values;
- 4 fresh AOD values;
- 192 frozen Pickles/Johnson-V comparisons.

This endpoint-training stage does **not** authorize those solver calls. A separate post-training authorization is required only after all 25 endpoint cases and all structural seam gates pass and the v3.2 training LUT is frozen by hash.

The existing protected-holdout scientific gates remain unchanged for that later stage:

- max absolute `Delta A_V <= 0.025 mag`;
- RMS `Delta A_V <= 0.010 mag`;
- globally and separately for every new altitude interval.

## Claim boundary

Even if endpoint training and structural seam checks pass:

- protected holdout opened: false;
- computational reference validation complete: false;
- model production authorization: false;
- empirical real-sky validation: false;
- human first-seeing validation: false.

GitHub Re-run, per-case retry, solver resume, threshold relaxation, and post-result retuning are forbidden.
