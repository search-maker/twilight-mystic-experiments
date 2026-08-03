# MYSTIC batch v1

This package introduces the reusable execution shape for future bounded MYSTIC batches:

```text
authorization / exact manifest
             |
             v
        matrix case jobs
             |
             v
          aggregate
             |
             v
     independent artifact audit
```

This change is deliberately **synthetic-only**. It contains no `uvspec` invocation, no MYSTIC execution, and no scientific classification. The purpose is to prove the matrix, isolation, aggregation, exact-manifest binding, and independent-audit contracts before a separately reviewed scientific adapter is added.

## Frozen invariants

- Every case has a unique `caseId`, seed, ordinal, and output directory.
- `strategy.fail-fast` is disabled so one failed case does not cancel diagnostic evidence from the others.
- The plan freezes the raw manifest SHA-256, exact case set, photon ceiling, and maximum parallelism.
- Synthetic jobs require the authorization file to remain disabled.
- A future scientific manifest must be bound to a one-purpose authorization containing the exact raw manifest hash.
- Scientific mode additionally requires pinned runtime identities for the container, `uvspec`, libRadtran data, and atmosphere.
- The aggregator accepts exactly one result for every planned case and rejects missing, duplicate, or extra results.
- The auditor independently recomputes case hashes, accounting, mean, sample standard deviation, and coefficient of variation.

## Local synthetic smoke test

```bash
python experiments/mystic-batch-v1/plan.py \
  --manifest experiments/mystic-batch-v1/manifest.synthetic.json \
  --authorization experiments/mystic-batch-v1/authorization.json \
  --output plan.json \
  --allow-synthetic
```

The GitHub workflow runs the complete matrix and audit path automatically using synthetic case outputs only.
