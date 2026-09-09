# LOWALT-STELLAR-STATE-0003 — fresh source-equivalence comparison matrix v1

Status: `FROZEN / WHOLLY_FRESH_NONPROTECTED / NOT_EXECUTED / POST_V1_NONBLOCKING`

Machine-readable authority: `LOWALT_STELLAR_STATE_0003_FRESH_SOURCE_EQUIVALENCE_MATRIX_V1.json`.

This file freezes the first STATE-0003 comparison universe **before any source-extractor, exact-direct-evaluator, or sdisort result at these coordinates is opened**. It does not authorize execution by itself.

## Fresh nonprotected matrix

The low-altitude reference/training universe is the full Cartesian product:

- geometric target altitude: `0.44, 1.11, 2.36, 3.83, 4.91 deg`;
- observer elevation: `375, 1375, 2250 m`;
- AOD550: `0.08, 0.27, 0.36`.

Total: **45 fresh cases**, each on the frozen 380–780 nm / 1 nm grid.

The altitude values are disjoint from all published STATE-0002 capability altitudes and from the published coordinate identities of the opened STATE-0001 low-altitude sets. This collision audit uses coordinate identities only; no STATE-0001 residual/error values, signs, magnitudes, or patterns were consulted. Taylor and Jerusalem were not consulted.

## Exact reference identity

Every later reference comparison must use:

- exact recovered HTTP-content-decoded source SHA-256 `999e47f4af4b5df6f85a6887fc105fc8f6e1a7cee89a3124f69ac8d8912c8e85`;
- exact package `rubin-libradtran=2.0.6=py312pl5321he9373c2_1`;
- exact `uvspec` SHA-256 `2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3`;
- AFGLUS, CRS molecular absorption, default aerosol scaled by AOD550 at 550 nm, albedo 0.15;
- exact post-observer `atm_z_grid` truncation;
- `sdisort nscat 1`, no refraction, direct `edir/mu0` identity.

The source-instrumented reference extractor may serialize already-computed optical properties but may not modify optical-property calculations.

## Inherited 5 deg seam controls

The machine manifest separately freezes nine controls at exact `5.00 deg`, using the three fresh observer elevations and three fresh AOD values. These are **not** part of the wholly fresh low-altitude training matrix and may never be used to lower the V1 floor. Their only role is to prove that any later POST_V1 evaluator preserves the authoritative >=5 deg seam exactly enough for a separately reviewed transition.

Until such a transition exists, the existing V1 route remains authoritative at and above 5.0 deg and production remains fail-closed below 5.0 deg.

## Result-opening order

1. This matrix and its payload hash are frozen.
2. A narrow exact-999 source instrumentation/reference extractor for precision-preserving `dtauc` is implemented and reviewed without reading these comparison results.
3. The optimized exact-direct evaluator is implemented from the source audit, not from residual fitting.
4. Execution may occur only after a fresh #60/main/AVPS/Actions fence confirms no actual V1 contention and the LOWALT execution contract permits it.
5. All 45-case outputs are made immutable before any comparison is interpreted.
6. No formula, tolerance, support floor, or matrix coordinate may be retuned after results are opened.
7. A separate unopened protected transition matrix would still be required before any production support change.
