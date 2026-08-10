#!/usr/bin/env python3
from __future__ import annotations
import re
from typing import Any

AUTH_BRANCH = 'authorization/full-spectrum-estimator-pilot-v2-ordinal14'
DISPATCH_BRANCH = 'dispatch/full-spectrum-estimator-pilot-v2-ordinal14'
EXECUTION_KEY = 'full-spectrum-estimator-pilot-v2:numerical:14'
TITLE = 'Full-spectrum estimator pilot v2 ordinal 14'
CANDIDATE_ORDINAL = 14
PRIOR_ORDINAL = 13
MARKER_RE = re.compile(
    r'^ORDINAL14_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED '
    r'commit=([0-9a-f]{40}) parent=([0-9a-f]{40}) pr=([1-9][0-9]*)$', re.I
)
POSITIVE_WORDS = r'(?:allocat(?:e|ed|ion)|reserv(?:e|ed|ation)|authoriz(?:e|ed|ation)|consum(?:e|ed|ption)|dispatch(?:ed)?)'
NEGATIVE = re.compile(r'\b(?:no|not|never|without|unallocated|unreserved|unauthorized|not-authorized|review-only|candidate-only|absent|missing|unpublished)\b', re.I)
ORDINAL_PATTERNS = [
    re.compile(rf'\b{POSITIVE_WORDS}\b[^\n.;]{{0,80}}\bordinal\s*[-:#]?\s*14\b', re.I),
    re.compile(rf'\bordinal\s*[-:#]?\s*14\b[^\n.;]{{0,80}}\b{POSITIVE_WORDS}\b', re.I),
]

class FreshnessRefusal(RuntimeError):
    pass

def require(cond: bool, msg: str) -> None:
    if not cond:
        raise FreshnessRefusal(msg)

def positive_candidate_claims(text: str) -> list[str]:
    claims=[]
    for raw in re.split(r'[\n]+|(?<=[.;])\s+', text or ''):
        line=raw.strip()
        if not line:
            continue
        if MARKER_RE.fullmatch(line):
            claims.append(line); continue
        if EXECUTION_KEY in line or TITLE.lower() in line.lower():
            # identity mention alone is not a positive allocation/authorization claim.
            pass
        for pat in ORDINAL_PATTERNS:
            m=pat.search(line)
            if not m:
                continue
            prefix=line[:m.start()]
            segment=line[max(0,m.start()-36):m.end()+12]
            if NEGATIVE.search(prefix[-36:]) or NEGATIVE.search(segment):
                continue
            claims.append(line)
            break
    return claims

def validate_common(ctx: dict[str, Any], dispatch_must_be_absent: bool = True) -> None:
    require(ctx.get('latestPriorConsumedScientificOrdinal') == PRIOR_ORDINAL, 'latest prior consumed scientific ordinal is not 13')
    require(ctx.get('candidatePriorScientificRunCount') == 0, 'candidate has prior scientific runs')
    if dispatch_must_be_absent:
        require(ctx.get('dispatchBranchExists') is False, 'candidate dispatch branch already exists')
    require(ctx.get('positiveCandidateClaimsExcludingCurrent') == 0, 'positive candidate ordinal claim already exists')
    require(ctx.get('allStatePullRequestsInspected') is True, 'all-state pull requests not inspected')
    require(ctx.get('allStateIssuesInspected') is True, 'all-state issues not inspected')
    require(ctx.get('allActionsRunsInspected') is True, 'all Actions runs not inspected')
    require(ctx.get('allBranchesInspected') is True, 'all branches not inspected')
    require(ctx.get('issue60AndCommentsInspected') is True, 'Issue #60 surface not inspected')
    require(ctx.get('candidateCodePathsOnMainInspected') is True, 'candidate code paths on main not inspected')

def validate_preauthorization(ctx: dict[str, Any]) -> None:
    validate_common(ctx)
    require(ctx.get('authorizationBranchExists') is False, 'candidate authorization branch already exists')
    require(ctx.get('activeAuthorizationPathOnMainExists') is False, 'active authorization file already exists on main')
    require(ctx.get('matchingAuthorizationMarkers') == 0, 'authorization marker already exists')
    require(ctx.get('nextAvailableScientificOrdinal') == CANDIDATE_ORDINAL, 'ordinal 14 is not next available')

def validate_authorization_review(ctx: dict[str, Any], head_sha: str) -> None:
    validate_common(ctx)
    require(ctx.get('authorizationBranchExists') is True, 'authorization branch missing during authorization review')
    require(ctx.get('authorizationBranchHeadSha') == head_sha, 'authorization branch head differs from reviewed head')
    require(ctx.get('activeAuthorizationPathOnMainExists') is False, 'active authorization file already exists on main')
    require(ctx.get('matchingAuthorizationMarkers') == 0, 'authorization marker must not pre-exist review')

def validate_dispatch(ctx: dict[str, Any], head_sha: str, post_dispatch: bool = False) -> None:
    validate_common(ctx, dispatch_must_be_absent=not post_dispatch)
    require(ctx.get('authorizationBranchExists') is True, 'authorization branch missing before dispatch')
    require(ctx.get('authorizationBranchHeadSha') == head_sha, 'authorization head drift before dispatch')
    require(ctx.get('matchingAuthorizationMarkers') == 1, 'exactly one matching authorization marker required')
    if post_dispatch:
        require(ctx.get('dispatchBranchExists') is True, 'dispatch branch missing after dispatch transition')
        require(ctx.get('dispatchBranchHeadSha') == head_sha, 'dispatch branch head differs from authorization head')

def matching_marker(text: str, head: str, parent: str, pr: int) -> bool:
    m=MARKER_RE.fullmatch((text or '').strip())
    return bool(m and m.group(1).lower()==head.lower() and m.group(2).lower()==parent.lower() and int(m.group(3))==int(pr))
