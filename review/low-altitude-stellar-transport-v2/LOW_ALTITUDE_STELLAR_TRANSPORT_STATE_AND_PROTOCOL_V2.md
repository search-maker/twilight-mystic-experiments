# Low-altitude stellar transport state/protocol v2 — LOWALT-STELLAR-STATE-0002

Status: **REVIEW-ONLY / RESULT-BLIND SUCCESSOR PROTOCOL; NO STATE-0002 SOLVER CAMPAIGN AUTHORIZED BY THIS FILE**

Lane: direct stellar atmospheric transmission for target/star **topocentric vacuum/geometric altitude above the local geometric horizon**. Observer-site elevation is a separate atmosphere-truncation axis. Apparent/refracted altitude is a separate observational geometry transform.

Review branch base: public `main` `2a5a54cb24cc7cdf7baa88f56f78b9a3166cc265`.
Authoritative control ledger: Issue #60. Dashboard: Issue #668.

## 1. Durable inheritance audit

The three scientific facts below must never be collapsed into one statement.

1. **MYSTIC-STATE-0077: representation FAIL in the >=5 deg development domain.** The compact wavelength-resolved stellar transport attempt used altitude knots `5, 7.5, 10, 15, 20, 30, 45, 60, 70, 80 deg`; its independent validation points were all >=6.25 deg. Authoritative exact-runtime gate: run `31988825068`, job `95268545799`, artifact `9274892119`; 432 Pickles/Johnson-V comparisons; RMS `0.0063601882169680435 mag` passed the frozen `0.010` limit, while max `|delta A_V|=0.02627247081962647 mag` failed the frozen `0.025` limit by `0.00127247081962647 mag`. This is immutable representation-failure evidence, not a solver failure. Its residuals are forbidden as tuning/model-selection/acceptance evidence for this state.
2. **MYSTIC-STATE-0081 v2 and later v3/v3.2: successful repair for >=5 deg.** The fresh denser deterministic grid starting at 5 deg passed its fresh 576-comparison gate, with max error about `0.0075203570 mag` and RMS about `0.0013362205 mag`; later v3/v3.2 extend the upper endpoint to 90 deg. The validated >=5 deg runtime/asset semantics are a protected seam and are not redesigned here.
3. **<5 deg remains unvalidated.** LOWALT-STELLAR-STATE-0001 executed a fresh training/candidate chain and a fresh protected-v2 gate. The protected execution completed numerically but failed the preregistered scientific accuracy gate: run `33316048419`, job `99269582393`, artifact `9733633988`, digest `sha256:dcd41806c78b643c70f53d717ea6fa6ff5d0b0de843c6a6fc47de03931fb1bdf`; 176/176 spectra and 528 Johnson-V comparisons completed. Therefore that state established **no** support below 5 deg. Its opened residual pattern is sealed from successor design: no residual value, altitude pattern, sign, ranking, or near-pass/fail location may select this protocol's representation, grid, thresholds, or support floor.

Current authoritative application support therefore remains **geometric target altitude 5..90 deg** (subject to the other v3.2 LUT axes). `starsvisibility/scientific-tools/visibility-v3/stellar-spectral-runtime.mjs` currently enforces `MIN_SUPPORTED_TARGET_ALTITUDE_DEG = 5.0` and fails closed below it. STATE-0002 must not change that routing until fresh protected evidence authorizes a lower floor.

## 2. Physical geometry contract

The libRadtran pseudo-spherical direct-beam equation is the governing geometry, not scalar plane-parallel `csc(h)`. libRadtran User's Guide section 2.3.2 defines the Chapman extinction path as an integral containing the wavelength-dependent extinction profile `beta_ext(r, nu)` and replaces `tau/mu0` by that spherical path for the direct beam. Consequences fixed before any STATE-0002 result:

- RT input is geometric target altitude `h_geo > 0 deg`; source zenith angle is exactly `sza = 90 deg - h_geo`.
- `1/sin(h_geo)` is neither exact physical geometry nor an eligible below-5 extrapolation coordinate.
- There is no assumed universal one-dimensional Chapman coordinate independent of wavelength/profile: the extinction profile appears inside the spherical path integral. A source-exact compact coordinate may be considered only in a **future** separately reviewed state if derived from the pinned libRadtran implementation before protected results. STATE-0002 does not model-select such a coordinate.
- Observer elevation is separate. The atmosphere is truncated at the geometric site elevation exactly as in the inherited runtime (`atm_z_grid` begins at site height, local output `zout 0`). Target altitude must never be confused with site elevation.
- Refraction remains outside RT. Apparent/refracted altitude may be used by the observational interface, but it may not replace `h_geo` at the transport seam and may never be applied twice.
- Terrain/horizon obstruction and clouds remain separate blockers/providers. AVPS aerosol-profile science is out of scope; STATE-0002 retains the frozen AFGL-US/default aerosol family and AOD axis.

