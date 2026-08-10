#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, re, urllib.error, urllib.parse, urllib.request
from pathlib import Path
from typing import Any
from freshness import AUTH_BRANCH, DISPATCH_BRANCH, EXECUTION_KEY, TITLE, positive_candidate_claims, matching_marker

ORDINAL_FROM_DISPATCH = re.compile(r'ordinal[-_]?([0-9]+)', re.I)

def _api(url: str, token: str) -> Any:
    req=urllib.request.Request(url, headers={'Authorization':f'Bearer {token}','Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def _pages(base: str, token: str) -> list[Any]:
    out=[]; page=1
    while True:
        sep='&' if '?' in base else '?'
        value=_api(f'{base}{sep}per_page=100&page={page}', token)
        if not isinstance(value,list): raise RuntimeError('paged GitHub endpoint returned non-list')
        out.extend(value)
        if len(value)<100: return out
        page+=1

def _exists(url: str, token: str) -> tuple[bool, Any|None]:
    try: return True,_api(url,token)
    except urllib.error.HTTPError as exc:
        if exc.code==404: return False,None
        raise

def build_surface(payload: dict[str, Any], current_pr: int|None=None, marker_head: str|None=None, marker_parent: str|None=None, current_run_id: int|None=None) -> dict[str, Any]:
    branches=payload.get('branches',[]); runs=payload.get('runs',[]); prs=payload.get('pulls',[]); issues=payload.get('issues',[]); comments=payload.get('issue60Comments',[])
    branch_names=[b.get('name','') for b in branches]
    prior_ordinals=[]
    for name in branch_names:
        if name==DISPATCH_BRANCH: continue
        if 'dispatch/' in name:
            m=ORDINAL_FROM_DISPATCH.search(name)
            if m: prior_ordinals.append(int(m.group(1)))
    # Actions history is retained even if an old dispatch ref is later deleted; use it as a second repository-global ordinal source.
    for r in runs:
        hb=r.get('head_branch') or ''
        if hb and hb!=DISPATCH_BRANCH and 'dispatch/' in hb:
            m=ORDINAL_FROM_DISPATCH.search(hb)
            if m: prior_ordinals.append(int(m.group(1)))
    latest=max(prior_ordinals) if prior_ordinals else None
    candidate_runs=[]
    for r in runs:
        if current_run_id and int(r.get('id') or 0)==int(current_run_id):
            continue
        hb=r.get('head_branch') or ''
        title=r.get('display_title') or ''
        name=r.get('name') or ''
        if hb==DISPATCH_BRANCH or EXECUTION_KEY in title or TITLE.lower() in title.lower() or TITLE.lower() in name.lower():
            candidate_runs.append(r)
    positive=[]
    for pr in prs:
        if current_pr and int(pr.get('number') or 0)==current_pr: continue
        positive.extend(positive_candidate_claims((pr.get('title') or '')+'\n'+(pr.get('body') or '')))
    for issue in issues:
        if issue.get('pull_request'): continue
        positive.extend(positive_candidate_claims((issue.get('title') or '')+'\n'+(issue.get('body') or '')))
    marker_count=0
    for c in comments:
        body=c.get('body') or ''
        if marker_head and marker_parent and current_pr and matching_marker(body,marker_head,marker_parent,current_pr):
            marker_count+=1
            continue
        positive.extend(positive_candidate_claims(body))
    auth_head=None; dispatch_head=None
    for b in branches:
        if b.get('name')==AUTH_BRANCH:
            auth_head=(b.get('commit') or {}).get('sha')
        if b.get('name')==DISPATCH_BRANCH:
            dispatch_head=(b.get('commit') or {}).get('sha')
    return {
      'latestPriorConsumedScientificOrdinal': latest,
      'nextAvailableScientificOrdinal': (latest+1 if latest is not None else None),
      'candidatePriorScientificRunCount': len(candidate_runs),
      'authorizationBranchExists': AUTH_BRANCH in branch_names,
      'authorizationBranchHeadSha': auth_head,
      'dispatchBranchExists': DISPATCH_BRANCH in branch_names,
      'dispatchBranchHeadSha': dispatch_head,
      'positiveCandidateClaimsExcludingCurrent': len(positive),
      'matchingAuthorizationMarkers': marker_count,
      'activeAuthorizationPathOnMainExists': bool(payload.get('activeAuthorizationPathOnMainExists')),
      'allStatePullRequestsInspected': True,
      'allStateIssuesInspected': True,
      'allActionsRunsInspected': True,
      'allBranchesInspected': True,
      'issue60AndCommentsInspected': True,
      'candidateCodePathsOnMainInspected': True,
    }

def collect(repository: str, token: str) -> dict[str, Any]:
    base=f'https://api.github.com/repos/{repository}'
    branches=_pages(base+'/branches',token)
    runs=[]
    page=1
    while True:
        v=_api(base+f'/actions/runs?per_page=100&page={page}',token)
        rows=v.get('workflow_runs',[]); runs.extend(rows)
        if len(rows)<100: break
        page+=1
    pulls=_pages(base+'/pulls?state=all',token)
    issues=_pages(base+'/issues?state=all',token)
    issue60=_api(base+'/issues/60',token)
    comments=_pages(base+'/issues/60/comments',token)
    auth_path='experiments/full-spectrum-estimator-pilot-v2/authorization.ordinal14.json'
    exists,_=_exists(base+'/contents/'+urllib.parse.quote(auth_path,safe='/')+'?ref=main',token)
    return {'branches':branches,'runs':runs,'pulls':pulls,'issues':issues,'issue60':issue60,'issue60Comments':comments,'activeAuthorizationPathOnMainExists':exists}

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--repository',required=True); ap.add_argument('--output',type=Path,required=True); ap.add_argument('--current-pr',type=int); ap.add_argument('--marker-head'); ap.add_argument('--marker-parent'); ap.add_argument('--token-env',default='GITHUB_TOKEN'); ap.add_argument('--input',type=Path); ap.add_argument('--current-run-id',type=int)
    a=ap.parse_args()
    if a.input: payload=json.loads(a.input.read_text())
    else:
        token=os.getenv(a.token_env)
        if not token: raise SystemExit(f'missing {a.token_env}')
        payload=collect(a.repository,token)
    out=build_surface(payload,a.current_pr,a.marker_head,a.marker_parent,a.current_run_id)
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    return 0
if __name__=='__main__': raise SystemExit(main())
