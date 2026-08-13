#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,re
from pathlib import Path
from common_v1 import *
ORD=re.compile(r'ordinal[-_]?([1-9][0-9]*)',re.I)

def flatten_list(p):
    x=json.loads(p.read_text()); require(isinstance(x,list),'pages malformed'); return [r for page in x for r in page]
def flatten_obj(p,key):
    x=json.loads(p.read_text()); require(isinstance(x,list),'pages malformed'); return [r for page in x for r in page.get(key,[])]
def consumed(branches,runs):
    out=[]
    for name in [str(x.get('name') or '') for x in branches]+[str(x.get('head_branch') or '') for x in runs if x.get('event')=='push']:
        if name.startswith('dispatch/'):
            m=ORD.search(name)
            if m: out.append(int(m.group(1)))
    return out

def seed_set(rows,label):
    require(isinstance(rows,list),f'{label} missing')
    out=[]
    for row in rows:
        require(isinstance(row,dict),f'{label} row malformed')
        seed=row.get('seed'); require(isinstance(seed,int),f'{label} seed malformed'); out.append(seed)
    require(len(out)==len(set(out)),f'{label} contains duplicate seeds')
    return set(out)

def verify_source_seed_audit(contract,audit,path):
    b=contract['preauthorizationInputs']['source166SeedAudit']
    require(git_blob_sha1(path)==b['gitBlobSha'], 'source166 seed audit Git blob identity drift')
    require(audit.get('auditId')==b['auditId'] and audit.get('auditSha256')==b['auditSha256'],'source166 seed audit identity drift')
    require(audit.get('status')=='PASSED_LOCAL_EXACT_166_SOURCE_SEED_AUDIT','source166 seed audit not passed')
    source=seed_set(audit.get('sourceCases'),'source166 audit sourceCases'); require(len(source)==166,'source166 seed universe drift')
    require(audit.get('sourceCasesCanonicalSha256')==b['sourceCasesCanonicalSha256'],'source166 canonical identity drift')
    pilot=seed_set(audit.get('candidateCases'),'pilot candidateCases')
    return source,pilot

def verify_confirmation_prereg(contract,prereg,path):
    b=contract['preauthorizationInputs']['ordinal17ConfirmationPreregistration']
    require(git_blob_sha1(path)==b['gitBlobSha'],'ordinal17 confirmation preregistration Git blob identity drift')
    require(prereg.get('preregistrationSha256')==b['preregistrationSha256'],'ordinal17 confirmation preregistration identity drift')
    cases=(prereg.get('caseDesign') or {}).get('cases'); seeds=seed_set(cases,'ordinal17 confirmation cases')
    require(len(seeds)==24,'ordinal17 confirmation seed universe drift')
    return seeds

VARIANT_DISPLAY={'train0014':'train-0014','train0037':'train-0037'}

LEGACY_PR137_ACTIVATION_ARTIFACT={
    'variant':'train0014','nextOrdinal':18,
    'artifactId':9163137456,'artifactName':'training-continuation-train0014-ordinal18-activation-review',
    'artifactDigest':'sha256:d00d4977894faeeb345f05db702ea61b7a5a686f43cacad10ac8724b9c875f32','artifactSize':2791,
    'runId':31652512386,'workflowName':'Training continuation train-0014 ordinal18 activation review',
    'workflowPath':'.github/workflows/training-continuation-train0014-ordinal18-activation-review.yml',
    'event':'pull_request','runAttempt':1,'status':'completed','conclusion':'success',
    'headBranch':'codex/github-mention-prepare-train-0014-ordinal-18-activation-wit',
    'headSha':'abf5da606f8094d8eebcb76dcdac906bf45b9acf',
}

