from __future__ import annotations

import re
from typing import Any

from freshness import positive_candidate_claims

ORDINAL_RE = re.compile(r"ordinal\s*[-_:#]?\s*([0-9]+)", re.I)
GENERIC_ALLOCATION_MARKER = re.compile(
    r"^ORDINAL([0-9]+)_.+_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED(?:\s|$)", re.I
)
GENERIC_CONSUMED_MARKER = re.compile(r"^ORDINAL([0-9]+)_.+_DISPATCH_CONSUMED$", re.I)


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
    observed_max=max(int(row["ordinal"]) for row in observations)
    if observed_max != latest_consumed:
        raise GlobalOrdinalRefusal(
            f"global identity surface is ahead of latest consumed ordinal: consumed={latest_consumed} observed={observed_max}"
        )
    return latest_consumed+1,observations
