from __future__ import annotations

import hashlib
import importlib.util
import re
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "aerosol-optical-property-sensitivity-v1" / "execution-candidate" / "global_ordinal.py"
EXPECTED_BASE_BLOB = "27f8ac62bc8a520ab22b0215e847ef878db5aa5f"
STAGE = "aerosol-vertical-profile-sensitivity-v1"
AUTH_REVIEW_WORKFLOW = ".github/workflows/aerosol-vertical-profile-authorization-review.yml"
SCIENCE_WORKFLOW = ".github/workflows/avps-v1-science.yml"
ALLOCATION_MARKER = re.compile(
    r"^ORDINAL([0-9]+)_AVPS_V1_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED "
    r"commit=([0-9a-f]{40}) parent=([0-9a-f]{40}) pr=([1-9][0-9]*)$",
    re.I,
)


class GlobalOrdinalRefusal(RuntimeError):
    pass


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _base():
    if git_blob_sha1(BASE) != EXPECTED_BASE_BLOB:
        raise GlobalOrdinalRefusal("bound AOPS global-ordinal bytes changed")
    spec = importlib.util.spec_from_file_location("avps_bound_aops_global_ordinal", BASE)
    if spec is None or spec.loader is None:
        raise GlobalOrdinalRefusal("cannot load bound AOPS global ordinal")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def authoritative_global_ordinal_observations(
    payload: dict[str, Any], *, current_run_id: int | None = None
) -> list[dict[str, Any]]:
    return _base().authoritative_global_ordinal_observations(payload, current_run_id=current_run_id)


def _history_pattern(ordinal: int) -> re.Pattern[str]:
    return re.compile(
        rf"^history/{re.escape(STAGE)}-ordinal-{ordinal}-auth-review-failed-([1-9][0-9]*)$",
        re.I,
    )


def failed_authorization_history(payload: dict[str, Any], ordinal: int) -> dict[str, Any]:
    """Prove failed AVPS authorization review history is unallocated and undispatched.

    A preserved failed head is reusable only when there is exactly one closed,
    unmerged authorization PR and exactly one terminal attempt-1 authorization
    review failure for that head, with no allocation marker, dispatch branch,
    consumed marker, or AVPS science run.
    """
    auth_branch = f"authorization/{STAGE}-ordinal-{ordinal}"
    dispatch_branch = f"dispatch/{STAGE}-ordinal-{ordinal}"
    pattern = _history_pattern(ordinal)

    by_head: dict[str, list[str]] = {}
    for row in payload.get("branches", []):
        name = str(row.get("name") or "")
        if not pattern.fullmatch(name):
            continue
        head = str(((row.get("commit") or {}).get("sha") or "")).lower()
        if re.fullmatch(r"[0-9a-f]{40}", head) is None:
            raise GlobalOrdinalRefusal(f"ordinal {ordinal} failed-history ref has invalid head")
        by_head.setdefault(head, []).append(name)

    pr_numbers: set[int] = set()
    run_ids: set[int] = set()
    issue60 = [str(row.get("body") or "").strip() for row in payload.get("issue60Comments", [])]

    for head, names in by_head.items():
        if len(names) != 1:
            raise GlobalOrdinalRefusal(f"ordinal {ordinal} failed head has multiple history refs")

        prs = [
            p for p in payload.get("pulls", [])
            if str(((p.get("head") or {}).get("ref") or "")) == auth_branch
            and str(((p.get("head") or {}).get("sha") or "")).lower() == head
        ]
        if len(prs) != 1 or prs[0].get("state") != "closed" or prs[0].get("merged_at") is not None:
            raise GlobalOrdinalRefusal(
                f"ordinal {ordinal} failed head lacks exactly one closed/unmerged authorization PR"
            )
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
            raise GlobalOrdinalRefusal(
                f"ordinal {ordinal} failed head lacks exactly one authorization-review run"
            )
        review = reviews[0]
        if (
            int(review.get("run_attempt") or 0) != 1
            or review.get("status") != "completed"
            or review.get("conclusion") != "failure"
        ):
            raise GlobalOrdinalRefusal(
                f"ordinal {ordinal} preserved review is not a terminal attempt-1 failure"
            )
        run_id = int(review.get("id") or 0)
        if run_id <= 0:
            raise GlobalOrdinalRefusal(f"ordinal {ordinal} failed review run id invalid")

        for body in issue60:
            match = ALLOCATION_MARKER.fullmatch(body)
            if (
                match
                and int(match.group(1)) == ordinal
                and match.group(2).lower() == head
                and int(match.group(4)) == pr_number
            ):
                raise GlobalOrdinalRefusal(f"ordinal {ordinal} failed head already has allocation marker")
            if body.lower() == f"ORDINAL{ordinal}_AVPS_V1_DISPATCH_CONSUMED".lower():
                raise GlobalOrdinalRefusal(f"ordinal {ordinal} already has consumed marker")

        if any(str(row.get("name") or "") == dispatch_branch for row in payload.get("branches", [])):
            raise GlobalOrdinalRefusal(f"ordinal {ordinal} already has dispatch branch")
        if any(
            str(row.get("path") or "") == SCIENCE_WORKFLOW
            and str(row.get("head_sha") or "").lower() == head
            for row in payload.get("runs", [])
        ):
            raise GlobalOrdinalRefusal(f"ordinal {ordinal} failed head already has AVPS science run")

        pr_numbers.add(pr_number)
        run_ids.add(run_id)

    return {
        "heads": sorted(by_head),
        "prNumbers": sorted(pr_numbers),
        "reviewRunIds": sorted(run_ids),
    }


