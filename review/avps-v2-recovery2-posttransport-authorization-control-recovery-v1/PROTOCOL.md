# AVPS v2 recovery2 — post-transport authorization-control recovery

## Purpose

This is a fresh solver-free recovery of the post-native-transport authorization-control gate after PR #645 / exact head `06ad291093e5179d17981d6a8b89c7e7ecc6100d` / run `33266397565` attempt 1 failed mechanically before any repository-global scan or authorization proposal was produced. The failed run is immutable evidence and must never be rerun, retried or resumed.

The failure occurred in `Rebuild candidate ledger at native historical ordinal-42 path`: the workflow wrote `AVPS_ORDINAL42_LEDGER_PATH` only to `$GITHUB_ENV` and then consumed it in Python within the same Actions step. `$GITHUB_ENV` only affects later steps, so the imported recovery2 seed ledger could not see the required environment variable. This recovery changes only that transport of the already-frozen native historical ledger path: it exports the variable in the current shell before the Python import and also writes it to `$GITHUB_ENV` for later steps.

No scientific design, seed derivation, profile family, atmosphere, geometry, photon budget, analysis rule, result-opening rule or Level-B boundary changes. The successful post-transport preauthorization proof remains PR #644 / exact head `318eb6e133650244c396c930c0d498c935ea3857` / run `33265595046` attempt 1 / artifact `9718710154` / digest `sha256:e0eb535df7780308404a79736d9c2a42bcb3af9e0dcf9bc5431cd1757eaa28d6`.

Ordinals 41 and 42, their 72-seed sets, authorization/dispatch identities and failed attempt-1 runs remain permanently consumed and non-reusable. Neither produced a scientific solver result. Recovery2 continues to preserve the frozen science: 360 cases, 72 common-random-number groups, five independently defined OPAC vertical-profile states, AOD550 0.10/0.30, four solar depressions, three geometries, three CRN replicates, 20,000,000 photon histories per case, fixed `continental_average` optical family, exact four-species OPAC transport, and the frozen analysis/result-opening rules. Taylor/Jerusalem residuals are not used.

The independently reviewed recovery2 candidate identity remains 72 candidates with seed canonical SHA-256 `38c074fe01bd6d09fa7dc78af1ad323e2f42b606ca992c2950b8fc1f5b343a9f` and row canonical SHA-256 `a88b28dcfaaeb354f294d1705a0f8ddbcd061083f277a038ab8c9dace44d9954`, with zero overlap against consumed ordinal-41/42 seeds.

## Required review

The fresh attempt-1 pull-request review must:

- bind exact base branch/head, fresh recovery branch/head, exact two-file recovery scope and unchanged public `main`;
- bind failed PR #645/run `33266397565` attempt 1 as terminal failed immutable evidence, never as reusable execution;
- require the recovery PR to remain Draft/open/unmerged;
- bind merged PR #643 and the native authorization-seed transport helper byte;
- bind merged seed proof PR #639 and its successful seed-review artifact;
- bind successful post-transport preauthorization PR #644, dedicated proof artifact and generic contract run;
- verify ordinal-41 and ordinal-42 remain consumed failed attempt-1 identities;
- reconstruct the consumed ordinal-42 seed ledger only at its native historical authorization-head path in a detached worktree, with the path exported into the current shell before importing the recovery2 ledger;
- rebuild the exact 72-candidate recovery2 ledger and prove zero overlap with both consumed seed sets;
- repeat tracked-tree and snapshot-fenced two-pass repository-global candidate-seed scans;
- dynamically derive the next unused global scientific ordinal, refuse an already-existing proposed authorization/dispatch ref or exact-looking Issue #60 marker, and never hard-code the successor;
- materialize a proposed `authorization.json` only as an Actions artifact, with the derived ordinal/ref names and exact recovery-control head as its prospective parent;
- preserve all no-rerun/no-retry/no-resume, protected-holdout, anti-fitting, result-opening, Level-B and production boundaries.

## Boundary

A successful recovery-control artifact is not an ordinal allocation and is not a dispatch. This PR creates no authorization branch, no dispatch branch, no ordinal allocation/consumed marker, no scientific runtime, no `uvspec`/MYSTIC execution, no AVPS result opening, no Level-B admission, no protected holdout access and no production change.

A later one-file authorization child must be a direct child of the exact successfully reviewed recovery-control head and byte-equal to its successful `authorization.json` artifact. Its own fresh attempt-1 review must repeat the live seed/global-ordinal/identity fence before any Issue #60 allocation marker is written. Dispatch/science and result opening remain separately gated transitions.
