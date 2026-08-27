# Exact Jerusalem event mesopic sensitivity v1 — result

Status: review-only sensitivity diagnostic; no production change.

Binding run: `33034940239`, attempt 1, SUCCESS.
Artifact: `9631656421`, digest `sha256:3f552f9179827f9a71127b3c067a3191756bdf73a1273f6018867983192c500b`.
Application SHA: `80110c8cb4575c7be3c91b4817be5126c40b2b15`.

Method: exact frozen Tishrei/Tammuz Jerusalem event geometry; four non-native matched OPAC aerosol families; same-family ASIV photopic/scotopic sky; current-catalog Pickles SED selection; matched-stellar-v2 wavelength-resolved direct transmission; CIE MES2 review-only transformation. F=3.14 was retained for scenario plumbing but cancels from the mesopic delta. No MYSTIC solver execution, no parameter fit, no retuning.

Overall delta visibility-margin range: `-0.0336268 .. +0.0140700 mag`.

## Exact completing stars

- Tishrei Gamma Cyg HR7796: `-0.0336268 .. -0.0305378 mag` across the four families. This makes the star slightly harder relative to the present photopic convention.
- Tammuz Regulus HR3982: `-0.0000041 .. +0.0005547 mag`, effectively zero.

Other exact stars:
- Tishrei Antares: `-0.0101596 .. 0.0000000 mag`.
- Tishrei Rasalhague: `-0.0080110 .. -0.0032660 mag`.
- Tammuz Alkaid: `+0.0081196 .. +0.0140700 mag`.
- Tammuz Alioth: `+0.0004877 .. +0.0042210 mag`.

Interpretation: the exact-event mesopic/color sensitivity is at most a few hundredths of a magnitude here and is essentially zero for the Tammuz completing star. It cannot account for a multi-minute early Jerusalem Three-Star event. It also does not establish CIE 191/MES2 as a validated foveal naked-eye star-detection model; human first-seeing validation remains required.

Claim boundaries remain: review-only; F unchanged; sky/stellar transport unchanged; no human-first-seeing validation; no production authorization; no Pandora opening.
