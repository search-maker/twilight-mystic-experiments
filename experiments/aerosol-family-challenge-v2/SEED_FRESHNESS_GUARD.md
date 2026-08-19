# Seed freshness guard required before preregistration freeze — R6

The 72 SHA-256-derived comparison-group seeds in `candidate-seed-ledger.v1.json` and `design.review.json` are candidate identities only. R6 does not claim that they are fresh.

## Distinct Git identities

`sourceBaseMainSha` binds the reviewed scientific/runtime sources. A later `seedAuditExactHead` must bind the published review head containing this package. Any authorization head is a further, later identity and requires a new recheck. These identities are intentionally distinct.

## Required preregistration proof

The only freeze-eligible seed proof status is:

`PASSED_EXACT_HEAD_TRACKED_TREE_AND_REPOSITORY_GLOBAL_COLLISION_SURFACES_NEGATIVE_CHECK`

### 1. Exact-head tracked-tree byte scan

`tracked_tree_seed_scan.py` must run on the exact published review head, enumerate `git ls-files -z`, and scan every tracked byte stream for all 72 candidate integers, including underscore-formatted numeric literals. Candidate occurrences are allowed only in the paths listed by `seed-self-ledger-paths.json`. Any external occurrence refuses the proof.

### 2. Expanded repository-global collision scan

`repository_global_seed_scan.py` must paginate and inspect:

- all repository branch metadata;
- all GitHub Actions run metadata;
- all repository Actions artifact metadata;
- all-state pull-request metadata and bodies;
- all-state issue metadata and bodies;
- all repository issue comments;
- all repository pull-review comments;
- all repository commit comments;
- all Issue #60 comments.

Only the metadata record for the currently executing pre-solver audit run may be excluded, and its run ID is bound into the merged proof. Any candidate seed on an external scanned surface refuses the proof.

The optional `actions_artifact_seed_scan.py` can inspect retained raw log/artifact ZIP bytes as a stricter forensic diagnostic. Recovery of every expired historical artifact byte is not a mandatory gate.

## Proof merge

`merge_seed_proof.py` binds the exact review head, source base, exact design bytes, exact deterministic candidate-ledger bytes/namespace, tracked-tree result, expanded repository-global result, and current audit run ID. It must report zero external collisions and must keep `authorizationPermitted: false`.

## Authorization-time recheck

Preregistration freshness does not reserve a seed or scientific identity. Before scientific dispatch, the separate authorization/dispatch guards must repeat exact-head seed and identity freshness against the then-current repository state, require the constructible one-file authorization lifecycle and exact control marker, and refuse any intervening collision or identity consumption. GitHub Re-run, retry and resume remain forbidden.

## Stable enumeration and proof persistence (R6)

The repository-global collector performs two complete paginated enumerations. The first complete enumeration establishes a deterministic snapshot fence after removing only the current audit run row and artifact metadata created by that same run. Branches are fenced by the complete first-pass branch-name set; append-only GitHub surfaces are fenced by their first-pass high-water numeric row IDs. The second complete enumeration must reproduce every fenced row after lifecycle normalization. Edits, deletions, conflicting pagination duplicates, or head movement of any fenced branch therefore remain fail-closed.

Rows created after the first-pass fence are not allowed to make an otherwise fixed historical snapshot impossible to reproduce on an active repository. They are excluded only from the stability fingerprint, are still inspected immediately for candidate-seed literals, and any post-fence candidate-seed occurrence refuses the audit. A review-proof artifact is checked outside the fence and therefore also refuses the initial `review-freeze` even if it appeared after the fence. The audited branch head is queried again after both complete enumerations and must still equal the exact expected head. All later post-fence activity remains subject to the mandatory authorization-time repository-global recheck before any scientific dispatch.

The review proof is usable only when the workflow exists on the default branch. A successful run creates the exact proof/freeze files under `evidence/aerosol-family-challenge-v2/`, uploads them as one review artifact, and requires a later evidence-only preservation commit. Future evidence paths are predeclared as self-ledger locations so later exact-head scans can permit the frozen candidate seed bytes there without weakening collision checks elsewhere.

## One-time review-freeze identity and later authorization mode

The post-merge preregistration proof runs in explicit `review-freeze` mode and only on GitHub Actions attempt 1. Repository-global artifact metadata must contain zero earlier artifacts named `aerosol-family-v2-r6-freeze-proof` after excluding only the current run's own self-metadata; a prior proof artifact makes a second review-freeze attempt ineligible. This prevents two independent manual dispatches from manufacturing competing freeze identities.

The later pre-dispatch seed audit is a distinct `authorization-recheck` mode. A historical review proof artifact may exist there because the preregistration freeze has already been preserved; that audit cannot be used as a substitute for the original review-freeze proof, and `freeze.py` explicitly refuses it.

Artifact retention is not the only one-use signal. The initial `review-freeze` tracked-tree proof also requires zero pre-existing paths from the predeclared permanent evidence set. Once the first proof is preserved under `evidence/aerosol-family-challenge-v2/`, those paths remain allowed seed self-ledgers for later exact-head scans but permanently make another `review-freeze` ineligible, even if the original Actions artifact later expires or is deleted.

Stable pagination does not by itself prove that the checked commit is still the intended branch head. The repository-global audit therefore records the audited branch name, the observed branch-head SHA, and whether it equals the expected repository head. `review-freeze` requires the exact default-branch head used by the workflow dispatch; `authorization-recheck` requires the exact authorization-branch head. A branch that moved before both enumeration passes is still rejected.

The fenced two-pass fingerprint is a deterministic canonical representation of the complete collision-relevant first-pass universe: stable row identities plus all non-operational fields/content, with rows and nested arrays sorted deterministically. Only inherently mutable lifecycle metadata (timestamps, status/state, conclusion and retry/expiry fields) is omitted. Thus harmless pagination order, lifecycle drift, and non-seed post-fence arrivals are tolerated, while any fenced branch/head, artifact-name, PR/issue body, comment, or candidate-seed change remains a stability failure and stays fail-closed.
