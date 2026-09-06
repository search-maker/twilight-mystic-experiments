# ARM SGP holdout firewall note v1

Status: **pre-MYSTIC, fail-closed scientific-integrity rule**.

## General rule

A candidate cannot serve as a primary held-out SASZE validation case if calibrated SASZE radiance **magnitudes** for that candidate are surfaced to the validation worker before the exact case set, atmosphere reconstruction, numerical settings, wavelengths and comparison metrics are frozen.

Such a case is retained in the complete candidate ledger with
`holdout_blindness_status=EXPOSED_DEVELOPMENT_ONLY` and may be used only after the independent primary validation as a labelled secondary/development diagnostic. It must not be deleted from the archive or silently omitted from the ledger.

Timing, file identity/SHA-256, wavelength coordinates, fill/validity counts, integration modes, housekeeping, QC, product semantics and native timestamp continuity are not radiance-magnitude outcomes and remain admissible for residual-blind Stage-A screening.

## Current application

During dependency discovery on 2026-08-30, File-Library search surfaced a local-derived `sasze_20240209_representative_spectra.json` snippet before primary case preregistration. That file corresponds to `2024-02-08_dusk` / UTC 2024-02-09. The worker did not intentionally open the spectrum or use the displayed magnitudes for any fit, ranking, threshold or atmosphere choice, but the magnitude firewall is no longer pristine for that event.

Therefore freeze now, before any MYSTIC comparison:

- `2024-02-08_dusk`: `holdout_blindness_status=EXPOSED_DEVELOPMENT_ONLY`;
- it is **ineligible for primary held-out case selection**, even if all independent atmosphere/QC gates later pass;
- its timing/validity/product-semantics evidence may still be used to correct generic extractor semantics because those corrections do not depend on radiance agreement;
- its radiance remains forbidden as a tuning target and may only be opened deliberately after the primary held-out validation protocol has been executed on still-blind cases.

This exclusion is a holdout-integrity safeguard, not a statement that the event or instrument is scientifically bad.
