# Exact-vertical optical-column recovery1 protocol

Stage ID: `native-stellar-zenith-exact-vertical-optical-column-recovery1`

This is a bounded infrastructure recovery of run `33040457601`. No v1 scientific spectrum existed, so no scientific result is being retried or replaced.

## Frozen recovery change

The sole allowed scientific-input rendering change is:

- v1: repository-relative `wavelength_grid_file experiments/aerosol-family-challenge-v2-r8/wavelength-grid-1nm.dat`
- recovery1: the **same file bytes**, expressed as its canonical absolute filesystem path before launching `uvspec` from a case directory.

No wavelength, atmosphere, aerosol, surface, solver, stream count, output quantity, SED, photometric response, geometry, case universe, or acceptance threshold may change.

## Immutable case universe

1. observer elevation 500 m, AOD550 0.30
2. observer elevation 1250 m, AOD550 0.10
3. observer elevation 1250 m, AOD550 0.30
4. observer elevation 2000 m, AOD550 0.20

Each case is exact physical zenith (`sza=0°`) using deterministic DISORT and 16 streams.

## Unchanged gates

- maximum spectral `|tau_direct - tau_verbose_column| <= 1e-5`
- maximum Johnson-V consequence across frozen Pickles representatives `<= 1e-4 mag`

The verbose optical-property columns must still be interpreted by the already-validated Tier-1 parser.

## Required pre-execution proofs

The recovery implementation must fail closed unless:

- the supplied grid path exists before case-directory creation;
- the grid values are exactly integers 380 through 780 inclusive;
- the recovery renderer and original v1 renderer differ in exactly one line;
- that line is only `wavelength_grid_file ...`;
- original path and resolved path refer to the same file bytes;
- v1 run/artifact identity is frozen in the dispatch.

## Claim boundary

Even on PASS this recovery only supports drafting an exact-zenith endpoint method. It does **not** open protected holdouts, fit or refit a model, evaluate the stellar LUT acceptance gate, authorize production, validate real-sky observations, or validate human first-seeing.

GitHub Re-run and per-case solver retry are forbidden. A recovery execution, if authorized, is a new one-shot run with exactly four deterministic process calls.
