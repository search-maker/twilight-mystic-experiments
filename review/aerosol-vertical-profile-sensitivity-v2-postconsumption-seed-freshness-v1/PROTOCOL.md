# AVPS v2 post-consumption recovery1 candidate-seed freshness review

This is a solver-free, result-closed identity-recovery gate after ordinal 41 was consumed exactly once by workflow run `33236295233` attempt 1 and then failed structurally before any scientific solver execution because the already-reviewed support byte `rh_audit_dependency.py` had not been transported onto default-branch `main`.

## Immutable predecessor facts

- consumed marker: `ORDINAL41_AVPS_V2_DISPATCH_CONSUMED`;
- consumed scientific identity: ordinal `41`, execution key `aerosol-vertical-profile-sensitivity-v2:numerical:41`;
- failed run: `33236295233`, attempt 1;
- ordinal-41 preflight artifact: `9710095370`, digest `sha256:64a00547a8d0be68322a58db239e9fbc57ad477938efd5d9254fa0098fe879f2`;
- ordinal 41, its 72 group seeds, dispatch identity, and run identity are permanently non-reusable;
- exact missing support byte was restored by merged PR #621; current recovery base is `6f0b3f3c73b23f84951bd7b6a2bad58d00854982`;
- restored path `review/aerosol-vertical-profile-sensitivity-v2-control-v1/rh_audit_dependency.py` must remain Git blob `095ff86f12a79dc312a51f734b0a03bd318f2337`.

No numerical conclusion is inherited from ordinal 41. The frozen AVPS-v2 scientific question, 360-case / 72-CRN-group / five-state universe, physical inputs, vertical templates, aerosol family, AOD levels, geometries, 20M-photon budget, primary endpoints, analysis rules, result-opening rules, and anti-fitting boundaries remain unchanged.

## New recovery identity, frozen before scanning

Candidate seed namespace:

`aerosol-vertical-profile-sensitivity-v2|postconsumption-recovery1|group-seed|sha256-v1`

The deterministic candidate set contains exactly 72 signed-32-bit scanner-visible group seeds. Seed values are artifact-only and must never be committed, placed in PR/Issue text, or applied to cases at this gate.

Frozen candidate identities:

- candidate-seed canonical SHA-256: `a514212990a94a39d577bd038b631a600e18e4c0f750f781bbd7c99b897228a7`;
- candidate-row canonical SHA-256: `8213e65782b62d0e1a0ea51d620016fdcaa24b348e726f5570c54f7f1155a895`;
- overlap with consumed ordinal-41 seed set: exactly `0`.

## Required review gate

The exact PR head must:

1. remain a direct descendant of recovery base `6f0b3f3c73b23f84951bd7b6a2bad58d00854982` and contain only this review package;
2. rebind the unchanged AVPS-v2 preregistration skeleton Git blob `b4a4ab6917ad28f08d4980194f7b68f3961d5d59` and canonical skeleton `a8d2d8f59aec01d82d8d98672152d00c11261660b0a69a59e2716c2edabd2b02`;
3. bind the consumed ordinal-41 seed-ledger Git blob `c757507b05074340507df1ca6e76d35b44cf6090` and prove the new candidate set has zero overlap with it;
4. prove the merged runtime support repair blob is still exact;
5. scan the exact tracked tree for any new candidate-seed literal, permitting no tracked self-ledger;
6. perform the unchanged two-pass repository-global scan with snapshot fencing across branches, Actions runs/artifacts, all-state PRs/issues, issue comments, PR-review comments, commit comments, and Issue #60 comments;
7. require zero external collisions and a stable fenced surface;
8. upload the candidate values only inside the immutable review artifact `vertical-profile-v2-postconsumption-recovery1-seed-freshness-proof`;
9. publish at most a non-seed checkpoint containing only candidate hashes/counts and zero-collision status.

## Hard boundary

This review does **not** choose or allocate a new scientific ordinal. It does not create an authorization branch, dispatch branch, consumed marker, scientific run, solver runtime, result opening, Level-B opening, protected-holdout transition, Taylor/Jerusalem scoring, or production transition.

After this seed-freshness gate passes, a **separate fresh repository-global preauthorization/ordinal review** must derive whatever global scientific ordinal is then available. It must not assume ordinal 42. Candidate freshness must be rechecked again at authorization time. Any later scientific execution requires a separately reviewed fresh authorization and execution identity; ordinal 41 and its seeds remain permanently consumed.
