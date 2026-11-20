# 2026-11-20 pre-outcome: inter-observer cue leakage in first-star observations — source audit + blank custody amendment candidate

**Status: INDEPENDENT PROTOCOL-SAFETY PROPOSAL / NOT APPROVED / NO ENROLLMENT / NO DATA / NO PREDICTIONS.** Science-only source review; no claim of a new or executed scientific study. This does **not** supersede V0 or the conflicting SCO R1 operational card. Coordinator/registrar must prospectively select and freeze one protocol and its data schema before outcomes. Protected Taylor/Ann Arbor and Jerusalem holdouts are excluded.

## New original-host source, bounded admission

Original researcher-authored educational method: Akihiko Tomita, **"Evening Sky watching for students"**, IAU-endorsed astroEDU educational activity 1616 (created **2016-11-09**), DOI **10.14586/astroedu/1616**, original hosted page https://astroedu.iau.org/activities/evening-sky-watching-for-students/ . Checked publisher's own HTML **Activity 2.1/2.2**, not a secondary summary. In this **teaching activity** the first participant calls attention to a star, a teacher asks where, and other participants receive directional clues (landmarks/hand pointing) and sometimes explicitly disagree about the "first" star. Its aim is education and sharing orientation, **not masked independent scientific threshold estimation**.

**Admit** the author's actual documented procedure as a concrete external demonstration of how a socially shared first-star task deliberately transfers target location/detection information between viewers. **Do NOT admit** it as source data for model accuracy, any first-NO/YES event, effect size, observer acuity distribution, or claim that volunteers necessarily communicate. Raw original HTML byte SHA: **NOT ACQUIRED** (original-host visual/textual page checked). The activity is not a source of individual original time-stamped records. This exact methodological caveat was not in the previous V0/R1 collision note.

## Newly isolated scientifically material R1 gap

