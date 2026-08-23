from __future__ import annotations

import hashlib
import importlib.util
import re
import sys
from pathlib import Path
from typing import Any


R8_DIR = Path(__file__).resolve().parents[2] / "aerosol-family-challenge-v2-r8" / "execution-candidate"
R8_FRESHNESS_BLOB = "732f803b5261e7986582dd7e0d69a66f70432b1e"
R8_PREAUTH_ORDINAL_BLOB = "7ca8efd17ae9e7ec2baa32fe935e5173ca6d173f"
STAGE = "aerosol-optical-property-sensitivity-v1"
AUTH_REVIEW_WORKFLOW = ".github/workflows/aops-v1-authorization-review.yml"
EXECUTION_WORKFLOW = ".github/workflows/aops-v1-execution.yml"
AOPS_ALLOCATION_MARKER = re.compile(
    r"^ORDINAL([0-9]+)_AOPS_V1_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED(?:\s|$)", re.I
)


class GlobalOrdinalRefusal(RuntimeError):
    pass


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GlobalOrdinalRefusal(f"cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _bound_r8_modules():
    freshness_path = R8_DIR / "freshness.py"
    ordinal_path = R8_DIR / "preauthorization_ordinal.py"
    if git_blob_sha1(freshness_path) != R8_FRESHNESS_BLOB:
        raise GlobalOrdinalRefusal("bound R8 freshness bytes changed")
    if git_blob_sha1(ordinal_path) != R8_PREAUTH_ORDINAL_BLOB:
        raise GlobalOrdinalRefusal("bound R8 preauthorization ordinal bytes changed")
    r8_freshness = load_module("aops_bound_r8_freshness", freshness_path)
    previous = sys.modules.get("freshness")
    sys.modules["freshness"] = r8_freshness
    try:
        r8_ordinal = load_module("aops_bound_r8_global_ordinal", ordinal_path)
    finally:
        if previous is None:
            sys.modules.pop("freshness", None)
        else:
            sys.modules["freshness"] = previous
    return r8_freshness, r8_ordinal


def authoritative_global_ordinal_observations(
    payload: dict[str, Any], *, current_run_id: int | None = None
) -> list[dict[str, Any]]:
    _, mod = _bound_r8_modules()
    return mod.authoritative_global_ordinal_observations(payload, current_run_id=current_run_id)


def _history_pattern(ordinal: int) -> re.Pattern[str]:
    return re.compile(
        rf"^history/{STAGE}-ordinal-{ordinal}-auth-review-failed-([1-9][0-9]*)$", re.I
    )


def failed_authorization_history(payload: dict[str, Any], ordinal: int) -> dict[str, Any]:
    """Prove an AOPS authorization-review failure is historical, unallocated and undispatched."""
    auth_branch = f"authorization/{STAGE}-ordinal-{ordinal}"
    dispatch_branch = f"dispatch/{STAGE}-ordinal-{ordinal}"
    pattern = _history_pattern(ordinal)
    by_head: dict[str, list[str]] = {}
    for row in payload.get("branches", []):
        name = str(row.get("name") or "")
        if not pattern.fullmatch(name):
            continue
        head = str(((row.get("commit") or {}).get("sha") or "")).lower()
        if not re.fullmatch(r"[0-9a-f]{40}", head):
            raise GlobalOrdinalRefusal(f"ordinal {ordinal} failed-history ref has invalid head")
        by_head.setdefault(head, []).append(name)

    pr_numbers: set[int] = set()
    run_ids: set[int] = set()
    for head, names in by_head.items():
        if len(names) != 1:
            raise GlobalOrdinalRefusal(f"ordinal {ordinal} failed head has multiple history refs")
        prs = [
            p for p in payload.get("pulls", [])
            if str(((p.get("head") or {}).get("ref") or "")) == auth_branch
            and str(((p.get("head") or {}).get("sha") or "")).lower() == head
        ]
        if len(prs) != 1 or prs[0].get("state") != "closed" or prs[0].get("merged_at") is not None:
            raise GlobalOrdinalRefusal(f"ordinal {ordinal} failed head lacks one closed/unmerged authorization PR")
        pr_number = int(prs[0].get("number") or 0)
        if pr_number <= 0:
            raise GlobalOrdinalRefusal(f"ordinal {ordinal} failed PR number invalid")
        reviews = [
            r for r in payload.get("runs", [])
            if str(r.get("head_branch") or "") == auth_branch
            and str(r.get("head_sha") or "").lower() == head
            and str(r.get("path") or "") == AUTH_REVIEW_WORKFLOW
            and str(r.get("event") or "") == "pull_request"
        ]
        if len(reviews) != 1:
            raise GlobalOrdinalRefusal(f"ordinal {ordinal} failed head lacks one authorization-review run")
        review = reviews[0]
        if int(review.get("run_attempt") or 0) != 1 or review.get("status") != "completed" or review.get("conclusion") != "failure":
            raise GlobalOrdinalRefusal(f"ordinal {ordinal} preserved review is not terminal attempt-1 failure")
        run_id = int(review.get("id") or 0)
        if run_id <= 0:
            raise GlobalOrdinalRefusal(f"ordinal {ordinal} failed review run id invalid")
        for row in payload.get("issue60Comments", []):
            body = str(row.get("body") or "").strip()
            m = AOPS_ALLOCATION_MARKER.match(body)
            if m and int(m.group(1)) == ordinal:
                raise GlobalOrdinalRefusal(f"ordinal {ordinal} failed head already has allocation marker")
            if body.lower() == f"ORDINAL{ordinal}_AOPS_V1_DISPATCH_CONSUMED".lower():
                raise GlobalOrdinalRefusal(f"ordinal {ordinal} failed head already has consumed marker")
        if any(str(b.get("name") or "") == dispatch_branch for b in payload.get("branches", [])):
            raise GlobalOrdinalRefusal(f"ordinal {ordinal} failed head already has dispatch branch")
        if any(
            str(r.get("path") or "") == EXECUTION_WORKFLOW and str(r.get("head_sha") or "").lower() == head
            for r in payload.get("runs", [])
        ):
            raise GlobalOrdinalRefusal(f"ordinal {ordinal} failed head already has scientific execution run")
        pr_numbers.add(pr_number)
        run_ids.add(run_id)

    return {"heads": sorted(by_head), "prNumbers": sorted(pr_numbers), "reviewRunIds": sorted(run_ids)}


def derive_next_global_ordinal(
    payload: dict[str, Any], latest_consumed: int, *, current_run_id: int | None = None
):
    _, mod = _bound_r8_modules()
    observations = mod.authoritative_global_ordinal_observations(payload, current_run_id=current_run_id)
    if not observations:
        raise GlobalOrdinalRefusal("no authoritative global scientific ordinal observations")
    observed_max = max(int(row["ordinal"]) for row in observations)
    if observed_max == latest_consumed + 1:
        failed = failed_authorization_history(payload, observed_max)
        auth_branch = f"authorization/{STAGE}-ordinal-{observed_max}"
        auth_rows = [r for r in payload.get("branches", []) if str(r.get("name") or "") == auth_branch]
        if len(auth_rows) > 1:
            raise GlobalOrdinalRefusal(f"ordinal {observed_max} has duplicate authorization branch observations")
        current_head = None if not auth_rows else str(((auth_rows[0].get("commit") or {}).get("sha") or "")).lower()
        if failed["heads"] and current_head in set(failed["heads"]):
            return observed_max, observations
    return mod.derive_next_global_ordinal(payload, latest_consumed, current_run_id=current_run_id)
