# ARM SGP post-G3 exact-eight collector firewall review v1

Status: `RESULT_BLIND_FIREWALL_CORRECTION`; no SASZE radiance magnitude/protected photometric value was opened or used.

## Source reviewed

Persistent-Library file `Collect_ARM_PostG3_Exact8_Native.ps1`, Library id `file_00000000753c81f59fe88206028dd840`, created 2026-08-31T19:27:13Z.

The script correctly encodes the eight authoritative G3 survivors and intends a non-radiance Stage-A handoff. However, its `SASZE_HK/FILTERBANDS_HK` collection pattern copies the entire native `sgpsaszefilterbandsC1.a1` source file into `raw/` while describing it as housekeeping/QC only. The existing ARM extraction contract documents that `sgpsaszefilterbandsC1.a1` contains fixed `zenith_radiance_*nm` variables. Under the current strict holdout firewall, copying that whole source makes the package radiance-bearing even if no radiance value is printed or inspected during collection.

Classification of the Library PowerShell collector: `DO_NOT_USE_FOR_HOLDOUT_SAFE_HANDOFF__RAW_FILTERBANDS_RADIANCE_BYTES_INCLUDED_BY_DESIGN`.

This is a transport/firewall defect, not a scientific candidate PASS/FAIL and not evidence against any of the eight cases. No generated package from this collector was found in the persistent Library during the review.

## Corrected collector

Corrected result-blind collector:

`review/arm-sgp-postg3-aeronet-acquisition-v1/collect_arm_postg3_exact8_nonradiance_v2.py`

First correction commit: `9fd2657336472db716f1c9c1b674294448cb7cf6`; source blob at that commit: `bf58d6d192ce2f64aebc9c1a254ed70726061294`.

Correction semantics:

- non-SASZE G2/G4-G9 source files may be copied byte-for-byte with hashes;
- raw `sgpsaszevis*`, `sgpsaszenir*`, and `sgpsaszefilterbands*` sources are never copied into the handoff;
- SASZE files are opened only for native time coordinates and a strict non-photometric housekeeping/QC/calibration allow-list;
- variable names containing protected photometric tokens (`radiance`, `irradiance`, `flux`, `luminance`, `brightness`, detector signal/count tokens) are rejected before variable data access;
- the collector derives only non-photometric JSON plus native-time continuity summaries for SASZE;
- HSRL `code_version` is recorded, but collection alone never promotes a scientific G4 PASS;
- the collector emits no scientific case selection or held-out comparison result.

## Next exact action

Run only the corrected v2 collector against the preserved ARM source tree with the existing vendored `numpy/netCDF4` environment, and return its generated `ARM_SGP_POSTG3_EXACT8_NATIVE_NONRADIANCE_V2_*.zip`. Then ingest that compact package and execute the frozen G2/G4-G9/SASZE-housekeeping gates. Do not use a v1 PowerShell-generated package for protected Stage-A selection, and do not upload/open SASZE VIS/NIR radiance before final preregistration and Stage-B authorization.
