# Issue #117 astronomy gaze / averted-vision evidence addendum

Status: **REVIEW ONLY / NO IMPLEMENTATION / NO SEMANTIC CHANGE**

Primary astronomy-specific source: Alexander et al. 2021, *Gaze mechanisms enabling the detection of faint stars in the night sky*, European Journal of Neuroscience 54:5357-5367, DOI `10.1111/ejn.15335`.

This source is directly relevant to the retinal eccentricity of a known faint-star detection task, but it must not be misused as a measured natural eye-movement distribution.

## Experimental geometry and timing

From the full paper:

- Experiment 1: 12 analysed participants; Experiment 2: 14 analysed participants.
- Participants dark-adapted for **20 minutes** before the star-detection trials.
- The simulated star was fixed at the **centre of the display**.
- Experiment 1 star brightness corresponded approximately to apparent magnitude **3.3** (Megrez-like).
- Experiment 2 used a dimmer simulated star of apparent magnitude **3.5** (Tau Ceti-like).
- Experiment 1 display subtended approximately `20.5° horizontal x 15° vertical`.
- Fixation-target positions were pseudorandomly distributed around the central star. Distances were approximately uniformly distributed from about **0.5° to 20.5°** in Experiment 1; Experiment 2 extended farther, to ~32.5° horizontally.
- Success required looking within **1.5°** of the fixation target, responding within **3 s**, and not looking more than 1.5° away for >0.5 s before the response.
- Display updates were timed around saccades to reduce awareness of appearance/disappearance transients.

Thus the task measured detection performance at experimentally imposed retinal eccentricities. It did **not** measure which gaze offsets observers spontaneously choose while searching a natural sky.

## Main result frozen as a retinal-eccentricity prior

Experiment 1:

- near-foveal detection within ~1° was at chance;
- maximum performance was first achieved around **8°** from the star;
- performance over **8°–14°** was significantly above the across-distance average;
- performance declined beyond ~14°.

Experiment 2 replicated the main pattern with the dimmer star:

- peak performance again appeared in roughly the **8°–14°** range;
- performance declined beyond ~15°;
- by ~31.5°–32.5°, accuracy approached chance.

The authors report that the 8°–14° optimum was similar for naive and non-naive observers and occurred in all directions around the star rather than one special visual-field quadrant.

## Correct project interpretation

Use this source as an independent **target eccentricity sensitivity prior** for averted stellar detection.

Do NOT infer from it:

- an adaptation-field radius;
- a natural probability distribution of gaze offsets;
- a fixed 8° production parameter;
- a temporal eye-movement kernel;
- a twilight/mesopic optimum at brighter backgrounds;
- a rule that all stars/spectral types/observers have the same optimum.

The experiment used a black display after 20 min dark adaptation and targets around magnitude 3.3/3.5, not a continuously brightening/dimming natural twilight background. Its relevance to our 2°–10.5° solar-depression regime should therefore be tested as a **shadow sensitivity family**, not transferred as a calibrated twilight gaze model.

## Preregistered astronomy gaze sensitivity family

Before any split-field event-time output is inspected, a future shadow protocol should freeze at minimum:

### G0 - direct fixation control

Target eccentricity `0°`; current/direct-vision control only.

### G1 - Alexander onset prior

Target eccentricity around **8°** from fixation. This represents the first eccentricity at which the source experiment reached maximum detection, not a unique optimum.

### G2 - Alexander peak-band sensitivity

Represent the **8°–14°** band as multiple fixed eccentricity arms (for example source-defined endpoints and a midpoint), not as a fitted continuous distribution. Exact numerical arms must be frozen before event results.

### G3 - broader historical/rod-density control

Include a larger ~20°–25° eccentricity arm only as a historical/rod-density control because the source experiment found it worse than 8°–14° for the tested faint stars.

No arm may be selected from Taylor/Jerusalem event-time agreement.

## Interaction with spatial adaptation field

For each fixed gaze/eccentricity arm:

- define local physical detection background `B_d` at the star's retinal/task location;
- define the adaptation-field spatial region relative to the **retinal task/fixation geometry**, not merely to sky coordinates;
- if using the Uchida-Ohno 12.4°-radius local field, state whether it is centred on the star/task point exactly as in that source experiment;
- if using a CIE-style evaluation-area control, define the area independently of the observed event result;
- if using surrounding kernels, angles must be computed relative to the frozen retinal task/fixation geometry.

This keeps gaze geometry, adaptation-field size, threshold mapping and state dynamics as separate experimental factors rather than fitting one combined correction.

## Hard boundary

This addendum adds no workflow, eye-movement implementation, star-threshold change, MYSTIC run, tau/F tuning, observational fitting or production routing. It is preregistration/evidence only.