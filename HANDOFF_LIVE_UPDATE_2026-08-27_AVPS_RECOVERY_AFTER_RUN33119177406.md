# LIVE HANDOFF ADDENDUM — AVPS ORDINAL 40 AFTER RECOVERY RUN 33119177406

**Timestamp context: 2026-08-27. This supersedes `HANDOFF_LIVE_UPDATE_2026-08-27_AVPS_RECOVERY_TEMPLATE_V2.md` for the live AVPS recovery checkpoint. Read it together with `HANDOFF_CURRENT_2026-08-27_POST_PR557.md`.**

All global scientific rules remain unchanged: no fitting to Taylor, F=3.14, frozen AVPS 360-case/72-CRN design, no new seed/ordinal allocation, no result opening before exact aggregate validation, and no manual MYSTIC run outside the reviewed transport.

## Immutable scientific identity remains unchanged

- live `main`: `99ade7798627e67921139697ba1a004fa8a304bb`;
- authorization PR #565: Draft/open/unmerged, head `338ee82c8e088e929f45782b1f7ac1c3aaaaa533`;
- ordinal 40 was allocated exactly once and consumed exactly once;
- dispatch branch `dispatch/aerosol-vertical-profile-sensitivity-v1-ordinal-40` remains at `338ee82c8e088e929f45782b1f7ac1c3aaaaa533`;
- no AVPS science run has started;
- no AVPS scientific result payload has been opened.

## Recovery review v2 succeeded

Draft PR #568, `Review AVPS post-consumption recovery template v2`, remains open/unmerged as review evidence.

- exact reviewed head: `4837ee4666b5ae9833e2854f89abf83e95994522`;
- exact reviewed inactive-template Git blob: `a7bc9b36a6a5f064e06adff2ad130503e2044b58`;
- contract run `33118692013`, attempt 1: **SUCCESS**;
- full unit/artifact audit, estimator-package checks, future-authorization proposal check, and proof that scientific execution remained unauthorized all passed.

Relative to #567, v2 changed only the request-variable export and the live GitHub publisher run-name binding.

## Fresh v2 activation chain

A fresh activation chain was built without moving main:

- R1 recovery-control commit: `4945f7c2c6e6b20d9ff8c2a01baa0ead0e9c9f19`
  - direct child of exact main `99ade779...`;
  - changes only `.github/workflows/avps-v1-dispatch-publisher.yml`;
  - reuses the exact reviewed blob `a7bc9b36...`.
- R2 request commit: `4864aa2e7f92ace0b5ea05beb76174508abbd053`
  - direct child of R1;
  - changes only `.github/dispatch-requests/avps-v1.json`;
  - binds ordinal 40, exact #565 authorization identity, original consuming publisher run `33114653044` / request `8708a0f8...`, and #568 exact review head.

The status branch was moved to R2, creating fresh publisher run `33119177406`, run number 3, attempt 1.

The failed R2 is now preserved immutably at:

`history/avps-v1-post-consumption-publisher-recovery-failed-2`

## Run 33119177406 — exact result

The v2 recovery passed both earlier failure points:

1. `Bind reviewed post-consumption recovery request` — **SUCCESS**;
2. `Bind authorization, preauthorization and zero-runtime review` — **SUCCESS**.

It then failed at:

`Prove original publisher consumed then failed before science`

Exact failure:

`original publisher prerequisite did not succeed: Perform actual git push that consumes dispatch identity=None`

Everything after that guard was skipped, including exact-consumed-state proof, evidence upload, and science dispatch. Therefore this run made no scientific transition and did not repeat any consumption action.

## Exact diagnosis from original run API

The original consuming publisher run `33114653044` has exactly these relevant step names/statuses:

- `Bind request, authorization, preauthorization and zero-runtime review` — success;
- `Prove dispatch eligible before creating ref` — success;
- `Actual git push consumes dispatch identity` — success;
- `Mark consumed once and prove post-dispatch state` — failure;
- `Stage immutable successful publisher evidence` — skipped;
- `Persist immutable publisher evidence before science trigger` — skipped;
- `Explicitly dispatch attempt-1 science on pushed ref` — skipped.

Therefore the v2 guard used one stale/wrong step-name string:

wrong: `Perform actual git push that consumes dispatch identity`

correct live API name: `Actual git push consumes dispatch identity`

The other relevant original step names already match exactly. This is a metadata-binding defect only; it does not change the scientific design or consumed identity.

## Next action

1. Create a fresh inactive recovery-template v3 review branch/PR, preserving #568 unchanged as evidence.
2. Change only the one stale step-name binding above, plus regression coverage that freezes the complete original-run step-name set.
3. Require the repository contract to pass before activation.
4. Preserve any new failed activation head before moving the status ref again.
5. If v3 review is green, build a fresh R1 direct child of exact live main using the exact reviewed v3 template blob, then a fresh R2 request child binding the new review PR/head.
6. Move the status branch to that fresh R2 to create a new attempt-1 run; never use GitHub Re-run.
7. The recovery must still prove exactly one allocation marker, exactly one consumed marker, immutable dispatch head, zero prior AVPS science runs, no prior successful publisher, and the original consuming failure before science.
8. Only after immutable recovered publisher evidence is uploaded may it explicitly dispatch the frozen `avps-v1-science.yml`.
9. If science starts, keep scientific result payloads closed until exact 360-case aggregate/hash/runtime/identity validation passes.

## Hard prohibitions

- no second allocation or consumed marker;
- no second dispatch-branch push;
- no new ordinal or seed allocation;
- no moving `main` during recovery;
- no rerun of publisher runs `33114653044`, `33117461748`, or `33119177406`;
- no manual MYSTIC execution;
- no result opening before exact aggregate validation.