def is_pr137_legacy_activation_review_artifact(variant,nexto,artifact,runs):
    e=LEGACY_PR137_ACTIVATION_ARTIFACT
    if variant!=e['variant'] or nexto!=e['nextOrdinal']:
        return False
    if (artifact.get('id')!=e['artifactId'] or artifact.get('name')!=e['artifactName']
            or artifact.get('digest')!=e['artifactDigest'] or artifact.get('size_in_bytes')!=e['artifactSize']):
        return False
    workflow_run=artifact.get('workflow_run')
    if not isinstance(workflow_run,dict) or workflow_run.get('id')!=e['runId']:
        return False
    linked=[x for x in runs if x.get('id')==e['runId']]
    if len(linked)!=1:
        return False
    run=linked[0]
    return (
        run.get('name')==e['workflowName'] and run.get('path')==e['workflowPath']
        and run.get('event')==e['event'] and run.get('run_attempt')==e['runAttempt']
        and run.get('status')==e['status'] and run.get('conclusion')==e['conclusion']
        and run.get('head_branch')==e['headBranch'] and run.get('head_sha')==e['headSha']
        and workflow_run.get('head_branch')==e['headBranch'] and workflow_run.get('head_sha')==e['headSha']
    )

def is_verified_activation_review_artifact(variant,nexto,artifact,runs):
    expected_artifact=f'training-continuation-{variant}-ordinal{nexto}-activation-review'
    if artifact.get('name')!=expected_artifact:
        return False
    workflow_run=artifact.get('workflow_run')
    if not isinstance(workflow_run,dict):
        return False
    run_id=workflow_run.get('id')
    if not isinstance(run_id,int) or run_id<=0:
        return False
    linked=[x for x in runs if x.get('id')==run_id]
    if len(linked)!=1:
        return False
    run=linked[0]
    expected_branch=f'agent/{variant}-ordinal{nexto}-activation-v1'
    expected_name=f"Training continuation {VARIANT_DISPLAY[variant]} ordinal{nexto} activation review"
    expected_path=f'.github/workflows/training-continuation-{variant}-ordinal{nexto}-activation-review.yml'
    head_sha=run.get('head_sha')
    return (
        run.get('name')==expected_name
        and run.get('path')==expected_path
        and run.get('event')=='pull_request'
        and run.get('run_attempt')==1
        and run.get('status')=='completed'
        and run.get('conclusion')=='success'
        and run.get('head_branch')==expected_branch
        and isinstance(head_sha,str) and re.fullmatch(r'[0-9a-f]{40}',head_sha) is not None
        and workflow_run.get('head_branch')==expected_branch
        and workflow_run.get('head_sha')==head_sha
    )

