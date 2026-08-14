#!/usr/bin/env python3
from __future__ import annotations
import argparse, concurrent.futures as cf, hashlib, importlib.util, io, json, math, os, re, subprocess, urllib.error, urllib.request, zipfile
from pathlib import Path
from typing import Any
import numpy as np

REPO='search-maker/twilight-mystic-experiments'
GRID_SHA='b5fae53c1cc88c7f3de6e3689bc25e4a36c54033d1d1bfd6169482f30cc5b477'
COMMON='review/tier2-stage1-ordinal20-artifact-salvage-v1/common_v1.py'
CASE_RX=re.compile(r'(train-\d{4})')
class Refusal(RuntimeError): pass
def req(c:bool,m:str)->None:
    if not c: raise Refusal(m)
def canon(v:Any)->str: return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def sha_bytes(b:bytes)->str: return hashlib.sha256(b).hexdigest()
def write_json(p:Path,v:Any)->None:
    p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
def load_json(p:Path)->dict[str,Any]:
    x=json.loads(p.read_text()); req(isinstance(x,dict),f'object required: {p}'); return x

def validate_protocol(p:dict[str,Any])->None:
    req((p.get('schemaVersion'),p.get('protocolId'),p.get('status'),p.get('governance'))==(1,'level-b-v1-core-training-spectral-adequacy-v1','REVIEW_ONLY_TRAINING_UNIVERSE_AND_SPECTRAL_ADEQUACY_FREEZE_NO_HOLDOUT_NO_FITTING','MYSTIC-STATE-0067'),'protocol identity drift')
    u=p.get('trainingUniverse') or {}; req((u.get('geometryCount'),u.get('sourceCaseArtifactCount'))==(44,138),'training universe accounting drift')
    h=u.get('historicalAdmitted') or {}; t=u.get('train0014FreshAdmitted') or {}; q=u.get('tier2Ordinal20Recovered') or {}
    req((h.get('geometryCount'),h.get('sourceCaseArtifactCount'))==(24,58),'historical cohort drift')
    req((t.get('geometryCount'),t.get('sourceCaseArtifactCount'),t.get('geometryId'))==(1,4,'train-0014'),'train0014 cohort drift')
    req((q.get('geometryCount'),q.get('sourceCaseArtifactCount'))==(19,76),'tier2 cohort drift')
    req(len(h.get('geometryIds') or [])==24 and len(set(h['geometryIds']))==24,'historical geometry list drift')
    req('train-0037' in set(u.get('explicitlyExcludedGeometryIds') or []),'train0037 exclusion missing')
    s=p.get('spectralAdequacy') or {}; g=s.get('wavelengthGrid') or {}
    req((g.get('nodeCount'),g.get('firstNm'),g.get('lastNm'),g.get('canonicalTokenStreamSha256'))==(8001,380.0,780.0,GRID_SHA),'grid contract drift')
    req(s.get('numericalRankRule')=='FLOAT64_SVD_MAX_DIMENSION_EPS_LEADING_SINGULAR_VALUE','numerical rank rule drift')
    req(s.get('componentSnrThreshold')==1.0 and s.get('maxPcaComponents')==8,'adequacy threshold/cap drift')
    req(s.get('rawResamplingAllowed') is False and s.get('rawSmoothingAllowed') is False and s.get('epsilonSubstitutionAllowed') is False,'raw mutation boundary drift')
    b=p.get('boundaries') or {}
    for k in ('scientificSolverExecutionAuthorized','newScientificOrdinalAuthorized','protectedHoldoutOpeningAuthorized','holdoutValuesMayBeRead','stage2Authorized','modelFittingAuthorized','modelSelectionAuthorized','oodFreezeAuthorizedByThisProtocol','definitionOfDoneFreezeAuthorizedByThisProtocol','productionPromotionAuthorized','workerBLaneReactivated','workerCLaneReactivated'):
        req(b.get(k) is False,f'closed boundary opened: {k}')

def load_common(repo_root:Path):
    path=repo_root/COMMON; spec=importlib.util.spec_from_file_location('salvage_common',path); req(spec is not None and spec.loader is not None,'common module load'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def request(url:str,token:str,json_accept:bool=True)->urllib.request.Request:
    h={'Authorization':f'Bearer {token}','User-Agent':'level-b-spectral-adequacy-v1','X-GitHub-Api-Version':'2022-11-28'}
    if json_accept: h['Accept']='application/vnd.github+json'
    return urllib.request.Request(url,headers=h)
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl): return None
def api_json(url:str,token:str)->dict[str,Any]:
    with urllib.request.urlopen(request(url,token),timeout=60) as r: x=json.loads(r.read()); req(isinstance(x,dict),'API object required'); return x
