# Waning-background dark-adaptation source admission v1

Status: **review-only literature admission. No runtime model, parameter change, Taylor/Jerusalem scoring, or production behavior is authorized.**

## Primary source

Lothar Spillmann, Anne T. Nowlan, and Charles D. Bernholz, **“Dark Adaptation in the Presence of Waning Background Luminances,”** *Journal of the Optical Society of America* 62(2), 177–181 (1972).

- DOI: `10.1364/JOSA.62.000177`
- PubMed PMID: `5009383`
- Optica record: https://opg.optica.org/josa/abstract.cfm?uri=josa-62-2-177
- Author/full-text copy surfaced through University of Nebraska-Lincoln / ResearchGate: https://www.researchgate.net/publication/18160198_Dark_Adaptation_in_the_Presence_of_Waning_Background_Luminances

## Why this source is admitted

This is unusually direct evidence for the project’s transient-adaptation question because it studies **visual threshold while the adapting background itself continuously decreases**, rather than ordinary dark adaptation after an abrupt switch to darkness. The authors explicitly frame the motivating natural case as twilight/dusk.

The source therefore supports replacing an arbitrary single-time-constant intuition with a history/rate-dependent **review hypothesis**. It does **not** by itself validate naked-eye stellar first-seeing.

## Experimental design supported by the paper

The paper reports one observer (author ATN), using a three-channel visual discriminometer. The adapting/background field subtended 30 degrees. Threshold measurements were made after 45 minutes of dark adaptation and, except for a specifically separate condition, after five minutes of pre-exposure to 325 millilamberts.

For the principal waning-background condition, log background luminance was reduced continuously and linearly from the pre-exposure level to `3.25e-5 mL`, a total span of seven log units, over four durations:

| Duration | Log-luminance descent rate |
| ---: | ---: |
| 3.5 min | 2.000 log10 units/min |
| 7 min | 1.000 log10 unit/min |
| 14 min | 0.500 log10 unit/min |
| 21 min | 0.333333 log10 unit/min = 1 log unit / 3 min |

Three runs were made for each of those four rates in random order. A separate no-pre-exposure condition used the 3.5-minute / seven-log-unit descent and had four runs. A stationary-background comparison adapted the observer for 90 seconds at each fixed luminance level.

The authors also temporarily removed the 14- and 21-minute waning backgrounds for 15–90 seconds to measure dark thresholds while the otherwise scheduled background descent continued invisibly.

## Results that may constrain a transient model

The following statements are source-supported and may be used as **literature constraints**, not fitted project parameters:

1. Thresholds under waning backgrounds lagged ordinary dark-adaptation thresholds, with the amount and form of delay depending on background-change rate and pre-exposure history.
2. Through most of the photopic range, stationary and waning-background increment thresholds were close. A larger separation appeared below about `0.3 mL`, increasing as luminance fell and as the descent rate increased.
3. The maximum reported dynamic-versus-stationary threshold elevation was about **1.25 log10 units** for the fastest/pre-exposed condition. At the same low background reached after 21 minutes, the reported deviation was about **0.2 log10 unit**.
4. In the fast 3.5-minute condition **without** the prior pre-exposure bleach, the largest reported deviation from the equilibrium increment-threshold curve was only about **0.4 log10 unit**. This establishes that prior light history is a major part of the effect and forbids modeling the penalty as a function of instantaneous luminance or descent rate alone.
5. When the 14- or 21-minute waning background was temporarily removed, dark thresholds remained elevated relative to ordinary dark adaptation: on average about 2x and 3x respectively in the reported experiment. Thus at least some history effect persisted even when the real background was removed.
6. The authors interpret the data using the concept of a **real background plus an equivalent background** associated with the prior exposure/bleach, while also acknowledging that the mechanism is not settled.
7. They state that the dynamic-versus-stationary threshold difference should disappear if the adapting luminance changes slowly enough for recovery to reach equilibrium.
8. Their concluding rate statement is that the eye approaches optimum light-discrimination performance when adapting luminance decreases no faster than about **1 log unit per 3 minutes**; they explicitly say the relationships should also apply to slower light-to-dark transitions such as twilight and dusk.

## Natural-twilight applicability stated by the paper

The paper itself estimates that global sky luminance changes by nearly seven log units while the Sun moves from roughly 5 degrees above to 15 degrees below the horizon, over about 1.5–2 hours in nature.

Taken literally, that corresponds to only about `0.058–0.078 log10 unit/min`, which is roughly **4.3–5.7 times slower** than the slowest laboratory seven-log descent (21 minutes; 0.333 log/min). This comparison is useful but must be treated as a source-level orientation, not a calibrated mapping to the project’s exact local line-of-sight twilight radiance history.

In particular, the paper does **not** justify importing its 1.25-log-unit maximum into ordinary astronomical twilight. That maximum occurred in a much faster laboratory descent with a specific pre-exposure history.

## What this source does NOT establish

This paper alone does not establish any of the following:

- a universal adaptation time constant `tau`;
- an exact transient penalty for star first-seeing;
- foveal versus averted-vision stellar detection behavior;
- a spectral/mesopic correction appropriate to real twilight colors;
- the angular field over which the project observer actually adapts in open-sky viewing;
- observer-to-observer variability (the study used one observer);
- the effect of realistic changing gaze, horizon/zenith gradients, Moon, artificial light, or clouds;
- a production-ready formula for the starsvisibility application.

The laboratory stimulus, adapting field, pre-exposure protocol, threshold task, and observer population differ materially from naked-eye stellar first-seeing. Any model built from this paper must remain review/experimental until independently tested.

## Binding next step

The paper contains graphical curves rather than a machine-readable numerical threshold table. Therefore **no numeric curve fitting is authorized from prose values alone**.

A later, separate review identity may digitize Figures 1–3 with explicit image provenance and digitization uncertainty. If that is done, model families must be specified **before** scoring project star-visibility events. A preferred physically interpretable candidate is a nonnegative history state represented as an additional/equivalent background added to the instantaneous real background, because that structure is directly motivated by the paper. Alternative history kernels may be compared only against the admitted psychophysical data, not selected to make Jerusalem/Taylor predictions later.

Any fitted parameters must be learned from the external psychophysical curves only. Taylor, Tishrei, Tammuz, halachic event times, and desired early/late outcomes remain forbidden for fitting or model selection.

## Relation to the current project model

This admission does **not** change the current experimental transient model or its frozen `tau`. It establishes that:

- a transient effect is scientifically plausible and directly studied under waning backgrounds;
- instantaneous-luminance-only treatment is incomplete in at least some conditions;
- the effect depends strongly on pre-exposure/history and rate;
- ordinary natural twilight may occupy a much slower descent-rate regime than the laboratory maxima;
- consequently, neither “transient adaptation is negligible” nor “transient adaptation explains several minutes” is justified before a source-anchored quantitative reconstruction is completed.
