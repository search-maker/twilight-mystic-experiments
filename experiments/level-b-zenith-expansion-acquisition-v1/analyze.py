#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,math
from pathlib import Path

def load_results(root):
    out=[]
    for p in root.rglob('case-result.json'):
        x=json.loads(p.read_text())
        if x.get('status')=='COMPLETED':out.append(x)
    return out
def mean_se(rows,key,stdkey):
    vals=[float(x[key]) for x in rows]; sig=[float(x[stdkey]) for x in rows]
    mean=sum(vals)/len(vals); se=math.sqrt(sum(s*s for s in sig))/len(sig); return mean,se
def main():
    p=argparse.ArgumentParser();p.add_argument('--results-root',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();m=json.loads(a.manifest.read_text());rows=load_results(a.results_root)
    if len(rows)!=m['caseCount']:raise SystemExit(f'expected {m["caseCount"]} completed cases, got {len(rows)}')
    by={}
    for r in rows:by.setdefault(r['geometryId'],[]).append(r)
    if any(len(v)!=4 for v in by.values()):raise SystemExit('every geometry must have exactly 4 completed blocks')
    stats={g:{'meanPhotopicCdM2':mean_se(rs,'selectedPhotopicContributionCdM2','selectedPhotopicStdContributionCdM2')[0],'sePhotopicCdM2':mean_se(rs,'selectedPhotopicContributionCdM2','selectedPhotopicStdContributionCdM2')[1]} for g,rs in by.items()}
    base=stats['zenith-train-90-b'];checks=[]
    for g in ['zenith-invariance-90-az90','zenith-invariance-90-az180']:
        x=stats[g]; delta=abs(math.log(x['meanPhotopicCdM2']/base['meanPhotopicCdM2'])); relsig=math.sqrt((x['sePhotopicCdM2']/x['meanPhotopicCdM2'])**2+(base['sePhotopicCdM2']/base['meanPhotopicCdM2'])**2);limit=max(0.01,4*relsig);checks.append({'geometryId':g,'absLogDifference':delta,'fourSigmaOrOnePercentLimit':limit,'pass':delta<=limit})
    out={'schemaVersion':1,'status':'ACQUISITION_COMPLETE' if all(x['pass'] for x in checks) else 'ACQUISITION_COMPLETE_ZENITH_INVARIANCE_GATE_FAILED','caseCount':len(rows),'geometryCount':len(by),'zenithAzimuthInvarianceChecks':checks,'geometryPhotopicSummary':stats,'boundary80GeometryIds':[g for g in by if g.startswith('zenith-train-80-')],'modelRefitAuthorized':False,'supportExpansionAuthorized':False,'holdoutExecutionAuthorized':False}
    a.output.mkdir(parents=True,exist_ok=True);(a.output/'summary.json').write_text(json.dumps(out,indent=2,sort_keys=True,allow_nan=False)+'\n');print(json.dumps(out,sort_keys=True))
    if not all(x['pass'] for x in checks):raise SystemExit(2)
if __name__=='__main__':main()
