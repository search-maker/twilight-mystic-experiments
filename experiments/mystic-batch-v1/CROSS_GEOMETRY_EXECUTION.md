# Cross-geometry pilot execution bridge

This bridge promotes the already-frozen `cross-geometry-pilot-v1` proposal into exactly one separately authorized matrix execution without changing the proposal itself.

The proposal remains `proposalOnly: true` and `scientificExecution: false`. A run is possible only from a one-purpose commit that changes the active cross-geometry authorization file and binds the exact proposal, contract, proposal validator, proposal adapter, execution adapter, workflow, runtime lock, plan, case executor, aggregate, audit, and screening-analysis driver.

Each of the 24 cases runs in an isolated matrix job with `fail-fast: false`, a maximum of six parallel jobs, one syntax check, at most one solver execution, no retry, and runtime identity recomputation after cache restore.

Completion means only that the frozen screening diagnostic completed and was independently audited. It does not establish all-geometry agreement, final engine validity, surrogate readiness, observational validity, or production permission.
