# 2026-11-22 — P1 independent original stellar-catalog SOURCE admission (pre-outcome; no event data)

**Status:** Verified original-catalog *metadata and parsing contract only*; **NOT DATA-BYTE-ADMITTED**, **NOT A PREREGISTRATION / APPROVAL**, and **NOT an unaided-eye first-sighting record**. This advances the still-missing HIP/Johnson-V source identity in P1 without opening observations or protected Taylor/Ann Arbor/Jerusalem cases.

## Primary source and independent corroboration

- ESA *The Hipparcos and Tycho Catalogues* (1997), CDS/VizieR **I/239**, original ReadMe catalog contract: https://cdsarc.cds.unistra.fr/viz-bin/ReadMe/I/239?format=html&tex=true
- NASA HEASARC catalog description independently attributes its derived table to CDS I/239 `hip_main.dat.gz`, with an April 2000 import and **October 2002 HEASARC-specific coordinate correction**: https://heasarc.gsfc.nasa.gov/w3browse/star-catalog/hipparcos.html (Provenance, parameter descriptions).
- NASA official dataset listing: https://data.nasa.gov/dataset/hipparcos-main-catalog
- CDS/I/239 is a *stellar photometry/astrometry catalog*, not measurements of human detection. A newer metadata timestamp in NASA's catalog is **not** proof of new stellar measurements or equivalence to original CDS bytes.

## Original field meanings verified from CDS indexed ReadMe and NASA explanation

| CDS field | CDS original fixed-width bytes (1-based) | Scientific meaning / admission caveat |
| --- | --- | --- |
| HIP | 9–14 | Stable Hipparcos ID, not informal star name. |
| Vmag (H5) | 42–46 | **Johnson V** apparent magnitude, may be blank. Not the same field or passband as Hpmag or Tycho VTmag. |
| VarFlag (H6) | 48 | Coarse Hipparcos variability: 1 means <0.06 mag; 2 means 0.06–0.6 mag; 3 means >0.6 mag; a blank is not proof of constant photometry. |
| r_Vmag (H7) | 50 | **G:** ground multicolour photometry in/reduced to Johnson UBV; **H:** conversion involving Hipparcos Hp and colour/luminosity; **T:** conversion from Tycho BT/VT. Missing code = no magnitude source. Preserve this flag. |
| RAdeg (H8) | 52–63 | ICRS coordinate, reference epoch **J1991.25**; not automatically valid as an unpropagated apparent alt/az in 2026. |
| DEdeg (H9) | 65–76 | Same reference frame/epoch; coordinate can be missing. |
| pmRA / pmDE (H12/H13) | 88–95 / 97–104 | Proper motions; date propagation is separate and must preserve definitions. |
| CombMag (H43), MultFlag (H59), Proxy (H2), Hpmag (H44) | see original ReadMe | Preserve multiple/combined-light and proximity flags for observer-target eligibility; never silently replace missing Johnson V with Hpmag. |

The NASA explanation states that **263 entries lack RAdeg/DEdeg** in its catalog due to missing astrometric solution. Therefore target selection must reject missing coordinate records, not invent pointings.

## Proposed P1 deterministic target-source gate (to be independently approved BEFORE site selection/outcomes)

1. Freeze and SHA256-hash the **exact original CDS file bytes**, the **ReadMe bytes**, table version and provenance receipt; distinguish any HEASARC-derived/mapped table from original CDS source. **No exact bytes were acquired in this check**: original SHA256s = `null` / `UNVERIFIED`. Do not fabricate checksums or number of eligible stars.
2. Parse Johnson `Vmag` with `r_Vmag` and `VarFlag`, preserve `CombMag`, `MultFlag`, `Proxy`, and missingness. Proposed easy-to-audit strata: prefer `G` with specified provenance, require separate documented uncertainty policy for converted `H/T`; flag high-variability / unresolved multiple entries for exclusion or independent reviewer determination. **These are candidate gates, not already-accepted P1 changes.**
3. Propagate ICRS J1991.25 astrometry to each prospective site/date using frozen ephemeris and proper-motion handling; independently freeze atmospheric, horizon, Moon, cloud, adaptation, time-source, and photometric passband inputs. **No observer site, target HIPs, predictions, predictions SHA, or selected non-protected cases have been fixed by this catalog audit.**
4. Require Coordinator + independent reviewer to lock the catalog bytes and documented selection/exclusion code, chosen sites/HIP/night grid, valid scientific predictor commit + runnable artifact SHA, source hashes, blind commitment, metrics and 12-evening/30-day/no-cost stopping criteria **before** any P1 field outcomes are seen. If the predictor cannot scientifically issue a time, precommit `UNSUPPORTED/null` instead of substituting a number.
5. No MYSTIC dispatch under this record (67 spent; 68 NEVER dispatch). No fitting, protected holdouts, paid work, participant recruitment, or altered model.

## Narrow outcome of this verification
**PASS: official source-schema identity and Johnson-V-vs-Hp/Tycho distinction confirmed.**
**BLOCKED: exact original catalog data/ReadMe bytes and hashes, site enrollment/consent, qualified model SHA and blind event data (zero) remain absent.**
**Prediction bias/uncertainty: NOT COMPUTED. (10.5,16]° visual first visibility: NOT VALIDATED.**
Next custodian action: acquire official CDS I/239 byte snapshot through a normal permitted source retrieval, record checksums; do not replace with the available unofficial mirror without an explicit provenance waiver; Coordinator to request P1-specific scientific reviewer approval and outreach-owner consent check.
