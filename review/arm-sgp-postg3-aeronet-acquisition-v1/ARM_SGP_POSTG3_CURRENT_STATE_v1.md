# ARM SGP post-G3 current state v1

Authoritative state through the result-blind post-G3 acquisition completed 2026-08-31.

- G0-V2: 29 still-blind primary candidates admitted by Issue #60 `5473411963`.
- G3: authoritative semantic re-audit Issue #60 `5480629113` leaves exactly 8 PASS / 21 FAIL / 0 unresolved.
- Exact eight: `2024-01-27_dusk`, `2024-02-01_dusk`, `2024-03-03_dusk`, `2024-03-04_dusk`, `2024-03-06_dusk`, `2024-03-27_dusk`, `2024-03-28_dusk`, `2024-05-31_dusk`.
- SASZE held-out radiance remains sealed. No MYSTIC result/residual, Taylor/Jerusalem value, or radiance agreement has been used for case selection.
- Public AERONET V3 result-blind acquisition completed SUCCESS: workflow run `33412493664`, artifact `9765688951`, digest `sha256:681adec27c7d1428b247e74e22dec596f9cff1e59fb0fdfa90c1fdbf0286b61f`.
- AERONET direct-sun Level-2 AOD contributes partial G6 evidence but cannot alone satisfy the frozen cross-source AOD gate.
- Seven exact-eight cases have a preceding AERONET AOD sample within ~5.7 hours or less; `2024-03-06_dusk` has no AERONET AOD sample in the preceding six hours (last preceding sample ~25.63 h earlier).
- None of the exact eight has finite Level-2 ALM/HYB SSA440 + real refractive index support within +/-24 h of the -6 anchor. This leaves AERONET primary microphysics MISSING; it is not an automatic case failure under the frozen protocol.
- G2 cloud, G4 corrected HSRL 2.6.7 event profile, G5 Raman diagnostic, remaining G6 cross-source ARM AOD, G7 two-sided sonde, G8 surface constraint, G9 ozone/upper-atmosphere, and SASZE housekeeping remain MISSING/UNRESOLVED until exact candidate science extracts are available. Metadata coverage alone is not PASS evidence.
- No case is currently eligible for deterministic primary selection. `radiance_magnitudes_opened=false`; `mystic_result_opened=false`.

Smallest exact missing-data handoff is frozen in `ARM_SGP_POSTG3_EXACT8_MINIMAL_DATA_REQUEST_v1.md`; it requests only the exact-eight event science/QC/provenance needed for post-G3 gates, not the ~65 GB archive and not held-out radiance.
