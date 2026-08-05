# Durable execution rules

This repository contains scientific software and immutable experiment evidence. GitHub is the sole source of truth for changing project state. Never infer current status from a prior chat, local branch, or this file. The one open issue titled `[CONTROL] MYSTIC Autonomous Coordination` is the rolling state ledger; re-fetch it before every material transition. Keep changing SHAs, runs, blockers, and queues in that issue, not here.

## Preflight

From the repository root, refresh and inspect before editing or dispatching:

```text
git fetch origin --prune
git status --short --branch
git rev-parse origin/main
git branch --all --verbose --no-abbrev
gh pr list --state all --limit 100
gh issue list --state all --limit 100
gh run list --limit 100
```

Read the complete control-issue comment history, all open PRs, recently merged/closed PRs, relevant issues, exact-head workflow runs and logs, artifact metadata/digests, and the files/contracts in scope. Check for path overlap before creating a branch. Use one purpose per branch/PR and start from freshly resolved `origin/main`.

## Verification commands

The baseline local contract suite is:

```text
python -m compileall -q experiment experiments integration modeling tests
python -m unittest discover -s tests -v
```

Run focused tests first while iterating, then the complete suite. Re-run deterministic generators and compare bytes/hashes when a package defines generated fixtures. Exact-head GitHub CI is required before merge; green CI proves software-contract success, not numerical convergence, physical correctness, observational validity, or production eligibility.

For Actions evidence, preserve GitHub's artifact digest separately from hashes of extracted files:

```text
gh api repos/search-maker/twilight-mystic-experiments/actions/runs/RUN_ID/artifacts --paginate
gh run view RUN_ID --json databaseId,workflowDatabaseId,headSha,event,status,conclusion,attempt,jobs
gh run download RUN_ID --dir ARTIFACT_DIR
find ARTIFACT_DIR -type f -print0 | sort -z | xargs -0 sha256sum
```

Record artifact ID, exact name, GitHub digest, downloaded ZIP SHA-256, compressed size, extraction inventory, internal file hashes, run/head/attempt, and discrepancies. Never replace an expected value with an observed one; record both.

## Architecture and scientific workstreams

- `experiments/mystic-batch-v1/`: MYSTIC plans, execution guards, one-shot case execution, aggregation, independent audit, Tier-1 analysis, runtime/provenance proofs, and immutable execution protocols. Frozen v1 programs and hashes remain unchanged; explicit `_v2.py` modules handle zero-hit semantics, raw numerical recomputation, and exact analysis bindings for preserved evidence and future versioned protocols.
- `experiments/tier1-precision-continuation-v1/`: proposal-only bounded continuation contracts. Continuation is additive and must never replace an original block.
- `experiments/tier2-disabled-readiness-v1/`: dormant Tier-2 readiness. It remains disabled until its preregistered trigger and separate authorization are satisfied.
- `modeling/surrogate-training-v2/`: strict Tier-1-to-v2 handoff, frozen candidate protocol, deterministic fitting/evaluation, uncertainty, OOD behavior, and model-card artifacts.
- `experiments/observation-integration-v2/`: observation/radiance contracts, calibration-versus-validation isolation, uncertainty/OOD propagation, provenance, and synthetic-only provider boundaries.
- `integration/twilight-observation-v1/`: earlier observation and visibility interfaces; inventory before integration and do not confuse contract fixtures with validated providers.
- `tests/` and `.github/workflows/`: refusal contracts and machine-verifiable governance.
- `evidence/`: immutable or reproducible evidence manifests. Historical evidence may be interpreted by newer code but never rewritten to simulate a different historical outcome.

The main workstreams are raw Tier-1 evidence and continuation, independent audit/handoff, surrogate training and holdout, anchor evaluation, observation integration, and the separately versioned star-visibility/physiology layer. Training, internal holdout, hard anchors, soft diagnostics, calibration observations, and untouched validation observations must remain role-isolated.

## Provenance and execution identity

Bind every scientific execution to an immutable source head, authorization ref, execution key, fresh monotonic ordinal, attempt 1, exact workflow, frozen runtime/package/binary/data hashes, manifest, seeds, inputs, thresholds, and artifact identities. Ordinals, execution keys, authorization refs, run IDs, and seeds are consumed once dispatched, regardless of success or failure.

