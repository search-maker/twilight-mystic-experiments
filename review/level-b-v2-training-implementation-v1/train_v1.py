#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

import numpy as np

REPO = 'search-maker/twilight-mystic-experiments'
ARTIFACT_ID = 9208203541
ARTIFACT_DIGEST = '2fe50ed674155f440322c92d28877f5c022f0cc5fa13e1e601596a9902482815'
DATASET_MEMBER = 'training-representation-dataset-v2.json'
DATASET_FILE_SHA256 = '066d6be846fa9b3bdd7236e327894f64d52ea56aa7e7b6e6af4d51d849eb1a61'
DATASET_CANONICAL_SHA256 = 'bb7908426d9d545f43c082aebbaab1829a486e2962d0b9ee34a5e8bef5390133'
CHANNELS = ('photopicLuminanceCdM2','scotopicLuminanceScotCdM2','johnsonVEffectiveRadiance_mW_m2_nm_sr')

class Refusal(RuntimeError):
    pass

def req(cond: bool, msg: str) -> None:
    if not cond:
        raise Refusal(msg)

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def canonical_sha(v: Any) -> str:
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def load_json(path: Path) -> dict[str,Any]:
    x=json.loads(path.read_text(encoding='utf-8'))
    req(isinstance(x,dict),f'object required: {path}')
    return x

def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')

def raw_cos(g: dict[str,Any]) -> np.ndarray:
    return np.array([
        (float(g['sunDepressionDeg'])-2.0)/8.5,
        (float(g['targetAltitudeDeg'])-5.0)/75.0,
        math.cos(math.radians(float(g['relativeAzimuthDeg']))),
        float(g['observerElevationM'])/2500.0,
        (float(g['aod550'])-0.05)/0.35,
    ],dtype=np.float64)

def physical(g: dict[str,Any]) -> np.ndarray:
    aod=float(g['aod550']); req(aod>0,'positive AOD required')
    return np.array([
        (float(g['sunDepressionDeg'])-2.0)/8.5,
        math.sin(math.radians(float(g['targetAltitudeDeg']))),
        math.cos(math.radians(float(g['relativeAzimuthDeg']))),
        float(g['observerElevationM'])/2500.0,
        math.log(aod/0.05)/math.log(8.0),
    ],dtype=np.float64)

def basis(g: dict[str,Any], name: str) -> np.ndarray:
    if name=='COS_COMPACT_13_TERMS':
        s,a,c,e,o=raw_cos(g)
        out=[1,s,a,c,e,o,s*s,a*a,c*c,s*a,s*c,s*o,a*c]
    else:
        s,a,c,e,o=physical(g)
        compact=[1,s,a,c,e,o,s*s,a*a,c*c,o*o,s*a,s*c,s*o,a*c,a*o,c*o]
        if name=='PHYSICAL_COMPACT_16_TERMS':
            out=compact
        elif name=='PHYSICAL_COMPACT_16_PLUS_S_A_O_CUBICS_19_TERMS':
            out=[*compact,s**3,a**3,o**3]
        elif name=='FULL_DEGREE2_ON_FIVE_PHYSICAL_COORDINATES_21_TERMS':
            v=(s,a,c,e,o); out=[1,*v]
            for i in range(5):
                for j in range(i,5): out.append(v[i]*v[j])
        else:
            raise Refusal(f'unknown basis: {name}')
    x=np.asarray(out,dtype=np.float64); req(np.all(np.isfinite(x)),'nonfinite basis'); return x

def target(rec: dict[str,Any], scales: np.ndarray) -> np.ndarray:
    vals=[]
    ch=rec.get('integratedChannels') or {}
    for k in CHANNELS:
        mean=float((ch.get(k) or {}).get('mean'))
        req(math.isfinite(mean) and mean>0,f'positive channel required: {rec.get("geometryId")} {k}')
        vals.append(math.log(mean))
    pcs=rec.get('nullspacePcaCoefficients') or []
    req(len(pcs)==10,'ten PCA coefficients required')
    for j,x in enumerate(pcs):
        mean=float((x or {}).get('mean')); req(math.isfinite(mean),'finite PCA coefficient required')
        vals.append(mean/float(scales[j]))
    y=np.asarray(vals,dtype=np.float64); req(y.shape==(13,) and np.all(np.isfinite(y)),'target shape drift'); return y

