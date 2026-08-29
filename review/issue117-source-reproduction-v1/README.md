# Issue #117 — Spillmann dynamic-waning source reproduction v1

Status: **RESEARCH / SOURCE-REPRODUCTION ONLY / NO ASTRONOMY OUTPUT / NO SEMANTIC CHANGE**

Parent protocol: PR #583, exact parent head `f48cc9bd6407be3eb6ed8abcb1ac43dfd25fae59`.

Application model checked: `search-maker/starsvisibility` main `e0da52eb0a2d5bac333da6572f51df52ea7e676e`, `scientific-tools/visibility-v3/transient-adaptation.mjs` blob `fa57726073974aeab5d52721dfcf1f10b8bf8420`.

## Frozen independent source target

Spillmann, Nowlan & Bernholz (1972), *Dark adaptation in the presence of waning background luminances*, JOSA 62(2):177–181, DOI `10.1364/JOSA.62.000177`.

The source varies a spatially uniform adapting background continuously downward by 7 log10 units over 3.5, 7, 14, or 21 minutes and reports that transient sensitivity lags stationary sensitivity, with the lag depending on decline rate/history. These source durations were frozen in PR #583 before this audit. No Taylor/Jerusalem residual, event time, or desired answer is used here.

## Exact state equation tested

The current project state is first-order in log10 luminance:

`da/dt = (x-a)/tau`, with `x=log10(B_a)`.

For a linear decline `x(t)=x0-r*t`, define `delta=a-x`. With initial lag `delta0`, the exact solution is

`delta(t) = r*tau*(1-exp(-t/tau)) + delta0*exp(-t/tau)`.

The audit independently evaluates both this closed form and the exact interval formula used by current `transient-adaptation.mjs`, and requires agreement below `1e-12` log10 unit.

## Result

All frozen `tau = 20, 30, 45, 60 s` sensitivity arms reproduce the **source-level qualitative rate ordering without fitting**: the 3.5-min descent leaves more lag than 7 min, which leaves more than 14 min, which leaves more than 21 min. Larger tau also leaves more lag, as expected for a slower state. A stationary field is an exact equilibrium identity. An explicit positive initial lag survives as the exact additive history term `delta0*exp(-t/tau)`, so pre-exposure histories are structurally distinguishable rather than silently reset.

End-of-ramp log10 state lag (`a-x`):

| decline duration | tau 20 s | tau 30 s | tau 45 s | tau 60 s |
|---:|---:|---:|---:|---:|
| 3.5 min | 0.666648 | 0.999088 | 1.485895 | 1.939605 |
| 7 min | 0.333333 | 0.500000 | 0.749934 | 0.999088 |
| 14 min | 0.166667 | 0.250000 | 0.375000 | 0.500000 |
| 21 min | 0.111111 | 0.166667 | 0.250000 | 0.333333 |

These are **state diagnostics, not measured threshold deviations**. They must not be compared numerically to the source’s threshold elevations to select tau or a mapping candidate.

## Scientific conclusion and boundary

This closes one narrow question: the current one-state log-luminance dynamics have the correct independent **directional rate/history structure** for Spillmann’s log-linear waning backgrounds. It does **not** calibrate tau and does not validate the final astronomy transient model.

More importantly, this source cannot select Candidate 2 vs 3 vs 4. Spillmann’s source geometry is spatially uniform, so `B_a=B_d`; under that same-field condition the surviving path-safe mappings collapse to the same threshold construction (as separately established by the preregistered mapping work). Therefore:

1. Spillmann is a gate for temporal-state direction/history and for equivalent-background provenance.
2. It is **not** a mapping-selection dataset.
3. Candidate discrimination must wait for the preregistered spatial source reproduction and then the split-field astronomy shadow where `B_a != B_d`.
4. PR #116 remains ineligible as a final physiological solution.
5. `TRANSIENT_VISIBILITY_NEGATIVE_PENALTY` remains fail-closed.
6. No rod/cone split or fitted tau is authorized by this result.

## Reproduction

Run:

`node review/issue117-source-reproduction-v1/spillmann-log-ramp-audit.mjs`

The script asserts closed-form equivalence, positive waning lag, frozen rate ordering, tau sensitivity ordering, stationary equilibrium identity, and explicit-history persistence. It emits JSON diagnostics only; it does not invoke MYSTIC, Taylor/Jerusalem data, event-time scoring, or production code.

## Next preregistered gate

Implement the Stokkermans E2 spatial source reproduction from PR #583 with its source-defined geometry and ALF control, keeping physical external luminance separate from the equal `0.07 cd/m^2` target veiling-luminance condition. Only if that source-level spatial ordering passes may the project proceed to a split-field astronomy shadow. The spatial implementation must not use astronomy outputs to choose kernel size, gaze arm, or normalization.
