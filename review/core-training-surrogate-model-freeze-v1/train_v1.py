#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, io, json, math, os, urllib.error, urllib.request, zipfile
from pathlib import Path
from typing import Any
import numpy as np

REPO='search-maker/twilight-mystic-experiments'
RESULT_BINDING='review/core-training-spectral-representation-v2-result-v1/result-v1.json'
RESULT_BINDING_BLOB='a18acace210eaef621930bd5682113a686ad10a3'
DOMAIN_PATH='review/level-b-v1-domain-scope-decision-v1/level-b-v1-domain-scope-decision-v1.json'
DOMAIN_BLOB='ccba48b1d2f4b1317bb02285c8b3cfe159607f84'
FEATURES=('sunDepressionDeg','targetAltitudeDeg','relativeAzimuthDeg','observerElevationM','aod550')
CHANNELS=('photopicLuminanceCdM2','scotopicLuminanceScotCdM2','johnsonVEffectiveRadiance_mW_m2_nm_sr')
FROZEN_SCALES=(0.27729231126929754,0.09054255337405856,0.04362631407125976,0.00791831782256918,0.0046149233253235545,0.002441189933423995,0.0015868955715692872,0.0008860617219488324,0.0004930249648425277,0.00021007512113759737)
class Refusal(RuntimeError): pass

def req(c:bool,m:str)->None:
    if not c: raise Refusal(m)
def sha(b:bytes)->str: return hashlib.sha256(b).hexdigest()
def canon(v:Any)->str: return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def load(p:Path)->dict[str,Any]:
    x=json.loads(p.read_text(encoding='utf-8')); req(isinstance(x,dict),f'object required: {p}'); return x
def write(p:Path,v:Any)->None:
    p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')

def validate_protocol(p:dict[str,Any])->None:
    req((p.get('schemaVersion'),p.get('protocolId'),p.get('status'),p.get('governance'))==(1,'level-b-v1-core-surrogate-model-freeze-v1','REVIEW_ONLY_PRE_HOLDOUT_MODEL_OOD_DOD_FREEZE_NO_REAL_MODEL_FIT_ON_PR','MYSTIC-STATE-0067'),'protocol identity drift')
    req(p.get('sourceMainAtFreeze')=='0b68c720dbd0df6fe018917770f315a43e44e6b8','source main drift')
    s=p.get('sourceRepresentation') or {}
    req((s.get('resultBindingGitBlobSha'),s.get('artifactId'),s.get('artifactDigest'))==(RESULT_BINDING_BLOB,9208203541,'sha256:2fe50ed674155f440322c92d28877f5c022f0cc5fa13e1e601596a9902482815'),'representation source drift')
    req((s.get('trainingGeometryCount'),s.get('sourceCaseArtifactCount'),s.get('representationFeatureCount'),s.get('mandatoryIntegratedChannelCount'),s.get('nullspacePcaComponentCount'))==(44,138,13,3,10),'representation dimensions drift')
    req(s.get('resolvedPcaIndices')==[0,1,2,3,4,5,6,7,9,12],'resolved PCA identity drift')
    scales=s.get('nullspaceCoefficientScales') or []; req(tuple(scales)==FROZEN_SCALES and all(math.isfinite(float(x)) and x>0 for x in scales),'coefficient scale drift')
    d=p.get('domainAndSupport') or {}; req(d.get('sourceDecisionGitBlobSha')==DOMAIN_BLOB,'domain source drift')
    req(d.get('nearestTrainingDistanceMaxInclusive')==0.6 and d.get('deploymentSupportAlwaysIntersectedWithDesignBox') is True and d.get('silentExtrapolationAllowed') is False,'support rule drift')
    m=p.get('modelSelection') or {}; fam=m.get('candidateFamilies') or []; req([x.get('familyId') for x in fam]==['ridge-cos-compact','ridge-physical-compact','ridge-poly2-cos','local-idw-cos'],'candidate family drift')
    req((m.get('crossValidationFolds') or {}).get('totalFoldCount')==15,'CV fold count drift')
    req((m.get('preHoldoutTrainingCvReadiness') or {}).get('selectedPrimaryMustBeatFoldMatchedTrainingMeanBaselineByFraction')==0.10,'readiness drift')
    q=p.get('definitionOfDone') or {}
    req((q.get('protectedHoldoutGeometryCountRequired'),q.get('positiveChannelAbsoluteMeanSignedLogBiasMax'),q.get('positiveChannelMedianAbsoluteLogErrorMax'),q.get('positiveChannelWorstAbsoluteLogErrorMax'))==(6,0.08,0.15,0.35),'primary DoD drift')
    req((q.get('shapeMedianPerCaseNrmseMax'),q.get('shapeWorstPerCaseNrmseMax'),q.get('shapeWorstSingleCoefficientNormalizedErrorMax'))==(0.75,1.25,3.0),'shape DoD drift')
    req(q.get('p90OrP95PrincipalMetricAllowed') is False and q.get('surrogateLogErrorBudgetOneSigma')==0.12,'DoD semantics drift')
    b=p.get('boundaries') or {}; req(b.get('realModelFitOnReviewPullRequestAuthorized') is False and b.get('separateTrainingOnlyActivationAfterMergePermitted') is True,'training activation boundary drift')
    for k in ('protectedHoldoutOpeningAuthorized','holdoutValuesMayBeRead','holdoutScientificExecutionAuthorized','stage2Authorized','newTrainingScientificSolverExecutionAuthorized','productionPromotionAuthorized','workerBLaneReactivated','workerCLaneReactivated'):
        req(b.get(k) is False,f'closed boundary opened: {k}')

