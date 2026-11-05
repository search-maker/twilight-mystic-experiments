#!/usr/bin/env python3
"""Result-blind ephemeris QC of five *published* Spitschan 2016 Table 1 extrema.
Never reads spectra or model predictions. Published elevation extrema are not
independent ground truth; this is a published-metadata geolocation audit.
"""
import datetime as dt, json, math
from zoneinfo import ZoneInfo
import swisseph as swe

# Table 1 of DOI 10.1038/srep26756, Rural rows. Each selected value is
# the maximum solar altitude at the table's start (E) or end (M).
ROWS = [
 ("2014-06-30T18:52:55",16.73,"rural-evening-jun30-start"),
 ("2014-07-01T08:08:23",26.45,"rural-morning-jul01-end"),
 ("2014-07-02T19:38:19",8.52,"rural-evening-jul02-start"),
 ("2014-07-12T19:09:09",13.34,"rural-evening-jul12-start"),
 ("2014-07-14T12:35:07",70.54,"rural-evening-jul14-start"),
]
# Representative geolocations, not verified instrument GPS coordinates.
SITES={"cherry_springs_pa":{"lon":-77.8125,"lat":41.6646,"elev_m":710},
       "philadelphia_pa":{"lon":-75.1652,"lat":39.9526,"elev_m":10}}

def solar_alt(clock,site,local_edst=True):
    tz=ZoneInfo("America/New_York") if local_edst else dt.timezone.utc
    t=dt.datetime.fromisoformat(clock).replace(tzinfo=tz).astimezone(dt.timezone.utc)
    j=swe.julday(t.year,t.month,t.day,t.hour+t.minute/60+t.second/3600)
    eq,_=swe.calc_ut(j,swe.SUN,swe.FLG_MOSEPH|swe.FLG_EQUATORIAL)
    alt=swe.azalt(j,swe.EQU2HOR,(site['lon'],site['lat'],site['elev_m']),0,15,eq)[1]
    return alt,t.isoformat()

def run():
    out={"source":"Spitschan et al 2016 DOI:10.1038/srep26756 published Table 1",
         "notice":"2017 erratum DOI:10.1038/srep46930: originally incomplete supplementary S2/S3",
         "sites":SITES,"geometry_only":True,"spectral_data_read":False,
         "model_validation":"NOT_PERFORMED","timestamp_authentication":"UNVERIFIED_EDT_HYPOTHESIS",
         "method":"Swiss Ephemeris 2.10.03 Moshier Sun equatorial true geometric altitude; local clock America/New_York (UTC-4) hypothesis, no refraction"}
    results=[]
    for clock,published,which in ROWS:
        row={"case":which,"table_clock":clock,"table_extremum_deg":published,"estimated_utc":None}
        for label,site in SITES.items():
            pred,t=solar_alt(clock,site)
            row[label+"_sun_alt_deg"]=round(pred,6)
            row[label+"_residual_vs_table_deg"]=round(pred-published,6)
            row['estimated_utc']=t
        results.append(row)
    out['comparison']=results
    for site in SITES:
        residuals=[r[site+'_residual_vs_table_deg'] for r in results]
        out[site+'_rmse_deg']=round(math.sqrt(sum(x*x for x in residuals)/len(residuals)),6)
        out[site+'_max_abs_residual_deg']=round(max(abs(x) for x in residuals),6)
    assert out['philadelphia_pa_max_abs_residual_deg'] < 0.1
    assert out['cherry_springs_pa_max_abs_residual_deg'] > 1.5
    assert out['cherry_springs_pa_rmse_deg'] > 1.5
    assert out['philadelphia_pa_rmse_deg'] < 0.1
    out['classification']='PUBLISHED_RURAL_SOLAR_ELEVATION_NUMBERS_MATCH_PHILADELPHIA_GEOMETRY_NOT_CHERRY_SPRINGS__REQUIRES_ORIGINAL_METADATA_RECONCILIATION'
    out['implication']='DO NOT use published rural solar-altitude metadata as Cherry Springs site-accurate label until site/time/calculation provenance resolved.'
    return out

if __name__=='__main__': print(json.dumps(run(),indent=2,sort_keys=True))
