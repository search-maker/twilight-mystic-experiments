#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.util, io, json, math, os, subprocess, zipfile
from pathlib import Path
from typing import Any
import numpy as np

V1_PATH='review/core-training-spectral-adequacy-v1/analyze_v1.py'
V1_PROTOCOL='review/core-training-spectral-adequacy-v1/protocol-v1.json'
V1_PROTOCOL_BLOB='a654acf9e8c072ec2c6aafece67f1ff53fd5d5e5'
V1_ANALYZER_BLOB='1c38b3492148ed7a84d01180fc1cef877d6117c5'
GRID_SHA='b5fae53c1cc88c7f3de6e3689bc25e4a36c54033d1d1bfd6169482f30cc5b477'
FEATURES=('sunDepressionDeg','targetAltitudeDeg','relativeAzimuthDeg','observerElevationM','aod550')
class Refusal(RuntimeError): pass
def req(c:bool,m:str)->None:
    if not c: raise Refusal(m)
def canon(v:Any)->str: return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def sha_bytes(b:bytes)->str: return hashlib.sha256(b).hexdigest()
def load_json(p:Path)->dict[str,Any]:
    x=json.loads(p.read_text(encoding='utf-8')); req(isinstance(x,dict),f'object required: {p}'); return x
def write_json(p:Path,v:Any)->None:
    p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
