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
POSITIVE_TOKEN = re.compile(rf'\b{POSITIVE_WORDS}\b', re.I)
ORDINAL_TOKEN = re.compile(r'\bordinal\s*[-:#]?\s*14\b', re.I)
NEGATIVE = re.compile(r'\b(?:no|not|never|without|unallocated|unreserved|unauthorized|not-authorized|review-only|candidate-only|absent|missing|unpublished|refus(?:e|ed|es|ing|al)|prohibit(?:ed|s|ing|ion)?|forbid(?:den|s|ding)?|disallow(?:ed|s|ing)?|block(?:ed|s|ing)?|prevent(?:ed|s|ing)?)\b', re.I)
BOOLEAN_FALSE = re.compile(r'(?:[:=]\s*|\bis\s+)(?:\*\*)?false(?:\*\*)?\b', re.I)
# A reset starts a new semantic predicate/list item. Bare "and" only resets when
# it clearly starts a fresh predicate/subject; this preserves negation scope in
# phrases such as "do not allocate and reserve ordinal 14".
RESET = re.compile(
    r'(?:,\s*(?:and|but|then)\b|,\s*(?=ordinal\s*[-:#]?\s*14\b\s+(?:is|was|were|has|have|will|remains|became|becomes)\b)|'
    r'\b(?:but|however|yet|nevertheless|nonetheless|whereas|then|while)\b|'
    r'\band\s+(?=(?:we\b|i\b|is|was|were|has|have|will|now|no|not|never|without|ordinal\s*[-:#]?\s*14|authorization\b|allocation\b|reservation\b|dispatch\b)))',
    re.I,
)
POST_NEGATIVE = re.compile(
    r'\b(?:refus(?:e|ed|es|ing|al)|prohibit(?:ed|s|ing|ion)?|forbid(?:den|s|ding)?|'
    r'disallow(?:ed|s|ing)?|block(?:ed|s|ing)?|prevent(?:ed|s|ing)?|unauthorized|'
    r'unallocated|unreserved|review-only|candidate-only|absent|missing|unpublished)\b',
    re.I,
)
POST_DENIAL = re.compile(
    r'\b(?:(?:did|does|do|has|have|had|is|was|were|are)\s+not\s+(?:occur(?:red)?|happen(?:ed)?|exist(?:ed)?|grant(?:ed)?|make|made|create(?:d)?|authorize(?:d)?|allocate(?:d)?|reserve(?:d)?|consume(?:d)?)|'
    r'(?:not|never)\s+(?:occurred|happened|existed|granted|made|created|authorized|allocated|reserved|consumed)|'
    r'denied|rejected)\b',
    re.I,
)

class FreshnessRefusal(RuntimeError):
    pass

def require(cond: bool, msg: str) -> None:
    if not cond:
        raise FreshnessRefusal(msg)

def _reset_bounds(line: str, pos: int) -> tuple[int, int]:
    resets=list(RESET.finditer(line))
    before=[m.end() for m in resets if m.end() <= pos]
    after=[m.start() for m in resets if m.start() >= pos]
    return (max(before, default=0), min(after, default=len(line)))

def _token_is_negative(line: str, token: re.Match[str], ordinal: re.Match[str]) -> bool:
    seg_start, seg_end = _reset_bounds(line, token.start())
    # A candidate ordinal may be carried across a reset (e.g. "ordinal 14 was
    # not reserved, and authorization was granted"). Negation before that reset
    # must not suppress the fresh predicate.
    prefix=line[seg_start:token.start()]
    if NEGATIVE.search(prefix):
        return True

    lo=min(token.start(), ordinal.start())
    hi=max(token.end(), ordinal.end())
    between=line[lo:hi]
    if BOOLEAN_FALSE.search(between):
        return True

    # Status/refusal words immediately after the claim phrase negate it; cap the
    # tail so a later unrelated negative list item cannot suppress a real claim.
    tail=line[hi:min(seg_end, hi+48)]
    if BOOLEAN_FALSE.search(tail) or POST_NEGATIVE.search(tail) or POST_DENIAL.search(tail):
        return True
    return False

def positive_candidate_claims(text: str) -> list[str]:
    claims=[]
    for raw in re.split(r'[\n]+|(?<=[.;])\s+', text or ''):
        line=raw.strip()
        if not line:
            continue
        if MARKER_RE.fullmatch(line):
            claims.append(line)
            continue
        ordinals=list(ORDINAL_TOKEN.finditer(line))
        if not ordinals:
            continue
        tokens=list(POSITIVE_TOKEN.finditer(line))
        found=False
        for ordinal in ordinals:
            for token in tokens:
                # Keep the same bounded association as the old parser, but test
                # every positive token rather than only the first regex match.
                if max(ordinal.start(), token.start()) - min(ordinal.end(), token.end()) > 80:
                    continue
                if _token_is_negative(line, token, ordinal):
                    continue
                claims.append(line)
                found=True
                break
            if found:
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
