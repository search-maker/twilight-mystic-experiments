from __future__ import annotations
import argparse, hashlib, importlib.util, json, os
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"experiments/aerosol-family-challenge-v2/repository_global_seed_scan.py"
EXPECTED_BASE_BLOB="4c6d704fa24228284780bcb1dd7c52537b4c5b0d"
REVIEW_PROOF_ARTIFACT_NAME="asiv-v1-seed-freshness-review-proof"

def blob(path: Path)->str:
    b=path.read_bytes(); return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

if blob(BASE)!=EXPECTED_BASE_BLOB: raise RuntimeError("bound repository-global seed scanner byte drift")
spec=importlib.util.spec_from_file_location("asiv_bound_repo_seed_scan",BASE); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
mod.REVIEW_PROOF_ARTIFACT_NAME=REVIEW_PROOF_ARTIFACT_NAME

def load_candidates(path: Path)->set[int]:
    x=json.loads(path.read_text()); s=x.get("candidateSeeds") if isinstance(x,dict) else None
    if not isinstance(s,list) or len(s)!=24 or len(set(s))!=24: raise ValueError("exactly 24 unique ASIV candidate seeds required")
    return set(int(v) for v in s)

def evaluate(context: dict[str,Any], candidates:set[int], current_run_id:int|None, stable_sha:str, audit_mode:str, expected_branch:str, expected_head:str, fence:dict[str,Any], counts:dict[str,int])->dict[str,Any]:
    if len(candidates)!=24: raise ValueError("exactly 24 candidates required")
    filtered=mod._without_current_audit_self_metadata(context,current_run_id); canonical=mod.canonical_collision_context(context,current_run_id)
    matches=[r for r in filtered["branches"] if str(r.get("name") or "")==expected_branch]
    observed=str(((matches[0].get("commit") or {}).get("sha") or "")) if len(matches)==1 else None
    external=[]; seen=set()
    surfaces=(("branch-metadata",canonical["branches"]),("workflow-run-metadata",canonical["runs"]),("artifact-metadata",canonical["artifacts"]),("all-state-pull-request-metadata-and-body",canonical["pulls"]),("all-state-issue-metadata-and-body",canonical["issues"]),("repository-issue-comment",canonical["issueComments"]),("repository-pull-review-comment",canonical["pullReviewComments"]),("repository-commit-comment",canonical["commitComments"]),("issue60-comment",canonical["issue60Comments"]))
    for surface,rows in surfaces:
        for row in rows:
            rid=str(row.get("id") or row.get("number") or row.get("name") or row.get("url") or ""); key=(surface,rid)
            if key in seen: continue
            seen.add(key); hits=mod.seed_literals(row,candidates)
            if hits: external.append({"surface":surface,"id":rid,"seeds":hits})
    prior=[r for r in filtered["artifacts"] if str(r.get("name") or "")==REVIEW_PROOF_ARTIFACT_NAME]
    fence_sha=hashlib.sha256(json.dumps(fence,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
    return {"schemaVersion":1,"stageId":"asiv-v1-repository-global-seed-scan","auditMode":audit_mode,"candidateSeedCount":24,"auditedBranchName":expected_branch,"repositoryHeadExpected":expected_head,"auditedBranchHeadShaObserved":observed,"auditedBranchHeadMatchesRepositoryHead":observed==expected_head and len(matches)==1,"priorReviewProofArtifactCount":len(prior),"reviewProofIdentityFresh":len(prior)==0 if audit_mode=="review-freeze" else None,"repositoryGlobalCollisionCount":len(external),"collisions":external,"repositoryGlobalCollisionSurfaceScanPassed":not external,"repositoryGlobalDoubleEnumerationStable":True,"repositoryGlobalEnumerationPassCount":2,"repositoryGlobalStableContextSha256":stable_sha,"repositoryGlobalSnapshotFenceSha256":fence_sha,"repositoryGlobalPostFenceArrivalCounts":counts,"repositoryGlobalPostFenceCandidateSeedCollisionCount":0,"allStatePullRequestsInspected":True,"allStateIssuesInspected":True,"allRepositoryIssueCommentsInspected":True,"allRepositoryPullReviewCommentsInspected":True,"allRepositoryCommitCommentsInspected":True,"rawHistoricalArtifactBytesRequiredForThisGate":False,"authorizationTimeRecheckStillRequired":True}

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--repository",required=True); ap.add_argument("--issue-number",type=int,default=60); ap.add_argument("--candidate-seed-ledger",type=Path,required=True); ap.add_argument("--output",type=Path,required=True); ap.add_argument("--current-run-id",type=int); ap.add_argument("--audit-mode",choices=["review-freeze","authorization-recheck"],required=True); ap.add_argument("--expected-branch-name",required=True); ap.add_argument("--expected-repo-head",required=True); a=ap.parse_args()
    token=os.environ.get("GITHUB_TOKEN")
    if not token: raise SystemExit("GITHUB_TOKEN required")
    c=load_candidates(a.candidate_seed_ledger)
    context,stable_sha,fence,counts=mod.collect_stable(a.repository,a.issue_number,token,a.current_run_id,c,a.audit_mode)
    final=mod.final_expected_branch_head(a.repository,a.expected_branch_name,token)
    if final!=a.expected_repo_head: raise RuntimeError(f"audited branch moved: {final}")
    out=evaluate(context,c,a.current_run_id,stable_sha,a.audit_mode,a.expected_branch_name,a.expected_repo_head,fence,counts)
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    passed=out["repositoryGlobalCollisionSurfaceScanPassed"] and out["repositoryGlobalDoubleEnumerationStable"] and out["auditedBranchHeadMatchesRepositoryHead"]
    return 0 if passed else 2
if __name__=="__main__": raise SystemExit(main())
