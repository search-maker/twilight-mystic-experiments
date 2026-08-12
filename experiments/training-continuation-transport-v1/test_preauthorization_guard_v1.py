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
        badcomments=[{'id':77,'body':'created authorization/training-continuation-train0014-ordinal18'}]
        try: build(c,'train0014',branches,runs,[],badcomments,source,p1,conf,p2); raise AssertionError('Issue marker collision accepted')
        except Refusal: pass
        # Seed collision mutation must refuse.
        source_bad=dict(source); source_bad['sourceCases']=list(source['sourceCases']); source_bad['sourceCases'][0]={'seed':1700000001}
        td3,p3=fake_git_blob_file(source_bad)
        try:
            c2=json.loads(json.dumps(c)); c2['preauthorizationInputs']['source166SeedAudit']['gitBlobSha']=git_blob_sha1(p3); c2['contractSha256']=canon({k:v for k,v in c2.items() if k!='contractSha256'})
            try: build(c2,'train0014',branches,runs,[],[],source_bad,p3,conf,p2); raise AssertionError('source seed collision accepted')
            except Refusal: pass
        finally: td3.cleanup()
        print('PASS: repository-global preauthorization seed/ref/run/artifact/Issue refusal tests')
    finally: td1.cleanup(); td2.cleanup()
if __name__=='__main__': main()
