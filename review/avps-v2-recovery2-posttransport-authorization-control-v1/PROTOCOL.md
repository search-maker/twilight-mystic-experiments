# AVPS v2 recovery2 — post-transport authorization control

## Purpose

This is a fresh solver-free authorization-control gate chained to the successful post-native-transport preauthorization proof on PR #644, exact head `318eb6e133650244c396c930c0d498c935ea3857`. It exists because the native authorization-seed transport implementation is now merged to public `main` and every authorization-time collision/ordinal/identity surface must be observed again before a new scientific identity may be allocated.

Ordinals 41 and 42, their 72-seed sets, authorization/dispatch identities and attempt-1 failed runs are permanently consumed and non-reusable. Neither failure produced a scientific solver result. Recovery2 preserves the frozen scientific design unchanged: 360 cases, 72 CRN groups, five independently defined OPAC vertical-profile states, AOD550 0.10/0.30, four solar depressions, three geometries, three CRN replicates, 20,000,000 photon histories per case, fixed `continental_average` optical family, exact four-species OPAC transport, and the already-frozen analysis/result-opening rules. Taylor/Jerusalem residuals are not used.

The independently reviewed recovery2 candidate identity remains 72 candidates with seed canonical SHA-256 `38c074fe01bd6d09fa7dc78af1ad323e2f42b606ca992c2950b8fc1f5b343a9f` and row canonical SHA-256 `a88b28dcfaaeb354f294d1705a0f8ddbcd061083f277a038ab8c9dace44d9954`, with zero overlap against consumed ordinal-41/42 seeds.

The fresh predecessor proof is PR #644 / run `33265595046` attempt 1 / artifact `9718710154` / digest `sha256:e0eb535df7780308404a79736d9c2a42bcb3af9e0dcf9bc5431cd1757eaa28d6`. That proof dynamically observed occupied scientific ordinals 1..42 and successor 43 at its snapshot, but this control must not assume 43: it must repeat the live global ordinal observation and derive `occupiedMax + 1` under its own exact-head fence.

## Required review

The attempt-1 pull-request review must:

- bind exact base branch/head, exact control branch/head, exact two-file scope, and unchanged public `main`;
- require the control PR to remain Draft/open/unmerged;
- bind merged PR #643 and the native authorization-seed transport helper byte;
- bind merged seed proof PR #639 and successful seed-review artifact;
- bind successful post-transport preauthorization PR #644, dedicated proof artifact and generic contract run;
- verify ordinal-41 and ordinal-42 remain consumed failed attempt-1 identities;
- reconstruct the consumed ordinal-42 seed ledger only at its native historical authorization-head path in a detached worktree;
- rebuild the exact 72-candidate recovery2 ledger and prove zero overlap with both consumed seed sets;
- repeat tracked-tree and snapshot-fenced two-pass repository-global candidate-seed scans;
- dynamically derive the next unused global scientific ordinal, refuse an already-existing proposed authorization/dispatch ref or exact-looking Issue #60 marker, and never hard-code the successor;
- materialize a proposed `authorization.json` only as an Actions artifact, with the derived ordinal/ref names and exact control head as its prospective parent;
- preserve all no-rerun/no-retry/no-resume, protected-holdout, anti-fitting, result-opening, Level-B and production boundaries.

## Boundary

A successful control artifact is not an allocation. This PR creates no authorization branch, no dispatch branch, no ordinal allocation/consumed marker, no scientific runtime, no `uvspec`/MYSTIC execution, no AVPS result opening, no Level-B admission, no protected holdout access and no production change.

A later one-file authorization child must be a direct child of this exact reviewed control head and byte-equal to the successful control artifact's `authorization.json`. Its own fresh attempt-1 review must repeat the live seed/global-ordinal/identity fence before any Issue #60 allocation marker is written. Dispatch/science and result opening remain separately gated transitions.
