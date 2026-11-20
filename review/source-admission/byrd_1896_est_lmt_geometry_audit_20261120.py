#!/usr/bin/env python3
"""Reproducible historical CLOCK-BASIS sensitivity, not first-star validation.
Only uses a published 1896 observation from an already-public 1899 source.
The location is a modern approximate Smith College campus CENTER, not an
established 1896 observer position. No protected holdouts or model outcomes.
Requires: pyswisseph 2.10.03 (Moshier mode).
"""
import json
from datetime import datetime, timezone, timedelta
import swisseph as swe

SITE = {"latitude_deg": 42.31750, "longitude_deg": -72.63750, "role": "modern campus-center proxy"}
CLOCK = "1896-10-09 18:32:00"
EST_UTC = datetime(1896, 10, 9, 23, 32, 0, tzinfo=timezone.utc)
# Local mean clock at longitude lambda is lambda/15h relative to UTC;
# eastern standard clock is -75deg / 15 = -5h relative to UTC.
LMT_AHEAD_OF_EST_SECONDS = (SITE["longitude_deg"] + 75.0) * 240.0
LMT_UTC = EST_UTC - timedelta(seconds=LMT_AHEAD_OF_EST_SECONDS)

def true_solar_depression(t):
    decimal_hour = t.hour + t.minute / 60.0 + (t.second + t.microsecond / 1e6) / 3600.0
    jd_ut = swe.julday(t.year, t.month, t.day, decimal_hour)
    equatorial, flags = swe.calc_ut(jd_ut, swe.SUN, swe.FLG_EQUATORIAL | swe.FLG_MOSEPH)
    azimuth, true_altitude, apparent_altitude = swe.azalt(
        jd_ut, swe.EQU2HOR, (SITE["longitude_deg"], SITE["latitude_deg"], 0),
        0, 0, equatorial[:3]
    )
    return -true_altitude

est_depression = true_solar_depression(EST_UTC)
lmt_depression = true_solar_depression(LMT_UTC)
assert abs(est_depression - 14.591608) < 0.001  # independently reruns prior source audit
assert est_depression > lmt_depression
out = {
    "source": "Mary E. Byrd, A Laboratory Manual in Astronomy (1899), pp. 135, 137",
    "scientific_class": "PUBLIC_HISTORICAL_CLOCK_SENSITIVITY_ONLY",
    "watch_reading_as_printed": CLOCK,
    "site": SITE,
    "time_basis_under_EST": EST_UTC.isoformat(),
    "time_basis_under_hypothetical_LMT": LMT_UTC.isoformat(),
    "hypothetical_local_mean_clock_ahead_EST_seconds": LMT_AHEAD_OF_EST_SECONDS,
    "true_solar_depression_under_EST_deg": round(est_depression, 6),
    "true_solar_depression_under_LMT_deg": round(lmt_depression, 6),
    "difference_deg": round(est_depression - lmt_depression, 6),
    "time_basis_status": "Author generally supports EST for prior chapters; event-level calibration unknown",
    "star_HIP_or_pointing": None,
    "last_not_seen": None,
    "matched_aerosol_source": None,
    "qualified_human_first_sighting_brackets": 0,
    "model_prediction_error_minutes": None,
    "validation_status_10p5_to_16": "UNSUPPORTED"
}
print(json.dumps(out, indent=2, sort_keys=True))
