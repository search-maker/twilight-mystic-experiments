# R4 changes

R4 is review-only and performs no scientific execution.

- Replaced the sequential R3 candidate seed range with 72 deterministic SHA-256-derived seeds bound to analysis-cell identity and replicate.
- Added `candidate-seed-ledger.v1.json` with exact derivation material hashes and a frozen namespace.
- Changed tracked-tree and historical-surface scanners to consume the explicit non-contiguous candidate ledger rather than assuming a contiguous range.
- Aligned seed-freshness governance with current repository preauthorization precedent: exact-head tracked-tree scan plus repository-global branches / Actions-run / artifact-metadata / Issue #60 collision surfaces, followed by a mandatory authorization-time recheck.
- Retained the raw Actions log/artifact ZIP scanner as an optional stricter forensic diagnostic, not an impossible requirement to recover expired historical bytes.
- Bound any future seed proof to both exact `design.review.json` bytes and exact candidate-ledger bytes/namespace.
- Added repository-global collision-surface unit tests.
- No result was opened, no `uvspec -c` was run, and no MYSTIC solver was invoked.
