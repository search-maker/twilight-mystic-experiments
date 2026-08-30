# AVPS v2 post-consumption recovery3 — preflight snapshot-fence protocol

Status: **PREREGISTERED / ZERO-RUNTIME / NO AUTHORIZATION / NO DISPATCH**

This protocol freezes the next safe recovery gate after the consumed ordinal-43 AVPS v2 recovery2 execution failed before any scientific solver runtime. It changes control choreography only. It does not change the frozen AVPS v2 scientific design, open any result, admit any richer Level-B mapping, or authorize a new scientific execution.

## Immutable failure evidence

- Governing ledger: Issue #60 under `MYSTIC-STATE-0067` unless a later explicit directive supersedes it.
- Runtime main/head: `970a566f33fefe80590c84cccf3bbe0b1176ec23`.
- Consumed authorization identity: ordinal 43, authorization head `5fd0c82cb14a02ace38a5a7be30b8b075ccae298`, authorization PR #647.
- Consumed dispatch branch: `dispatch/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery2-ordinal-43`.
- Consumed execution key: `aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery2:numerical:43`.
- Consumed marker: `ORDINAL43_AVPS_V2_POSTCONSUMPTION_RECOVERY2_DISPATCH_CONSUMED`, Issue #60 comment `5467062055`.
- Failed science workflow run: `33298433506`, attempt 1.
- Failed preflight job: `99222000748`.
- Step `Prove exact one-use dispatch and authorization identity before runtime`: **SUCCESS**.
- Step `Fresh repository-global candidate-seed recheck and one-use guard`: **FAILURE**.
- Exact failure class: `PRE_SOLVER_REPOSITORY_GLOBAL_SNAPSHOT_STABILITY_FAILURE`.
- The scanner raised `snapshot-fenced repository-global metadata changed between two complete enumerations; refuse this audit and start a fresh attempt-1 workflow run`.
- Profile recovery, exact matrix construction, OPAC acquisition/persistence, all four case-shard jobs, aggregate, and result opening were skipped.
- No `uvspec`, libRadtran/MYSTIC, estimator, aggregation, or numerical AVPS result was produced.
- Run artifact count is exactly 0, so no analysis-only recovery exists.

This failure is evidence about repository-global control coordination only. It is not evidence for or against any vertical-profile sensitivity hypothesis.

## Consumed-identity rule

Ordinal 43 is permanently consumed despite the pre-solver failure. Therefore:

- never GitHub Re-run/retry/resume run `33298433506`;
- never reuse ordinal 43;
- never reuse its authorization/dispatch branch, execution key, workflow-run identity, or its 72 candidate seeds;
- never reinterpret the failed run as numerical or scientific evidence;
- never follow the scanner's generic `start a fresh attempt-1 workflow run` wording using the consumed identity.

The consumed candidate-seed canonical SHA-256 is `38c074fe01bd6d09fa7dc78af1ad323e2f42b606ca992c2950b8fc1f5b343a9f`; the consumed candidate-row canonical SHA-256 is `a88b28dcfaaeb354f294d1705a0f8ddbcd061083f277a038ab8c9dace44d9954`. Those seeds may be retained as immutable evidence only, never as a successor execution set.

Any later scientific recovery requires a fresh repository-global candidate-seed ledger, a fresh authorization/execution identity, and the dynamically verified next unused global scientific ordinal. Ordinal 44 is only a numerical expectation and MUST NOT be hard-coded or allocated without a fresh global scan.

## Frozen scientific design to preserve

Recovery3 may repair coordination/control only. Unless a separate pre-result scientific preregistration explicitly changes science, it must preserve:

- 360 cases total;
- 72 common-random-number groups;
- 5 vertical-profile states per group;
- 20,000,000 photon histories per case;
- the same five independently defined profile states and validated profile-byte provenance;
- the same geometries, wavelengths, aerosol optical-property/source contracts, estimator/aggregation semantics, classification rules, stopping/budget rules, and closed-result boundary;
- no Taylor/Jerusalem residual use for seed generation, design, thresholds, profile choice, recovery choice, or mapper selection;
- `resultOpeningAuthorized=false` and `productionAuthorized=false` through execution;
- no Level-B mapping authorization from authorization, execution infrastructure, or an unopened result.

The consumed ordinal-43 seed values are not part of the preserved scientific design and must be replaced.

## What failed in the control choreography

The repository-global scanner deliberately performs two complete metadata enumerations and retains non-operational content of existing rows. It may ignore harmless append-only rows arriving after the first-pass high-water fence, but it must refuse if an already fenced branch/issue/PR/comment/run/artifact metadata row changes in collision-relevant content between passes.

Run `33298433506` correctly refused when the two fenced enumerations differed. The failure record does not identify which external row changed, and this protocol does not guess. The important control fact is that the final science preflight scan ran while independent repository metadata writers were not externally silenced.

The scanner itself must remain fail-closed. Recovery3 MUST NOT weaken canonicalization, remove audited surfaces, ignore edited existing rows, suppress the two-pass comparison, or accept instability merely to obtain a green run.

## Required recovery3 snapshot choreography

