#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math, statistics
from pathlib import Path
from typing import Any

ANALYSIS_ID='public-tier1-full-spectrum-estimator-pilot-analysis-v5'
ACQUISITION_PROTOCOL_SHA='7ca0923204452ab203249dfd060dd5fef5465c48a20ba529c0a20748e0152434'
ANALYSIS_PROTOCOL_SHA='628697232dde05bd024dd4575ec5874091342bd807c2c51873659b4babd24dcf'
EXEC_SHA='be81c717cd943415ac51dc2b5356010b3d584b5279228c525d2defccc4680e0f'
SOURCE_DATASET_SHA='42478d099efea7392f5558716571400dc84ee28de5df1e22f85e8031d2138c41'
ADMISSION_REPORT_SHA='a043fa6c0a5e7ec282d887a4febe01277e0a0a20c82bff65ccb127705b40e0cf'
PRIMARY=('photopicLuminanceCdM2','scotopicLuminanceScotCdM2','johnsonVEffectiveRadiance_mW_m2_nm_sr')
RATIO_BOUNDS=(0.5,2.0)
VARIANCE_PROXY_MAX=0.5
GRID_BOUND={'photopicLuminanceCdM2':0.0011168248714839013,'scotopicLuminanceScotCdM2':0.0020320382260645697,'johnsonVEffectiveRadiance_mW_m2_nm_sr':0.0018607417688334404}

def canon(v:Any)->str:
 return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def load(p:Path)->dict[str,Any]:
 v=json.loads(p.read_text())
 if not isinstance(v,dict): raise ValueError(f'expected object: {p}')
 return v

def stats(values:list[float])->dict[str,Any]:
 if len(values)!=2 or any((not math.isfinite(x) or x<0) for x in values):
  raise ValueError('each fresh screening method requires exactly two finite nonnegative blocks')
 zero=any(x==0 for x in values); mean=sum(values)/2
 if zero or mean<=0: rsem=None; sd=None; relsd=None
 else:
  sd=statistics.stdev(values); rsem=sd/math.sqrt(2)/mean; relsd=sd/mean
 total=sum(values); den=sum(x*x for x in values)
 eff=(total*total/den) if den>0 else 0.0
 return {'blockCount':2,'values':values,'mean':mean,'sampleStd':sd,'relativeSampleStd':relsd,'descriptiveTwoBlockRsem':rsem,'zeroHitPresent':zero,'effectiveBlockCount':eff,'maximumBlockFraction':(max(values)/total if total>0 else None),'inferentialUsePermitted':False}

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
 first=stats(vals[:2])
 return {
  'blockCount':int(c['blockCount']),'values':vals,'mean':sum(vals)/len(vals),
  'rsem':c.get('relativeStandardErrorOfMean'),'zeroHitBlockCount':int(c.get('zeroHitBlockCount',0)),
  'classification':c.get('classification'),'firstTwoScreening':first,
 }

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

def same_n_variance_screen(fresh:dict[str,Any],historical:dict[str,Any],problem_channels:list[str])->dict[str,Any]:
 per={}; applicable=[]
 for name in PRIMARY:
  fr=fresh['channels'][name]['descriptiveTwoBlockRsem']; hr=historical[name]['firstTwoScreening']['descriptiveTwoBlockRsem']
  if fr is None or hr is None or hr<=0:
   per[name]={'computable':False,'freshTwoBlockRsem':fr,'historicalFirstTwoBlockRsem':hr,'varianceProxyRatio':None,'passed':False if name in problem_channels else None}
  else:
   ratio=(fr/hr)**2
   per[name]={'computable':True,'freshTwoBlockRsem':fr,'historicalFirstTwoBlockRsem':hr,'varianceProxyRatio':ratio,'maximumAllowedVarianceProxyRatio':VARIANCE_PROXY_MAX,'passed':ratio<=VARIANCE_PROXY_MAX if name in problem_channels else None}
  if name in problem_channels: applicable.append(name)
 usable=bool(applicable) and all(per[n]['computable'] for n in applicable)
 passed=usable and all(per[n]['passed'] is True for n in applicable)
 return {'formula':'(freshTwoBlockRsem / historicalFirstTwoBlockRsem)^2','sameBlockCount':2,'samePerBlockPhotonHistoriesRequired':True,'historicalProblemChannels':applicable,'perChannel':per,'allProblemChannelsComputable':usable,'passed':passed,'inferentialClaim':False}

