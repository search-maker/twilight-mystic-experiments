# Exact-vertical optical-column analysis recovery2 protocol

Stage ID: `native-stellar-zenith-exact-vertical-optical-column-analysis-recovery2`

This protocol is frozen before the official analysis-only recovery result is produced. It consumes the immutable solver artifact from run `33041069040`; it authorizes **zero** new solver calls.

## Immutable source

- source run: `33041069040`
- source dispatch: `ac4a1230fd3ceb500019f5188173fb8f7165f5ec`
- source artifact ID: `9633879569`
- source artifact name: `native-stellar-zenith-exact-vertical-optical-column-recovery1-33041069040`
- source artifact digest: `sha256:eba59cc5d22e1600b0c38809cac29d615dddd0af02b491febae65164c3a1004e`
- source solver invocation count: 4
- source complete deterministic exact-vertical cases: 4

The source artifact contains the four frozen training-axis cases:

1. 500 m, AOD550 0.30
2. 1250 m, AOD550 0.10
3. 1250 m, AOD550 0.30
4. 2000 m, AOD550 0.20

All are exact physical zenith (`sza=0°`) with deterministic DISORT and 16 streams.

## Analysis-only boundary

The recovery workflow must not install libRadtran and must fail if `uvspec` is unexpectedly present. It may download the source artifact, read repository code/assets, parse text, calculate optical depths and photometry, and upload a derived analysis artifact. It may not execute any radiative-transfer solver.

## Dense stdout parser correction

For every source case, `case.stdout.txt` must be validated as follows before any scientific comparison:

- exactly 8001 nonblank rows;
- first wavelength exactly 380.000 nm within `1e-9` nm;
- last wavelength exactly 780.000 nm within `1e-9` nm;
- row `i` wavelength equals `380 + 0.05*i` nm within `1e-9` nm;
- every transmission is finite and in `(0, 1.000001]`;
- selecting rows whose indices are multiples of 20 yields exactly 401 nodes;
- those selected wavelengths are exactly integers 380..780 nm within `1e-9` nm.

Only those validated 401 integer-nm stdout nodes are used for the originally preregistered optical-column comparison.

## Independent selected-node cross-check

For every case, stderr must contain exactly 401 final direct-flux records matching:

`iv = 0..400`, wavelengths 380..780 nm, `iq = 0`, `flux_dir[lu=0]`.

The selected integer-nm stdout transmission and corresponding stderr `flux_dir[lu=0]` must agree at every wavelength within the preregistered parser-recovery tolerance:

`max |T_stdout_integer - flux_dir_stderr| <= 1e-7`.

This tolerance validates that selecting the integer stdout nodes recovers the actual final DISORT solve-node direct transmission rather than an unrelated interpolation value. It is a parser/evidence gate, not a scientific-method acceptance threshold.

## Verbose optical-column parser

The recovery must reuse the v1 `parse_verbose_optical_columns()` implementation, which itself delegates the optical-property table semantics to the already-validated Tier-1 `parse_resolved_optical_table()` parser. It must require:

- exactly 401 final solve-stage wavelength blocks with albedo;
- `iv=0..400` and wavelengths 380..780 nm;
- one optical-properties table per final block;
- stable layer count across all 401 wavelengths within each case;
- zero configured cloud optical depth.

The expected layer count is derived structurally from the preserved `atm_z_grid` line in that case's immutable `case.inp`: number of grid levels minus one. The case identity is also derived from the preserved input: the bottom `atm_z_grid` level is the observer elevation and `aerosol_set_tau_at_wvl 550` supplies AOD550. These values must match the frozen four-case universe.

## Unchanged scientific gates

After all parser/evidence checks pass:

`tau_direct(lambda) = -ln(T_stdout_integer(lambda))`

and the v1 evaluator compares it with the summed verbose optical column and evaluates the same frozen Pickles/Johnson-V photometry.

The original preregistered scientific gates remain exactly:

- maximum spectral `|tau_direct - tau_verbose_column| <= 1e-5`
- maximum Johnson-V consequence across frozen Pickles representatives 1/26/45 `<= 1e-4 mag`

No threshold may be relaxed based on the recovery result.

## Required output and claim boundary

The analysis result must record source run/artifact/dispatch/digest, zero solver executions by recovery2, four source solver invocations, all parser/evidence metrics, per-case scientific metrics, and global scientific metrics.

A PASS means only that the exact-vertical optical-column diagnostic passed its original gates on the already-existing four training-only solver outputs and may support drafting a v3.2 exact-zenith endpoint method.

Even on PASS:

- protected holdout opening: forbidden
- model fitting/refitting: forbidden
- stellar LUT acceptance evaluation: forbidden
- production authorization: forbidden
- empirical real-sky validation: false
- human first-seeing validation: false