A successor execution may proceed only after a separately reviewed control path implements all of the following:

1. Generate and review a fresh candidate-seed set without using Taylor/Jerusalem/holdout results, and prove no overlap with consumed AVPS seed sets.
2. Under a normal preregistered repository-global review fence, dynamically derive the next unused global scientific ordinal; do not hard-code 44.
3. Review exactly one fresh authorization child and one fresh one-use dispatch/execution identity. The authorization must remain result-closed and production-closed.
4. Immediately before the final science preflight, acquire a **short-lived repository WRITE_QUIET snapshot fence** in Issue #60. The marker must name the fresh authorization head, dispatch identity, expected science workflow, and a unique recovery3 fence token.
5. After that BEGIN marker, perform all explicitly preregistered bootstrap writes needed for the one-use execution identity (for example exact dispatch ref and exact consumed marker) **before** launching the science workflow. No unrelated manual repository metadata writes are allowed after bootstrap begins.
6. Dispatch the fresh science workflow exactly once. The science preflight must itself make no repository metadata mutations while it performs the repository-global two-pass seed/ordinal/identity guard.
7. The publisher/control process must become read-only and wait for the exact fresh science run and its exact `preflight` job. It must observe the specific step `Fresh repository-global candidate-seed recheck and one-use guard` to a terminal **step** conclusion without editing repository metadata. It MUST NOT wait for the entire successful preflight job before closing the fence.
8. As soon as that exact repository-global guard step is terminal, write the matching `WRITE_QUIET_END` with exact BEGIN comment, authorization/dispatch/run/job identities, step conclusion, and observed timestamp. On a successful guard step this END must be written while the remaining non-solver preflight preparation may continue; on a failed guard step it must be written as soon as the refusal is observable. The fence must not remain active for the 360-case runtime.
9. The fresh science workflow must contain an explicit read-only **snapshot-fence-release barrier** after `preflight` and before every case-shard/solver job. That barrier must verify the exact matching `WRITE_QUIET_END` for its own BEGIN token + authorization + dispatch + run identity. Every solver-bearing case job must depend on this barrier as well as the successful preflight. If the matching END is absent, malformed, belongs to another run, or does not arrive within the preregistered bounded wait, the barrier must fail closed before any solver execution. This prevents scheduler races in which case jobs could start before the external publisher has released the repository fence.
10. If preflight/guard fails for any reason, preserve that fresh successor identity as consumed and immutable; never GitHub Re-run/retry/resume it. Any later attempt requires another fresh identity under a separately reviewed gate.
11. If the repository-global guard, remaining preflight, and snapshot-fence-release barrier all succeed, solver jobs may continue under the already frozen science design. Result opening remains a separate preregistered gate.

Automatic GitHub Actions/check/artifact lifecycle bookkeeping during the short fence may occur. The repository-global scanner already treats current-audit self metadata and operational lifecycle fields under its reviewed semantics; recovery3 must not loosen those semantics. Other workers/coordinators must treat the active recovery3 WRITE_QUIET as read-only until the matching END.

## Review requirements before implementation

The recovery3 implementation/control gate must be independently solver-free reviewed and prove:

- exact parent/main and exact changed-file scope;
- run `33298433506` attempt 1 and job `99222000748` remain immutable terminal failure evidence;
- the ordinal-43 consumed marker exists exactly once;
- ordinal 43 and its 72 seeds are explicitly non-reusable;
- fresh seed and dynamic-next-ordinal requirements are explicit;
- the scanner's two-pass stability contract is preserved byte-for-byte unless a separate scanner-change preregistration is reviewed first;
- WRITE_QUIET BEGIN precedes the final bootstrap/dispatch sequence;
- matching WRITE_QUIET END is emitted from the exact guard-step terminal result, not delayed until a successful whole-preflight completion;
- an exact-run snapshot-fence-release barrier gates every solver-bearing job and fails closed if END is absent or mismatched;
- no fence is held across long solver runtime;
- no scientific/runtime source change, dispatch, result opening, Level-B admission, protected holdout access, Taylor/Jerusalem scoring, or production transition occurs in this preregistration gate.

## Level-B boundary

Nothing in recovery3 authorizes richer Operational Atmosphere State v2 consumption. Until a successful fresh AVPS result is opened through its frozen result gate and a separately preregistered component-selective shadow mapper passes held-out direct-MYSTIC validation:

- `AOD550` remains the only directly consumed validated-v3 aerosol coordinate;
- arbitrary spectral AOD remains represented but not newly consumed;
- vertical aerosol profile/normalized optical-depth shape remains represented but not newly consumed;
- SSA spectrum remains sensitivity evidence only, not a universal fast-model mapping;
- phase function and aerosol family/classification remain represented/set-valued evidence only;
- every richer `newMappingAuthorized` flag remains `false`.

## This PR explicitly does not authorize

This preregistration does not create fresh seeds, allocate an ordinal, create authorization/dispatch refs, execute libRadtran/MYSTIC/`uvspec`, open results, admit Level-B components, access protected holdouts, score Taylor/Jerusalem residuals, or change production/default behavior.