def download_artifact(aid:int,token:str)->bytes:
    url=f'https://api.github.com/repos/{REPO}/actions/artifacts/{aid}/zip'; op=urllib.request.build_opener(NoRedirect)
    try: r=op.open(request(url,token,False),timeout=60)
    except urllib.error.HTTPError as e:
        req(e.code in (301,302,303,307,308) and e.headers.get('Location'),'artifact redirect missing'); loc=e.headers['Location']
    else:
        with r: return r.read()
    with urllib.request.urlopen(urllib.request.Request(loc,headers={'User-Agent':'level-b-spectral-adequacy-v1'}),timeout=120) as r: return r.read()
def metadata(aid:int,token:str)->dict[str,Any]: return api_json(f'https://api.github.com/repos/{REPO}/actions/artifacts/{aid}',token)
def verified_artifact(aid:int,want_digest:str,token:str)->bytes:
    m=metadata(aid,token); req(m.get('expired') is False and m.get('digest')==want_digest,f'artifact metadata drift: {aid}'); raw=download_artifact(aid,token); req('sha256:'+sha_bytes(raw)==want_digest,f'artifact ZIP digest drift: {aid}'); return raw

def zip_json(raw:bytes,name:str)->dict[str,Any]:
    with zipfile.ZipFile(io.BytesIO(raw)) as z: x=json.loads(z.read(name)); req(isinstance(x,dict),f'object required: {name}'); return x
def basename_member(names:list[str],base:str)->str:
    hits=[n for n in names if n.rstrip('/').split('/')[-1]==base]; req(len(hits)==1,f'exactly one {base} required'); return hits[0]
def parse_spectrum(raw:bytes,common)->tuple[np.ndarray,np.ndarray,str]:
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        n=basename_member(z.namelist(),'mc.rad.spc'); data=z.read(n); lines=data.decode('utf-8',errors='strict').splitlines()
    toks=[]; vals=[]
    for line in lines:
        p=line.split()
        if not p: continue
        req(len(p)>=2 and re.fullmatch(r'[0-9]+\.[0-9]{5}',p[0]) is not None,'spectrum serialization drift')
        row=[float(x) for x in p]; req(all(math.isfinite(x) for x in row) and all(x>=0.0 for x in row[1:]),'invalid spectrum value'); toks.append(p[0]); vals.append(row[-1])
    req(len(toks)==8001 and toks[0]=='380.00000' and toks[-1]=='780.00000','spectrum grid count/endpoints drift')
    g=sha_bytes(('\n'.join(toks)+'\n').encode()); req(g==GRID_SHA,'spectrum token grid drift')
    wl=np.array([float(x) for x in toks],dtype=np.float64); y=np.array(vals,dtype=np.float64); req(np.all(np.diff(wl)>0),'spectrum order drift')
    return wl,y,sha_bytes(data)

def integration_weights(wl:np.ndarray,common)->np.ndarray:
    n=len(wl); quadr=np.zeros(n); quadr[0]=(wl[1]-wl[0])/2; quadr[-1]=(wl[-1]-wl[-2])/2; quadr[1:-1]=(wl[2:]-wl[:-2])/2
    phot=np.array([common.interp(common.V_PHOT,float(w)) for w in wl]); scot=np.array([common.interp(common.V_SCOT,float(w)) for w in wl]); bv=np.array([common.bess(float(w)) for w in wl])
    wp=common.KM_PHOT*1e-3*quadr*phot; ws=common.KM_SCOT*1e-3*quadr*scot; den=float(np.sum(quadr*bv*wl)); req(den>0,'Johnson denominator'); wv=quadr*bv*wl/den
    W=np.vstack([wp,ws,wv]); req(np.linalg.matrix_rank(W)==3,'integration weight rank drift'); return W

def projection_residual(y:np.ndarray,W:np.ndarray)->tuple[np.ndarray,np.ndarray]:
    ch=W@y; req(ch[0]>0 and np.all(np.isfinite(ch)),'nonpositive/nonfinite primary channel'); x=y/ch[0]; gram=W@W.T; proj=W.T@np.linalg.solve(gram,W@x); r=x-proj; req(float(np.max(np.abs(W@r)))<1e-9,'nullspace projection drift'); return r,ch

def canonicalize_components(vt:np.ndarray)->np.ndarray:
    out=vt.copy()
    for i in range(out.shape[0]):
        j=int(np.argmax(np.abs(out[i])))
        if out[i,j]<0: out[i]*=-1
    return out

