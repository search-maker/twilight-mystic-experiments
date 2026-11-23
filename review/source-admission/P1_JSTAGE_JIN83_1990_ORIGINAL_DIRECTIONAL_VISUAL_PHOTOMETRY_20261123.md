# P1 original empirical source audit — JIN 83 (1990), p.65–70
Date of audit: **2026-11-23 (America/New_York), permitted Monday / 13 Kislev 5787**. Role: **Twilight Scientific Validation**. **Exploratory source admission only; NOT a blind first-onset validation case.**

## Original source and verification
Jiro Mochizuki, Takahiro Tsuji, Susumu Hashimoto, *An Experimental Study on the Extent of the Visible Horizon in the Duration of Twilight*, The Journal of Japan Institute of Navigation **83** (1990), pp.65–70, DOI **10.9749/jin.83.65**. Official publisher: https://www.jstage.jst.go.jp/article/jin/83/0/83_KJ00004841391/_article/-char/en ; official 6-page PDF: https://www.jstage.jst.go.jp/article/jin/83/0/83_KJ00004841391/_pdf/-char/en .

The publisher-hosted **page images were directly inspected**, especially printed p.66 Table 1 (session/site/weather/photometer/scanning method), p.67 Table 2 (measured directional sky and sea luminance, sunset-depression grid), p.69 Table 5 (named human-observed celestial objects and directional background luminance), and printed p.69–70 Figs.5–8 and narrative (approximate solar depressions). **Unlike the incomplete Ugolnikov 1996 accessible four pages, this original has the relevant printed numerical tables present.** Source PDF byte download / raw SHA-256 could not be acquired in this run; original raw instrument observations could not be located; these fail source-byte/raw-data custody and prevent archival admission as raw measurements.

## Original session and procedure (printed p.66, Table 1)
**1990-02-21**, training vessel **Seiun Maru**, position **36°16.2′ S, 178°09.2′ E** (ship location, not fixed survey), eye height **16 m**; ship-clock sunset **18:56** at azimuth **257°**; moon age **25.3 d**; clear-sky observing, SW wind force 2, air **21°C**, sea **22°C**, sea state smooth. **Ship clock time zone not verified**, so no UTC timestamps have been inferred. **TOPCON BM-8** luminance meter, published measuring range **0.01–12,000,000 cd m⁻²**, with sky scan elevation **10°, 30°, 50°, 70°, 90°** and relative bearing **0°, 45°, 90°, 135°, 180°**. Approximately **100 s** per complete directional scan; paper itself estimates ~**0.3°** change in solar altitude across a scan. Thus even the instrument grid is not temporally simultaneous.

## Paper's Table 5: matched human-object report and measured-session directional background
All numbers below are **direct transcriptions of printed Table 5, p.69**. The objects' angular elevations are source degrees and minutes, not hyphenated time ranges. The solar-center altitudes at the plotted recognition contours are **approximate**, taken from Figs.5–8 and p.69–70, **not individually timestamped first-visibility events**.

| Object | Kind | Altitude | Relative azimuth | Sky background (cd/m²) | Approx. Sun-center altitude |
|---|---|---:|---:|---:|---:|
| Jupiter | planet | 28°50.7′ | 240.8° | **141.0** | ~0° (Fig.5) |
| Sirius | star | 61°07.9′ | 202.6° | **48.0** | ~−2° (Fig.6) |
| Canopus | star | 69°30.6′ | 107.8° | **3.8** | ~−4° (Fig.7) |
| Achernar | star | 47°55.5′ | 35.3° | **2.4** | ~−6° (Fig.8) |
| Aldebaran | star | 36°17.9′ | 271.7° | **0.27** | ~−6° (Fig.8) |

This is notably **closer to sought human-ground-truth than naked-eye-star-only diaries**: a **named human-observed star and its directional background**, instrument source/method, solar depression geometry, site, conditions and observing date are reported in one original same-session study. But Table 5 values should be interpreted as **directional luminance associated via the measured map/contours**; the source does **not** establish a direct sensor reading in exactly the star's direction **at the exact second of first detection**. Cloud-free selection is claimed but no independent meteorological cloud amount, aerosol extinction/AOD profile, local artificial skyglow characterization or visual adaptation history is recorded. Magnitudes are not listed in Table 5. The full grid reaches approx. solar-center −11° but with instrument zeros near its reporting floor: **zero is NOT zero physical sky radiance**.

## Eligibility and preregistration verdict
- **Original identified celestial objects:** 5 (4 fixed stars, 1 planet).
- **Original source-reported directional luminances associated with objects:** 5.
- **Timestamped previous non-seeing → first naked-eye seeing pairs:** **0**.
- **Naked-eye first-onset validation cases qualified for blinded P1:** **0**.
- **Independent 10.5°–16° star-first-onset cases:** **0**.
- **New model error estimates:** **none**. No model run, predictor comparison, fitting, threshold change or runtime claim.
- **HOLDOUT:** This source was discovered/read **before** any sealed preregistration of its outcome; it can be documented for exploratory optical range/sanity work but **never rebranded as independent blinded performance confirmation**.
- **Next targeted acquisition:** locate instrument raw scanned time/azimuth pairs, dated observing notebook (individual attempted non-detections / onsets, magnitudes and adaptation), clock definition, and weather/aerosol metadata if actually archived. Without them, preserve ineligible status and use prospective volunteers with sealed inputs+predictions.

**Controls:** verified live America/New_York time and Brooklyn diaspora calendar *before project actions*; re-read #152 and binding #60. This evidence-only branch is **not** a MYSTIC dispatch or solver identity. No ordinal67/68, protected Taylor/Jerusalem data, blocked source writes, outreach bypass, extra paid action, branch merge or deployment. Scientific model SHA remains **not frozen/approved for P1**, so there is no prospective prediction release. Coordinator owns further integration.
