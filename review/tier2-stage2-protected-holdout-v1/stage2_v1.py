#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math, re, subprocess
from pathlib import Path
from typing import Any
import numpy as np

CONTRACT_ID='level-b-v1-tier2-stage2-protected-holdout-v1'
CAMPAIGN='review/tier2-core-campaign-contract-v1/tier2-core-campaign-contract-v1.json'
CAMPAIGN_BLOB='dc69f67829cf7412e8e9374f005d92842bd500ca'
MODEL_BIND='review/core-training-surrogate-model-freeze-result-v1/result-v1.json'
MODEL_BIND_BLOB='3782ebee0af6d1496e9598a6e48623af95fc332a'
GRID_SHA='b5fae53c1cc88c7f3de6e3689bc25e4a36c54033d1d1bfd6169482f30cc5b477'
CHANNELS=('photopicLuminanceCdM2','scotopicLuminanceScotCdM2','johnsonVEffectiveRadiance_mW_m2_nm_sr')
FEATURES=('sunDepressionDeg','targetAltitudeDeg','relativeAzimuthDeg','observerElevationM','aod550')
class Refusal(RuntimeError): pass

def req(c:bool,m:str)->None:
    if not c: raise Refusal(m)
def canon(v:Any)->str: return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def sha_bytes(b:bytes)->str: return hashlib.sha256(b).hexdigest()
def sha_file(p:Path)->str: return sha_bytes(p.read_bytes())
def load(p:Path)->dict[str,Any]:
    x=json.loads(p.read_text(encoding='utf-8')); req(isinstance(x,dict),f'object required: {p}'); return x
def write(p:Path,v:Any)->None:
    p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')

def expected_cases(p:dict[str,Any])->list[dict[str,Any]]:
    out=[]
    for g in p['stage2Scope']['geometries']:
        seeds=g['reservedSeeds']; req(len(seeds)==4,'four seeds per geometry required')
        for block,seed in enumerate(seeds,1):
            out.append({'caseId':f"tier2-core-v1-{g['geometryId']}-b{block}",'geometryId':g['geometryId'],'block':block,'seed':int(seed),'photonHistories':int(g['photonHistoriesPerBlock']),'alisSpectralImportanceSamplingNm':float(g['alisSpectralImportanceSamplingNm'])})
    return out

