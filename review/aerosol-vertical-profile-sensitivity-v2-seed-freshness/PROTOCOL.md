# AVPS v2 candidate-seed freshness review

Status: **REVIEW ONLY / CANDIDATE SEEDS ARTIFACT-ONLY / NO ORDINAL / NO AUTHORIZATION / NO SOLVER**

## Prerequisite

This gate is permitted only after replacement preregistration PR #597 passed both exact-head gates on `2bba54c6e78ed99d169887eef51d0c88d812b6f1`:

- dedicated review `33193778176` — SUCCESS
- repository contract `33193778174` — SUCCESS
- prereg review artifact `9694863701`, digest `sha256:7de79aa4d8d9b51ad8ca4b1bdaceedae7ee5df17b3dd79c43c21cdaf9ae9a171`
- review receipt content SHA `717411c68c48f34f79c93da3ae8024e3d99a32c78ebe63935d262b3548e62c61`
- skeleton canonical SHA `a8d2d8f59aec01d82d8d98672152d00c11261660b0a69a59e2716c2edabd2b02`
- exactly 72 fresh CRN groups and 360 fresh `avps-v2-*` case identities
- seed count zero and scientific ordinal null in the preregistration artifact

## Candidate derivation

The safety shape of the old AVPS seed derivation is retained but no v1 namespace, group ID, or seed value is reused.

Frozen namespace:

`aerosol-vertical-profile-sensitivity-v2|group-seed|sha256-v1`

For each exact v2 group ID in skeleton order:

`seed = (uint64_be(SHA256(namespace|groupId|counter)[0:8]) % (2147483647-10000000)) + 10000000`

`counter` begins at 0 and increments only if needed to avoid an intra-ledger collision.

Frozen expected properties before repository scanning:

- candidate count 72
- 72 unique values
- every value lies in `[10000000,2147483647)` so the repository scanners can recognize any leaked decimal literal
- all collision counters are expected to remain zero
- candidate-seed canonical SHA-256 `02f624d582e9b2caba6b920d65a5e8a8bc8fc1a2693623bc2f73abf5d3f706d2`
- candidate-row canonical SHA-256 `41f70d6a0381db6b569d3f4e17d74bb38b05cf212c2f2e432455a502f73dc670`

The actual 72 values must not be tracked in Git, copied into the PR body, or applied to cases during this review. They exist only in the review artifact.

## Required freshness checks

1. rebuild the exact #597 skeleton and derive the deterministic artifact-only candidate ledger;
2. scan the exact tracked tree byte surface for every candidate decimal literal;
3. require zero tracked candidate literals outside the explicitly empty self-ledger policy;
4. run the bound repository-global two-pass scanner against branches, workflow-run metadata, artifacts, all-state PR and issue metadata/bodies, repository issue/PR/commit comments, and Issue #60 comments;
5. use the scanner's first-complete-enumeration snapshot fence and require stable collision-relevant content;
6. require zero historical and zero post-fence candidate-seed collisions;
7. require this v2 proof-artifact identity to be fresh;
8. preserve authorization-time recheck requirement because repository metadata can change after this review.

## Bound scanners

The v2 wrappers bind the already-reviewed generic scanners from frozen `main`:

- tracked-tree scanner blob `1c110d75b516cb7b9d50dc2674080f4a67e55d2a`
- repository-global scanner blob `4c6d704fa24228284780bcb1dd7c52537b4c5b0d`

No scanner semantics are weakened.

## Hard boundary

PASS means only: these 72 candidate values were fresh across the audited surfaces at this review checkpoint.

PASS does **not**:

- apply candidate seeds to the 360 cases;
- allocate scientific ordinal 41;
- create authorization or dispatch;
- run `uvspec`, DISORT or MYSTIC;
- open results;
- authorize Level-B or production.

After PASS, the next mandatory step is a fresh Issue #60 + authorization/dispatch branch audit immediately before ordinal allocation/authorization, together with an authorization-time repeat of repository-global seed freshness. If ordinal 40 is still the latest consumed ordinal at that later checkpoint, 41 is expected next; it is not allocated here.
