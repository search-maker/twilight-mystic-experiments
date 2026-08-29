# AVPS v2 ordinal-41 default-branch publication v1

Status: **PUBLICATION REVIEW ONLY / SOLVER FREE / NO DISPATCH**

Purpose: publish onto `main` only the exact already-reviewed callable AVPS-v2 ordinal-41 implementation bytes needed for the later zero-runtime dispatch publisher and attempt-1 science workflow. This publication does not allocate or consume any identity, does not create the dispatch ref, does not post the consumed marker, does not run libRadtran/MYSTIC, does not open results or Level-B, and does not authorize production or Taylor/Jerusalem scoring.

Frozen source implementation review:
- source PR #609 exact head `2b0c349ad49678867742df5995ad13a23dc3f259`
- review run `33229229379`, attempt 1, SUCCESS
- review artifact `9707919147`, digest `sha256:3c49e9f14c8018a609726c67a9a45f1ca204119535569650cf31406fbc560e8b`
- review status `PASS_SOLVER_FREE_SCIENCE_WORKFLOW_AND_ZERO_RUNTIME_PUBLISHER_REVIEW_DISPATCH_NOT_CREATED`
- science workflow SHA-256 `f6d24a33d923bd4fa621a153dbeeddd35301551acc4d4aea32191e62735d1dc5`
- publisher workflow SHA-256 `e702518a88cdf9f88e00ec9b1021ea9d023dbb2e90dbe48443bfd667b2319478`

The publication is an exact-byte copy of the minimal runtime dependency closure from the reviewed source lineage. The local copy of `review/aerosol-vertical-profile-sensitivity-v2-authorization-control-v4/authorization.json` is only a byte-bound reference required by the reviewed executor. Scientific authority remains the detached immutable authorization head `d5f5e4d9d19d7ede573fecae68565a92baabbec3`, authorization PR #604 remains Draft/open/unmerged, and the science workflow independently fetches and verifies that detached authorization before runtime.

After this publication is reviewed and merged to `main`, a fresh pre-dispatch fence is still required. Ordinal 41 must remain unconsumed until that later zero-runtime publisher passes all exact authorization, marker, dispatch-absence, candidate-seed freshness, and reviewed-byte checks. No GitHub Re-run/retry/resume is permitted for the future scientific identity.