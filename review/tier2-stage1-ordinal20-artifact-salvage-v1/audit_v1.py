#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math, statistics
from pathlib import Path
from typing import Any
KM_PHOT=683.002; KM_SCOT=1700.06
CIE_WL=tuple(float(w) for w in range(380,781,10))
V_PHOT=(0.00004,0.00012,0.0004,0.0012,0.0040,0.0116,0.023,0.038,0.060,0.09098,0.13902,0.20802,0.323,0.503,0.710,0.862,0.954,0.99495,0.995,0.952,0.870,0.757,0.631,0.503,0.381,0.265,0.175,0.107,0.061,0.032,0.017,0.00821,0.004102,0.002091,0.001047,0.00052,0.000249,0.00012,0.00006,0.00003,0.000015)
V_SCOT=(0.000589,0.002209,0.00929,0.03484,0.0966,0.1998,0.3281,0.455,0.567,0.676,0.793,0.904,0.982,0.997,0.935,0.811,0.650,0.481,0.3288,0.2076,0.1212,0.0655,0.03315,0.01593,0.00737,0.003335,0.001497,0.000677,0.0003129,0.000148,0.0000715,0.00003533,0.0000178,0.00000914,0.00000478,0.000002546,0.000001379,0.00000076,0.000000425,0.000000241,0.000000139)
BESSELL=((470.,0.),(480.,.03),(490.,.163),(500.,.458),(510.,.78),(520.,.967),(530.,1.),(540.,.973),(550.,.898),(560.,.792),(570.,.684),(580.,.574),(590.,.461),(600.,.359),(610.,.27),(620.,.197),(630.,.135),(640.,.081),(650.,.045),(660.,.025),(670.,.017),(680.,.013),(690.,.009),(700.,0.))
class Refusal(RuntimeError):pass
def req(c,m):
    if not c:raise Refusal(m)
