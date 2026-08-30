# ARM SGP independent real-atmosphere validation protocol v1

Status: **pre-result / residual-blind freeze**. No SASZE held-out radiance or MYSTIC comparison may be used to alter this protocol.

Objective: independent atmosphere -> frozen direct spherical MYSTIC -> held-out SASZE zenith spectral radiance at ARM SGP C1, with no fitting to Taylor/Jerusalem and no atmosphere/metric retuning from validation residuals.

## 1. Site and candidate universe

- Site: ARM Southern Great Plains C1, 36.607322 N, 97.487643 W, 314 m.
- Civil-date universe: 2023-12-14 through 2024-06-02 inclusive.
- For every local civil date enumerate both **dawn** and **dusk**.
- Solar geometry is the **topocentric geometric/unrefracted solar-center altitude**. Atmospheric refraction is zero/disabled. Do not use apparent upper-limb sunrise/sunset conventions.
- Root-solve exact UTC crossings for solar-center altitudes `-6`, `-7`, `-8`, and `-12` degrees. Store the ephemeris/library version, observer coordinates/elevation, time scale and root tolerance in the ledger.
- The primary closure core is the chronological interval spanning `-8..-6` degrees. `-12` is retained as an extended-depth availability/diagnostic point, not required to redefine the first primary target.

Every dawn/dusk event is retained in the complete ledger even when excluded. No event disappears merely because a required datastream is absent.

## 2. Required ledger fields

At minimum, one row per event:

`case_id,local_civil_date,event,t_minus6_utc,t_minus7_utc,t_minus8_utc,t_minus12_utc,sasze_vis_disposition,sasze_nir_disposition,sasze_filter_diagnostic_disposition,sasze_vis_continuity_margin_s,sasze_health_disposition,moon_max_alt_core_deg,moon_gate,arscl_disposition,ceil_or_mpl_disposition,cloud_consensus,hsrl_267_disposition,hsrl_valid_height_min_m,hsrl_valid_height_max_m,raman_disposition,hsrl_raman_common_support,aod_mfrsr_disposition,aod_nimfr_disposition,csphot_disposition,aeronet_aod_disposition,aeronet_l2_microphysics_disposition,aod_stability_disposition,aod_crosssource_disposition,sonde_disposition,surface_disposition,ozone_disposition,ompslp_disposition,evidence_stratum,profile_mode,primary_eligible,exclusion_reason,priority_order`

All source files and source SHA-256 values live in a separate normalized provenance table keyed by `case_id/source_role`.

## 3. Hard gates, in order

### G0 — held-out observable exists

Actual 2024 local file evidence resolves an important product distinction before any model comparison:

- `sgpsaszevisC1.a1` and `sgpsaszenirC1.a1` are the calibrated full spectral-radiance streams and retain usable per-pixel calibrated radiance into twilight, subject to their native fill/validity masks and integration modes.
- `sgpsaszefilterbandsC1.a1` is a daylight-derived filterband/transmittance product. Its time coordinate can continue into twilight even when every derived filterband radiance field is fill; in the inspected 2024-02-09 file the band-radiance product is populated only through apparent solar zenith 89 deg. Therefore filterband timestamp continuity is **not evidence that the held-out twilight spectrum exists**, and filterband fill in twilight is **not evidence that the full VIS/NIR spectrum is absent**.

Mandatory primary gate: `sgpsaszevisC1.a1` native timestamps must be `TWILIGHT_CONTIGUOUS` through the whole `-8..-6` core under the unchanged strict native-time rule: actual samples bracket both chronological endpoints and every positive gap in the bracketing segment is `<= 2 x` the stream's source-day median positive cadence. Global `time_coverage_*` attributes are not continuity evidence.

