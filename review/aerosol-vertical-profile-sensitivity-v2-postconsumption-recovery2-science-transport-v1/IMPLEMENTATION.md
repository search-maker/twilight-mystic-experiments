# AVPS v2 recovery2 native seed-transport implementation

Status: **MECHANICAL IMPLEMENTATION / SOLVER-FREE / NO AUTHORIZATION / NO DISPATCH**

This is the implementation gate required by the already-merged recovery2 transport protocol before any fresh AVPS authorization allocation. It fixes only the path-context failure that consumed ordinal 42 before scientific runtime.

The reusable helper `native_authorization_seed_transport.py` validates an authorization-bound seed ledger only inside an exact detached worktree at the requested authorization head. It verifies that head has exactly the expected parent, that the ledger is a tracked repository-relative path with the exact expected Git blob, and that the path resolves inside the detached authorization worktree. It refuses absolute paths and `..` traversal.

Recovery2 seed validation also depends on the permanently consumed ordinal-42 seed ledger. The helper therefore creates a second detached historical worktree at the exact historical authorization head, verifies that historical ledger at its native tracked path and exact blob, exports only that native path through the explicit dependency environment variable, and then imports the fresh authorization ledger from its own native worktree path. Neither ledger is copied to a temporary standalone path before validation.

The helper validates the frozen 72-seed and candidate-row canonical hashes and zero overlap with the consumed ordinal-41 and ordinal-42 seed sets. It emits machine-readable ledger/context evidence including `relocatedBeforeValidation=false`, then removes both detached worktrees.

This PR does not alter `.github/workflows/avps-v2-postconsumption-recovery1-science.yml`; the consumed ordinal-42 workflow remains preserved. It does not create the future recovery2 science workflow or bind a future authorization head. A later separately reviewed recovery2 science workflow must call this merged helper before any runtime setup and must retain every existing one-use/seed/global-ordinal/closed-result guard.

The exact-head review exercises the helper against the already-reviewed recovery2 seed ledger on main and the historical ordinal-42 authorization head, and separately proves a relocated/path-escape request is refused. It also re-verifies run `33259899524` attempt 1 failed before profile recovery, OPAC acquisition, case jobs, `uvspec`, MYSTIC, aggregation or result opening.

No scientific matrix, geometry, profile definition, optical property, wavelength, estimator, aggregation, classification threshold, stopping/budget rule, CRN structure, or photon count changes here. The frozen design remains 360 cases, 72 CRN groups, five profile states, and 20,000,000 photon histories per case. No Taylor/Jerusalem residual is used. Ordinals 41 and 42 and their seed/run/dispatch identities remain permanently consumed and non-reusable.

This implementation authorizes no ordinal allocation, authorization branch, dispatch, solver execution, result opening, Level-B admission, protected holdout opening, Taylor/Jerusalem scoring, or production change. After merge, candidate-seed/global-preauthorization evidence must be refreshed against the new main before a future authorization child can be allocated.