def validate_contract(p:dict[str,Any])->None:
    req((p.get('schemaVersion'),p.get('contractId'),p.get('status'),p.get('governance'))==(1,CONTRACT_ID,'REVIEW_ONLY_PROTECTED_HOLDOUT_EXECUTION_AND_EVALUATION_FREEZE_NO_AUTHORIZATION_NO_VALUES_OPENED','MYSTIC-STATE-0067'),'contract identity drift')
    req(p.get('sourceMainAtFreeze')=='7ce21ec9c13be9bf901784992a7b6c7e82f3c364','source main drift')
    s=p.get('sourceBindings') or {}
    req((s.get('campaignContractGitBlobSha'),s.get('modelResultBindingGitBlobSha'))==(CAMPAIGN_BLOB,MODEL_BIND_BLOB),'reviewed source blob drift')
    req((s.get('modelArtifactId'),s.get('modelArtifactDigest'),s.get('modelCanonicalSha256'))==(9208482214,'sha256:f8fc1290d16ebd6d5712706fafadd10d8a67af0b6bc18944349868d2c07fabf1','bcdcc41f2a3af718f00d81a3b41f4ba63674fdc3e29f8562875b0d5401ad493a'),'model identity drift')
    req((s.get('representationArtifactId'),s.get('representationArtifactDigest'),s.get('representationPackageSha256'))==(9208203541,'sha256:2fe50ed674155f440322c92d28877f5c022f0cc5fa13e1e601596a9902482815','2491ac91ed924f2ba69b37ea20f48d63f51d41146cd9fe50e0bd63bfb315a763'),'representation identity drift')
    req((s.get('ordinal20SalvageArtifactId'),s.get('consumedTrainingSeedLedgerSha256'),s.get('latestConsumedScientificOrdinalAtFreeze'))==(9206827621,'aeddc2a1516ba7b7c8430d9d95866da5d18756123d00bff6ef7948ddf8fe1319',20),'consumed-seed/ordinal source drift')
    q=p.get('stage2Scope') or {}; gs=q.get('geometries') or []
    req((q.get('stageId'),q.get('geometryCount'),q.get('caseCount'),q.get('blocksPerGeometry'),q.get('configuredPhotonHistories'))==('PROTECTED_HOLDOUT_AFTER_MODEL_FREEZE',6,24,4,720000000),'stage2 accounting drift')
    req([g.get('geometryId') for g in gs]==['train-0050','train-0060','train-0065','train-0070','train-0080','train-0090'],'holdout geometry identity/order drift')
    cases=expected_cases(p); req(len(cases)==24 and len({x['caseId'] for x in cases})==24 and len({x['seed'] for x in cases})==24,'case/seed uniqueness drift')
    expected_seeds={1900000001,1900000002,1900000003,1900000004,1900000021,1900000022,1900000023,1900000024,1900000033,1900000034,1900000035,1900000036,1900000045,1900000046,1900000047,1900000048,1900000065,1900000066,1900000067,1900000068,1900000085,1900000086,1900000087,1900000088}
    req({x['seed'] for x in cases}==expected_seeds,'reserved seed set drift'); req(sum(x['photonHistories'] for x in cases)==720000000,'photon accounting drift')
    for g in gs:
        req(2.0<=float(g['sunDepressionDeg'])<=10.5 and 5.0<=float(g['targetAltitudeDeg'])<=80.0 and 0<=float(g['relativeAzimuthDeg'])<=180 and 0<=float(g['observerElevationM'])<=2500 and 0.05<=float(g['aod550'])<=0.4,'holdout geometry outside frozen design box')
    m=p.get('modelAndEvaluation') or {}
    req((m.get('selectedFamilyId'),m.get('selectedRidge'),m.get('representationFeatureCount'),m.get('mandatoryIntegratedChannelCount'),m.get('nullspacePcaComponentCount'))==('ridge-physical-compact',0.001,13,3,10),'model/representation freeze drift')
    req((m.get('positiveChannelAbsoluteMeanSignedLogBiasMax'),m.get('positiveChannelMedianAbsoluteLogErrorMax'),m.get('positiveChannelWorstAbsoluteLogErrorMax'),m.get('positiveChannelWorstUncertaintyNormalizedErrorMax'))==(0.08,0.15,0.35,3.0),'primary DoD drift')
    req((m.get('surrogateLogErrorBudgetOneSigma'),m.get('aggregatePrimaryMeanAbsoluteLogErrorMustBeAtMostFractionOfFrozenTrainingMeanBaseline'))==(0.12,0.7),'uncertainty/baseline DoD drift')
    req((m.get('shapeMedianPerCaseNrmseMax'),m.get('shapeWorstPerCaseNrmseMax'),m.get('shapeWorstSingleCoefficientNormalizedErrorMax'))==(0.75,1.25,3.0),'shape DoD drift')
    req(m.get('p90OrP95PrincipalMetricAllowed') is False and m.get('noRetuningAfterHoldoutOpening') is True,'evaluation semantics drift')
    b=p.get('boundaries') or {}
    for k in ('reviewMergeAuthorizesScience','scientificOrdinalAllocated','protectedHoldoutOpeningAuthorized','holdoutValuesMayBeRead','scientificSolverExecutionAuthorized','stage2Authorized','modelRetuningAuthorized','productionPromotionAuthorized','workerBLaneReactivated','workerCLaneReactivated'):
        req(b.get(k) is False,f'closed review boundary opened: {k}')

def validate_review_sources(root:Path,p:dict[str,Any])->None:
    validate_contract(p)
    for path,want in ((CAMPAIGN,CAMPAIGN_BLOB),(MODEL_BIND,MODEL_BIND_BLOB)):
        got=subprocess.check_output(['git','rev-parse',f'HEAD:{path}'],cwd=root,text=True).strip(); req(got==want,f'git blob drift: {path}')
    campaign=load(root/CAMPAIGN); req(campaign.get('contractSha256')==p['sourceBindings']['campaignContractSha256'],'campaign content identity drift')
    cgs={g['geometryId']:g for g in campaign['geometryManifest'] if g.get('role')=='protected-holdout'}; req(set(cgs)==set(g['geometryId'] for g in p['stage2Scope']['geometries']),'campaign protected holdout set drift')
    for g in p['stage2Scope']['geometries']:
        c=cgs[g['geometryId']]
        for k in ('sourceIndex','sunDepressionDeg','targetAltitudeDeg','relativeAzimuthDeg','observerElevationM','aod550','alisSpectralImportanceSamplingNm','photonHistoriesPerBlock'): req(c.get(k)==g.get(k),f'campaign geometry drift {g["geometryId"]}:{k}')
        req(c.get('executionStage')=='PROTECTED_HOLDOUT_AFTER_MODEL_FREEZE','campaign stage drift')
    mb=load(root/MODEL_BIND); req(mb.get('frozenModel',{}).get('modelCanonicalSha256')==p['sourceBindings']['modelCanonicalSha256'],'model result binding drift')
    req(mb.get('boundaries',{}).get('holdoutValuesMayBeRead') is False,'model binding unexpectedly opened holdout')

