#!/usr/bin/env python3
from __future__ import annotations

import hashlib, json, math, statistics, sys, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

OUT=Path(sys.argv[1] if len(sys.argv)>1 else 'atmosphere-artifact'); OUT.mkdir(parents=True,exist_ok=True)
LAT,LON=42.256,-83.709
START=datetime(2025,8,8,0,30,tzinfo=timezone.utc); END=datetime(2025,8,8,1,30,tzinfo=timezone.utc); MID=datetime(2025,8,8,1,0,tzinfo=timezone.utc)
POINTS=[('center',LAT,LON),('north',LAT+0.4,LON),('south',LAT-0.4,LON),('east',LAT,LON+0.4),('west',LAT,LON-0.4)]
REGIONAL_RELATIVE_ERROR_ENVELOPE=0.49
SENS=[0.05,0.10,0.15,0.20,0.30,0.40]

def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':'twilight-mystic-experiments/1.0 scientific-validation'})
    with urllib.request.urlopen(req,timeout=90) as r:return r.read()
def sha(b):return hashlib.sha256(b).hexdigest()
def api_url(lat,lon):
    p={'latitude':lat,'longitude':lon,'hourly':'aerosol_optical_depth','domains':'cams_global','start_date':'2025-08-07','end_date':'2025-08-08','timezone':'GMT','cell_selection':'nearest'}
    return 'https://air-quality-api.open-meteo.com/v1/air-quality?'+urllib.parse.urlencode(p)
def parse(raw):
    j=json.loads(raw); times=j['hourly']['time']; vals=j['hourly']['aerosol_optical_depth']; out=[]
    for t,v in zip(times,vals):
        if v is None:continue
        dt=datetime.fromisoformat(t).replace(tzinfo=timezone.utc)
        out.append((dt,float(v)))
    return j,out
def interp(rows,t):
    rows=sorted(rows)
    exact=[v for tt,v in rows if tt==t]
    if exact:return exact[0]
    lo=[x for x in rows if x[0]<=t]; hi=[x for x in rows if x[0]>=t]
    if not lo or not hi:return None
    a,b=lo[-1],hi[0]
    if a[0]==b[0]:return a[1]
    q=(t-a[0]).total_seconds()/(b[0]-a[0]).total_seconds(); return a[1]+q*(b[1]-a[1])
def main():
    datasets={}; metadata={}; midpoint={}
    for name,lat,lon in POINTS:
        u=api_url(lat,lon); b=get(u); (OUT/f'cams_global_{name}_raw.json').write_bytes(b); j,rows=parse(b)
        if not rows:raise RuntimeError(f'no CAMS AOD values for {name}')
        datasets[name]=rows; midpoint[name]=interp(rows,MID)
        metadata[name]={'requestLatitude':lat,'requestLongitude':lon,'returnedLatitude':j.get('latitude'),'returnedLongitude':j.get('longitude'),'elevationM':j.get('elevation'),'timezone':j.get('timezone'),'url':u,'rawSha256':sha(b),'midpointAOD550':midpoint[name]}
    primary=midpoint['center']
    spatial_values=[v for v in midpoint.values() if v is not None]
    spatial_sd=statistics.stdev(spatial_values) if len(spatial_values)>1 else 0.0
    central=datasets['center']; near=[v for t,v in central if datetime(2025,8,7,22,tzinfo=timezone.utc)<=t<=datetime(2025,8,8,4,tzinfo=timezone.utc)]
    temporal_sd=statistics.stdev(near) if len(near)>1 else 0.0
    local_sigma=math.sqrt(spatial_sd**2+temporal_sd**2)
    model_error_halfwidth=REGIONAL_RELATIVE_ERROR_ENVELOPE*primary
    freeze={'schemaVersion':3,'status':'CAMS_GLOBAL_FALLBACK_PRIMARY_FROZEN','provider':'CAMS Global Atmospheric Composition via Open-Meteo archive API','providerDomain':'cams_global','nativeResolution':'0.4 deg, 3-hourly per provider documentation; API may expose interpolated hourly values','selectionReason':'AERONET V3 Level-2 returned no records for Windsor_B or Windsor_M under predeclared <=75 km +/-3 h rule','observationWindowUTC':[START.isoformat(),END.isoformat()],'primaryAOD550AtMidpoint':primary,'spatialSampleAOD550':midpoint,'spatialSampleStdAOD':spatial_sd,'temporalStdAODCentralWindow':temporal_sd,'localSpatialTemporalSigmaAOD':local_sigma,'camsNorthAmericaRelativeErrorEnvelope':REGIONAL_RELATIVE_ERROR_ENVELOPE,'camsModelErrorEnvelopeHalfWidthAOD':model_error_halfwidth,'primaryAOD550Envelope':[max(0.0,primary-model_error_halfwidth),primary+model_error_halfwidth],'aodSensitivity550':SENS,'sources':metadata,'qualityBoundary':'CAMS acquisition and uncertainty rule frozen without reading Taylor SQM brightness or MYSTIC residuals. Regional 49% error envelope is external CAMS validation evidence and is not treated as a Gaussian 1-sigma term.'}
    obs=[START+timedelta(minutes=2*i) for i in range(31)]; obs.insert(9,datetime(2025,8,8,0,47,tzinfo=timezone.utc))
    per=[{'row':i+1,'timeUTC':t.isoformat(),'aod550':interp(central,t)} for i,t in enumerate(obs)]
    (OUT/'cams_aod_per_observation.json').write_text(json.dumps(per,indent=2,sort_keys=True)+'\n')
    (OUT/'atmosphere.cams.freeze.json').write_text(json.dumps(freeze,indent=2,sort_keys=True)+'\n')
    print(json.dumps(freeze,indent=2,sort_keys=True)); return 0
if __name__=='__main__':raise SystemExit(main())
