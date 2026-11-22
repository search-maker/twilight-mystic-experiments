# P1 external source admission — Mary E. Byrd, Smith College, 1896 visual twilight (2026-11-22)

**Classification: RETROSPECTIVE HUMAN-VISUAL TIMING, EXPLORATORY ONLY; NOT A FIRST-STAR VALIDATION CASE.** No protected Taylor/Ann Arbor or Jerusalem cases were accessed. Neither model predictions nor tuning nor a MYSTIC run was performed. No scoring or preregistration is claimed.

## Original evidence and primary provenance

- Printed source: Mary E. Byrd, *A Laboratory Manual in Astronomy* (Ginn & Co., 1899), chapter V §120, **printed page 135**, observation 2. Public original book scan: https://upload.wikimedia.org/wikipedia/commons/0/06/A_laboratory_manual_in_astronomy_%28IA_laboratorymanual00byrdrich%29.pdf ; Google Books bibliographic locator https://books.google.com/books?id=RUwAAAAAYAAJ .
- Original contemporaneous observation **Friday 1896-10-09**, "Back Campus" at Smith College, Northampton, Massachusetts. Observer initials **A.E.T.** The observer recorded disappearance of the solar upper limb behind a hills/trees horizon at **17:07**, first described appearance of **sixth-magnitude stars in Ursa Minor at 18:32**, distinctly visible Milky Way at **18:34**, with better Milky Way appearance **12 minutes later**. Those are **observed clock readings**, not modern predictions. Exact star HIP identities, a continuous negative-to-positive sighting sequence, and individual optical pointing were NOT reported. Even the 18:32 claim is class/constellation-level, not a named single star.
- Same book, **Appendix E, printed p. 263**, supplies *period-specific* Northampton position **42°19.0′ N, longitude 4 h 50 m 33 s W**, corresponding to lat **42.316666667°**, lon **−72.637500°**. This is a town/observatory proxy, NOT surveyed position of Back Campus. This period-specific coordinate is superior for source custody to retrofitting a contemporary arbitrary town coordinate.
- Same book **§120 pp. 134–135** explicitly warns that artificial light, atmospheric state, eye state and local sunset obstructions alter twilight observations. **Chapter I §2 pp. 3–4** cautions against observer outcome knowledge and rejects discarding discordant observations solely on outcome. The 1896 July example on p.135 says the observer avoided learning the actual time within half an hour while watching twilight. This shows a historically documented anti-bias method, **not** that 1896-10-09 had any formally blinded protocol.
- **Time convention**: chapter V uses Eastern Standard Time generally, as indicated by the text in the opening of chapter VI p.137, but p.135 does not separately specify whether the 18:32 watch was EST or local mean time. Treat EST as a stated *analysis hypothesis*, not proven contemporaneous clock custody.
- Original scan page-image verification: **not completed**; the available web PDF screenshot endpoint rejected this 17,887,278-byte file. Extracted original-book text and page/appendix are directly readable. Full original PDF byte hash: **not acquired**. Do not claim visual facsimile or raw-byte SHA pass.

## Reproducible independent geometry (computed 2026-11-22, NON-model output)

Computational tool: PySwissEph/Swiss Ephemeris **2.10.03**, `swe.FLG_MOSEPH | swe.FLG_EQUATORIAL` and `swe.azalt(..., swe.EQU2HOR)`. Civil date Gregorian. Longitude positive east. Assumed observer elevation **70 m** (proxy, not measured), pressure 1013 hPa and temperature 10 °C; **TRUE** solar altitude is reported, not refracted star visibility. Delta-T and exact locality are not empirically established. These numbers are for **historical record interpretation only**, not the StarsVisibility model.

| Event / hypothesis | UTC | Derived true Sun altitude | Derived true Moon altitude | Derived Moon lit fraction |
|---|---|---:|---:|---:|
| reported horizon-blocked solar limb 17:07, EST hypothesis | 1896-10-09 22:07 | **+1.077°** | not computed | not computed |
| sixth-mag stars reported 18:32, **EST=UTC−05** hypothesis | 1896-10-09 23:32 | **−14.5917°** | **+1.3198°** | **0.1372** |
| same watch 18:32, *local mean time* alternative | 1896-10-09 23:22:33 | **−12.8459°** | **+2.6658°** | **0.1367** |
| Milky Way distinctly reported at 18:34, EST hypothesis | 1896-10-09 23:34 | **−14.961° approximate** | not computed | not computed |

