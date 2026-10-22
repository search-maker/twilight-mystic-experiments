# Taylor CAMS broadband vertical-shape v1

Status: **review-only implementation; no solver workflow or scientific execution is present in this branch.**

This package implements the pre-result follow-up frozen on Taylor CAMS PR #505 before its endpoint result was opened.

## Scientific question

For Taylor rows 23-25 only, at the unchanged Taylor-v1 row AOD550 and unchanged `aerosol_default` optical-property family, how much does the full 380-780 nm original-SQM MYSTIC prediction change if only the aerosol vertical optical-depth distribution is replaced by the independently retrieved same-cycle CAMS extinction shape?

## Fixed source identity

- Taylor-v1 science source SHA: `7231bd873859cc8c36fe6749985e0ece193b5de7`.
- Taylor-v1 rows: 23, 24, 25 only.
- CAMS endpoints must come from PR #505: `analysis00` at valid 00Z and `forecast03` at valid 03Z.
- The future workflow must pin the exact successful #505 run, artifact ID, and artifact digest before any solver invocation.

## Endpoint acceptance gate

The future science run fails closed unless both CAMS endpoints have:

- exactly 137 model levels;
- finite nonnegative extinction at 532 nm and at least one strictly positive level;
- finite positive direct CAMS AOD532;
- `0.95 <= integratedExtinctionTau532 / directCamsAOD532 <= 1.05`;
- finite strictly increasing reconstructed heights and finite surface pressure.

No tolerance widening or alternate cycle/profile selection is permitted after #505 result opening.

## Vertical-shape transformation

For each accepted CAMS endpoint:

1. map the 137 extinction coefficients to the exact Taylor/libRadtran site-anchored altitude coordinate;
2. integrate extinction within every exact Taylor-v1 atmosphere layer beginning at 0.262 km;
3. normalize the above-site layer optical depths to unit sum;
4. linearly interpolate those **normalized layer fractions** in time between 00Z and 03Z for the Taylor row timestamp;
5. renormalize only for floating-point closure;
6. write the descending two-column libRadtran `aerosol_file tau` file on the exact site grid.

The CAMS endpoint total AOD is **not** used in the MYSTIC test. After the shape file is supplied, the unchanged Taylor-v1 row AOD550 is applied with `aerosol_set_tau_at_wvl 550`.

## Radiative-transfer identity

The runner imports the frozen Taylor-v1 `run_row.py` and obtains the default condition directly from its `render()` function with 50,000 photons. The CAMS condition is generated from that exact rendered input by inserting only:

```text
aerosol_file tau <exact generated tau file>
```

immediately after `aerosol_default`. Apart from the condition-specific `mc_basename`, the runner refuses the CAMS condition if any other rendered input line differs from the default condition.

Therefore both conditions preserve Taylor-v1:

- direct libRadtran/MYSTIC, `mc_spherical 1D`;
- 380-780 nm and `mc_spectral_is 550.0`;
- AFGLUS atmosphere and 0.262 km site-grid treatment;
- row solar geometry and surface pressure;
- day 220, albedo 0.15;
- `aerosol_default` SSA/phase/spectral behavior;
- frozen row AOD550;
- original wide-angle Unihedron SQM 64-ray quadrature, spectral response, and Hoya incidence-angle correction.

## Frozen Monte Carlo design

- rows: 23, 24, 25;
- 64 rays;
- conditions: default vertical profile and CAMS vertical profile;
- two paired replicates;
- 50,000 photons per ray per condition per replicate;
- 768 total solver calls, 38.4M configured photon histories;
- common-random-number pairing within each replicate: the two conditions use the same ray seed;
- replicate 1 seed: `951000000 + row*1000 + rayIndex`;
- replicate 2 seed: `952000000 + row*1000 + rayIndex`.

These namespaces were searched before freeze and were absent from the repository.

## Frozen outputs

Per row and replicate:

- default synthetic SQM-response integral;
- CAMS-shape synthetic SQM-response integral;
- `deltaMag = -2.5*log10(CAMS/default)`;
- paired aggregate spectra for diagnostic retention;
- generated layer-fraction profile and exact input hashes.

Analysis reports both replicate deltas, mean, sample SD and SE, then applies the independently computed mean model shift to the already-frozen Taylor-v1 observed-minus-model residual as an orientation-only diagnostic.

## Boundaries

No Taylor-based AOD fitting, offset fitting, row selection, profile smoothing, optical-property fitting, F/tau change, Level-B change, production promotion, lunar/background reinterpretation, or human first-seeing claim is authorized. Rows 26-32 remain outside this follow-up because the frozen Taylor validation classified them secondary in the absence of a validated lunar/background model.