def coords(g:dict[str,Any])->np.ndarray:
    try: vals=[float(g[k]) for k in FEATURES]
    except Exception as e: raise Refusal('geometry feature missing') from e
    req(all(math.isfinite(x) for x in vals),'nonfinite geometry')
    sun,alt,az,elev,aod=vals
    return np.array([(sun-2.0)/8.5,(alt-5.0)/75.0,(math.cos(math.radians(az))+1.0)/2.0,elev/2500.0,(aod-0.05)/0.35],dtype=np.float64)
def raw_cos(g:dict[str,Any])->np.ndarray:
    c=coords(g); return np.array([c[0],c[1],2*c[2]-1,c[3],c[4]],dtype=np.float64)
def physical(g:dict[str,Any])->np.ndarray:
    sun=float(g['sunDepressionDeg']); alt=float(g['targetAltitudeDeg']); az=float(g['relativeAzimuthDeg']); elev=float(g['observerElevationM']); aod=float(g['aod550'])
    req(aod>0,'positive AOD required')
    return np.array([(sun-2.0)/8.5,math.sin(math.radians(alt)),math.cos(math.radians(az)),elev/2500.0,math.log(aod/0.05)/math.log(8.0)],dtype=np.float64)
def design_box(g:dict[str,Any])->bool:
    box={'sunDepressionDeg':(2,10.5),'targetAltitudeDeg':(5,80),'relativeAzimuthDeg':(0,180),'observerElevationM':(0,2500),'aod550':(.05,.4)}
    return all(box[k][0] <= float(g[k]) <= box[k][1] for k in FEATURES)
def support(g:dict[str,Any],train_geoms:list[dict[str,Any]],threshold:float=0.6)->tuple[bool,float]:
    if not design_box(g): return False,math.inf
    c=coords(g); ds=[float(np.linalg.norm(c-coords(x))) for x in train_geoms]; req(ds,'training geometry required'); d=min(ds); return d<=threshold,d

def poly2(v:np.ndarray)->np.ndarray:
    out=[1.0,*v.tolist()]
    for i in range(len(v)):
        for j in range(i,len(v)): out.append(float(v[i]*v[j]))
    return np.array(out,dtype=np.float64)
