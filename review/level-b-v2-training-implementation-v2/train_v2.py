#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

import numpy as np

REPO='search-maker/twilight-mystic-experiments'
ARTIFACT_ID=9208203541
ARTIFACT_DIGEST='2fe50ed674155f440322c92d28877f5c022f0cc5fa13e1e601596a9902482815'
DATASET_MEMBER='training-representation-dataset-v2.json'
DATASET_FILE_SHA256='066d6be846fa9b3bdd7236e327894f64d52ea56aa7e7b6e6af4d51d849eb1a61'
DATASET_CANONICAL_SHA256='bb7908426d9d545f43c082aebbaab1829a486e2962d0b9ee34a5e8bef5390133'
CHANNELS=('photopicLuminanceCdM2','scotopicLuminanceScotCdM2','johnsonVEffectiveRadiance_mW_m2_nm_sr')

class Refusal(RuntimeError): pass
def req(c:bool,m:str)->None:
    if not c: raise Refusal(m)
def sha256_bytes(b:bytes)->str: return hashlib.sha256(b).hexdigest()
def canonical_sha(v:Any)->str: return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def load_json(path:Path)->dict[str,Any]:
    v=json.loads(path.read_text(encoding='utf-8')); req(isinstance(v,dict),f'object required: {path}'); return v
def write_json(path:Path,v:Any)->None:
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')

def raw_cos(g:dict[str,Any])->np.ndarray:
    return np.array([(float(g['sunDepressionDeg'])-2.0)/8.5,(float(g['targetAltitudeDeg'])-5.0)/75.0,math.cos(math.radians(float(g['relativeAzimuthDeg']))),float(g['observerElevationM'])/2500.0,(float(g['aod550'])-0.05)/0.35],dtype=np.float64)
def physical(g:dict[str,Any])->np.ndarray:
    aod=float(g['aod550']); req(aod>0,'positive AOD required')
    return np.array([(float(g['sunDepressionDeg'])-2.0)/8.5,math.sin(math.radians(float(g['targetAltitudeDeg']))),math.cos(math.radians(float(g['relativeAzimuthDeg']))),float(g['observerElevationM'])/2500.0,math.log(aod/0.05)/math.log(8.0)],dtype=np.float64)
def idw_coords(g:dict[str,Any])->np.ndarray:
    return np.array([(float(g['sunDepressionDeg'])-2.0)/8.5,(float(g['targetAltitudeDeg'])-5.0)/75.0,(math.cos(math.radians(float(g['relativeAzimuthDeg'])))+1.0)/2.0,float(g['observerElevationM'])/2500.0,(float(g['aod550'])-0.05)/0.35],dtype=np.float64)
def basis(g:dict[str,Any],name:str)->np.ndarray:
    if name=='COS_COMPACT_13_TERMS':
        s,a,c,e,o=raw_cos(g); out=[1,s,a,c,e,o,s*s,a*a,c*c,s*a,s*c,s*o,a*c]
    else:
        s,a,c,e,o=physical(g)
        if name=='PHYSICAL_COMPACT_16_TERMS': out=[1,s,a,c,e,o,s*s,a*a,c*c,o*o,s*a,s*c,s*o,a*c,a*o,c*o]
        elif name=='FULL_DEGREE2_ON_FIVE_PHYSICAL_COORDINATES_21_TERMS':
            v=(s,a,c,e,o); out=[1,*v]
            for i in range(5):
                for j in range(i,5): out.append(v[i]*v[j])
        else: raise Refusal(f'unknown basis: {name}')
    x=np.asarray(out,dtype=np.float64); req(np.all(np.isfinite(x)),'nonfinite basis'); return x