def canon(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def interp(tab,w):
    if w<380 or w>780:return 0.0
    if w==780:return tab[-1]
    x=(w-380.)/10.;i=int(math.floor(x));f=x-i;return tab[i]*(1-f)+tab[i+1]*f
def bess(w):
    if w<470 or w>700:return 0.0
    if w==700:return 0.0
    x=(w-470.)/10.;i=int(math.floor(x));f=x-i;return BESSELL[i][1]*(1-f)+BESSELL[i+1][1]*f
def parse(p,grid):
    toks=[];wl=[];r=[]
    for line in p.read_text(encoding='utf-8',errors='strict').splitlines():
        x=line.split();req(len(x)>=2,'audit spectrum row drift');toks.append(x[0]);vals=[float(v) for v in x];req(all(math.isfinite(v) for v in vals) and all(v>=0 for v in vals[1:]),'audit invalid spectrum');wl.append(vals[0]);r.append(vals[-1])
    req(len(toks)==8001 and toks[0]=='380.00000' and toks[-1]=='780.00000','audit grid count/endpoints drift');req(all(wl[i+1]>wl[i] for i in range(8000)),'audit grid order drift');g=hashlib.sha256(('\n'.join(toks)+'\n').encode()).hexdigest();req(g==grid['canonicalTokenStreamSha256'],'audit grid token hash drift');req(not all(abs((wl[i+1]-wl[i])-0.05)<1e-7 for i in range(8000)),'audit legacy parser unexpectedly accepts');return wl,r,g
def trap(wl,r,weight,km):return km*1e-3*sum(.5*(weight(wl[i])*r[i]+weight(wl[i+1])*r[i+1])*(wl[i+1]-wl[i]) for i in range(len(wl)-1))
def johnson(wl,r):
    num=den=0.0
    for i in range(len(wl)-1):
        dl=wl[i+1]-wl[i];a=bess(wl[i])*wl[i];b=bess(wl[i+1])*wl[i+1];num+=.5*(a*r[i]+b*r[i+1])*dl;den+=.5*(a+b)*dl
    req(den>0,'audit Johnson support zero');return num/den
def channels(wl,r):return {'photopicLuminanceCdM2':trap(wl,r,lambda w:interp(V_PHOT,w),KM_PHOT),'scotopicLuminanceScotCdM2':trap(wl,r,lambda w:interp(V_SCOT,w),KM_SCOT),'johnsonVEffectiveRadiance_mW_m2_nm_sr':johnson(wl,r)}
def main()->int:
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--contract',type=Path,required=True);p.add_argument('--results-root',type=Path,required=True);p.add_argument('--aggregate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    try:
        m=load(a.manifest);c=load(a.contract);agg=load(a.aggregate);req(agg['aggregateSha256']==canon({k:v for k,v in agg.items() if k!='aggregateSha256'}),'aggregate selfhash drift');e=[]
        for case in m['cases']:
            d=a.results_root/case['caseId'];r=load(d/'salvage-case.json');h=r['contentSha256'];z=dict(r);z.pop('contentSha256');req(h==canon(z),'salvage case selfhash drift');req(r['status']=='ARTIFACT_ONLY_SALVAGED_COMPLETED' and r['solverExecutionCountProven']==1 and r['protectedHoldoutValueExposed'] is False,'audit case boundary drift');req((r['caseId'],r['geometryId'],r['block'],r['seed'],r['photonHistories'])==(case['caseId'],case['geometryId'],case['block'],case['seed'],case['photonHistories']),'audit case identity drift')
            for name,want in r['rawMemberSha256ByBasename'].items():req(sha(d/name)==want,f'audit raw hash drift {case["caseId"]}/{name}')
            wl,rad,g=parse(d/'mc.rad.spc',c['gridSerialization']);swl,_,sg=parse(d/'mc.rad.std.spc',c['gridSerialization']);req(wl==swl and g==sg,'audit rad/std grid mismatch');ch=channels(wl,rad);req(ch==r['channels'],'audit case channels mismatch');e.append({'caseId':case['caseId'],'geometryId':case['geometryId'],'block':case['block'],'seed':case['seed'],'photonHistories':case['photonHistories'],'sourceArtifactId':r['sourceArtifactId'],'sourceArtifactDigest':r['sourceArtifactDigest'],'radianceOutputSha256':r['radianceOutputSha256'],'stdRadianceOutputSha256':r['stdRadianceOutputSha256'],'wavelengthTokenGridSha256':g,'physicalInputCanonicalSha256':r['physicalInputCanonicalSha256'],'rawAllZero':all(v==0.0 for v in rad),'channels':ch})
        req(e==agg['caseEvidence'],'audit aggregate case evidence mismatch');recs=[]
        for g in m['geometries']:
            rows=sorted([x for x in e if x['geometryId']==g['geometryId']],key=lambda x:x['block']);means={};se={}
            for k in rows[0]['channels']:
                vals=[x['channels'][k] for x in rows];means[k]=statistics.fmean(vals);se[k]=statistics.stdev(vals)/2.0
            recs.append({'geometryId':g['geometryId'],'role':'surrogate-training','blockCount':4,'channelsMean':means,'channelsBlockStandardError':se,'rawExactZeroCaseIds':[x['caseId'] for x in rows if x['rawAllZero']]})
        req(recs==agg['records'],'audit geometry records mismatch');out={'schemaVersion':1,'stageId':'tier2-stage1-ordinal20-artifact-salvage-independent-audit-v1','status':'PASSED','contractId':c['contractId'],'manifestSha256':m['manifestSha256'],'sourceRunId':c['source']['runId'],'aggregateSha256':agg['aggregateSha256'],'caseCountAudited':76,'trainingGeometryCount':19,'caseEvidenceCanonicalSha256':canon(e),'geometryRecordsCanonicalSha256':canon(recs),'failureCount':0,'holdoutValuesRead':False,'protectedHoldoutRecordCount':0,'modelFittingAuthorized':False,'modelSelectionAuthorized':False,'protectedHoldoutOpeningAuthorized':False};out['auditSha256']=canon(out);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n');print(out['auditSha256']);return 0
    except Exception as x:print(json.dumps({'status':'REFUSED','reason':str(x)},sort_keys=True));return 2
if __name__=='__main__':raise SystemExit(main())