Reference: libRadtran User's Guide, section 2.3.2, `https://www.libradtran.org/doc/libRadtran.pdf`.

## 3. Frozen atmosphere/spectral identity

Preserve the established stellar identity:

- deterministic pseudo-spherical `sdisort` reference;
- wavelengths 380..780 nm inclusive at 1 nm;
- AFGL US, `mol_abs_param crs`, `aerosol_default`, albedo 0.15;
- AOD550 dimension initially `0.05, 0.10, 0.20, 0.30, 0.40`;
- observer-elevation dimension initially `0, 500, 1250, 2000, 2500 m`;
- Pickles/Johnson-V consequence using protected stellar library numbers `1, 26, 45`;
- exact 5-deg seam sourced from the authoritative v3.2 asset, never regenerated/replaced by the lower extension.

No Taylor, Jerusalem, desired halachic first-seeing time, 0077 holdout residual, or STATE-0001 protected residual may enter training, refinement, acceptance, or support-floor selection.

## 4. Representation selected a priori for STATE-0002

STATE-0002 uses **direct optical depth** `tau(lambda) = -ln(T_direct(lambda))` and multilinear interpolation on a deterministic tensor grid in:

1. geometric target altitude `h_geo`,
2. observer elevation,
3. AOD550.

This is not a claim that geometric altitude is a linearized spherical coordinate. Instead, the grid itself is refined on fresh training/model-selection evidence until interpolation is demonstrably converged to a budget much tighter than the protected gate. The protected set remains unopened during all refinement.

Initial altitude knots are inherited from the result-blind v1 preparation, not selected from any opened STATE-0001 protected residual:

`0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0 deg`.

Exact horizon `0 deg` is excluded. The inherited direct estimator normalizes by `mu0=sin(h_geo)` and therefore requires `mu0>0`. A horizon endpoint would require a separate pre-result method/state.

## 5. Fresh training/model-selection refinement — protected CLOSED

The refinement algorithm is frozen before any STATE-0002 solver result.

### 5.1 Initial tensor grid

- altitude knots: the 12 values above;
- elevation knots: `0, 500, 1250, 2000, 2500 m`;
- AOD550 knots: `0.05, 0.10, 0.20, 0.30, 0.40`.

Every tensor vertex needed by the candidate is training data. Within each current 3-D cell, two fresh model-selection probes are fixed at normalized cell fractions:

- training probe A: `(h,e,a) = (1/3, 2/5, 3/7)`;
- training probe B: `(h,e,a) = (2/3, 3/5, 4/7)`.

Fractions are applied to the cell's lower/upper bounds. These points are training/model-selection only and can never become protected evidence.

### 5.2 Numerical eligibility

Each exact training/model-selection spectrum is eligible only if:

- one intended deterministic `uvspec`/`sdisort` execution completes with exit 0;
- wavelength grid is exactly 380..780 nm / 1 nm;
- `mu0` is finite and strictly positive;
- every direct transmission is finite and strictly in `(0,1]`.

Zero/negative/nonfinite/missing direct transmission is `NUMERICALLY_UNRESOLVED`. Do not replace with epsilon; do not convert a zero to finite extinction; do not retry/resume/GitHub-Re-run the same scientific execution identity.

### 5.3 Training convergence gate

At every interior training probe, compare the exact spectrum with the candidate interpolated in `tau`, then integrate both through the frozen Pickles/Johnson-V consequence.

The **training/model-selection** budget is mechanically set to one tenth of the immutable protected gate, not tuned from results:

- local max `|delta A_V| <= 0.0025 mag` across the three frozen Pickles spectra at every training probe;
- global RMS `<= 0.0010 mag` across all training/model-selection comparisons in the refinement round.

If every local probe and the global RMS pass, freeze the current tensor grid. If not, refine without inspecting any protected value: for every failing 3-D cell, add the midpoint of that cell's altitude interval to the global altitude-knot set, the midpoint of its elevation interval to the global elevation-knot set, and the midpoint of its AOD interval to the global AOD-knot set. Rebuild the tensor grid and repeat with newly generated training/model-selection probes.

Maximum refinement rounds: **3**. No tolerance change is allowed. If convergence is still not achieved after round 3, STATE-0002 terminates `TRAINING_CONVERGENCE_FAIL`; no protected matrix may be materialized/opened under this state. This conservative all-axis refinement is intentional: it prevents post-result attribution of a discrepancy to whichever interpolation axis looks convenient.

All training/model-selection coordinates must be mechanically collision-checked against previously opened protected coordinates. A collision is a protocol/materialization failure, not permission to inspect/reuse the prior protected value.

## 6. Fresh protected matrix generation after training grid freeze