def parse_spectrum(path:Path)->tuple[np.ndarray,np.ndarray,str]:
    toks=[]; vals=[]; data=path.read_bytes()
    for line in data.decode('utf-8',errors='strict').splitlines():
        q=line.split()
        if not q: continue
        req(len(q)>=2 and re.fullmatch(r'[0-9]+\.[0-9]{5}',q[0]) is not None,f'spectrum serialization drift: {path}')
        row=[float(x) for x in q]; req(all(math.isfinite(x) for x in row) and all(x>=0 for x in row[1:]),f'invalid spectrum value: {path}'); toks.append(q[0]); vals.append(row[-1])
    req(len(toks)==8001 and toks[0]=='380.00000' and toks[-1]=='780.00000',f'spectrum grid count/endpoints drift: {path}')
    req(sha_bytes(('\n'.join(toks)+'\n').encode())==GRID_SHA,f'spectrum token grid drift: {path}')
    return np.asarray([float(x) for x in toks],dtype=np.float64),np.asarray(vals,dtype=np.float64),sha_bytes(data)

def projection_residual(y:np.ndarray,W:np.ndarray)->tuple[np.ndarray,np.ndarray]:
    ch=W@y; req(ch[0]>0 and np.all(np.isfinite(ch)),'nonpositive/nonfinite direct primary channel'); x=y/ch[0]; proj=W.T@np.linalg.solve(W@W.T,W@x); r=x-proj; req(float(np.max(np.abs(W@r)))<1e-9,'direct nullspace projection drift'); return r,ch

def stats(a:np.ndarray)->dict[str,float|None]:
    req(a.ndim==1 and len(a)==4 and np.all(np.isfinite(a)),'exact four finite blocks required'); mean=float(np.mean(a)); sd=float(np.std(a,ddof=1)); sem=sd/2.0; return {'mean':mean,'sampleStd':sd,'standardError':sem,'relativeStandardError':abs(sem/mean) if mean!=0 else None}

def physical_basis(g:dict[str,Any])->np.ndarray:
    sun=float(g['sunDepressionDeg']); alt=float(g['targetAltitudeDeg']); az=float(g['relativeAzimuthDeg']); elev=float(g['observerElevationM']); aod=float(g['aod550']); req(aod>0,'positive AOD required')
    s=(sun-2.0)/8.5; a=math.sin(math.radians(alt)); c=math.cos(math.radians(az)); e=elev/2500.0; o=math.log(aod/0.05)/math.log(8.0)
    return np.asarray([1,s,a,c,e,o,s*s,a*a,c*c,o*o,s*a,s*c,s*o,a*c,a*o,c*o],dtype=np.float64)
def support_coords(g:dict[str,Any])->np.ndarray:
    return np.asarray([(float(g['sunDepressionDeg'])-2.0)/8.5,(float(g['targetAltitudeDeg'])-5.0)/75.0,(math.cos(math.radians(float(g['relativeAzimuthDeg'])))+1)/2,float(g['observerElevationM'])/2500.0,(float(g['aod550'])-0.05)/0.35],dtype=np.float64)
def in_box(g:dict[str,Any])->bool:
    return 2<=float(g['sunDepressionDeg'])<=10.5 and 5<=float(g['targetAltitudeDeg'])<=80 and 0<=float(g['relativeAzimuthDeg'])<=180 and 0<=float(g['observerElevationM'])<=2500 and .05<=float(g['aod550'])<=.4

def verify_model(model:dict[str,Any],p:dict[str,Any])->None:
    want=p['sourceBindings']['modelCanonicalSha256']; req(model.get('modelSha256')==want,'model canonical identity drift'); base={k:v for k,v in model.items() if k!='modelSha256'}; req(canon(base)==want,'model canonical selfhash drift')
    req(model.get('selectedCandidate')=={'familyId':'ridge-physical-compact','hyperparameters':{'ridge':0.001},'selectionScore':model['selectedCandidate']['selectionScore']},'selected model drift')
    req(model.get('trainingGeometryCount')==44 and len(model.get('targetNames') or [])==13,'model target dimensions drift')
    req(model.get('definitionOfDone')==load_definition(p),'model DoD differs from reviewed Stage2 freeze')

