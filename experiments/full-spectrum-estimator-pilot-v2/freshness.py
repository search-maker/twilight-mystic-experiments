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
ORDINAL = r'ordinal\s*[-:#]?\s*14'
SUBJECT = r'(?:we|i|they|(?:the\s+)?(?:system|repository|project|candidate))'
BASE_VERB = r'(?:allocate|reserve|authorize|consume|dispatch)'
PAST_VERB = r'(?:allocated|reserved|authorized|consumed|dispatched)'
NOUN = r'(?:allocation|reservation|authorization|consumption|dispatch)'
ORDINAL_TOKEN = re.compile(rf'\b{ORDINAL}\b', re.I)

# Split contrastive/list clauses only for local prefix interpretation. The
# positive grammar itself remains explicit and finite below.
RESET = re.compile(
    r'(?:[.;]\s*|,\s*(?:and|but|then)\b|,\s*(?=ordinal\s*[-:#]?\s*14\b)|'
    r'\b(?:but|however|yet|nevertheless|nonetheless|whereas|then|while)\b|'
    r'\band\s+(?=(?:we\b|i\b|they\b|the\b|this\b|is\b|was\b|were\b|has\b|have\b|will\b|now\b|ordinal\s*[-:#]?\s*14\b|authorization\b|allocation\b|reservation\b|dispatch\b)))',
    re.I,
)
INTERROGATIVE = re.compile(
    rf'^\s*(?:(?:did|do|does)\s+{SUBJECT}\b|'
    rf'(?:is|are|was|were|has|have|had|can|could|would|should|will|may|might|must)\s+'
    rf'(?:{ORDINAL}|{SUBJECT}|{NOUN})\b|(?:who|what|when|where|why|how)\b)',
    re.I,
)
DIRECT_NEGATIVE = re.compile(
    r'\b(?:no|not|never|without|unauthorized|unallocated|unreserved|candidate-only|review-only)\b', re.I
)
NONFACTUAL_PREFIX = re.compile(
    r'\b(?:if|whether|when|before|hope(?:d|s)?|wish(?:ed|es)?|want(?:ed|s)?|'
    r'expect(?:ed|s)?|plan(?:ned|s)?|intend(?:ed|s)?|propose(?:d|s)?|'
    r'false\s+that|not\s+established\s+that|not\s+proven\s+that|not\s+confirmed\s+that)\b',
    re.I,
)

# Positive prose is intentionally a finite whitelist. This avoids treating a
# nearby past-tense token as evidence when it actually appears in a question,
# modal, expectation, negation, review note, or other non-factual frame.
FACT_PATTERNS = [
    re.compile(rf'\b{SUBJECT}\s+(?:(?:have|has|had)\s+)?(?:(?:now|already|hereby)\s+)?{PAST_VERB}\s+(?:the\s+)?{ORDINAL}\b', re.I),
    re.compile(rf'\b{SUBJECT}\s+(?:(?:now|hereby)\s+)?{BASE_VERB}\s+(?:the\s+)?{ORDINAL}\b', re.I),
    re.compile(rf'\b{SUBJECT}\s+(?:did|do|does)\s+{BASE_VERB}\s+(?:the\s+)?{ORDINAL}\b', re.I),
    re.compile(rf'\bnot\s+only\s+(?:did|do|does)\s+{SUBJECT}\s+{BASE_VERB}\s+(?:the\s+)?{ORDINAL}\b', re.I),
    re.compile(rf'\b{SUBJECT}\s+{PAST_VERB}\s+and\s+{PAST_VERB}\s+(?:the\s+)?{ORDINAL}\b', re.I),
    re.compile(rf'\b{SUBJECT}\s+{BASE_VERB}\s+and\s+{BASE_VERB}\s+(?:the\s+)?{ORDINAL}\b', re.I),
    re.compile(rf'\b{ORDINAL}\b\s+(?:is|was|were|has\s+been|had\s+been)\s+(?:(?:now|already)\s+)?{PAST_VERB}\b', re.I),
    re.compile(rf'\b{ORDINAL}\b[^\n.;]{{0,72}}\b(?:and|but|then)\s+(?:is|was|were|has\s+been|had\s+been)\s+(?:(?:now|already)\s+)?{PAST_VERB}\b', re.I),
]
NOUN_FACT_PATTERNS = [
    re.compile(rf'\b{NOUN}\b(?:\s+(?:of|for))?\s+{ORDINAL}\b[^\n.;]{{0,28}}\b(?:occurred|completed|succeeded|exists|is\s+active|was\s+active|is\s+granted|was\s+granted|has\s+been\s+granted|had\s+been\s+granted)\b', re.I),
    re.compile(rf'\b{ORDINAL}\b\s+{NOUN}\b[^\n.;]{{0,28}}\b(?:occurred|completed|succeeded|exists|is\s+active|was\s+active|is\s+granted|was\s+granted|has\s+been\s+granted|had\s+been\s+granted)\b', re.I),
    re.compile(rf'\b{NOUN}\b\s+(?:was|is|has\s+been|had\s+been)\s+(?:granted|completed|active)\b[^\n.;]{{0,36}}\b(?:for|of)\s+{ORDINAL}\b', re.I),
]
NOUN_MATCH_NEGATIVE = re.compile(
    r'\b(?:no|not|never|without|pending|requested|request|proposed|proposal|planned|plan|considered|discussion|review|'
    r'denied|rejected|refused|revoked|rescinded|cancelled|canceled|unauthorized|unallocated|unreserved)\b',
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

def _match_is_nonfactual(line: str, match: re.Match[str]) -> bool:
    seg_start, seg_end = _reset_bounds(line, match.start())
    clause=line[seg_start:seg_end]
    prefix=line[seg_start:match.start()]
    if clause.rstrip().endswith('?') or INTERROGATIVE.match(clause):
        return True
    if DIRECT_NEGATIVE.search(prefix) or NONFACTUAL_PREFIX.search(prefix):
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
        if not ORDINAL_TOKEN.search(line):
            continue
        found=False
        for pat in FACT_PATTERNS:
            for match in pat.finditer(line):
                if _match_is_nonfactual(line, match):
                    continue
                claims.append(line)
                found=True
                break
            if found:
                break
        if found:
            continue
        for pat in NOUN_FACT_PATTERNS:
            for match in pat.finditer(line):
                if _match_is_nonfactual(line, match) or NOUN_MATCH_NEGATIVE.search(match.group(0)):
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
    auth_exists=ctx.get('authorizationBranchExists') is True
    reusable=ctx.get('authorizationBranchReusableAfterFailedReview') is True
    require((not auth_exists) or reusable, 'candidate authorization branch already exists and is not an unconsumed failed-review ref')
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
