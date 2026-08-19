# r2 accuracy changes

- Corrected selected pilot observer elevations to canonical `0 m / 0 m / 0 m`; removed the erroneous 1000 m / 2000 m working-note values.
- Converted geometry and photon budget from "historical values missing" to explicit **new v2 choices** with exact source-path and Git-blob bindings.
- Frozen selected view geometries to g02/g04/g06 and uniform 20M histories per case; derived 11.52B total configured histories.
- Rejected candidate seed prefix `1910000` after a repository-code match; versioned candidate ledger to `1911000001..1911000072`.
- Recorded a clean review-time indexed/control-surface snapshot for `1911000`, while explicitly preserving exact-tree and complete artifact-history scans as pending.
- Strengthened `freeze.py`: a separate seed proof must bind exact design bytes, exact seed list, exact-head tracked-tree scan, complete run-history/artifact scan and zero collisions before any manifest/freeze output is written.
- Expanded focused regression coverage from 13 to 20 tests, including geometry drift, photon-budget drift, candidate-ledger drift, incomplete-proof refusal, exact-design audit binding and closed success-path semantics.
