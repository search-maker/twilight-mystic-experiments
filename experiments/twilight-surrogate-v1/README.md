# Twilight surrogate v1 synthetic harness

This package prepares the sampling and surrogate path without consuming or claiming scientific data.

It provides:

- explicit train, validation, and withheld splits;
- a log-radiance ridge surrogate with a frozen engineered basis and explicit distance sensitivities;
- uncertainty and nearest-sample distance reporting;
- out-of-domain detection;
- deterministic adaptive case selection;
- a two-stage allocation rule using additional **independent** Monte Carlo blocks;
- frozen synthetic-only acceptance gates.

The generated dataset is analytic contract-test data. It is not MYSTIC output, an atmospheric model, a physical validation, or an observation. Passing this harness does not authorize a LUT, website default, or production prediction.
