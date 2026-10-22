# Adaptation-field and mesopic decrement-dynamics source admission v1

Status: **review-only literature admission. No runtime formula, tau change, event-time shift, Taylor/Jerusalem scoring, or production behavior is authorized.**

This record complements the waning-background source admission in PR #523. It addresses two gaps that Spillmann et al. (1972) does not resolve for the project: **what spatial luminance distribution should define adaptation state**, and **whether one universal temporal constant can represent recovery after luminance decreases**.

## Source A — local versus surrounding adaptation field

Tatsukiyo Uchida and Yoshihiro Ohno, **“Experimental study of the visual adaptation field in mesopic photometry: Does surrounding luminance affect peripheral adaptation?”** *Lighting Research & Technology* (2014), DOI `10.1177/1477153513498084`.

- NIST record: https://www.nist.gov/publications/experimental-study-visual-adaptation-field-mesopic-photometry-does-surrounding
- Publisher DOI: https://doi.org/10.1177/1477153513498084

Source-supported constraint: mesopic peripheral adaptation depends **mainly on local luminance at the task point**, while surrounding luminance has an additional smaller effect. The authors report that the surrounding effect can exceed simple foveal veiling-luminance predictions, but is not significant for uniform mesopic luminance distributions.

A related Uchida/Ohno experimental report, **“An Experimental Approach to A Definition of The Mesopic Adaptation Field”** (CIE 2012 proceedings; NIST record published 2015), specifically varied adaptation-field extent and reports that **local adaptation for a field-of-view angle of about 10 degrees was dominant rather than global adaptation**.

- NIST record: https://www.nist.gov/publications/experimental-approach-definition-mesopic-adaptation-field

Further Uchida/Ohno work on high-luminance surrounding sources supports representing some surrounding influence as an added effective/veiling luminance whose effect decreases with angular separation, rather than replacing the local adaptation luminance by an unweighted hemispheric average.

- NIST record: https://www.nist.gov/publications/defining-visual-adaptation-field-mesopic-photometry-how-does-high-luminance-source
- Open full text: https://pmc.ncbi.nlm.nih.gov/articles/PMC11231917/
- Angular-position follow-up: https://pmc.ncbi.nlm.nih.gov/articles/PMC11526385/

### Binding project implication from Source A

The current project must keep two concepts distinct:

1. **detection background** — the local sky background against which the star is detected;
2. **adaptation state/field** — primarily local/task-centered adaptation, with a smaller angularly weighted surrounding contribution.

Neither of the following is source-justified as a physical default:

- using an unweighted or simple cosine-weighted **whole hemisphere** as the observer's adaptation luminance;
- using exactly one **single ray / target-direction luminance** as the complete adaptation field while ignoring surrounding light.

The sources support a local-dominant spatial model, but they do **not** supply an exact open-sky kernel, gaze trajectory, or one universal angular radius for naked-eye stellar first-seeing. The reported ~10-degree result is evidence of local dominance in the authors' experimental task, not authorization to hard-code a 10-degree astronomical kernel.

## Source B — recovery after mesopic luminance decrements

Celeste M. Howard, Stephen J. Tregear, and John S. Werner, **“Time course of early mesopic adaptation to luminance decrements and recovery of spatial resolution,”** *Vision Research* 40(22), 3059–3064 (2000), DOI `10.1016/S0042-6989(00)00153-X`, PMID `10996609`.

- PubMed: https://pubmed.ncbi.nlm.nih.gov/10996609/
- Publisher record/full article: https://www.sciencedirect.com/science/article/pii/S004269890000153X

Experimental design relevant to this project:

- six observers overall; principal data shown for four observers;
- Maxwellian-view adaptation;
- 20-degree uniform adapting fields at 1.6–2.6 log photopic trolands;
- 7-degree, 250-ms Gabor test stimuli;
- test field 2–3 log units lower than the adapting field;
- recovery measured from 0.25 to 9 s after the adapting field was replaced by the lower test field.

The authors fit the early recovery of **log contrast threshold** using

`log C(t) = a + b * exp(-k t)`

and report that recovery is slower for **larger illuminance decrements** and for **higher spatial frequency**. They interpret the results as evidence for a slow component of gain control and note that recovery after a decrease can be slower than recovery after an increase.

### Binding project implication from Source B

An exponential temporal state is scientifically plausible over at least one early mesopic decrement paradigm. However, the fitted recovery rate is **condition dependent**. Therefore the project may not interpret its current single `tau=30 s` as a universal physiological constant merely because a first-order exponential state is mathematically convenient.

At minimum, any source-anchored temporal model must allow the possibility that dynamics depend on:

- adapting level;
- size of the luminance decrement / recent luminance history;
- retinal task / spatial characteristics;
- observer.

Howard et al. studied an abrupt 2–3-log-unit decrement and spatial-resolution/contrast tasks over the first 9 seconds. Those conditions are not identical to gradual twilight or point-source stellar detection and must not be used to directly set a star-visibility time constant.

## Joint interpretation with Spillmann et al. (PR #523)

The three evidence strands are mutually consistent at the level justified by the sources:

- Spillmann et al.: under **continuously waning** backgrounds, threshold history depends strongly on rate and pre-exposure; real background plus an equivalent/history background is a useful interpretation; sufficiently slow change approaches equilibrium.
- Uchida/Ohno: adaptation is **local-dominant**, with a smaller surrounding contribution; whole-field light can influence the task but should not simply replace local luminance.
- Howard/Tregear/Werner: following a decrement, an **exponential-like early recovery** is observed, but its rate is not universal across decrement/task conditions.

This combination directly identifies two structural weaknesses in the current experimental project layer:

1. a discontinuous definition of adaptation field (broad hemispheric proxy in one regime, target-direction luminance in another) is not a defensible physiological definition;
2. one globally fixed tau should remain only a sensitivity parameter, not a calibrated physiological constant.

## What can be completed without new project observations

The literature is sufficient to do the following without collecting a star observation:

- reject a claim that the current `tau=30 s` is physiologically calibrated;
- reject a claim that whole-hemisphere luminance or a single target ray is uniquely the correct adaptation field;
- preserve local detection background separately from adaptation state;
- design a review-only local-dominant + angular-surround adaptation-field family;
- digitize admitted psychophysical curves and fit temporal/history model candidates **only to external data**;
- run blinded sensitivity of those externally fitted candidates on project event histories after model selection is frozen.

## What still requires empirical star/open-sky evidence

The sources do not establish:

- the gaze/search trajectory used by an observer locating a star;
- the effective angular adaptation kernel in an anisotropic real twilight sky;
- direct versus averted-vision dependence for stellar first-seeing;
- the correct interaction of spectral/mesopic state with transient adaptation for a point source;
- observer-to-observer variability relevant to the project population;
- a validated mapping from psychophysical contrast-threshold recovery to naked-eye first detection of stars.

Those remain targets for the A1/H1 observation protocol; they must not be back-fit from desired Jerusalem/Tishrei/Tammuz event times.

## Next authorized computational step

Before any runtime change:

1. obtain reproducible figure provenance for the external dynamic-adaptation data;
2. digitize curves with explicit pixel/axis calibration and digitization uncertainty;
3. preregister a small set of model families (for example, equivalent-background/history-state models and condition-dependent exponential alternatives);
4. fit/select them using **external psychophysical data only**;
5. freeze parameters/model selection;
6. only then run project-event sensitivity, preserving the current production/default model unchanged.
