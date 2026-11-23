#!/usr/bin/env python3
"""Reproduce solar geometry of ICOP 2008-09-28 MORNING LAST-star notices.

Original archived observation: https://astronomycenter.net/icop/shw29.html
Ma'rufin Sudibyo: Canopus not seen since 05:12; Sirius since 05:15,
both UTC+07 at 7d40m S, 109d40m E, 21m ASL. Optical aid is mentioned
for lunar observations; naked-eye modality for individual stars is not
unambiguously specified. Not evening FIRST visibility.
No StarsVisibility predictor or protected holdout is used.
"""
import json
from datetime import datetime, timedelta, timezone
import swisseph as swe

LOCAL_TZ = timezone(timedelta(hours=7))
SITE = (109 + 40 / 60, -(7 + 40 / 60), 21)

def calc(local_h, local_m):
    local = datetime(2008, 9, 28, local_h, local_m, tzinfo=LOCAL_TZ)
    utc = local.astimezone(timezone.utc)
    jd = swe.julday(utc.year, utc.month, utc.day,
                    utc.hour + utc.minute / 60 + utc.second / 3600)
    ra_dec = swe.calc_ut(jd, swe.SUN, swe.FLG_MOSEPH | swe.FLG_EQUATORIAL)[0]
    az_w_s, h_true, h_app = swe.azalt(
        jd, swe.EQU2HOR, SITE, 0.0, 10.0, (ra_dec[0], ra_dec[1], ra_dec[2]))
    return {
        'local_utc_plus_7': local.isoformat(),
        'utc': utc.isoformat().replace('+00:00', 'Z'),
        'site_lon_e_deg': SITE[0], 'site_lat_deg': SITE[1],
        'site_height_m': SITE[2],
        'sun_true_altitude_deg': round(h_true, 6),
        'sun_center_depression_deg': round(-h_true, 6),
        'sun_azimuth_north_clockwise_deg': round((az_w_s + 180) % 360, 6),
    }

if __name__ == '__main__':
    canopus = calc(5, 12)
    sirius = calc(5, 15)
    reported_sunrise = calc(5, 31)
    assert canopus['utc'] == '2008-09-27T22:12:00Z'
    assert sirius['utc'] == '2008-09-27T22:15:00Z'
    assert 4.6 < canopus['sun_center_depression_deg'] < 4.8
    assert 3.8 < sirius['sun_center_depression_deg'] < 4.1
    assert sirius['sun_true_altitude_deg'] > canopus['sun_true_altitude_deg']
    assert abs(reported_sunrise['sun_true_altitude_deg']) < 0.25
    print(json.dumps({
        'source': 'https://astronomycenter.net/icop/shw29.html',
        'source_report': "Ma'rufin Sudibyo 2008-09-28 (indexed archive)",
        'star_report_type': 'MORNING_LAST_VISIBILITY_NOT_EVENING_FIRST',
        'source_raw_byte_hash': 'UNVERIFIED',
        'human_unaided_star_mode': 'AMBIGUOUS',
        'canopus_not_seen_since': canopus,
        'sirius_not_seen_since': sirius,
        'reported_local_sunrise': reported_sunrise,
        'eligible_blind_first_star_events': 0,
        'first_sighting_model_residuals_computed': 0,
        'self_checks_passed': 6,
        'limitation': 'no first-YES or paired star checks, no directional sky radiance or aerosol, no source bytes, no adaptation',
    }, indent=2, ensure_ascii=False))
