# OPAC NULL aerosol optical-depth table calibration v1

Status: **REVIEW / NULL-SOLVER CALIBRATION ONLY — NO SCIENTIFIC ORDINAL**

## Purpose

PR #594 froze the actual AFGL-US relative-humidity behavior and preserved the locked libRadtran `optical_properties()` verbose table at 550 nm for OPAC `continental_average`. That table prints aerosol columns labelled `scatter.` and `abs.` for every atmospheric layer, but a replacement AVPS renderer may not treat their sum as layer aerosol optical depth merely from the label.

This calibration tests that interpretation directly using the documented `aerosol_set_tau_at_wvl` column normalization.

## Exact cases

All three inputs are identical except for column AOD normalization:

1. `baseline`: standard `continental_average`, no explicit AOD rescale;
2. `aod010`: add `aerosol_set_tau_at_wvl 550 0.10`;
3. `aod030`: add `aerosol_set_tau_at_wvl 550 0.30`.

All use:

- exact frozen AFGL-US atmosphere;
- exact frozen OPAC archive and trace-proven four no-extension aliases;
- `aerosol_default` + `aerosol_species_library OPAC` + `aerosol_species_file continental_average`;
- wavelength exactly 550 nm;
- `rte_solver null` only;
- `verbose` optical-property output.

No custom vertical template is used in this calibration.

## Preregistered parser and tolerances

The parser reads only the aerosol block of the single 550-nm `*** optical_properties()` table.

For each of the 49 atmospheric layers:

`layer aerosol tau candidate = printed aerosol scatter + printed aerosol abs`

It also reads the printed aggregate `sum` line.

PASS requires:

- exactly 49 finite nonnegative aerosol layer rows on the same descending altitude grid;
- rowwise summed aerosol tau agrees with the printed aggregate aerosol `scatter+abs` to absolute tolerance `7e-5` (chosen from the six-decimal row print precision across 49 layers);
- in `aod010`, aggregate `scatter+abs` equals 0.10 to absolute tolerance `2.1e-6`;
- in `aod030`, aggregate `scatter+abs` equals 0.30 to absolute tolerance `2.1e-6`;
- the 0.30/0.10 aggregate ratio equals 3 within `1e-4`;
- after normalizing layer `scatter+abs` to unit column sum, every pair of baseline/0.10/0.30 shapes has maximum absolute layer-fraction difference <= `6e-5` and L1 difference <= `1.5e-3`.

The shape tolerances are frozen before execution and explicitly accommodate only the six-decimal verbose row print precision; they are not selected from results.

## Evidence dependency

This review must bind exact PR #594:

- head `e7f968ee70dbecaf5f315bc8b03627ce1628edef`;
- NULL audit run `33190680002` attempt 1 SUCCESS;
- artifact `9693619172`, digest `sha256:74813789c2bf2842788de16aba6f3269c9f4efec675f6ee758903e4f6c52f9da`;
- report content SHA-256 `fd4e691f14f9cab427f7992acfc0435f50442e65e519520e6edae55c250a7f14`;
- repo contract `33190679858` attempt 1 SUCCESS.

The runtime/archive/alias reconstruction helper is copied byte-identically from the reviewed #594 audit code and hash-bound in CI.

## Interpretation boundary

A PASS would establish only that, in the locked 550-nm NULL verbose table, aerosol `scatter+abs` can be used as layer aerosol optical depth and that `aerosol_set_tau_at_wvl` rescales total column AOD without materially changing normalized vertical shape at the table's print precision.

It does **not** validate a custom four-species mass renderer or any of the five AVPS vertical states. That is the next separate review gate.

## Hard boundaries

- no DISORT/MYSTIC/scientific RTE solver;
- no scientific ordinal; ordinal 41 remains unallocated;
- no scientific seeds;
- no Taylor/Jerusalem residual use;
- no custom AVPS target profile in this calibration;
- no Level-B or production mutation;
- no renderer authorization from source equations alone.
