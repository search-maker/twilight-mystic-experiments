from __future__ import annotations

import re
from typing import Any

from freshness import positive_candidate_claims

ORDINAL_RE = re.compile(r"ordinal\s*[-_:#]?\s*([0-9]+)", re.I)
GENERIC_ALLOCATION_MARKER = re.compile(
    r"^ORDINAL([0-9]+)_.+_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED(?:\s|$)", re.I
)
GENERIC_CONSUMED_MARKER = re.compile(r"^ORDINAL([0-9]+)_.+_DISPATCH_CONSUMED$", re.I)
R8_ALLOCATION_MARKER = re.compile(
    r"^ORDINAL([0-9]+)_AEROSOL_FAMILY_V2_R8_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED "
    r"commit=([0-9a-f]{40}) parent=([0-9a-f]{40}) pr=([1-9][0-9]*)$",
    re.I,
)
R8_RETIRED_MARKER = re.compile(
    r"^ORDINAL([0-9]+)_AEROSOL_FAMILY_V2_R8_AUTHORIZATION_RETIRED_UNDISPATCHED$", re.I
)
PUBLISHER_WORKFLOW = '.github/workflows/aerosol-family-v2-r8-dispatch-publisher.yml'
AUTH_REVIEW_WORKFLOW = '.github/workflows/aerosol-family-v2-r8-authorization-review.yml'

def retired_authorization_marker(ordinal: int) -> str:
    return f'ORDINAL{ordinal}_AEROSOL_FAMILY_V2_R8_AUTHORIZATION_RETIRED_UNDISPATCHED'


class GlobalOrdinalRefusal(RuntimeError):
    pass


def _ordinals(text: str) -> set[int]:
    return {int(m.group(1)) for m in ORDINAL_RE.finditer(text or "")}


def _row_text(row: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("name", "path", "head_branch", "display_title", "title", "body"):
        value = row.get(key)
        if isinstance(value, str):
            parts.append(value)
    head = row.get("head") or {}
    if isinstance(head, dict) and isinstance(head.get("ref"), str):
        parts.append(head["ref"])
    return "\n".join(parts)


def authoritative_global_ordinal_observations(
    payload: dict[str, Any],
    *,
    current_run_id: int | None = None,
) -> list[dict[str, Any]]:
    """Return conservative repository-global scientific identity observations.

    Authorization/dispatch refs and runs are identity-bearing even before a dispatch is consumed.
    Authorization/dispatch artifacts are also treated conservatively as reservations.  For prose,
    reuse the established positive-claim parser so planned/questions/negations do not reserve an
    identity.  Exact generic allocation/consumption markers on Issue #60 are always authoritative.
    """
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str, int, str]] = set()

    def add(surface: str, identity: str, ordinal: int, reason: str) -> None:
        if ordinal <= 0:
            return
        key=(surface,identity,ordinal,reason)
        if key in seen:
            return
        seen.add(key)
        out.append({"surface":surface,"id":identity,"ordinal":ordinal,"reason":reason})

    for row in payload.get("branches", []):
        name=str(row.get("name") or "")
        if name.startswith(("authorization/", "dispatch/")):
            for ordinal in _ordinals(name):
                add("branch",name,ordinal,"identity-ref")

    for row in payload.get("runs", []):
        run_id=int(row.get("id") or 0)
        if current_run_id is not None and run_id == int(current_run_id):
            continue
        head=str(row.get("head_branch") or "")
        if head.startswith(("authorization/", "dispatch/")):
            for ordinal in _ordinals(head):
                add("workflow-run",str(run_id),ordinal,"identity-run-head")

    for row in payload.get("pulls", []):
        number=str(row.get("number") or row.get("id") or "")
        head=str(((row.get("head") or {}).get("ref") or ""))
        if head.startswith(("authorization/", "dispatch/")):
            for ordinal in _ordinals(head):
                add("pull-request",number,ordinal,"identity-pr-head")

    for row in payload.get("artifacts", []):
        name=str(row.get("name") or "")
        lowered=name.lower()
        if "ordinal" in lowered and ("authorization" in lowered or "dispatch" in lowered):
            for ordinal in _ordinals(name):
                add("artifact",str(row.get("id") or name),ordinal,"identity-evidence-artifact")

    for row in payload.get("issue60Comments", []):
        body=str(row.get("body") or "").strip()
        identity=str(row.get("id") or row.get("url") or "")
        for pattern,reason in (
            (GENERIC_ALLOCATION_MARKER,"exact-allocation-marker"),
            (GENERIC_CONSUMED_MARKER,"exact-consumed-marker"),
            (R8_RETIRED_MARKER,"exact-retired-undispatched-marker"),
        ):
            match=pattern.match(body)
            if match:
                add("issue60-comment",identity,int(match.group(1)),reason)

    prose_surfaces=(
        ("pull-request-prose",payload.get("pulls",[])),
        ("issue-prose",payload.get("issues",[])),
        ("issue-comment-prose",payload.get("issueComments",[])),
        ("pull-review-comment-prose",payload.get("pullReviewComments",[])),
        ("commit-comment-prose",payload.get("commitComments",[])),
        ("issue60-comment-prose",payload.get("issue60Comments",[])),
    )
    for surface,rows in prose_surfaces:
        for row in rows:
            text=_row_text(row)
            identity=str(row.get("id") or row.get("number") or row.get("url") or "")
            for ordinal in sorted(_ordinals(text)):
                if positive_candidate_claims(text,ordinal):
                    add(surface,identity,ordinal,"positive-allocation-reservation-consumption-claim")

    return sorted(out,key=lambda row:(int(row["ordinal"]),str(row["surface"]),str(row["id"]),str(row["reason"])))



