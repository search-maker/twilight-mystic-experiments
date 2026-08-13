#!/usr/bin/env python3
from __future__ import annotations
import argparse, concurrent.futures as cf, copy, hashlib, importlib.util, json, os, re, shutil, tempfile, urllib.error, urllib.request, zipfile
from pathlib import Path
from typing import Any
PID='public-artifact-pipeline-replay-v1-preregistration'; STATUS='REVIEW_ONLY_EXISTING_REAL_ARTIFACT_PIPELINE_REPLAY_NO_SCIENCE'; GOV='MYSTIC-STATE-0067'
BASE='0afd0691c1e1508c52273325e07f0cd4b044aa27'; TIER2='5043929fdf13aaf90c9face0c380b514999a52a7226079807969a74469764f93'; BUILDER='9bc53956fc4a49935ba2957087d8bf4203b7e8be'; ADMISSION='c136f23f7df68b1481cb5ff939646198a3e336fe'
HACQ='6cc7c93a395b8e4a42ba31d38c7a7d1fb8cf54b0993b80dbb652d29e73a04539'; HDS='5b16b05b0ee891a140d41503993e012e76bd0b4105fbc2d09fb9260a8284e478'; HADM='42478d099efea7392f5558716571400dc84ee28de5df1e22f85e8031d2138c41'
RUNS=[
 {'ordinal':2,'runId':30952457327,'headSha':'c9679a515c5f4538345d0d83252bcd8e37eb7b7e','runAttempt':1,'event':'workflow_dispatch','conclusion':'failure','workflowPath':'.github/workflows/twilight-surrogate-tier-1-ordinal2-execution.yml','blocks':[1,2],'expectedTrainingCaseArtifacts':78},
 {'ordinal':11,'runId':31052639692,'headSha':'5b28ea31649f2c37e8b56ddae893a57608c2e148','runAttempt':1,'event':'workflow_dispatch','conclusion':'failure','workflowPath':'.github/workflows/tier1-precision-continuation-wave1-ordinal11-execution.yml','blocks':[3,4],'expectedTrainingCaseArtifacts':34},
 {'ordinal':12,'runId':31065046524,'headSha':'18a5746778441d57b722c740a17c94af9b56e9c9','runAttempt':1,'event':'push','conclusion':'success','workflowPath':'.github/workflows/tier1-precision-continuation-wave2-ordinal12-execution.yml','blocks':[5,6],'expectedTrainingCaseArtifacts':28},
 {'ordinal':13,'runId':31070968611,'headSha':'6c22de3578b1b0dcbc640779baa66be8d1051fe1','runAttempt':1,'event':'push','conclusion':'success','workflowPath':'.github/workflows/tier1-precision-continuation-wave3-ordinal13-execution.yml','blocks':[7,8],'expectedTrainingCaseArtifacts':26}]
MUST_EXERCISE=['INPUT_RENDER_AND_PHYSICAL_FINGERPRINT','PREPARED_CASE_BINDING','CASE_RESULT_AND_RAW_SPECTRUM_HASHING','TRANSPORT_ARTIFACT_ID_AND_DIGEST_BINDING','FULL_SPECTRUM_DERIVED_CHANNEL_REINTEGRATION','AGGREGATE_AND_INDEPENDENT_AUDIT','TRAINING_HANDOFF_ROLE_EXCLUSION']
RX=re.compile(r'(train-\d{4}).*-b([1-8])$')
class Refusal(RuntimeError): pass
def req(c,m):
 if not c: raise Refusal(m)
def cb(v): return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def ch(v): return hashlib.sha256(cb(v)).hexdigest()
def self_hash_null(v,f):
 x=copy.deepcopy(v); x[f]=None; return ch(x)
