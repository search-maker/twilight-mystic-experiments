#!/usr/bin/env python3
from pathlib import Path
import sys,tempfile,json
HERE=Path(__file__).resolve().parent; sys.path.insert(0,str(HERE))
from common_v1 import *
from preauthorization_guard_v1 import build

def fake_git_blob_file(obj):
    td=tempfile.TemporaryDirectory(); p=Path(td.name)/'x.json'; p.write_text(json.dumps(obj,sort_keys=True,separators=(',',':'))); return td,p

def main():
    c=load(HERE/'transport-contract.v1.json')
    # Replace immutable file bindings only inside this synthetic unit-test contract, then re-self-hash it.
    source={'auditId':'source-audit','auditSha256':'a'*64,'status':'PASSED_LOCAL_EXACT_166_SOURCE_SEED_AUDIT','sourceCases':[{'seed':1000+i} for i in range(166)],'candidateCases':[{'seed':970001+i} for i in range(44)],'sourceCasesCanonicalSha256':'b'*64}
    conf={'preregistrationSha256':'c'*64,'caseDesign':{'cases':[{'seed':1600000001+i} for i in range(24)]}}
    td1,p1=fake_git_blob_file(source); td2,p2=fake_git_blob_file(conf)
    try:
        c['preauthorizationInputs']['source166SeedAudit']={'path':'x','gitBlobSha':git_blob_sha1(p1),'auditId':'source-audit','auditSha256':'a'*64,'sourceCasesCanonicalSha256':'b'*64}
        c['preauthorizationInputs']['ordinal17ConfirmationPreregistration']={'path':'y','gitBlobSha':git_blob_sha1(p2),'preregistrationSha256':'c'*64}
        c['contractSha256']=canon({k:v for k,v in c.items() if k!='contractSha256'})
        branches=[{'name':'dispatch/full-spectrum-estimator-confirmation-v1-ordinal17'}]
        runs=[{'id':1,'event':'push','head_branch':'dispatch/full-spectrum-estimator-confirmation-v1-ordinal17','name':'x','display_title':'x'}]
        r=build(c,'train0014',branches,runs,[],[],source,p1,conf,p2)
        assert r['latestConsumedScientificOrdinal']==17 and r['nextAvailableScientificOrdinalIfAllocatedLater']==18
        assert r['source166SeedAuditVerified'] is True and not any(r['seedCollisions'].values())
        assert r['authorizationOrdinalAllocated'] is False and r['scientificExecutionAuthorized'] is False
        bad=branches+[{'name':'dispatch/training-continuation-train0014-ordinal18'}]
        try: build(c,'train0014',bad,runs,[],[],source,p1,conf,p2); raise AssertionError('branch collision accepted')
        except Refusal: pass
        badruns=runs+[{'id':99,'event':'push','head_branch':'dispatch/training-continuation-train0037-ordinal19','name':'x','display_title':'x'}]
        try: build(c,'train0037',branches,badruns,[],[],source,p1,conf,p2); raise AssertionError('run collision accepted')
        except Refusal: pass
        # Descriptive Issue #60 discussion may mention future auth/dispatch refs; only the
        # exact allocation marker consumed by execution_guard_v1.py counts as allocation.
        discussion=[{'id':76,'body':'correction keeps dispatch/training-continuation-train0014-ordinal18 dormant and authorization/training-continuation-train0014-ordinal18 absent'}]
        dr=build(c,'train0014',branches,runs,[],discussion,source,p1,conf,p2)
        assert dr['authorizationOrdinalAllocated'] is False
        exact_marker='ORDINAL18_TRAIN0014_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED commit='+'a'*40+' parent='+'b'*40+' pr=136'
        badcomments=[{'id':77,'body':exact_marker}]
        try: build(c,'train0014',branches,runs,[],badcomments,source,p1,conf,p2); raise AssertionError('exact Issue allocation marker accepted')
        except Refusal: pass
        embedded=[{'id':78,'body':'not allocated; example only: '+exact_marker}]
        er=build(c,'train0014',branches,runs,[],embedded,source,p1,conf,p2)
        assert er['authorizationOrdinalAllocated'] is False

        # A prior activation-review artifact is non-scientific only when it is tightly linked
        # to the exact successful attempt-1 pull-request review run for this pending ordinal.
        head='a'*40
        review_run={'id':31638997308,'name':'Training continuation train-0014 ordinal18 activation review','path':'.github/workflows/training-continuation-train0014-ordinal18-activation-review.yml','event':'pull_request','run_attempt':1,'status':'completed','conclusion':'success','head_branch':'agent/train0014-ordinal18-activation-v1','head_sha':head}
        review_artifact={'id':9158119416,'name':'training-continuation-train0014-ordinal18-activation-review','workflow_run':{'id':31638997308,'head_branch':'agent/train0014-ordinal18-activation-v1','head_sha':head}}
        review_runs=runs+[review_run]
        rr=build(c,'train0014',branches,review_runs,[review_artifact],[],source,p1,conf,p2)
        assert rr['status']=='PREAUTHORIZATION_SURFACE_CLEAN_NOT_ALLOCATED'
        combined=build(c,'train0014',branches,review_runs,[review_artifact],discussion,source,p1,conf,p2)
        assert combined['status']=='PREAUTHORIZATION_SURFACE_CLEAN_NOT_ALLOCATED'

        # PR #137's one known Codex-branch activation artifact is non-scientific only
        # when every immutable artifact, run, head, and workflow-run linkage agrees.
        legacy_head='abf5da606f8094d8eebcb76dcdac906bf45b9acf'
        legacy_branch='codex/github-mention-prepare-train-0014-ordinal-18-activation-wit'
        legacy_run={'id':31652512386,'name':'Training continuation train-0014 ordinal18 activation review','path':'.github/workflows/training-continuation-train0014-ordinal18-activation-review.yml','event':'pull_request','run_attempt':1,'status':'completed','conclusion':'success','head_branch':legacy_branch,'head_sha':legacy_head}
        legacy_artifact={'id':9163137456,'name':'training-continuation-train0014-ordinal18-activation-review','digest':'sha256:d00d4977894faeeb345f05db702ea61b7a5a686f43cacad10ac8724b9c875f32','size_in_bytes':2791,'workflow_run':{'id':31652512386,'head_branch':legacy_branch,'head_sha':legacy_head}}
        lr=build(c,'train0014',branches,runs+[legacy_run],[legacy_artifact],[],source,p1,conf,p2)
        assert lr['status']=='PREAUTHORIZATION_SURFACE_CLEAN_NOT_ALLOCATED'

        def refuse_legacy_case(label,artifact=None,run=None):
            a=legacy_artifact if artifact is None else artifact
            rr=legacy_run if run is None else run
            try: build(c,'train0014',branches,runs+[rr],[a],[],source,p1,conf,p2); raise AssertionError(label+' accepted')
            except Refusal: pass

        for field,value,label in [
            ('id',9163137457,'legacy artifact id drift'),
            ('digest','sha256:'+'0'*64,'legacy artifact digest drift'),
            ('size_in_bytes',2792,'legacy artifact size drift'),
        ]:
            a=json.loads(json.dumps(legacy_artifact)); a[field]=value; refuse_legacy_case(label,artifact=a)
        for field,value,label in [
            ('id',31652512387,'legacy run id drift'),
            ('event','push','legacy event drift'),
            ('run_attempt',2,'legacy attempt drift'),
            ('status','in_progress','legacy status drift'),
            ('conclusion','failure','legacy conclusion drift'),
            ('name','Training continuation train-0014 ordinal18 execution','legacy workflow name drift'),
            ('path','.github/workflows/training-continuation-train0014-ordinal18-execution.yml','legacy workflow path drift'),
            ('head_branch','codex/other','legacy head branch drift'),
            ('head_sha','b'*40,'legacy head SHA drift'),
        ]:
            rr=json.loads(json.dumps(legacy_run)); rr[field]=value; refuse_legacy_case(label,run=rr)
        a=json.loads(json.dumps(legacy_artifact)); a['workflow_run']['head_branch']='codex/other'; refuse_legacy_case('legacy workflow_run branch linkage drift',artifact=a)
        a=json.loads(json.dumps(legacy_artifact)); a['workflow_run']['head_sha']='b'*40; refuse_legacy_case('legacy workflow_run SHA linkage drift',artifact=a)

        def refuse_review_case(label,artifact=None,run=None,extra_runs=None):
            a=review_artifact if artifact is None else artifact
            rs=runs+([review_run if run is None else run])+(extra_runs or [])
            try: build(c,'train0014',branches,rs,[a],[],source,p1,conf,p2); raise AssertionError(label+' accepted')
            except Refusal: pass

        a=json.loads(json.dumps(review_artifact)); a.pop('workflow_run'); refuse_review_case('unlinked activation-review artifact',artifact=a)
        a=json.loads(json.dumps(review_artifact)); a['workflow_run']['id']=999; refuse_review_case('activation-review artifact with unknown run',artifact=a)
        for field,value,label in [
            ('event','push','activation-review push run'),
            ('run_attempt',2,'activation-review retry run'),
            ('status','in_progress','activation-review incomplete run'),
            ('conclusion','failure','activation-review failed run'),
            ('name','Training continuation train-0014 ordinal18 execution','activation-review wrong workflow name'),
            ('path','.github/workflows/training-continuation-train0014-ordinal18-execution.yml','activation-review wrong workflow path'),
            ('head_branch','agent/other','activation-review wrong branch'),
        ]:
            br=json.loads(json.dumps(review_run)); br[field]=value; refuse_review_case(label,run=br)
        a=json.loads(json.dumps(review_artifact)); a['workflow_run']['head_sha']='b'*40; refuse_review_case('activation-review head mismatch',artifact=a)
        refuse_review_case('duplicate linked run id',extra_runs=[json.loads(json.dumps(review_run))])
        for name in [
            'training-continuation-train0014-ordinal18-preflight',
            'training-continuation-train0014-case-train-0014-fs-acquire-alis-600-t1',
            'training-continuation-train0014-ordinal18-analysis',
            'training-continuation-train0014-ordinal18-authorization-review',
        ]:
            try: build(c,'train0014',branches,review_runs,[{'id':123,'name':name}],[],source,p1,conf,p2); raise AssertionError('scientific/non-activation artifact accepted: '+name)
            except Refusal: pass

        # Seed collision mutation must refuse.
        source_bad=dict(source); source_bad['sourceCases']=list(source['sourceCases']); source_bad['sourceCases'][0]={'seed':1700000001}
        td3,p3=fake_git_blob_file(source_bad)
        try:
            c2=json.loads(json.dumps(c)); c2['preauthorizationInputs']['source166SeedAudit']['gitBlobSha']=git_blob_sha1(p3); c2['contractSha256']=canon({k:v for k,v in c2.items() if k!='contractSha256'})
            try: build(c2,'train0014',branches,runs,[],[],source_bad,p3,conf,p2); raise AssertionError('source seed collision accepted')
            except Refusal: pass
        finally: td3.cleanup()
        print('PASS: repository-global preauthorization seed/ref/run/artifact/Issue refusal tests including exact activation-review evidence classification')
    finally: td1.cleanup(); td2.cleanup()
if __name__=='__main__': main()
