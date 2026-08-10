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
CLAIM_VERBS = r'(?:allocate(?:d)?|reserve(?:d)?|authorize(?:d)?|consume(?:d)?|dispatch(?:ed)?)'
CLAIM_VERB = re.compile(rf'\b{CLAIM_VERBS}\b', re.I)
ORDINAL_TOKEN = re.compile(r'\bordinal\s*[-:#]?\s*14\b', re.I)
# Structural prose guard: only explicit factual predicates count. Bare nouns such
# as "authorization for ordinal 14" are intentionally non-positive unless paired
# with a factual completion/state predicate below.
RESET = re.compile(
    r'(?:[.;]\s*|,\s*(?:and|but|then)\b|,\s*(?=ordinal\s*[-:#]?\s*14\b)|\b(?:but|however|yet|nevertheless|nonetheless|whereas|then|while)\b|'
    r'\band\s+(?=(?:we\b|i\b|they\b|the\b|this\b|is\b|was\b|were\b|has\b|have\b|will\b|now\b|ordinal\s*[-:#]?\s*14\b|authorization\b|allocation\b|reservation\b|dispatch\b)))',
    re.I,
)
NEGATED_AUX = re.compile(
    r"\b(?:(?:do|does|did|has|have|had|is|are|was|were|will|would|should|could|can|may|might|must)\s+not|"
    r"cannot|can't|won't|wouldn't|shouldn't|couldn't|mustn't)\b",
    re.I,
)
MODAL_OR_NONFACTUAL = re.compile(
    r'\b(?:may|might|could|can|would|should|will|plan(?:s|ned)?\s+to|intend(?:s|ed)?\s+to|'
    r'propose(?:s|d)?\s+to|consider(?:s|ed|ing)?(?:\s+to)?|discuss(?:ed|es|ing)?|'
    r'request(?:ed|s|ing)?(?:\s+to)?|pending|await(?:s|ed|ing)?|yet\s+to|before|when|whether|if)\b',
    re.I,
)
META_FALSE = re.compile(
    r'\b(?:false\s+that|no\s+one\s+denied\s+that|nobody\s+denied\s+that|not\s+established\s+that|'
    r'not\s+proven\s+that|not\s+confirmed\s+that)\b',
    re.I,
)
DIRECT_NEGATIVE = re.compile(r'\b(?:no|not|never|without|unauthorized|unallocated|unreserved|candidate-only|review-only)\b', re.I)
BOOLEAN_FALSE = re.compile(r'(?:[:=]\s*|\bis\s+)(?:\*\*)?false(?:\*\*)?\b', re.I)
# Noun forms are admitted only when they have an explicit factual state/completion
# predicate. This keeps "authorization request/pending review" non-positive.
NOUN = r'(?:allocation|reservation|authorization|consumption|dispatch)'
NOUN_FACT_PATTERNS = [
    re.compile(rf'\b{NOUN}\b(?:\s+(?:of|for))?\s+ordinal\s*[-:#]?\s*14\b[^\n.;]{{0,36}}\b(?:occurred|completed|succeeded|exists|active|granted)\b', re.I),
    re.compile(rf'\bordinal\s*[-:#]?\s*14\b[^\n.;]{{0,36}}\b{NOUN}\b[^\n.;]{{0,28}}\b(?:occurred|completed|succeeded|exists|active|granted)\b', re.I),
    re.compile(rf'\b{NOUN}\b[^\n.;]{{0,28}}\b(?:was|is|has\s+been|had\s+been)\s+(?:granted|completed|active)\b[^\n.;]{{0,36}}\bordinal\s*[-:#]?\s*14\b', re.I),
]
NOUN_FACT_NEGATIVE = re.compile(
    r'\b(?:no|not|never|without|pending|requested|request|proposed|proposal|planned|plan|considered|discussion|review|'
    r'denied|rejected|refused|revoked|rescinded|cancelled|canceled|did\s+not\s+occur|does\s+not\s+exist|'
    r'has\s+not\s+occurred|was\s+not\s+granted|is\s+not\s+granted)\b',
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

def _boolean_false_for_claim(line: str, token: re.Match[str], ordinal: re.Match[str]) -> bool:
    lo=min(token.end(), ordinal.end())
    hi=max(token.start(), ordinal.start())
    if hi > lo and BOOLEAN_FALSE.search(line[lo:hi]):
        return True
    after=max(token.end(), ordinal.end())
    tail=line[after:after+56]
    stop=len(tail)
    for ch in (',',';'):
        i=tail.find(ch)
        if i >= 0: stop=min(stop,i)
    return bool(BOOLEAN_FALSE.search(tail[:stop]))

def _verb_is_factual(line: str, token: re.Match[str], ordinal: re.Match[str]) -> bool:
    seg_start, seg_end = _reset_bounds(line, token.start())
    clause=line[seg_start:seg_end]
    rel=token.start()-seg_start
    prefix=clause[max(0, rel-52):rel]
    # "not only ... authorize" is affirmative; remove only this idiom before
    # applying ordinary negation tests.
    cleaned_prefix=re.sub(r'\bnot\s+only\b', '', prefix, flags=re.I)
    if NEGATED_AUX.search(cleaned_prefix) or DIRECT_NEGATIVE.search(cleaned_prefix):
        return False
    if MODAL_OR_NONFACTUAL.search(cleaned_prefix) or META_FALSE.search(cleaned_prefix):
        return False
    # Bare infinitives are plans/instructions, not evidence of completed state.
    if re.search(r'\bto\s*$', cleaned_prefix, re.I):
        return False
    # Conditional/meta frames tied to the ordinal are non-factual even when the
    # verb itself looks affirmative.
    before_token=clause[:rel]
    if re.search(r'\b(?:if|whether|when|before)\b[^,;]{0,48}$', before_token, re.I):
        return False
    # Base-form verbs require an affirmative subject/auxiliary frame. Past forms
    # (allocated/authorized/...) are factual unless negated above.
    word=token.group(0).lower()
    if not word.endswith('ed'):
        if not re.search(r'\b(?:we|i|they|system|repository|project|candidate)\s+(?:(?:now|hereby)\s+)?$', cleaned_prefix, re.I) \
           and not re.search(r'\b(?:did|do|does)\s+(?:we|i|they|the\s+system|the\s+repository)\s+$', cleaned_prefix, re.I):
            return False
    if _boolean_false_for_claim(line, token, ordinal):
        return False
    # Keep association bounded to the explicit candidate ordinal.
    distance=max(token.start(), ordinal.start())-min(token.end(), ordinal.end())
    return distance <= 80

def _noun_fact_is_positive(line: str) -> bool:
    for pat in NOUN_FACT_PATTERNS:
        m=pat.search(line)
        if not m:
            continue
        seg_start, seg_end = _reset_bounds(line, m.start())
        clause=line[seg_start:seg_end]
        prefix=clause[:max(0, m.start()-seg_start)]
        segment=m.group(0)
        if DIRECT_NEGATIVE.search(prefix) or META_FALSE.search(prefix):
            continue
        if NOUN_FACT_NEGATIVE.search(segment):
            continue
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
        found=False
        for ordinal in ordinals:
            for token in CLAIM_VERB.finditer(line):
                if _verb_is_factual(line, token, ordinal):
                    claims.append(line)
                    found=True
                    break
            if found:
                break
        if not found and _noun_fact_is_positive(line):
            claims.append(line)
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