def basis(g:dict[str,Any],name:str)->np.ndarray:
    if name=='COS_COMPACT_13_TERMS':
        s,a,c,e,o=raw_cos(g); return np.array([1,s,a,c,e,o,s*s,a*a,c*c,s*a,s*c,s*o,a*c],dtype=np.float64)
    if name=='PHYSICAL_COMPACT_16_TERMS':
        s,a,c,e,o=physical(g); return np.array([1,s,a,c,e,o,s*s,a*a,c*c,o*o,s*a,s*c,s*o,a*c,a*o,c*o],dtype=np.float64)
    if name=='FULL_DEGREE2_ON_FIVE_COS_COORDINATES_21_TERMS': return poly2(raw_cos(g))
    raise Refusal(f'unknown basis: {name}')

def targets(rec:dict[str,Any],scales:list[float])->np.ndarray:
    ch=rec.get('integratedChannels') or {}; out=[]
    for k in CHANNELS:
        s=ch.get(k) or {}; x=float(s.get('mean')); req(math.isfinite(x) and x>0,f'positive channel required: {rec.get("geometryId")} {k}'); out.append(math.log(x))
    pcs=rec.get('nullspacePcaCoefficients') or []; req(len(pcs)==10,'ten PCA coefficients required')
    for j,s in enumerate(pcs):
        x=float((s or {}).get('mean')); req(math.isfinite(x),'finite PCA coefficient required'); out.append(x/scales[j])
    return np.array(out,dtype=np.float64)

