# STAR VISIBILITY / MYSTIC — LIVE HANDOFF CHECKPOINT

**Checkpoint: 2026-08-27, immediately before second reviewed AVPS post-consumption recovery activation.**

This checkpoint supplements `HANDOFF_CURRENT_2026-08-27_POST_PR557.md`. It records the exact state that must remain true when the second recovery activation starts.

## Live control state

- Repository: `search-maker/twilight-mystic-experiments`
- Live `main`: `99ade7798627e67921139697ba1a004fa8a304bb` (PR #563 merge). Do not move main while ordinal-40 recovery is active.
- Authorization PR #565 remains Draft/open/unmerged.
- Authorization head: `338ee82c8e088e929f45782b1f7ac1c3aaaaa533`.
- Authorization parent: `99ade7798627e67921139697ba1a004fa8a304bb`.
- Authorization review run `33113256151`, attempt 1: SUCCESS.
- Issue 60 has exactly one allocation marker and exactly one consumed marker for ordinal 40.
- Ordinal 40 is already allocated and consumed. Never allocate/reuse/re-consume it.
- Dispatch branch: `dispatch/aerosol-vertical-profile-sensitivity-v1-ordinal-40`, frozen at authorization head `338ee82c...`.
- Latest pre-activation readback: zero workflow runs on the dispatch branch; no AVPS science run has started; results remain closed.

## Failure history that must remain immutable

### Original publisher
- Request head: `8708a0f8a2fa86c5c13b27c94517552b0bf7dc2a`.
- Run `33114653044`, attempt 1: FAILURE after successful dispatch-branch push + consumed marker, before evidence upload/science dispatch.
- Preserved at `history/avps-v1-dispatch-publisher-ordinal-40-failed-after-consume-1`.

### First post-consumption recovery activation
- R1: `cd4e6ca95d85cc5208a63fc8fd73ed685d4f8178`.
- R2/request head: `00805a95dd1d179b544bf8f531a8ed726cf2d0c1`.
- Run `33117461748`, attempt 1: FAILURE at `Bind reviewed post-consumption recovery request` with `KeyError: 'AUTH_PARENT'`.
- No dispatch push, marker write, publisher-evidence upload, science dispatch, or result opening occurred in this run.
- Failed R2 is preserved at `history/avps-v1-post-consumption-publisher-recovery-failed-1`.
- Never GitHub Re-run either failed publisher run.

## Review correction history

### PR #567
- Draft/open/unmerged immutable review evidence for recovery template v1.
- Final head `b606dbda29c7beaa58c9bb176d436412ddc0f29e`.
- Reviewed template blob `3470a0d6d2620d43c4c841f17d50d32eb9941ec4`.
- Contract run `33116868465`: SUCCESS.
- First activation exposed an environment-export bug; do not activate this blob again.

### PR #568 — current reviewed recovery template v2
- Title: `Review AVPS post-consumption recovery template v2`.
- Draft/open/unmerged. Never merge; preserve as review evidence.
- Head: `4837ee4666b5ae9833e2854f89abf83e95994522`.
- Base/main: `99ade7798627e67921139697ba1a004fa8a304bb`.
- Files remain only the inactive recovery template + its regression test.
- Relative to #567 final head, workflow change is only 3 additions / 1 deletion; tests add 15 lines.
- Two orchestration corrections only:
  1. immediately export all request-derived variables after `source request.env` before embedded Python reads `os.environ[...]`;
  2. bind the original publisher run name to GitHub's actual live run-name form `AVPS v1 dispatch publisher status/avps-v1-dispatch-publisher-ordinal-40`.
- Reviewed template Git blob: `a7bc9b36a6a5f064e06adff2ad130503e2044b58`.
- Contract run `33118692013`, attempt 1: SUCCESS.
- Full unit/artifact audit, estimator package checks, future-authorization proposal, and proof that scientific execution remains unauthorized all passed.

## Fresh second activation chain — prepared, not yet activated at this checkpoint

### R1 v2
- Commit: `4945f7c2c6e6b20d9ff8c2a01baa0ead0e9c9f19`.
- Direct child of live main `99ade779...`.
- Changes only `.github/workflows/avps-v1-dispatch-publisher.yml`.
- Active publisher blob at R1 was re-read from GitHub and equals the reviewed #568 template blob exactly: `a7bc9b36a6a5f064e06adff2ad130503e2044b58`.

### R2 v2
- Commit: `4864aa2e7f92ace0b5ea05beb76174508abbd053`.
- Direct child of R1 v2 `4945f7c2...`.
- Changes only `.github/dispatch-requests/avps-v1.json`.
- Request blob: `6b97061ee6f3db3ed15c7d22cd25bbe9f8006b20`.
- Request binds ordinal 40, #565/auth head/parent, original failed publisher run `33114653044` + request head `8708a0f8...`, and current recovery review #568/head `4837ee46...`.

## Activation rule

Only after the live preflight above remains true may `status/avps-v1-dispatch-publisher-ordinal-40` be force-moved to R2 v2 `4864aa2e...`.

That move must create a fresh push-triggered **attempt-1** publisher identity. It is not a GitHub Re-run.

The recovery publisher is allowed to read repository/issue state and use `actions: write` only for the final explicit science workflow-dispatch after immutable recovered publisher evidence has been uploaded. It must not push the dispatch branch again, write a second marker, allocate another ordinal, change seeds, set up scientific runtime, execute MYSTIC itself, or open results.

## Results gate

Even if the recovery publisher succeeds and science starts, do **not** inspect/open scientific result payloads before the frozen exact aggregate/result-opening guards pass, including all 360 cases, hashes, identities, 8001-node products, and exact-360 aggregate completeness.

Primary result opening remains a separate controlled post-aggregate action.
