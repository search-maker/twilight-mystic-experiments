# AVPS v2 ordinal-41 publisher trigger bridge v1

Status: **review-only, zero-runtime transport proposal; not activated; no scientific identity consumed by this proposal.**

## Purpose

The connected scheduled-chat GitHub action surface can read Actions state but does not expose a workflow-dispatch creation primitive. The already-reviewed default-branch workflow `.github/workflows/avps-v2-dispatch-publisher.yml` is the only authorized path that may perform the fresh repository-global seed fence, publish the exact ordinal-41 dispatch ref/consumed marker, persist publisher evidence, and then request the AVPS-v2 science workflow.

This bridge exists only to request that already-reviewed publisher workflow through GitHub Actions without reproducing or bypassing any publisher logic.

## Frozen bindings

- Review base main before bridge publication: `38bb4ec95f35a44478976c6d6434f88bd83419cb`.
- Scientific ordinal: `41`.
- Authorization head remains `d5f5e4d9d19d7ede573fecae68565a92baabbec3`; authorization PR #604 remains Draft/open/unmerged.
- Publisher workflow: `.github/workflows/avps-v2-dispatch-publisher.yml`.
- Publisher SHA-256 on the review base: `e702518a88cdf9f88e00ec9b1021ea9d023dbb2e90dbe48443bfd667b2319478`.
- Activation branch name: `dispatch-trigger/aerosol-vertical-profile-sensitivity-v2-ordinal-41-publisher-v1`.
- Activation marker path: `dispatch-triggers/avps-v2-ordinal41-publisher-v1.txt`.

The activation marker, if and only if this bridge is separately reviewed and published to main, must contain exactly five key/value lines with no duplicates:

```text
schema=AVPS_V2_PUBLISHER_TRIGGER_V1
main=<exact then-current main SHA, also the sole parent of the activation commit>
publisher=avps-v2-dispatch-publisher.yml
publisherSha256=e702518a88cdf9f88e00ec9b1021ea9d023dbb2e90dbe48443bfd667b2319478
scientificOrdinal=41
```

## Allowed bridge behavior

The bridge may:

1. run only from a push to the exact activation branch that changes the exact marker path;
2. prove the activation commit has exactly one parent and that parent equals then-current `origin/main`;
3. prove the activation commit changes exactly the marker path;
4. prove the publisher bytes still have the frozen SHA-256;
5. refuse if a prior `workflow_dispatch` run of the publisher already exists;
6. upload zero-runtime transport evidence; and
7. issue exactly one GitHub Actions workflow-dispatch request to `avps-v2-dispatch-publisher.yml` with `ref=main`.

## Forbidden bridge behavior

The bridge must not:

- create or update `dispatch/aerosol-vertical-profile-sensitivity-v2-ordinal-41`;
- post the ordinal-41 consumed marker or any Issue #60 marker;
- dispatch `avps-v2-science.yml` directly;
- run or install libRadtran/MYSTIC/uvspec;
- read or open AVPS-v2 scientific results;
- alter authorization, seeds, case universe, photons, stopping rules, analysis, thresholds, Level-B admission, Taylor/Jerusalem scoring, holdouts, or production state;
- use GitHub Re-run/retry/resume for any scientific identity; or
- silently substitute a bridge action for any fresh fence owned by the reviewed publisher.

## Review and activation gates

Before this bridge may be published, a dedicated pull-request review must prove the exact three-file bridge proposal scope, the frozen publisher byte identity, current authorization invariants, absence of the ordinal-41 dispatch ref and consumed marker, absence of any prior publisher workflow-dispatch run, and the bridge's static zero-runtime/single-target mutation contract.

After exact-head review and ordinary non-scientific CI succeed, the bridge may be merged to main. That merge alone does not consume ordinal 41 and does not authorize direct ref/marker creation.

Immediately before activation, Issue #60 and repository state must be refreshed. If a WRITE_QUIET/global snapshot fence is active, or main/auth/marker/ref/publisher state has drifted, activation must not be created. Otherwise create the exact activation branch from exact then-current main and exactly one marker-only commit. The bridge then requests the publisher. The publisher, not the bridge, owns the fresh seed/repository fence and all one-time scientific-dispatch bookkeeping.
