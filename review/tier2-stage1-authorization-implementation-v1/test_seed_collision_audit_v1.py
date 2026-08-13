#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, shutil, subprocess, tempfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
SPEC=importlib.util.spec_from_file_location('auditmod',HERE/'audit_tier2_stage1_seed_collisions_v1.py')
A=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(A)
BASE=json.loads((HERE/'tier2-stage1-authorization-implementation-v1.json').read_text(encoding='utf-8'))

def sh(*args:str,cwd:Path)->None:
    subprocess.run(args,cwd=cwd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

def make_repo(extra_text:str|None=None)->tuple[Path,Path,tempfile.TemporaryDirectory]:
    td=tempfile.TemporaryDirectory(); root=Path(td.name)
    sh('git','init','-q',cwd=root); sh('git','config','user.email','ci@example.invalid',cwd=root); sh('git','config','user.name','ci',cwd=root)
    for rel in BASE['seedCollisionReviewAudit']['allowedTrackedSelfLedgerPaths']:
        p=root/rel; p.parent.mkdir(parents=True,exist_ok=True)
        if rel.endswith('tier2-stage1-authorization-implementation-v1.json'):
            p.write_text(json.dumps(BASE,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        else:
            p.write_text('# declared self-ledger validation surface\n',encoding='utf-8')
    if extra_text is not None:
        p=root/'external-seed-declaration.txt'; p.write_text(extra_text,encoding='utf-8')
    sh('git','add','.',cwd=root); sh('git','commit','-qm','fixture',cwd=root)
    review=root/'review/tier2-stage1-authorization-implementation-v1/tier2-stage1-authorization-implementation-v1.json'
    return root,review,td

root,review,td=make_repo()
try:
    out=A.audit(root,review)
    assert out['status']=='PASSED_EXACT_HEAD_TRACKED_TREE_NEGATIVE_COLLISION_CHECK'
    assert out['externalCollisionCount']==0 and out['authorizationPermitted'] is False
    assert out['artifactRunHistoryRecheckStillRequired'] is True
finally: td.cleanup()

first=BASE['seedCollisionReviewAudit']['candidateLedgerFirstSeed']
for text in (str(first)+'\n', format(first,'_')+'\n'):
    root,review,td=make_repo(text)
    try:
        try: A.audit(root,review)
        except A.V.Refusal: pass
        else: raise SystemExit(f'accepted external collision literal: {text.strip()}')
    finally: td.cleanup()

print('PASS: exact and underscored external seed collisions refused')
