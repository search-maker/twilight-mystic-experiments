#!/usr/bin/env python3
"""Retrospective dual-clock sensitivity of one ORIGINAL observer log.
NOT a first-sighting validation; no prediction/tuning/protected cases.
Run: python3 echo_valley_2018_dual_clock.py
Requires pyswisseph==2.10.3.2 (uses built-in Moshier solar ephemeris).
"""
import datetime as dt
import json
import swisseph as swe

SITE = (-103.8946, 50.77533, 520.0)  # PARK reference, not observer's camp pad
ORIGINAL = "https://www.sciencedowneast.com/joomla4/index.php/observations/all-observations/general-session-july-11-2018"
OFFICIAL_PARK = "https://www.skparks-pl.castatic.reserveamerica.com/camping/echo-valley-provincial-park/r/facilityDetails.do?contractCode=SKPP&parkId=290180"
HEIGHT_REFERENCE = "https://mapcarta.com/24238624"  # approximate 521m
EVENTS = [
    ("21:35", "Venus", "unaided visual planet; non-star control"),
    ("21:50", "Antares", "noticed before binocular use; unaided onset unproved"),
    ("22:28", "Vega, Deneb, Altair", "explicit unaided visual positive; no negative look"),
    ("22:28", "Regulus", "first noticed; method unclear; no negative look"),
]

def solar_alt(utc):
    j = swe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute / 60)
    equ, flags = swe.calc_ut(j, swe.SUN, swe.FLG_EQUATORIAL | swe.FLG_MOSEPH)
    assert flags & swe.FLG_MOSEPH
    return swe.azalt(j, swe.EQU2HOR, SITE, 0.0, 10.0, equ[:3])[1]

def main():
    cases = []
    for printed, obj, method in EVENTS:
        hh, mm = map(int, printed.split(":"))
        for name, offset in (("header_MDT_UTCminus6", -6), ("literal_entry_CDT_UTCminus5", -5)):
            local = dt.datetime(2018, 7, 11, hh, mm,
                                tzinfo=dt.timezone(dt.timedelta(hours=offset)))
            utc = local.astimezone(dt.timezone.utc)
            alt = round(solar_alt(utc), 3)
            cases.append({
                "object": obj, "printed_clock": printed, "method": method,
                "clock_hypothesis": name, "utc": utc.isoformat().replace("+00:00", "Z"),
                "solar_true_alt_deg": alt,
                "solar_depression_deg_if_below_horizon": round(-alt, 3) if alt < 0 else None,
                "first_sighting_bracket_admitted": False
            })
    control = [x for x in cases if x["object"] == "Venus"]
    assert control[0]["solar_true_alt_deg"] < -4
    assert control[1]["solar_true_alt_deg"] > 3
    assert all(not x["first_sighting_bracket_admitted"] for x in cases)
    print(json.dumps({
        "status": "NEW_ORIGINAL_HUMAN_LOG_REVIEW_NO_FIRST_SIGHTING_GROUND_TRUTH",
        "original_url": ORIGINAL, "official_park_reference": OFFICIAL_PARK,
        "height_reference": HEIGHT_REFERENCE,
        "original_session_header": "9:30PM-11:30PM MDT",
        "individual_event_labels": "CDT",
        "legal_park_summer_offset": "UTC-6 (America/Regina/CST, equivalent MDT offset)",
        "site": {"longitude_deg": SITE[0], "latitude_deg": SITE[1],
                 "approx_elevation_m": SITE[2], "exact_pad_unknown": True},
        "ephemeris": {"pyswisseph_version": "2.10.3.2", "swiss_version": swe.version,
                      "engine": "Moshier", "notes": "approx horizontal Sun altitude from geocentric RA/Dec; uncorrected for local horizon/refraction"},
        "unresolved_clock_shift_seconds": 3600,
        "missing": ["same-target timestamped non-detections", "confirming direct detection",
                    "clock/offset source", "exact observation pad/directional horizon",
                    "coincident cloud, skyglow and aerosol", "adaptation"],
        "outcome": {"new_valid_brackets": 0, "prediction_error_seconds": None},
        "events": cases
    }, indent=2, ensure_ascii=True))

if __name__ == "__main__":
    main()