def fit_ridge(recs:list[dict[str,Any]],basis_name:str,ridge:float,scales:list[float])->dict[str,Any]:
    X=np.vstack([basis(r['geometry'],basis_name) for r in recs]); Y=np.vstack([targets(r,scales) for r in recs]); req(X.shape[0]>X.shape[1]//2,'insufficient fit rows')
    G=X.T@X; P=np.eye(G.shape[0]); P[0,0]=0.0; B=np.linalg.solve(G+ridge*P,X.T@Y); req(np.all(np.isfinite(B)),'nonfinite ridge state')
    return {'kind':'RIDGE','basis':basis_name,'ridge':float(ridge),'coefficients':B.tolist()}
def fit_idw(recs:list[dict[str,Any]],neighbors:int,power:float,scales:list[float])->dict[str,Any]:
    req(1<=neighbors<len(recs) and power>0,'invalid IDW hyperparameter')
    return {'kind':'IDW','neighbors':int(neighbors),'power':float(power),'coordinates':[coords(r['geometry']).tolist() for r in recs],'targets':[targets(r,scales).tolist() for r in recs]}
def predict(model:dict[str,Any],g:dict[str,Any])->np.ndarray:
    if model['kind']=='RIDGE': return basis(g,model['basis'])@np.asarray(model['coefficients'],dtype=np.float64)
    c=coords(g); X=np.asarray(model['coordinates'],dtype=np.float64); Y=np.asarray(model['targets'],dtype=np.float64); ds=np.linalg.norm(X-c,axis=1); exact=np.where(ds<=1e-15)[0]
    if len(exact): return Y[int(exact[0])].copy()
    k=min(int(model['neighbors']),len(ds)); idx=np.argsort(ds,kind='stable')[:k]; w=1.0/np.power(ds[idx],float(model['power'])); return (w[:,None]*Y[idx]).sum(axis=0)/w.sum()
def transformed_to_physical(t:np.ndarray,scales:list[float])->tuple[np.ndarray,np.ndarray]:
    return np.exp(t[:3]),t[3:]*np.asarray(scales)

def folds(recs:list[dict[str,Any]])->list[tuple[str,list[int],list[int]]]:
    order=sorted(range(len(recs)),key=lambda i:str(recs[i]['geometryId'])); out=[]
    for k in range(5):
        val=[idx for pos,idx in enumerate(order) if pos%5==k]; fit=[i for i in range(len(recs)) if i not in set(val)]; out.append((f'balanced-{k}',fit,val))
    predicates=[
      ('sun-shallow',lambda g:float(g['sunDepressionDeg'])<=4.0),
      ('sun-deep-core',lambda g:8.5<=float(g['sunDepressionDeg'])<=10.5),
      ('az-low',lambda g:float(g['relativeAzimuthDeg'])<=60.0),
      ('az-high',lambda g:float(g['relativeAzimuthDeg'])>=150.0),
      ('alt-low',lambda g:float(g['targetAltitudeDeg'])<=20.0),
      ('alt-high',lambda g:float(g['targetAltitudeDeg'])>=65.0),
      ('aod-low',lambda g:float(g['aod550'])<=0.10),
      ('aod-high',lambda g:float(g['aod550'])>=0.35),
      ('elev-low',lambda g:float(g['observerElevationM'])<=500.0),
      ('elev-high',lambda g:float(g['observerElevationM'])>=2000.0),
    ]
    for name,p in predicates:
        val=[i for i,r in enumerate(recs) if p(r['geometry'])]; valset=set(val); fit=[i for i in range(len(recs)) if i not in valset]; req(len(val)>=4 and len(fit)>=20,f'boundary fold count drift: {name} {len(val)}'); out.append((name,fit,val))
    req(len(out)==15,'fold count drift'); return out

def fit_candidate(recs:list[dict[str,Any]],cand:dict[str,Any],hp:dict[str,Any],scales:list[float])->dict[str,Any]:
    if cand['kind']=='RIDGE': return fit_ridge(recs,cand['basis'],float(hp['ridge']),scales)
    return fit_idw(recs,int(hp['neighbors']),float(hp['power']),scales)
def hps(c:dict[str,Any])->list[dict[str,Any]]:
    if c['kind']=='RIDGE': return [{'ridge':float(x)} for x in c['ridgeValues']]
    return [{'neighbors':int(k),'power':float(p)} for k in c['neighbors'] for p in c['powers']]
def candidate_key(c:dict[str,Any],hp:dict[str,Any])->tuple:
    return (int(c['complexityRank']),str(c['familyId']),float(hp.get('ridge',0)),int(hp.get('neighbors',0)),float(hp.get('power',0)))

def eval_candidate(recs:list[dict[str,Any]],cand:dict[str,Any],hp:dict[str,Any],scales:list[float])->dict[str,Any]:
    rows=[]; baseline_rows=[]
    for name,fi,vi in folds(recs):
        fit=[recs[i] for i in fi]; val=[recs[i] for i in vi]; model=fit_candidate(fit,cand,hp,scales); base=np.mean(np.vstack([targets(r,scales) for r in fit]),axis=0)
        prim=[]; shapes=[]; single=[]; bprim=[]
        for r in val:
            truth=targets(r,scales); pred=predict(model,r['geometry']); e=np.abs(pred[:3]-truth[:3]); prim.append(float(np.mean(e))); single.append(float(np.max(e))); shapes.append(float(np.sqrt(np.mean((pred[3:]-truth[3:])**2)))); bprim.append(float(np.mean(np.abs(base[:3]-truth[:3]))))
        rows.append({'fold':name,'count':len(val),'primaryMale':float(np.mean(prim)),'shapeNrmse':float(np.mean(shapes)),'worstSinglePrimaryLogError':max(single)})
        baseline_rows.append(float(np.mean(bprim)))
    mp=float(np.mean([x['primaryMale'] for x in rows])); ms=float(np.mean([x['shapeNrmse'] for x in rows])); wp=max(x['primaryMale'] for x in rows); ws=max(x['shapeNrmse'] for x in rows); wsingle=max(x['worstSinglePrimaryLogError'] for x in rows); baseline=float(np.mean(baseline_rows)); score=mp+0.20*ms+0.25*wp+0.05*wsingle+0.05*ws
    return {'familyId':cand['familyId'],'hyperparameters':hp,'complexityRank':cand['complexityRank'],'selectionScore':score,'meanFoldPrimaryMale':mp,'meanFoldShapeNrmse':ms,'worstFoldPrimaryMale':wp,'worstFoldShapeNrmse':ws,'worstSinglePrimaryLogError':wsingle,'foldMatchedTrainingMeanBaselinePrimaryMale':baseline,'primaryImprovementFractionVsBaseline':(baseline-mp)/baseline if baseline>0 else None,'folds':rows}
def select(recs:list[dict[str,Any]],p:dict[str,Any])->tuple[dict[str,Any],list[dict[str,Any]]]:
    scales=[float(x) for x in p['sourceRepresentation']['nullspaceCoefficientScales']]; allrows=[]; cmap={c['familyId']:c for c in p['modelSelection']['candidateFamilies']}
    for c in p['modelSelection']['candidateFamilies']:
        for hp in hps(c): allrows.append(eval_candidate(recs,c,hp,scales))
    allrows.sort(key=lambda r:(r['selectionScore'],*candidate_key(cmap[r['familyId']],r['hyperparameters'])))
    best=allrows[0]; q=p['modelSelection']['preHoldoutTrainingCvReadiness']; req(best['meanFoldPrimaryMale']<=q['meanFoldPrimaryMax'],'selected model primary CV readiness failed'); req(best['worstSinglePrimaryLogError']<=q['worstSinglePrimaryLogErrorMax'],'selected model worst primary CV readiness failed'); req(best['meanFoldShapeNrmse']<=q['meanFoldShapeNrmseMax'],'selected model shape CV readiness failed'); req(best['worstFoldShapeNrmse']<=q['worstFoldShapeNrmseMax'],'selected model worst shape CV readiness failed'); req(best['primaryImprovementFractionVsBaseline'] is not None and best['primaryImprovementFractionVsBaseline']>=q['selectedPrimaryMustBeatFoldMatchedTrainingMeanBaselineByFraction'],'selected model fails baseline-improvement readiness')
    return best,allrows

def validate_dataset(d:dict[str,Any],r:dict[str,Any],p:dict[str,Any])->list[dict[str,Any]]:
    s=p['sourceRepresentation']; req(d.get('schemaVersion')==2 and d.get('stageId')=='level-b-v1-core-training-representation-dataset-v2','dataset identity drift'); req(d.get('geometryCount')==44 and d.get('sourceCaseArtifactCount')==138 and d.get('representationFeatureCount')==13,'dataset dimensions drift'); req(d.get('datasetSha256')==s['trainingDatasetCanonicalSha256'] and canon({k:v for k,v in d.items() if k!='datasetSha256'})==d['datasetSha256'],'dataset canonical hash drift'); req(d.get('holdoutValuesRead') is False and d.get('protectedHoldoutRecordCount')==0,'holdout contamination')
    req(r.get('resultSha256')==s['representationResultCanonicalSha256'] and r.get('representationPackageSha256')==s['representationPackageSha256'],'representation result drift'); req(r.get('resolvedPcaIndices')==s['resolvedPcaIndices'],'resolved component drift')
    recs=d.get('records') or []; req(len(recs)==44 and len({x['geometryId'] for x in recs})==44,'training record drift'); [targets(x,s['nullspaceCoefficientScales']) for x in recs]; return recs

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl): return None
def download(aid:int,digest:str,token:str)->bytes:
    req(token,'GITHUB_TOKEN required'); headers={'Authorization':f'Bearer {token}','Accept':'application/vnd.github+json','User-Agent':'level-b-model-freeze-v1','X-GitHub-Api-Version':'2022-11-28'}
    meta_req=urllib.request.Request(f'https://api.github.com/repos/{REPO}/actions/artifacts/{aid}',headers=headers); meta=json.loads(urllib.request.urlopen(meta_req,timeout=60).read()); req(meta.get('expired') is False and meta.get('digest')==digest,'source artifact metadata drift')
    op=urllib.request.build_opener(NoRedirect); req2=urllib.request.Request(f'https://api.github.com/repos/{REPO}/actions/artifacts/{aid}/zip',headers={k:v for k,v in headers.items() if k!='Accept'})
    try: response=op.open(req2,timeout=60)
    except urllib.error.HTTPError as e:
        req(e.code in (301,302,303,307,308) and e.headers.get('Location'),'artifact redirect missing'); location=e.headers['Location']
    else:
        with response: raw=response.read(); req('sha256:'+sha(raw)==digest,'source artifact ZIP digest drift'); return raw
    with urllib.request.urlopen(urllib.request.Request(location,headers={'User-Agent':'level-b-model-freeze-v1'}),timeout=120) as response: raw=response.read()
    req('sha256:'+sha(raw)==digest,'source artifact ZIP digest drift'); return raw

