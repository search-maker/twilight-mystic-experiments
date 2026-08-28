from __future__ import annotations

import hashlib
import importlib.util
import re
import sys
from pathlib import Path
from typing import Any

ORDINAL = 40
STAGE = "aerosol-vertical-profile-sensitivity-v1"
AUTH_BRANCH = f"authorization/{STAGE}-ordinal-{ORDINAL}"
DISPATCH_BRANCH = f"dispatch/{STAGE}-ordinal-{ORDINAL}"
AUTH_REVIEW_WORKFLOW = ".github/workflows/aerosol-vertical-profile-authorization-review.yml"
SCIENCE_WORKFLOW = ".github/workflows/avps-v1-science.yml"
FAILED_HISTORY_BRANCH = "history/aerosol-vertical-profile-sensitivity-v1-ordinal-40-auth-review-failed-1"
FAILED_HEAD = "67844e1dd2523963f2682f186387280dfb930760"
FAILED_PR = 561
FAILED_REVIEW_RUN = 33109014744
EXPECTED_LATEST_PRIOR_ORDINAL = 39

EXPECTED_SCIENCE_BLOBS = {
    ".github/workflows/avps-v1-science.yml": "55f48bbdf99aac58a96bd96f6735a4e56b8b466a",
    "experiments/aerosol-vertical-profile-sensitivity-v1/science_guard.py": "c774be7ea8655854bb85071a9fb260e21498beda",
    "experiments/aerosol-vertical-profile-sensitivity-v1/preauthorization_surface.py": "08a18315c9011effb24d860d917c7ff3dfd9df4e",
    "experiments/aerosol-vertical-profile-sensitivity-v1/global_ordinal.py": "67b4b3ac8aeadcc68b2191d7c0a0b4773d560ef0",
    "experiments/aerosol-vertical-profile-sensitivity-v1/freshness.py": "9ce9be8567bd810db5b5e1deea38d204bc21c17f",
    "experiments/aerosol-vertical-profile-sensitivity-v1/repository_global_seed_scan.py": "1cfb54e3ed96ff57f84739b4e4393544c49e2d32",
    "experiments/aerosol-vertical-profile-sensitivity-v1/execution-contract.review.json": "230874923004115ff21f218bb0ce4d2e038d3a98",
    "experiments/aerosol-optical-property-sensitivity-v1/execution-candidate/control_surface.py": "bc6d5a565b2b98f496793b35b226a334ba6b87f4",
}


