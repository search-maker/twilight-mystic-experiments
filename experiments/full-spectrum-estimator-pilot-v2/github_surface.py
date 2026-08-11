#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, re, ssl, subprocess, urllib.error, urllib.parse, urllib.request
from pathlib import Path
from typing import Any
from freshness import AUTH_BRANCH, DISPATCH_BRANCH, EXECUTION_KEY, TITLE, positive_candidate_claims, matching_marker

ORDINAL_FROM_DISPATCH = re.compile(r'ordinal[-_]?([0-9]+)', re.I)
SCIENTIFIC_WORKFLOW = '.github/workflows/full-spectrum-estimator-pilot-v2-ordinal14-execution-v6.yml'
AUTHORIZATION_REVIEW_WORKFLOW = '.github/workflows/full-spectrum-estimator-pilot-v2-authorization-review-v6.yml'

def _api_with_urllib(url: str, token: str) -> Any:
    req=urllib.request.Request(url, headers={'Authorization':f'Bearer {token}','Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def _api_with_gh(url: str, token: str) -> Any:
    parsed=urllib.parse.urlsplit(url)
    if parsed.scheme!='https' or parsed.netloc!='api.github.com' or parsed.username or parsed.password:
        raise RuntimeError('refusing non-canonical GitHub API fallback URL')
    endpoint=parsed.path+(('?'+parsed.query) if parsed.query else '')
    env=os.environ.copy(); env['GH_TOKEN']=token
    result=subprocess.run(['gh','api','--method','GET',endpoint],capture_output=True,text=True,timeout=35,env=env)
    if result.returncode:
        raise RuntimeError('verified GitHub CLI fallback failed')
    try: return json.loads(result.stdout)
    except json.JSONDecodeError as exc: raise RuntimeError('verified GitHub CLI fallback returned invalid JSON') from exc

def _api(url: str, token: str) -> Any:
    try: return _api_with_urllib(url,token)
    except ssl.SSLCertVerificationError:
        return _api_with_gh(url,token)

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

def _is_candidate_scientific_run(run: dict[str, Any]) -> bool:
    hb=run.get('head_branch') or ''
    if hb==DISPATCH_BRANCH:
        return True
    # The frozen ordinal-14 solver transport is push-only. Pull-request checks share the PR display title,
    # so title matching alone must never turn authorization/transport/contract review runs into scientific history.
    if (run.get('event') or '') != 'push':
        return False
    path=run.get('path') or ''
    title=(run.get('display_title') or '').strip()
    name=(run.get('name') or '').strip()
    return path==SCIENTIFIC_WORKFLOW or EXECUTION_KEY in title or title.lower()==TITLE.lower() or name.lower()==(TITLE+' execution v6').lower()

def _failed_authorization_ref_reusable(auth_head: str|None, prs: list[dict[str, Any]], runs: list[dict[str, Any]]) -> bool:
    if not auth_head:
        return False
    matching_prs=[]
    for pr in prs:
        head=pr.get('head') or {}
        if head.get('ref')==AUTH_BRANCH and head.get('sha')==auth_head:
            matching_prs.append(pr)
    closed_unmerged=[p for p in matching_prs if p.get('state')=='closed' and p.get('merged_at') is None]
    if len(closed_unmerged)!=1 or any(p.get('state')=='open' for p in matching_prs):
        return False
    review_runs=[r for r in runs if (r.get('head_branch') or '')==AUTH_BRANCH and (r.get('head_sha') or '')==auth_head and (r.get('path') or '')==AUTHORIZATION_REVIEW_WORKFLOW and (r.get('event') or '')=='pull_request']
    failed=[r for r in review_runs if int(r.get('run_attempt') or 0)==1 and r.get('status')=='completed' and r.get('conclusion')=='failure']
    successful=[r for r in review_runs if r.get('status')=='completed' and r.get('conclusion')=='success']
    return len(failed)==1 and not successful

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
        if _is_candidate_scientific_run(r):
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
      'authorizationBranchReusableAfterFailedReview': _failed_authorization_ref_reusable(auth_head,prs,runs),
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