def validate_analysis_protocol(ap:dict[str,Any], acquisition:dict[str,Any], admission:dict[str,Any])->dict[str,Any]:
 if ap.get('analysisProtocolSha256')!=ANALYSIS_PROTOCOL_SHA or canon({k:v for k,v in ap.items() if k!='analysisProtocolSha256'})!=ANALYSIS_PROTOCOL_SHA: raise ValueError('screening analysis protocol identity/self-hash drift')
 if ap.get('acquisitionProtocolSha256')!=ACQUISITION_PROTOCOL_SHA or ap.get('executionManifestSha256')!=EXEC_SHA or ap.get('sourceAdmissionReportSha256')!=ADMISSION_REPORT_SHA: raise ValueError('screening analysis protocol source binding drift')
 if acquisition.get('protocolSha256')!=ACQUISITION_PROTOCOL_SHA or canon({k:v for k,v in acquisition.items() if k!='protocolSha256'})!=ACQUISITION_PROTOCOL_SHA: raise ValueError('acquisition protocol identity/self-hash drift')
 if ap.get('caseDesignUnchanged',{}).get('casesCanonicalSha256')!=canon(acquisition.get('cases')): raise ValueError('analysis/acquisition case design drift')
 baseline=ap.get('historicalFirstTwoScreeningBaseline',{}); rows=baseline.get('geometryBaselines')
 if not isinstance(rows,list) or baseline.get('geometryBaselinesCanonicalSha256')!=canon(rows): raise ValueError('frozen first-two baseline self-hash drift')
 # Independently reproduce the frozen first-two baseline from the immutable admission report.
 source=source_baseline_map(admission); got=[]
 selected={x['geometryId']:x for x in acquisition['selectedGeometries']}
 for frozen in rows:
  gid=frozen['geometryId']; rep=source.get(gid); sel=selected.get(gid)
  if rep is None or sel is None: raise ValueError(f'frozen baseline geometry missing: {gid}')
  channels={}; problem=[]; rare=False
  for name in PRIMARY:
   c=rep['channels'][name]; vals=[float(x) for x in c['values']]; st=stats(vals[:2]); full=c.get('relativeStandardErrorOfMean'); z=int(c.get('zeroHitBlockCount',0))
   if z>0: rare=True
   if z>0 or (full is not None and float(full)>0.08): problem.append(name)
   channels[name]={'firstTwoValues':vals[:2],'firstTwoMean':st['mean'],'firstTwoSampleStd':st['sampleStd'],'firstTwoDescriptiveRsem':st['descriptiveTwoBlockRsem'],'firstTwoZeroHitCount':1 if st['zeroHitPresent'] else 0,'fullHistoryBlockCount':int(c['blockCount']),'fullHistoryMean':sum(vals)/len(vals),'fullHistoryRsem':full,'fullHistoryZeroHitCount':z}
  got.append({'geometryId':gid,'historicalBlockNumbers':[1,2],'perBlockPhotonHistories':int(sel['photonHistoriesPerFreshCase']),'freshScreeningPerBlockPhotonHistories':int(sel['photonHistoriesPerFreshCase']),'sameNAndSamePhotonCountComparison':True,'historicalRareEventBoundary':rare,'historicalProblemChannels':problem,'channels':channels})
 if canon(got)!=baseline.get('geometryBaselinesCanonicalSha256'): raise ValueError('immutable admission report no longer reproduces frozen first-two baseline')
 return {r['geometryId']:r for r in rows}

