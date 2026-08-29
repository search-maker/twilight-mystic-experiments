# AVPS v2 ordinal-41 pre-consumption publisher recovery1

Status: REVIEW ONLY. No scientific execution, dispatch publication, consumed-marker write, result opening, Level-B admission, or production transition is authorized by this package.

## Frozen incident

The original reviewed publisher run `33231924719`, attempt 1, job `99046120701`, failed in `Fresh zero-runtime pre-dispatch fence` before `Create exact dispatch ref and consumed marker once`, before publisher evidence upload, and before science dispatch. Ordinal 41 therefore remains allocated and reviewed but unconsumed. The original attempt must never be rerun, retried, or resumed.

The failure was mechanical: `review/aerosol-vertical-profile-sensitivity-v2-prereg/build_skeleton.py` hard-binds Git blob `d790fb3fa2d214d1f430f4417b17212a8e5038a8` at `review/aerosol-vertical-profile-sensitivity-v2-prereg/protocol.review.json`, but that preregistration file was omitted from default-branch publication. Recovery restores exactly that existing reviewed blob; it does not alter scientific design.

## Recovery contract

1. Restore only the already-reviewed preregistration blob `d790fb3fa2d214d1f430f4417b17212a8e5038a8` at its original path.
2. Preserve the published AVPS v2 science workflow blob `9970540d122a6feecbc19a34ec3e204e3aae10d9` and original publisher blob `ce572e89bc6ea67757190cd60bd515d457833450` unchanged.
3. Use a fresh publisher identity `.github/workflows/avps-v2-dispatch-publisher-recovery1.yml`; never rerun/retry/resume original publisher run `33231924719`.
4. Before any dispatch publication, recovery1 must independently prove the original failure was pre-consumption, rebind authorization PR #604/review evidence/allocation marker, prove no dispatch ref/consumed marker/science run exists, recompute the exact 72-seed ledger with canonical SHA-256 `02f624d582e9b2caba6b920d65a5e8a8bc8fc1a2693623bc2f73abf5d3f706d2`, rerun tracked-tree and repository-global collision scans, and rebind a successful attempt-1 implementation review to unchanged science/original-publisher bytes.
5. Only after that full fresh zero-runtime fence may recovery1 create `dispatch/aerosol-vertical-profile-sensitivity-v2-ordinal-41` at authorization head `d5f5e4d9d19d7ede573fecae68565a92baabbec3`, post exactly one `ORDINAL41_AVPS_V2_DISPATCH_CONSUMED` marker, upload publisher evidence, and request the existing `avps-v2-science.yml` once from `main` with that dispatch ref.
6. Because the connected operator lacks a direct workflow-dispatch primitive, a fresh one-use zero-runtime bridge may request only the recovery1 publisher. The bridge cannot create refs, post Issue #60 markers, call the science workflow, or run a solver.
7. Candidate seeds, ordinal, geometry, AOD, vertical templates, optical family, wavelength grid, photon budget, endpoints, contrasts, numeric rules, and anti-fitting boundaries are unchanged. Taylor/Jerusalem residuals are not inputs. Level-B admission and production remain blocked pending terminal AVPS v2 opening and separately reviewed mapper validation.

Any drift or ambiguity fails closed before dispatch publication.