The existing [SCO R1 blank field pack](https://github.com/search-maker/twilight-mystic-experiments/blob/2983306b9634278b0f3f66f9d5da52e62fb688ba/review/first-visibility-pilot-20261109/SCO_Observer_FieldPack_R1_BLANK_20261119.md) anticipates **3 observers** and says each observer follows a named target with an independent timekeeper, but does not specify what happens if observer #1 calls out "I see it" or points to the source while observers #2 and #3 are still searching. This is *not* a generic statistical cluster issue: a pre-confirmation cue can change target localization, directed-versus-undirected search, and the actual first positive interval. Merely using separate observer tokens does not remove information leakage. A site/night cluster adjustment also cannot retrospectively recover an independently blinded visual detection.

**Pre-outcome candidate rule to be adopted or rejected explicitly by Coordinator:** Until the last predeclared star check has closed, each observer must submit their own status to an isolated recorder/timekeeper without a shared audible declaration or visible gestures. Issue identical neutral clock prompts to all observers; the operator may show the same preselected non-predictive chart to everyone BEFORE searching, but not model onset times, solar-depression predictions, which participant has succeeded, or other participants' evolving detection status. Provide separation appropriate to the site, without new light, dangerous walking, or privacy-intrusive audio. If isolation cannot be provided, do **not** silently treat same-site first-sighting timings as masked independent outcomes. Independent observers may retain independent trial labels only if no exposure to another observer's target-specific status/cue before their own confirmation.

**Blank, initially zero-row source-record extension (proposal only):**

| Field | Requirement |
|---|---|
| `record_type` | `CUE_EXPOSURE` (separate from CHECK/CONDITION; one row per exposure or observed absence documented by independent custodian) |
| `protocol_id` / `source_schema_sha256` | Prospective single chosen protocol and frozen source hash; **UNSET**, not made up |
| `session_token`, `observer_token`, `target_HIP` | Opaque private-linked identifiers; no names or public location |
| `timestamp_utc`, `clock_bound_s`, `original_record_sha256` | Original independently time-stamped audio/page/electronic record, byte hash and clock uncertainty; never backfill missing event |
| `cue_status` | `NONE_OBSERVED`, `AUDIBLE_STAR_FOUND`, `POINTING_OR_LOCATION_HINT`, `DISPLAYED_PREDICTION`, `OTHER`, `UNKNOWN` |
| `source_observer_token` | Opaque token or `UNKNOWN`; no personal details |
| `target_exposure` | `THIS_TARGET`, `OTHER_TARGET`, `UNKNOWN` |
| `affected_check_range` | First and last actual CHECK tokens exposed, never a fabricated interval |
| `original_private_ref` | restricted URI + original byte SHA, no publicly published voice/participant identity |

Keep raw `NOT_SEEN`, `POSSIBLE`, `CONFIRMED`, `OBSCURED` and `NOT_CHECKED` events even when contaminated. If a target-specific cue or prediction leak precedes an observer's first independently corroborated `CONFIRMED`, **classify that observer-target-night as CUE_EXPOSED / NOT_ADMITTED_TO_INDEPENDENT_BLINDED_SCORE**, without deleting checks. An unaided yes *after a hint* can be descriptively retained as a *cued search*, not used as an independent threshold. Unknown exposure must be reported as **UNKNOWN**, not silently assumed absent; its treatment must be frozen before observations. These are proposed decision rules, not completed locks.

## Outcome-blind custody gates and compact existing budget

- **Coordinator / registrar:** select exactly one V0 versus R1/new-prospective amendment; freeze protocol ID, admission, cue-exposure rules and blank event schema Git source/sha before volunteers receive instructions. Existing V0 has <=120 s / <=5 s, R1 has <=150 s / <=10 s, so neither is "already approved" as a unified protocol.
- **Authorized Outreach Replies owner:** independently inspect the **existing** unsent Halifax Judy Black and Belokrylov author drafts / threads, contact only under existing authority, seek adult volunteer expression of interest and site/key-holder permission, then obtain individual affirmative consent privately; no duplicate/fabricated email or promises. Consent from an institution is not consent from the individual.
- **Predictor custodian A:** only after valid model qualification freeze actual runnable 40-hex model commit, input SHA256s (HIP/magnitude, ephemeris, site/horizon, condition source QC), sealed null/UNSUPPORTED outputs, and private salted SHA256 prediction commitment **before the first outcome**; observer B sees only preselected sky chart; independent raw custodian C hashes first-NO/YES and cue logs before unsealing.
- **R1 candidate cap, unchanged:** max 3 observers × 3 weekday nights × 2 stars = 18 observer-star cases; max 5 site attempts OR 8 weeks; no payments. Do not convert an unsupported physical prediction into a time or claim that six late-band onsets are guaranteed. Original moon/cloud/clock/adaptation/atmosphere/pointing must be present or explicitly UNKNOWN. A 90° zenith optical SQM/SG_088 cannot be presented as the human or <=80° directional signal.
- **STOP** for Shabbat/Yom Tov blackout, site/safety concern or finite R1 cap. No MYSTIC run or identity dispatch (ordinal67 spent; ordinal68 frozen), no protected Taylor/Jerusalem access or fitting.

## Current result and precise handoff

Original astroEDU procedure **SOURCE VERIFIED; HUMAN FIRST-SIGHTING BENCHMARK ADMISSION FAIL** (zero new target-specific last-NO/first-YES records). *New operational defect:* same-site participant visibility/location signaling lacks a prospective exclusion/recording rule, so "three observers" is not automatically three independent masked measurements. **Coordinator to explicitly accept/reject this additive blank custody amendment as part of a SINGLE prospective registered schema before enrollment**; keep actual personal documents and exposure records private. Outreach owner next authenticates and acts on the already pending relevant correspondences. No current verified adult consent, approved site, scientifically accepted model SHA, prediction seal, pilot outcome or predictive error; (10.5°,16°] remains unsupported/null, [2°,10.5°] conditional only, >16° outside v1.

**No code/model edit, model rerun, MYSTIC dispatch, contact send, or new sample acquisition is claimed.**
