#!/usr/bin/env python3
from __future__ import annotations
import argparse, copy, hashlib, json, math, statistics
from pathlib import Path
from typing import Any

KM_PHOT=683.002; KM_SCOT=1700.06
CIE_WL=tuple(float(w) for w in range(380,781,10))
V_PHOT=(0.00004,0.00012,0.0004,0.0012,0.0040,0.0116,0.023,0.038,0.060,0.09098,0.13902,0.20802,0.323,0.503,0.710,0.862,0.954,0.99495,0.995,0.952,0.870,0.757,0.631,0.503,0.381,0.265,0.175,0.107,0.061,0.032,0.017,0.00821,0.004102,0.002091,0.001047,0.00052,0.000249,0.00012,0.00006,0.00003,0.000015)
V_SCOT=(0.000589,0.002209,0.00929,0.03484,0.0966,0.1998,0.3281,0.455,0.567,0.676,0.793,0.904,0.982,0.997,0.935,0.811,0.650,0.481,0.3288,0.2076,0.1212,0.0655,0.03315,0.01593,0.00737,0.003335,0.001497,0.000677,0.0003129,0.000148,0.0000715,0.00003533,0.0000178,0.00000914,0.00000478,0.000002546,0.000001379,0.00000076,0.000000425,0.000000241,0.000000139)
BESSELL=((470.,0.),(480.,.03),(490.,.163),(500.,.458),(510.,.78),(520.,.967),(530.,1.),(540.,.973),(550.,.898),(560.,.792),(570.,.684),(580.,.574),(590.,.461),(600.,.359),(610.,.27),(620.,.197),(630.,.135),(640.,.081),(650.,.045),(660.,.025),(670.,.017),(680.,.013),(690.,.009),(700.,0.))

class Refusal(RuntimeError): pass
def req(c:bool,m:str)->None:
    if not c: raise Refusal(m)
def canon(v:Any)->str: return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def sha(p:Path)->str: return hashlib.sha256(p.read_bytes()).hexdigest()

def interp(tab:tuple[float,...],w:float)->float:
    if w<CIE_WL[0] or w>CIE_WL[-1]: return 0.0
    if w==CIE_WL[-1]: return tab[-1]
    x=(w-380.)/10.; i=int(math.floor(x)); f=x-i; return tab[i]*(1-f)+tab[i+1]*f

def bess(w:float)->float:
    if w<470 or w>700: return 0.0
    if w==700: return 0.0
    x=(w-470.)/10.; i=int(math.floor(x)); f=x-i; return BESSELL[i][1]*(1-f)+BESSELL[i+1][1]*f

def parse(path:Path)->tuple[list[float],list[float]]:
    wl=[]; r=[]
    for line in path.read_text(encoding='utf-8',errors='strict').splitlines():
        p=line.split()
        if len(p)<2: continue
        try: w=float(p[0]); v=float(p[-1])
        except ValueError: continue
        req(math.isfinite(w) and math.isfinite(v) and v>=0,'invalid spectrum'); wl.append(w); r.append(v)
    req(len(wl)==8001 and abs(wl[0]-380)<1e-8 and abs(wl[-1]-780)<1e-8 and all(abs((wl[i+1]-wl[i])-.05)<1e-7 for i in range(8000)),'spectrum grid drift')
    return wl,r

def trap(wl:list[float],r:list[float],weight,km:float)->float:
    return km*1e-3*sum(.5*(weight(wl[i])*r[i]+weight(wl[i+1])*r[i+1])*(wl[i+1]-wl[i]) for i in range(len(wl)-1))

def johnson(wl:list[float],r:list[float])->float:
    num=den=0.0
    for i in range(len(wl)-1):
        dl=wl[i+1]-wl[i]; a=bess(wl[i])*wl[i]; b=bess(wl[i+1])*wl[i+1]; num+=.5*(a*r[i]+b*r[i+1])*dl; den+=.5*(a+b)*dl
    req(den>0,'Johnson V zero support')
    return num/den

def channels(wl:list[float],r:list[float])->dict[str,float]:
    return {'photopicLuminanceCdM2':trap(wl,r,lambda w:interp(V_PHOT,w),KM_PHOT),'scotopicLuminanceScotCdM2':trap(wl,r,lambda w:interp(V_SCOT,w),KM_SCOT),'johnsonVEffectiveRadiance_mW_m2_nm_sr':johnson(wl,r)}

def locate(root:Path,case_id:str)->Path:
    hits=[]
    for p in root.rglob('case-result.json'):
        try:x=json.loads(p.read_text())
        except Exception:continue
        if x.get('caseId')==case_id:hits.append(p.parent)
    req(len(hits)==1,f'audit case occurrence !=1: {case_id}')
    return hits[0]