def git_blob(root:Path,path:str)->str:
    import subprocess
    return subprocess.check_output(['git','rev-parse',f'HEAD:{path}'],cwd=root,text=True).strip()

def execute(root:Path,protocol_path:Path,out:Path)->None:
    p=load(protocol_path); validate_protocol(p); req(git_blob(root,RESULT_BINDING)==RESULT_BINDING_BLOB,'result binding git blob drift'); req(git_blob(root,DOMAIN_PATH)==DOMAIN_BLOB,'domain decision git blob drift')
    s=p['sourceRepresentation']; raw=download(s['artifactId'],s['artifactDigest'],os.environ.get('GITHUB_TOKEN',''))
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        d=json.loads(z.read('training-representation-dataset-v2.json')); r=json.loads(z.read('spectral-representation-result-v2.json'))
    recs=validate_dataset(d,r,p); best,ranking=select(recs,p); cmap={c['familyId']:c for c in p['modelSelection']['candidateFamilies']}; scales=s['nullspaceCoefficientScales']; model=fit_candidate(recs,cmap[best['familyId']],best['hyperparameters'],scales); base=np.mean(np.vstack([targets(x,scales) for x in recs]),axis=0)
    in_core=[x for x in recs if design_box(x['geometry'])]; loo=[]
    for rec in in_core:
        others=[x['geometry'] for x in recs if x['geometryId']!=rec['geometryId']]; ok,dist=support(rec['geometry'],others,p['domainAndSupport']['nearestTrainingDistanceMaxInclusive']); loo.append({'geometryId':rec['geometryId'],'nearestDistance':dist,'insideSupportAgainstOtherTraining':ok})
    req(len(in_core)==42 and abs(max(x['nearestDistance'] for x in loo)-p['domainAndSupport']['trainingInputOnlyCalibration']['maxInCoreLeaveOneOutNearestTrainingDistance'])<1e-12,'support calibration drift')
    artifact={'schemaVersion':1,'modelId':'level-b-v1-core-surrogate-model-v1','status':'FROZEN_TRAINING_ONLY_MODEL_PENDING_PROTECTED_HOLDOUT_AUTHORIZATION','protocolId':p['protocolId'],'sourceRepresentationDatasetSha256':s['trainingDatasetCanonicalSha256'],'trainingGeometryCount':44,'featureNames':list(FEATURES),'targetNames':list(CHANNELS)+[f'nullspacePcaCoefficient{i}' for i in range(10)],'targetTransform':p['targets'],'selectedCandidate':{'familyId':best['familyId'],'hyperparameters':best['hyperparameters'],'selectionScore':best['selectionScore']},'modelState':model,'frozenTrainingMeanBaselineTransformed':base.tolist(),'validatedSupport':p['domainAndSupport'],'definitionOfDone':p['definitionOfDone'],'trainingGeometryInputs':[{'geometryId':x['geometryId'],'geometry':x['geometry']} for x in sorted(recs,key=lambda x:x['geometryId'])],'holdoutValuesRead':False,'protectedHoldoutRecordCount':0,'productionPromotionAuthorized':False}; artifact['modelSha256']=canon(artifact)
    selection={'schemaVersion':1,'stageId':'level-b-v1-core-surrogate-training-selection-v1','status':'TRAINING_ONLY_CV_SELECTION_COMPLETE','protocolId':p['protocolId'],'selected':best,'candidates':ranking,'supportLeaveOneOut':loo,'holdoutValuesRead':False}; selection['selectionSha256']=canon(selection)
    result={'schemaVersion':1,'stageId':'level-b-v1-core-surrogate-model-freeze-result-v1','status':'TRAINING_ONLY_MODEL_FROZEN_PENDING_REVIEWED_RESULT_BINDING_AND_SEPARATE_HOLDOUT_AUTHORIZATION','protocolId':p['protocolId'],'modelSha256':artifact['modelSha256'],'selectionSha256':selection['selectionSha256'],'selectedFamilyId':best['familyId'],'selectedHyperparameters':best['hyperparameters'],'trainingGeometryCount':44,'representationFeatureCount':13,'validatedSupportNearestDistanceMaxInclusive':0.6,'definitionOfDoneFrozen':True,'holdoutValuesRead':False,'protectedHoldoutRecordCount':0,'protectedHoldoutOpeningAuthorized':False,'newScientificExecutionAuthorized':False,'stage2Authorized':False,'productionPromotionAuthorized':False}; result['resultSha256']=canon(result)
    out.mkdir(parents=True,exist_ok=True); write(out/'model-artifact-v1.json',artifact); write(out/'training-selection-v1.json',selection); write(out/'model-freeze-result-v1.json',result)