def spectral_pca(blocks:dict[str,list[np.ndarray]],W:np.ndarray,max_components:int=8,threshold:float=1.0)->dict[str,Any]:
    gids=sorted(blocks); req(len(gids)==44,'PCA geometry count drift')
    residual_blocks:dict[str,list[np.ndarray]]={}
    for g in gids:
        req(len(blocks[g])>=2,f'at least two admitted blocks required: {g}'); residual_blocks[g]=[projection_residual(y,W)[0] for y in blocks[g]]
    means=np.vstack([np.mean(np.vstack(residual_blocks[g]),axis=0) for g in gids]); grand=np.mean(means,axis=0); M=means-grand
    U,s,vt=np.linalg.svd(M,full_matrices=False); vt=canonicalize_components(vt)
    lead=float(s[0]) if len(s) else 0.0; rank_tol=float(max(M.shape)*np.finfo(np.float64).eps*lead); active=s>rank_tol
    scores=M@vt.T
    between=np.var(scores,axis=0,ddof=1); noise=[]
    for j in range(vt.shape[0]):
        q=[]
        for g in gids:
            a=np.array([float(r@vt[j]) for r in residual_blocks[g]])
            q.append(float(np.var(a,ddof=1)/len(a)))
        noise.append(float(np.mean(q)))
    noise=np.array(noise); snr=np.array([math.inf if nv==0 and bv>0 else (0.0 if nv==0 else bv/nv) for bv,nv in zip(between,noise)])
    resolved=[int(i) for i,x in enumerate(snr) if bool(active[i]) and x>threshold and between[i]>0]
    req(len(resolved)<=max_components,f'{len(resolved)} resolved nullspace components exceeds frozen cap {max_components}')
    selected=vt[resolved] if resolved else np.zeros((0,len(W[0])))
    return {'geometryIds':gids,'grandMeanResidual':grand,'components':selected,'resolvedIndices':resolved,'singularValues':s,'numericalRankTolerance':rank_tol,'numericalRank':int(np.count_nonzero(active)),'betweenVariance':between,'noiseVariance':noise,'snr':snr,'allComponents':vt}

def derive_sources(protocol:dict[str,Any],token:str)->tuple[list[dict[str,Any]],dict[str,bytes]]:
    u=protocol['trainingUniverse']; evidence={}
    h=u['historicalAdmitted']; hr=verified_artifact(h['replayEvidenceArtifactId'],h['replayEvidenceArtifactDigest'],token); evidence['historical']=hr
    with zipfile.ZipFile(io.BytesIO(hr)) as z:
        hand=json.loads(z.read('training-handoff-replay.json')); trans=json.loads(z.read('transport-manifest.json'))
    req(hand.get('replayDatasetSha256')==h['replayDatasetSha256'] and trans.get('transportManifestSha256')==h['transportManifestSha256'],'historical replay hash drift')
    allowed=set(h['geometryIds']); ce={(x['geometryId'],int(x['block'])):x for x in hand['caseEvidence'] if x['geometryId'] in allowed}; te={(x['geometryId'],int(x['block'])):x for x in trans['entries'] if x['geometryId'] in allowed}; req(set(ce)==set(te) and len(te)==58,'historical admitted source universe drift')
    src=[]
    for k in sorted(te):
        a=te[k]; c=ce[k]; src.append({'cohort':'historical-admitted','geometryId':k[0],'block':k[1],'caseId':c['caseId'],'artifactId':int(a['artifactId']),'artifactDigest':a['githubArtifactDigest'],'expectedRadianceSha256':c['radianceSha256'],'sourceRunId':a['runId'],'sourceRunAttempt':a['runAttempt'],'sourceHeadSha':a['headSha']})
    t=u['train0014FreshAdmitted']; tr=verified_artifact(t['salvageEvidenceArtifactId'],t['salvageEvidenceArtifactDigest'],token); evidence['train0014']=tr
    with zipfile.ZipFile(io.BytesIO(tr)) as z:
        arts=json.loads(z.read('source-artifacts.json'))['artifacts']; norm=json.loads(z.read('salvage/normalized-evidence.json'))
    cases={x['caseId']:x for x in norm['cases']}; req(len(cases)==4 and set(x['geometryId'] for x in cases.values())=={'train-0014'},'train0014 normalized universe drift')
    case_arts=[a for a in arts if '-case-' in a['name']]; req(len(case_arts)==4,'train0014 source artifact count drift')
    for a in sorted(case_arts,key=lambda x:x['name']):
        cid=a['name'].split('-case-',1)[1]; req(cid in cases,'train0014 case artifact identity drift'); c=cases[cid]; src.append({'cohort':'train0014-fresh-admitted','geometryId':'train-0014','block':int(c['block']),'caseId':cid,'artifactId':int(a['id']),'artifactDigest':a['digest'],'expectedRadianceSha256':None,'sourceRunId':t['sourceScientificRunId'],'sourceRunAttempt':t['sourceScientificRunAttempt'],'sourceHeadSha':t['sourceScientificHeadSha']})
    q=u['tier2Ordinal20Recovered']; qr=verified_artifact(q['salvageEvidenceArtifactId'],q['salvageEvidenceArtifactDigest'],token); evidence['tier2']=qr
    with zipfile.ZipFile(io.BytesIO(qr)) as z: inv=json.loads(z.read('inventory.json')); agg=json.loads(z.read('aggregate.json'))
    req(inv.get('inventorySha256')==q['inventorySha256'] and agg.get('aggregateSha256')==q['aggregateSha256'],'tier2 salvage hash drift'); req(len(inv['cases'])==76,'tier2 case source count drift')
    for c in inv['cases']:
        req(c.get('protectedHoldoutValueExposed') is False and c.get('solverExecutionCountProven')==1,'tier2 source boundary drift')
        src.append({'cohort':'tier2-ordinal20-recovered','geometryId':c['geometryId'],'block':int(c['block']),'caseId':c['caseId'],'artifactId':int(c['artifactId']),'artifactDigest':c['artifactDigest'],'expectedRadianceSha256':c['rawMemberSha256ByBasename']['mc.rad.spc'],'sourceRunId':q['sourceScientificRunId'],'sourceRunAttempt':q['sourceScientificRunAttempt'],'sourceHeadSha':q['sourceScientificHeadSha']})
    req(len(src)==138 and len({(x['cohort'],x['caseId']) for x in src})==138,'combined source case count/identity drift'); req(len(set(x['geometryId'] for x in src))==44,'combined geometry count drift')
    excluded=set(u['explicitlyExcludedGeometryIds']); req(not (excluded & set(x['geometryId'] for x in src)),'excluded geometry entered training universe')
    return src,evidence

