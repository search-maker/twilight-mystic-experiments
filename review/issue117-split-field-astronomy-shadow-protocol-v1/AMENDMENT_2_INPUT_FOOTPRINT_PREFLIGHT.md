# Issue #117 split-field SF-A — Amendment 2 / input-footprint preflight

Status: **FROZEN BEFORE ANY SKY-LUMINANCE OR CANDIDATE-THRESHOLD OUTPUT / INPUT-ONLY CORRECTION AND AUDIT**

This amendment is stacked on PR #610 exact preflight parent `87eef45a95de96466f3f8e0d10ba44d46cfbd492`. It does not inspect Taylor, Jerusalem, a protected holdout, any SF-A sky-luminance value, or any Candidate 2/3/4 threshold. It corrects one ambiguity in `PROTOCOL.md` section 3 and freezes the geometry/refusal implementation before any split-field shadow output.

## 1. Clarification of the section-3 center-direction statement

The sentence saying that “all center directions” lie far enough inside the Level-B 5°–80° target-altitude design box applies only to the three **base target directions** `{30°,45°,60°}` under `G_TARGET`.

It does **not** guarantee that the displaced `G_FIX_8`, `G_FIX_11`, or `G_FIX_14` adaptation-field centers — or their 20°/12.4° footprints — remain inside the provider design box. Their displacement is defined on the celestial sphere relative to the actual target-to-Sun great-circle direction and can move a footprint toward either altitude boundary.

This is not repaired by clipping, shrinking the field, changing the gaze offset, or renormalizing the surviving samples. The already-frozen missing-scene/support rule controls: if any required footprint direction is outside the bound provider's validated support, that spatial/gaze row is refused.

## 2. Frozen spherical geometry semantics

For the input/spatial implementation:

- set the Sun direction to altitude `-sunDepressionDeg` and azimuth `0°`;
- represent the frozen target by its target altitude and relative azimuth;
- compute `toward_sun` as the initial great-circle bearing from target to Sun;
- `away_from_sun`, `cross_plus90`, and `cross_minus90` are exactly +180°, +90°, and -90° from that bearing;
- displace the fixation center by the exact frozen eccentricity `{8°,11°,14°}` along that great circle;
- generate spatial samples by great-circle offsets from the adaptation-field center;
- map each physical direction to the axisymmetric Level-B coordinate by folding azimuthal separation from the Sun into `[0°,180°]`;
- keep `B_d` at the undisplaced target direction in every gaze arm.

The implementation must verify the requested fixation separation to `1e-9°` and refuse non-finite geometry.

## 3. Solid-angle and missing-sample contract

The audit helper implements deterministic annular spherical-cap cells with exact per-ring solid-angle accounting. Its `1°` radial step is **test/audit resolution only**; it is not yet the final SF-A luminance-execution quadrature and may not be used to claim the preregistered 16°/20° luminance-convergence gate has passed.

For any actual spatial integration:

- each sample is evaluated before normalization;
- any unsupported, unavailable, non-finite, or non-positive required channel sample refuses the arm immediately;
- normalization occurs only after the complete frozen footprint has valid samples;
- no zero-fill, interpolation, mirroring, edge clipping, or partial-footprint renormalization is permitted;
- photopic is the only candidate-mapping-eligible coordinate under Amendment 1;
- scotopic remains descriptor-only and CIE mesopic remains unavailable.

## 4. Pre-output nominal-design-box audit

A deterministic input-only audit was run over the complete frozen SF-A geometry ledger:

- base histories: `45` (`3` target altitudes × `5` target relative azimuths × `3` AOD values);
- time rows per history: `35` Sun depressions (`2.0°`–`10.5°` by `0.25°`);
- spatial/gaze input rows: `63,000`;
- nominally altitude-contained rows: `53,184`;
- rows whose frozen footprint necessarily reaches outside the provider's 5°–80° target-altitude design box: `9,816`;
- nominal containment fraction: `0.8441904761904762`.

By spatial arm:

| arm | rows | nominally complete | nominally incomplete |
|---|---:|---:|---:|
| `S0_POINT` | 1,575 | 1,575 | 0 |
| `S1_WHOLE_CAP` | 20,475 | 16,401 | 4,074 |
| `S2_ALF` | 20,475 | 16,401 | 4,074 |
| `S3_UCHIDA_LOCAL` | 20,475 | 18,807 | 1,668 |

The base `45°` target-altitude rows are nominally contained for every frozen gaze/spatial footprint. Displaced controls at `30°` and `60°` account for all design-box edge failures. These failures are retained as preregistered refusals; the grid is **not** narrowed after seeing this preflight.

This count is only a deterministic **lower bound on refusal**. The real bound provider additionally requires nearest frozen training distance `<=0.60`, valid channel output, and cloud/support status. Those checks must be applied from the exact bound application runtime; this public review package does not copy private/runtime model state merely to make unsupported rows appear usable.

## 5. Regression/audit requirements

The input-spatial helper and test must verify at minimum:

1. exact frozen 35-point Sun-depression grid and 45 base histories;
2. great-circle offset distance preservation for the 8°/11°/14° gaze controls;
3. provider relative azimuth always folded to `[0°,180°]`;
4. exact spherical-cap solid-angle totals for 12.4°, 16°, and 20° caps;
5. constant-field identity for S0/S1/S2/S3 after valid normalization;
6. strictly decreasing ALF radial weight at representative radii;
7. immediate refusal after the first invalid required spatial sample, with no partial renormalization;
8. photopic mapping eligibility and scotopic diagnostic-only status;
9. exact `63,000 = 53,184 + 9,816` preflight accounting.

Local review execution before publication: **PASS**.

## 6. Boundary and next gate

This preflight does not execute Level-B luminance prediction, does not propagate an adaptation state, does not evaluate C2/C3/C4, and does not rank any model. It therefore opens no SF-A scientific shadow result.

The next safe gate is to bind the exact application runtime privately/read-only, implement the full provider-support audit and final luminance quadrature with a separately frozen quadrature-refinement check, and only then execute the preregistered SF-A shadow. The 9,816 deterministic design-box refusals above remain refusals and may not be rescued by post-preflight geometry edits.

PR #116 remains non-final and `TRANSIENT_VISIBILITY_NEGATIVE_PENALTY` remains fail-closed.
