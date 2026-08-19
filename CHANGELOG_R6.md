# R6 changelog — pre-result review transport hardening

R6 supersedes R5 before publication. No scientific result was opened and no solver was run.

- Fixed the review seed-proof lifecycle so a successful proof is not ephemeral: the same review-only run now creates `manifest.frozen.json` and `freeze-record.json`, hashes the six-file proof bundle, and persists it as artifact `aerosol-family-v2-r6-freeze-proof`.
- Added an explicit evidence-only preservation lifecycle. The Actions artifact is transport evidence, not permanent archival evidence; its six files must later be copied byte-for-byte to predeclared `evidence/aerosol-family-challenge-v2/` paths before authorization.
- Predeclared future evidence paths as seed self-ledger locations without requiring them to exist on the initial review head. Required current self-ledgers still must exist.
- Added stable **double enumeration** of repository-global metadata. The two complete snapshots must have identical canonical external bytes after excluding only the current audit run and same-run proof-artifact metadata; otherwise the audit refuses.
- Separated actual issues from pull requests in the REST `/issues` surface, because GitHub's issues endpoint includes pull requests while PRs are already enumerated independently.
- Bound the R6 freeze and authorization-time guards to the two-pass stability evidence.
- Upgraded the active review transport contract to `transport-contract.v3.json`; R5 `v2` is retained only under `reference/superseded-pre-result/`.
- Pinned the review proof workflow's external actions by full verified commit: `actions/checkout` v7.0.1 and `actions/upload-artifact` v7.0.1.
- Documented the GitHub lifecycle constraint that `workflow_dispatch` must be present on the default branch before it can be triggered; the proof is therefore a post-merge, pre-authorization, zero-scientific-runtime review gate.
- Added explicit seed-audit modes. The one-time preregistration freeze uses `review-freeze`; authorization-time freshness uses `authorization-recheck` and cannot be substituted for the freeze proof.
- Made the review-freeze workflow attempt-1 only and fail-closed when prior metadata already contains artifact `aerosol-family-v2-r6-freeze-proof`, preventing a second manual proof run from silently creating a competing preregistration freeze identity.
- Added direct regressions for predeclared future seed self-ledger paths: they may be absent on the review head, required current paths may not be absent, and later evidence files may contain the frozen candidate seeds only at those exact predeclared paths.
- Closed the post-retention duplicate-proof loophole: `review-freeze` also requires zero pre-existing permanent evidence self-ledger paths, so expiration/deletion of the Actions artifact cannot make a second preregistration freeze eligible after evidence preservation.
- Bound the repository-global audit to an explicit branch head. A stable two-pass snapshot is insufficient if the audited branch has moved away from the workflow/authorization SHA; review-freeze now requires the exact default-branch head and authorization-recheck requires the exact authorization-branch head.
- Strengthened the execution guard so the authorization-time seed audit must bind the exact 72-seed canonical ledger and derivation namespace carried by the frozen manifest, rather than relying on a PASS status alone.
