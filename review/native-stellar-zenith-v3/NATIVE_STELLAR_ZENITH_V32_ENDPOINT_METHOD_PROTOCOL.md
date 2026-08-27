# Native stellar zenith v3.2 exact-vertical endpoint method

## Purpose

The frozen native stellar zenith v3 design extends the validated stellar direct-optical-depth LUT from 80 deg to 90 deg with new training knots at 82.5, 85.0, 87.5, and 90.0 deg. The original SDISORT endpoint cannot evaluate exact `umu0=1.0`. A preregistered positive-epsilon selection returned `NO_SELECTION_UNDER_PREREGISTERED_PROTOCOL` and therefore may not be substituted for physical zenith.

The separately preregistered exact-vertical optical-column diagnostic has now passed. Its immutable analysis-only recovery2 result is:

- analysis run: `33041830554`;
- analysis dispatch SHA: `bdac3f0f03f1d2c63d274076365f1f3331a8b68e`;
- result artifact ID: `9634148868`;
- result artifact digest: `sha256:aa5b0b4a5b705bdcefd29c35113f331aa667b8dca9a2b228d44aa52ec864ca78`;
- source solver run: `33041069040`;
- source solver artifact ID: `9633879569`;
- source solver artifact digest: `sha256:eba59cc5d22e1600b0c38809cac29d615dddd0af02b491febae65164c3a1004e`;
- `max |delta tau| = 8.630205807602653e-06 <= 1.0e-05`;
- `max |delta A_V| = 2.0522918572907223e-06 mag <= 1.0e-04 mag`;
- dense-stdout / stderr direct-flux parser cross-check `5.000000002919336e-08 <= 1.0e-07`.

The exact-vertical protocol explicitly authorizes drafting a v3.2 endpoint method after this PASS.

## Frozen v3.2 method

The physical target-altitude axis, atmosphere axes, wavelength grid, interpolation coordinates, photometric assets, validation coordinates, and acceptance gates are unchanged from native stellar zenith v3.

### Altitudes below 90 deg

For every physical target altitude `< 90 deg`, v3.2 is byte-for-byte the existing native v3 SDISORT renderer and parser:

- `rte_solver sdisort`;
- `sdisort nscat 1`;
- line-of-sight direct transmission from `edir / mu0`;
- `mu0 = sin(targetAltitudeDeg)`.

No positive-epsilon substitute is introduced.

### Exact physical 90 deg

For physical target altitude exactly `90 deg`, v3.2 uses the validated exact-vertical deterministic optical-column endpoint:

- SZA exactly `0.00000000`;
- `rte_solver disort`;
- `number_of_streams 16`;
- the same AFGLUS / `atm_z_grid` elevated-site atmosphere representation;
- the same molecular absorption, aerosol, albedo, wavelength-grid, and packaged solar-source assets as the successful exact-vertical diagnostic;
- `verbose` optical-property output;
- no MYSTIC, no Monte Carlo, no SDISORT, and no positive zenith-angle approximation.

For each of the 401 wavelengths 380..780 nm, the existing proven verbose-table parser reconstructs

`tau_vertical(lambda) = sum_layers(totalLayerOpticalDepth)`.

The exact-zenith training spectrum is then

`T_vertical(lambda) = exp(-tau_vertical(lambda))`.

The stdout `edir` spectrum is preserved as raw evidence but is not the v3.2 endpoint estimator. This avoids dependence on SDISORT's unsupported exact endpoint and uses the exact-vertical optical-column identity already validated under the frozen `1e-5` / `1e-4 mag` gates.

## Frozen training and protected validation universe

Training coordinates are exactly the original v3 coordinates:

- target altitude: 82.5, 85.0, 87.5, 90.0 deg;
- observer elevation: 0, 500, 1250, 2000, 2500 m;
- AOD550: 0.05, 0.10, 0.20, 0.30, 0.40.

This is exactly **100 training spectra**:

- 75 unchanged SDISORT spectra below 90 deg;
- 25 exact-vertical DISORT optical-column spectra at 90 deg.

The protected validation coordinates remain exactly the original 64 v3 holdouts:

- altitude: 80.9375, 83.4375, 85.9375, 88.4375 deg;
- 4 frozen 3/8 elevation coordinates;
- 4 frozen 3/8 AOD coordinates.

All 64 holdouts are below 90 deg and therefore use the unchanged SDISORT reference method. No holdout coordinate is changed to accommodate the endpoint method.

## Frozen LUT and interpolation

The existing validated v2 LUT values through 80 deg must remain byte-for-byte unchanged.

The extended v3.2 LUT retains:

- altitude knots through 80 deg unchanged;
- new knots 82.5, 85.0, 87.5, 90.0 deg;
- direct optical depth as the stored spectral quantity;
- csc(altitude) interpolation;
- linear elevation interpolation;
- linear AOD interpolation.

No new fit, smoothing, retuning, or post-result model selection is authorized.

## Frozen validation gates

The original v3 protected-holdout gates remain unchanged. For frozen Pickles library numbers 1, 26, and 45, across all 64 fresh atmospheric holdouts (192 Johnson-V comparisons):

1. global `max |delta A_V| <= 0.025 mag`;
2. global RMS `<= 0.010 mag`;
3. each of the four new altitude intervals must independently satisfy both the same max and RMS limits.

No threshold may be relaxed after holdout values are opened.

## Review and execution boundary

This method implementation and its one-shot workflow must be merged to `main` after repository-wide tests pass **before** the protected 64 holdouts may be opened.

The review PR itself is non-executing. After merge, a separate one-file dispatch directly on the then-current `main` may explicitly authorize exactly:

- 100 training solver calls;
- 64 protected-holdout solver calls;
- 164 total deterministic solver calls;
- opening of the frozen 64 holdout results under the unchanged gates.

GitHub re-run, per-case retry/resume, post-result threshold relaxation, and post-result retuning are forbidden.

## Claim boundary

A protected-holdout PASS would establish only computational direct-stellar-transport validation of the 80..90 deg v3.2 extension against the frozen libRadtran reference method.

It does not by itself authorize:

- production deployment;
- empirical real-sky validation claims;
- human first-seeing validation claims;
- lunar, natural-night, or artificial-sky background validation.
