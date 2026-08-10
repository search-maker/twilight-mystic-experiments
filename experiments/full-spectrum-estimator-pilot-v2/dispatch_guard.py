#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path
from typing import Any
from freshness import AUTH_BRANCH, validate_dispatch, matching_marker
from authorization_guard import validate_static, validate_enabled_document, require
SHA40=re.compile(r'^[0-9a-f]{40}$')
def load(p:Path): return json.loads(p.read_text())
def evaluate(auth:dict[str,Any],ctx:dict[str,Any],post_dispatch:bool=False)->dict[str,Any]:
    c,b=validate_static(); head=ctx.get('authorizationHead'); parent=ctx.get('authorizationParent'); pr=ctx.get('pr') or {}; review=ctx.get('authorizationReview') or {}
    require(isinstance(head,str) and SHA40.fullmatch(head),'authorization head invalid')
    require(isinstance(parent,str) and SHA40.fullmatch(parent),'authorization parent invalid')
    require(ctx.get('liveMain')==parent,'live main moved after authorization review')
    validate_enabled_document(auth,parent,c,b)
    require(pr.get('state')=='open' and pr.get('draft') is True and pr.get('merged') is False,'authorization PR no longer Draft/open/unmerged')
    require(pr.get('headBranch')==AUTH_BRANCH and pr.get('headSha')==head,'authorization PR head/branch drift')
    require(review.get('headSha')==head and review.get('prNumber')==pr.get('number'),'authorization review identity drift')
    require(review.get('workflow')==c['authorizationReviewRules']['workflow'],'authorization review workflow drift')
    require(review.get('runAttempt')==1 and review.get('conclusion')=='success','exact successful attempt-1 authorization review required')
    require(review.get('scientificRuntimeSetupPerformed') is False and review.get('scientificExecutionPerformed') is False,'authorization review was not zero-runtime')
    validate_dispatch(ctx.get('freshness') or {},head,post_dispatch=post_dispatch)
    markers=ctx.get('issue60Markers') or []
    good=[m for m in markers if matching_marker(m,head,parent,int(pr.get('number') or 0))]
    require(len(good)==1 and len(markers)==1,'exactly one exact Issue #60 authorization marker required')
    return {'status':'DISPATCH_ELIGIBLE_NOT_CREATED','authorizationHead':head,'authorizationParent':parent,'authorizationPr':pr['number'],'dispatchBranchMayPointTo':head,'scientificExecutionPerformed':False}
def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--authorization',type=Path,required=True); ap.add_argument('--context',type=Path,required=True); ap.add_argument('--output',type=Path); a=ap.parse_args()
    try:
        out=evaluate(load(a.authorization),load(a.context)); text=json.dumps(out,indent=2,sort_keys=True)+'\n'; a.output.write_text(text) if a.output else print(text,end=''); return 0
    except Exception as exc:
        print(json.dumps({'status':'REFUSED','reason':str(exc)},sort_keys=True),file=sys.stderr); return 2
if __name__=='__main__': raise SystemExit(main())
