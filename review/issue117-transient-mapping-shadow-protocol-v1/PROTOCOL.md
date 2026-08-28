# Issue #117 transient mapping shadow protocol v1

Status: **REVIEW ONLY / NO EXECUTION / NO SEMANTIC CHANGE**

This protocol is frozen **before** inspecting the output of the real-trajectory diagnostic in PR #577. Its purpose is to prevent hindsight selection of a replacement transient mapping.

## Bound identities

- `search-maker/starsvisibility` scientific application baseline: `e0da52eb0a2d5bac333da6572f51df52ea7e676e`
- current transient state model remains unchanged for this comparison: first-order log-luminance state from `transient-adaptation.mjs`
- default field factor remains `F = 3.14`
- tau values are sensitivity-only: `20, 30, 45, 60 s`
- Crumey Eq.34 frozen negative-slope interval from PR #119: `B = 0.021567318651181808 .. 0.04705255275868123 cd/m^2`

No candidate below changes physical sky radiance, stellar extinction, atmosphere selection, `F`, `tau`, the adaptation ODE, or production routing.

## Why a mapping comparison is needed

Spillmann, Nowlan & Bernholz (1972; DOI `10.1364/JOSA.62.000177`) support adding a real background to an **equivalent background inferred from threshold elevation**. They do not define equivalent background as a direct EMA-minus-current luminance difference. Cameron/Pianta/Lamb-style Crawford transformations likewise infer equivalent background by applying the inverse steady-state increment-threshold relation to a measured/modelled desensitisation state.

The current shadow implementation instead turns the lagged photometric state directly into a luminance debt, adds that debt to local detection `B`, and re-evaluates the steady-state Crumey threshold. Because Eq.34 has a small frozen non-monotone region, a positive debt can formally improve limiting magnitude. That contradicts the intended interpretation of the debt as desensitisation.

## Notation

For a given timestamp:

- `B_d`: physical local detection-background luminance.
- `B_a`: physical broad adaptation-field luminance.
- `B_lag`: lagged adaptation-state luminance returned by the unchanged Version-0 state model. For waning support, `B_lag >= B_a`.
- `D = B_lag - B_a >= 0`: current photometric debt.
- `T(B)`: the unchanged steady-state point-source required-signal threshold corresponding to Crumey/Blackwell full-branch `F=3.14`. Comparisons should be carried out in required-signal/threshold space; magnitude differences are derived afterwards.
- `E(B0,B1) = max(T(B) for B in [B0,B1])` for `B1 >= B0`: path-envelope threshold over the closed interval. The implementation must locate all analytic/numerically certified stationary extrema of the frozen threshold function in the interval; a coarse sampling grid is not an acceptable final implementation.

## Candidate 0 - current mapping, diagnostic baseline only

`B_eff = B_d + D`

`T0 = T(B_eff)`

This is retained only as the baseline that exposes the known topology problem. It is **not** eligible for semantic promotion unless it independently satisfies all invariants, which the PR #119 counterexample already shows it does not.

## Candidate 1 - endpoint floor (PR #116 semantic baseline)

`B_eff = B_d + D`

`T1 = max(T(B_d), T(B_eff))`

Purpose: reproduce the proposed PR #116 idea in threshold space. This guarantees no better threshold than instantaneous equilibrium at the two endpoints, but it may miss an interior maximum of `T(B)` when the interval crosses the Eq.34 non-monotone region.

PR #116 remains unmerged regardless of the diagnostic outcome until the comparison below is complete.

## Candidate 2 - path-envelope luminance-debt mapping

`B_eff = B_d + D`

`T2 = E(B_d, B_eff)`

Purpose: minimally preserve the current interpretation of `D` as an equivalent luminance debt while enforcing the physical invariant that increasing positive debt cannot improve sensitivity merely because the fitted steady-state threshold has a local wiggle.

Properties to test:

- equilibrium identity when `D=0`;
- `T2 >= T(B_d)`;
- monotonic non-decrease of `T2` as `D` increases with all physical inputs fixed;
- exact equality with current mapping whenever `T(B)` is monotone non-decreasing on `[B_d,B_eff]`;
- continuity at the frozen Eq.34 transition boundaries.

## Candidate 3 - adaptation-threshold-ratio mapping

This candidate does **not** add a broad-field adaptation debt directly to local detection luminance.

First derive a desensitisation factor from the broad adaptation field:

`R = E(B_a, B_lag) / T(B_a)`

