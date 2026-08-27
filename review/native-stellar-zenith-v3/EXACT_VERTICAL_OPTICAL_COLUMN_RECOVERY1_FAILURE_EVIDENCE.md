# Exact-vertical optical-column recovery1 — immutable failure evidence

Status: **POST_SOLVER_DENSE_OUTPUT_GRID_PARSER_FAILURE_NUMERIC_GATES_NOT_EVALUATED**

This note freezes the outcome of recovery1. It is not a scientific gate failure and it does not authorize another solver execution.

## Immutable source identity

- GitHub Actions run: `33041069040`
- canonical dispatch commit: `ac4a1230fd3ceb500019f5188173fb8f7165f5ec`
- source artifact ID: `9633879569`
- source artifact name: `native-stellar-zenith-exact-vertical-optical-column-recovery1-33041069040`
- source artifact digest: `sha256:eba59cc5d22e1600b0c38809cac29d615dddd0af02b491febae65164c3a1004e`
- job: `98414564910`

## What succeeded

The recovery1 preflight, exact runtime and asset checks, original v1 tests, recovery tests, and the path-only renderer proof all passed. The canonical absolute wavelength-grid path reached each case correctly.

All four deterministic exact-vertical DISORT process calls completed their full solve grid. The preserved stderr for each case reaches the final solve marker `iv = 400, 780.000000 nm` and contains 401 final solve-stage wavelength blocks (`iv=0..400`, 380..780 nm). Thus the prior pre-solver path failure was fixed.

## Why recovery1 still reported FAIL

The v1 direct-transmission parser assumed that `output_user lambda edir` would contain only the 401 requested 1-nm solve nodes. In this runtime, stdout instead contains 8001 rows from 380.000 through 780.000 nm at 0.050-nm spacing. The parser therefore refused at the first non-integral wavelength with:

`non-integral wavelength in 1-nm output`

Consequently recovery1 recorded:

- `solverInvocationCount = 4`
- `successfulParsedCaseCount = 0`
- `metrics = null`
- original optical-depth gate evaluated: **no**
- original Johnson-V gate evaluated: **no**

This is a post-solver parsing failure, not a numerical rejection of the exact-vertical method.

## Evidence-preserving analysis consequence

No further solver call is needed or permitted to repair this failure. The immutable artifact already contains all four complete stdout/stderr pairs required for the originally preregistered comparison. A recovery must therefore be **analysis-only**, must consume exactly the frozen artifact above, and must not install or invoke `uvspec`.

The only permitted parser correction is to validate the complete 8001-row 0.050-nm stdout grid and select its exact integer-nm nodes 380..780 for the originally intended 401-node comparison. The 401 selected stdout values must also be cross-checked against the 401 final solve-stage `flux_dir[lu=0]` values in stderr before the scientific gates are evaluated.

The original preregistered gates remain unchanged:

- maximum spectral `|tau_direct - tau_verbose_column| <= 1e-5`
- maximum Johnson-V consequence `<= 1e-4 mag`

Protected holdout opening, model fitting/refitting, stellar LUT acceptance evaluation, production authorization, empirical real-sky validation, and human first-seeing validation remain forbidden.
