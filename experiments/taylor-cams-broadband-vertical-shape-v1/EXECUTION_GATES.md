# Binding execution gates

These gates were frozen while CAMS PR #505 was still retrieving and before its endpoint result was opened.

A future scientific workflow may execute or interpret the Taylor CAMS broadband vertical-shape comparison only in this order.

## Gate 1 — immutable endpoint identity

Pin the successful PR #505 head, workflow run ID, artifact ID/name, and artifact digest. Refuse any other profile bytes.

## Gate 2 — CAMS endpoint sanity

Both `analysis00` and `forecast03` must independently satisfy:

- exactly 137 model levels;
- finite nonnegative ext532, with at least one positive level;
- strictly increasing reconstructed height after sorting;
- finite positive surface pressure;
- finite positive direct AOD532;
- `0.95 <= integratedExtinctionTau532/directCamsAOD532 <= 1.05`.

Any failure stops the experiment. No alternate cycle/profile or widened gate may be selected afterward.

## Gate 3 — exact input-delta dry audit

Run `preflight.py` using the immutable Taylor-v1 runner and exact CAMS bytes. For all 3 rows × 2 replicates × 64 rays, render the same-seed/same-case-path default input, insert the CAMS tau line, and prove byte-for-byte equality after deleting exactly that one inserted line:

`aerosol_file tau <generated normalized shape file>`

The line must occur exactly once, immediately after `aerosol_default`.

## Gate 4 — one-shot scientific execution

Binding design is the later conservative pre-result freeze:

- rows 23-25 only;
- two CRN replicates;
- both conditions in replicate 1 use `951000000 + row*1000 + rayIndex`;
- both conditions in replicate 2 use `952000000 + row*1000 + rayIndex`;
- 50,000 photons/ray/condition;
- 768 solver calls / 38.4M configured photon histories;
- no GitHub rerun/retry/resume reusing the identity after any solver invocation.

The earlier 384-call sketch is superseded and nonbinding.

## Gate 5 — fresh-default self replication

Before CAMS-shape results are interpreted, run `check_default_replication.py` against immutable Taylor-v1 row artifacts from scientific run `33015974632`.

For every row and both fresh replicates:

`z = abs(Qfresh - QtaylorV1) / sqrt(sigmaFresh^2 + sigmaTaylorV1^2)`

All 6 checks must satisfy `z <= 5.0`. A single failure stops scientific interpretation. Do not average away a failure, inflate sigma, or change the gate.

## Gate 6 — frozen analysis

Only after Gates 1-5 pass may `analyze.py` report the paired broadband CAMS-shape minus default magnitude shifts and the orientation-only residual consequence.

No AOD fitting, SQM zero-point fitting, response adjustment, profile smoothing chosen from results, F/tau/human change, Level-B promotion, late-row lunar interpretation, or human first-seeing validation is authorized.
