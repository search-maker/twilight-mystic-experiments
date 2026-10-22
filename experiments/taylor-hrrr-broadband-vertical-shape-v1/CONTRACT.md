# Taylor HRRR broadband vertical-shape v1

Status: **review-only until separate scientific execution is authorized.**

## Question

The preregistered HRRR vertical-shape MYSTIC diagnostic at 550 nm (PR #491, run `33033634173`) moved rows 23–32 darker by about 0.31 mag on average. This follow-up asks one narrower question: does that already-established vertical-shape effect survive the full Taylor-v1 `380–780 nm` original-SQM forward operator, or was its scale mainly a single-wavelength artifact?

This experiment does **not** promote HRRR smoke mass to a calibrated aerosol optical profile. HRRR remains a normalized vertical-shape proxy only.

## Frozen source identity

- Taylor-v1 science source SHA: `7231bd873859cc8c36fe6749985e0ece193b5de7`.
- Taylor-v1 original science run: `33015974632`.
- HRRR raw source run: `33031968397`.
- HRRR raw artifact: `9630599968`, ZIP digest `sha256:afd3f5fbf3e20674a1c5432112ce36fcb7f6678690f9ea8cff5ef6bcca5d5c9c`.
- HRRR raw `point_profile_raw.csv` SHA-256: `929e787c15f8d689bf63a732152eb552e621542325e4942d4d48bf91eb6d75a9`.
- Frozen HRRR vertical-shape implementation source: commit `3b32dfba4d861c0db8a4c2dac3e2d5c4ce73e359`, file `experiments/taylor-hrrr-vertical-sensitivity-v3/run_profile_row.py`, Git blob `572e80fef1c0456011f09d176a2ae0adf20a597f`.

## Frozen rows

Only Taylor primary rows **23, 24, 25** are in scope. These are the final three preregistered primary rows before the geometric Sun-altitude `-6 deg` cutoff. Rows 26–32 remain excluded because Taylor-v1 classified them secondary without a validated lunar/background model.

## Frozen physical transformation

For each row:

1. use the independently retrieved HRRR-Smoke MASSDEN/HGT profile at 01Z and 02Z;
2. use the already-reviewed HRRR v3 interpolation/integration code to construct normalized layer mass fractions on the exact Taylor/libRadtran site grid beginning at 0.262 km;
3. treat those normalized fractions as an aerosol optical-depth **shape proxy** with `aerosol_file tau`;
4. keep the unchanged frozen Taylor-v1 row AOD550 via `aerosol_set_tau_at_wvl 550 <row AOD550>`;
5. keep Taylor-v1 `aerosol_default` SSA/phase/spectral law unchanged.

Thus HRRR supplies vertical distribution only; it supplies neither total AOD nor aerosol optical properties.

## Frozen radiative-transfer and instrument operator

Both default and HRRR-shape conditions use the immutable Taylor-v1 renderer except that the HRRR condition contains one additional physical input line immediately after `aerosol_default`:

`aerosol_file tau <generated normalized HRRR shape>`

Everything else remains Taylor-v1:

- direct libRadtran/MYSTIC, `mc_spherical 1D`;
- `wavelength 380 780` with `mc_spectral_is 550.0`;
- AFGLUS and exact 0.262-km site-grid treatment;
- row solar geometry and surface pressure;
- day 220, albedo 0.15;
- original wide-angle Unihedron SQM 64-ray angular quadrature;
- frozen SQM spectral response and Hoya incidence-angle correction.

## Frozen Monte Carlo design

- rows: 23, 24, 25;
- conditions: Taylor-v1 default vertical profile and HRRR vertical-shape proxy;
- two paired common-random-number replicates;
- 50,000 photons per ray per condition per replicate;
- 3 rows × 64 rays × 2 conditions × 2 replicates = **768 solver calls**;
- 38.4M configured photon histories;
- replicate 1, both conditions: `955000000 + row*1000 + rayIndex`;
- replicate 2, both conditions: `956000000 + row*1000 + rayIndex`.

The 955/956 namespaces were searched before freeze and were absent from the repository. No retry/rerun/resume may reuse this scientific identity after any solver invocation.

## Binding pre-interpretation gates

1. immutable Taylor-v1 and HRRR source identities/hashes verified;
2. HRRR HGT/MASSDEN/PRES profile remains 50 joined hybrid levels at both 01Z and 02Z, with `rho dz / COLMD` within the already-reviewed 0.98..1.02 sanity interval;
3. dry same-seed/same-case-path audit proves every HRRR input is byte-identical to the corresponding default input except exactly one inserted `aerosol_file tau` line;
4. before HRRR-shape contrast interpretation, each of the six fresh default results (3 rows × 2 replicates) must reproduce immutable Taylor-v1 `primaryQ` within **5 combined Monte-Carlo sigma**.

A single gate failure stops interpretation. No averaging away a failed replicate, sigma inflation, or threshold change is permitted.

## Frozen outputs

Primary:

- original-SQM response integral for default and HRRR conditions;
- paired `deltaMag = -2.5*log10(Q_HRRR/Q_default)` per replicate;
- row mean, sample SD and SE;
- orientation-only consequence for the already-frozen Taylor-v1 observed-minus-model residual.

Secondary deterministic diagnostics from the same angular-weighted 8001-node raw sky spectrum:

- photopic luminance;
- scotopic luminance;
- Johnson-V effective radiance;

using the already-reviewed `experiments/aerosol-family-challenge-v2/derived_channels.py` implementation, pinned blob `ccfd04d4c21188966351f4257e92893d7ce340c7`. These secondary channels do not replace the original-SQM primary metric.

## Boundaries

No AOD fitting/substitution, SQM-zero-point fit, response adjustment, profile smoothing chosen from results, row addition, F/tau/human change, Level-B promotion, production change, lunar/background reinterpretation, or human first-seeing claim is authorized. A result only tests the spectral robustness of the already-existing HRRR vertical-shape sensitivity.