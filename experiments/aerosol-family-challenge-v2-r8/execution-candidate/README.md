# Execution candidate — R8 review-only, not authorized

This directory contains a hard-disabled transport candidate. It is not an active workflow and does not carry a frozen manifest, fresh scientific ordinal, execution key, enabled authorization, control marker or dispatch ref.

## Constructible authorization lifecycle

R8 preserves the rule that avoids embedding an authorization commit's own SHA inside the authorization document. A future enabled document binds the then-live parent commit and exact hashes of the frozen manifest, freeze record, transport contract, adapter, executor, workflows and guards while `exactAuthorizationCommit` remains null. The real child commit SHA is bound externally by Git metadata.

A valid authorization transition additionally requires:

- the fresh next global scientific ordinal and execution key;
- a one-parent commit changing exactly `experiments/aerosol-family-challenge-v2-r8/authorization.json`;
- a same-repository Draft/open/unmerged PR;
- an attempt-1 `pull_request: opened` review with no scientific runtime setup or execution;
- all-state PR/issue/control/code identity freshness;
- a fresh exact-head seed collision proof;
- exactly one Issue #60 marker binding ordinal, authorization head, parent and PR number;
- a later dispatch branch pointing to the reviewed authorization head.

The included regression test constructs the one-file authorization commit in a real temporary Git repository and verifies that self-embedding the head SHA is refused.

## Execution boundary

The case executor requires both explicit execution opt-in and a guard report with status `EXACT_ONE_USE_AEROSOL_FAMILY_V2_R8_DISPATCH_AUTHORIZED`. The guard requires post-dispatch freshness, zero prior dispatch use, zero prior aerosol-family case artifacts, no consumed marker, and all closed protected/fitting/production boundaries.

Before a case can invoke the syntax check or solver, its runtime report must match the frozen runtime identity and explicitly state `scientificSolverExecuted=false`. The case contract then allows exactly one syntax check and one solver invocation, no retry/resume/rerun, and preserves the complete raw evidence surface and hashes.

The intended future transport is four 144-case shards keyed by Sun depression (2, 4, 6, 8 degrees), avoiding the GitHub Actions matrix-size ceiling without changing scientific inputs. The template remains hard-disabled and cannot execute cases as shipped.

## R8 proof/freeze prerequisite

Before an enabled authorization can bind manifest/freeze bytes, the review-only seed-proof workflow must already have run from an exact default-branch HEAD and produced a stable two-pass repository-global seed proof. The same run freezes and uploads the proof bundle. Those exact bytes must then be preserved in a separate evidence-only commit at the predeclared `evidence/aerosol-family-challenge-v2-r8/` paths. Artifact retention by itself is not treated as permanent evidence. Authorization still requires a new exact-head seed/identity recheck after that preservation change.

R8 distinguishes the one-time `review-freeze` seed audit from the later `authorization-recheck`. Scientific dispatch requires the latter on the exact authorization head; the execution guard refuses a review-freeze proof in its place. The original review-freeze is attempt-1 only and refuses a prior proof artifact identity.

The authorization-time seed audit is also re-bound to the frozen scientific identity: its 72-seed count, first/last seed, canonical seed-ledger SHA and derivation namespace must match the frozen manifest/core identity, and its audited authorization branch must still point to the exact reviewed authorization HEAD.
