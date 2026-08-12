# Training continuation disabled transport v1

Review-only transport for the two continuation-required geometries after PR #134.

- `train0014`: exact four-block 600 nm fresh acquisition, 200M histories total.
- `train0037`: exact 500/550/600 comparison, four blocks per center, 1.2B histories total.
- analysis and normalization are frozen before any fresh result.
- no ordinal, authorization ref, execution key, dispatch branch, or scientific run is allocated here.
- no workflow in this package invokes `executor_v1.py` or a solver.
- after merge, repository-global preauthorization must be repeated; a separate activation/authorization lifecycle is required.

Transport contract SHA-256: `103266ce52879245a7ce175f74ad29ab0f8713c7cfc1d9c6931ef0e33969abb6`
Analysis contract SHA-256: `31218e4263603aef3b676a82e07180076a9fc67b71c60dc861104b90bf0ac885`