def targets_and_shape_se(rec:dict[str,Any],scales:np.ndarray)->tuple[np.ndarray,np.ndarray]:
    vals=[]
    ch=rec.get('integratedChannels') or {}
    for k in CHANNELS:
        mean=float((ch.get(k) or {}).get('mean')); req(math.isfinite(mean) and mean>0,f'positive channel required: {rec.get("geometryId")} {k}'); vals.append(math.log(mean))
    pcs=rec.get('nullspacePcaCoefficients') or []; req(len(pcs)==10,'ten PCA coefficients required')
    ses=[]
    for j,x in enumerate(pcs):
        mean=float((x or {}).get('mean')); se=float((x or {}).get('standardError')); req(math.isfinite(mean) and math.isfinite(se) and se>=0,'finite PCA mean/se required'); vals.append(mean/float(scales[j])); ses.append(se/float(scales[j]))
    y=np.asarray(vals,dtype=np.float64); u=np.asarray(ses,dtype=np.float64); req(y.shape==(13,) and u.shape==(10,) and np.all(np.isfinite(y)) and np.all(np.isfinite(u)),'target/uncertainty shape drift'); return y,u

def fit_primary_ridge(recs:list[dict[str,Any]],basis_name:str,ridge:float,scales:np.ndarray)->dict[str,Any]:
    X=np.vstack([basis(r['geometry'],basis_name) for r in recs]); Y=np.vstack([targets_and_shape_se(r,scales)[0][:3] for r in recs]); G=X.T@X; P=np.eye(G.shape[0]); P[0,0]=0.0; B=np.linalg.solve(G+ridge*P,X.T@Y); req(np.all(np.isfinite(B)),'nonfinite primary ridge'); return {'kind':'RIDGE_PRIMARY','basis':basis_name,'ridge':float(ridge),'coefficients':B.tolist()}
def fit_weighted_shape_ridge(recs:list[dict[str,Any]],basis_name:str,ridge:float,scales:np.ndarray)->dict[str,Any]:
    X=np.vstack([basis(r['geometry'],basis_name) for r in recs]); pairs=[targets_and_shape_se(r,scales) for r in recs]; Y=np.vstack([p[0][3:] for p in pairs]); U=np.vstack([p[1] for p in pairs]); P=np.eye(X.shape[1]); P[0,0]=0.0; cols=[]
    for j in range(10):
        w=1.0/(1.0+U[:,j]**2); XtW=X.T*w[None,:]; B=np.linalg.solve(XtW@X+ridge*P,XtW@Y[:,j]); req(np.all(np.isfinite(B)),'nonfinite weighted shape ridge'); cols.append(B)
    return {'kind':'UNCERTAINTY_WEIGHTED_SHAPE_RIDGE','basis':basis_name,'ridge':float(ridge),'coefficients':np.column_stack(cols).tolist(),'weightFormula':'1/(1+normalizedSE^2)'}
def fit_idw_shape(recs:list[dict[str,Any]],neighbors:int,power:float,scales:np.ndarray)->dict[str,Any]:
    req(1<=neighbors<len(recs) and power>0,'invalid IDW hyperparameter'); X=np.vstack([idw_coords(r['geometry']) for r in recs]); Y=np.vstack([targets_and_shape_se(r,scales)[0][3:] for r in recs]); return {'kind':'IDW_SHAPE','neighbors':int(neighbors),'power':float(power),'coordinates':X.tolist(),'targets':Y.tolist()}
def predict_primary(model:dict[str,Any],g:dict[str,Any])->np.ndarray: return basis(g,model['basis'])@np.asarray(model['coefficients'],dtype=np.float64)
def predict_shape(model:dict[str,Any],g:dict[str,Any])->np.ndarray:
    if model['kind']=='UNCERTAINTY_WEIGHTED_SHAPE_RIDGE': return basis(g,model['basis'])@np.asarray(model['coefficients'],dtype=np.float64)
    c=idw_coords(g); X=np.asarray(model['coordinates'],dtype=np.float64); Y=np.asarray(model['targets'],dtype=np.float64); ds=np.linalg.norm(X-c,axis=1); exact=np.where(ds<=1e-15)[0]
    if len(exact): return Y[int(exact[0])].copy()
    k=min(int(model['neighbors']),len(ds)); idx=np.argsort(ds,kind='stable')[:k]; w=1.0/np.power(ds[idx],float(model['power'])); return (w[:,None]*Y[idx]).sum(axis=0)/w.sum()