def _retired_undispatched_proof(payload: dict[str, Any], ordinal: int) -> None:
    comments=[str(row.get('body') or '').strip() for row in payload.get('issue60Comments', [])]
    retired=retired_authorization_marker(ordinal)
    if sum(1 for body in comments if body.lower() == retired.lower()) != 1:
        raise GlobalOrdinalRefusal(f'ordinal {ordinal} lacks exactly one retired-undispatched marker')

    allocations=[]
    for body in comments:
        match=R8_ALLOCATION_MARKER.fullmatch(body)
        if match and int(match.group(1)) == ordinal:
            allocations.append(match)
    if len(allocations) != 1:
        raise GlobalOrdinalRefusal(f'ordinal {ordinal} lacks exactly one R8 allocation marker')
    allocation=allocations[0]
    auth_head=allocation.group(2).lower()
    pr_number=int(allocation.group(4))
    auth_branch=f'authorization/aerosol-family-challenge-v2-r8-ordinal-{ordinal}'
    dispatch_branch=f'dispatch/aerosol-family-challenge-v2-r8-ordinal-{ordinal}'
    publisher_branch=f'status/aerosol-family-v2-r8-dispatch-publisher-ordinal-{ordinal}'

    auth_rows=[row for row in payload.get('branches', []) if str(row.get('name') or '') == auth_branch]
    if len(auth_rows) != 1 or str(((auth_rows[0].get('commit') or {}).get('sha') or '')).lower() != auth_head:
        raise GlobalOrdinalRefusal(f'ordinal {ordinal} retired authorization branch/head evidence drift')
    if any(str(row.get('name') or '') == dispatch_branch for row in payload.get('branches', [])):
        raise GlobalOrdinalRefusal(f'ordinal {ordinal} has a dispatch branch and cannot be retired undispatched')

    matching_prs=[]
    for pr in payload.get('pulls', []):
        head=pr.get('head') or {}
        if int(pr.get('number') or 0) == pr_number and head.get('ref') == auth_branch and str(head.get('sha') or '').lower() == auth_head:
            matching_prs.append(pr)
    if len(matching_prs) != 1:
        raise GlobalOrdinalRefusal(f'ordinal {ordinal} retired allocation PR evidence missing/drifted')
    pr=matching_prs[0]
    if pr.get('state') != 'closed' or pr.get('merged_at') is not None:
        raise GlobalOrdinalRefusal(f'ordinal {ordinal} retired allocation PR must be closed and unmerged')

    auth_review_runs=[
        row for row in payload.get('runs', [])
        if str(row.get('head_branch') or '') == auth_branch
        and str(row.get('head_sha') or '').lower() == auth_head
        and str(row.get('path') or '') == AUTH_REVIEW_WORKFLOW
        and str(row.get('event') or '') == 'pull_request'
    ]
    if len(auth_review_runs) != 1:
        raise GlobalOrdinalRefusal(f'ordinal {ordinal} must have exactly one authorization-review run on the allocated head')
    auth_review=auth_review_runs[0]
    if (
        int(auth_review.get('run_attempt') or 0) != 1
        or auth_review.get('status') != 'completed'
        or auth_review.get('conclusion') != 'success'
    ):
        raise GlobalOrdinalRefusal(f'ordinal {ordinal} authorization review is not successful attempt-1 evidence')

    publisher_branches=[row for row in payload.get('branches', []) if str(row.get('name') or '') == publisher_branch]
    if len(publisher_branches) != 1:
        raise GlobalOrdinalRefusal(f'ordinal {ordinal} must preserve exactly one publisher request branch')
    publisher_head=str(((publisher_branches[0].get('commit') or {}).get('sha') or '')).lower()
    if not re.fullmatch(r'[0-9a-f]{40}', publisher_head):
        raise GlobalOrdinalRefusal(f'ordinal {ordinal} publisher request branch head is invalid')

    publisher_runs=[
        row for row in payload.get('runs', [])
        if str(row.get('head_branch') or '') == publisher_branch
        and str(row.get('path') or '') == PUBLISHER_WORKFLOW
        and str(row.get('event') or '') == 'push'
    ]
    if len(publisher_runs) != 1:
        raise GlobalOrdinalRefusal(f'ordinal {ordinal} must have exactly one publisher attempt to justify retirement')
    if str(publisher_runs[0].get('head_sha') or '').lower() != publisher_head:
        raise GlobalOrdinalRefusal(f'ordinal {ordinal} publisher run head differs from preserved request branch head')
    if any(
        int(row.get('run_attempt') or 0) != 1
        or row.get('status') != 'completed'
        or row.get('conclusion') != 'failure'
        for row in publisher_runs
    ):
        raise GlobalOrdinalRefusal(f'ordinal {ordinal} publisher history is not terminal attempt-1 failure only')
    if any(str(row.get('head_branch') or '') == dispatch_branch for row in payload.get('runs', [])):
        raise GlobalOrdinalRefusal(f'ordinal {ordinal} has a scientific dispatch-branch run and cannot be retired undispatched')
    consumed=f'ORDINAL{ordinal}_AEROSOL_FAMILY_V2_R8_DISPATCH_CONSUMED'
    if any(body.lower() == consumed.lower() for body in comments):
        raise GlobalOrdinalRefusal(f'ordinal {ordinal} has a dispatch-consumed marker and cannot be retired undispatched')


