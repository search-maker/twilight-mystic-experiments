# Science Validation — NEW first-party visual source and UTC clock-admission guard (2026-11-22)

**Classification:** firsthand retrospectively posted *human visual detection notices*, NOT a prospectively blinded first-NOT_SEEN to first-CONFIRMED-YES validation set. These observations were already public before this review and are explicitly excluded from a result-blind holdout.

## Original evidence and custody

- Observer-authored public log: [ScienceDownEast, General Session — July 26/27, 2017](https://sciencedowneast.com/joomla/index.php/observations/all-observations/general-session-july-26-27-2017), dated 2017-07-26/27, page metadata Created **2017-07-26**, Last Updated **2022-06-20**.
- Log labels its location **SCO**; independently identified as the [Halifax RASC St. Croix Observatory](https://halifax.rasc.ca/index.php/observing/14-st-croix-observatory), an observing site near St. Croix, Nova Scotia. This does **not** establish the observer's surveyed location, height or skyline.
- The session header (original page lines 58–66) gives **Visual + 10x30 binoculars**, transparency **Excellent (5)**, seeing **Excellent (5)**, temperature **10 C**, *no wind or cloud*. These are observer descriptions, not calibrated aerosol/cloud/radiance measurements.
- The **Scorpius subsection** (original page lines 80–88) individually labels **Instrument: Visual** and admits the observer noted when stars became visible **or when they were noticed**. Unlike the Lyra subsection, it is expressly visual. No statement establishes repeated prior negative tests.
- The **Lyra subsection** (lines 73–79) is **Visual + Binoculars** and therefore the 21:38 Vega notice and epsilon/zeta co-notices **cannot be promoted to individually verified naked-eye** from the source alone.
- The same post labels a later 00:25–00:45 segment **EDT** (lines 157–159), although July civil time at this Nova Scotia site is **ADT**. This is an unresolved provenance anomaly, **not proof that early times were EDT**.
- The public edited HTML page is not the raw observation notebook. Exact event UTC/source-file bytes, pre-detection checks, data-use consent and contemporaneous metrology are not in custody. Raw-site/source SHA: **NULL**.

## Direct event extraction, no inferred prior absence

| Source wall time July 26, 2017 | Reported named object(s) | Modality stated for section | First-NO check | Repeated confirmed YES |
|:--|:--|:--|:--|:--|
| 21:38 | Vega (and epsilon/zeta Lyrae) | **MIXED visual + binocular** | absent | absent |
| 21:40 | Antares / alpha Scorpii | **VISUAL** | absent | absent |
| 21:48 | nu Scorpii; Graffias / beta Scorpii | **VISUAL** | absent | absent |
| 21:54 | pi Scorpii; rho Scorpii | **VISUAL** | absent | absent |
| 22:12 | Scorpius stars **below Antares**, not individually identified | **VISUAL**; trees obstruct low southern horizon | absent; horizon censoring present | absent |

Thus **five individually named positive visual notices** over **three timestamps** in the Scorpius section, on **one** site-night observational cluster, plus one explicitly mixed-modality Lyra timestamp. Those counts are **not** 5 independent first-visibility validation events. The 22:12 stars cannot be retrospectively assigned theta/eta or a measured magnitude.

## Reproducible bounded solar-geometry *scenarios*, not verified observer geometry

Runnable source: [`scorpius_2017_solar_clock_scenarios.py`](scorpius_2017_solar_clock_scenarios.py), requires `pyswisseph` and IANA `zoneinfo`. Executed **2026-11-22** with Swiss Ephemeris 2.10.03, 5 source wall times × 2 clocks; all finite/time assertions passed. Computes **unrefracted solar-center geometric depression** in degrees; not target alt/az and not human sighting thresholds.

**Location for computation ONLY:** publicly indexed *St. Croix community centroid* **44.96194 N, -64.03379 E**, as listed by [Mapcarta](https://mapcarta.com/24657216), **NOT** a measured observatory or observer position. Assumed zero observer elevation for this scenario; not a field measurement.

| Named/description | Source local clock | If ADT (UTC-3) solar depression | If EDT (UTC-4) solar depression |
|:--|:--|--:|--:|
| Vega (mixed) | 21:38 | 8.0246° | 15.7068° |
| Antares (visual) | 21:40 | 8.3044° | 15.9345° |
| nu, beta Scorpii (visual) | 21:48 | 9.4087° | 16.8247° |
| pi, rho Scorpii (visual) | 21:54 | 10.2209° | 17.4702° |
| Unnamed below-Antares/horizon group (visual) | 22:12 | 12.5698° | 19.2860° |

**Clock delta for Antares:** **7.6301°** in inferred solar depression (two mutually exclusive timestamp interpretations), not a physical model error. *ADT is the expected civil zone*, but the source's **EDT** notation is not reconciled by a dated, observer-authoritative timezone/clock record. ADT place-side calculations indicate named visual notices in **2–10.5°** only; the unnamed, horizon-censored 22:12 notice occurs at **12.57°** under ADT but provides **no target identity/magnitude and no prior negatives**. EDT puts later named notices beyond the 16° v1 domain, illustrating the importance of the offset check, **not evidence for that range**.

## Admission decision / no-blind-promotion

- **PASS:** authentic observer-authored first-party publicly posted visual *notices* with time order and one explicit naked-eye modality section; source separately logs no cloud and some tree-line obstruction. Source page preserved by stable URL, not cryptographically raw.
- **FAIL:** true first-detection brackets (`last_NOT_SEEN_UTC < first_CONFIRMED_YES_UTC`) = **0**. Individual exact HIP/HD/HR/Johnson V magnitudes **not admitted**, observer direction/altitude/azimuth **missing**, precise site/timing/timezone **unverified**, measured aerosol/skyglow/adaptation **missing**, no blind predictor SHA and no legal data-use/volunteer consent. No all-sky radiance or zenith SG_088 substitution is permitted.
- **Validation outputs:** new qualified event count **0**, residual/MAE/bias/coverage **NULL**, `sun_depression_(10.5,16]_human_first_visibility=UNSUPPORTED/null`; 2–10.5 conditional numerical support is **not** minute-accurate, >16 out of v1 domain. No Taylor/Ann Arbor/Jerusalem protected holdout, MYSTIC solver, spent ordinal67 or forbidden ordinal68 used.

## Finite next handoff

Coordinator or the **pre-existing authorized Outreach Replies owner only**, when legitimately enabled, can request **the observer's original per-target negative/positive notebooks**, contemporaneous timestamp and time-zone settings (resolve embedded EDT notation), exact lawful observing point/horizon, per-target visual-vs-binocular status, magnitude/pointing, and contemporaneous weather/adaptation/skyglow/AOD. This observer is associated with the same Halifax-area organization as the **existing unsent Halifax scientific enquiry**: check full authorized correspondence and draft first; **do not send a second duplicate message or claim consent/permit**, and do not access private raw notes until use terms and the independent test plan are frozen. Coordinator owns the single preregistration, frozen runnable predictor SHA, protected excluded cases, predictions hidden from enrolled observers, clustered-error thresholds, budget and stopping rules *before prospective outcomes*.
