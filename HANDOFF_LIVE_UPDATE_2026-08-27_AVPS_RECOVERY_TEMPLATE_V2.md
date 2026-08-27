# LIVE HANDOFF ADDENDUM — AVPS ORDINAL 40 POST-CONSUMPTION RECOVERY V2

**Timestamp context: 2026-08-27. Read this addendum after `HANDOFF_CURRENT_2026-08-27_POST_PR557.md`.**

This addendum updates only the live AVPS ordinal-40 recovery checkpoint. All scientific design, anti-fitting rules, Taylor separation, F=3.14, seed universe, 360-case design, result-opening boundary, and other project lanes remain as stated in the main handoff.

## Exact immutable state

- live `main`: `99ade7798627e67921139697ba1a004fa8a304bb` — do not move while ordinal 40 is being recovered;
- authorization PR #565 remains Draft/open/unmerged at head `338ee82c8e088e929f45782b1f7ac1c3aaaaa533`;
- ordinal 40 is already allocated and consumed exactly once;
- dispatch branch `dispatch/aerosol-vertical-profile-sensitivity-v1-ordinal-40` remains at exact auth head `338ee82c8e088e929f45782b1f7ac1c3aaaaa533`;
- original consuming publisher request `8708a0f8a2fa86c5c13b27c94517552b0bf7dc2a` remains preserved at `history/avps-v1-dispatch-publisher-ordinal-40-failed-after-consume-1`;
- first post-consumption recovery request `00805a95dd1d179b544bf8f531a8ed726cf2d0c1` is preserved at `history/avps-v1-post-consumption-publisher-recovery-failed-1`;
- no AVPS science run has started and no result payload has been opened.

## First recovery activation failure — exact diagnosis

Publisher recovery run `33117461748`, attempt 1, failed in `Bind reviewed post-consumption recovery request` before any later proof/evidence/science step.

Exact exception:

`KeyError: 'AUTH_PARENT'`

Cause: `source request.env` created shell variables but the template did not export them before an embedded Python block read `os.environ['AUTH_PARENT']` / `os.environ['RECOVERY_REVIEW_HEAD']`.

This run had `contents: read`, `issues: read`, and no git-push/Issue-60 POST path. It therefore did not repeat consumption or mutate the scientific identity.

## Additional latent binding bug found before retry

A live GitHub API readback of original publisher run `33114653044` shows its `name` is:

`AVPS v1 dispatch publisher status/avps-v1-dispatch-publisher-ordinal-40`

The #567 template expected the shorter string `AVPS v1 dispatch publisher`. If only the environment export were fixed, recovery would fail later at this run-name identity check.

Therefore do not reactivate the #567 template blob `3470a0d6d2620d43c4c841f17d50d32eb9941ec4`.

## Recovery template v2 review

Fresh review branch:

- `review/avps-v1-post-consumption-publisher-recovery-template-2`

Draft PR:

- #568 — `Review AVPS post-consumption recovery template v2`

Initial v2 head:

- `4837ee4666b5ae9833e2854f89abf83e95994522`

Only two semantic corrections relative to #567:

1. immediately after `source request.env`, export all request-derived variables before any Python `os.environ[...]` read;
2. bind the original publisher run name to the live GitHub run-name shape `AVPS v1 dispatch publisher {expected_branch}`.

Regression coverage now requires both corrections.

#568 is review evidence only. **Do not merge it to main.** No scientific inputs, protocol, seeds, solver settings, F, atmosphere choices, case universe, or result-opening rules changed.

## Next action gate

1. Wait for #568 review/contract CI to be terminal success.
2. Freeze the exact reviewed v2 template blob/head.
3. Build fresh R1 direct child of live main changing only `.github/workflows/avps-v1-dispatch-publisher.yml` to that exact reviewed blob.
4. Build fresh R2 child changing only `.github/dispatch-requests/avps-v1.json`, binding #568 exact review evidence and the original consuming publisher identity.
5. Move `status/avps-v1-dispatch-publisher-ordinal-40` to fresh R2 to obtain a new attempt-1 push run. Never use GitHub Re-run.
6. Recovery must prove exactly one allocation marker, one consumed marker, immutable dispatch head, zero prior AVPS science runs, no prior successful publisher, and the original consuming failure before science.
7. Successful recovery must upload compatible `DISPATCH_PUBLISHED_ZERO_RUNTIME` evidence before explicitly dispatching frozen `avps-v1-science.yml`.
8. If science starts, keep result payloads closed until exact 360-case aggregate/hash/runtime/identity validation passes.

## Hard prohibitions

- no second allocation or consumed marker;
- no second dispatch-branch push;
- no new ordinal or seed allocation;
- no manual MYSTIC execution outside the frozen workflow;
- no moving `main` during this recovery;
- no rerun of `33114653044` or `33117461748`;
- no opening AVPS scientific results before exact aggregate validation.
