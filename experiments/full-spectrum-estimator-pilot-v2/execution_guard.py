#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from typing import Any
from freshness import DISPATCH_BRANCH
from dispatch_guard import evaluate as dispatch_evaluate
from authorization_guard import require

def load(p:Path): return json.loads(p.read_text())
def evaluate(auth:dict[str,Any],ctx:dict[str,Any])->dict[str,Any]:
    dispatch_ctx=ctx.get('dispatchEligibility') or {}
    d=dispatch_evaluate(auth,dispatch_ctx,post_dispatch=True)
    head=d['authorizationHead']
    require(ctx.get('githubActions') is True,'scientific execution must run in GitHub Actions')
    require(ctx.get('eventName')=='push','scientific workflow is push-only')
    require(ctx.get('refName')==DISPATCH_BRANCH,'scientific workflow trigger branch drift')
    require(ctx.get('headSha')==head,'dispatch ref does not point to reviewed authorization head')
    require(ctx.get('dispatchBranchHeadSha')==head,'live dispatch branch head drift')
    require(ctx.get('runAttempt')==1,'scientific workflow attempt must be exactly 1')
    require(ctx.get('priorMatchingScientificRuns')==0,'candidate scientific workflow has prior run; retry/rerun refused')
    require(ctx.get('resumeRequested') is False,'resume refused')
    require(ctx.get('retryRequested') is False,'retry refused')
    require(ctx.get('automaticDownstreamTransition') is False,'automatic downstream scientific transition refused')
    return {'status':'SCIENTIFIC_EXECUTION_GUARD_PASS','authorizationHead':head,'runAttempt':1,'oneSyntaxCheckPerCase':True,'solverExecutionsPerCaseMaximum':1,'automaticFittingAuthorized':False}
def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--authorization',type=Path,required=True); ap.add_argument('--context',type=Path,required=True); ap.add_argument('--output',type=Path); a=ap.parse_args()
    try:
        out=evaluate(load(a.authorization),load(a.context)); text=json.dumps(out,indent=2,sort_keys=True)+'\n'; a.output.write_text(text) if a.output else print(text,end=''); return 0
    except Exception as exc:
        print(json.dumps({'status':'REFUSED','reason':str(exc)},sort_keys=True),file=sys.stderr); return 2
if __name__=='__main__': raise SystemExit(main())
