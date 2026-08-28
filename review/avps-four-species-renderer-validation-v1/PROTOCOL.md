# AVPS four-species renderer validation v1

Status: **REVIEW / NULL-SOLVER RENDERER VALIDATION ONLY / NO SCIENTIFIC ORDINAL**

## Purpose

AVPS scientific ordinal 40 is scientifically non-informative because its state-specific `aerosol_file tau` profiles did not survive into effective solver physics. The replacement experiment must preserve the already-preregistered question: vary only normalized aerosol vertical optical-depth shape while keeping the OPAC `continental_average` optical family fixed.

The predecessor chain has now frozen the required runtime facts:

- #590: explicit species-profile transport reaches DISORT/MYSTIC when the exact no-extension OPAC resolver alias is present;
- #591: locked `continental_average.dat` uses species columns `INSO WASO SOOT SUSO`;
- #592: all four species resolve together through one explicit `aerosol_species_file`;
- #593/#594: exact 550-nm OPAC RH source values and the locked AFGL-US runtime RH/nearest-node behavior are frozen;
- #595: NULL verbose aerosol `scatter + abs` is calibrated as layer aerosol optical depth, and `aerosol_set_tau_at_wvl` rescales column AOD while preserving normalized vertical shape.

This gate validates a corrected renderer for the five vertical templates already frozen in `experiments/aerosol-vertical-profile-sensitivity-v1/opac_vertical_templates.py` blob `8e8175ae771438b91fc9543b329175c193a215a4`.

## Frozen representation

For every AFGL-US aerosol layer, the renderer must keep the four local mass concentrations as **one common nonnegative scalar multiple** of the locked `continental_average` layer vector. Thus INSO/WASO/SOOT/SUSO local ratios remain fixed while only the amount of the mixture changes.

The runtime input surface is exactly:

```text
aerosol_default
aerosol_species_library OPAC
aerosol_species_file <state-profile> INSO WASO SOOT SUSO
aerosol_set_tau_at_wvl 550 <0.10 or 0.30>
```

The four official optical-property files are exposed only by the already-proven byte-identical no-extension aliases under `data/aerosol/OPAC/optprop/{INSO,WASO,SOOT,SUSO}`. No `.nc` aliases and no competing `aerosol_file tau` are permitted.

## Lower-bound layer semantics gate

The locked standard file is a layer concentration table. Before rendering any scientific template, this review expands its source rows onto every AFGL level using the source row at the greatest altitude not exceeding the layer lower boundary, with zero at and above 35 km. This is not trusted by assertion: an explicit four-species expanded standard profile at AOD550=0.10 must reproduce the built-in `aerosol_species_file continental_average` normalized NULL layer-tau shape within the same print-precision tolerances used by #595.

Only after that baseline gate passes may the renderer use, for each layer:

`common_scalar = frozen_target_layer_tau_fraction / expanded_standard_layer_tau_fraction`.

All four species in that layer receive the same scalar. Positive target support with zero standard support fails closed.

## Five frozen target states

No new profile is selected here. The exact existing AVPS states remain:

- `opac-profile-continental-average`
- `opac-profile-maritime-clean`
- `opac-profile-desert`
- `opac-profile-arctic`
- `opac-profile-antarctic`

Their target normalized layer-tau fractions come only from the exact frozen generator blob above, based on the independently selected OPAC Tables 3/5 construction. Taylor/Jerusalem residuals are not read or scored.

## Validation

For every state, run NULL at AOD550=0.10 and 0.30. PASS requires:

- aggregate printed aerosol tau matches requested AOD within `2.1e-6`;
- target-shape max absolute fraction error <= `6.0e-5`;
- target-shape L1 fraction error <= `1.5e-3`;
- 0.10 vs 0.30 normalized-shape differences satisfy the same limits;
- all rendered masses and common scalars are finite and nonnegative;
- no DISORT/MYSTIC or scientific RTE solution occurs.

These tolerances are frozen before runtime and reuse the #595 NULL print-precision calibration limits; they are not chosen from renderer results.

## Hard boundaries

- `main` stays `99ade7798627e67921139697ba1a004fa8a304bb`.
- Scientific ordinal 41 remains unallocated.
- No scientific seed is allocated.
- No MYSTIC or DISORT is executed.
- No Taylor/Jerusalem residual or event-time scoring is used.
- No Level-B mapping or production mutation occurs.
- PASS authorizes only a later review-only replacement AVPS preregistration using this representation; it does not authorize science by itself.
