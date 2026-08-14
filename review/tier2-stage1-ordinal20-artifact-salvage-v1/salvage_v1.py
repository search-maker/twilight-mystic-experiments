#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, statistics, zipfile
from pathlib import Path
from typing import Any
from common_v1 import *
from source_v1 import *
def aggregate_records(manifest:dict[str,Any],records:list[dict[str,Any]],contract:dict[str,Any])->dict[str,Any]:
    req(len(records)==76 and len({r['caseId'] for r in records})==76,'salvage case universe drift')
    geoms=[]
    for g in manifest['geometries']:
        rows=sorted([r for r in records if r['geometryId']==g['geometryId']],key=lambda r:r['block']); req([r['block'] for r in rows]==[1,2,3,4],f'geometry block universe drift: {g["geometryId"]}')
        means={}; se={}
        for k in rows[0]['channels']:
            vals=[r['channels'][k] for r in rows]; means[k]=statistics.fmean(vals); se[k]=statistics.stdev(vals)/2.0
        geoms.append({'geometryId':g['geometryId'],'role':'surrogate-training','blockCount':4,'channelsMean':means,'channelsBlockStandardError':se,'rawExactZeroCaseIds':[r['caseId'] for r in rows if r['rawAllZero']]})
    evidence=[{k:r[k] for k in ('caseId','geometryId','block','seed','photonHistories','sourceArtifactId','sourceArtifactDigest','radianceOutputSha256','stdRadianceOutputSha256','wavelengthTokenGridSha256','physicalInputCanonicalSha256','rawAllZero','channels')} for r in records]
    out={'schemaVersion':1,'stageId':'tier2-stage1-ordinal20-artifact-salvage-aggregate-v1','status':'TRAINING_ACQUISITION_RECOVERED_FROM_IMMUTABLE_ORDINAL20_ARTIFACTS_NO_FITTING','contractId':contract['contractId'],'manifestSha256':manifest['manifestSha256'],'sourceRunId':contract['source']['runId'],'sourceHeadSha':contract['source']['headSha'],'caseCount':76,'trainingGeometryCount':19,'configuredPhotonHistories':sum(r['photonHistories'] for r in records),'caseEvidence':evidence,'records':geoms,'rawExactZeroCaseIds':sorted(r['caseId'] for r in records if r['rawAllZero']),'holdoutValuesRead':False,'protectedHoldoutRecordCount':0,'modelFittingAuthorized':False,'modelSelectionAuthorized':False,'protectedHoldoutOpeningAuthorized':False,'stage2Authorized':False,'sourceArtifactsModified':False}
    out['aggregateSha256']=canon(out); return out

def execute(repo_root:Path,manifest_path:Path,contract_path:Path,out_root:Path)->None:
    contract=load(contract_path); manifest=load(manifest_path); validate_contract(contract); validate_manifest(manifest); verify_source_blobs(repo_root,contract)
    repo=contract['source']['repository']; rid=contract['source']['runId']
    run=gh_json(f'repos/{repo}/actions/runs/{rid}'); jobs=gh_json(f'repos/{repo}/actions/runs/{rid}/jobs?per_page=100'); arts=gh_json(f'repos/{repo}/actions/runs/{rid}/artifacts?per_page=100')
    by_name,job_map=verify_run_metadata(contract,manifest,run,jobs,arts)
    meta_dir=out_root/'source-metadata'; write_json(meta_dir/'run.json',run); write_json(meta_dir/'jobs.json',jobs); write_json(meta_dir/'artifacts.json',arts)
    zips=out_root/'artifact-zips'; extracted=out_root/'source-cases'; zips.mkdir(parents=True,exist_ok=True); extracted.mkdir(parents=True,exist_ok=True)
    for n in (f"tier2-stage1-preflight-{contract['source']['headSha']}",f"tier2-stage1-aggregate-{contract['source']['headSha']}"):
        download_artifact(repo,by_name[n],zips/(n+'.zip'))
    with zipfile.ZipFile(zips/(f"tier2-stage1-preflight-{contract['source']['headSha']}"+'.zip')) as z:
        hits=[n for n in z.namelist() if n.endswith('stage1-execution-manifest-v1.json')]; req(len(hits)==1,'preflight manifest member drift'); req(z.read(hits[0])==manifest_path.read_bytes(),'preflight manifest bytes drift')
    with zipfile.ZipFile(zips/(f"tier2-stage1-aggregate-{contract['source']['headSha']}"+'.zip')) as z:
        req(z.namelist()==['aggregate.json'],'source aggregate member drift'); a=json.loads(z.read('aggregate.json').decode('utf-8')); req(a.get('status')=='REFUSED' and a.get('reason')=='case status/role drift','source aggregate refusal drift'); req(a.get('holdoutValuesRead') is False and a.get('protectedHoldoutRecordCount')==0 and a.get('modelFittingAuthorized') is False and a.get('protectedHoldoutOpeningAuthorized') is False,'source aggregate boundary drift')
    geom={g['geometryId']:g for g in manifest['geometries']}; records=[]; inventory=[]; ledger=[]
    for c in manifest['cases']:
        name=expected_case_artifact_name(c['caseId']); a=by_name[name]; zp=zips/(name+'.zip'); download_artifact(repo,a,zp); r=verify_case_zip(zp,a,job_map[c['caseId']],c,geom[c['geometryId']],manifest,contract,extracted); records.append(r)
        inventory.append({'artifactId':a['id'],'artifactName':a['name'],'artifactDigest':a['digest'],'sizeBytes':a['size_in_bytes'],'caseId':c['caseId'],'geometryId':c['geometryId'],'block':c['block'],'role':'surrogate-training','seed':c['seed'],'photonHistories':c['photonHistories'],'sourceCaseStatus':r['sourceCaseResultStatus'],'sourceRefusalReason':r['sourceCaseResultReason'],'memberNames':sorted(manifest['artifactContract']['requiredMembers']),'rawMemberSha256ByBasename':r['rawMemberSha256ByBasename'],'wavelengthTokenGridSha256':r['wavelengthTokenGridSha256'],'legacyParserRefusalReproduced':True,'solverExecutionCountProven':1,'protectedHoldoutValueExposed':False})
        ledger.append({'caseId':c['caseId'],'geometryId':c['geometryId'],'block':c['block'],'seed':c['seed'],'sourceArtifactId':a['id'],'sourceArtifactDigest':a['digest'],'sourceJobId':r['sourceJobId'],'solverExecutionCountProven':1,'consumed':True,'reuseAuthorized':False})
    inv={'schemaVersion':1,'stageId':'tier2-stage1-ordinal20-artifact-inventory-v1','status':'COMPLETE','sourceRunId':rid,'sourceHeadSha':contract['source']['headSha'],'artifactCount':78,'caseArtifactCount':76,'preflightArtifact':by_name[f"tier2-stage1-preflight-{contract['source']['headSha']}"],'aggregateArtifact':by_name[f"tier2-stage1-aggregate-{contract['source']['headSha']}"],'cases':inventory,'holdoutValuesRead':False,'protectedHoldoutRecordCount':0}; inv['inventorySha256']=canon(inv); write_json(out_root/'inventory.json',inv)
    led={'schemaVersion':1,'stageId':'tier2-stage1-ordinal20-consumed-training-seed-ledger-v1','status':'ALL_76_STAGE1_SOLVER_SEEDS_CONSUMED','sourceRunId':rid,'caseCount':76,'consumedSeedCount':76,'entries':ledger,'protectedHoldoutSeedCount':0,'holdoutValuesRead':False,'reuseAuthorized':False}; led['ledgerSha256']=canon(led); write_json(out_root/'consumed-training-seed-ledger.json',led)
    agg=aggregate_records(manifest,records,contract); write_json(out_root/'aggregate.json',agg)

