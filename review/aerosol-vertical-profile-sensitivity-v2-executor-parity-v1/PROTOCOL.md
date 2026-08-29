# AVPS v2 executor parity gate v1

Status: **review-only / solver-free / no dispatch / no result opening**.

This child of the successful ordinal-41 execution-control gate implements only the per-case execution primitive needed by a later one-shot scientific workflow. It does not create the dispatch publisher, dispatch branch, consumed marker, workflow dispatch, solver run, aggregate result, Level-B result, or production state.

The executor is not a mechanical copy of AVPS v1. The v1 vertical transport was scientifically non-informative because its state-specific `aerosol_file tau` surface was overridden by a later OPAC species directive. V2 therefore binds the reviewed v2 adapter and requires the explicit four-species profile representation:

```text
aerosol_species_file profiles/<state>.four-species.dat INSO WASO SOOT SUSO
aerosol_set_tau_at_wvl 550 <AOD550>
```

Every case must preserve and hash the exact `<state>.four-species.dat` bytes. A legacy `aerosol_file` directive is a hard refusal.

## Bound scientific identity

- ordinal: 41
- execution key: `aerosol-vertical-profile-sensitivity-v2:numerical:41`
- authorization PR/head: #604 / `d5f5e4d9d19d7ede573fecae68565a92baabbec3`
- execution-control parent: PR #605 exact head `53bfe783f5106252149e9da106ae87b5b6e3f710`
- case universe: 360 cases / 72 CRN groups / five vertical states
- photon histories: 20,000,000 per case
- candidate seed values remain derived in memory only from the separately reviewed v2 seed ledger; tracked review outputs contain only the frozen canonical identity
- one syntax check and one solver execution per case; attempt 1 only; no retry/resume/GitHub Re-run
- exact four-alias OPAC data-tree identity required
- frozen R8 derived-channel helper and process-group runner are reused by exact Git blob identity only

## Future guard required before any solver call

`execute_case()` defaults to refusal and requires explicit `allow_execution=True`. Even then it requires a future one-use guard proving:

- exact ordinal/execution key/authorization head and PR;
- exact dispatch branch at the authorization head;
- exactly one allocation marker and exactly one consumed marker;
- workflow attempt exactly 1 and a positive run ID;
- fresh pre-solver repository-global seed recheck;
- exact candidate-seed canonical identity;
- exact four-alias runtime identity;
- solver permission for this one execution identity;
- rerun/retry/resume all false.

The runtime report must independently prove the locked `uvspec`, AFGL-US and four-alias data-tree identities before solver invocation.

## Case evidence

After a successful single solver execution, each case result binds:

- case/group/state/geometry/AOD/replicate identity;
- scientific ordinal/execution key/run identity;
- exact input SHA;
- exact explicit four-species profile SHA and relative path;
- exact four-alias runtime identity;
- raw spectrum/std-spectrum hashes and complete required-member hash map;
- independently derived photopic, scotopic and Johnson-V channels;
- marginal MC diagnostics;
- `resultOpeningAuthorized=false` and `productionAuthorized=false`.

No partial case or individual result may be interpreted scientifically before the separately frozen complete-universe opening gate.

## Next stage

After this exact-head executor review passes, the next safe implementation gate is the v2 aggregate/opening parity plus one-shot orchestration/dispatch publisher. That later gate must remain solver-free until all bytes are independently reviewed, and actual dispatch remains a separate fresh repository-global pre-dispatch transition.