def download_sources(src:list[dict[str,Any]],token:str)->dict[int,bytes]:
    def get(x):
        raw=verified_artifact(x['artifactId'],x['artifactDigest'],token); return x['artifactId'],raw
    out={}
    with cf.ThreadPoolExecutor(max_workers=12) as pool:
        fs=[pool.submit(get,x) for x in src]
        for f in cf.as_completed(fs): aid,raw=f.result(); req(aid not in out,'duplicate artifact id'); out[aid]=raw
    req(len(out)==138,'downloaded source count drift'); return out

def execute(repo_root:Path,protocol_path:Path,out:Path)->None:
    token=os.environ.get('GITHUB_TOKEN',''); req(token,'GITHUB_TOKEN required'); p=load_json(protocol_path); validate_protocol(p)
    # Bind reviewed admission/result files exactly by git blob before reading any source values.
    for cohort,key_path,key_sha in [('historical','admissionReadinessPath','admissionReadinessGitBlobSha'),('train0014','admissionDecisionPath','admissionDecisionGitBlobSha'),('tier2','resultBindingPath','resultBindingGitBlobSha')]:
        q={'historical':p['trainingUniverse']['historicalAdmitted'],'train0014':p['trainingUniverse']['train0014FreshAdmitted'],'tier2':p['trainingUniverse']['tier2Ordinal20Recovered']}[cohort]
        got=subprocess.check_output(['git','rev-parse',f'HEAD:{q[key_path]}'],cwd=repo_root,text=True).strip(); req(got==q[key_sha],f'{cohort} reviewed source blob drift')
    common=load_common(repo_root); src,evidence=derive_sources(p,token); raws=download_sources(src,token)
    blocks:dict[str,list[np.ndarray]]={}; inventory=[]; wl0=None
    for x in sorted(src,key=lambda r:(r['geometryId'],r['block'],r['caseId'])):
        wl,y,rsha=parse_spectrum(raws[x['artifactId']],common)
        if x['expectedRadianceSha256'] is not None: req(rsha==x['expectedRadianceSha256'],f'raw radiance hash drift: {x["caseId"]}')
        if wl0 is None: wl0=wl
        else: req(np.array_equal(wl0,wl),'wavelength numeric grid identity drift')
        blocks.setdefault(x['geometryId'],[]).append(y)
        inventory.append({**x,'radianceSha256':rsha,'sourceZipSha256':sha_bytes(raws[x['artifactId']]),'wavelengthTokenGridSha256':GRID_SHA})
    req(wl0 is not None and len(blocks)==44 and sum(len(v) for v in blocks.values())==138,'parsed training universe drift')
    W=integration_weights(wl0,common)
    # Cross-check weight implementation against the existing reviewed integration implementation.
    for g in sorted(blocks)[:3]:
        y=blocks[g][0]; ch=np.array([common.channels(wl0.tolist(),y.tolist())[k] for k in ('photopicLuminanceCdM2','scotopicLuminanceScotCdM2','johnsonVEffectiveRadiance_mW_m2_nm_sr')]); calc=W@y; req(np.allclose(ch,calc,rtol=2e-12,atol=1e-15),f'integration implementation mismatch: {g}')
    r=spectral_pca(blocks,W,int(p['spectralAdequacy']['maxPcaComponents']),float(p['spectralAdequacy']['componentSnrThreshold']))
    decision='KEEP_THREE_INTEGRATED_CHANNELS_ONLY' if not r['resolvedIndices'] else 'ADD_EXACTLY_THE_RESOLVED_NULLSPACE_PCA_COMPONENTS_TO_THE_THREE_INTEGRATED_CHANNELS'
    out.mkdir(parents=True,exist_ok=True)
    npz=out/'spectral-representation-v1.npz'; np.savez_compressed(npz,wavelength_nm=wl0,integration_weights=W,grand_mean_nullspace_residual=r['grandMeanResidual'],selected_nullspace_pca_components=r['components'],resolved_pca_indices=np.array(r['resolvedIndices'],dtype=np.int64))
    universe={'schemaVersion':1,'status':'FROZEN_TRAINING_ONLY_UNIVERSE_RECONSTRUCTED_FROM_REVIEWED_IMMUTABLE_EVIDENCE','protocolId':p['protocolId'],'geometryCount':44,'sourceCaseArtifactCount':138,'sourceArtifactIds':[x['artifactId'] for x in inventory],'cases':inventory,'excludedGeometryIds':p['trainingUniverse']['explicitlyExcludedGeometryIds'],'holdoutValuesRead':False,'protectedHoldoutRecordCount':0,'scientificSolverExecutionPerformed':False}; universe['universeSha256']=canon(universe); write_json(out/'training-universe-v1.json',universe)
    result={'schemaVersion':1,'status':'TRAINING_ONLY_SPECTRAL_ADEQUACY_ANALYZED','protocolId':p['protocolId'],'numpyVersion':np.__version__,'geometryCount':44,'sourceCaseArtifactCount':138,'wavelengthTokenGridSha256':GRID_SHA,'trainingUniverseSha256':universe['universeSha256'],'representationPackageSha256':sha_bytes(npz.read_bytes()),'mandatoryIntegratedChannelCount':3,'resolvedNullspacePcaComponentCount':len(r['resolvedIndices']),'resolvedPcaIndices':r['resolvedIndices'],'decision':decision,'numericalRankRule':p['spectralAdequacy']['numericalRankRule'],'numericalRankTolerance':r['numericalRankTolerance'],'numericalRank':r['numericalRank'],'componentSnrThreshold':p['spectralAdequacy']['componentSnrThreshold'],'maxPcaComponents':p['spectralAdequacy']['maxPcaComponents'],'singularValues':[float(x) for x in r['singularValues']],'betweenGeometryScoreVariance':[float(x) for x in r['betweenVariance']],'noiseFloorVariance':[float(x) for x in r['noiseVariance']],'componentSnr':[('Infinity' if math.isinf(float(x)) else float(x)) for x in r['snr']],'holdoutValuesRead':False,'protectedHoldoutRecordCount':0,'modelFittingAuthorized':False,'modelSelectionAuthorized':False,'stage2Authorized':False,'newScientificExecutionAuthorized':False,'sourceArtifactsModified':False}; result['resultSha256']=canon(result); write_json(out/'spectral-adequacy-result-v1.json',result)

def main()->int:
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='cmd',required=True)
    v=sub.add_parser('validate'); v.add_argument('--protocol',type=Path,required=True)
    e=sub.add_parser('execute'); e.add_argument('--repo-root',type=Path,required=True); e.add_argument('--protocol',type=Path,required=True); e.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    try:
        if a.cmd=='validate': validate_protocol(load_json(a.protocol))
        else: execute(a.repo_root,a.protocol,a.output)
        return 0
    except Exception as x:
        print(json.dumps({'status':'REFUSED','reason':str(x)},sort_keys=True),file=os.sys.stderr); return 2
if __name__=='__main__': raise SystemExit(main())
