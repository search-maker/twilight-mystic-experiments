# Execution handoff — ARM SGP C1 SASZE real-sky MYSTIC validation v1

This package is ready for repository review and exact-runtime execution control. It deliberately contains no SASZE comparison radiance values.

## Required execution order
1. Verify package SHA-256 manifest and repository/runtime identity.
2. Implement a fail-closed renderer that consumes only `frozen-config.json`, `uncertainty-scenarios.csv`, `screening-case-ledger.csv`, and `fex-profile-shapes.csv`.
3. Reuse the reviewed generic aerosol vertical-profile transport math; do not ad-hoc normalize layers. Construct per-scenario near-surface slab + elevated shape, then render custom `aerosol_file tau`.
4. Run exactly one syntax-only preflight (`uvspec -c`) on central -7 case. If it fails, stop before solver and before SASZE radiance access.
5. Allocate fresh candidate seeds only after repository-global collision scan and current control-issue admissibility review. No seed reuse.
6. Execute Phase 1 only. Aggregate cardinality/integrity before any model-based selection.
7. Select Phase-2 states using MYSTIC radiance only under the frozen rule; SASZE remains sealed.
8. Execute Phase 2 with three fresh CRN replicates/state. Enforce <=2% numerical gate.
9. Only then extract SASZE native 464.020874-nm samples using the frozen +/-15 s validity rule and perform comparison.
10. Publish raw outputs, MC std evidence, exact input texts, hashes, selections, and final comparison. No retuning.

## Exact point requiring a real MYSTIC runtime
The local ChatGPT analysis environment does not contain `uvspec`; solver dispatch must occur on the repository's reviewed libRadtran/MYSTIC runtime. Everything before that boundary is solver-free.
