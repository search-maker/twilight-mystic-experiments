# Scientific adapter preparation stage

This stage adds the strict adapter and runtime-identity capture needed before a scientific matrix execution workflow can be authorized.

It deliberately stops before both `uvspec -c` and solver execution.

## What it establishes

- one supported adapter ID: `mystic-spectral-radiance-v1`;
- exact rendering of the MYSTIC input from a scientific manifest and one isolated case;
- case-level geometry, seed and photon binding;
- strict rooted paths for repository files and libRadtran data files;
- runtime identity claims for the `uvspec` binary, its help output, the libRadtran data tree, atmosphere and runtime lock;
- a transitional exact micromamba package build, with cache treated only as an accelerator;
- a disabled one-purpose scientific authorization template.

## What it does not establish

- no syntax check;
- no MYSTIC solver execution;
- no scientific result;
- no enabled authorization;
- no permission to reuse a runtime identity after any package, data, atmosphere or lock change;
- no production or physical-validity claim.

## Contract workflow

The contract workflow installs the exact locked runtime, recomputes all runtime hashes, builds an ephemeral scientific manifest from those hashes, and prepares the exact reference-style input for one case. The prepared input and runtime report are uploaded for review, but are never passed to `uvspec` as scientific input.

A later stage may add the guarded workflow-dispatch execution path only after this contract and its runtime artifact are reviewed.
