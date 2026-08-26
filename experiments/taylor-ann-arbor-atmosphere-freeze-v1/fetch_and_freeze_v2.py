#!/usr/bin/env python3
from __future__ import annotations

import csv, hashlib, io, json, math, statistics, sys, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else 'atmosphere-artifact')
OUT.mkdir(parents=True, exist_ok=True)
START = datetime(2025,8,8,0,30,tzinfo=timezone.utc)
END = datetime(2025,8,8,1,30,tzinfo=timezone.utc)
MID = datetime(2025,8,8,1,0,tzinfo=timezone.utc)
WINDOW = timedelta(hours=3)
SITES = [
    {'name':'Windsor_B','distance_km':51.6,'lat':42.283,'lon':-83.083,'elev_m':200.0},
    {'name':'Windsor_M','distance_km':69.8,'lat':42.170,'lon':-82.870,'elev_m':190.0},
]
SENS = [0.05,0.10,0.15,0.20,0.30,0.40]


def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':'twilight-mystic-experiments/1.0 scientific-validation'})
    with urllib.request.urlopen(req,timeout=90) as r: return r.read()

def h(b): return hashlib.sha256(b).hexdigest()

def url(site,lunar=False):
    p={'site':site,'year':2025,'month':8,'day':7,'year2':2025,'month2':8,'day2':9,'AOD20':1,'AVG':10,'if_no_html':1}
    if lunar: p['lunar_merge']=1
    return 'https://aeronet.gsfc.nasa.gov/cgi-bin/print_web_data_v3?'+urllib.parse.urlencode(p)

def f(x):
    try:
        v=float((x or '').strip())
        return v if math.isfinite(v) and v>0 and v>-900 else None
    except Exception: return None

def parse(raw,site):
    lines=[x.strip() for x in raw.decode('utf-8-sig',errors='replace').splitlines() if x.strip()]
    hi=next((i for i,x in enumerate(lines) if 'Date(dd:mm:yyyy)' in x and 'Time(hh:mm:ss)' in x),None)
    if hi is None: return [],{'header':False,'preview':lines[:8]}
    out=[]
    for r in csv.DictReader(io.StringIO('\n'.join(lines[hi:]))):
        try: t=datetime.strptime(r['Date(dd:mm:yyyy)']+' '+r['Time(hh:mm:ss)'],'%d:%m:%Y %H:%M:%S').replace(tzinfo=timezone.utc)
        except Exception: continue
        d={n:f(r.get('AOD_%dnm'%n)) for n in (440,500,551,550,675,870)}
        d={k:v for k,v in d.items() if v is not None}
        if 550 in d: tau,method=d[550],'direct_550'
        elif 551 in d: tau,method=d[551],'direct_551_as_550'
        else:
            tau=method=None
            for a,b in ((500,675),(440,675),(440,870),(500,870)):
                if a in d and b in d:
                    alpha=-math.log(d[b]/d[a])/math.log(b/a)
                    tau=d[a]*(550/a)**(-alpha); method=f'angstrom_{a}_{b}'; break
        if tau is not None: out.append({'site':site,'time':t,'aod550':tau,'method':method})
    return out,{'header':True,'records':len(out)}

def estimate(rows,t):
    rows=sorted(rows,key=lambda r:r['time'])
    lo=[r for r in rows if r['time']<=t and t-r['time']<=WINDOW]
    hi=[r for r in rows if r['time']>=t and r['time']-t<=WINDOW]
    if lo and hi and lo[-1]['time']!=hi[0]['time']:
        a,b=lo[-1],hi[0]; q=(t-a['time']).total_seconds()/(b['time']-a['time']).total_seconds()
        return a['aod550']+q*(b['aod550']-a['aod550']),'linear_bracket',[a,b]
    c=[r for r in rows if abs((r['time']-t).total_seconds())<=WINDOW.total_seconds()]
    if not c:return None,'none',[]
    r=min(c,key=lambda x:abs((x['time']-t).total_seconds()))
    return r['aod550'],'nearest_3h',[r]

def robust_sigma(rows):
    v=[r['aod550'] for r in rows if abs((r['time']-MID).total_seconds())<=WINDOW.total_seconds()]
    if len(v)<2:return 0.0
    m=statistics.median(v); return 1.4826*statistics.median(abs(x-m) for x in v)

