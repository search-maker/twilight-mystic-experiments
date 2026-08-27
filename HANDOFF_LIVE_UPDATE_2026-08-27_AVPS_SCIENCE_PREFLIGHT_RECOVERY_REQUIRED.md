# LIVE HANDOFF ADDENDUM — AVPS ORDINAL 40 SCIENCE-PREFLIGHT RECOVERY REQUIRED

**Timestamp context: 2026-08-27. This supersedes `HANDOFF_LIVE_UPDATE_2026-08-27_AVPS_RECOVERY_AFTER_RUN33119177406.md` for the live AVPS recovery checkpoint. Read it together with `HANDOFF_CURRENT_2026-08-27_POST_PR557.md`.**

All global scientific rules remain unchanged: no fitting to Taylor, F=3.14, frozen AVPS 360-case / 72-CRN design, no new seed or ordinal allocation, no result opening before exact aggregate validation, and no manual MYSTIC run outside reviewed transport.

## Immutable scientific identity remains unchanged

- live `main`: `99ade7798627e67921139697ba1a004fa8a304bb`;
- authorization PR #565: Draft/open/unmerged, head `338ee82c8e088e929f45782b1f7ac1c3aaaaa533`;
- ordinal 40 is already allocated exactly once and consumed exactly once;
- dispatch branch `dispatch/aerosol-vertical-profile-sensitivity-v1-ordinal-40` remains at exact auth head `338ee82c8e088e929f45782b1f7ac1c3aaaaa533`;
- original consuming request `8708a0f8a2fa86c5c13b27c94517552b0bf7dc2a` is preserved at `history/avps-v1-dispatch-publisher-ordinal-40-failed-after-consume-1`;
- failed recovery request `00805a95dd1d179b544bf8f531a8ed726cf2d0c1` is preserved at `history/avps-v1-post-consumption-publisher-recovery-failed-1`;
- failed v2 recovery request `4864aa2e7f92ace0b5ea05beb76174508abbd053` is preserved at `history/avps-v1-post-consumption-publisher-recovery-failed-2`;
- no AVPS science workflow run has started;
- no AVPS scientific result payload has been opened.

## Publisher recovery review state

### #568 — reviewed v2 evidence

Draft PR #568 remains open/unmerged as review evidence.

- exact reviewed head: `4837ee4666b5ae9833e2854f89abf83e95994522`;
- exact reviewed inactive-template blob: `a7bc9b36a6a5f064e06adff2ad130503e2044b58`;
- contract run `33118692013`, attempt 1: SUCCESS.

### v2 activation failure

Fresh v2 activation used:

- R1 `4945f7c2c6e6b20d9ff8c2a01baa0ead0e9c9f19` — direct child of live main; only active publisher workflow changed, using exact reviewed blob;
- R2 `4864aa2e7f92ace0b5ea05beb76174508abbd053` — only recovery request changed.

Publisher run `33119177406`, attempt 1:

- request binding: SUCCESS;
- authorization/preauthorization binding: SUCCESS;
- original-publisher-history proof: FAILURE because the template expected stale step name `Perform actual git push that consumes dispatch identity`.

Live API proves the exact original step name is:

`Actual git push consumes dispatch identity`

Everything after the failed guard was skipped, including evidence upload and science dispatch.

## #569 — exact step-binding review only; DO NOT ACTIVATE

Draft PR #569:

`Review AVPS post-consumption recovery template v3 exact step binding`

Exact head:

`f980458e646c91ad112ed8a7d8114986e50bcb92`

Relative to #568, the inactive recovery workflow changes exactly one string (1 addition / 1 deletion):

- stale: `Perform actual git push that consumes dispatch identity`
- live API exact: `Actual git push consumes dispatch identity`

Regression coverage freezes the complete relevant original publisher step-name set and forbids the stale string.

**Do not activate #569 even if its review CI is green.** It is now retained only as evidence for the corrected publisher-history binding.

## New downstream blocker found before v3 activation

The exact frozen science workflow on authorization/dispatch head `338ee82c8e088e929f45782b1f7ac1c3aaaaa533` is:

`.github/workflows/avps-v1-science.yml`

Git blob:

`55f48bbdf99aac58a96bd96f6735a4e56b8b466a`

Before solver setup, in `Build live pre-solver seed proof and one-use science guard`, it calls:

```python
surface=preauthorization_surface.build_dispatch_surface(
    payload,int(os.environ['ORDINAL']),os.environ['GITHUB_SHA'],os.environ['AUTH_PARENT'],
    current_pr=int(os.environ['PR_NUMBER']),current_run_id=int(os.environ['GITHUB_RUN_ID']),
    candidate_seed_authorization_recheck_passed=True,post_dispatch=True,
)
```

That path delegates into the same AVPS control surface whose `failed_authorization_history(...)` currently rejects the legitimate ordinal-40 consumed marker because the ordinal also has preserved failed-authorization history.

Therefore, after successful publisher recovery, blindly dispatching the frozen science workflow is expected to fail **pre-solver** with the same class of error:

`GlobalOrdinalRefusal: ordinal 40 already has consumed marker`

This is a control-plane / pre-solver recovery problem. It is not a MYSTIC result and does not justify changing any scientific input.

## Required recovery architecture from this point

The recovery should be split into two separately reviewed stages.

### Stage A — publisher-evidence-only recovery

Recover the publisher evidence for the already-consumed dispatch state, but **do not trigger science**.

Must prove at least:

- exact live main `99ade779...`;
- exact #565 authorization identity and successful review/preauthorization evidence;
- exactly one allocation marker and exactly one consumed marker;
- dispatch branch still at exact auth head `338ee82...`;
- original publisher run `33114653044` pushed dispatch successfully and failed only after consumption, before evidence/science dispatch;
- zero prior AVPS science runs;
- no previous successful AVPS ordinal-40 publisher recovery;
- no git push and no Issue-60 comment POST in the recovery run itself;
- successful immutable `DISPATCH_PUBLISHED_ZERO_RUNTIME`-compatible publisher evidence is uploaded;
- science dispatch is absent from this recovery stage.

### Stage B — separate science-preflight recovery

Only after Stage A succeeds, review a dedicated science-recovery transport that keeps the entire scientific experiment frozen but replaces the broken consumed-state control proof with a narrow, explicit consumed-state recovery proof.

It must bind at least:

- live main `99ade779...`;
- exact auth/dispatch head `338ee82...`;
- #565 Draft/open/unmerged identity;
- exact successful auth-review and preauthorization artifacts;
- exactly one allocation marker and exactly one consumed marker;
- exactly one successful recovered publisher evidence artifact from Stage A;
- zero prior AVPS science/solver runs;
- exact frozen scientific source/orchestration inputs required by the execution contract;
- exact candidate seed ledger and 72 CRN groups;
- exact 360-case universe / four 90-case shards;
- F=3.14;
- 20,000,000 photon histories per case;
- exact OPAC source binding;
- no Taylor residual/result access;
- no new ordinal, marker, dispatch branch, or seed allocation.

The recovery may repair only control-plane admission. It must not alter MYSTIC inputs, case universe, seeds, analysis contrasts, convergence rules, or result-opening rules.

## Immediate next work

1. Let #569 CI finish and record the result, but do not activate it.
2. Audit existing repository recovery precedents, especially pre-solver/science recovery patterns, before inventing a new workflow.
3. Build and review Stage-A publisher-evidence-only recovery first.
4. Separately build/review Stage-B science-preflight recovery using the narrowest precedent-supported mechanism.
5. Only after Stage-B review is green may a science run be started.
6. Keep all AVPS result payloads closed until exact aggregate/hash/runtime/identity validation passes.

## Hard prohibitions

- no second allocation marker;
- no second consumed marker;
- no second dispatch-branch push;
- no new ordinal or seed allocation;
- no moving live `main` during ordinal-40 recovery;
- no rerun of publisher runs `33114653044`, `33117461748`, or `33119177406`;
- no activation of #569 as currently written;
- no manual MYSTIC execution;
- no result opening before exact aggregate validation.