def build(contract,variant,branches,runs,artifacts,issue_comments,source_audit,source_audit_path,confirmation_prereg,confirmation_prereg_path):
    verify_self(contract,'contractSha256'); require(contract.get('status')=='REVIEW_ONLY_DISABLED_TRANSPORT_NOT_AUTHORIZED','transport contract boundary drift')
    spec=contract['sourcePreregistrations'][variant]; ords=consumed(branches,runs); require(ords,'no consumed ordinal history found'); latest=max(ords); nexto=latest+1
    seeds=set(spec['seeds']); require(len(seeds)==spec['caseCount'],'candidate seed uniqueness/count drift')
    source_seeds,pilot_seeds=verify_source_seed_audit(contract,source_audit,source_audit_path)
    confirmation_seeds=verify_confirmation_prereg(contract,confirmation_prereg,confirmation_prereg_path)
    other='train0037' if variant=='train0014' else 'train0014'; other_seeds=set(contract['sourcePreregistrations'][other]['seeds'])
    collisions={
        'source166':sorted(seeds & source_seeds),
        'pilot':sorted(seeds & pilot_seeds),
        'ordinal17Confirmation':sorted(seeds & confirmation_seeds),
        'otherFrozenContinuationVariant':sorted(seeds & other_seeds),
    }
    require(not any(collisions.values()),f'candidate seed collision: {collisions}')

    auth_prefix=f'authorization/training-continuation-{variant}-ordinal'
    dispatch_prefix=f'dispatch/training-continuation-{variant}-ordinal'
    branch_names=[str(x.get('name') or '') for x in branches]
    ref_collisions=sorted(n for n in branch_names if n.startswith(auth_prefix) or n.startswith(dispatch_prefix)); require(not ref_collisions,f'authorization/dispatch ref collision already exists: {ref_collisions}')
    scientific_runs=[int(x.get('id') or 0) for x in runs if x.get('event')=='push' and str(x.get('head_branch') or '').startswith(dispatch_prefix)]; require(not scientific_runs,f'prior scientific push run exists: {scientific_runs}')
    artifact_prefix=f'training-continuation-{variant}-'
    scientific_artifacts=[]
    for x in artifacts:
        if not str(x.get('name') or '').lower().startswith(artifact_prefix):
            continue
        if (is_verified_activation_review_artifact(variant,nexto,x,runs)
                or is_pr137_legacy_activation_review_artifact(variant,nexto,x,runs)):
            continue
        scientific_artifacts.append({'id':x.get('id'),'name':x.get('name')})
    require(not scientific_artifacts,f'prior scientific artifact exists: {scientific_artifacts}')
    marker_re=re.compile(rf'^ORDINAL{nexto}_{variant.upper()}_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED commit=([0-9a-f]{{40}}) parent=([0-9a-f]{{40}}) pr=([1-9][0-9]*)$',re.I)
    issue_markers=[]
    for x in issue_comments:
        body=str(x.get('body') or '').strip()
        if marker_re.fullmatch(body):
            issue_markers.append(int(x.get('id') or 0))
    require(not issue_markers,f'prior Issue #60 exact authorization-allocation marker exists: {issue_markers}')

    out={'schemaVersion':1,'reportId':f'public-tier1-training-continuation-{variant}-preauthorization-review-v2','status':'PREAUTHORIZATION_SURFACE_CLEAN_NOT_ALLOCATED','variant':variant,'transportContractSha256':contract['contractSha256'],'candidateSeedCount':len(seeds),'candidateSeedRange':[min(seeds),max(seeds)],'source166SeedCount':len(source_seeds),'pilotSeedCount':len(pilot_seeds),'ordinal17ConfirmationSeedCount':len(confirmation_seeds),'otherFrozenContinuationSeedCount':len(other_seeds),'seedCollisions':collisions,'latestConsumedScientificOrdinal':latest,'nextAvailableScientificOrdinalIfAllocatedLater':nexto,'authorizationOrdinalAllocated':False,'authorizationRefAllocated':False,'executionKeyAllocated':False,'dispatchBranchAllocated':False,'scientificExecutionAuthorized':False,'dispatchAuthorized':False,'repositoryGlobalBranchesInspected':True,'repositoryGlobalActionsRunsInspected':True,'repositoryGlobalActionsArtifactsInspected':True,'controlIssue60CommentsInspected':True,'source166SeedAuditVerified':True,'ordinal17ConfirmationSeedLedgerVerified':True,'note':'Fresh report only. It does not allocate the reported ordinal and must be repeated after transport merge immediately before authorization.'}; out['reportSha256']=canon(out); return out

def main():
    p=argparse.ArgumentParser(); p.add_argument('--contract',type=Path,required=True); p.add_argument('--variant',choices=['train0014','train0037'],required=True); p.add_argument('--branches-pages',type=Path,required=True); p.add_argument('--runs-pages',type=Path,required=True); p.add_argument('--artifacts-pages',type=Path,required=True); p.add_argument('--issue-comments-pages',type=Path,required=True); p.add_argument('--source-seed-audit',type=Path,required=True); p.add_argument('--confirmation-preregistration',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
    try:
        o=build(load(a.contract),a.variant,flatten_list(a.branches_pages),flatten_obj(a.runs_pages,'workflow_runs'),flatten_obj(a.artifacts_pages,'artifacts'),flatten_list(a.issue_comments_pages),load(a.source_seed_audit),a.source_seed_audit,load(a.confirmation_preregistration),a.confirmation_preregistration)
        a.output.write_text(json.dumps(o,indent=2,sort_keys=True)+'\n'); print(json.dumps(o,sort_keys=True)); return 0
    except Exception as e: print(json.dumps({'status':'REFUSED','reason':str(e)})); return 2
if __name__=='__main__': raise SystemExit(main())
