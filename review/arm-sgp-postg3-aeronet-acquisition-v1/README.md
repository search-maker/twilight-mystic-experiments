# ARM SGP post-G3 AERONET evidence package v1

Result-blind support package for the exact eight candidates surviving authoritative ARM G3. No SASZE radiance magnitude, MYSTIC result/residual, Taylor/Jerusalem value, or case-ranking outcome is opened by this package.

Contents:

- `arm_sgp_postg3_exact8_evidence_ledger_v1.csv` — current hard-gate ledger. G0/G3 are bound PASS; unacquired science gates remain explicitly MISSING; no case is selected.
- `arm_sgp_postg3_aeronet_exact8_summary_v1.csv` — exact-event public AERONET V3 Level-2 direct-sun AOD support and ALM/HYB Level-2 inversion-availability diagnostics.
- `arm_sgp_postg3_aeronet_manifest_v1.json` — immutable acquisition/run/artifact/raw-file provenance and SHA-256 identities.
- `ARM_SGP_POSTG3_EXACT8_MINIMAL_DATA_REQUEST_v1.md` — smallest remaining ARM science extraction needed to classify G2/G4/G5/G6/G7/G8/G9 + SASZE housekeeping without opening radiance.

Public AERONET acquisition identity: workflow run `33412493664`, attempt 1, artifact `9765688951`, digest `sha256:681adec27c7d1428b247e74e22dec596f9cff1e59fb0fdfa90c1fdbf0286b61f`.

Interpretation boundary: AERONET contributes independent spectral-column evidence to G6 but does not alone satisfy the frozen cross-source AOD gate. None of the exact eight has finite Level-2 ALM/HYB SSA440 + real-refractive-index support within +/-24 h of the -6 anchor. That is **not** an automatic case failure under the frozen protocol; it leaves AERONET primary microphysics MISSING and retains the typical-AOD/profile-closure path unless another qualifying source is admitted.

Current terminal state: **not selected / not preregistered / radiance sealed / MYSTIC not run**.