- NIR is audited independently as `SECONDARY_SPECTRAL_EXTENSION`; it is required only for later metrics that explicitly use NIR wavelengths. The currently frozen primary anchor wavelengths 415/500/615/673/870 nm are VIS.
- Filterbands are retained as `DAYLIGHT_DERIVED_DIAGNOSTIC` only; they never rescue or veto the primary held-out-observable gate.
- `SOURCE_FILE_MISSING` or `UNREADABLE` on VIS is a local-data blocker, not evidence of observational absence.
- If all events in the frozen priority set have **readable VIS** that is absent/discontinuous, the current target halts rather than moving shallower after the fact.
- This product-semantics correction does not relax the strict continuity threshold and does not promote any already-inspected case. A VIS event with a gap larger than the frozen threshold remains ineligible even if filterband timestamps are continuous.

### G1 — SASZE health is independently admissible

Retain actual VIS integration-time/scan mode, shutter state if present, tilt, temperatures and any native saturation/high-SZA/health flags. Multiple integration times are allowed by design and are not themselves a failure. Native per-pixel fill/validity masks are preserved as measurement-validity metadata; fill is never converted to zero. No saturation threshold or wavelength-validity rule is invented from MYSTIC agreement.

Before exact case selection, measurement completeness at the already-frozen primary anchor wavelengths may be assessed only from **valid/non-fill counts and timing**, not from radiance magnitudes. Full radiance values remain held out until Stage B.

### G2 — conservative clear-sky consensus

Use KAZRARSCL `.c1` when available, plus at least one independent laser cloud stream (CEIL or MPLCMASK), with HSRL/Raman feature/cloud masks as additional vetoes.

Any valid cloud/hydrometeor detection anywhere in the predeclared guard interval vetoes primary clear-sky admission. Missing a stream never counts as clear evidence.

Primary disposition required: `CLEAR_MULTI_SENSOR`.

### G3 — Moon

Primary solar-only tier: airless topocentric lunar-center elevation at SGP C1 must remain `<= -10.000 deg` through the entire `-8..-6` core. No refraction. The maximum lunar altitude over the core is the gating value.

Events failing only this rule may be retained as explicitly secondary lunar-sensitivity cases, never silently promoted to primary.

### G4 — event-time aerosol profile

Corrected HSRL `code_version=2.6.7` is the preferred event-time 532-nm aerosol anchor. Valid native timestamps, extinction/backscatter/depolarization support, QC/feature masks and valid vertical range are required.

Valid HSRL extinction/OD is `RETRIEVED`. Invalid/unsupported near-field or upper bins are `MISSING`, not zero aerosol.

### G5 — Raman independent profile diagnostic

RLPROFBE/RLPROF-FEX is compared with HSRL only on actual common valid height/time support and only with native QC. No full-column extrapolation is fabricated from the Raman product.

Consistency is judged only against documented/native uncertainty fields. If a defensible uncertainty is absent for the selected file, disposition is `UNRESOLVED_UNCERTAINTY`, not visual PASS.

### G6 — spectral AOD stability and cross-source consistency

Sources: MFRSR AOD, NIMFR AOD, CSPHOT/AERONET direct-sun AOD as available. Every direct-sun value is `RETRIEVED` at its actual daylight timestamp; carrying spectral shape to twilight is `INTERPOLATED`.

For each source use the nearest quality-valid daylight block on the same local civil date adjacent to the event (pre-dusk or post-dawn), without crossing a product-invalid solar-zenith-angle range. The block is fixed as the nearest **30 minutes of quality-valid observations**; require at least 5 valid samples at a wavelength to evaluate stability.

For each wavelength with a documented per-sample uncertainty `sigma`:

- robust spread gate: `1.4826 * MAD(tau) <= 2 * median(sigma)`;
- endpoint drift gate: `|median(first third) - median(last third)| <= 3 * sqrt(sigma_first^2 + sigma_last^2)`.

If the product supplies no defensible uncertainty field/formula, record stability as `UNRESOLVED_UNCERTAINTY`; do not invent a percentage after seeing results.

For two independently measured/retrieved sources at a common wavelength/time-support block, cross-source consistency requires