Protected coordinates do not exist numerically until the training grid is frozen. The **generation rule is frozen now**, before training and before protected results.

For every final 3-D cell with altitude interval wholly below 5 deg, generate two protected interior points:

- protected probe P: normalized fractions `(2/7, 3/11, 5/13)` in `(h,e,a)`;
- protected probe Q: normalized fractions `(5/7, 8/11, 8/13)` in `(h,e,a)`.

Use exact rational construction from decimal cell boundaries before rendering solver inputs. The resulting protected universe must be mechanically proven disjoint from:

- all STATE-0002 tensor vertices and training/model-selection probes;
- all opened STATE-0001 protected-v1/protected-v2 coordinates;
- 0077/0081/v3/v3.2 protected/holdout coordinates where applicable;
- exact 5-deg seam/control points.

If any collision exists, stop before solver execution and require a new reviewed protocol. Do **not** perturb a point ad hoc.

Each protected atmospheric spectrum produces three Johnson-V comparisons for Pickles library numbers `1,26,45`.

## 7. Protected accuracy and minimum-supported-altitude decision

Immutable protected thresholds remain:

- max `|delta A_V| <= 0.025 mag`;
- RMS `<= 0.010 mag`.

No post-result threshold relaxation is permitted.

Unlike STATE-0001's whole-domain-only protected-v2 decision, STATE-0002 preregisters a deterministic **contiguous-suffix support rule before any result**. This is the same scientific concept already present in the original result-blind v1 numerical-floor protocol; it is not selected from STATE-0001 residuals.

For each final altitude cell `[h_i,h_{i+1}]`, collect every protected P/Q comparison whose altitude lies in that cell across all elevation/AOD cells and all three Pickles spectra. An altitude cell passes only if both its max and RMS meet the frozen limits. Starting with the cell adjacent to 5 deg and moving downward, form the maximal contiguous suffix of passing altitude cells. The candidate support floor is the lower boundary of that suffix, provided the aggregate max and RMS over the entire suffix also pass the same frozen limits. Decision is mechanical:

- if the topmost `<5 deg` altitude cell fails, `minimumSupportedGeometricAltitudeDeg = 5.0`;
- otherwise the minimum is the lower boundary of the maximal contiguous passing suffix;
- any failed cell blocks all lower cells from a support claim even if a still-lower cell happens to pass;
- if all cells pass, the minimum may be `0.25 deg`;
- `0 deg` is never implied.

The complete protected result is preserved whether it passes or fails. Failed lower cells may not be used to redesign STATE-0002 or to select a new formula; any successor after a failure requires a new scientific identity and new protected evidence.

## 8. Exact 5-deg seam and runtime semantics

The lower candidate's 5-deg endpoint must be the authoritative v3.2 5-deg spectral row/content, byte/content-identical under the existing asset schema. The lower interpolator may approach that endpoint from below, but exact `h_geo = 5.0 deg` and every `h_geo > 5.0 deg` continue routing to v3.2. Required review/validation tests:

- copied seam content hash/equality against v3.2;
- exact 5-deg Johnson-V equality;
- no lower-extension overwrite of any v3.2 altitude >=5 deg;
- lower side finite/continuous as `h -> 5-` under the frozen interpolation;
- application OOD refusal below the eventual protected floor and above inherited domain bounds.

## 9. Application/refraction separation

No `starsvisibility` change is authorized while this protocol is only under review/training or while protected evidence is absent/failed. On a future admissible protected decision only:

- route RT using an explicitly named geometric/vacuum target-altitude field;
- keep apparent/refracted altitude in the observational geometry layer;
- never feed refracted apparent altitude into the transport LUT unless a separately reviewed physical contract explicitly calls for it;
- never apply refraction twice;
- fail closed below the protected minimum geometric altitude;
- keep terrain/horizon obstruction and clouds separate.

## 10. Governance and execution order

1. Review this inheritance/protocol package and its solver-free planning helper.
2. Only after review passes, create a separate fresh STATE-0002 training execution identity. No protected solver call is allowed in training/model-selection.
3. Freeze the converged grid and its content identity; then materialize/collision-audit the protected P/Q matrix from the already-frozen rule.
4. Review a one-shot protected controller bound to that exact candidate/protocol/matrix.
5. Re-read Issue #60 immediately before every repository mutation and honor any newer `WRITE_QUIET`, `NOT_ADMISSIBLE`, `DO NOT USE`, `CLOSED`, `FAIL-CLOSED`, recovery or superseding directive.
6. Execute protected attempt 1 only. Never use GitHub Re-run/retry/resume to manufacture another protected attempt under the same identity.
7. Only an admissible protected decision may lower application support.

This file authorizes **no solver execution and no application support change**. Its purpose is to put the successor design, stopping rule, freshness rule, accuracy budget, support-floor decision, seam semantics and refraction separation under review before any new scientific result exists.