def synthetic_records(n:int=44)->list[dict[str,Any]]:
    out=[]
    for i in range(n):
        g={'sunDepressionDeg':2+8.5*((i*7)%n)/(n-1),'targetAltitudeDeg':5+75*((i*9)%n)/(n-1),'relativeAzimuthDeg':180*((i*13)%n)/(n-1),'observerElevationM':2500*((i*17)%n)/(n-1),'aod550':.05+.35*((i*19)%n)/(n-1)}
        x=raw_cos(g); phot=math.exp(3-2*x[0]+.4*x[1]-.3*x[2]-.2*x[4]); scot=phot*math.exp(.8+.1*x[0]); jv=phot*.015*math.exp(.05*x[2]); pcs=[]
        for j in range(10):
            z=(0.18*x[0]-0.11*x[1]+0.07*x[2]+0.04*x[3]-0.05*x[4])*(1.0-0.03*j); pcs.append({'mean':FROZEN_SCALES[j]*z,'sampleStd':FROZEN_SCALES[j]*0.02,'standardError':FROZEN_SCALES[j]*0.01,'relativeStandardError':None})
        out.append({'geometryId':f'train-{i+1:04d}','geometry':g,'blockCount':4,'integratedChannels':{CHANNELS[0]:{'mean':phot,'relativeStandardError':.01},CHANNELS[1]:{'mean':scot,'relativeStandardError':.01},CHANNELS[2]:{'mean':jv,'relativeStandardError':.01}},'nullspacePcaCoefficients':pcs})
    return out

def main()->int:
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='cmd',required=True); v=sub.add_parser('validate'); v.add_argument('--protocol',type=Path,required=True); t=sub.add_parser('synthetic'); t.add_argument('--protocol',type=Path,required=True); e=sub.add_parser('execute'); e.add_argument('--repo-root',type=Path,required=True); e.add_argument('--protocol',type=Path,required=True); e.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    try:
        p=load(a.protocol); validate_protocol(p)
        if a.cmd=='synthetic':
            recs=synthetic_records(); best,ranking=select(recs,p); print(json.dumps({'status':'SYNTHETIC_PASS','selected':best['familyId'],'candidateCount':len(ranking)},sort_keys=True))
        elif a.cmd=='execute': execute(a.repo_root,a.protocol,a.output)
        return 0
    except Exception as x:
        print(json.dumps({'status':'REFUSED','reason':str(x)},sort_keys=True),file=os.sys.stderr); return 2
if __name__=='__main__': raise SystemExit(main())
