# Scientific execution transport

This stage installs the guarded scientific execution path for `mystic-batch-v1`.

## Execution order

1. Check out the exact authorization commit.
2. Verify that the commit changes only `authorization.scientific.json`.
3. Verify the exact manifest, adapter, runtime lock, workflow hashes, execution key and ordinal.
4. Refuse a duplicate workflow marker before any syntax check or solver.
5. Freeze the matrix plan.
6. Run every case in an isolated matrix job with `fail-fast: false`.
7. Recompute runtime identity after cache restore in every job.
8. Perform exactly one `uvspec -c` syntax check and at most one solver execution per case, with no retry.
9. Aggregate the exact planned case set.
10. Independently recompute accounting, hashes and summary statistics.

## Current authorization boundary

The committed active authorization remains disabled. This PR cannot create a scientific run by itself. A future authorization must be a separate one-purpose commit bound to one merged manifest and the exact merged execution package.

A completed batch establishes numerical completion under its frozen contract only. It does not establish physical validity, observational validity, all-geometry validity, surrogate or LUT readiness, production readiness, or permission to change a default model.
