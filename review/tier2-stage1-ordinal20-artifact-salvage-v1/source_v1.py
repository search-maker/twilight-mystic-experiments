#!/usr/bin/env python3
from __future__ import annotations
import copy, hashlib, json, math, subprocess, zipfile
from pathlib import Path
from typing import Any
from common_v1 import *
def expected_case_artifact_name(case_id:str)->str: return 'tier2-stage1-case-'+case_id

def source_job_for(case_id:str,jobs:list[dict[str,Any]])->dict[str,Any]:
    hits=[j for j in jobs if str(j.get('name','')).startswith(f'cases ({case_id}, ')]
    req(len(hits)==1,f'source case job occurrence !=1: {case_id}')
    j=hits[0]; req(j.get('status')=='completed' and j.get('conclusion')=='failure','source case job status drift')
    req(j.get('run_attempt')==1 and j.get('runner_id') not in (None,0),'source case job attempt/runner drift')
    steps={s.get('name'):s.get('conclusion') for s in j.get('steps',[])}
    req(steps.get('Re-prove exact runtime identity without solver execution')=='success','runtime-identity step drift')
    req(steps.get('Execute exactly one syntax check and one stage1 solver invocation')=='failure','source solver/parser step status drift')
    req(steps.get('Run actions/upload-artifact@v4')=='success','source artifact upload step drift')
    return j

def verify_run_metadata(contract:dict[str,Any],manifest:dict[str,Any],run:dict[str,Any],jobs_doc:dict[str,Any],art_doc:dict[str,Any])->tuple[dict[str,dict[str,Any]],dict[str,dict[str,Any]]]:
    src=contract['source']; expected={'id':src['runId'],'status':'completed','conclusion':'failure','run_attempt':src['runAttempt'],'head_sha':src['headSha'],'head_branch':src['headBranch'],'event':src['event'],'path':src['workflowPath']}
    stale={k:(run.get(k),v) for k,v in expected.items() if run.get(k)!=v}; req(not stale,f'source run identity drift: {stale}')
    jobs=jobs_doc.get('jobs',[]); req(jobs_doc.get('total_count')==src['expectedJobCount'] and len(jobs)==src['expectedJobCount'],'source job count drift')
    pf=[j for j in jobs if j.get('name')=='preflight']; req(len(pf)==1 and pf[0].get('conclusion')=='success','source preflight drift')
    for c in manifest['cases']: source_job_for(c['caseId'],jobs)
    arts=art_doc.get('artifacts',[]); req(len(arts)==src['expectedArtifactCount'],'source artifact count drift')
    by_name={a.get('name'):a for a in arts}; req(len(by_name)==len(arts),'duplicate source artifact name')
    expected_names={f"tier2-stage1-preflight-{src['headSha']}",f"tier2-stage1-aggregate-{src['headSha']}"}|{expected_case_artifact_name(c['caseId']) for c in manifest['cases']}
    req(set(by_name)==expected_names,f'source artifact universe drift: missing={sorted(expected_names-set(by_name))} extra={sorted(set(by_name)-expected_names)}')
    for a in arts:
        req(a.get('expired') is False and str(a.get('digest','')).startswith('sha256:'),'expired/unhashed source artifact')
        wr=a.get('workflow_run') or {}; req(wr.get('id')==src['runId'] and wr.get('head_sha')==src['headSha'] and wr.get('head_branch')==src['headBranch'],'source artifact run binding drift')
    pfa=by_name[f"tier2-stage1-preflight-{src['headSha']}"]; aga=by_name[f"tier2-stage1-aggregate-{src['headSha']}"]
    req((pfa.get('id'),pfa.get('digest'))==(src['preflightArtifact']['id'],src['preflightArtifact']['digest']),'preflight artifact identity drift')
    req((aga.get('id'),aga.get('digest'))==(src['aggregateArtifact']['id'],src['aggregateArtifact']['digest']),'aggregate artifact identity drift')
    for anchor in src['serializationAnchors']:
        a=by_name[expected_case_artifact_name(anchor['caseId'])]; req((a.get('id'),a.get('digest'))==(anchor['artifactId'],anchor['artifactDigest']),f'serialization anchor drift: {anchor["caseId"]}')
    return by_name,{c['caseId']:source_job_for(c['caseId'],jobs) for c in manifest['cases']}