def derive_next_global_ordinal(
    payload: dict[str, Any], latest_consumed: int, *, current_run_id: int | None = None
):
    """Reuse only a rigorously preserved failed AVPS authorization ordinal.

    All ordinary global-ordinal logic remains delegated byte-for-byte to the
    already reviewed AOPS/R8 implementation. This wrapper handles only the AVPS
    failed-review state that the original preregistration explicitly refused
    pending a separately reviewed recovery extension.
    """
    base = _base()
    observations = base.authoritative_global_ordinal_observations(
        payload, current_run_id=current_run_id
    )
    if not observations:
        raise GlobalOrdinalRefusal("no authoritative global scientific ordinal observations")

    observed_max = max(int(row["ordinal"]) for row in observations)
    if observed_max < latest_consumed:
        raise GlobalOrdinalRefusal(
            f"global identity surface is behind latest consumed ordinal: consumed={latest_consumed} observed={observed_max}"
        )
    if observed_max == latest_consumed:
        return latest_consumed + 1, observations

    auth_branch = f"authorization/{STAGE}-ordinal-{observed_max}"
    auth_rows = [
        row for row in payload.get("branches", [])
        if str(row.get("name") or "") == auth_branch
    ]
    if len(auth_rows) > 1:
        raise GlobalOrdinalRefusal(f"ordinal {observed_max} has duplicate AVPS authorization branch observations")
    current_head = None if not auth_rows else str(((auth_rows[0].get("commit") or {}).get("sha") or "")).lower()
    failed = failed_authorization_history(payload, observed_max)
    failed_heads = {str(value).lower() for value in failed["heads"]}

    if failed_heads:
        if observed_max != latest_consumed + 1:
            raise GlobalOrdinalRefusal(
                "failed AVPS authorization reuse is allowed only for the immediate next unconsumed ordinal"
            )
        if current_head is not None and current_head not in failed_heads:
            raise GlobalOrdinalRefusal(
                "AVPS authorization branch moved away from preserved failed head before fresh preauthorization"
            )
        return observed_max, observations

    if current_head is not None:
        raise GlobalOrdinalRefusal(
            "active AVPS authorization branch exists without preserved failed-review proof"
        )

    return base.derive_next_global_ordinal(
        payload, latest_consumed, current_run_id=current_run_id
    )