def derive_next_global_ordinal(
    payload: dict[str, Any],
    latest_consumed: int,
    *,
    current_run_id: int | None = None,
) -> tuple[int, list[dict[str, Any]]]:
    if not isinstance(latest_consumed,int) or latest_consumed <= 0:
        raise GlobalOrdinalRefusal("latest consumed global scientific ordinal is invalid")
    observations=authoritative_global_ordinal_observations(payload,current_run_id=current_run_id)
    if not observations:
        raise GlobalOrdinalRefusal("no authoritative global scientific ordinal observations")
    retired_ordinals=sorted({
        int(match.group(1))
        for row in payload.get("issue60Comments", [])
        if (match := R8_RETIRED_MARKER.fullmatch(str(row.get("body") or "").strip()))
    })
    for ordinal in retired_ordinals:
        _retired_undispatched_proof(payload, ordinal)
    observed_max=max(int(row["ordinal"]) for row in observations)
    if observed_max < latest_consumed:
        raise GlobalOrdinalRefusal(
            f"global identity surface is behind latest consumed ordinal: consumed={latest_consumed} observed={observed_max}"
        )
    for ordinal in range(latest_consumed + 1, observed_max + 1):
        _retired_undispatched_proof(payload, ordinal)
    return observed_max+1,observations