def audit(manifest:dict[str,Any],aggregate:dict[str,Any],results_root:Path,module_root:Path|None=None)->dict[str,Any]:
    req(manifest.get('caseCount')==76 and manifest.get('geometryCount')==19 and manifest.get('trainingOnly') is True,'manifest stage1 drift')
    req(all(c.get('role')=='surrogate-training' and c.get('executionStage')=='TRAINING_ACQUISITION' for c in manifest.get('cases',[])),'manifest non-training case leaked')
    req(aggregate.get('aggregateSha256')==canon({k:v for k,v in aggregate.items() if k!='aggregateSha256'}),'aggregate selfhash drift')
    req(aggregate.get('manifestSha256')==manifest.get('manifestSha256'),'aggregate manifest binding drift')
    req((aggregate.get('caseCount'),aggregate.get('trainingGeometryCount'),aggregate.get('configuredPhotonHistories'))==(76,19,2_120_000_000),'aggregate accounting drift')
    req(aggregate.get('holdoutValuesRead') is False and aggregate.get('protectedHoldoutRecordCount')==0,'aggregate holdout drift')
    req(aggregate.get('modelFittingAuthorized') is False and aggregate.get('modelSelectionAuthorized') is False and aggregate.get('protectedHoldoutOpeningAuthorized') is False,'aggregate downstream boundary drift')
    required=set(manifest['artifactContract']['requiredMembers'])-{'case-result.json'}
    evidence=[]
    for c in manifest['cases']:
        d=locate(results_root,c['caseId']); r=json.loads((d/'case-result.json').read_text()); h=r.get('contentSha256'); z=copy.deepcopy(r); z.pop('contentSha256',None); req(h==canon(z),'audit case-result selfhash drift')
        req(r.get('status')=='COMPLETED' and r.get('role')=='surrogate-training' and r.get('protectedHoldoutValueExposed') is False,'audit saw failed/non-training/holdout exposure')
        req((r.get('caseId'),r.get('geometryId'),r.get('block'),r.get('seed'),r.get('photonHistories'))==(c['caseId'],c['geometryId'],c['block'],c['seed'],c['photonHistories']),'audit case identity drift')
        req((r.get('workflowRunAttempt'),r.get('syntaxCheckCount'),r.get('solverExecutionCount'))==(1,1,1) and r.get('retryPerformed') is False and r.get('resumePerformed') is False and r.get('githubRerun') is False,'audit attempt/retry contract drift')
        raw=r.get('rawMemberSha256ByBasename') or {}; req(set(raw)==required,'audit raw member hash map drift')
        for name,want in raw.items(): req((d/name).is_file() and sha(d/name)==want,f'audit raw member hash mismatch: {c["caseId"]}/{name}')
        wl,rad=parse(d/'mc.rad.spc'); swl,srad=parse(d/'mc.rad.std.spc'); req(wl==swl,'audit radiance/std wavelength grid mismatch')
        ch=channels(wl,rad); zero=all(v==0.0 for v in rad); req(zero==r.get('rawAllZero'),'audit raw zero flag drift')
        evidence.append({'caseId':c['caseId'],'geometryId':c['geometryId'],'block':c['block'],'seed':c['seed'],'photonHistories':c['photonHistories'],'rawAllZero':zero,'channels':ch,'radianceSha256':sha(d/'mc.rad.spc'),'stdRadianceSha256':sha(d/'mc.rad.std.spc'),'physicalInputCanonicalSha256':r['physicalInputCanonicalSha256']})
    req(len(evidence)==76 and len({x['caseId'] for x in evidence})==76,'audit case evidence universe drift')
    req(aggregate.get('caseEvidence')==evidence,'aggregate case evidence differs from independent raw-spectrum recomputation')
    records=[]
    for g in manifest['geometries']:
        rows=sorted([x for x in evidence if x['geometryId']==g['geometryId']],key=lambda x:x['block']); req([x['block'] for x in rows]==[1,2,3,4],'audit geometry block universe drift')
        means={}; se={}
        for k in rows[0]['channels']:
            vals=[x['channels'][k] for x in rows]; means[k]=statistics.fmean(vals); se[k]=statistics.stdev(vals)/2.0
        records.append({'geometryId':g['geometryId'],'role':'surrogate-training','blockCount':4,'channelsMean':means,'channelsBlockStandardError':se,'rawExactZeroCaseIds':[x['caseId'] for x in rows if x['rawAllZero']]})
    zeros=sorted(x['caseId'] for x in evidence if x['rawAllZero'])
    req(aggregate.get('records')==records,'aggregate geometry records/means/SE differ from independent recomputation')
    req(aggregate.get('rawExactZeroCaseIds')==zeros,'aggregate exact-zero case set drift')
    req(sum(x['photonHistories'] for x in evidence)==2_120_000_000,'audit photon accounting drift')
    out={'schemaVersion':1,'stageId':'public-tier2-v1-core-stage1-independent-audit-v1','status':'PASSED','manifestSha256':manifest['manifestSha256'],'aggregateSha256':aggregate['aggregateSha256'],'caseCountAudited':76,'trainingGeometryCount':19,'holdoutValuesRead':False,'protectedHoldoutRecordCount':0,'independentlyRecomputedFullSpectra':76,'independentlyRecomputedGeometryRecords':19,'caseEvidenceCanonicalSha256':canon(evidence),'geometryRecordsCanonicalSha256':canon(records),'exactZeroCaseIds':zeros,'failureCount':0,'modelFittingAuthorized':False,'modelSelectionAuthorized':False,'protectedHoldoutOpeningAuthorized':False}
    out['auditSha256']=canon(out); return out

def main()->int:
    p=argparse.ArgumentParser(); p.add_argument('--manifest',type=Path,required=True); p.add_argument('--aggregate',type=Path,required=True); p.add_argument('--results-root',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
    try:
        o=audit(json.loads(a.manifest.read_text()),json.loads(a.aggregate.read_text()),a.results_root); a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(o,indent=2,sort_keys=True,allow_nan=False)+'\n'); print(o['auditSha256']); return 0
    except Exception as e:
        o={'schemaVersion':1,'stageId':'public-tier2-v1-core-stage1-independent-audit-v1','status':'REFUSED','reason':str(e),'holdoutValuesRead':False,'protectedHoldoutRecordCount':0,'modelFittingAuthorized':False,'protectedHoldoutOpeningAuthorized':False}; a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(o,indent=2,sort_keys=True)+'\n'); print(json.dumps(o)); return 2
if __name__=='__main__': raise SystemExit(main())
