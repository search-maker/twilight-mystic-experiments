# Observation Integration V2

This package defines **contracts only** between observations, atmosphere metadata, radiance providers, star-visibility integration, and a future isolated caller in the main application. It does not change any active website or production default.

## Immutable scientific boundaries

- Calibration observations may be used for tuning; untouched validation observations may not.
- A validation record marked `usedForTuning: true` is rejected.
- Role changes require append-only `roleHistory`; provenance is mandatory and never discarded.
- Canonical SHA-256 hashes are field-order independent and exclude only the hash field itself.
- Every radiance response carries exact model artifact, dataset, source-code, uncertainty, training-distance, out-of-domain, production-eligibility, and observation-validation status.
- `outOfDomain` must propagate with `OUT_OF_DOMAIN`; it cannot be production eligible.

## Synthetic-only boundary

`synthetic_radiance_response()` exists solely to prove deterministic wiring. It is not MYSTIC, not a surrogate artifact, not atmospheric truth, and not a visibility model. Every visibility payload freezes:

- `syntheticOnly: true`
- `scientificVisibilityModelInstalled: false`
- `productionUseForbidden: true`
- `observationallyValidated: false`

## Dependencies still missing

Surrogate-dependent fields: `modelId`, `modelVersion`, `modelArtifactHash`, `sourceDatasetHash`, `sourceCodeSha`, spectrum, photopic integration, uncertainty, uncertainty method, nearest-training-distance, and out-of-domain classification.

Star-visibility-model-dependent fields: extinction transformation, color response, observer adaptation, detection threshold/probability, and any predicted visibility result. This package intentionally emits no such prediction.

Observation-dependent fields: validation status, calibration adequacy, domain coverage, residual/error evidence, and any permission to use the model operationally.

## Before production

A separately approved exact surrogate artifact must satisfy the request/response contract; a real scientific visibility model must be installed; calibration and untouched validation datasets must be audited; uncertainty and out-of-domain behavior must pass gates; production eligibility must be granted explicitly; and a separate change must connect the contract to the active application.

## Validation

```bash
PYTHONPATH=experiments/observation-integration-v2 python -m unittest -v tests/test_observation_integration_v2.py
python -m py_compile experiments/observation-integration-v2/*.py tests/test_observation_integration_v2.py
```