def gh_json(endpoint:str)->dict[str,Any]:
    out=subprocess.check_output(['gh','api',endpoint],text=True); x=json.loads(out); req(isinstance(x,dict),'GitHub API object required'); return x
def download_artifact(repo:str,artifact:dict[str,Any],dest:Path)->None:
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('wb') as f: subprocess.run(['gh','api',f'repos/{repo}/actions/artifacts/{artifact["id"]}/zip'],stdout=f,check=True)
    want=str(artifact['digest']).split(':',1)[1]; req(sha_path(dest)==want,f'artifact ZIP digest drift: {artifact["id"]}')

def verify_source_blobs(repo_root:Path,contract:dict[str,Any])->None:
    head=contract['source']['headSha']
    for path,want in contract['source']['sourceBlobSha'].items():
        got=subprocess.check_output(['git','rev-parse',f'{head}:{path}'],cwd=repo_root,text=True).strip(); req(got==want,f'source blob drift: {path}: {got}')

def selfhash_ok(obj:dict[str,Any],field:str)->bool:
    got=obj.get(field); z=copy.deepcopy(obj); z.pop(field,None); return got==canon(z)

def verify_case_zip(zip_path:Path,artifact:dict[str,Any],job:dict[str,Any],case:dict[str,Any],geometry:dict[str,Any],manifest:dict[str,Any],contract:dict[str,Any],extract_root:Path)->dict[str,Any]:
    required=set(manifest['artifactContract']['requiredMembers'])
    with zipfile.ZipFile(zip_path) as z:
        names=z.namelist(); req(len(names)==len(set(names)) and set(names)==required,f'case artifact member universe drift: {case["caseId"]}')
        source_result=json.loads(z.read('case-result.json').decode('utf-8')); req(selfhash_ok(source_result,'contentSha256'),'source refusal selfhash drift')
        req(source_result.get('caseId')==case['caseId'] and source_result.get('status')=='FAILED_OR_REFUSED_TERMINAL_ATTEMPT1','source case-result identity/status drift')
        req(source_result.get('reason')=='raw spectrum step/order drift','source refusal reason drift')
        req(source_result.get('workflowRunAttempt')==1 and source_result.get('retryPerformed') is False and source_result.get('resumePerformed') is False and source_result.get('githubRerun') is False,'source attempt boundary drift')
        req(source_result.get('protectedHoldoutValueExposed') is False,'source holdout exposure flag drift')
        prepared=json.loads(z.read('prepared.json').decode('utf-8')); runtime=json.loads(z.read('runtime-report.json').decode('utf-8')); inp=z.read('input-resolved.txt'); seed_text=z.read('randomseed').decode('utf-8').strip()
        req(prepared.get('caseId')==case['caseId'] and prepared.get('geometryId')==case['geometryId'] and prepared.get('block')==case['block'] and prepared.get('role')=='surrogate-training','prepared case identity drift')
        req(prepared.get('seed')==case['seed'] and prepared.get('photonHistories')==case['photonHistories'],'prepared seed/photon drift')
        req(prepared.get('executionManifestSha256')==manifest['manifestSha256'],'prepared manifest hash drift')
        req(prepared.get('inputResolvedSha256')==sha_bytes(inp),'prepared input hash drift')
        req(prepared.get('physicalInputCanonicalSha256')==canon(prepared.get('inputs')),'prepared physical fingerprint drift')
        x=prepared.get('inputs') or {}; expected_input={'caseId':case['caseId'],'groupId':case['geometryId'],'method':'alis','block':case['block'],'seed':case['seed'],'photonHistories':case['photonHistories'],'sunDepressionDeg':geometry['sunDepressionDeg'],'targetAltitudeDeg':geometry['targetAltitudeDeg'],'relativeAzimuthDeg':geometry['relativeAzimuthDeg'],'observerElevationM':geometry['observerElevationM'],'aod550':geometry['aod550'],'alisSpectralImportanceSamplingNm':case['alisSpectralImportanceSamplingNm']}
        stale={k:(x.get(k),v) for k,v in expected_input.items() if x.get(k)!=v}; req(not stale,f'prepared physical input drift: {case["caseId"]}: {stale}')
        req(seed_text==str(case['seed']),'randomseed member drift')
        it=inp.decode('utf-8',errors='strict'); req(f'mc_randomseed {case["seed"]}' in it and f'mc_photons {case["photonHistories"]}' in it,'resolved seed/photon input drift')
        want_runtime=manifest.get('runtimeIdentityRequired') or {}
        for k in RUNTIME_KEYS: req(runtime.get(k)==want_runtime.get(k),f'runtime identity drift: {case["caseId"]}/{k}')
        rad=parse_spectrum_bytes(z.read('mc.rad.spc'),contract['gridSerialization']); std=parse_spectrum_bytes(z.read('mc.rad.std.spc'),contract['gridSerialization'])
        req(rad['wavelengthTokens']==std['wavelengthTokens'],'radiance/std wavelength token mismatch')
        raw_hash={name:sha_bytes(z.read(name)) for name in sorted(required-{'case-result.json'})}
        dest=extract_root/case['caseId']; dest.mkdir(parents=True,exist_ok=False)
        for name in sorted(required): (dest/name).write_bytes(z.read(name))
    ch=channels(rad['wavelengths'],rad['lastColumn'])
    rec={'schemaVersion':1,'stageId':'tier2-stage1-ordinal20-artifact-salvage-case-v1','status':'ARTIFACT_ONLY_SALVAGED_COMPLETED','caseId':case['caseId'],'geometryId':case['geometryId'],'block':case['block'],'role':'surrogate-training','seed':case['seed'],'photonHistories':case['photonHistories'],'sourceRunId':contract['source']['runId'],'sourceRunAttempt':1,'sourceHeadSha':contract['source']['headSha'],'sourceArtifactId':artifact['id'],'sourceArtifactDigest':artifact['digest'],'sourceArtifactSizeBytes':artifact['size_in_bytes'],'sourceCaseResultSha256':sha_bytes((extract_root/case['caseId']/'case-result.json').read_bytes()),'sourceCaseResultStatus':'FAILED_OR_REFUSED_TERMINAL_ATTEMPT1','sourceCaseResultReason':'raw spectrum step/order drift','sourceJobId':job['id'],'sourceJobName':job['name'],'sourceJobConclusion':job['conclusion'],'sourceSolverParserStepConclusion':'failure','solverExecutionCountProven':1,'retryPerformed':False,'resumePerformed':False,'githubRerun':False,'protectedHoldoutValueExposed':False,'physicalInputCanonicalSha256':prepared['physicalInputCanonicalSha256'],'inputResolvedSha256':prepared['inputResolvedSha256'],'runtimeReportSha256':sha_bytes((extract_root/case['caseId']/'runtime-report.json').read_bytes()),'rawMemberSha256ByBasename':raw_hash,'radianceOutputSha256':raw_hash['mc.rad.spc'],'stdRadianceOutputSha256':raw_hash['mc.rad.std.spc'],'wavelengthTokenGridSha256':rad['gridSha256'],'wavelengthNodeCount':rad['rowCount'],'legacyParserRefusalReproduced':not rad['legacyParserAccepts'],'radianceStdGridIdentity':True,'rawExactZeroScalarCount':rad['exactZeroScalarCount'],'rawAllZero':rad['rawAllZeroLastColumn'],'channels':ch,'rawBytesModified':False,'modelFittingAuthorized':False,'protectedHoldoutOpeningAuthorized':False}
    rec['contentSha256']=canon(rec); write_json(extract_root/case['caseId']/'salvage-case.json',rec); return rec
