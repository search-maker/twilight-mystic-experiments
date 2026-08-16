#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from typing import Any
AUTH_BRANCH='authorization/level-b-v3-fresh-validation-ordinal28-v1'
LOCK_BRANCH='allocation/level-b-v3-fresh-validation-ordinal28-v1'
DISPATCH_BRANCH='dispatch/level-b-v3-fresh-validation-ordinal28-v1'
ORDINAL_PREFIX='ALLOCATED-SCIENCE-IDENTITY | MYSTIC-STATE-0072 | ordinal=28 | '
SEED_SUFFIX=' | seeds=2110000001-2110000024'
class Refusal(RuntimeError):pass
def req(c:bool,m:str)->None:
    if not c:raise Refusal(m)
def flat(v:Any,key:str|None=None)->list[dict[str,Any]]:
    req(isinstance(v,list),'paginated array required');out=[]
    for page in v:
        rows=page.get(key,[]) if key is not None and isinstance(page,dict) else page
        req(isinstance(rows,list),'page rows array required');out.extend(x for x in rows if isinstance(x,dict))
    return out
def exact_marker(auth_head:str)->str:return f'{ORDINAL_PREFIX}authHead={auth_head}{SEED_SUFFIX}'
def validate_markers(comments:list[dict[str,Any]],auth_head:str)->dict[str,Any]:
    expected=exact_marker(auth_head); bodies=[str(c.get('body') or '').strip() for c in comments if ORDINAL_PREFIX in str(c.get('body') or '')]
    req(len(bodies)>=1,'ordinal28 allocation marker missing');distinct=sorted(set(bodies));req(distinct==[expected],f'distinct ordinal28 marker body: {distinct}');n=sum(x==expected for x in bodies);req(n>=1,'exact marker missing');return {'expectedMarkerBody':expected,'exactMarkerCopies':n,'logicalAllocationIdentityCount':1}
def validate_dispatch(branch_pages:Any,run_pages:Any,comment_pages:Any,auth_head:str,current_run_id:int)->dict[str,Any]:
    branches=flat(branch_pages);runs=flat(run_pages,'workflow_runs');comments=flat(comment_pages);by={str(b.get('name') or ''):str((b.get('commit') or {}).get('sha') or '') for b in branches}
    req(by.get(AUTH_BRANCH)==auth_head,'authorization branch/head drift');req(by.get(LOCK_BRANCH)==auth_head,'allocation lock missing/wrong');req(by.get(DISPATCH_BRANCH)==auth_head,'dispatch branch/head drift')
    for prefix,exact in (('authorization/level-b-v3-fresh-validation-ordinal28-',AUTH_BRANCH),('allocation/level-b-v3-fresh-validation-ordinal28-',LOCK_BRANCH),('dispatch/level-b-v3-fresh-validation-ordinal28-',DISPATCH_BRANCH)):
        aliases=[(n,s) for n,s in by.items() if n.startswith(prefix) and not(n==exact and s==auth_head)];req(not aliases,f'competing ordinal28 ref: {aliases}')
    rr=[r for r in runs if r.get('event')=='push' and str(r.get('head_branch') or '').startswith('dispatch/level-b-v3-fresh-validation-ordinal28-')]
    req(len(rr)==1,f'expected exactly one ordinal28 dispatch push run, found {[(r.get("id"),r.get("head_branch"),r.get("head_sha")) for r in rr]}');cur=rr[0]
    req(int(cur.get('id') or 0)==int(current_run_id),'dispatch push run is not current');req(str(cur.get('head_branch') or '')==DISPATCH_BRANCH and str(cur.get('head_sha') or '')==auth_head,'dispatch run identity drift');req(int(cur.get('run_attempt') or 0)==1,'dispatch attempt must be 1')
    return {'status':'PASS','authorizationBranch':AUTH_BRANCH,'allocationLockBranch':LOCK_BRANCH,'dispatchBranch':DISPATCH_BRANCH,'authHead':auth_head,'currentRunId':int(current_run_id),**validate_markers(comments,auth_head)}
def load(p:Path)->Any:return json.loads(p.read_text(encoding='utf-8'))
def main()->int:
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='cmd',required=True);m=sub.add_parser('markers');m.add_argument('--comments',type=Path,required=True);m.add_argument('--auth-head',required=True);d=sub.add_parser('dispatch');d.add_argument('--branches',type=Path,required=True);d.add_argument('--runs',type=Path,required=True);d.add_argument('--comments',type=Path,required=True);d.add_argument('--auth-head',required=True);d.add_argument('--current-run-id',type=int,required=True);a=ap.parse_args()
    try:r=validate_markers(flat(load(a.comments)),a.auth_head) if a.cmd=='markers' else validate_dispatch(load(a.branches),load(a.runs),load(a.comments),a.auth_head,a.current_run_id);print(json.dumps({'status':'PASS',**r},sort_keys=True));return 0
    except Exception as e:print(json.dumps({'status':'REFUSED','reason':str(e)},sort_keys=True));return 2
if __name__=='__main__':raise SystemExit(main())
