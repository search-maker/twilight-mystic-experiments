#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, math, statistics
from pathlib import Path

CHANNELS=('photopicLuminanceCdM2','scotopicLuminanceScotCdM2','johnsonVEffectiveRadiance_mW_m2_nm_sr')
MODEL_SHA='f9202b45a6540416b3cb021425b40da27e2c9adc966edd81d3608c55826a162a'
OLD_SHA='c4902eb3c2ba67b12dc4ef2b9cefb67c5963a6abc104708a73b2aab5dd0163b9'
class Refusal(RuntimeError):pass
def req(c,m):
 if not c:raise Refusal(m)
def load(p):
 x=json.loads(Path(p).read_text());req(isinstance(x,dict),f'object required: {p}');return x
def module(name,p):
 s=importlib.util.spec_from_file_location(name,p);req(s and s.loader,f'cannot load {p}');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def dist(a,b):return math.sqrt(sum((x-y)*(x-y) for x,y in zip(a,b)))
def old_basis(g):
 s=(g['sunDepressionDeg']-2)/8.5;a=math.sin(math.radians(g['targetAltitudeDeg']));c=math.cos(math.radians(g['relativeAzimuthDeg']));e=g['observerElevationM']/2500;o=math.log(g['aod550']/0.05)/math.log(8);return [1,s,a,c,e,o,s*s,a*a,c*c,o*o,s*a,s*c,s*o,a*c,a*o,c*o]
def old_coord(g):return [(g['sunDepressionDeg']-2)/8.5,(g['targetAltitudeDeg']-5)/75,(math.cos(math.radians(g['relativeAzimuthDeg']))+1)/2,g['observerElevationM']/2500,(g['aod550']-.05)/.35]
def old_predict(m,g):
 b=old_basis(g);c=m['baseModel']['primary']['coefficients'];out=[sum(b[i]*c[i][j] for i in range(16)) for j in range(3)];q=old_coord(g);rows=sorted(((dist(x,q),i) for i,x in enumerate(m['residualCoordinates'])),key=lambda x:(x[0],x[1]))
 if rows[0][0]==0:corr=m['residualTargets'][rows[0][1]]
 else:
  rows=rows[:m['residualNeighbors']];ws=[1/(d**m['residualPower']) for d,i in rows];sw=sum(ws);corr=[sum(w*m['residualTargets'][i][j] for w,(d,i) in zip(ws,rows))/sw for j in range(3)]
 return [out[j]+m['residualShrinkage']*corr[j] for j in range(3)]
def extension_coord(g):
 t=(g['targetAltitudeDeg']-80)/10;c=math.cos(math.radians(g['relativeAzimuthDeg']));ce=1-(1-c)*(1-t);return [(g['sunDepressionDeg']-2)/8.5,t,(ce+1)/2,g['observerElevationM']/2500,(g['aod550']-.05)/.35]
def effective_geometry(g):
 t=(g['targetAltitudeDeg']-80)/10;c=math.cos(math.radians(g['relativeAzimuthDeg']));ce=max(-1,min(1,1-(1-c)*(1-t)));x=dict(g);x['relativeAzimuthDeg']=math.degrees(math.acos(ce));return x
def predict(old,ext,g):
 if g['targetAltitudeDeg']<=80:return old_predict(old,g)
 t=(g['targetAltitudeDeg']-80)/10;base=old_predict(old,effective_geometry(g));q=extension_coord(g);rows=sorted(((dist(r['coordinate'],q),i,r) for i,r in enumerate(ext['trainingFit'])),key=lambda x:(x[0],x[1]));k=ext['selectedSpec']['neighbors']
 if rows[0][0]==0:corr=rows[0][2]['normalizedPrimaryLogCorrectionPerUnitT']
 else:
  rows=rows[:k];ws=[1/(d**ext['selectedSpec']['power']) for d,i,r in rows];sw=sum(ws);corr=[sum(w*r['normalizedPrimaryLogCorrectionPerUnitT'][j] for w,(d,i,r) in zip(ws,rows))/sw for j in range(3)]
 return [base[j]+ext['selectedSpec']['shrinkage']*t*corr[j] for j in range(3)]