def handoff(manifest_path:Path,contract_path:Path,out_root:Path,audit_path:Path)->None:
    manifest=load(manifest_path); contract=load(contract_path); agg=load(out_root/'aggregate.json'); inv=load(out_root/'inventory.json'); ledger=load(out_root/'consumed-training-seed-ledger.json'); audit=load(audit_path)
    req(audit.get('status')=='PASSED' and audit.get('aggregateSha256')==agg.get('aggregateSha256'),'audit not passed/bound')
    out={'schemaVersion':1,'stageId':'tier2-stage1-ordinal20-artifact-salvage-training-handoff-v1','status':'TRAINING_DATASET_RECOVERED_AND_FROZEN_PENDING_TRAINING_ONLY_SPECTRAL_ADEQUACY_AND_MODEL_FREEZE','contractId':contract['contractId'],'manifestSha256':manifest['manifestSha256'],'sourceRunId':contract['source']['runId'],'sourceHeadSha':contract['source']['headSha'],'inventorySha256':inv['inventorySha256'],'consumedSeedLedgerSha256':ledger['ledgerSha256'],'aggregateSha256':agg['aggregateSha256'],'auditSha256':audit['auditSha256'],'trainingCaseCount':76,'trainingGeometryCount':19,'configuredPhotonHistories':2_120_000_000,'holdoutValuesRead':False,'protectedHoldoutRecordCount':0,'trainingOnlySpectralAdequacyDecisionClosed':False,'modelFittingAuthorized':False,'modelSelectionAuthorized':False,'protectedHoldoutOpeningAuthorized':False,'stage2Authorized':False,'newSolverExecutionAuthorized':False,'sourceArtifactsModified':False}; out['handoffSha256']=canon(out); write_json(out_root/'training-handoff.json',out)

def main()->int:
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='cmd',required=True)
    e=sub.add_parser('execute'); e.add_argument('--repo-root',type=Path,required=True); e.add_argument('--manifest',type=Path,required=True); e.add_argument('--contract',type=Path,required=True); e.add_argument('--output-root',type=Path,required=True)
    h=sub.add_parser('handoff'); h.add_argument('--manifest',type=Path,required=True); h.add_argument('--contract',type=Path,required=True); h.add_argument('--output-root',type=Path,required=True); h.add_argument('--audit',type=Path,required=True)
    v=sub.add_parser('validate-contract'); v.add_argument('--contract',type=Path,required=True)
    a=p.parse_args()
    try:
        if a.cmd=='execute': execute(a.repo_root,a.manifest,a.contract,a.output_root)
        elif a.cmd=='handoff': handoff(a.manifest,a.contract,a.output_root,a.audit)
        else: validate_contract(load(a.contract))
        return 0
    except Exception as e:
        print(json.dumps({'status':'REFUSED','reason':str(e)},sort_keys=True),file=os.sys.stderr); return 2
if __name__=='__main__': raise SystemExit(main())