def load_definition(p:dict[str,Any])->dict[str,Any]:
    m=p['modelAndEvaluation']
    return {'aggregatePrimaryMeanAbsoluteLogErrorMustBeAtMostFractionOfFrozenTrainingMeanBaseline':m['aggregatePrimaryMeanAbsoluteLogErrorMustBeAtMostFractionOfFrozenTrainingMeanBaseline'],'allSixMustBeInsideFrozenValidatedSupport':True,'baselineDefinition':'TRAINING_MEAN_IN_TRANSFORMED_TARGET_SPACE_FROZEN_WITH_SELECTED_MODEL_ARTIFACT','exactZeroPrimaryAggregateRule':'PRESERVE_ZERO_NO_EPSILON_AND_FAIL_VALIDATED_SUPPORT_PASS_CLAIM_FOR_THAT_GEOMETRY','nonFinitePredictionRule':'FAIL','p90OrP95PrincipalMetricAllowed':False,'passRule':'ALL_SUPPORT_PRIMARY_BIAS_MEDIAN_WORST_UNCERTAINTY_BASELINE_AND_SHAPE_CRITERIA_MUST_PASS','positiveChannelAbsoluteMeanSignedLogBiasMax':m['positiveChannelAbsoluteMeanSignedLogBiasMax'],'positiveChannelMedianAbsoluteLogErrorMax':m['positiveChannelMedianAbsoluteLogErrorMax'],'positiveChannelRulesApplySeparatelyToAllThreeChannels':True,'positiveChannelWorstAbsoluteLogErrorMax':m['positiveChannelWorstAbsoluteLogErrorMax'],'positiveChannelWorstUncertaintyNormalizedErrorMax':m['positiveChannelWorstUncertaintyNormalizedErrorMax'],'protectedHoldoutGeometryCountRequired':6,'scope':'ONE_TIME_SIX_GEOMETRY_PROTECTED_COMPUTATIONAL_HOLDOUT_EVALUATION_AFTER_MODEL_FREEZE','shapeMedianPerCaseNrmseMax':m['shapeMedianPerCaseNrmseMax'],'shapePerCaseNrmseDefinition':'RMS_OVER_10_OF((PREDICTED_COEFFICIENT-DIRECT_MYSTIC_COEFFICIENT)/SQRT(FROZEN_COMPONENT_SCALE^2+DIRECT_MYSTIC_COEFFICIENT_STANDARD_ERROR^2))','shapeWorstPerCaseNrmseMax':m['shapeWorstPerCaseNrmseMax'],'shapeWorstSingleCoefficientNormalizedErrorMax':m['shapeWorstSingleCoefficientNormalizedErrorMax'],'surrogateLogErrorBudgetOneSigma':m['surrogateLogErrorBudgetOneSigma'],'uncertaintyNormalizedErrorDefinition':'ABS_LOG_ERROR/SQRT(LOG1P(DIRECT_MYSTIC_RELATIVE_STANDARD_ERROR_OF_MEAN)^2+0.12^2)'}

def locate_cases(root:Path,p:dict[str,Any])->dict[str,Path]:
    expected={x['caseId'] for x in expected_cases(p)}; found={}
    for f in root.rglob('case-result.json'):
        try:r=load(f)
        except Exception: continue
        cid=r.get('caseId')
        if cid in expected: req(cid not in found,f'duplicate case artifact: {cid}'); found[cid]=f.parent
    req(set(found)==expected,f'case artifact universe drift missing={sorted(expected-set(found))} extra={sorted(set(found)-expected)}'); return found