def mean_se(v):return statistics.fmean(v),statistics.stdev(v)/math.sqrt(len(v))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repo-root',type=Path,required=True);ap.add_argument('--manifest',type=Path,required=True);ap.add_argument('--results-root',type=Path,required=True);ap.add_argument('--old-model',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();root=a.repo_root.resolve()
 manifest=load(a.manifest);req(manifest['manifestSha256']=='4a0a91e07c6a1f2c9f4870da70eda55664231e645d4050e78f72b46e22eb6394','manifest drift');req(manifest['sourceModelCanonicalSha256']==MODEL_SHA,'frozen extension model drift')
 ext=load(root/manifest['sourceTrainingModelPath']);req(ext['modelCanonicalSha256']==MODEL_SHA and ext['status']=='TRAINING_ONLY_FROZEN_PENDING_FRESH_HOLDOUT','extension model identity drift');req(ext['holdoutValuesOpened'] is False,'model file already claims holdout opened')
 old_art=load(a.old_model);old=old_art['model'];req(old['modelCanonicalSha256']==OLD_SHA,'old model drift')
 spectral=module('zenith_channel_analysis',root/'experiments/level-b-zenith-expansion-acquisition-v1/analyze_channels_v3.py');common=spectral.load_common(root)
 by={};case_ids=set();seeds=set()
 for rp in a.results_root.rglob('case-result.json'):
  r=load(rp)
  if r.get('status')!='COMPLETED':continue
  req(r['caseId'] not in case_ids and r['seed'] not in seeds,'duplicate case/seed');case_ids.add(r['caseId']);seeds.add(r['seed']);req(r['solverExecutionCount']==1 and r['syntaxCheckCount']==1,'execution-count drift')
  sp=rp.with_name('mc.rad.spc');wl,rad,rawsha=spectral.parse_spectrum(sp);req(rawsha==r['radianceOutputSha256'],'raw spectrum hash drift');ch=common.channels(wl,rad);by.setdefault(r['geometryId'],[]).append({'block':r['block'],'channels':ch,'caseId':r['caseId'],'seed':r['seed']})
 req(len(case_ids)==32 and seeds==set(range(2240000001,2240000033)),'complete fresh 32-case universe required');req(set(by)=={g['geometryId'] for g in manifest['geometries']},'geometry universe drift');req(all(len(v)==4 for v in by.values()),'four blocks per holdout required')
 cases=[];all_abs=[];support_ok=True;per_channel={k:{'signed':[],'abs':[],'norm':[]} for k in CHANNELS};gmap={g['geometryId']:g for g in manifest['geometries']}
 for gid in sorted(by):
  rows=sorted(by[gid],key=lambda x:x['block']);g=gmap[gid];truth=[];relse=[];means={};ses={}
  for key in CHANNELS:
   vals=[float(x['channels'][key]) for x in rows];req(all(math.isfinite(v) and v>0 for v in vals),'positive channel values required');mu,se=mean_se(vals);means[key]=mu;ses[key]=se;truth.append(math.log(mu));relse.append(se/mu)
  pred=predict(old,ext,g);q=extension_coord(g);nearest=min(dist(q,r['coordinate']) for r in ext['trainingFit']);supported=nearest<=manifest['freshHoldoutGates']['validatedSupportNearestDistanceMaxInclusive'];support_ok=support_ok and supported
  errs=[]
  for j,key in enumerate(CHANNELS):
   signed=pred[j]-truth[j];ab=abs(signed);norm=ab/math.sqrt(manifest['freshHoldoutGates']['surrogateLogErrorBudgetOneSigma']**2+relse[j]**2);per_channel[key]['signed'].append(signed);per_channel[key]['abs'].append(ab);per_channel[key]['norm'].append(norm);all_abs.append(ab);errs.append(ab)
  cases.append({'geometryId':gid,'geometry':g,'predictedPrimaryLogs':pred,'truthChannelMeans':means,'truthChannelStandardErrors':ses,'absoluteLogErrors':dict(zip(CHANNELS,errs)),'nearestExtensionTrainingDistance':nearest,'supportedByFrozenCandidateRule':supported})
 gates=manifest['freshHoldoutGates'];channel_summary={};allpass=True
 for key in CHANNELS:
  d=per_channel[key];s={'absoluteMeanSignedLogBias':abs(statistics.fmean(d['signed'])),'medianAbsoluteLogError':statistics.median(d['abs']),'worstAbsoluteLogError':max(d['abs']),'worstUncertaintyNormalizedError':max(d['norm'])};s['passes']=s['absoluteMeanSignedLogBias']<=gates['positiveChannelAbsoluteMeanSignedLogBiasMax'] and s['medianAbsoluteLogError']<=gates['positiveChannelMedianAbsoluteLogErrorMax'] and s['worstAbsoluteLogError']<=gates['positiveChannelWorstAbsoluteLogErrorMax'] and s['worstUncertaintyNormalizedError']<=gates['positiveChannelWorstUncertaintyNormalizedErrorMax'];channel_summary[key]=s;allpass=allpass and s['passes']
 agg=statistics.fmean(all_abs);allpass=allpass and agg<=gates['primaryAggregateMeanAbsoluteLogErrorMax'] and support_ok
 out={'schemaVersion':1,'evaluationId':'level-b-v3-zenith-extension-fresh-holdout-v1','status':'PASS_FROZEN_FRESH_HOLDOUT' if allpass else 'FAIL_FROZEN_FRESH_HOLDOUT_NO_SUPPORT_EXPANSION','sourceModelCanonicalSha256':MODEL_SHA,'sourceManifestSha256':manifest['manifestSha256'],'caseCount':32,'geometryCount':8,'aggregatePrimaryMeanAbsoluteLogError':agg,'channelSummary':channel_summary,'supportPass':support_ok,'cases':cases,'frozenGates':gates,'retuningPerformed':False,'modelChangedAfterHoldoutOpening':False,'supportExpansionAuthorized':False,'productionAuthorized':False}
 a.output.mkdir(parents=True,exist_ok=True);(a.output/'fresh-holdout-evaluation-v1.json').write_text(json.dumps(out,indent=2,sort_keys=True,allow_nan=False)+'\n');print(json.dumps({'status':out['status'],'aggregatePrimaryMeanAbsoluteLogError':agg,'supportPass':support_ok,'channelSummary':channel_summary},sort_keys=True));return 0 if allpass else 2
if __name__=='__main__':raise SystemExit(main())