def iem():
    p=[('station','ARB'),('data','all'),('year1',2025),('month1',8),('day1',7),('year2',2025),('month2',8),('day2',9),('tz','Etc/UTC'),('format','onlycomma'),('latlon','yes'),('elev','yes'),('missing','empty'),('trace','empty'),('direct','no'),('report_type',3),('report_type',4)]
    u='https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?'+urllib.parse.urlencode(p)
    b=get(u); (OUT/'karb_asos_raw.csv').write_bytes(b)
    return u,b

def main():
    rows={}; src={}
    for s in SITES:
        su=url(s['name']); sb=get(su); (OUT/f"aeronet_{s['name']}_solar_L2.txt").write_bytes(sb)
        sr,sm=parse(sb,s['name']); rows[s['name']]=sr
        lu=url(s['name'],True); lb=get(lu); (OUT/f"aeronet_{s['name']}_lunar_L2.txt").write_bytes(lb)
        lr,lm=parse(lb,s['name'])
        src[s['name']]={'solar':{'url':su,'sha256':h(sb),**sm},'lunar':{'url':lu,'sha256':h(lb),**lm}}
    q=[]
    for s in SITES:
        v,m,sup=estimate(rows[s['name']],MID)
        if v is not None:q.append((s['distance_km'],s,v,m,sup))
    met_url,met_raw=iem()
    base={'schemaVersion':2,'selectionRule':'nearest AERONET V3 solar Level-2 site <=75 km with AOD550 within +/-3 h; lunar Level-2 retained only as additive evidence; otherwise reanalysis','observationWindowUTC':[START.isoformat(),END.isoformat()],'aodSensitivity550':SENS,'sources':src,'surfaceMeteorology':{'station':'KARB/ARB','url':met_url,'sha256':h(met_raw)}}
    if not q:
        base['status']='AERONET_PRIMARY_UNAVAILABLE_REANALYSIS_REQUIRED'
        (OUT/'atmosphere.freeze.json').write_text(json.dumps(base,indent=2,sort_keys=True)+'\n'); print(json.dumps(base,indent=2)); return 42
    q.sort(key=lambda x:x[0]); _,ps,pv,pm,_=q[0]; pr=rows[ps['name']]
    sec=q[1][2] if len(q)>1 else None; spatial=abs(pv-sec) if sec is not None else 0.0; temporal=robust_sigma(pr)
    sigma=math.sqrt(0.01**2+spatial**2+temporal**2)
    base.update({'status':'AERONET_SOLAR_LEVEL2_PRIMARY_FROZEN','primarySite':ps,'primaryAOD550AtMidpoint':pv,'primaryInterpolation':pm,'measurementSigmaAOD':0.01,'temporalRobustSigmaAOD':temporal,'spatialCrossSiteAbsDifferenceAOD':spatial,'combinedConservativeSigmaAOD':sigma,'secondarySiteMidpointAOD550':sec,'qualityBoundary':'No Taylor SQM brightness or MYSTIC residual was read.'})
    times=[START+timedelta(minutes=2*i) for i in range(31)]; times.insert(9,datetime(2025,8,8,0,47,tzinfo=timezone.utc))
    per=[]
    for i,t in enumerate(times,1):
        v,m,sup=estimate(pr,t); per.append({'row':i,'timeUTC':t.isoformat(),'aod550':v,'method':m,'supportUTC':[x['time'].isoformat() for x in sup]})
    (OUT/'aod_per_observation.json').write_text(json.dumps(per,indent=2,sort_keys=True)+'\n')
    with (OUT/'aeronet_derived_aod550.csv').open('w',newline='') as fh:
        w=csv.writer(fh); w.writerow(['site','timeUTC','aod550','method'])
        for s in SITES:
            for r in rows[s['name']]:w.writerow([s['name'],r['time'].isoformat(),f"{r['aod550']:.9f}",r['method']])
    (OUT/'atmosphere.freeze.json').write_text(json.dumps(base,indent=2,sort_keys=True)+'\n'); print(json.dumps(base,indent=2)); return 0

if __name__=='__main__': raise SystemExit(main())