def evaluate(p:dict[str,Any],cases_root:Path,model_dir:Path,rep_dir:Path,out:Path)->dict[str,Any]:
    validate_contract(p); model=load(model_dir/'model-artifact-v1.json'); verify_model(model,p)
    npz=rep_dir/'spectral-representation-v2.npz'; req(sha_file(npz)==p['sourceBindings']['representationPackageSha256'],'representation NPZ hash drift'); z=np.load(npz); W=z['integration_weights']; C=z['selected_nullspace_pca_components']; grand=z['grand_mean_nullspace_residual']; req(W.shape==(3,8001) and C.shape==(10,8001) and grand.shape==(8001,),'representation array shape drift')
    scales=np.asarray([0.27729231126929754,0.09054255337405856,0.04362631407125976,0.00791831782256918,0.0046149233253235545,0.002441189933423995,0.0015868955715692872,0.0008860617219488324,0.0004930249648425277,0.00021007512113759737],dtype=np.float64)
    case_dirs=locate_cases(cases_root,p); by_gid:dict[str,list[tuple[np.ndarray,np.ndarray,dict[str,Any]]]]={}
    expected={x['caseId']:x for x in expected_cases(p)}
    for cid,c in expected.items():
        d=case_dirs[cid]; r=load(d/'case-result.json'); base={k:v for k,v in r.items() if k!='contentSha256'}; req(r.get('contentSha256')==canon(base),'case-result selfhash drift'); req(r.get('status')=='COMPLETED' and r.get('solverExecutionCount')==1 and r.get('workflowRunAttempt')==1,'case not successful one-use execution'); req((r.get('seed'),r.get('photonHistories'),r.get('block'))==(c['seed'],c['photonHistories'],c['block']),'case execution identity drift')
        wl,y,rsha=parse_spectrum(d/'mc.rad.spc'); swl,_,ssha=parse_spectrum(d/'mc.rad.std.spc'); req(np.array_equal(wl,swl),'radiance/std grid identity drift'); req(r.get('radianceOutputSha256')==rsha and r.get('stdRadianceOutputSha256')==ssha,'case raw hash drift')
        residual,ch=projection_residual(y,W); coeff=(residual-grand)@C.T; by_gid.setdefault(c['geometryId'],[]).append((ch,coeff,r))
    req(set(by_gid)==set(g['geometryId'] for g in p['stage2Scope']['geometries']) and all(len(v)==4 for v in by_gid.values()),'geometry block universe drift')
    B=np.asarray(model['modelState']['coefficients'],dtype=np.float64); req(B.shape==(16,13),'frozen model coefficient shape drift'); train_geoms=[x['geometry'] for x in model['trainingGeometryInputs']]; threshold=float(model['validatedSupport']['nearestTrainingDistanceMaxInclusive']); req(threshold==0.6,'support threshold drift')
    records=[]; all_abs=[]; base_abs=[]; per_channel={k:{'signed':[],'abs':[],'un':[]} for k in CHANNELS}; shape_cases=[]; shape_single=[]
    gmap={g['geometryId']:g for g in p['stage2Scope']['geometries']}
    for gid in sorted(by_gid):
        g=gmap[gid]; rows=by_gid[gid]; cha=np.vstack([x[0] for x in rows]); pca=np.vstack([x[1] for x in rows]); cs=[stats(cha[:,j]) for j in range(3)]; ps=[stats(pca[:,j]) for j in range(10)]
        req(all(float(s['mean'])>0 for s in cs),'exact-zero/nonpositive direct primary aggregate')
        pred_t=physical_basis(g)@B; req(pred_t.shape==(13,) and np.all(np.isfinite(pred_t)),'nonfinite prediction'); pred_ch=np.exp(pred_t[:3]); pred_pc=pred_t[3:]*scales
        c0=support_coords(g); dmin=min(float(np.linalg.norm(c0-support_coords(x))) for x in train_geoms); supported=in_box(g) and dmin<=threshold
        channel_metrics={}
        for j,k in enumerate(CHANNELS):
            truth=float(cs[j]['mean']); signed=float(math.log(pred_ch[j])-math.log(truth)); ae=abs(signed); rsem=float(cs[j]['relativeStandardError']); un=ae/math.sqrt(math.log1p(rsem)**2+float(p['modelAndEvaluation']['surrogateLogErrorBudgetOneSigma'])**2); base=float(model['frozenTrainingMeanBaselineTransformed'][j]); be=abs(base-math.log(truth)); per_channel[k]['signed'].append(signed); per_channel[k]['abs'].append(ae); per_channel[k]['un'].append(un); all_abs.append(ae); base_abs.append(be); channel_metrics[k]={'direct':cs[j],'predicted':float(pred_ch[j]),'signedLogError':signed,'absoluteLogError':ae,'uncertaintyNormalizedError':un,'baselineAbsoluteLogError':be}
        norm=np.asarray([(pred_pc[j]-float(ps[j]['mean']))/math.sqrt(float(scales[j])**2+float(ps[j]['standardError'])**2) for j in range(10)]); nrmse=float(math.sqrt(float(np.mean(norm**2)))); shape_cases.append(nrmse); shape_single.extend(abs(float(x)) for x in norm)
        records.append({'geometryId':gid,'geometry':{k:g[k] for k in FEATURES},'insideValidatedSupport':supported,'nearestTrainingDistance':dmin,'channels':channel_metrics,'directNullspacePcaCoefficients':ps,'predictedNullspacePcaCoefficients':[float(x) for x in pred_pc],'shapeNormalizedErrors':[float(x) for x in norm],'shapePerCaseNrmse':nrmse})
    m=p['modelAndEvaluation']; chsum={}; checks=[]
    for k in CHANNELS:
        signed=np.asarray(per_channel[k]['signed']); aa=np.asarray(per_channel[k]['abs']); un=np.asarray(per_channel[k]['un']); x={'absoluteMeanSignedLogBias':abs(float(np.mean(signed))),'medianAbsoluteLogError':float(np.median(aa)),'worstAbsoluteLogError':float(np.max(aa)),'worstUncertaintyNormalizedError':float(np.max(un))}; x['passes']=x['absoluteMeanSignedLogBias']<=m['positiveChannelAbsoluteMeanSignedLogBiasMax'] and x['medianAbsoluteLogError']<=m['positiveChannelMedianAbsoluteLogErrorMax'] and x['worstAbsoluteLogError']<=m['positiveChannelWorstAbsoluteLogErrorMax'] and x['worstUncertaintyNormalizedError']<=m['positiveChannelWorstUncertaintyNormalizedErrorMax']; chsum[k]=x; checks.append(x['passes'])
    aggregate=float(np.mean(all_abs)); baseline=float(np.mean(base_abs)); baseline_ratio=aggregate/baseline if baseline>0 else math.inf; shape_med=float(np.median(shape_cases)); shape_worst=max(shape_cases); single_worst=max(shape_single); support_pass=all(r['insideValidatedSupport'] for r in records); shape_pass=shape_med<=m['shapeMedianPerCaseNrmseMax'] and shape_worst<=m['shapeWorstPerCaseNrmseMax'] and single_worst<=m['shapeWorstSingleCoefficientNormalizedErrorMax']; baseline_pass=baseline_ratio<=m['aggregatePrimaryMeanAbsoluteLogErrorMustBeAtMostFractionOfFrozenTrainingMeanBaseline']; passed=support_pass and all(checks) and baseline_pass and shape_pass
    result={'schemaVersion':1,'stageId':'level-b-v1-tier2-stage2-protected-holdout-evaluation-v1','status':'PASS' if passed else 'FAIL_FROZEN_DOD_NO_RETUNING','contractId':p['contractId'],'modelSha256':model['modelSha256'],'representationPackageSha256':p['sourceBindings']['representationPackageSha256'],'geometryCount':6,'caseCount':24,'configuredPhotonHistories':720000000,'records':records,'channelSummary':chsum,'aggregatePrimaryMeanAbsoluteLogError':aggregate,'frozenTrainingMeanBaselinePrimaryMeanAbsoluteLogError':baseline,'aggregateToBaselineFraction':baseline_ratio,'supportPass':support_pass,'shapeMedianPerCaseNrmse':shape_med,'shapeWorstPerCaseNrmse':shape_worst,'shapeWorstSingleCoefficientNormalizedError':single_worst,'shapePass':shape_pass,'baselinePass':baseline_pass,'definitionOfDonePassed':passed,'p90OrP95Used':False,'retuningPerformed':False,'holdoutValuesRead':True,'modelChangedAfterHoldoutOpening':False,'productionPromotionAuthorized':False}; result['resultSha256']=canon(result); write(out,result); return result

def main()->int:
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='cmd',required=True); v=sub.add_parser('validate'); v.add_argument('--contract',type=Path,required=True); v.add_argument('--repo-root',type=Path); c=sub.add_parser('cases'); c.add_argument('--contract',type=Path,required=True); e=sub.add_parser('evaluate'); e.add_argument('--contract',type=Path,required=True); e.add_argument('--cases-root',type=Path,required=True); e.add_argument('--model-dir',type=Path,required=True); e.add_argument('--representation-dir',type=Path,required=True); e.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    try:
        p=load(a.contract)
        if a.cmd=='validate': validate_contract(p); validate_review_sources(a.repo_root,p) if a.repo_root else None
        elif a.cmd=='cases': print(json.dumps(expected_cases(p),sort_keys=True,separators=(',',':')))
        else: evaluate(p,a.cases_root,a.model_dir,a.representation_dir,a.output)
        return 0
    except Exception as x:
        print(json.dumps({'status':'REFUSED','reason':str(x)},sort_keys=True)); return 2
if __name__=='__main__': raise SystemExit(main())
