# P1 field cadence/dwell proposal — 2026-11-24 — pre-outcome candidate, not registered

Parent attention supplement c38517f40a0d7bd432c3970abeb545329f8253e6, blob c2195e0e8912564ebff3ef8027f71e3a05a5536d; existing outreach packet #152 comment 7120789424; Coordinator request 7122322092. No outcomes accessed, enrolled volunteers, scientific predictor approval, protected data, solver runs, spending or outreach.

## Source evidence and limitation

Zuidema, Bouman & Koenderink, *Detection of light and flicker at low luminance levels in the human peripheral visual system. I. Psychophysical experiments* (1984), original author abstract at https://pubmed.ncbi.nlm.nih.gov/6747741/ : controlled flashes 5–1000 ms, diameter 5.7–480 arcmin, retinal eccentricities 7 and 40 degrees. Reported preprocessing summation around 100 ms and detection summation around 500 ms, dependent on stimulus geometry. Full per-trial data not obtained. This is real lab psychophysics, not steady outdoor stellar onset and NOT a justification of a precise field minimum. Previously reviewed Alexander et al. (2021), https://pmc.ncbi.nlm.nih.gov/articles/PMC8389526/ Methods: simulated star present in half the trials, gaze tracked, response timeout 3 s after fixation and 20 min prior dark adaptation. Distinguish response opportunity from physiological integration; do not import its scotopic accuracy into twilight. No new real sky measurements.

## Prospective operational choice (review required before any outcome)

One observer/one assigned target, fixed schedule independent of predictions. Start a 10 s target-directed look every 25 s using a screen-free audio timer, with start deviation +/-2 s from its fixed UTC grid, actual duration 8–12 s, natural blinks permitted; record interruption separately. These are operational reproducibility tolerances, NOT evidence that a non-detection after 8 s proves a star is invisible. Record exact UTC start, response-window end, and actual first positive report UTC separately (do not substitute end-of-window for first detection), YES/NO/UNCERTAIN, gaze mode, target clearance, light exposures, missing checks. A NO requires full actual dwell and no interruptions. YES can be logged immediately but complete the scheduled look when practicable. Require a separate confirmation on next scheduled look, same direct unaided mode. If it fails, retain the first report but do not classify the sequence as a confirmed primary bracket; retain uncertain/averted/censored strata, never erase. End primary eligibility at confirmation; subsequent observations remain separate. No replacement of a missed/uncertain intervening check with an invented NO. Ordinary corrective lenses documented. Never look at Sun; choose safe sites and pointings. Record sky and atmosphere per existing receipt gates. Observer receives only target identity/pointing and schedule, no expected time or other observers' reports. Clock accuracy <=5 s per existing packet.

Maximum 90 min scheduled observation per observer-night plus >=10 min adaptation prior to first look (10 min planned; longer exposures recorded), 216 looks max, 24 observer-target-night sequences / 12 site-evenings / 30 calendar days / $0 as existing cap. No extra paid devices or recruitment commitments. Exact site, dates, ephemeris, magnitude/catalog inputs and end geometry must be determined prospectively by Coordinator, reject sites where selected geometry cannot fit the time cap; no after-outcome substitution or expansion. No confirmation slot left => retain censored. Feasibility screen inherited: >=8 admitted brackets across >=4 site-evenings, NOT confirmatory evidence of accuracy. Any later inferential criteria remain separate.

## Executed outcome-free integer timing grid

625 combinations: two start deviations in [-2,-1,0,1,2] seconds and two dwell durations in [8,9,10,11,12] seconds. Consecutive starts nominally 25 s apart. Define gap before next look = 25+s1-s0-d0 and end-to-end interval = 25+s1-s0+d1-d0. Computed minimum idle gap 9 s, end-to-end range 17–33 s; expanding both endpoints by the existing clock bound of 5 s gives worst-case operational bracket width 43 s. This is an arithmetic bound on record timing for compliant consecutive windows, not an onset error estimate, not guaranteed biological visibility onset. 216 slots x 24 = 5184 max checks, 36 min nominal directed dwell per 90-min sequence, 40 observer-hours for nominal 10-min adaptation plus max duration (additional adaptation/coordination not included). Reproduction (integer grid, no observations):

```python
from itertools import product
g=[(25+b-a-d,25+b-a+e-d) for a,b,d,e in product(range(-2,3),range(-2,3),range(8,13),range(8,13))]
assert len(g)==625
assert min(x[0] for x in g)==9
assert (min(x[1] for x in g),max(x[1] for x in g))==(17,33)
assert max(x[1] for x in g)+2*5==43
assert 90*60//25==216
assert 216*24==5184
```

## Next decisive gates

Before registration or enrollment: independently review cadence/dwell/first-positive-vs-window-end schema; perform no-sky procedural dry run with timer (no outcome data); decide if observer burden acceptable; freeze schema, analytical definition, selected non-protected cases, source versions, model SHA and sealed predictions independently. The current engineering RC 6ee0db2f6dcd1ef1c6a5291bb99b3d8a45c4dba6 is NOT approved scientific predictor. Exact approved scientific SHA and consent remain unset. No new accuracy evidence: 0 qualifying observed brackets, no computed residuals, conditional 2–10.5 degrees, unsupported (10.5,16], >16 OOD. No MYSTIC or protected holdout access.