`|tau_A - tau_B| <= 3 * sqrt(sigma_A^2 + sigma_B^2)`.

MFRSR and NIMFR are independent instruments but share ARM AOD-VAP algorithm/calibration-family assumptions, so they are not treated as fully algorithmically independent. AERONET/CSPHOT provides the stronger algorithmic cross-check when available.

Event spectral AOD is reconstructed, when admissible, as

`tau_event(lambda) = tau_HSRL,event(532) * R_daylight(lambda;532)`

with HSRL anchoring event-time column burden and `R_daylight` supplying only independently stable spectral shape. The transferred spectrum is `INTERPOLATED`.

### G7 — thermodynamic state

Raw SONDE P/T/RH/wind is `MEASURED`. Event-time INTERPSONDE is `INTERPOLATED`. Primary admission requires two-sided valid sonde support through the model-relevant height range. MERGESONDE is not primary measured truth because it blends external model/reanalysis information.

Any upper-atmosphere completion above demonstrated sonde support is `ASSUMED` from a fixed standard-atmosphere extension and receives a pre-result sensitivity calculation.

### G8 — surface boundary

Raw MFR upwelling / MFRSR downwelling irradiances are `MEASURED`. QC-valid SURFSPECALB is `RETRIEVED` at daylight time. Carrying same-day stable spectral albedo to twilight is `INTERPOLATED`. Lambertian BRDF treatment is `ASSUMED`.

A precipitation/surface-state change between the daylight surface estimate and twilight makes primary spectral albedo `MISSING`. Do not substitute a fixed 0.15 primary albedo after residual opening.

### G9 — upper atmosphere

- surface O3 monitor: local near-surface ozone only; `MEASURED`, not a vertical ozone profile;
- OMPS ozone profile if used: native satellite retrieval `RETRIEVED`, event/site transfer `INTERPOLATED`;
- OMPS-LP stratospheric aerosol: native extinction profile `RETRIEVED`, event/site transfer `INTERPOLATED`, supplementing rather than replacing valid event-time HSRL.

If no quality-qualified upper-atmosphere profile satisfies the predeclared collocation rule, the missing layer remains `MISSING/ASSUMED` with a sensitivity envelope. It is not silently called measured atmosphere.

## 4. Evidence strata

After hard gates and before any held-out radiance is opened:

- `FULL_MICROPHYSICS_CLOSURE`: valid event profile/column plus quality-qualified contemporaneous AERONET Level-2 inversion support (SSA/RI/size/phase) whose temporal applicability is independently supported.
- `TYPICAL_AOD_PROFILE_CLOSURE`: valid event profile/column and spectral AOD constraints but no qualifying contemporaneous Level-2 microphysics. SSA/RI/phase remain `MISSING` for primary truth and may enter only a frozen physical sensitivity envelope.

Separately record profile mode:

- `EVENT_ANCHORED_SPECTRAL_PROFILE`: corrected HSRL event 532 profile + independently stable daylight spectral-ratio transfer + Raman/HSRL common-support diagnostic acceptable under supplied uncertainties.
- `EVENT_532_ONLY_PROFILE`: valid event HSRL 532 profile but spectral transfer/Raman gate unavailable, inconsistent or unresolved; other-wavelength vertical profile is `MISSING` for primary truth.

AERONET L2 microphysics availability is not a universal ranking bonus because L2 inversion availability is biased toward high-AOD conditions.

## 5. Deterministic selection of 1-3 primary cases

The complete universe is always retained. For the current frozen priority queue, preserve its pre-result `priority_order`; do not reorder it after reading SASZE/MYSTIC radiance.

From independently eligible survivors:

1. select the first surviving `FULL_MICROPHYSICS_CLOSURE` row in frozen priority order, if one exists;
2. select the first surviving `TYPICAL_AOD_PROFILE_CLOSURE` row in frozen priority order, if one exists;
3. fill at most one remaining slot with the next surviving row in frozen priority order;
4. if only one stratum exists, take the first up to three surviving rows in frozen priority order;
5. never replace a selected case because its held-out residual is inconvenient.