def fit_candidate(recs:list[dict[str,Any]],spec:dict[str,Any],scales:np.ndarray)->dict[str,Any]:
    p=fit_primary_ridge(recs,spec['primaryBasis'],spec['primaryRidge'],scales)
    if spec['kind']=='UNCERTAINTY_WEIGHTED_SPLIT_RIDGE': s=fit_weighted_shape_ridge(recs,spec['shapeBasis'],spec['shapeRidge'],scales)
    else: s=fit_idw_shape(recs,spec['neighbors'],spec['power'],scales)
    return {'kind':spec['kind'],'primary':p,'shape':s}
def predict(model:dict[str,Any],g:dict[str,Any])->np.ndarray:
    y=np.concatenate([predict_primary(model['primary'],g),predict_shape(model['shape'],g)]); req(y.shape==(13,) and np.all(np.isfinite(y)),'nonfinite prediction'); return y

def candidate_specs(p:dict[str,Any])->list[dict[str,Any]]:
    out=[]
    for fam in p['modelSelection']['candidateFamilies']:
        if fam['kind']=='UNCERTAINTY_WEIGHTED_SPLIT_RIDGE':
            for pr in fam['primaryRidgeValues']:
                for sr in fam['shapeRidgeValues']: out.append({'familyId':fam['familyId'],'kind':fam['kind'],'complexityRank':fam['complexityRank'],'primaryBasis':fam['primaryBasis'],'shapeBasis':fam['shapeBasis'],'primaryRidge':float(pr),'shapeRidge':float(sr)})
        else:
            for pr in fam['primaryRidgeValues']:
                for k in fam['neighbors']:
                    for pw in fam['powers']: out.append({'familyId':fam['familyId'],'kind':fam['kind'],'complexityRank':fam['complexityRank'],'primaryBasis':fam['primaryBasis'],'primaryRidge':float(pr),'neighbors':int(k),'power':float(pw)})
    req(len(out)==p['modelSelection']['candidateCountRequired'],'candidate count drift'); return out

def boundary_predicates():
    return [('sun-shallow',lambda g:float(g['sunDepressionDeg'])<=4.0),('sun-deep-core',lambda g:8.5<=float(g['sunDepressionDeg'])<=10.5),('az-low',lambda g:float(g['relativeAzimuthDeg'])<=60.0),('az-high',lambda g:float(g['relativeAzimuthDeg'])>=150.0),('alt-low',lambda g:float(g['targetAltitudeDeg'])<=20.0),('alt-high',lambda g:float(g['targetAltitudeDeg'])>=65.0),('aod-low',lambda g:float(g['aod550'])<=0.10),('aod-high',lambda g:float(g['aod550'])>=0.35),('elev-low',lambda g:float(g['observerElevationM'])<=500.0),('elev-high',lambda g:float(g['observerElevationM'])>=2000.0)]
def folds(recs:list[dict[str,Any]],p:dict[str,Any],enforce_counts:bool=True)->list[dict[str,Any]]:
    order=sorted(range(len(recs)),key=lambda i:str(recs[i]['geometryId'])); out=[]
    for k in range(5):
        val=[idx for pos,idx in enumerate(order) if pos%5==k]; vs=set(val); out.append({'name':f'balanced-{k}','kind':'balanced','fit':[i for i in range(len(recs)) if i not in vs],'val':val})
    for name,pred in boundary_predicates():
        val=[i for i,r in enumerate(recs) if pred(r['geometry'])]; vs=set(val); out.append({'name':name,'kind':'boundary','fit':[i for i in range(len(recs)) if i not in vs],'val':val})
    for i in order: out.append({'name':f'loo-{recs[i]["geometryId"]}','kind':'loo','fit':[j for j in range(len(recs)) if j!=i],'val':[i]})
    cv=p['modelSelection']['crossValidationFolds']; req(len(out)==59,'fold count drift'); req([len(x['val']) for x in out[:5]]==cv['expectedBalancedFoldCounts'],'balanced counts drift')
    if enforce_counts: req({x['name']:len(x['val']) for x in out[5:15]}==cv['expectedBoundaryFoldCounts'],'boundary counts drift')
    return out

