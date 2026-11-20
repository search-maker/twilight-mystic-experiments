"""Source-limited solar-center geometry, not a human first-star prediction.

Mary E. Byrd (1899), A Laboratory Manual in Astronomy, printed p.135,
Oct 9 1896 Back Campus Northampton, MA. The stars are UNNAMED sixth
magnitude Ursa Minor group, and no prior non-detection was recorded.
This is a retrospective published record. Model timing error is NULL.

Clock EST and modern campus location are explicit unverified assumptions.
"""
import json
from datetime import date
import swisseph as swe

LAT, LON = 42.31750, -72.63750

def sun_alt(hour, minute, latitude=LAT, longitude=LON):
    jd = swe.julday(1896, 10, 9, hour + minute / 60 + 5)
    eq, flags = swe.calc_ut(jd, swe.SUN, swe.FLG_MOSEPH | swe.FLG_EQUATORIAL)
    return swe.azalt(jd, swe.EQU2HOR, (longitude, latitude, 0.0),
                     0.0, 10.0, eq[:3])[1]  # geometric true altitude

def main():
    assert date(1896, 10, 9).weekday() == 4
    reported = {
       "17:07 reported sunset hidden by hills": sun_alt(17, 7),
       "18:32 group of sixth-mag stars noticed": sun_alt(18, 32),
       "18:34 Milky Way distinct": sun_alt(18, 34),
       "18:37 composite twilight endpoint": sun_alt(18, 37)
    }
    stress = [
        -sun_alt(18, 32 + minute_delta, LAT + dlat, LON + dlon)
        for minute_delta in (-10, 0, 10)
        for dlat in (-0.05, 0, 0.05)
        for dlon in (-0.05, 0, 0.05)
    ]
    depression = -reported["18:32 group of sixth-mag stars noticed"]
    assert 14.0 < depression < 15.0
    assert min(stress) < depression < max(stress)
    assert reported["17:07 reported sunset hidden by hills"] > 0
    print(json.dumps({
       "source": "Byrd 1899 original book, p135, Oct 9 1896",
       "site_assumed": [LAT, LON],
       "local_time_assumption": "EST UTC-5, unverified",
       "ephemeris": "Swiss Ephemeris Moshier " + str(swe.version),
       "true_sun_center_altitude_degrees": {
           k: round(v, 4) for k, v in reported.items()},
       "18_32_solar_depression_nominal_degrees": round(depression, 4),
       "stress_plusminus10min_plusminus0_05deg_site": [
            round(min(stress), 4), round(max(stress), 4)],
       "uncertainty_bounds_are_assumed_not_measured": True,
       "individual_star_identity": None,
       "first_nonseen_then_seen_bracket": None,
       "matched_cloud_aerosol_adaptation": None,
       "model_prediction_error_minutes": None,
       "validation_admission": "HISTORICAL_CONTEXT_ONLY"
    }, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