def load_builder(p):
 s=importlib.util.spec_from_file_location('hb',p); req(s is not None and s.loader is not None,'builder load'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
def validate_protocol(p):
 req((p.get('schemaVersion'),p.get('protocolId'),p.get('status'),p.get('governance'))==(1,PID,STATUS,GOV),'identity')
 req(p.get('protocolSha256')==self_hash_null(p,'protocolSha256'),'selfhash'); s=p.get('decisionSemantics') or {}
 for k in ('newScientificExecutionAuthorized','campaignAuthorizationIssued','campaignDispatchIssued','scientificOrdinalAllocated','modelFittingAuthorized','modelSelectionAuthorized','protectedHoldoutOpeningAuthorized','productionPromotionAuthorized'): req(s.get(k) is False,k)
 req(s.get('nextScientificOrdinal') is None and s.get('existingRealArtifactsOnly') is True and s.get('solverInvocationAllowed') is False,'science boundary')
 b=p.get('sourceBindings') or {}; req(b.get('liveMainAtFreeze')==BASE and b.get('tier2CoreCampaignContractSha256')==TIER2 and b.get('historicalBuilderGitBlobSha')==BUILDER and b.get('historicalAdmissionGitBlobSha')==ADMISSION,'bindings')
 req(p.get('sourceRuns')==RUNS,'runs'); u=p.get('trainingReplayUniverse') or {}; req((u.get('trainingGeometryCount'),u.get('trainingCaseArtifactCount'),u.get('internalHoldoutGeometryCountExcluded'),u.get('holdoutValuesMayBeRead'))==(39,166,9,False),'universe'); req(u.get('expectedCaseCountBySourceOrdinal')=={'2':78,'11':34,'12':28,'13':26},'partition')
 req(p.get('mustExercise')==MUST_EXERCISE,'surface'); h=p.get('historicalReferenceHashes') or {}; req((h.get('acquisitionManifestSha256'),h.get('trainingDatasetSha256'),h.get('admissionReportSha256'))==(HACQ,HDS,HADM),'historical refs')
 o=p.get('outputContract') or {}; req(o.get('candidateArtifactName')=='artifact-pipeline-replay-v1-candidate' and o.get('candidateDoesNotSatisfyReplayGateByItself') is True and o.get('separateVersionedResultBindingPRRequired') is True,'output boundary'); req(o.get('requiredOutputFiles')==['transport-manifest.json','training-handoff-replay.json','artifact-pipeline-replay-attestation.json'],'files')
 n=p.get('nextBoundary') or {}; req(n.get('replayGateStatusAfterCandidate')=='PENDING_SEPARATE_VERSIONED_RESULT_BINDING' and n.get('scientificExecutionAllowedAfterCandidate') is False and n.get('ordinal19AllocationAllowedAfterCandidate') is False,'next boundary')
def rq(url,t,json_accept=True):
 h={'Authorization':f'Bearer {t}','User-Agent':'twilight-mystic-artifact-replay-v1','X-GitHub-Api-Version':'2022-11-28'}
 if json_accept: h['Accept']='application/vnd.github+json'
 return urllib.request.Request(url,headers=h)
def api(url,t):
 with urllib.request.urlopen(rq(url,t),timeout=60) as r: return json.loads(r.read())
class NR(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl): return None
def dl(repo,aid,t):
 url=f'https://api.github.com/repos/{repo}/actions/artifacts/{aid}/zip'; op=urllib.request.build_opener(NR)
 try: r=op.open(rq(url,t,False),timeout=60)
 except urllib.error.HTTPError as e:
  req(e.code in (301,302,303,307,308) and e.headers.get('Location'),'download redirect'); loc=e.headers['Location']
 else:
  with r: return r.read()
 with urllib.request.urlopen(urllib.request.Request(loc,headers={'User-Agent':'twilight-mystic-artifact-replay-v1'}),timeout=120) as r: return r.read()
def arts(repo,rid,t):
 z=[]; page=1
 while True:
  a=api(f'https://api.github.com/repos/{repo}/actions/runs/{rid}/artifacts?per_page=100&page={page}',t).get('artifacts') or []; z+=a
  if len(a)<100: return z
  page+=1; req(page<=10,'pagination')
def key(name):
 m=RX.search(name); return (m.group(1),int(m.group(2))) if m else None
def inspect(zp,b,c):
 with zipfile.ZipFile(zp) as z:
  ns=z.namelist(); ir=z.read(b.find_one(ns,'input-resolved.txt')); rr=z.read(b.find_one(ns,'case-result.json')); pr=z.read(b.find_prepared(ns)); sr=z.read(b.find_one(ns,'mc.rad.spc')); st=z.read(b.find_one(ns,'mc.rad.std.spc'))
 p=b.parse_rendered_input(ir); req(p==c['inputs'],'input parse'); req(hashlib.sha256(rr).hexdigest()==c['caseResultSha256'] and hashlib.sha256(pr).hexdigest()==c['preparedSha256'] and hashlib.sha256(sr).hexdigest()==c['radianceSha256'] and hashlib.sha256(st).hexdigest()==c['stdRadianceSha256'],'embedded hashes')
 return {'caseId':c['caseId'],'inputResolvedSha256':hashlib.sha256(ir).hexdigest(),'physicalInputCanonicalSha256':ch(p),'caseResultSha256':c['caseResultSha256'],'preparedSha256':c['preparedSha256'],'radianceSha256':c['radianceSha256'],'stdRadianceSha256':c['stdRadianceSha256']}
def main():
 a=argparse.ArgumentParser(); a.add_argument('--protocol',type=Path,required=True); a.add_argument('--builder',type=Path,required=True); a.add_argument('--historical-admission',type=Path,required=True); a.add_argument('--output-dir',type=Path,required=True); x=a.parse_args(); token=os.environ.get('GITHUB_TOKEN',''); repo=os.environ.get('GITHUB_REPOSITORY',''); req(token and repo=='search-maker/twilight-mystic-experiments','github context')
 p=json.loads(x.protocol.read_text()); validate_protocol(p); b=load_builder(x.builder); exp=set(b.expected_case_keys()); req(len(b.TRAINING_IDS)==39 and len(b.HOLDOUT_IDS)==9 and len(exp)==166 and not ({g for g,_ in exp}&set(b.HOLDOUT_IDS)),'builder universe')
 adm=json.loads(x.historical_admission.read_text()); req(adm.get('expectedCaseArtifactCount')==166 and adm.get('expectedGeometryCount')==39 and adm.get('fullTrainingUniversePresent') is True and adm.get('fittingAuthorized') is False,'admission')
 sel={}; src=[]; excluded=[]; base=f'https://api.github.com/repos/{repo}'
 for sp in p['sourceRuns']:
  r=api(f"{base}/actions/runs/{sp['runId']}",token); req((r.get('id'),r.get('head_sha'),r.get('run_attempt'),r.get('event'),r.get('conclusion'),r.get('path'))==(sp['runId'],sp['headSha'],sp['runAttempt'],sp['event'],sp['conclusion'],sp['workflowPath']) and r.get('status')=='completed','run identity')
  n=0
  for ar in arts(repo,sp['runId'],token):
   k=key(str(ar.get('name','')))
   if not k: continue
   if k[0] in b.HOLDOUT_IDS: excluded.append({'runId':sp['runId'],'artifactId':ar.get('id'),'artifactName':ar.get('name'),'geometryId':k[0],'block':k[1]}); continue
   if k[1] not in sp['blocks'] or k not in exp: continue
   req(k not in sel and ar.get('expired') is False and re.fullmatch(r'sha256:[0-9a-f]{64}',str(ar.get('digest',''))),'artifact metadata'); wr=ar.get('workflow_run') or {}; req(not wr or (wr.get('id')==sp['runId'] and wr.get('head_sha')==sp['headSha']),'artifact run'); sel[k]={'sp':sp,'ar':ar}; n+=1
  req(n==sp['expectedTrainingCaseArtifacts'],'run case count'); src.append({'ordinal':sp['ordinal'],'runId':sp['runId'],'runAttempt':sp['runAttempt'],'headSha':sp['headSha'],'event':sp['event'],'conclusion':sp['conclusion'],'selectedTrainingCaseArtifactCount':n})
 req(set(sel)==exp,'exact 166 selection'); x.output_dir.mkdir(parents=True,exist_ok=True); tmp=Path(tempfile.mkdtemp(prefix='replay-'))
 try:
  def get(it):
   k,v=it; ar=v['ar']; raw=dl(repo,int(ar['id']),token); h=hashlib.sha256(raw).hexdigest(); req('sha256:'+h==ar['digest'],'transport digest'); q=tmp/f'{k[0]}-replay-b{k[1]}-{ar["id"]}.zip'; q.write_bytes(raw); return k,q,{'geometryId':k[0],'block':k[1],'sourceOrdinal':v['sp']['ordinal'],'runId':v['sp']['runId'],'runAttempt':v['sp']['runAttempt'],'headSha':v['sp']['headSha'],'artifactId':ar['id'],'artifactName':ar['name'],'githubArtifactDigest':ar['digest'],'downloadedZipSha256':h,'expiredAtReplay':False}
  paths={}; trans=[]
  with cf.ThreadPoolExecutor(max_workers=12) as pool:
   for f in cf.as_completed([pool.submit(get,it) for it in sorted(sel.items())]): k,q,e=f.result(); paths[k]=q; trans.append(e)
  trans.sort(key=lambda e:(e['geometryId'],e['block'])); req(len(trans)==166,'transport count')
  cases=[b.parse_case(paths[k]) for k in sorted(exp)]; req({(c['geometryId'],int(c['block'])) for c in cases}==exp and all(c['geometryId'] not in b.HOLDOUT_IDS for c in cases),'parsed universe'); req(all(c['positivePrimaryChannels'] or c['rawAllZero'] for c in cases),'channel state')
  fps=[inspect(paths[(c['geometryId'],int(c['block']))],b,c) for c in cases]; fps.sort(key=lambda e:e['caseId']); rec=b.aggregate(cases); zeros=sorted(c['caseId'] for c in cases if c['rawAllZero']); req(len(rec)==39,'aggregate record count'); req(all((not c['rawAllZero']) or (c['channels']['photopicLuminanceCdM2']==0.0 and c['channels']['scotopicLuminanceScotCdM2']==0.0 and c['channels']['johnsonVEffectiveRadiance_mW_m2_nm_sr']==0.0) for c in cases),'exact-zero preservation')
  ac=[b.parse_case(paths[k]) for k in sorted(exp)]; ar=b.aggregate(ac); req(ch(ac)==ch(cases) and ch(ar)==ch(rec),'independent second pass')
  tm={'schemaVersion':1,'stageId':'public-artifact-pipeline-replay-v1-transport-manifest','protocolSha256':p['protocolSha256'],'sourceRuns':src,'expectedTrainingCaseArtifactCount':166,'observedTrainingCaseArtifactCount':166,'excludedHoldoutArtifactMetadataCount':len(excluded),'holdoutArtifactsDownloaded':False,'entries':trans}; tm['transportManifestSha256']=ch(tm)
  zero_hash=ch(zeros)
  ds={'schemaVersion':1,'stageId':'public-artifact-pipeline-replay-v1-training-handoff','protocolSha256':p['protocolSha256'],'historicalBuilderGitBlobSha':BUILDER,'trainingGeometryIds':list(b.TRAINING_IDS),'internalHoldoutGeometryIdsExcluded':list(b.HOLDOUT_IDS),'holdoutValuesRead':False,'holdoutRecordCount':0,'observedCaseArtifactCount':166,'trainingGeometryRecordCount':39,'zeroHitCaseIds':zeros,'rawExactZeroCaseSetSha256':zero_hash,'physicalInputFingerprintManifestSha256':ch(fps),'caseEvidence':cases,'records':rec,'scientificExecutionPerformed':False,'modelFittingAuthorized':False,'modelSelectionAuthorized':False}; ds['replayDatasetSha256']=ch(ds)
  gates={'INPUT_RENDER_AND_PHYSICAL_FINGERPRINT':len(fps)==166,'PREPARED_CASE_BINDING':len(cases)==166,'CASE_RESULT_AND_RAW_SPECTRUM_HASHING':len(cases)==166,'TRANSPORT_ARTIFACT_ID_AND_DIGEST_BINDING':all(e['githubArtifactDigest']=='sha256:'+e['downloadedZipSha256'] for e in trans),'FULL_SPECTRUM_DERIVED_CHANNEL_REINTEGRATION':len(rec)==39,'AGGREGATE_AND_INDEPENDENT_AUDIT':ch(ar)==ch(rec),'TRAINING_HANDOFF_ROLE_EXCLUSION':not any(c['geometryId'] in b.HOLDOUT_IDS for c in cases)}; req(list(gates)==MUST_EXERCISE and all(gates.values()),'gate coverage')
  at={'schemaVersion':1,'attestationId':'public-artifact-pipeline-replay-v1-candidate-attestation','attestationSha256':None,'protocolId':PID,'protocolSha256':p['protocolSha256'],'governance':GOV,'status':'CANDIDATE_REPLAY_PASS_REQUIRES_SEPARATE_VERSIONED_RESULT_BINDING','replayHeadSha':os.environ.get('GITHUB_SHA'),'sourceRuns':src,'transportManifestSha256':tm['transportManifestSha256'],'replayDatasetSha256':ds['replayDatasetSha256'],'physicalInputFingerprintManifestSha256':ds['physicalInputFingerprintManifestSha256'],'trainingCaseArtifactCount':166,'trainingGeometryCount':39,'internalHoldoutGeometryCountExcluded':9,'holdoutValuesRead':False,'zeroHitCaseCount':len(zeros),'rawExactZeroCaseSetSha256':zero_hash,'allRequiredReplaySurfacesPassed':True,'replaySurfaceResults':gates,'historicalReferenceHashes':p['historicalReferenceHashes'],'historicalReferenceConsistency':{'caseArtifactCountMatches':True,'geometryCountMatches':True,'rawExactZeroCasesPreservedAndReportedWithoutAdmissionCountConflation':True},'decisionSemantics':{'existingRealArtifactsOnly':True,'newScientificExecutionPerformed':False,'solverInvoked':False,'campaignAuthorizationIssued':False,'campaignDispatchIssued':False,'scientificOrdinalAllocated':False,'nextScientificOrdinal':None,'modelFittingAuthorized':False,'modelSelectionAuthorized':False,'protectedHoldoutOpeningAuthorized':False,'productionPromotionAuthorized':False},'nextBoundary':{'replayGateSatisfiedByThisCandidateAlone':False,'separateVersionedResultBindingPRRequired':True,'scientificExecutionAllowedNow':False,'ordinal19AllocationAllowedNow':False}}; at['attestationSha256']=self_hash_null(at,'attestationSha256')
  for name,obj in [('transport-manifest.json',tm),('training-handoff-replay.json',ds),('artifact-pipeline-replay-attestation.json',at)]: (x.output_dir/name).write_text(json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+'\n')
  print(json.dumps({'status':at['status'],'transportManifestSha256':tm['transportManifestSha256'],'replayDatasetSha256':ds['replayDatasetSha256'],'attestationSha256':at['attestationSha256'],'trainingCaseArtifactCount':166,'trainingGeometryCount':39,'zeroHitCaseCount':len(zeros),'rawExactZeroCaseSetSha256':zero_hash,'excludedHoldoutArtifactMetadataCount':len(excluded)},indent=2,sort_keys=True))
 finally: shutil.rmtree(tmp,ignore_errors=True)
 return 0
if __name__=='__main__': raise SystemExit(main())
