# R5 changes

R5 is review-only and performs no scientific execution.

- Corrected the review provenance statement for the source-bound geometries: g02, g04 and g06 all use observer elevation 0 m in the exact current-main cross-geometry manifest. The earlier 0/1000/2000 m description was incorrect and is not used by the design.
- Replaced the unconstructible authorization self-reference from R4. An enabled authorization now requires `exactAuthorizationCommit: null`; the parent and payload byte hashes are embedded, while the real authorization HEAD is bound externally through Git metadata, zero-runtime review, control marker and dispatch ref.
- Added a real-Git regression that commits the frozen transport as a base, then creates a child commit changing exactly `experiments/aerosol-family-challenge-v2/authorization.json`, proving the lifecycle is constructible without a self-hash paradox.
- Added separate `freshness.py`, `authorization_guard.py`, `dispatch_guard.py`, an attempt-1 zero-runtime authorization-review workflow template, and a v2 transport contract.
- Expanded repository-global candidate-seed collision coverage to all-state PRs/issues and repository-wide issue, pull-review and commit comments in addition to branches, Actions runs/artifact metadata and Issue #60.
- Bound the review design to the exact local candidate-seed ledger bytes, not just a 64-hex placeholder.
- Kept raw historical artifact-byte scanning as optional forensic strengthening rather than a permanently impossible prerequisite when historical artifacts have expired.
- Added a pre-solver runtime-report guard requiring `scientificSolverExecuted=false`, plus explicit case-input/runtime/radiance/std-radiance hashes in `case-result.json`.
- Fixed a pre-result analysis mismatch by adding the separate preregistered directional strong-ratio flag: ratio `>=1.5` or `<=2/3` is strong; ratio `>=2` or `<=0.5` is very large. The fractional-change interpretation bands remain separately reported.
- Added regressions for all of the above, including exact rendered aerosol directives for all 576 cases, CRN pairing, expanded seed surfaces, real Git authorization constructibility, dispatch marker enforcement, pre-solver runtime provenance and strong-ratio boundaries.
- No result was opened, no real `uvspec -c` was run, and no real MYSTIC solver was invoked.