def fit_split_ridge(recs: list[dict[str,Any]], basis_name: str, primary_ridge: float, shape_ridge: float, scales: np.ndarray) -> dict[str,Any]:
    req(primary_ridge>0 and shape_ridge>0,'positive ridges required')
    X=np.vstack([basis(r['geometry'],basis_name) for r in recs])
    Y=np.vstack([target(r,scales) for r in recs])
    G=X.T@X; P=np.eye(G.shape[0],dtype=np.float64); P[0,0]=0.0
    bp=np.linalg.solve(G+primary_ridge*P,X.T@Y[:,:3])
    bs=np.linalg.solve(G+shape_ridge*P,X.T@Y[:,3:])
    req(np.all(np.isfinite(bp)) and np.all(np.isfinite(bs)),'nonfinite ridge state')
    return {'kind':'SPLIT_RIDGE','basis':basis_name,'primaryRidge':float(primary_ridge),'shapeRidge':float(shape_ridge),'primaryCoefficients':bp.tolist(),'shapeCoefficients':bs.tolist()}

def predict(model: dict[str,Any], g: dict[str,Any]) -> np.ndarray:
    x=basis(g,str(model['basis']))
    p=x@np.asarray(model['primaryCoefficients'],dtype=np.float64)
    s=x@np.asarray(model['shapeCoefficients'],dtype=np.float64)
    y=np.concatenate([p,s]); req(y.shape==(13,) and np.all(np.isfinite(y)),'nonfinite prediction'); return y