with the invariant `R >= 1`.

Then apply that factor to the local physical detection threshold:

`T3 = T(B_d) * R`

Purpose: keep the broad adaptation state and local detection background explicitly separate. This is closer to a threshold/desensitisation interpretation: the adaptation history contributes a threshold elevation ratio, while the instantaneous local sky remains the physical `B_d` used by the steady-state visibility model.

Properties to test:

- equilibrium identity when `B_lag=B_a`;
- `T3 >= T(B_d)`;
- monotonic non-decrease in lag/debt;
- no mutation of physical `B_d`;
- when `B_a=B_d` and `T(B)` is monotone on the relevant interval, quantify rather than assume agreement/disagreement with Candidate 2.

## Candidate 4 - threshold-derived equivalent-background reconstruction

This is a literature-structure candidate, not yet a preferred mapping.

1. Obtain an adaptation-induced target threshold `T_adapt` from an independently specified threshold-state rule, initially using the preregistered path envelope on the **adaptation field** only: `T_adapt = E(B_a,B_lag)`.
2. On a separately frozen monotone representation of the steady-state threshold relation, invert `T_adapt` to obtain the total background `B_total,a` that would produce the same threshold.
3. Define `B_eq = max(0, B_total,a - B_a)`.
4. Evaluate local detection with `B_d + B_eq`, again using a monotone/path-safe threshold evaluation.

This mirrors the logical order of a Crawford/equivalent-background transform (threshold/desensitisation -> inverse steady-state relation -> equivalent background -> combination with real background). It must not be treated as validated until the monotone inverse and the threshold-state rule are independently justified.

## Frozen mathematical acceptance invariants

Every candidate eligible for further shadow validation must satisfy, over both synthetic edge grids and the real trajectories from PR #577:

1. **Equilibrium identity:** zero adaptation lag gives exactly the current equilibrium threshold.
2. **No beneficial debt:** positive adaptation debt never lowers required signal or improves limiting magnitude relative to equilibrium.
3. **Debt monotonicity:** with all physical inputs fixed, increasing lag/debt cannot decrease required signal.
4. **Continuity:** no material discontinuity is introduced at the Eq.34 transition interval or at candidate branch boundaries.
5. **Physical-sky separation:** no candidate overwrites or relabels MYSTIC/Level-B physical sky radiance as an adapted sky measurement.
6. **No double counting:** adaptation correction remains forbidden for observer criteria whose field factor/calibration already absorbed transient adaptation.
7. **Order independence:** event root queries must remain pure reads of a precomputed chronological state.
8. **Out-of-domain fail closed:** material brightening, unsupported history, missing required channels, and invalid state remain refusals rather than extrapolations.

## Frozen comparison outputs

For each candidate, night, tau and target trajectory, report only diagnostics until a later gate:

- count/fraction of supported states;
- equilibrium identity error;
- minimum transient penalty in required-signal and magnitude space;
- monotonicity violations under synthetic increasing-debt probes;
- maximum difference from Candidate 0 outside the frozen non-monotone region;
- Candidate 1 vs Candidate 2 difference when the interval contains an interior threshold maximum;
- Candidate 2 vs Candidate 3 differences as a function of `B_a/B_d` and debt ratio;
- event-time shift only in a later **shadow** run after mathematical invariants pass.

No Taylor residual, Jerusalem observational residual, first-seeing event error, or desired timing may be used to rank or select candidates.

## External-evidence gate

Mathematical success is necessary but not sufficient. Before semantic replacement:

- document the Spillmann/Crawford equivalent-background construction and its domain;
- document known failures/limitations of equivalent-background equivalence across temporal/spatial conditions;
- seek natural-twilight or suitably dynamic-background psychophysical evidence relevant to the seconds-to-minutes waning regime;
- preregister which external evidence would favor a luminance-equivalent mapping versus a threshold-ratio mapping.

If independent evidence cannot discriminate candidates, retain uncertainty/shadow alternatives rather than selecting from observational fit.

## Shadow-validation gate

Only after a candidate passes the mathematical and external-evidence gates may a separate PR:

- implement it in shadow-only code;
- rerun frozen synthetic diagnostics;
- rerun the two existing canonical Jerusalem Tishrei/Tammuz benchmark trajectories;
- compare against the existing fail-closed behavior;
- quantify timing sensitivity without fitting to Taylor/Jerusalem observations.

Production/UI/default routing remains unauthorized. PR #116 remains unmerged until this sequence is resolved.