def evaluate_candidate(recs:list[dict[str,Any]],spec:dict[str,Any],p:dict[str,Any],scales:np.ndarray,enforce_counts:bool=True)->dict[str,Any]:
    rows=[]; loo_primary=[]; loo_single=[]; loo_raw=[]; loo_ua=[]; loo_uasing=[]; loo_base=[]
    for f in folds(recs,p,enforce_counts):
        fit=[recs[i] for i in f['fit']]; model=fit_candidate(fit,spec,scales); base=np.mean(np.vstack([targets_and_shape_se(r,scales)[0] for r in fit]),axis=0)
        prim=[]; sing=[]; raw=[]; ua=[]; uasing=[]; basep=[]
        for i in f['val']:
            truth,u=targets_and_shape_se(recs[i],scales); pred=predict(model,recs[i]['geometry']); pe=np.abs(pred[:3]-truth[:3]); se=pred[3:]-truth[3:]; denom=np.sqrt(1.0+u*u)
            prim.append(float(np.mean(pe))); sing.append(float(np.max(pe))); raw.append(float(np.sqrt(np.mean(se*se)))); ua.append(float(np.sqrt(np.mean((se/denom)**2)))); uasing.append(float(np.max(np.abs(se)/denom)); basep.append(float(np.mean(np.abs(base[:3]-truth[:3]))))
        row={'fold':f['name'],'kind':f['kind'],'count':len(f['val']),'primaryMale':float(np.mean(prim)),'worstSinglePrimaryLogError':max(sing),'rawShapeNrmse':float(np.mean(raw)),'uncertaintyAdjustedShapeNrmse':float(np.mean(ua)),'worstUncertaintyAdjustedSingleCoefficientError':max(uasing)}; rows.append(row)
        if f['kind']=='loo': loo_primary+=prim; loo_single+=sing; loo_raw+=raw; loo_ua+=ua; loo_uasing+=uasing; loo_base+=basep
    req(len(loo_primary)==44,'LOO count drift'); b=[x for x in rows if x['kind']=='boundary']; baseline=float(np.mean(loo_base)); lm=float(np.mean(loo_primary)); lraw=float(np.mean(loo_raw)); imp=1.0-lm/baseline
    vals={'looMeanPrimaryMale':lm,'looWorstSinglePrimaryLogError':max(loo_single),'looMeanRawShapeNrmse':lraw,'looWorstRawShapeNrmseReportOnly':max(loo_raw),'looWorstUncertaintyAdjustedShapeNrmse':max(loo_ua),'looWorstUncertaintyAdjustedSingleCoefficientError':max(loo_uasing),'boundaryWorstPrimaryMale':max(x['primaryMale'] for x in b),'boundaryWorstRawShapeNrmse':max(x['rawShapeNrmse'] for x in b),'looFoldMatchedTrainingMeanBaselinePrimaryMale':baseline,'looPrimaryImprovementVsBaselineFraction':imp}
    g=p['modelSelection']['trainingOnlyReadinessGates']; checks={'looMeanPrimary':vals['looMeanPrimaryMale']<=g['looMeanPrimaryMaleMax'],'looWorstSinglePrimary':vals['looWorstSinglePrimaryLogError']<=g['looWorstSinglePrimaryLogErrorMax'],'looMeanRawShape':vals['looMeanRawShapeNrmse']<=g['looMeanRawShapeNrmseMax'],'looWorstUncertaintyAdjustedShape':vals['looWorstUncertaintyAdjustedShapeNrmse']<=g['looWorstUncertaintyAdjustedShapeNrmseMax'],'looWorstUncertaintyAdjustedSingleCoefficient':vals['looWorstUncertaintyAdjustedSingleCoefficientError']<=g['looWorstUncertaintyAdjustedSingleCoefficientErrorMax'],'boundaryWorstPrimary':vals['boundaryWorstPrimaryMale']<=g['boundaryWorstPrimaryMaleMax'],'boundaryWorstRawShape':vals['boundaryWorstRawShapeNrmse']<=g['boundaryWorstRawShapeNrmseMax'],'looPrimaryBaselineImprovement':vals['looPrimaryImprovementVsBaselineFraction']>=g['looPrimaryMustBeatFoldMatchedTrainingMeanBaselineByFraction']}
    score=max(vals['looMeanPrimaryMale']/0.25,vals['looWorstSinglePrimaryLogError']/0.9,vals['looMeanRawShapeNrmse']/1.0,vals['looWorstUncertaintyAdjustedShapeNrmse']/1.45,vals['looWorstUncertaintyAdjustedSingleCoefficientError']/3.0,vals['boundaryWorstPrimaryMale']/0.30,vals['boundaryWorstRawShapeNrmse']/1.45)+0.10*((vals['looMeanPrimaryMale']/0.25)+(vals['looMeanRawShapeNrmse']/1.0))
    return {**spec,**vals,'eligible':all(checks.values()),'gateChecks':checks,'selectionScore':float(score),'foldMetrics':rows}

def hyper_key(r:dict[str,Any])->str:
    return json.dumps({k:r[k] for k in ('primaryRidge','shapeRidge','neighbors','power') if k in r},sort_keys=True,separators=(',',':'))
def ranking_key(r:dict[str,Any])->tuple:
    return (float(r['selectionScore']),float(r['looWorstUncertaintyAdjustedShapeNrmse']),float(r['boundaryWorstPrimaryMale']),float(r['looMeanRawShapeNrmse']),float(r['looMeanPrimaryMale']),int(r['complexityRank']),str(r['familyId']),hyper_key(r))
def select(recs:list[dict[str,Any]],p:dict[str,Any],enforce_counts:bool=True)->tuple[dict[str,Any]|None,list[dict[str,Any]]]:
    scales=np.asarray(p['sourceTrainingRepresentation']['nullspaceCoefficientScales'],dtype=np.float64); results=[evaluate_candidate(recs,s,p,scales,enforce_counts) for s in candidate_specs(p)]; elig=sorted([x for x in results if x['eligible']],key=ranking_key); return (elig[0] if elig else None),sorted(results,key=lambda x:(not x['eligible'],*ranking_key(x)))

def validate_dataset(d:dict[str,Any],p:dict[str,Any],file_bytes:bytes|None=None)->list[dict[str,Any]]:
    if file_bytes is not None: req(sha256_bytes(file_bytes)==DATASET_FILE_SHA256,'dataset file SHA drift')
    req(d.get('datasetSha256')==DATASET_CANONICAL_SHA256,'dataset canonical SHA drift'); req((d.get('geometryCount'),d.get('representationFeatureCount'),d.get('protectedHoldoutRecordCount'),d.get('holdoutValuesRead'))==(44,13,0,False),'dataset role/dimension drift'); recs=d.get('records') or []; req(len(recs)==44,'44 records required'); ids=[r.get('geometryId') for r in recs]; req(ids==p['roleIsolation']['exactTrainingGeometryIds'],'training IDs/order drift'); req(not set(ids)&set(p['roleIsolation']['openedV1ProtectedDiagnosticOnlyGeometryIds']),'opened geometry present'); scales=np.asarray(p['sourceTrainingRepresentation']['nullspaceCoefficientScales'],dtype=np.float64)
    for r in recs: targets_and_shape_se(r,scales); basis(r['geometry'],'PHYSICAL_COMPACT_16_TERMS')
    return recs

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req_obj,fp,code,msg,headers,newurl): return None
def download_dataset(token:str)->tuple[dict[str,Any],str]:
    req(token,'GITHUB_TOKEN required'); h={'Authorization':f'Bearer {token}','Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'level-b-v2-training-fit-v2'}; meta=json.loads(urllib.request.urlopen(urllib.request.Request(f'https://api.github.com/repos/{REPO}/actions/artifacts/{ARTIFACT_ID}',headers=h),timeout=60).read()); req(meta.get('expired') is False and meta.get('digest')=='sha256:'+ARTIFACT_DIGEST,'artifact metadata drift'); op=urllib.request.build_opener(NoRedirect); zreq=urllib.request.Request(f'https://api.github.com/repos/{REPO}/actions/artifacts/{ARTIFACT_ID}/zip',headers={k:v for k,v in h.items() if k!='Accept'})
    try: response=op.open(zreq,timeout=60)
    except urllib.error.HTTPError as e: req(e.code in (301,302,303,307,308) and e.headers.get('Location'),'artifact redirect missing'); loc=e.headers['Location']
    else:
        with response: blob=response.read(); req(sha256_bytes(blob)==ARTIFACT_DIGEST,'artifact ZIP digest drift'); loc=None
    if loc:
        with urllib.request.urlopen(urllib.request.Request(loc,headers={'User-Agent':'level-b-v2-training-fit-v2'}),timeout=120) as response: blob=response.read()
        req(sha256_bytes(blob)==ARTIFACT_DIGEST,'artifact ZIP digest drift')
    with zipfile.ZipFile(io.BytesIO(blob)) as z: req(DATASET_MEMBER in z.namelist(),'dataset member missing'); raw=z.read(DATASET_MEMBER)
    req(sha256_bytes(raw)==DATASET_FILE_SHA256,'dataset file hash drift'); d=json.loads(raw.decode()); return d,sha256_bytes(blob)

def synthetic_records(p:dict[str,Any])->list[dict[str,Any]]:
    scales=np.asarray(p['sourceTrainingRepresentation']['nullspaceCoefficientScales']); recs=[]; suns=[2,3,4,6,8.5,9,10,10.5]; alts=[5,10,20,30,50,65,70,80]; azs=[0,30,60,90,150,160,180]; elevs=[0,250,500,1000,2000,2250,2500]; aods=[.05,.08,.10,.20,.35,.38,.40]
    for i in range(44):
        g={'sunDepressionDeg':suns[i%8],'targetAltitudeDeg':alts[(i*3)%8],'relativeAzimuthDeg':azs[(i*5)%7],'observerElevationM':elevs[(i*2)%7],'aod550':aods[(i*4)%7]}; x=basis(g,'PHYSICAL_COMPACT_16_TERMS'); y=np.zeros(13); y[:3]=[.5+.8*x[1]-.2*x[2]+.1*x[3],1+.7*x[1]-.15*x[2]+.08*x[3],-1.2+.75*x[1]-.18*x[2]+.09*x[3]]
        for j in range(10): y[3+j]=(.15/(j+1))*x[1]+(.08/(j+1))*x[2]-(.04/(j+1))*x[3]
        ch={k:{'mean':float(math.exp(y[j])),'standardError':float(math.exp(y[j])*.02)} for j,k in enumerate(CHANNELS)}; pcs=[{'mean':float(y[3+j]*scales[j]),'standardError':float((.05+.02*((i+j)%3))*scales[j])} for j in range(10)]; recs.append({'geometryId':f'synthetic-{i:04d}','geometry':g,'integratedChannels':ch,'nullspacePcaCoefficients':pcs})
    return recs

def execute(p:dict[str,Any],out:Path)->None:
    req(np.__version__=='2.3.2',f'numpy version drift: {np.__version__}'); d,zsha=download_dataset(os.environ.get('GITHUB_TOKEN','')); recs=validate_dataset(d,p); best,ranking=select(recs,p); selection={'schemaVersion':2,'stageId':'level-b-v2-training-selection-v2','status':'TRAINING_ONLY_GENERATION2_SELECTION_COMPLETE' if best else 'NO_GENERATION2_CANDIDATE_PASSES_TRAINING_ONLY_READINESS','protocolId':p['protocolId'],'sourceArtifactId':ARTIFACT_ID,'sourceArtifactZipSha256':zsha,'sourceDatasetCanonicalSha256':DATASET_CANONICAL_SHA256,'trainingGeometryCount':44,'candidateCount':len(ranking),'eligibleCandidateCount':sum(x['eligible'] for x in ranking),'selectedCandidate':None if best is None else {k:best[k] for k in best if k in ('familyId','kind','complexityRank','primaryBasis','shapeBasis','primaryRidge','shapeRidge','neighbors','power','selectionScore')},'candidates':ranking,'generation1ResultRemainsFailed':True,'ordinal22ValuesRead':False,'protectedValidationOpened':False}; selection['selectionSha256']=canonical_sha({k:v for k,v in selection.items() if k!='selectionSha256'}); out.mkdir(parents=True,exist_ok=True); write_json(out/'training-selection-v2-generation2.json',selection)
    if best is None:
        result={'schemaVersion':2,'stageId':'level-b-v2-training-fit-result-v2','status':'NO_GENERATION2_CANDIDATE_PASSES_TRAINING_ONLY_READINESS','trainingSelectionSha256':selection['selectionSha256'],'modelArtifactWritten':False,'generation1ResultRemainsFailed':True,'ordinal22ValuesRead':False,'protectedValidationAuthorized':False,'productionPromotionAuthorized':False}; result['resultSha256']=canonical_sha({k:v for k,v in result.items() if k!='resultSha256'}); write_json(out/'training-fit-result-v2-generation2.json',result); return
    scales=np.asarray(p['sourceTrainingRepresentation']['nullspaceCoefficientScales'],dtype=np.float64); model=fit_candidate(recs,best,scales); artifact={'schemaVersion':2,'stageId':'level-b-v2-model-artifact-generation2-v1','protocolId':p['protocolId'],'trainingGeometryCount':44,'sourceDatasetCanonicalSha256':DATASET_CANONICAL_SHA256,'selectedSpec':{k:best[k] for k in best if k in ('familyId','kind','complexityRank','primaryBasis','shapeBasis','primaryRidge','shapeRidge','neighbors','power')},'model':model,'nullspaceCoefficientScales':scales.tolist(),'trainingSelectionSha256':selection['selectionSha256'],'generation1ResultRemainsFailed':True,'holdoutValuesRead':False,'protectedHoldoutRecordCount':0,'protectedValidationAuthorized':False,'productionPromotionAuthorized':False}; artifact['modelSha256']=canonical_sha({k:v for k,v in artifact.items() if k!='modelSha256'}); write_json(out/'model-artifact-v2-generation2.json',artifact); metrics={k:best[k] for k in ('selectionScore','looMeanPrimaryMale','looWorstSinglePrimaryLogError','looMeanRawShapeNrmse','looWorstRawShapeNrmseReportOnly','looWorstUncertaintyAdjustedShapeNrmse','looWorstUncertaintyAdjustedSingleCoefficientError','boundaryWorstPrimaryMale','boundaryWorstRawShapeNrmse','looPrimaryImprovementVsBaselineFraction')}; result={'schemaVersion':2,'stageId':'level-b-v2-training-fit-result-v2','status':'TRAINING_ONLY_GENERATION2_MODEL_FROZEN','trainingSelectionSha256':selection['selectionSha256'],'modelArtifactWritten':True,'modelSha256':artifact['modelSha256'],'selectedSpec':artifact['selectedSpec'],'selectedTrainingMetrics':metrics,'generation1ResultRemainsFailed':True,'ordinal22ValuesRead':False,'protectedValidationAuthorized':False,'productionPromotionAuthorized':False}; result['resultSha256']=canonical_sha({k:v for k,v in result.items() if k!='resultSha256'}); write_json(out/'training-fit-result-v2-generation2.json',result)

def main()->int:
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='cmd',required=True); s=sub.add_parser('synthetic'); s.add_argument('--protocol',type=Path,required=True); e=sub.add_parser('execute'); e.add_argument('--protocol',type=Path,required=True); e.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    try:
        p=load_json(a.protocol)
        if a.cmd=='synthetic': recs=synthetic_records(p); best,ranking=select(recs,p,enforce_counts=False); req(len(ranking)==230,'synthetic candidate count drift'); req(best is not None,'synthetic no eligible candidate'); print(json.dumps({'status':'SYNTHETIC_PASS','candidateCount':len(ranking),'selected':best['familyId']},sort_keys=True))
        else: execute(p,a.output)
        return 0
    except Exception as e: print(json.dumps({'status':'REFUSED','reason':str(e)},sort_keys=True),file=os.sys.stderr); return 2
if __name__=='__main__': raise SystemExit(main())
