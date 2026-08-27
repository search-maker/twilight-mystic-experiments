# Jerusalem Tammuz direct-MYSTIC exact-event proposal v1

Status: **proposal only — no scientific execution authorized**.

This package preregisters a direct libRadtran/MYSTIC diagnostic at the binding Jerusalem Three-Star equilibrium event for 1 Tammuz 5786 / 2026-06-16.

## Frozen event

- Site: 31.778 N, 35.235 E
- Observer elevation: 800 m
- Time zone: Asia/Jerusalem
- Application: `search-maker/starsvisibility` at `e2d5b761206b6223526f6f79fcb0af5f6de3ba06`
- Sunset: `1781628380546`
- Three-Star event: `1781629701483.5`
- 22.015625 minutes after sunset
- Sun depression: 4.8882245305886585 deg
- CAMS AOD550: 0.18
- F baseline: 3.14, unchanged
- Effective-magnitude threshold: 1.7
- Required stars: 3
- Stability: 60 s

The determining rows are the **live date-transformed Level-B catalog rows**, not a reconstruction from the raw 9,090-row built-in catalog:

1. Alkaid — HR 5191
2. Alioth — HR 4905
3. Regulus — HR 3982 — completing star

Binding source evidence:

- workflow run `33025015603`
- workflow head `a6cd5a3edab83f4c1e11164be37acd9d53baf533`
- artifact `9628151845`
- digest `sha256:42ed5920f88428c768bc25f7203de7ea48173fe541f857f9fedcc42efaec1008`

`level-b-event-evidence.json` freezes event samples plus +30 s and +60 s Level-B samples. Only the event geometries are proposed for direct MYSTIC; the later samples document the original 60-second stability semantics and are not extra MYSTIC cases.

## Proposed direct-MYSTIC batch

Exactly 12 cases are proposed:

- 3 frozen geometries
- per geometry: 2 `reference-vroom` replicates + 2 `alis` replicates
- 20,000,000 photon histories per case
- 240,000,000 total configured photon histories
- maximum parallelism 6
- 900 s per-case timeout

Frozen atmosphere/radiative-transfer inputs:

- AFGLUS
- AOD550 = 0.18, explicitly at 550 nm
- observer elevation 800 m
- surface albedo 0.15
- scalar MYSTIC
- `mc_spherical 1D`
- molecular absorption `crs`
- 380–780 nm domain
- ALIS spectral-importance wavelength 405 nm

The new Tammuz seed family is used only to avoid seed collisions with the completed Tishrei batch. It is not tuning.

## Analysis boundary

ALIS is the primary full-spectrum direct-MYSTIC source for photopic, scotopic, and Johnson-V channel derivation. Sparse reference-VROOM is an independent numerical-method cross-check only and must not be used to synthesize full photopic/scotopic/Johnson-V channels.

The sky-only human-threshold comparison must:

- keep each frozen Level-B apparent stellar V unchanged;
- replace only the photopic sky background by the mean direct-ALIS photopic result;
- use the exact frozen application human-threshold module;
- keep F = 3.14.

Matched-family stellar extinction, F sensitivity, and transient adaptation remain separate diagnostics and must not be folded into the sky-only comparison.

## Hard boundary

This package does **not** authorize MYSTIC or even `uvspec -c` syntax execution.

Before any scientific execution package is created, an exact-head no-solver proposal validation must pass. Any later execution must use a separate one-purpose authorization/guard path with exactly-once case semantics and no retry/resume/rerun.

No parameter tuning. No production authorization. No real-sky or human-first-seeing validation claim. Level-B has no full-spectrum runtime, so direct spectra cannot be described as full-spectrum Level-B validation. Pandora remains unopened.