The local mean time alternative follows the historical site longitude, east of the standard 75°W meridian by 2.3625°, or **9 min 27 s**. Local mean time 18:32 therefore corresponds to EST 18:22:33 and UTC 23:22:33. **Clock-convention impact: 1.7458° difference in derived solar depression.** The 17:07 hillside disappearance occurs while calculated Sun center is ~+1.08° above the mathematical horizon under EST, a plausible horizon obstruction; it is NOT an independently timed astronomical sunset.

Reproduction command, requiring `pip install pyswisseph==2.10.3.2` (library internal version 2.10.03); package-installation is not part of this evidence:
```python
import swisseph as swe
lat = 42 + 19/60
lon = -(4*3600 + 50*60 + 33) / 240
def sky_at(utc_hour):
    jd = swe.julday(1896, 10, 9, utc_hour)
    out = {}
    for name, body in (("sun", swe.SUN), ("moon", swe.MOON)):
        coords, flags = swe.calc_ut(jd, body, swe.FLG_MOSEPH|swe.FLG_EQUATORIAL)
        az, true_alt, apparent_alt = swe.azalt(jd, swe.EQU2HOR, (lon,lat,70),1013,10,coords[:3])
        out[name] = {"true_alt_deg": round(true_alt,5), "az_north_deg": round((az+180)%360,5)}
    out["moon_lit_fraction"] = round(swe.pheno_ut(jd,swe.MOON,swe.FLG_MOSEPH)[1],5)
    return out
print("EST hypothesis", sky_at(23+32/60))
print("LMT hypothesis", sky_at(23+22/60+33/3600))
```
Actual independent execution on 2026-11-22: EST solar −14.59167°, Moon +1.31978°, Moon lit 0.13720; local-mean solar −12.84585°, Moon +2.66576°. No model error statistics calculated.

## Admission/exclusion manifest

| Data requirement | Source evidence | P1 judgment |
|---|---|---|
| Human naked-eye visual detection | Yes, §120 timed appearance of sixth-mag Ursa Minor stars | **human detection confirmed at class level** |
| Named star + individual Johnson V magnitude | No; "sixth magnitude" is a class and not a catalog ID | **FAIL** |
| Earlier independently timed non-detection / first-detection bracket and repeat | No | **FAIL** |
| Actual observing site, observer, clock | Town/site descriptor and initials, but not measured Back Campus coordinate or clock calibration | **PARTIAL** |
| Solar geometry, individual stellar pointing | Solar geometry computationally reconstructable; no individual target ID/alt/az | **PARTIAL / FAIL target** |
| Clouds/haze, skyglow and matched AOD vertical profile | Explicitly not numerically recorded for this event | **FAIL** |
| Adaptation/observer method and independence | General book methodological caution, not event-specific protocol | **FAIL** |
| Protected independent prospective score | Historical published result already inspected | **EXCLUDE** |

**Verdict: NO-GO for independent first-visibility timing error, particularly NO new observational support for (10.5°,16°].** It is a genuine retrospective human-vision datum in that solar-depression interval *conditional on clock interpretation*, useful as an **exploratory field-design plausibility check** only. The class of sixth-magnitude stars, unknown exact sky direction, missing repeated absence/first-presence and unknown atmospheric conditions prohibit quantitative model admission.

**Next highest-value action:** authorized outreach owner/Coordinator must obtain explicit consent and exact site/time/pointing, and preregister 2 negative + first positive + confirming positive checks for *named* V-mag star with matched cloud/skyglow/AOD/adaptation; freeze model/source SHAs and acceptance limits before observation. Previously drafted 2026-11-19 outreach emails remained unsent at this check; do not presume replies/consent or send duplicative requests. No paid obligations. Existing scientific P1 freeze receipt remains a DRAFT.
