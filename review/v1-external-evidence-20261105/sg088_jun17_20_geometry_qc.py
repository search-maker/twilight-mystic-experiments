#!/usr/bin/env python3
"""Retrospective SG_088 solar/lunar geometry screen. No MYSTIC; no V1 pass.
Requires pyswisseph (Moshier). Reads the fixed, source-line-linked 24-row CSV.
Coordinates are a broad site-sensitivity box, NOT verified SG_088 coordinates.
Moon-free means geometric lunar altitude <-5 deg throughout the box.
"""
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import swisseph as swe

HERE=Path(__file__).resolve().parent
ROWS=HERE/'sg088_jun17_20_24rows.csv'
LAT=(32.0,32.4); LON=(-111.1,-110.5); ELEV=(0.,2500.)
FLAGS=swe.FLG_MOSEPH|swe.FLG_TOPOCTR|swe.FLG_EQUATORIAL

def alt(jd,body,lon,lat,elev):
    swe.set_topo(lon,lat,elev)
    vec,flag=swe.calc_ut(jd,body,FLAGS)
    assert flag & swe.FLG_MOSEPH
    return swe.azalt(jd,swe.EQU2HOR,(lon,lat,elev),0.,20.,vec[:3])[1]

def box(jd,body):
    return [alt(jd,body,lon,lat,elev) for lat in LAT for lon in LON for elev in ELEV]

with ROWS.open(newline='',encoding='utf-8') as f:
    rows=list(csv.DictReader(f))
assert len(rows)==24 and len({r['source_line_zero_based'] for r in rows})==24
result=[]
for row in rows:
    t=datetime.fromisoformat(row['utc']).astimezone(timezone.utc)
    jd=swe.julday(t.year,t.month,t.day,t.hour+t.minute/60+t.second/3600)
    suns=box(jd,swe.SUN); moons=box(jd,swe.MOON)
    sun_min=-max(suns);sun_max=-min(suns)
    assert 10.5 < sun_min and sun_max <=16, (row['utc'],sun_min,sun_max)
    result.append({'utc':row['utc'], 'mag':float(row['mag']),
      'source_line':int(row['source_line_zero_based']),
      'sun_dep_min':round(sun_min,4),'sun_dep_max':round(sun_max,4),
      'moon_alt_min':round(min(moons),4),'moon_alt_max':round(max(moons),4),
      'moon_disk_fraction':round(swe.pheno_ut(jd,swe.MOON,swe.FLG_MOSEPH)[1],6),
      'strict_moon_below_minus5':max(moons)<-5})
by_day={day:[r for r in result if r['utc'][:10]==day] for day in
        ('2023-06-17','2023-06-18','2023-06-19','2023-06-20')}
assert all(len(v)==6 for v in by_day.values())
assert all(x['strict_moon_below_minus5'] for x in by_day['2023-06-17']+by_day['2023-06-18'])
assert not any(x['strict_moon_below_minus5'] for x in by_day['2023-06-20'])
# Flux is proportional to 10**(-0.4*mag) for a fixed instrument passband.
flux_ratios=[round(10**(.4*(a['mag']-b['mag'])),4) for a,b in
  zip(by_day['2023-06-17'],by_day['2023-06-18'])]
assert all(1.6<x<3.2 for x in flux_ratios)
print(json.dumps({'rows':len(result),'all_in_10p5_16':True,
  'strict_moonfree_rows':sum(r['strict_moon_below_minus5'] for r in result),
  'moonfree_dates':['2023-06-17','2023-06-18'],
  'june18_to_june17_relative_flux_at_six_utc_slots':flux_ratios,
  'classification':'RETROSPECTIVE_SOURCE-QC_ONLY__90DEG_ZENITH_OOD_FOR_LATE_MODEL'},indent=2))
