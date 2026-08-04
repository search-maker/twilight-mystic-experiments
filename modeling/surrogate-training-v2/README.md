# Surrogate training v2 and Tier-1 dataset adapter

This package prepares model-training infrastructure without fitting any real MYSTIC Tier-1 data and without authorizing production use.

## Owned scope

- strict `tier1-numerical-dataset.json` ingestion and provenance validation;
- immutable separation of surrogate-training, internal-holdout, hard external anchor, and g01 soft-diagnostic records;
- a preregistered small candidate family;
- training-side cross-validation and deterministic model selection;
- model freezing before one-time internal-holdout evaluation;
- hard-anchor evaluation only after holdout;
- g01 report-only evaluation;
- model artifact provenance, uncertainty, and out-of-domain metadata;
- synthetic-only fixtures and direct contract tests.

This package does not modify Tier-1 execution, recovery, authorization, workflow dispatch, precision continuation, Tier-2 authorization, observation integration, the production website, production defaults, or the scientific visibility model.

## Dataset gate

`adapter.py` refuses a dataset unless the dataset and its independent envelope prove:

- exact schema, stage, status, geometry count, frozen roles, and exact `main` SHA;
- matching raw SHA-256 bindings for the dataset, design, manifest, aggregate, independent audit, and analysis;
- aggregate, independent audit, precision classification, and provenance validation all passed;
- unique geometry and case IDs;
- disjoint training, holdout, hard-anchor, and soft-diagnostic IDs;
- no `ADAPTIVE_CONTINUATION_REQUIRED` geometry;
- complete case IDs and source bindings;
- finite geometry values and positive finite radiances.

The current merged Tier-1 analyzer emits schema version 1 without the full envelope required here. A later Tier-1 handoff must add or generate the schema-version-2 dataset and envelope without weakening this adapter.

## Frozen evaluation order

1. Use surrogate-training geometries only for five-fold cross-validation, candidate-family selection, hyperparameter selection, transformations, uncertainty rules, and out-of-domain rules.
2. Freeze the selected family, hyperparameters, transformations, normalization constants, thresholds, source hashes, and generated model hash.
3. Open the internal holdout once. Its results cannot change the model family, features, hyperparameters, thresholds, uncertainty calibration, or OOD rule.
4. Evaluate hard external computational anchors separately.
5. Report g01 separately as a soft diagnostic. It cannot by itself pass or fail the model.

Calibration observations and validation observations are forbidden in this package.

## Candidate protocol

`candidate-protocol.json` preregisters exactly three candidates:

- a transparent constant log-radiance baseline;
- fixed-basis log-radiance ridge regression;
- local log-radiance inverse-distance interpolation with uncertainty and OOD reporting.

No candidate may be added after internal-holdout results are visible. Synthetic results cannot establish which family is appropriate for real MYSTIC data.

## Synthetic fixture

`synthetic_fixture.py` generates the exact adapter-facing schema and always marks every generated artifact with:

- `syntheticOnly: true`;
- `scientificExecution: false`;
- `observationallyValidated: false`;
- `productionModelReady: false`;
- `successDoesNotAuthorizeProduction: true`.

Tests may copy the fixture and temporarily alter the envelope solely to exercise the strict reader path. Such a test object is not a scientific artifact and cannot authorize real fitting.

## Reused concepts from PR #11

Only general ideas were retained: explicit split isolation, log-radiance modeling, uncertainty, nearest-training distance, out-of-domain reporting, and deterministic behavior. The code, dataset contract, candidate protocol, tests, artifact boundary, and Tier-1 integration were rewritten against current `main`. PR #11 must not be merged into this branch.

## Production boundary

A successful contract run proves engineering behavior only. It does not prove physical validity, observational validity, model-family suitability for MYSTIC, LUT readiness, production readiness, or permission to change any production default.