def boundary_predicates():
    return [
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

def folds(recs: list[dict[str,Any]], protocol: dict[str,Any], enforce_expected_counts: bool=True) -> list[dict[str,Any]]:
    order=sorted(range(len(recs)),key=lambda i:str(recs[i]['geometryId']))
    out=[]
    for k in range(5):
        val=[idx for pos,idx in enumerate(order) if pos%5==k]; vs=set(val)
        out.append({'name':f'balanced-{k}','kind':'balanced','fit':[i for i in range(len(recs)) if i not in vs],'val':val})
    for name,pred in boundary_predicates():
        val=[i for i,r in enumerate(recs) if pred(r['geometry'])]; vs=set(val)
        out.append({'name':name,'kind':'boundary','fit':[i for i in range(len(recs)) if i not in vs],'val':val})
    for idx in order:
        out.append({'name':f'loo-{recs[idx]["geometryId"]}','kind':'loo','fit':[i for i in range(len(recs)) if i!=idx],'val':[idx]})
    cv=(protocol['modelSelection']['crossValidationFolds'])
    req(len(out)==cv['totalFoldCountRequired'],'fold count drift')
    req([len(x['val']) for x in out[:5]]==cv['expectedBalancedFoldCounts'],'balanced fold count drift')
    got={x['name']:len(x['val']) for x in out[5:15]}
    if enforce_expected_counts:
        req(got==cv['expectedBoundaryFoldCounts'],'boundary fold count drift')
    return out

def candidate_specs(protocol: dict[str,Any]) -> list[dict[str,Any]]:
    out=[]
    for fam in protocol['modelSelection']['candidateFamilies']:
        for pr in fam['primaryRidgeValues']:
            for sr in fam['shapeRidgeValues']:
                out.append({'familyId':fam['familyId'],'basis':fam['basis'],'complexityRank':fam['complexityRank'],'primaryRidge':float(pr),'shapeRidge':float(sr)})
    req(len(out)==protocol['modelSelection']['candidateCountRequired'],'candidate count drift')
    return out

def eval_candidate(recs: list[dict[str,Any]], spec: dict[str,Any], protocol: dict[str,Any], scales: np.ndarray, enforce_expected_counts: bool=True) -> dict[str,Any]:
    rows=[]; loo_primary=[]; loo_shape=[]; loo_single=[]; loo_baseline=[]
    for f in folds(recs,protocol,enforce_expected_counts=enforce_expected_counts):
        fit=[recs[i] for i in f['fit']]; val=[recs[i] for i in f['val']]
        model=fit_split_ridge(fit,spec['basis'],spec['primaryRidge'],spec['shapeRidge'],scales)
        base=np.mean(np.vstack([target(r,scales) for r in fit]),axis=0)
        prim=[]; shape=[]; single=[]; basep=[]
        for r in val:
            truth=target(r,scales); pred=predict(model,r['geometry']); pe=np.abs(pred[:3]-truth[:3])
            prim.append(float(np.mean(pe))); shape.append(float(np.sqrt(np.mean((pred[3:]-truth[3:])**2)))); single.append(float(np.max(pe))); basep.append(float(np.mean(np.abs(base[:3]-truth[:3]))))
        row={'fold':f['name'],'kind':f['kind'],'count':len(val),'primaryMale':float(np.mean(prim)),'shapeNrmse':float(np.mean(shape)),'worstSinglePrimaryLogError':max(single)}
        rows.append(row)
        if f['kind']=='loo':
            loo_primary.extend(prim); loo_shape.extend(shape); loo_single.extend(single); loo_baseline.extend(basep)
    req(len(loo_primary)==44,'LOO record count drift')
    boundary=[r for r in rows if r['kind']=='boundary']
    balanced=[r for r in rows if r['kind']=='balanced']
    lm=float(np.mean(loo_primary)); ls=float(np.mean(loo_shape)); lws=max(loo_single); lwshape=max(loo_shape)
    bwp=max(r['primaryMale'] for r in boundary); bws=max(r['shapeNrmse'] for r in boundary)
    baseline=float(np.mean(loo_baseline)); improve=1.0-lm/baseline
    gates=protocol['modelSelection']['trainingOnlyReadinessGates']
    checks={
        'looMeanPrimary':lm<=gates['looMeanPrimaryMaleMax'],
        'looWorstSinglePrimary':lws<=gates['looWorstSinglePrimaryLogErrorMax'],
        'looMeanShape':ls<=gates['looMeanShapeNrmseMax'],
        'looWorstShape':lwshape<=gates['looWorstShapeNrmseMax'],
        'boundaryWorstPrimary':bwp<=gates['boundaryWorstPrimaryMaleMax'],
        'boundaryWorstShape':bws<=gates['boundaryWorstShapeNrmseMax'],
        'looPrimaryBaselineImprovement':improve>=gates['looPrimaryMustBeatFoldMatchedTrainingMeanBaselineByFraction'],
    }
    score=max(lm/0.25,ls/1.0,lws/0.9,lwshape/1.45,bwp/0.3,bws/1.45)+0.10*((lm/0.25)+(ls/1.0))
    return {
        **spec,
        'eligible':all(checks.values()),
        'gateChecks':checks,
        'selectionScore':float(score),
        'looMeanPrimaryMale':lm,
        'looWorstSinglePrimaryLogError':lws,
        'looMeanShapeNrmse':ls,
        'looWorstShapeNrmse':lwshape,
        'boundaryWorstPrimaryMale':bwp,
        'boundaryWorstShapeNrmse':bws,
        'looFoldMatchedTrainingMeanBaselinePrimaryMale':baseline,
        'looPrimaryImprovementVsBaselineFraction':float(improve),
        'balancedMeanPrimaryMale':float(np.mean([r['primaryMale'] for r in balanced])),
        'balancedMeanShapeNrmse':float(np.mean([r['shapeNrmse'] for r in balanced])),
        'foldMetrics':rows,
    }

def ranking_key(x: dict[str,Any]) -> tuple:
    return (float(x['selectionScore']),float(x['boundaryWorstShapeNrmse']),float(x['looMeanPrimaryMale']),int(x['complexityRank']),str(x['familyId']),float(x['primaryRidge']),float(x['shapeRidge']))

def select(recs: list[dict[str,Any]], protocol: dict[str,Any], enforce_expected_counts: bool=True) -> tuple[dict[str,Any]|None,list[dict[str,Any]]]:
    scales=np.asarray(protocol['sourceTrainingRepresentation']['nullspaceCoefficientScales'],dtype=np.float64)
    results=[eval_candidate(recs,s,protocol,scales,enforce_expected_counts=enforce_expected_counts) for s in candidate_specs(protocol)]
    eligible=sorted([r for r in results if r['eligible']],key=ranking_key)
    return (eligible[0] if eligible else None),sorted(results,key=lambda r:(not r['eligible'],*ranking_key(r)))

def validate_dataset(d: dict[str,Any], protocol: dict[str,Any], file_bytes: bytes|None=None) -> list[dict[str,Any]]:
    if file_bytes is not None: req(sha256_bytes(file_bytes)==DATASET_FILE_SHA256,'dataset file hash drift')
    req(d.get('datasetSha256')==DATASET_CANONICAL_SHA256,'dataset canonical identity drift')
    req((d.get('geometryCount'),d.get('representationFeatureCount'),d.get('protectedHoldoutRecordCount'),d.get('holdoutValuesRead'))==(44,13,0,False),'dataset dimensions/role drift')
    recs=d.get('records') or []; req(isinstance(recs,list) and len(recs)==44,'44 records required')
    ids=[str(r.get('geometryId')) for r in recs]
    req(ids==protocol['roleIsolation']['exactTrainingGeometryIds'],'training record identity/order drift')
    req(not set(ids)&set(protocol['roleIsolation']['openedV1ProtectedDiagnosticOnlyGeometryIds']),'opened v1 geometry present')
    scales=np.asarray(protocol['sourceTrainingRepresentation']['nullspaceCoefficientScales'],dtype=np.float64)
    for r in recs: target(r,scales); basis(r['geometry'],'COS_COMPACT_13_TERMS')
    return recs

def download_training_dataset(token: str) -> tuple[dict[str,Any],str]:
    req(bool(token),'GITHUB_TOKEN required')
    url=f'https://api.github.com/repos/{REPO}/actions/artifacts/{ARTIFACT_ID}/zip'
    request=urllib.request.Request(url,headers={'Authorization':f'Bearer {token}','Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'level-b-v2-training-fit-v1'})
    with urllib.request.urlopen(request,timeout=120) as resp: blob=resp.read()
    req(sha256_bytes(blob)==ARTIFACT_DIGEST,'artifact ZIP digest drift')
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        req(DATASET_MEMBER in z.namelist(),'training dataset member missing'); raw=z.read(DATASET_MEMBER)
    req(sha256_bytes(raw)==DATASET_FILE_SHA256,'dataset file SHA drift')
    d=json.loads(raw.decode('utf-8')); req(isinstance(d,dict),'dataset object required')
    return d,sha256_bytes(blob)

def synthetic_records() -> list[dict[str,Any]]:
    recs=[]
    suns=[2.0,3.0,4.0,6.0,8.5,9.0,10.0,10.5]
    alts=[5.0,10.0,20.0,30.0,50.0,65.0,70.0,80.0]
    azs=[0.0,30.0,60.0,90.0,150.0,160.0,180.0]
    elevs=[0.0,250.0,500.0,1000.0,2000.0,2250.0,2500.0]
    aods=[0.05,0.08,0.10,0.20,0.35,0.38,0.40]
    for i in range(44):
        g={'sunDepressionDeg':suns[i%len(suns)],'targetAltitudeDeg':alts[(i*3)%len(alts)],'relativeAzimuthDeg':azs[(i*5)%len(azs)],'observerElevationM':elevs[(i*2)%len(elevs)],'aod550':aods[(i*4)%len(aods)]}
        x=basis(g,'COS_COMPACT_13_TERMS')
        y=np.zeros(13,dtype=np.float64)
        y[0]=0.5+0.8*x[1]-0.2*x[2]+0.1*x[3]; y[1]=1.0+0.7*x[1]-0.15*x[2]+0.08*x[3]; y[2]=-1.2+0.75*x[1]-0.18*x[2]+0.09*x[3]
        for j in range(10): y[3+j]=(0.15/(j+1))*x[1]+(0.08/(j+1))*x[2]-(0.04/(j+1))*x[3]
        channels={k:{'mean':float(math.exp(y[j]))} for j,k in enumerate(CHANNELS)}
        scales=np.asarray([0.27729231126929754,0.09054255337405856,0.04362631407125976,0.00791831782256918,0.0046149233253235545,0.002441189933423995,0.0015868955715692872,0.0008860617219488324,0.0004930249648425277,0.00021007512113759737],dtype=np.float64)
        pcs=[{'mean':float(y[3+j]*scales[j])} for j in range(10)]
        recs.append({'geometryId':f'synthetic-{i:04d}','geometry':g,'integratedChannels':channels,'nullspacePcaCoefficients':pcs})
    return recs

def execute(protocol: dict[str,Any], output: Path) -> None:
    req(np.__version__=='2.3.2',f'numpy version drift: {np.__version__}')
    d,zipsha=download_training_dataset(os.environ.get('GITHUB_TOKEN',''))
    recs=validate_dataset(d,protocol)
    best,ranking=select(recs,protocol)
    selection={
        'schemaVersion':1,'stageId':'level-b-v2-training-selection-v1','status':'TRAINING_ONLY_SELECTION_COMPLETE' if best else 'NO_V2_CANDIDATE_PASSES_TRAINING_ONLY_READINESS',
        'protocolId':protocol['protocolId'],'sourceArtifactId':ARTIFACT_ID,'sourceArtifactZipSha256':zipsha,'sourceDatasetCanonicalSha256':DATASET_CANONICAL_SHA256,
        'trainingGeometryCount':44,'candidateCount':len(ranking),'eligibleCandidateCount':sum(1 for r in ranking if r['eligible']),'selectedCandidate':None if best is None else {k:best[k] for k in ('familyId','basis','complexityRank','primaryRidge','shapeRidge','selectionScore')},
        'candidates':ranking,'ordinal22ValuesRead':False,'protectedValidationOpened':False,
    }
    selection['selectionSha256']=canonical_sha({k:v for k,v in selection.items() if k!='selectionSha256'})
    output.mkdir(parents=True,exist_ok=True); write_json(output/'training-selection-v2.json',selection)
    if best is None:
        result={'schemaVersion':1,'stageId':'level-b-v2-training-fit-result-v1','status':'NO_V2_CANDIDATE_PASSES_TRAINING_ONLY_READINESS','trainingSelectionSha256':selection['selectionSha256'],'modelArtifactWritten':False,'ordinal22ValuesRead':False,'protectedValidationAuthorized':False,'productionPromotionAuthorized':False}
        result['resultSha256']=canonical_sha({k:v for k,v in result.items() if k!='resultSha256'}); write_json(output/'training-fit-result-v2.json',result); return
    scales=np.asarray(protocol['sourceTrainingRepresentation']['nullspaceCoefficientScales'],dtype=np.float64)
    model=fit_split_ridge(recs,best['basis'],best['primaryRidge'],best['shapeRidge'],scales)
    artifact={'schemaVersion':1,'stageId':'level-b-v2-model-artifact-v1','protocolId':protocol['protocolId'],'trainingGeometryCount':44,'sourceDatasetCanonicalSha256':DATASET_CANONICAL_SHA256,'familyId':best['familyId'],'basis':best['basis'],'complexityRank':best['complexityRank'],'primaryRidge':best['primaryRidge'],'shapeRidge':best['shapeRidge'],'targetNames':[ *CHANNELS, *[f'nullspacePcaCoefficient{i}' for i in range(10)] ],'nullspaceCoefficientScales':scales.tolist(),'model':model,'trainingSelectionSha256':selection['selectionSha256'],'holdoutValuesRead':False,'protectedHoldoutRecordCount':0,'protectedValidationAuthorized':False,'productionPromotionAuthorized':False}
    artifact['modelSha256']=canonical_sha({k:v for k,v in artifact.items() if k!='modelSha256'})
    write_json(output/'model-artifact-v2.json',artifact)
    result={'schemaVersion':1,'stageId':'level-b-v2-training-fit-result-v1','status':'TRAINING_ONLY_V2_MODEL_FROZEN','trainingSelectionSha256':selection['selectionSha256'],'modelArtifactWritten':True,'modelSha256':artifact['modelSha256'],'selectedFamilyId':best['familyId'],'selectedPrimaryRidge':best['primaryRidge'],'selectedShapeRidge':best['shapeRidge'],'selectedTrainingMetrics':{k:best[k] for k in ('selectionScore','looMeanPrimaryMale','looWorstSinglePrimaryLogError','looMeanShapeNrmse','looWorstShapeNrmse','boundaryWorstPrimaryMale','boundaryWorstShapeNrmse','looPrimaryImprovementVsBaselineFraction')},'ordinal22ValuesRead':False,'protectedValidationAuthorized':False,'productionPromotionAuthorized':False}
    result['resultSha256']=canonical_sha({k:v for k,v in result.items() if k!='resultSha256'}); write_json(output/'training-fit-result-v2.json',result)

def main() -> int:
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='cmd',required=True)
    s=sub.add_parser('synthetic'); s.add_argument('--protocol',type=Path,required=True)
    e=sub.add_parser('execute'); e.add_argument('--protocol',type=Path,required=True); e.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    try:
        p=load_json(a.protocol)
        if a.cmd=='synthetic':
            recs=synthetic_records(); best,ranking=select(recs,p,enforce_expected_counts=False); req(len(ranking)==100,'synthetic candidate count drift'); req(best is not None,'synthetic no eligible candidate'); print(json.dumps({'status':'SYNTHETIC_PASS','selected':best['familyId'],'candidateCount':len(ranking)},sort_keys=True))
        else: execute(p,a.output)
        return 0
    except Exception as exc:
        print(json.dumps({'status':'REFUSED','reason':str(exc)},sort_keys=True),file=os.sys.stderr); return 2

if __name__=='__main__':
    raise SystemExit(main())
