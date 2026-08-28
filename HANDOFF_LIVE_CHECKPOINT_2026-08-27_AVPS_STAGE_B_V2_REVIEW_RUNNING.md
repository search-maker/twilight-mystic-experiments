# LIVE HANDOFF CHECKPOINT — AVPS STAGE B V2 REVIEW RUNNING

**Timestamp context: 2026-08-27 EDT / 2026-08-28 UTC. This supersedes the Stage-B section of `HANDOFF_LIVE_CHECKPOINT_2026-08-27_POST_AVPS_STAGE_A_V3_SUCCESS_STAGE_B_REVIEW.md`. Stage A remains complete and must not be repeated.**

## Immutable state

- frozen main/auth parent: `99ade7798627e67921139697ba1a004fa8a304bb`
- authorization PR #565 remains Draft/open/unmerged
- authorization + dispatch head: `338ee82c8e088e929f45782b1f7ac1c3aaaaa533`
- ordinal 40 has exactly one allocation marker and exactly one consumed marker
- Stage A is complete through successful run `33123226959`, artifact `9667291127`, digest `sha256:0338d418d554c5ceaead8712a1ee860c2ee154d839cfe7c038098607786a0b3f`
- no AVPS science run has started
- no solver run has started
- no AVPS result has been opened

## #574 is immutable failed review evidence — DO NOT RERUN

Draft PR #574 exact failed review head:
`9a3390d27963359c7c39b1762a1b8eec90e24185`

Generic contract run `33130500968`, attempt 1, job `98718644364`:
- 1013 / 1014 tests passed
- sole failure was a static test overconstraint requiring a seed-hash token to appear literally in inactive YAML
- actual canonical seed-hash enforcement remains in frozen `science_guard.py`
- no science/solver/result boundary crossed

Dedicated live Stage-B review run `33130501045`, attempt 1, job `98718644744`:
- Stage-B unit contract PASS
- exact scientific authorization-head checkout PASS
- live main/auth/dispatch/Stage-A/one-use binding PASS
- tracked-tree seed scan PASS with `filesScanned=417`, `occurrenceCount=76`, status `PASS_NO_TRACKED_TREE_CANDIDATE_SEED_COLLISIONS_OUTSIDE_SELF_LEDGER`
- repository-global read-only metadata acquisition failed on exact `HTTP Error 429: Too Many Requests`
- recovered freshness construction never started
- unchanged freshness validator never ran
- unchanged science guard never ran
- no science/solver/result boundary crossed

#574 has an explicit conversation comment freezing these facts and forbidding rerun/activation.

## #575 — fresh Stage-B live-surface review v2

Draft PR:
`#575 Review AVPS Stage B live surface recovery v2`

Branch:
`review/avps-v1-ordinal40-stage-b-science-recovery-control-2`

Exact head:
`f9eefab39edb87b270f296f545342b482526bd87`

Base remains frozen main:
`99ade7798627e67921139697ba1a004fa8a304bb`

Relative to #574, v2 changes only review/orchestration evidence:
- bounded 429-only wrapper around the unchanged repository-global seed scanner for the dedicated live review;
- unit tests for that wrapper;
- frozen #574 failure/no-rerun record;
- corrected static seed-identity regression that binds the exact unchanged `science_guard.py` blob and its canonical seed/row-hash comparisons.

No frozen scientific source, authorization, science guard, case universe, seed ledger, F, runtime identity, analysis or result-opening code changed.

### 429-only wrapper contract

Frozen scanner blob:
`1cfb54e3ed96ff57f84739b4e4393544c49e2d32`

Wrapper policy:
- max 3 scanner invocations
- retry only exact `HTTP Error 429: Too Many Requests`
- delays 60 seconds then 120 seconds
- delete partial output before retry
- caller cannot override output identity
- any non-429 failure terminates immediately
- seed collision / semantic scanner refusal is never retried
- HTTP 503 is not retried by this AVPS wrapper
- third 429 is terminal
- scanner bytes and scanner scientific/control semantics remain unchanged

## Current #575 attempt-1 review runs

Generic non-scientific contract:
- run `33131102921`
- job `98720568547`
- attempt 1
- exact head `f9eefab39edb87b270f296f545342b482526bd87`
- currently in progress in full unit/artifact audit at this checkpoint

Dedicated live Stage-B review:
- run `33131102940`
- job `98720569058`
- attempt 1
- exact head `f9eefab39edb87b270f296f545342b482526bd87`
- unit/retry/recovery contract PASS
- exact scientific checkout PASS
- Stage-A/live one-use binding PASS
- currently in the live 72-seed authorization recheck at this checkpoint

Do not manually rerun either check. Terminal attempt-1 outcome is authoritative.

## #575 is deliberately NOT activation-ready

Even if both #575 checks finish SUCCESS, **do not activate Stage B from #575**.

Reason: #575 applies the 429-safe wrapper to the dedicated review workflow only. The inactive future science recovery template still invokes the repository-global seed scanner directly.

After green #575, the next required step is a separate fresh Stage-B transport review (v3) that:
1. applies the exact same frozen-scanner 429-only wrapper to the inactive science recovery transport;
2. changes future activation R1 from a 3-file to a 4-file exact surface, adding `retry_repository_global_seed_scan.py` alongside publisher workflow, science workflow, and `post_consumption_surface.py`;
3. updates both inactive publisher/science transport assertions to freeze that exact four-file control surface;
4. keeps every scientific input, case, seed, F, OPAC/runtime identity and unchanged `science_guard.py` byte-identical;
5. still stops after raw exact-360 artifact metadata and does not aggregate/open/interpret results;
6. receives fresh attempt-1 generic + dedicated review success before any activation can be considered.

## Immediate next action

Read terminal state of `33131102921` and `33131102940` only. If either fails, preserve #575 and repair only the exact demonstrated defect on a fresh review head. If both pass, record exact terminal evidence and immediately construct the separate transport v3 review; do not move any status ref and do not start science.