class RecoverySurfaceRefusal(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RecoverySurfaceRefusal(message)


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RecoverySurfaceRefusal(f"cannot import recovery-bound source: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_frozen_science_bytes(science_root: Path) -> dict[str, str]:
    actual: dict[str, str] = {}
    for rel, expected in EXPECTED_SCIENCE_BLOBS.items():
        path = science_root / rel
        require(path.is_file(), f"missing frozen science/control source: {rel}")
        got = git_blob_sha1(path)
        require(got == expected, f"frozen science/control byte drift: {rel} expected={expected} observed={got}")
        actual[rel] = got
    return actual


def _head_sha(row: dict[str, Any]) -> str:
    return str(((row.get("head") or {}).get("sha") or "")).lower()


def _head_ref(row: dict[str, Any]) -> str:
    return str(((row.get("head") or {}).get("ref") or ""))


def recovery_failed_authorization_history(payload: dict[str, Any], ordinal: int) -> dict[str, Any]:
    """Re-prove the one preserved failed authorization without treating current consumption as its use.

    The original AVPS failed_authorization_history() was intentionally written for the
    *pre-allocation reuse* phase and therefore refuses any consumed marker or dispatch branch.
    Stage B is later in the same ordinal lifecycle: the exact successful authorization has now
    legitimately been allocated and consumed once. This recovery proof preserves every fact about
    the old failed head itself while deliberately leaving current successful-head consumption to
    the unchanged post-dispatch freshness validator.
    """
    require(ordinal == ORDINAL, f"Stage-B recovery is frozen to ordinal {ORDINAL}")

    matching_history = [
        row for row in payload.get("branches", [])
        if re.fullmatch(rf"history/{re.escape(STAGE)}-ordinal-{ordinal}-auth-review-failed-[1-9][0-9]*", str(row.get("name") or ""), re.I)
    ]
    require(len(matching_history) == 1, f"expected exactly one preserved failed-authorization history ref, got {len(matching_history)}")
    history = matching_history[0]
    require(str(history.get("name") or "") == FAILED_HISTORY_BRANCH, "failed-authorization history branch drift")
    history_head = str(((history.get("commit") or {}).get("sha") or "")).lower()
    require(history_head == FAILED_HEAD, "failed-authorization history head drift")

    prs = [
        row for row in payload.get("pulls", [])
        if _head_ref(row) == AUTH_BRANCH and _head_sha(row) == FAILED_HEAD
    ]
    require(len(prs) == 1, f"failed authorization head must have exactly one PR, got {len(prs)}")
    pr = prs[0]
    require(int(pr.get("number") or 0) == FAILED_PR, "failed authorization PR number drift")
    require(pr.get("state") == "closed" and pr.get("merged_at") is None, "failed authorization PR must remain closed/unmerged")

    runs = [
        row for row in payload.get("runs", [])
        if str(row.get("head_branch") or "") == AUTH_BRANCH
        and str(row.get("head_sha") or "").lower() == FAILED_HEAD
        and str(row.get("path") or "") == AUTH_REVIEW_WORKFLOW
        and str(row.get("event") or "") == "pull_request"
    ]
    require(len(runs) == 1, f"failed authorization head must have exactly one authorization-review run, got {len(runs)}")
    run = runs[0]
    require(int(run.get("id") or 0) == FAILED_REVIEW_RUN, "failed authorization review run id drift")
    require(int(run.get("run_attempt") or 0) == 1, "failed authorization review must remain attempt 1")
    require(run.get("status") == "completed" and run.get("conclusion") == "failure", "failed authorization review terminal state drift")

    issue60 = [str(row.get("body") or "").strip() for row in payload.get("issue60Comments", [])]
    failed_allocation = re.compile(
        rf"^ORDINAL{ordinal}_AVPS_V1_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED "
        rf"commit={FAILED_HEAD} parent=[0-9a-f]{{40}} pr={FAILED_PR}$",
        re.I,
    )
    require(not any(failed_allocation.fullmatch(body) for body in issue60), "preserved failed authorization head acquired an allocation marker")

    failed_head_science = [
        row for row in payload.get("runs", [])
        if str(row.get("path") or "") == SCIENCE_WORKFLOW
        and str(row.get("head_sha") or "").lower() == FAILED_HEAD
    ]
    require(not failed_head_science, "preserved failed authorization head has an AVPS science run")

    return {
        "heads": [FAILED_HEAD],
        "prNumbers": [FAILED_PR],
        "reviewRunIds": [FAILED_REVIEW_RUN],
        "recoverySemantics": "FAILED_HEAD_PROVED_UNUSED_WHILE_CURRENT_SUCCESSFUL_HEAD_CONSUMPTION_IS_VALIDATED_SEPARATELY",
    }


def build_post_consumption_surface(
    science_root: Path,
    payload: dict[str, Any],
    ordinal: int,
    head_sha: str,
    parent_sha: str,
    *,
    current_pr: int,
    current_run_id: int,
    candidate_seed_authorization_recheck_passed: bool,
) -> dict[str, Any]:
    """Build the original control surface with one narrow lifecycle-appropriate history substitution."""
    validate_frozen_science_bytes(science_root)
    require(ordinal == ORDINAL, f"Stage-B recovery is frozen to ordinal {ORDINAL}")
    require(re.fullmatch(r"[0-9a-f]{40}", head_sha or "") is not None, "authorization head SHA invalid")
    require(re.fullmatch(r"[0-9a-f]{40}", parent_sha or "") is not None, "authorization parent SHA invalid")
    require(isinstance(current_pr, int) and current_pr > 0, "authorization PR invalid")
    require(isinstance(current_run_id, int) and current_run_id > 0, "recovery workflow run id invalid")
    require(candidate_seed_authorization_recheck_passed is True, "live candidate seed recheck must pass before recovery surface")

    stage = science_root / "experiments" / STAGE
    preauthorization_surface = load_module(
        "avps_stage_b_bound_preauthorization_surface",
        stage / "preauthorization_surface.py",
    )
    freshness, control, _ = preauthorization_surface._modules()

    original_failed_history = control.failed_authorization_history
    control.failed_authorization_history = recovery_failed_authorization_history
    try:
        surface = control.build_surface(
            payload,
            ordinal,
            current_pr=current_pr,
            current_run_id=current_run_id,
            marker_head=head_sha,
            marker_parent=parent_sha,
            active_authorization_path_on_main_exists=False,
            candidate_code_paths_on_main_inspected=True,
            candidate_seed_authorization_recheck_passed=True,
            allow_authorization_branch=True,
            allow_dispatch_branch=True,
        )
    finally:
        control.failed_authorization_history = original_failed_history

    surface["nextAvailableScientificOrdinal"] = ordinal
    try:
        freshness.validate_dispatch(surface, ordinal, head_sha, post_dispatch=True)
    except Exception as exc:
        raise RecoverySurfaceRefusal(f"unchanged post-dispatch freshness validator refused recovered surface: {exc}") from exc

    require(surface.get("latestPriorConsumedScientificOrdinal") == EXPECTED_LATEST_PRIOR_ORDINAL, "latest prior global scientific ordinal drift")
    require(surface.get("candidatePriorScientificRunCount") == 0, "ordinal 40 already has a prior scientific run")
    require(surface.get("candidateExecutionKeyPriorUseCount") == 0, "ordinal 40 execution key already used")
    require(surface.get("positiveCandidateClaimsExcludingCurrent") == 0, "unexpected positive ordinal-40 identity claim exists")
    require(surface.get("authorizationBranchExists") is True, "authorization branch missing")
    require(surface.get("authorizationBranchHeadSha") == head_sha, "authorization branch head drift")
    require(surface.get("dispatchBranchExists") is True, "dispatch branch missing")
    require(surface.get("dispatchBranchHeadSha") == head_sha, "dispatch branch head drift")
    require(surface.get("matchingAuthorizationMarkers") == 1, "exactly one matching allocation marker required")
    require(surface.get("currentConsumedMarkerCount") == 1, "exactly one consumed marker required")
    require(surface.get("candidateSeedAuthorizationRecheckPassed") is True, "recovered surface lost live seed recheck")

    surface["postConsumptionRecovery"] = True
    surface["recoveryStage"] = "STAGE_B_SCIENCE_PREFLIGHT"
    surface["recoveryRepairScope"] = "FAILED_AUTHORIZATION_HISTORY_SUBPROOF_ONLY"
    surface["originalFreshnessValidateDispatchPassed"] = True
    return surface
