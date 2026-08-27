# Exact-vertical optical-column diagnostic v1

## Purpose

The frozen SDISORT 2.0.6 endpoint cannot evaluate exact `umu0=1.0`. The preregistered positive-epsilon path returned `NO_SELECTION_UNDER_PREREGISTERED_PROTOCOL`, and the separately frozen DISORT bridge v1 correctly failed its near-zenith cross-solver optical-depth gate even though exact DISORT@0 and its plane-parallel self-reconstruction passed.

This protocol therefore tests the exact vertical direct transmission without substituting a positive zenith angle and without comparing a slanted plane-parallel ray to a pseudo-spherical ray. It compares two quantities produced from the **same fresh exact-vertical deterministic DISORT run**:

1. direct-beam optical depth from `output_quantity transmittance` / `edir` at SZA 0: `tau_direct = -ln(edir)`;
2. the resolved atmospheric column optical depth reconstructed by summing the layer optical properties printed by libRadtran's proven `verbose` `*** optical_properties()` table.

The verbose-table parser follows the already successful Tier-1 `atm_z_grid` equivalence proof. No NetCDF writer is used; the two prior full-grid `write_optical_properties` format probes are retained as failed infrastructure attempts and are not rerun.

## Frozen training-only universe

No protected stellar holdout coordinate is opened. Execute exactly four fresh atmosphere states, all on the existing stellar training axes and distinct from the previous 0/2500-m DISORT bridge corners:

- observer elevation 500 m, AOD550 0.30;
- observer elevation 1250 m, AOD550 0.10;
- observer elevation 1250 m, AOD550 0.30;
- observer elevation 2000 m, AOD550 0.20.

Every case uses physical target altitude exactly 90 deg / source zenith angle exactly 0 deg.

Total fresh deterministic solver calls: **4**.

## Frozen libRadtran input

Each case uses the exact reviewed libRadtran 2.0.6 runtime and MYSTIC-STATE-0081 atmosphere surface:

- AFGLUS atmosphere;
- `mol_abs_param crs`;
- exact 380..780 nm inclusive 1-nm grid;
- explicit packaged `solar_flux/atlas_plus_modtran` source file;
- `sza 0.00000000`;
- the existing `atm_z_grid` elevated-site representation with its bottom at the physical site altitude;
- `zout 0.000000`;
- surface albedo 0.15;
- `aerosol_default` and the requested AOD550;
- `rte_solver disort`;
- `number_of_streams 16` (the already proven deterministic verbose-control setting; it does not alter the analytic direct-beam attenuation being tested);
- `output_quantity transmittance`;
- `output_user lambda edir`;
- `verbose`;
- no `write_optical_properties`, no MYSTIC, and no Monte Carlo directive.

## Verbose optical-column reconstruction

For every requested wavelength, the parser must find exactly one solve-stage block of the form

`*** wavelength: iv = <index>, <wavelength> nm, ...`

followed by exactly one `*** optical_properties()` table. It must require:

- indices 0..400 in order;
- wavelengths 380..780 nm exactly;
- exactly `len(atm_z_grid)-1` layer rows for that case;
- finite layer values;
- zero configured cloud optical depth.

The layer fields are interpreted identically to the already validated Tier-1 parser:

`tau_layer = Rayleigh + aerosol_scattering + aerosol_absorption + water_scattering + water_absorption + ice_scattering + ice_absorption + molecular_absorption`.

Then

`tau_column_verbose(lambda) = sum_layers(tau_layer)`.

## Preregistered gates

Every fresh case must return code 0 and produce exactly 401 direct-transmission rows and 401 complete verbose optical-property tables.

The following thresholds are frozen **before** the four fresh cases are executed:

1. **Spectral optical-column consistency:** maximum over all four cases and all 401 wavelengths of `abs(tau_direct - tau_column_verbose)` must be `<= 1.0e-5`.
2. **Johnson-V consequence:** for frozen Pickles library numbers 1, 26, and 45, maximum absolute difference in Johnson-V extinction magnitude between `exp(-tau_direct)` and `exp(-tau_column_verbose)` must be `<= 1.0e-4 mag`.

The `1e-5` optical-depth tolerance explicitly accounts for the finite decimal precision of the existing libRadtran verbose table. Before this protocol was frozen, already-open historical Tier-1 proof data showed row-sum versus printed-column differences up to approximately `3.15e-6`; therefore a `1e-6` gate would test text rounding rather than the physical identity. The photometric gate retains the same strict `1e-4 mag` scale used by earlier zenith diagnostics.

No threshold may be relaxed after these four results are opened.

## Decision rule and claim boundary

The diagnostic returns `EXACT_VERTICAL_OPTICAL_COLUMN_DIAGNOSTIC_PASS` only if all structural checks and both frozen gates pass. Otherwise it returns `..._FAIL` and preserves the complete raw input/stdout/stderr and parsed metrics.

A PASS authorizes only drafting a separate stellar v3.2 endpoint method in which exact physical 90 deg uses the validated exact-vertical deterministic endpoint while all altitudes below 90 deg retain the existing SDISORT method. The v3.2 method must itself be frozen and reviewed before the 64 protected holdouts may be opened.

A PASS does **not** authorize production, empirical real-sky validation, or human first-seeing validation.

A FAIL leaves the 64 protected holdouts closed and forbids use of this endpoint path unless a separately preregistered method is developed.