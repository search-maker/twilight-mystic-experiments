# AVPS v2 post-consumption recovery1 preauthorization review

Status: **REVIEW ONLY / FRESH GLOBAL-ORDINAL OBSERVATION / AUTHORIZATION-TIME SEED RECHECK / NO ALLOCATION / NO SOLVER**

## Purpose

Ordinal 41 and its 72 group seeds, authorization/dispatch identity, and scientific run identity are permanently consumed by AVPS-v2 run `33236295233` attempt 1. That run failed structurally before scientific solver execution. Merged PR #621 restored the already-reviewed missing runtime support byte without changing scientific physics.

The successor seed-freshness review is Draft PR #622 at exact head `3f9a03b913125077a37a3eb56d1c031127bdfd60`. Its dedicated attempt-1 review run `33242753388` succeeded and produced artifact `9711902664`, digest `sha256:12934972f2a533c006a11012d2f2374e76873d9982dae0b1d5db656e6097b460`. The frozen recovery candidate-seed canonical SHA-256 is `a514212990a94a39d577bd038b631a600e18e4c0f750f781bbd7c99b897228a7`; the row canonical SHA-256 is `8213e65782b62d0e1a0ea51d620016fdcaa24b348e726f5570c54f7f1155a895`; overlap with the consumed ordinal-41 seed set is exactly zero. Actual seed values remain artifact/workspace-only.

## Required gate

This review must:

1. bind exact public `main` `6f0b3f3c73b23f84951bd7b6a2bad58d00854982` and the exact successful #622 seed-review evidence;
2. preserve the unchanged AVPS-v2 360-case / 72-CRN-group / five-state scientific design and the restored support byte;
3. regenerate the exact recovery candidate ledger in the workspace only;
4. repeat the exact tracked-tree candidate-literal scan and require zero tracked candidate values;
5. repeat the unchanged snapshot-fenced repository-global candidate-seed scan in `authorization-recheck` mode and require zero collisions and exactly one prior recovery seed-review proof artifact;
6. use the already-reviewed conservative repository-global scientific-ordinal observation parser to enumerate all authoritative authorization/dispatch refs, runs, PR heads, artifacts, exact Issue #60 allocation/consumption markers, and positive identity claims;
7. require ordinal 41 to remain authoritatively consumed, treat every observed higher scientific ordinal as occupied/reserved, and derive the next candidate ordinal as `max(authoritative observed ordinals) + 1`;
8. require the proposed AVPS-v2 recovery authorization and dispatch branches for that dynamically derived ordinal to be absent;
9. repeat the ordinal observation scan immediately before proof publication and fail closed if the surface changes.

## Hard boundary

PASS is only a non-allocation preauthorization proof. It does not allocate or reserve the reported ordinal, apply candidate seeds to cases, create authorization/dispatch, execute `uvspec`/MYSTIC, open results, open Level-B or protected holdouts, use Taylor/Jerusalem residuals, or alter production.

The next step after PASS is a separately reviewed one-file authorization allocation using the exact reported fresh ordinal and the exact recovery candidate-seed artifact, followed by the existing guarded execution chain. The successor ordinal is never assumed in advance; in particular this review must not hard-code ordinal 42 as available.