def analyze(acquisition:dict[str,Any],analysis_protocol:dict[str,Any],admission:dict[str,Any],evidence:dict[str,Any])->dict[str,Any]:
 frozen_baseline=validate_analysis_protocol(analysis_protocol,acquisition,admission)
 if evidence.get('evidenceId')!='public-tier1-full-spectrum-estimator-pilot-normalized-evidence-v6' or evidence.get('protocolSha256')!=ACQUISITION_PROTOCOL_SHA or evidence.get('executionManifestSha256')!=EXEC_SHA or evidence.get('caseCount')!=44 or evidence.get('holdoutValuesRead') is not False: raise ValueError('normalized evidence identity/boundary drift')
 es=evidence.get('evidenceSha256')
 if es!=canon({k:v for k,v in evidence.items() if k!='evidenceSha256'}): raise ValueError('normalized evidence self-hash mismatch')
 base=source_baseline_map(admission); expected={c['caseId']:c for c in acquisition['cases']}; rows=evidence.get('cases')
 if not isinstance(rows,list) or len(rows)!=44 or {r['caseId'] for r in rows}!=set(expected): raise ValueError('evidence case universe mismatch')
 for r in rows:
  e=expected[r['caseId']]
  for k in ('geometryId','method','replicate','seed','photonHistories'):
   if r.get(k)!=e.get(k): raise ValueError(f'evidence/acquisition case mismatch: {r["caseId"]}.{k}')
  if r.get('importanceCenterNm')!=e.get('importanceCenterNm'): raise ValueError('importance center drift')
 by={}
 for r in rows: by.setdefault(r['geometryId'],[]).append(r)
 reports=[]
 for sel in acquisition['selectedGeometries']:
  gid=sel['geometryId']; gro=by[gid]; br=base[gid]; frozen=frozen_baseline[gid]
  historical={n:historical_stats(br,n) for n in PRIMARY}
  problem=list(frozen['historicalProblemChannels'])
  historical_rare=bool(frozen['historicalRareEventBoundary'])
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
   varscreen=same_n_variance_screen(astat,historical,problem)
   if astat['zeroHitCaseCount']>0:
    cls='RARE_EVENT_UNRESOLVED' if historical_rare else 'NO_CLEAR_SCREENING_GAIN'
   elif historical_rare:
    if vstat and vstat['zeroHitCaseCount']==0 and refcomp and any_ratio_fail(refcomp): cls='GROSS_METHOD_DISAGREEMENT'
    elif vstat and vstat['zeroHitCaseCount']==0 and refcomp and all_ratio_pass(refcomp): cls='RARE_EVENT_TWO_METHOD_FINITE_SCREENING_REQUIRES_CONFIRMATION'
    else: cls='RARE_EVENT_UNRESOLVED'
   elif any_ratio_fail(hcomp): cls='GROSS_METHOD_DISAGREEMENT'
   elif all_ratio_pass(hcomp) and maxr is not None and maxr<=0.08: cls='LOW_TWO_BLOCK_RSEM_SCREENING_CANDIDATE'
   elif all_ratio_pass(hcomp) and varscreen['passed']: cls='SCREENING_VARIANCE_GAIN_ON_HISTORICAL_PROBLEM_CHANNELS'
   else: cls='NO_CLEAR_SCREENING_GAIN'
   methods.append({'method':'alis-alt-importance','importanceCenterNm':center,'statistics':astat,'historicalMeanRatioScreen':hcomp,'referenceVroomMeanRatioScreen':refcomp,'sameNVarianceGainScreen':varscreen,'classification':cls})
  reports.append({'geometryId':gid,'phenotype':sel['phenotype'],'historicalImportanceCenterNm':sel['historicalAlisImportanceCenterNm'],'historicalChannels':historical,'historicalProblemChannels':problem,'historicalZeroHitCount':sel['historicalZeroHitCount'],'historicalRareEventBoundary':historical_rare,'frozenFirstTwoBaseline':frozen,'methodReports':methods})
 counts={}
 for g in reports:
  for m in g['methodReports']: counts[m['classification']]=counts.get(m['classification'],0)+1
 out={'schemaVersion':1,'analysisId':ANALYSIS_ID,'status':'PILOT_SCREENING_ANALYZED_NO_AUTOMATIC_ESTIMATOR_SELECTION','acquisitionProtocolSha256':ACQUISITION_PROTOCOL_SHA,'screeningAnalysisProtocolSha256':ANALYSIS_PROTOCOL_SHA,'executionManifestSha256':EXEC_SHA,'sourceTrainingDatasetSha256':SOURCE_DATASET_SHA,'sourceAdmissionReportSha256':ADMISSION_REPORT_SHA,'normalizedEvidenceSha256':es,'geometryCount':len(reports),'classificationCounts':counts,'geometryReports':reports,'statisticalInferenceClaim':False,'twoBlockRsemFinalPrecisionClaim':False,'fullAdaptiveHistoricalRsemUsedForVarianceGainThreshold':False,'automaticGlobalEstimatorSelection':False,'continuationAuthorized':False,'fittingAuthorized':False,'holdoutOpeningAuthorized':False,'productionAuthorization':False}
 out['analysisSha256']=canon(out); return out

def main()->int:
 ap=argparse.ArgumentParser(); ap.add_argument('--acquisition-protocol',type=Path,required=True); ap.add_argument('--analysis-protocol',type=Path,required=True); ap.add_argument('--admission-report',type=Path,required=True); ap.add_argument('--evidence',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
 try:
  v=analyze(load(a.acquisition_protocol),load(a.analysis_protocol),load(a.admission_report),load(a.evidence)); a.output.write_text(json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+'\n'); print(json.dumps({'status':v['status'],'analysisSha256':v['analysisSha256'],'classificationCounts':v['classificationCounts']},indent=2)); return 0
 except Exception as e:
  print(json.dumps({'status':'REFUSED','reason':str(e)},indent=2)); return 2
if __name__=='__main__': raise SystemExit(main())
