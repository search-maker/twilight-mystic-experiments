# AVPS v2 recovery2 ordinal-43 execution-control v1

Status: **review-only / zero runtime / no dispatch / results closed**.

This gate freezes the mechanical execution delta after the recovery2 successor authorization became reviewed and allocated. It does not publish an executable recovery2 workflow, create a dispatch ref or consumed marker, execute libRadtran/MYSTIC/uvspec, open any result, admit vertical profile into Level-B, access a protected holdout, use Taylor/Jerusalem residuals, or change production.

## Current reviewed identity

Ordinal 43 is the sole current recovery2 authorization identity. Authorization PR #647 remains Draft/open/unmerged at exact head `5fd0c82cb14a02ace38a5a7be30b8b075ccae298`, direct child of `0842dd27f62c4bc2af4b5763ae4dd547ee009fce`. Its protected authorization review run `33277629404`, attempt 1, completed SUCCESS and produced artifact `9722104370`, digest `sha256:9dac9e9305b78e2ddbceacbc10a19435121b0eeacfe48550d23878359556ae15`. Issue #60 comment `5465211169` records the exact single allocation marker. No ordinal-43 dispatch ref, consumed marker, science workflow run, solver execution or result opening exists at this gate.

Ordinals 41 and 42 are permanently consumed and non-reusable. Their failed attempt-1 runs produced no numerical AVPS conclusion and must never be rerun, retried, resumed, or repurposed as an execution identity.

## Frozen science

The scientific design remains exactly the already-reviewed AVPS v2 design: 360 cases, 72 common-random-number groups, five independently defined OPAC vertical-profile states, 20,000,000 photon histories per case, fixed geometry/AOD/wavelength/optical-property transport, exact four-species profile provenance, unchanged estimator/aggregation/classification/stopping rules, and closed result-opening/Level-B/holdout/production gates.

The recovery2 candidate seed identity is exactly 72 groups, canonical SHA-256 `38c074fe01bd6d09fa7dc78af1ad323e2f42b606ca992c2950b8fc1f5b343a9f`, rows canonical SHA-256 `a88b28dcfaaeb354f294d1705a0f8ddbcd061083f277a038ab8c9dace44d9954`, with zero overlap against consumed ordinal-41 and ordinal-42 seed sets.

## Required mechanical execution repair

The published recovery1 science workflow `.github/workflows/avps-v2-postconsumption-recovery1-science.yml` and publisher `.github/workflows/avps-v2-postconsumption-recovery1-dispatch-publisher.yml` are immutable historical implementation evidence bound to consumed ordinal 42. They must not be reused or edited in place to reinterpret ordinal 42 as ordinal 43.

A fresh additive recovery2 implementation must be generated/reviewed as new workflow identities. Relative to the frozen recovery1 implementation, changes are limited to:

- ordinal-43 authorization branch/head/parent/PR/review artifact and allocation marker;
- recovery2 dispatch branch, execution key, consumed marker, workflow/run/concurrency/artifact names;
- recovery2 72-seed canonical identity;
- replacing the failed relocated-ledger import with the merged `native_authorization_seed_transport.py` helper at exact Git blob `2df2c3fd1ffa78e16f44e6825d67b3e82e903c1e`;
- uniqueness queries scoped to the new recovery2 science/publisher identities.

The helper must validate the recovery2 authorization-bound ledger at its native tracked path in an exact detached authorization-head worktree, validate the historical ordinal-42 ledger at its own native historical authorization-head path, and emit `relocatedBeforeValidation=false`. Copying either ledger to a standalone temporary path before validation is forbidden.

No scientific matrix, geometry, wavelength, profile definition, optical property, photon budget, estimator, aggregation, stopping rule, threshold, analysis rule, or result-opening criterion may change in this recovery package.

## Fresh pre-dispatch gate remains mandatory

Even after candidate workflow bytes are independently reviewed and later published, a separate zero-runtime publisher gate must immediately before mutation prove all of the following against live repository state:

1. exact PR #647 authorization/review/artifact identity and exactly one allocation marker;
2. ordinal 43 remains unconsumed, the dispatch branch is absent, and there is no prior recovery2 scientific workflow-dispatch identity;
3. the recovery2 seed ledger validates at native authorization path through the reviewed helper;
4. tracked-tree and repository-global candidate-seed collision counts remain zero;
5. a fresh global ordinal/identity observation still permits only the already allocated self identity and finds no conflicting independent ordinal-43 use;
6. exact reviewed recovery2 workflow bytes are the bytes on default main;
7. run attempt is exactly 1 and rerun/retry/resume are false.

Only that later gate may create the exact dispatch ref and consumed marker once and request the fresh science workflow. A successful science execution still leaves AVPS numerical interpretation closed until the separately preregistered result-opening gate passes.

Taylor/Jerusalem residuals are prohibited from selecting recovery parameters, profiles, thresholds, mapper architecture, or acceptance rules. Vertical profile and all richer OAS-v2 Level-B mappings remain represented-but-unconsumed and unauthorized at this stage.
