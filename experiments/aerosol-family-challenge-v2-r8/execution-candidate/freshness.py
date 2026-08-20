from __future__ import annotations

import re
from typing import Any

SHA40 = re.compile(r'^[0-9a-f]{40}$')


class FreshnessRefusal(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise FreshnessRefusal(message)


def authorization_branch(ordinal: int) -> str:
    return f'authorization/aerosol-family-challenge-v2-r8-ordinal-{ordinal}'


def dispatch_branch(ordinal: int) -> str:
    return f'dispatch/aerosol-family-challenge-v2-r8-ordinal-{ordinal}'


def execution_key(ordinal: int) -> str:
    return f'aerosol-family-challenge-v2-r8:numerical:{ordinal}'


def authorization_marker(ordinal: int, head: str, parent: str, pr_number: int) -> str:
    return (
        f'ORDINAL{ordinal}_AEROSOL_FAMILY_V2_R8_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED '
        f'commit={head} parent={parent} pr={pr_number}'
    )


def consumed_marker(ordinal: int) -> str:
    return f'ORDINAL{ordinal}_AEROSOL_FAMILY_V2_R8_DISPATCH_CONSUMED'


def marker_regex(ordinal: int) -> re.Pattern[str]:
    return re.compile(
        rf'^ORDINAL{ordinal}_AEROSOL_FAMILY_V2_R8_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED '
        rf'commit=([0-9a-f]{{40}}) parent=([0-9a-f]{{40}}) pr=([1-9][0-9]*)$',
        re.I,
    )


def _assertive_markdown_prose(text: str) -> str:
    out: list[str] = []
    in_fence = False
    fence: str | None = None
    for raw in (text or '').splitlines():
        stripped = raw.lstrip()
        if stripped.startswith('```') or stripped.startswith('~~~'):
            token = stripped[:3]
            if not in_fence:
                in_fence = True
                fence = token
            elif token == fence:
                in_fence = False
                fence = None
            continue
        if in_fence or stripped.startswith('>'):
            continue
        out.append(re.sub(r'`[^`\n]*`', ' ', raw))
    return '\n'.join(out)


def positive_candidate_claims(text: str, ordinal: int) -> list[str]:
    """Return assertive positive reservation/authorization/consumption claims for one ordinal.

    The parser intentionally ignores quoted/fenced examples, questions, future/planned language,
    and directly negated clauses so review prose cannot self-deadlock the candidate identity.
    """
    ord_pat = rf'ordinal\s*[-:#]?\s*{ordinal}'
    ordinal_token = re.compile(rf'\b{ord_pat}\b', re.I)
    marker = marker_regex(ordinal)
    action = r'(?:allocat(?:e|ed)|reserv(?:e|ed)|authoriz(?:e|ed)|consum(?:e|ed)|dispatch(?:ed)?)'
    noun = r'(?:allocation|reservation|authorization|consumption|dispatch)'
    factual = [
        re.compile(rf'\b(?:we|i|they|the\s+(?:system|repository|project|candidate))\b[^\n.;]{{0,48}}\b{action}\b[^\n.;]{{0,48}}\b{ord_pat}\b', re.I),
        re.compile(rf'\b{ord_pat}\b[^\n.;]{{0,64}}\b(?:is|was|were|has\s+been|had\s+been)\s+(?:now\s+|already\s+)?{action}\b', re.I),
        re.compile(rf'\b{noun}\b(?:\s+(?:of|for))?\s+{ord_pat}\b[^\n.;]{{0,40}}\b(?:occurred|completed|succeeded|exists|is\s+active|was\s+active|is\s+granted|was\s+granted)\b', re.I),
    ]
    nonfactual = re.compile(
        r'\b(?:no|not|never|without|pending|requested|request|proposed|proposal|planned|plan|'
        r'intended|intend|would|could|should|may|might|if|whether|before|after review|review-only|'
        r'candidate-only|denied|rejected|refused|revoked|rescinded|cancelled|canceled|'
        r'unauthorized|unallocated|unreserved)\b',
        re.I,
    )
    claims: list[str] = []
    prose = _assertive_markdown_prose(text)
    for raw in re.split(r'[\n]+|(?<=[.;])\s+', prose):
        line = raw.strip()
        if not line:
            continue
        if marker.fullmatch(line):
            claims.append(line)
            continue
        if not ordinal_token.search(line):
            continue
        if line.endswith('?') or re.match(r'^(?:did|do|does|is|are|was|were|has|have|had|can|could|would|should|will|may|might|must|who|what|when|where|why|how)\b', line, re.I):
            continue
        matched = False
        for pat in factual:
            match = pat.search(line)
            if not match:
                continue
            prefix = line[max(0, match.start() - 72):match.start()]
            span = line[match.start():match.end()]
            if nonfactual.search(prefix) or nonfactual.search(span):
                continue
            claims.append(line)
            matched = True
            break
        if matched:
            continue
    return claims


def matching_marker(text: str, ordinal: int, head: str, parent: str, pr_number: int) -> bool:
    m = marker_regex(ordinal).fullmatch((text or '').strip())
    return bool(
        m
        and m.group(1).lower() == head.lower()
        and m.group(2).lower() == parent.lower()
        and int(m.group(3)) == int(pr_number)
    )


def validate_common(ctx: dict[str, Any], ordinal: int, dispatch_must_be_absent: bool = True) -> None:
    require(isinstance(ordinal, int) and ordinal > 0, 'candidate scientific ordinal invalid')
    require(ctx.get('nextAvailableScientificOrdinal') == ordinal, 'candidate is not the fresh next global scientific ordinal')
    prior = ctx.get('latestPriorConsumedScientificOrdinal')
    require(isinstance(prior, int) and prior < ordinal, 'latest prior consumed scientific ordinal invalid')
    require(ctx.get('candidatePriorScientificRunCount') == 0, 'candidate ordinal already has scientific runs')
    require(ctx.get('candidateExecutionKeyPriorUseCount') == 0, 'candidate execution key already used')
    require(ctx.get('positiveCandidateClaimsExcludingCurrent') == 0, 'positive candidate ordinal claim already exists')
    require(ctx.get('allBranchesInspected') is True, 'all repository branches not inspected')
    require(ctx.get('allActionsRunsInspected') is True, 'all repository Actions runs not inspected')
    require(ctx.get('allActionsArtifactsInspected') is True, 'all repository Actions artifacts not inspected')
    require(ctx.get('allStatePullRequestsInspected') is True, 'all-state pull requests not inspected')
    require(ctx.get('allStateIssuesInspected') is True, 'all-state issues not inspected')
    require(ctx.get('allRepositoryIssueCommentsInspected') is True, 'repository-wide issue comments not inspected')
    require(ctx.get('allRepositoryPullReviewCommentsInspected') is True, 'repository-wide pull review comments not inspected')
    require(ctx.get('issue60AndCommentsInspected') is True, 'Issue #60 control surface not inspected')
    require(ctx.get('candidateCodePathsOnMainInspected') is True, 'candidate identity code paths on main not inspected')
    if dispatch_must_be_absent:
        require(ctx.get('dispatchBranchExists') is False, 'candidate dispatch branch already exists')


def validate_preauthorization(ctx: dict[str, Any], ordinal: int) -> None:
    validate_common(ctx, ordinal)
    require(ctx.get('currentConsumedMarkerCount') == 0, 'candidate consumed marker already exists')
    auth_exists = ctx.get('authorizationBranchExists') is True
    reusable = ctx.get('authorizationBranchReusableAfterFailedReview') is True
    require((not auth_exists) or reusable, 'authorization branch already exists and is not a proven unconsumed failed-review ref')
    require(ctx.get('activeAuthorizationPathOnMainExists') is False, 'active authorization path already exists on main')
    require(ctx.get('matchingAuthorizationMarkers') == 0, 'authorization marker already exists before review')


def validate_authorization_review(ctx: dict[str, Any], ordinal: int, head_sha: str) -> None:
    validate_common(ctx, ordinal)
    require(ctx.get('currentConsumedMarkerCount') == 0, 'candidate consumed marker exists during authorization review')
    require(ctx.get('authorizationBranchExists') is True, 'authorization branch missing during review')
    require(ctx.get('authorizationBranchHeadSha') == head_sha, 'authorization branch head differs from reviewed head')
    require(ctx.get('activeAuthorizationPathOnMainExists') is False, 'active authorization path already exists on main')
    require(ctx.get('matchingAuthorizationMarkers') == 0, 'authorization marker must not pre-exist review')


def validate_dispatch(ctx: dict[str, Any], ordinal: int, head_sha: str, post_dispatch: bool = False) -> None:
    validate_common(ctx, ordinal, dispatch_must_be_absent=not post_dispatch)
    require(ctx.get('authorizationBranchExists') is True, 'authorization branch missing before dispatch')
    require(ctx.get('authorizationBranchHeadSha') == head_sha, 'authorization branch head drift before dispatch')
    require(ctx.get('matchingAuthorizationMarkers') == 1, 'exactly one matching authorization marker required')
    if post_dispatch:
        require(ctx.get('dispatchBranchExists') is True, 'dispatch branch missing after dispatch transition')
        require(ctx.get('dispatchBranchHeadSha') == head_sha, 'dispatch branch head differs from reviewed authorization head')
        require(ctx.get('currentConsumedMarkerCount') == 1, 'exactly one current dispatch-consumed marker required after git push')
    else:
        require(ctx.get('currentConsumedMarkerCount') == 0, 'dispatch-consumed marker must not exist before git push')
