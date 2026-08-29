# AVPS v2 post-consumption recovery authorization-review infrastructure v1

Status: review-only infrastructure proposal. No authorization identity is allocated by this package, no dispatch ref is created, no scientific runtime or solver is executed, and result opening, Level-B, protected holdout, Taylor/Jerusalem fitting, and production remain closed.

## Frozen predecessor

The package is tied to recovery authorization-control PR #625 exact head `a68f603d6da21cd28ab8324da080cc8ad27f9094`, dedicated attempt-1 control run `33246777379`, and unexpired artifact `9713174217` digest `sha256:d96c4351bd5384a90af0c55b734c7508716689fa5eb1f9811a07f94d71e0c290`. That artifact proposes, but does not allocate, the then-fresh successor ordinal 42 after consumed ordinal 41, with 72 recovery CRN-group seeds whose canonical SHA-256 is `a514212990a94a39d577bd038b631a600e18e4c0f750f781bbd7c99b897228a7` and zero overlap with the consumed ordinal-41 seed set.

## Purpose

A one-file authorization commit must remain a direct child of the exact reviewed control head so its bytes can exactly match the already-reviewed `authorization.json` proposal, including `exactAuthorizationParentCommit`. Adding the review workflow to that control branch would change the parent and invalidate those bytes. Therefore this package publishes a read-only `pull_request_target` authorization-review workflow on default `main`. That workflow can review an authorization PR whose base remains the exact control branch/head without mutating the control lineage.

## Authorization-review contract

The target workflow is restricted to an `opened` pull request targeting `review/aerosol-vertical-profile-sensitivity-v2-postconsumption-authorization-control-v1` and changing only `review/aerosol-vertical-profile-sensitivity-v2-postconsumption-authorization-control-v1/authorization.json`. It requires the exact authorization branch proposed by the frozen control artifact, exact base head `a68f603d6da21cd28ab8324da080cc8ad27f9094`, one direct parent, Draft/open/unmerged same-repository state, and attempt 1.

Before passing it must:

1. bind the successful PR #625 control run/artifact and prove the authorization bytes are identical to the reviewed artifact proposal;
2. rebuild the fresh 72-seed recovery ledger and perform an exact-head tracked-tree scan;
3. perform a fresh repository-global candidate-seed scan with a post-fence recheck;
4. re-enumerate the global scientific-ordinal surface while excluding only the current authorization branch/PR/workflow self-observations;
5. prove ordinal 41 remains consumed, the proposed successor is still the next available ordinal, no independent reservation/allocation of that successor exists, no dispatch ref exists, and no Issue #60 marker exists;
6. emit an immutable authorization-review receipt stating that allocation, dispatch, solver execution, result opening, Level-B, holdout and production remain false.

If the global surface moves so that ordinal 42 is no longer the next free successor, this workflow fails closed. A new reviewed preauthorization/control identity must then derive the actually fresh successor; the number 42 is not a standing entitlement.

## Security and runtime boundary

The `pull_request_target` job has read-only GitHub permissions and `persist-credentials: false`. It executes only after proving the PR is a same-repository, one-file, direct-child identity from the exact reviewed control head. It contains no workflow dispatch, branch creation, marker write, solver command, MYSTIC execution, result opening, Level-B activation, or production transition.
