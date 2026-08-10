#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,math,statistics
from pathlib import Path
from typing import Any

ANALYSIS_ID='public-tier1-full-spectrum-estimator-pilot-analysis-v4'
PROTOCOL_SHA='7ca0923204452ab203249dfd060dd5fef5465c48a20ba529c0a20748e0152434'
EXEC_SHA='be81c717cd943415ac51dc2b5356010b3d584b5279228c525d2defccc4680e0f'
SOURCE_DATASET_SHA='42478d099efea7392f5558716571400dc84ee28de5df1e22f85e8031d2138c41'
ADMISSION_REPORT_SHA='a043fa6c0a5e7ec282d887a4febe01277e0a0a20c82bff65ccb127705b40e0cf'
PRIMARY=('photopicLuminanceCdM2','scotopicLuminanceScotCdM2','johnsonVEffectiveRadiance_mW_m2_nm_sr')
RATIO_BOUNDS=(0.5,2.0)
GRID_BOUND={'photopicLuminanceCdM2':0.0011168248714839013,'scotopicLuminanceScotCdM2':0.0020320382260645697,'johnsonVEffectiveRadiance_mW_m2_nm_sr':0.0018607417688334404}

def canon(v:Any)->str: return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def load(p:Path)->dict[str,Any]:
 v=json.loads(p.read_text())
 if not isinstance(v,dict): raise ValueError(f'expected object: {p}')
 return v

def stats(values:list[float])->dict[str,Any]:
 if len(values)!=2 or any((not math.isfinite(x) or x<0) for x in values): raise ValueError('each fresh screening method requires exactly two finite nonnegative blocks')
 zero=any(x==0 for x in values); mean=sum(values)/2
 if zero or mean<=0: rsem=None; sd=None
 else:
  sd=statistics.stdev(values); rsem=sd/math.sqrt(2)/mean
 total=sum(values); den=sum(x*x for x in values)
 eff=(total*total/den) if den>0 else 0.0
 return {'blockCount':2,'values':values,'mean':mean,'sampleStd':sd,'descriptiveTwoBlockRsem':rsem,'zeroHitPresent':zero,'effectiveBlockCount':eff,'maximumBlockFraction':(max(values)/total if total>0 else None),'inferentialUsePermitted':False}

def ratio_screen(a_mean:float,b_mean:float,grid_bound:float=0.0)->dict[str,Any]:
 if not math.isfinite(a_mean) or not math.isfinite(b_mean) or a_mean<=0 or b_mean<=0:
  return {'computable':False,'passed':False,'reason':'nonpositive/nonfinite mean','statisticalEquivalenceClaim':False}
 ratio=a_mean/b_mean; lo,hi=RATIO_BOUNDS
 return {'computable':True,'meanRatio':ratio,'closedInterval':[lo,hi],'passed':lo<=ratio<=hi,'gridDiscretizationUpperBoundRelative':grid_bound,'statisticalEquivalenceClaim':False}

def source_baseline_map(admission:dict[str,Any])->dict[str,Any]:
 supplied=admission.get('reportSha256')
 if supplied!=ADMISSION_REPORT_SHA or supplied!=canon({k:v for k,v in admission.items() if k!='reportSha256'}): raise ValueError('source admission report identity/self-hash drift')
 if admission.get('sourceDatasetSha256')!=SOURCE_DATASET_SHA or admission.get('observedGeometryCount')!=39 or admission.get('expectedGeometryCount')!=39: raise ValueError('source training universe drift')
 rows=admission.get('geometryReports')
 if not isinstance(rows,list) or len(rows)!=39: raise ValueError('source geometry reports missing')
 return {r['geometryId']:r for r in rows}

def historical_stats(report:dict[str,Any],name:str)->dict[str,Any]:
 c=report['channels'][name]; vals=[float(x) for x in c['values']]
 return {'blockCount':int(c['blockCount']),'values':vals,'mean':sum(vals)/len(vals),'rsem':c.get('relativeStandardErrorOfMean'),'zeroHitBlockCount':int(c.get('zeroHitBlockCount',0)),'classification':c.get('classification')}

