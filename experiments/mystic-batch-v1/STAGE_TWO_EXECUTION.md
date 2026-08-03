# Cross-geometry stage-two execution bridge

This bridge prepares a separately authorized scientific matrix for the 16 proposal cases in `manifest.cross-geometry-stage-two.proposal.json`.

The guard binds the exact proposal, pilot manifest, frozen pilot screening analysis, source provenance, screening contract, base and execution adapters, analysis module, duplicate-run guard, runtime probe and lock, execution workflow, plan, combined-analysis driver, case executor, aggregate, and independent audit. It accepts only a first-attempt manual `workflow_dispatch` checked out at a one-purpose authorization commit that changes only the active stage-two authorization file.

Each matrix case performs exactly one syntax check and at most one MYSTIC solver execution. The matrix has `fail-fast: false`, at most six concurrent cases, no retry path, and independent case artifacts.

After the 16 new cases pass generic aggregate and independent audit, the screening job downloads the preserved pilot post-processing artifact from run `30858046820`. It verifies that source artifact against the frozen hashes, combines pilot blocks 1-2 with stage-two blocks 3-4 for the four selected geometries, and carries forward the two pilot agreement geometries. A remaining noisy or discrepant selected geometry may recommend final fresh blocks 5-6, but no outcome hauthorizes scientific acceptance, surrogate use, LUT generation, observation claims, or production use.

The committed active authorization is disabled. This bridge cannot run a scientific case unless a later reviewed one-purpose authorization commit is created and manually dispatched.
