# Training continuation disabled transport v1

Review-only transport for the two continuation-required geometries after PR #134.

- `train0014`: exact four-block 600 nm fresh acquisition, 200M histories total.
- `train0037`: exact 500/550/600 comparison, four blocks per center, 1.2B histories total.
- analysis and normalization are frozen before any fresh result.
- no ordinal, authorization ref, execution key, dispatch branch, or scientific run is allocated here.
- no workflow in this package invokes `executor_v1.py` or a solver.
- after merge, repository-global preauthorization must be repeated; a separate activation/authorization lifecycle is required.

Transport contract SHA-256: `eb66408e40776aadc18440ff20c25308ac3a8b099fd6d6ff0249f46b70c5bfcf`
Analysis contract SHA-256: `1f7dc8cc71beeb2b56a15a137f377317ae0de90de088ea429fc2eafedcc89c0c`