def method_stats(rows:list[dict[str,Any]])->dict[str,Any]:
 if len(rows)!=2 or sorted(r['replicate'] for r in rows)!=[1,2]: raise ValueError('method requires exact screening replicates 1,2')
 ordered=sorted(rows,key=lambda x:x['replicate']); channels={}
 for name in PRIMARY: channels[name]=stats([float(r['channels'][name]) for r in ordered])
 spr=[]
 for r in ordered:
  p=float(r['channels']['photopicLuminanceCdM2']); s=float(r['channels']['scotopicLuminanceScotCdM2']); spr.append(None if p<=0 else s/p)
 finite=[x for x in spr if x is not None]
 return {'channels':channels,'derivedScotopicPhotopicRatio':{'values':spr,'mean':sum(finite)/len(finite) if finite else None,'maxMinRatio':(max(finite)/min(finite) if len(finite)==2 and min(finite)>0 else None)},'zeroHitCaseCount':sum(1 for r in rows if r.get('zeroHit') is True),'screeningBlockCount':2,'inferentialVarianceClaim':False}

def all_ratio_pass(comp:dict[str,Any])->bool: return all(x['computable'] and x['passed'] for x in comp.values())
def any_ratio_fail(comp:dict[str,Any])->bool: return any(x['computable'] and not x['passed'] for x in comp.values())

