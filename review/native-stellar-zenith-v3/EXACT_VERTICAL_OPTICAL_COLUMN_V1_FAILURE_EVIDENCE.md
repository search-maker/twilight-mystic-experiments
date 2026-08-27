# Exact-vertical optical-column v1 — immutable failure evidence

Status: **PRE-SOLVER_INFRASTRUCTURE_FAILURE_NO_SCIENTIFIC_SPECTRA**

This note freezes the outcome of the first authorized exact-vertical optical-column v1 dispatch. It is evidence, not a scientific result and not an authorization to relax any preregistered gate.

## Immutable run identity

- GitHub Actions run: `33040457601`
- canonical dispatch commit: `2663fbc3241b31e095f3fb814cecc5a60e078c0a`
- base main: `037ea4acb27aee2a7bc7b693ab285fa613ca197d`
- artifact ID: `9633642762`
- artifact digest: `sha256:f2f6f5b0d33518a48d36312b7f4bf18bea4ae22e1ce5fba2e80775c6b063332f`
- job: `98412617267`

## What happened

Preflight, exact-runtime hashes, frozen assets, parser tests, and the review-only surface all passed. The workflow then issued the four authorized deterministic `uvspec` process calls, but **all four terminated before spectral solving** in `setup_wlgrid()`.

The preserved stderr for every case contains:

`Error, file 'experiments/aerosol-family-challenge-v2-r8/wavelength-grid-1nm.dat' not found!`

The input path was repository-relative, while each `uvspec` process intentionally ran with its case directory as `cwd`. Therefore the frozen wavelength-grid file was not resolvable from that working directory.

## Scientific consequence

- requested process calls: 4
- valid scientific spectra: 0
- successfully parsed cases: 0
- optical-depth gate evaluated: **no**
- Johnson-V gate evaluated: **no**
- protected holdout opened: **no**
- model fit performed: **no**
- production authorization: **no**

The workflow-level execute step completed because the diagnostic script is evidence-preserving and records case failures in its summary; the final preregistered gate correctly failed. The phrase “four spectra” in that step label must not be interpreted as four completed spectra.

## Recovery boundary

A recovery may reuse the same four frozen training-axis cases because no scientific spectrum was produced. It must:

1. be a new workflow/run, never a GitHub Re-run of `33040457601`;
2. keep the original v1 code and dispatch immutable;
3. change only path resolution for the already-frozen wavelength-grid file;
4. prove that the resolved file has the exact expected 380–780 nm, 1-nm contents;
5. prove that the rendered libRadtran input is byte-identical to v1 except for the `wavelength_grid_file` path string;
6. keep the original preregistered gates unchanged: `max |Δτ| <= 1e-5`, `max |ΔA_V| <= 1e-4 mag`;
7. keep holdout opening, model fitting, LUT acceptance, and production forbidden.
