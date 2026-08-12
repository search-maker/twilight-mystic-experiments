# Full-spectrum estimator confirmation decision v1

This is a post-result, review-only decision package bound to ordinal-17 confirmation run `31561567317`, attempt 1, aggregate job `94010476759`, and immutable analysis SHA `69d58846e889fcd5051cdf66db9660f40d788271c0661b6742e236494f0f179d`.

It makes only geometry-specific numerical-configuration decisions. It does not select a global estimator or importance center, does not admit confirmation values as training labels, does not allocate a fresh ordinal or seed, and does not authorize fitting, holdout opening, Tier-2, or production.

Frozen result mapping:

- `train-0009` / ALIS 500 nm: confirmed at the historical 5% final target.
- `train-0014` / ALIS 600 nm: confirmed within the historical 8% maximum; the 5% scotopic target was not met.
- `train-0013`, both `train-0041` configurations, and `train-0047`: precision not established.
- `train-0047`: exact zero is preserved and remains unresolved.

The two confirmed configurations are eligible only to be referenced by a future separately reviewed **fresh** acquisition/repair contract for the exact geometry and frozen physical inputs. Confirmation values themselves remain confirmation evidence and are not training labels.

Local review:

```bash
python3 review/full-spectrum-estimator-confirmation-decision-v1/validate_confirmation_decision_v1.py \
  --analysis /path/to/confirmation-analysis-v1.json \
  --decision review/full-spectrum-estimator-confirmation-decision-v1/full-spectrum-estimator-confirmation-decision-v1.json
python3 review/full-spectrum-estimator-confirmation-decision-v1/test_confirmation_decision_v1.py
python3 review/full-spectrum-estimator-confirmation-decision-v1/test_workflow_surface_v1.py \
  --workflow .github/workflows/full-spectrum-estimator-confirmation-decision-v1-review.yml
```