def load_v1(root:Path):
    p=root/V1_PATH; s=importlib.util.spec_from_file_location('spectral_adequacy_v1',p); req(s is not None and s.loader is not None,'v1 analyzer load'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def validate_protocol(p:dict[str,Any])->None:
    req((p.get('schemaVersion'),p.get('protocolId'),p.get('status'),p.get('governance'))==(2,'level-b-v1-core-training-spectral-representation-v2','REVIEW_ONLY_TRAINING_RESOLVED_SPECTRAL_REPRESENTATION_AFTER_V1_CAP_REFUSAL_NO_HOLDOUT_NO_FITTING','MYSTIC-STATE-0067'),'protocol identity drift')
    req(p.get('sourceMainAtFreeze')=='c21f2b67001d98df85622f4782593d30ddb90934','source main drift')
    r=p.get('priorAdequacyRefusal') or {}
    req((r.get('protocolGitBlobSha'),r.get('analyzerGitBlobSha'))==(V1_PROTOCOL_BLOB,V1_ANALYZER_BLOB),'v1 source blob drift')
    req((r.get('activationCommitSha'),r.get('activationParentMainSha'),r.get('runId'),r.get('runAttempt'),r.get('event'),r.get('conclusion'))==('be3944fcf37b03d02979c86f8550e2045bc24bbc','c21f2b67001d98df85622f4782593d30ddb90934',31769561806,1,'push','failure'),'v1 refusal identity drift')
    req(r.get('exactRefusalReason')=='10 resolved nullspace components exceeds frozen cap 8' and r.get('observedResolvedNullspacePcaComponentCount')==10,'v1 refusal finding drift')
    req(r.get('trainingSpectraRead') is True and r.get('protectedHoldoutValuesRead') is False and r.get('scientificSolverExecutionPerformed') is False,'v1 refusal boundary drift')
    u=p.get('trainingUniverse') or {}; req((u.get('geometryCount'),u.get('sourceCaseArtifactCount'),u.get('sourceProtocolGitBlobSha'))==(44,138,V1_PROTOCOL_BLOB),'training universe drift')
    req(u.get('mustBeByteAndIdentityEquivalentToV1') is True and u.get('protectedHoldoutGeometryCount')==0 and u.get('protectedHoldoutValuesMayBeRead') is False,'training universe boundary drift')
    q=p.get('representation') or {}
    req(q.get('decision')=='RETAIN_ALL_TRAINING_RESOLVED_NULLSPACE_COMPONENTS_OBSERVED_BY_V1','representation decision drift')
    req((q.get('mandatoryIntegratedChannelCount'),q.get('expectedResolvedNullspacePcaComponentCount'),q.get('totalRepresentationFeatureCount'))==(3,10,13),'representation dimensionality drift')
    req(q.get('componentSnrThreshold')==1.0 and q.get('numericalRankRule')=='FLOAT64_SVD_MAX_DIMENSION_EPS_LEADING_SINGULAR_VALUE','scientific resolution rule drift')
    req(q.get('wavelengthTokenGridSha256')==GRID_SHA,'grid hash drift')
    for k in ('rawResamplingAllowed','rawSmoothingAllowed','epsilonSubstitutionAllowed','protectedHoldoutMayInfluenceRepresentation'):
        req(q.get(k) is False,f'forbidden representation operation opened: {k}')
    req(q.get('representationFitUsesTrainingOnly') is True,'training-only representation drift')
    b=p.get('boundaries') or {}
    for k in ('scientificSolverExecutionAuthorized','newScientificOrdinalAuthorized','protectedHoldoutOpeningAuthorized','holdoutValuesMayBeRead','stage2Authorized','modelFittingAuthorized','modelSelectionAuthorized','oodFreezeAuthorizedByThisProtocol','definitionOfDoneFreezeAuthorizedByThisProtocol','productionPromotionAuthorized','workerBLaneReactivated','workerCLaneReactivated'):
        req(b.get(k) is False,f'closed boundary opened: {k}')

def git_blob(root:Path,path:str)->str:
    return subprocess.check_output(['git','rev-parse',f'HEAD:{path}'],cwd=root,text=True).strip()
def prepared_inputs(raw:bytes)->dict[str,Any]:
    candidates=[]
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        for n in z.namelist():
            if not n.lower().endswith('.json') or 'prepared' not in n.lower(): continue
            try: x=json.loads(z.read(n))
            except Exception: continue
            if not isinstance(x,dict): continue
            y=x.get('inputs') if isinstance(x.get('inputs'),dict) else x
            if all(k in y for k in FEATURES) and ('groupId' in y or 'geometryId' in y):
                candidates.append(y)
    req(candidates,'prepared geometry inputs missing')
    sigs={(tuple(float(x[k]) for k in FEATURES),str(x.get('groupId') or x.get('geometryId'))) for x in candidates}
    req(len(sigs)==1,'prepared geometry input ambiguity')
    vals,gid=next(iter(sigs)); return {'geometryId':gid,'geometry':{k:float(v) for k,v in zip(FEATURES,vals,strict=True)}}
def stats(xs:list[float])->dict[str,float]:
    req(xs and all(math.isfinite(x) for x in xs),'finite statistics required'); a=np.asarray(xs,dtype=np.float64); n=len(xs); mean=float(np.mean(a)); sd=float(np.std(a,ddof=1)) if n>1 else 0.0; sem=sd/math.sqrt(n) if n else math.nan
    return {'mean':mean,'sampleStd':sd,'standardError':sem,'relativeStandardError':(abs(sem/mean) if mean!=0 else math.inf)}

def execute(root:Path,protocol_path:Path,out:Path)->None:
    token=os.environ.get('GITHUB_TOKEN',''); req(token,'GITHUB_TOKEN required'); p=load_json(protocol_path); validate_protocol(p)
    req(git_blob(root,V1_PROTOCOL)==V1_PROTOCOL_BLOB,'v1 protocol git blob drift'); req(git_blob(root,V1_PATH)==V1_ANALYZER_BLOB,'v1 analyzer git blob drift')
    v1=load_v1(root); v1p=load_json(root/V1_PROTOCOL); v1.validate_protocol(v1p); common=v1.load_common(root)
    src,_=v1.derive_sources(v1p,token); req(len(src)==138 and len({x['geometryId'] for x in src})==44,'v1 source universe reconstruction drift')
    raws=v1.download_sources(src,token); blocks:dict[str,list[np.ndarray]]={}; inputs:dict[str,dict[str,Any]]={}; inventory=[]; wl0=None
    for x in sorted(src,key=lambda q:(q['geometryId'],q['block'],q['caseId'])):
        raw=raws[x['artifactId']]; wl,y,rsha=v1.parse_spectrum(raw,common)
        if x.get('expectedRadianceSha256') is not None: req(rsha==x['expectedRadianceSha256'],f'raw radiance hash drift: {x["caseId"]}')
        if wl0 is None: wl0=wl
        else: req(np.array_equal(wl0,wl),'wavelength numeric grid identity drift')
        pi=prepared_inputs(raw); req(pi['geometryId']==x['geometryId'],f'prepared geometry id drift: {x["caseId"]}')
        if x['geometryId'] in inputs: req(inputs[x['geometryId']]==pi['geometry'],f'geometry feature drift across blocks: {x["geometryId"]}')
        else: inputs[x['geometryId']]=pi['geometry']
        blocks.setdefault(x['geometryId'],[]).append(y)
        inventory.append({**x,'radianceSha256':rsha,'sourceZipSha256':sha_bytes(raw),'wavelengthTokenGridSha256':GRID_SHA})
    req(wl0 is not None and len(blocks)==44 and len(inputs)==44 and sum(len(v) for v in blocks.values())==138,'parsed v2 universe drift')
    W=v1.integration_weights(wl0,common); r=v1.spectral_pca(blocks,W,max_components=10,threshold=1.0)
    req(len(r['resolvedIndices'])==10,f'resolved component count drift: {len(r["resolvedIndices"])} != 10')
    C=r['components']; req(C.shape==(10,8001),'selected component shape drift'); req(float(np.max(np.abs(W@C.T)))<1e-9,'selected components left mandatory-channel nullspace')
    records=[]
    for gid in sorted(blocks):
        channel_rows=[]; coeff_rows=[]
        for y in blocks[gid]:
            residual,ch=v1.projection_residual(y,W); channel_rows.append(ch); coeff_rows.append(residual@C.T)
        ca=np.vstack(channel_rows); pa=np.vstack(coeff_rows)
        records.append({'geometryId':gid,'geometry':inputs[gid],'blockCount':len(blocks[gid]),'integratedChannels':{
            'photopicLuminanceCdM2':stats(ca[:,0].tolist()),
            'scotopicLuminanceScotCdM2':stats(ca[:,1].tolist()),
            'johnsonVEffectiveRadiance_mW_m2_nm_sr':stats(ca[:,2].tolist())},
            'nullspacePcaCoefficients':[stats(pa[:,j].tolist()) for j in range(10)]})
    out.mkdir(parents=True,exist_ok=True)
    npz=out/'spectral-representation-v2.npz'; np.savez_compressed(npz,wavelength_nm=wl0,integration_weights=W,grand_mean_nullspace_residual=r['grandMeanResidual'],selected_nullspace_pca_components=C,resolved_pca_indices=np.asarray(r['resolvedIndices'],dtype=np.int64))
    universe={'schemaVersion':2,'stageId':'level-b-v1-core-training-representation-dataset-v2','status':'FROZEN_44_GEOMETRY_TRAINING_REPRESENTATION_NO_HOLDOUT','protocolId':p['protocolId'],'geometryCount':44,'sourceCaseArtifactCount':138,'representationFeatureCount':13,'mandatoryIntegratedChannelCount':3,'nullspacePcaComponentCount':10,'featureNames':list(FEATURES),'records':records,'sourceCases':inventory,'protectedHoldoutRecordCount':0,'holdoutValuesRead':False,'scientificSolverExecutionPerformed':False}; universe['datasetSha256']=canon(universe); write_json(out/'training-representation-dataset-v2.json',universe)
    result={'schemaVersion':2,'stageId':'level-b-v1-core-training-spectral-representation-result-v2','status':'TRAINING_ONLY_REPRESENTATION_FROZEN_PENDING_REVIEWED_RESULT_BINDING','protocolId':p['protocolId'],'priorV1RefusalRunId':31769561806,'priorV1RefusalReason':p['priorAdequacyRefusal']['exactRefusalReason'],'geometryCount':44,'sourceCaseArtifactCount':138,'mandatoryIntegratedChannelCount':3,'resolvedNullspacePcaComponentCount':10,'totalRepresentationFeatureCount':13,'resolvedPcaIndices':r['resolvedIndices'],'numericalRank':r['numericalRank'],'numericalRankTolerance':r['numericalRankTolerance'],'componentSnrThreshold':1.0,'singularValues':[float(x) for x in r['singularValues']],'betweenGeometryScoreVariance':[float(x) for x in r['betweenVariance']],'noiseFloorVariance':[float(x) for x in r['noiseVariance']],'componentSnr':[('Infinity' if math.isinf(float(x)) else float(x)) for x in r['snr']],'trainingDatasetSha256':universe['datasetSha256'],'representationPackageSha256':sha_bytes(npz.read_bytes()),'wavelengthTokenGridSha256':GRID_SHA,'holdoutValuesRead':False,'protectedHoldoutRecordCount':0,'modelFittingAuthorized':False,'modelSelectionAuthorized':False,'stage2Authorized':False,'newScientificExecutionAuthorized':False,'sourceArtifactsModified':False}; result['resultSha256']=canon(result); write_json(out/'spectral-representation-result-v2.json',result)

def main()->int:
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='cmd',required=True); v=sub.add_parser('validate'); v.add_argument('--protocol',type=Path,required=True); e=sub.add_parser('execute'); e.add_argument('--repo-root',type=Path,required=True); e.add_argument('--protocol',type=Path,required=True); e.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    try:
        if a.cmd=='validate': validate_protocol(load_json(a.protocol))
        else: execute(a.repo_root,a.protocol,a.output)
        return 0
    except Exception as x:
        print(json.dumps({'status':'REFUSED','reason':str(x)},sort_keys=True),file=os.sys.stderr); return 2
if __name__=='__main__': raise SystemExit(main())
