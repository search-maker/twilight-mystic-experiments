# AVPS v2 ordinal-41 publisher recovery1

Status: **review-only, zero-runtime recovery; ordinal 41 remains allocated and unconsumed until a separately reviewed recovery activation passes its fresh fence.**

## Failure being recovered

The original reviewed publisher ran exactly once as GitHub Actions run `33231924719`, attempt 1, on main `e3ab0b7c7dae02773fc4756325dcc4d15efabd65`. It failed in `Fresh zero-runtime pre-dispatch fence` while rebuilding the already-frozen AVPS-v2 candidate-seed ledger because the default branch lacked `review/aerosol-vertical-profile-sensitivity-v2-prereg/protocol.review.json`.

The failed run did **not** create `dispatch/aerosol-vertical-profile-sensitivity-v2-ordinal-41`, did **not** post `ORDINAL41_AVPS_V2_DISPATCH_CONSUMED`, did **not** upload publisher evidence as if dispatch had succeeded, and did **not** request or run AVPS-v2 science. The failed publisher is immutable evidence and must never be rerun/retried/resumed.

## Dependency closure restoration

This recovery restores exactly one missing preregistration file:

`review/aerosol-vertical-profile-sensitivity-v2-prereg/protocol.review.json`

It must be byte-identical to PR #597 exact head `2bba54c6e78ed99d169887eef51d0c88d812b6f1` and therefore have Git blob `d790fb3fa2d214d1f430f4417b17212a8e5038a8`. That exact blob is already hard-bound by the published `build_skeleton.py`; restoration changes no science design, seed derivation, case universe, endpoint, threshold, or analysis rule.

## Fresh recovery publisher identity

The recovery workflow is `.github/workflows/avps-v2-dispatch-publisher-recovery1.yml`. It is a new Actions identity and is activated only by a fresh one-file push to:

- branch: `dispatch-trigger/aerosol-vertical-profile-sensitivity-v2-ordinal-41-publisher-recovery1`
- marker: `dispatch-triggers/avps-v2-ordinal41-publisher-recovery1.txt`

The marker must be a single commit whose sole parent is exact then-current `main`, and must contain exactly:

```text
schema=AVPS_V2_PUBLISHER_RECOVERY1_TRIGGER_V1
main=<exact then-current main SHA>
originalPublisherRun=33231924719
scientificOrdinal=41
```

## Required fresh fence

Before any consumption write, recovery1 must prove all of the following in the same attempt-1 run:

1. its activation identity is exact and marker-only;
2. the restored preregistration file has Git blob `d790fb3fa2d214d1f430f4417b17212a8e5038a8`;
3. the original publisher bytes remain SHA-256 `e702518a88cdf9f88e00ec9b1021ea9d023dbb2e90dbe48443bfd667b2319478`;
4. original publisher run `33231924719` is terminal FAILURE, attempt 1, exact head `e3ab0b7c7dae02773fc4756325dcc4d15efabd65`, failed at its pre-dispatch fence, with ref/marker/evidence/science-dispatch steps skipped;
5. authorization PR #604 remains Draft/open/unmerged at exact head `d5f5e4d9d19d7ede573fecae68565a92baabbec3` over exact parent `b3d562222a38fc9d1ff5d218886afdda72c37fa2`, with its frozen successful review run/artifact/digest;
6. the exact allocation marker occurs once, the consumed marker occurs zero times, the ordinal-41 dispatch ref is absent, and AVPS-v2 science has zero workflow-dispatch runs;
7. the restored dependency closure rebuilds exactly 72 fresh candidate seeds with canonical SHA-256 `02f624d582e9b2caba6b920d65a5e8a8bc8fc1a2693623bc2f73abf5d3f706d2`;
8. tracked-tree and repository-global collision counts are zero under the live activation surface; and
9. the published science workflow and original publisher bytes still match an attempt-1 successful solver-free implementation-review artifact.

Only after all nine checks pass may recovery1 create the exact ordinal-41 dispatch ref at the frozen authorization head, post exactly one consumed marker, upload zero-runtime publisher evidence, and request the unchanged `avps-v2-science.yml` on `main` with the exact `dispatch_ref` input.

## Prohibited recovery behavior

Recovery1 must not change or derive a new scientific ordinal, case ID, group ID, candidate seed, photon count, vertical profile, aerosol optical family, AOD, geometry, wavelength range, numerical method, endpoint, analysis rule, or materiality threshold. It must not use Taylor/Jerusalem residuals, open AVPS-v2 results, open protected holdouts, admit new Level-B mappings, or change production/default behavior. It must not use GitHub Re-run/retry/resume on the failed original publisher or on any consumed scientific identity.

If any fresh fence condition fails, recovery1 fails closed before creating the dispatch ref or consumed marker. Any later technical failure after ordinal 41 is actually consumed requires a separately reviewed post-consumption recovery; ordinal 41 may never be reused as a fresh science identity.
