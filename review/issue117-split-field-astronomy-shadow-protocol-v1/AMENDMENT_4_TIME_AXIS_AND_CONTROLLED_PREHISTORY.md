# Issue #117 split-field SF-A — Amendment 4 / time axis and controlled prehistory

Status: **FROZEN BEFORE ANY SF-A SKY-LUMINANCE OR CANDIDATE-THRESHOLD OUTPUT / TEMPORAL-SEMANTICS CORRECTION**

The original SF-A protocol froze Sun depression samples and tau values in seconds, but did not freeze a mapping from solar depression to elapsed seconds. A first-order state with `tau={20,30,45,60} s` is undefined without that time axis. This amendment repairs that omission before any Candidate 2/3/4 shadow output is opened.

It also resolves the prehistory ambiguity without importing the existing point-field prehistory into the new split-field state.

## 1. Independent controlled solar-kinematic timing arms

SF-A remains a non-observational structural astronomy shadow. It therefore does **not** bind a named observing site/date merely to obtain timing.

Instead, for timing only, freeze the Cartesian product:

- latitude `phi = {0°,30°,45°,60°}`;
- solar declination `delta = {-23.44°,0°,+23.44°}`.

For each frozen Sun-centre depression `D`, set solar altitude `h=-D` and solve the evening hour-angle branch

`cos(H) = [sin(h) - sin(phi) sin(delta)] / [cos(phi) cos(delta)]`.

The controlled kinematic convention advances solar hour angle at exactly `15°` per mean-solar hour, so elapsed seconds are

`t(D) = [H(D)-H(2°)] * 240 s/deg`.

This is a synthetic timing arm for transient-structure sensitivity, not an ephemeris claim for a named date. Latitude/declination affect only the elapsed-time mapping; they do not alter the bound Level-B sky inputs, target geometry, AOD, threshold law, or candidate formula.

A timing arm is refused if the Sun cannot traverse the complete `2.0°..10.5°` evening-depression range. Under the frozen grid, `phi=60°, delta=+23.44°` is the sole refused arm. The other `11` timing arms are execution-eligible.

The exact deterministic audit helper is `sf-a-temporal-axis-audit.mjs` with regression `test-sf-a-temporal-axis-audit.mjs`.

Pre-output timing diagnostics are:

| phi | delta | 2°→10.5° duration (s) | minimum 0.25° step (s) | maximum 0.25° step (s) |
|---:|---:|---:|---:|---:|
| 0 | -23.44 | 2226.406550 | 65.405199 | 65.603748 |
| 0 | 0 | 2040.000000 | 60.000000 | 60.000000 |
| 0 | +23.44 | 2226.406550 | 65.405199 | 65.603748 |
| 30 | -23.44 | 2570.389778 | 74.299839 | 77.077056 |
| 30 | 0 | 2361.083068 | 69.297954 | 69.672378 |
| 30 | +23.44 | 2772.476732 | 79.027384 | 84.512105 |
| 45 | -23.44 | 3249.146652 | 92.100143 | 99.758596 |
| 45 | 0 | 2905.395104 | 84.911355 | 86.311795 |
| 45 | +23.44 | 3943.748826 | 106.071439 | 129.402961 |
| 60 | -23.44 | 5215.414598 | 137.809891 | 176.096817 |
| 60 | 0 | 4169.422022 | 120.248887 | 126.530876 |
| 60 | +23.44 | REFUSED | — | — |

No timing arm may be selected or weighted from C2/C3/C4 behavior. All 11 eligible arms are sensitivity arms.

## 2. Controlled split-field prehistory

SF-A cannot reconstruct a natural pre-sunset history from the bound Level-B provider because that provider's validated physical design box begins at `2°` solar depression. Importing the old point-field prehistory would violate the split-field definition.

For this structural shadow only, freeze a same-field controlled prelude:

- for each spatial/gaze/channel history, hold `B_a,instant` at its supported `D=2°` value for an indefinitely long synthetic interval before `t=0`;
- equivalently initialize exactly
  `a(0)=log10(B_a,instant(D=2°))`;
- then propagate the frozen first-order log state only along the chosen kinematic timing arm.

This is not a claim about natural human adaptation at the beginning of astronomical twilight. Its purpose is to remove unknown prehistory as a confound while testing whether the candidate mappings remain structurally valid and separable under identical split-field dynamics.

If the required `D=2°` split-field sample is unsupported for an arm/history, that arm/history is refused. No point-field state, borrowed earlier-time sky value, zero-fill, or fitted initial debt may substitute for it.

A later real stellar-track/first-seeing protocol must separately preregister a physically appropriate natural prehistory; SF-A cannot supply it.

## 3. Candidate-comparison consequence

For any fixed spatial/gaze/atmosphere/timing/tau arm, Candidates 2/3/4 receive **identical** `B_d(t)`, `B_a,instant(t)`, time stamps, initialization, and propagated `B_a,lagged(t)`. The only allowed difference is their frozen threshold mapping.

The timing-arm dimension is a sensitivity envelope only. It cannot be used to choose a preferred tau, candidate, latitude, declination, or astronomy answer.

## 4. Boundary

This amendment opens no Level-B luminance, no adaptation-state output, and no candidate threshold. It changes no application code, production behavior, `F`, Eq.34, tau values, atmosphere, spatial field, or mapping formula.

PR #116 remains non-final and `TRANSIENT_VISIBILITY_NEGATIVE_PENALTY` remains the authoritative fail-closed production guard.