Prefer the primary solar-only Moon gate for the first closure case. A lunar-sensitivity case is never substituted for a solar-only survivor.

## 6. Required model-property provenance taxonomy

| Property | Primary source / role | Classification at event |
|---|---|---|
| SASZE zenith spectral radiance | SASZE VIS calibrated full spectrum; NIR only for preregistered secondary extension; held out until Stage B | `MEASURED` |
| SASZE wavelength grid / timing / housekeeping / validity masks | native SASZE VIS/NIR files | `MEASURED` metadata |
| SASZE filterband radiance/transmittance | daylight-derived product; diagnostic only in this twilight lane | `RETRIEVED/DERIVED`, not primary held-out gate |
| Aerosol extinction/backscatter/depolarization at 532 nm | corrected HSRL 2.6.7 | `RETRIEVED` |
| Raman aerosol optical properties | RLPROFBE/FEX | `RETRIEVED` |
| Direct-sun spectral AOD | MFRSR/NIMFR/CSPHOT/AERONET at daylight timestamp | `RETRIEVED` |
| Spectral AOD transferred to twilight | stable daylight spectral ratio anchored to event HSRL 532 | `INTERPOLATED` |
| AERONET SSA/RI/size/phase | quality-qualified L2 inversion | `RETRIEVED`; otherwise `MISSING` |
| P/T/RH/wind sounding | SONDE | `MEASURED` |
| Event P/T/RH between soundings | INTERPSONDE | `INTERPOLATED` |
| Above-sonde atmosphere | fixed standard-atmosphere extension if needed | `ASSUMED` |
| Cloud-free state | ARSCL + CEIL/MPL + lidar consensus | `MEASURED/RETRIEVED consensus` |
| Surface narrowband irradiance | MFR/MFRSR/QCRAD | `MEASURED` |
| Daylight spectral albedo | SURFSPECALB | `RETRIEVED` |
| Twilight surface albedo | same-day stable SURFSPECALB transfer | `INTERPOLATED` |
| BRDF/Lambertian behavior | no direct twilight BRDF measurement | `ASSUMED` |
| Surface ozone concentration | ARM OZONE | `MEASURED`, local only |
| Vertical ozone profile | independent satellite/profile source if qualified | `RETRIEVED` then `INTERPOLATED`; otherwise `MISSING/ASSUMED` |
| Stratospheric aerosol | OMPS-LP L2 if collocated/QC-qualified | `RETRIEVED` then `INTERPOLATED`; otherwise `MISSING` |
| Aerosol gap between valid HSRL and OMPS supports | no measurement unless supports overlap/bridge | `MISSING` or explicitly `INTERPOLATED` only under frozen bridge rule |

No `MISSING` item may be silently renamed `MEASURED` because a standard profile produces a good residual.

## 7. Stage-B opening boundary

Only after exact case IDs, complete input provenance, interpolation choices, sensitivity envelopes, MYSTIC geometry/numerical settings, photon budgets/seeds/stopping rule, wavelengths and comparison metrics are frozen may full selected-case SASZE radiance be opened.

The currently frozen primary anchors are 415, 500, 615, 673 and 870 nm, all taken from the VIS stream. For each selected crossing (`-8`, `-7`, `-6`), the previously frozen measurement-support window is +/-2.5 s around the geometric crossing and requires at least three independently valid native samples in that window. This per-epoch support rule is applied from timing/validity masks before radiance magnitudes are opened and does not replace the stricter full-core G0 continuity gate.

No scale factor, aerosol multiplier, wavelength correction, time shift, albedo adjustment, SSA/phase choice or case replacement is fit to the held-out residual.

The primary comparison metrics already frozen for Stage B remain absolute log-radiance residual, spectral-shape residual, -8 to -6 twilight-evolution residual and 415-870 color evolution, with the conservative SASZE absolute calibration scale uncertainty kept separate from scale-resistant evolution metrics.