def analyze(protocol:dict[str,Any],admission:dict[str,Any],evidence:dict[str,Any])->dict[str,Any]:
 if protocol.get('protocolSha256')!=PROTOCOL_SHA or canon({k:v for k,v in protocol.items() if k!='protocolSha256'})!=PROTOCOL_SHA: raise ValueError('protocol identity/self-hash drift')
 plan=protocol.get('analysisPlan',{})
 if plan.get('twoBlockUncertaintyInterpretation',{}).get('inferentialPValueOrZScoreAllowed') is not False or plan.get('grossMeanConsistencyScreen',{}).get('closedInterval')!=[0.5,2.0]: raise ValueError('analysis plan statistical boundary drift')
 if evidence.get('evidenceId')!='public-tier1-full-spectrum-estimator-pilot-normalized-evidence-v6' or evidence.get('protocolSha256')!=PROTOCOL_SHA or evidence.get('executionManifestSha256')!=EXEC_SHA or evidence.get('caseCount')!=44 or evidence.get('holdoutValuesRead') is not False: raise ValueError('normalized evidence identity/boundary drift')
 es=evidence.get('evidenceSha256')
 if es!=canon({k:v for k,v in evidence.items() if k!='evidenceSha256'}): raise ValueError('normalized evidence self-hash mismatch')
 base=source_baseline_map(admission); expected={c['caseId']:c for c in protocol['cases']}; rows=evidence.get('cases')
 if not isinstance(rows,list) or len(rows)!=44 or {r['caseId'] for r in rows}!=set(expected): raise ValueError('evidence case universe mismatch')
 for r in rows:
  e=expected[r['caseId']]
  for k in ('geometryId','method','replicate','seed','photonHistories'):
   if r.get(k)!=e.get(k): raise ValueError(f'evidence/protocol case mismatch: {r["caseId"]}.{k}')
  if r.get('importanceCenterNm')!=e.get('importanceCenterNm'): raise ValueError('importance center drift')
 by={}
 for r in rows: by.setdefault(r['geometryId'],[]).append(r)
 reports=[]
 for sel in protocol['selectedGeometries']:
  gid=sel['geometryId']; gro=by[gid]; br=base[gid]
  historical={n:historical_stats(br,n) for n in PRIMARY}
  finite_hist=[x['rsem'] for x in historical.values() if x['rsem'] is not None]
  hist_max=max(finite_hist) if len(finite_hist)==3 else None
  historical_rare=sel['historicalZeroHitCount']>0 or any(x['zeroHitBlockCount']>0 for x in historical.values())
  methods=[]
  vrows=[r for r in gro if r['method']=='reference-vroom-1nm']; vstat=method_stats(vrows) if vrows else None
  if vstat:
   hcomp={n:ratio_screen(vstat['channels'][n]['mean'],historical[n]['mean'],GRID_BOUND[n]) for n in PRIMARY}
   if vstat['zeroHitCaseCount']>0: cls='REFERENCE_RARE_EVENT_UNRESOLVED'
   elif historical_rare: cls='REFERENCE_FINITE_RARE_EVENT_SCREENING_ONLY'
   elif all_ratio_pass(hcomp): cls='REFERENCE_GROSSLY_CONSISTENT_WITH_HISTORICAL_ALIS'
   elif any_ratio_fail(hcomp): cls='GROSS_METHOD_DISAGREEMENT'
   else: cls='REFERENCE_SCREENING_UNRESOLVED'
   methods.append({'method':'reference-vroom-1nm','importanceCenterNm':None,'statistics':vstat,'historicalMeanRatioScreen':hcomp,'classification':cls})
  for center in sorted({r['importanceCenterNm'] for r in gro if r['method']=='alis-alt-importance'}):
   arows=[r for r in gro if r['method']=='alis-alt-importance' and r['importanceCenterNm']==center]; astat=method_stats(arows)
   hcomp={n:ratio_screen(astat['channels'][n]['mean'],historical[n]['mean']) for n in PRIMARY}
   refcomp={n:ratio_screen(astat['channels'][n]['mean'],vstat['channels'][n]['mean'],GRID_BOUND[n]) for n in PRIMARY} if vstat else None
   maxr=max((astat['channels'][n]['descriptiveTwoBlockRsem'] for n in PRIMARY if astat['channels'][n]['descriptiveTwoBlockRsem'] is not None),default=None)
   if astat['zeroHitCaseCount']>0:
    cls='RARE_EVENT_UNRESOLVED'
   elif historical_rare:
    if vstat and vstat['zeroHitCaseCount']==0 and refcomp and any_ratio_fail(refcomp): cls='GROSS_METHOD_DISAGREEMENT'
    elif vstat and vstat['zeroHitCaseCount']==0 and refcomp and all_ratio_pass(refcomp): cls='RARE_EVENT_TWO_METHOD_FINITE_SCREENING_REQUIRES_CONFIRMATION'
    else: cls='RARE_EVENT_UNRESOLVED'
   elif any_ratio_fail(hcomp): cls='GROSS_METHOD_DISAGREEMENT'
   elif all_ratio_pass(hcomp) and maxr is not None and maxr<=0.08: cls='LOW_TWO_BLOCK_RSEM_SCREENING_CANDIDATE'
   elif all_ratio_pass(hcomp) and hist_max is not None and maxr is not None and maxr<=0.5*hist_max: cls='SCREENING_STRONG_VARIANCE_GAIN'
   else: cls='NO_CLEAR_SCREENING_GAIN'
   methods.append({'method':'alis-alt-importance','importanceCenterNm':center,'statistics':astat,'historicalMeanRatioScreen':hcomp,'referenceVroomMeanRatioScreen':refcomp,'classification':cls})
  reports.append({'geometryId':gid,'phenotype':sel['phenotype'],'historicalImportanceCenterNm':sel['historicalAlisImportanceCenterNm'],'historicalChannels':historical,'historicalMaxPrimaryRsem':hist_max,'historicalZeroHitCount':sel['historicalZeroHitCount'],'historicalRareEventBoundary':historical_rare,'methodReports':methods})
 counts={}
 for g in reports:
  for m in g['methodReports']: counts[m['classification']]=counts.get(m['classification'],0)+1
 out={'schemaVersion':1,'analysisId':ANALYSIS_ID,'status':'PILOT_SCREENING_ANALYZED_NO_AUTOMATIC_ESTIMATOR_SELECTION','protocolSha256':PROTOCOL_SHA,'executionManifestSha256':EXEC_SHA,'sourceTrainingDatasetSha256':SOURCE_DATASET_SHA,'sourceAdmissionReportSha256':ADMISSION_REPORT_SHA,'normalizedEvidenceSha256':es,'geometryCount':len(reports),'classificationCounts':counts,'geometryReports':reports,'statisticalInferenceClaim':False,'twoBlockRsemFinalPrecisionClaim':False,'automaticGlobalEstimatorSelection':False,'continuationAuthorized':False,'fittingAuthorized':False,'holdoutOpeningAuthorized':False,'productionAuthorization':False}
 out['analysisSha256']=canon(out); return out

def main()->int:
 ap=argparse.ArgumentParser(); ap.add_argument('--protocol',type=Path,required=True); ap.add_argument('--admission-report',type=Path,required=True); ap.add_argument('--evidence',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
 try:
  v=analyze(load(a.protocol),load(a.admission_report),load(a.evidence)); a.output.write_text(json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+'\n'); print(json.dumps({'status':v['status'],'analysisSha256':v['analysisSha256'],'classificationCounts':v['classificationCounts']},indent=2)); return 0
 except Exception as e: print(json.dumps({'status':'REFUSED','reason':str(e)},indent=2)); return 2
if __name__=='__main__': raise SystemExit(main())
