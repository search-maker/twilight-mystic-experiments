from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from authorization_guard import require, validate_enabled_document
from freshness import matching_marker, validate_dispatch

SHA40 = re.compile(r'^[0-9a-f]{40}$')


def evaluate(
    authorization: dict[str, Any],
    context: dict[str, Any],
    paths: dict[str, Path],
    post_dispatch: bool = False,
) -> dict[str, Any]:
    ordinal = authorization.get('scientificOrdinal')
    head = context.get('authorizationHead')
    parent = context.get('authorizationParent')
    pr = context.get('pr') or {}
    review = context.get('authorizationReview') or {}
    require(isinstance(head, str) and SHA40.fullmatch(head) is not None, 'authorization head invalid')
    require(isinstance(parent, str) and SHA40.fullmatch(parent) is not None, 'authorization parent invalid')
    require(context.get('liveMain') == parent, 'live main moved after authorization review')
    validate_enabled_document(authorization, parent, paths)
    require(pr.get('state') == 'open' and pr.get('draft') is True and pr.get('merged') is False, 'authorization PR no longer Draft/open/unmerged')
    require(pr.get('headBranch') == authorization['authorizationBranch'] and pr.get('headSha') == head, 'authorization PR head/branch drift')
    require(review.get('status') == 'AUTHORIZATION_REVIEW_PASS_ZERO_RUNTIME', 'zero-runtime authorization review pass missing')
    require(review.get('headSha') == head and review.get('prNumber') == pr.get('number'), 'authorization review identity drift')
    require(review.get('runAttempt') == 1 and review.get('conclusion') == 'success', 'exact successful attempt-1 authorization review required')
    require(review.get('scientificRuntimeSetupPerformed') is False and review.get('scientificExecutionPerformed') is False, 'authorization review was not zero-runtime')
    validate_dispatch(context.get('freshness') or {}, ordinal, head, post_dispatch=post_dispatch)
    markers = context.get('issue60Markers') or []
    good = [m for m in markers if matching_marker(m, ordinal, head, parent, int(pr.get('number') or 0))]
    require(len(good) == 1 and len(markers) == 1, 'exactly one exact Issue #60 authorization marker required')
    if post_dispatch:
        require(context.get('dispatchBranchHeadSha') == head, 'dispatch branch does not point to reviewed authorization head')
    return {
        'status': 'DISPATCH_TRANSITION_VALID' if post_dispatch else 'DISPATCH_ELIGIBLE_NOT_CREATED',
        'scientificOrdinal': ordinal,
        'executionKey': authorization['executionKey'],
        'authorizationHead': head,
        'authorizationParent': parent,
        'authorizationPr': pr['number'],
        'dispatchBranchMayPointTo': head,
        'scientificExecutionPerformed': False,
    }
