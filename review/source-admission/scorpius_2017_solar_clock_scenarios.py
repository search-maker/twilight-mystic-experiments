"""Descriptive geometry only for a PUBLIC 2017 visual-source locator.
No first-NOT_SEEN/first-YES evidence or scientifically qualified model predictions.
Requires pyswisseph (Swiss Ephemeris). This is not a MYSTIC run.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import swisseph as swe

# Community centroid (Mapcarta/OSM St. Croix, NS) -- NOT surveyed SCO observer coordinates.
PROXY_LAT = 44.96194
PROXY_LON = -64.03379
LOOKS = {"Vega_mixed": "21:38", "Antares_visual": "21:40",
         "Nu_Sco_Beta_Sco_visual": "21:48", "Pi_Sco_Rho_Sco_visual": "21:54",
         "tree_line_report_visual": "22:12"}


def sun_depression(utc):
    jd = swe.julday(utc.year, utc.month, utc.day,
                    utc.hour + utc.minute / 60 + utc.second / 3600)
    ra_dec, _ = swe.calc_ut(jd, swe.SUN, swe.FLG_SWIEPH | swe.FLG_EQUATORIAL)
    _, true_alt, _ = swe.azalt(jd, swe.EQU2HOR,
                               (PROXY_LON, PROXY_LAT, 0.0), 0.0, 10.0, ra_dec)
    return -true_alt


def scenarios(hhmm):
    hh, mm = map(int, hhmm.split(':'))
    wall = datetime(2017, 7, 26, hh, mm)
    # Legal zone at St. Croix, Canada, on this July date.
    local_adt = wall.replace(tzinfo=ZoneInfo('America/Halifax'))
    assert local_adt.utcoffset().total_seconds() == -3 * 3600
    # Alternative one-hour interpretation motivated ONLY by later note's 'EDT' text.
    eastern_edt = wall.replace(tzinfo=ZoneInfo('America/New_York'))
    assert eastern_edt.utcoffset().total_seconds() == -4 * 3600
    return [(label, t.astimezone(timezone.utc), sun_depression(t.astimezone(timezone.utc)))
            for label, t in [('ADT', local_adt), ('EDT', eastern_edt)]]


def main():
    results = []
    for label, hhmm in LOOKS.items():
        rows = scenarios(hhmm)
        assert len(rows) == 2 and rows[1][1] > rows[0][1]
        assert all(-90 < dep < 90 for _, _, dep in rows)
        print(label, hhmm, ' | '.join(f'{tz} {utc:%Y-%m-%dT%H:%MZ} dep={dep:.4f}'
                                  for tz, utc, dep in rows))
        results.append(rows)
    assert results[1][0][1].isoformat() == '2017-07-27T00:40:00+00:00'
    assert results[1][1][1].isoformat() == '2017-07-27T01:40:00+00:00'
    assert 7 < results[1][1][2] - results[1][0][2] < 9
    print('PASS: 5 source-clock cases, 10 scenario depressions; no validation metrics')


if __name__ == '__main__':
    main()