Never:

- use GitHub Re-run, retry a failed scientific case, or resume under an old identity;
- merge an authorization-only PR;
- force-push shared scientific evidence or rewrite evidence history;
- silently replace artifacts, fabricate nonzero values, drop zero-hit blocks, or change thresholds after observing results;
- let internal holdout, anchors, diagnostics, calibration, or validation leak into fitting/tuning;
- promote synthetic fixtures, unaudited data, unresolved continuation geometry, or OOD inputs to production.

A new execution requires a fresh identity, fresh independent seeds, duplicate-run refusal before any solver call, preregistered stopping/budget rules, exact attempt 1, and an auditable authorization boundary.

## State semantics

Use these concepts independently:

- **Structural failure:** missing/duplicate/unplanned artifacts, malformed or nonfinite values, invalid hashes/provenance, identity drift, seed duplication, incomplete geometry, or schema/accounting violations.
- **Execution failure:** timeout, nonzero syntax/solver exit, wrong execution counts, missing required solver outputs, or a case that did not execute its intended program.
- **Execution complete:** the intended syntax/parser/solver path ran once and returned parseable finite outputs. A valid Monte Carlo zero estimator can be execution-complete.
- **Numerical zero-hit underconvergence:** a successful stochastic execution produced a syntactically valid zero estimator and raw zero spectrum. Preserve it, report explicit zero-hit diagnostics, require additive continuation, and never use epsilon substitution or ordinary CV division by a zero/near-zero mean.
- **Numerically converged:** independent blocks satisfy the preregistered precision rule.
- **Scientific disagreement:** execution is valid, but independent methods/blocks/anchors or physical expectations disagree under a preregistered comparison rule.
- **Validation failure:** the frozen radiance/visibility system fails untouched real observations; do not relabel this as a software or execution failure.
- **Scientifically eligible:** all required geometry-level numerical/scientific gates pass. This is distinct from execution completion.
- **Surrogate validated internally:** the frozen selected model passes its one-time internal holdout and separate anchor evaluation.
- **Observationally validated:** the full radiance-plus-visibility system passes untouched real observations.
- **Production eligible:** provenance, numerical, scientific, software, uncertainty, OOD, observational, and safe-refusal gates all pass in a machine-readable reviewed state.

When evidence supports multiple explanations, state the competing hypotheses, preregister the smallest discriminating test, preserve the current evidence, and run a reversible bounded experiment. Do not tune the rule after observing the result.

## Control ledger and lifecycle

Before posting, re-fetch the exact control issue and live GitHub state so a newer state token is not overwritten. Use monotonically increasing `MYSTIC-STATE-NNNN` tokens and acknowledge newer valid directives with `ACK <token>`. State updates must include UTC and America/New_York time, main/base/head, branch/worktree, PRs, workflow runs, consumed identities, artifact IDs/digests, findings, tests, classifications, blockers, current task, queue, and next directive check.

Post only after material events: branch/PR, terminal CI or science, artifact inspection, classification change, merge, protocol, training, holdout, or observation report. End with `Next directive check: ... Continuing immediately in the meantime with ...`. A check is never a reason to idle; continue the highest-priority independent safe task.

## Recovery after interruption

After every material checkpoint, persist the exact parent SHA, branch/worktree, uncommitted diff, commands, exit codes, test results, artifact paths/hashes, current hypotheses, next command, and queue in commits/evidence plus the control ledger. After timeout, termination, context loss, or machine loss:

1. Re-fetch GitHub, the sole control issue, live `main`, PRs/issues, runs/logs/artifacts, and consumed identities.
2. Verify the local branch/worktree and diff against the ledger; never assume a prior command completed.
3. Re-hash preserved artifacts and resume from the latest verified checkpoint.
4. If a scientific run was dispatched, its identity remains consumed even if the process or platform failed.
5. Continue the highest-priority unblocked task; do not wait for a new instruction when the repository evidence is sufficient.

Priority order is P0 scientific truth, P1 next audited dataset, P2 validated surrogate, P3 observation/visibility integration, then P4 robustness and maintainability.
