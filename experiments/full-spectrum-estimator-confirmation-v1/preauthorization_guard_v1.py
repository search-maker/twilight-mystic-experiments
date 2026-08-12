#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

ORDINAL_RE = re.compile(r"ordinal[-_]?([1-9][0-9]*)", re.I)


class PreauthorizationRefusal(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PreauthorizationRefusal(message)


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    require(isinstance(value, dict), f"expected JSON object: {path}")
    return value


def canonical_sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def verify_contract(contract: dict[str, Any]) -> None:
    supplied = contract.get("contractSha256")
    require(isinstance(supplied, str) and len(supplied) == 64, "contract self-hash missing")
    bare = {k: v for k, v in contract.items() if k != "contractSha256"}
    require(canonical_sha(bare) == supplied, "contract self-hash mismatch")
    require(contract.get("status") == "REVIEW_ONLY_NOT_ALLOCATED", "contract status drift")
    policy = contract.get("ordinalPolicy") or {}
    require(policy.get("authorizationOrdinalAllocated") is False, "ordinal already allocated in static contract")
    require(policy.get("staticContractMayNotAllocateOrdinal") is True, "static ordinal allocation boundary drift")
    boundary = contract.get("authorizationBoundary") or {}
    for key in (
        "scientificExecutionAuthorized",
        "authorizationCommitAuthorizedByThisContract",
        "dispatchAuthorizedByThisContract",
        "githubRerunAllowed",
        "retryAllowed",
        "resumeAllowed",
        "modelFittingAuthorized",
        "modelSelectionAuthorized",
        "holdoutValidationOpeningAuthorized",
        "tier2Authorized",
        "productionPromotionAuthorized",
    ):
        require(boundary.get(key) is False, f"authorization boundary drift: {key}")


def flatten_list_pages(path: Path) -> list[dict[str, Any]]:
    pages = json.loads(path.read_text())
    require(isinstance(pages, list), f"expected slurped page list: {path}")
    rows: list[dict[str, Any]] = []
    for page in pages:
        require(isinstance(page, list), f"expected list page: {path}")
        for row in page:
            require(isinstance(row, dict), f"expected row object: {path}")
            rows.append(row)
    return rows


def flatten_object_pages(path: Path, key: str) -> list[dict[str, Any]]:
    pages = json.loads(path.read_text())
    require(isinstance(pages, list), f"expected slurped page list: {path}")
    rows: list[dict[str, Any]] = []
    for page in pages:
        require(isinstance(page, dict), f"expected object page: {path}")
        values = page.get(key, [])
        require(isinstance(values, list), f"expected {key} list: {path}")
        for row in values:
            require(isinstance(row, dict), f"expected {key} row object: {path}")
            rows.append(row)
    return rows


def consumed_ordinals(branches: list[dict[str, Any]], runs: list[dict[str, Any]]) -> list[int]:
    out: list[int] = []
    for branch in branches:
        name = str(branch.get("name") or "")
        if not name.startswith("dispatch/"):
            continue
        match = ORDINAL_RE.search(name)
        if match:
            out.append(int(match.group(1)))
    for run in runs:
        if str(run.get("event") or "") != "push":
            continue
        head = str(run.get("head_branch") or "")
        if not head.startswith("dispatch/"):
            continue
        match = ORDINAL_RE.search(head)
        if match:
            out.append(int(match.group(1)))
    return out


def seed_set(rows: Any, label: str) -> set[int]:
    require(isinstance(rows, list), f"{label} missing")
    values: set[int] = set()
    for row in rows:
        require(isinstance(row, dict), f"{label} row malformed")
        seed = row.get("seed")
        require(isinstance(seed, int), f"{label} seed malformed")
        values.add(seed)
    return values


def scan_authorization_paths(repository_root: Path) -> list[str]:
    found: list[str] = []
    for base in (
        repository_root / "experiments/full-spectrum-estimator-confirmation-v1",
        repository_root / "review/full-spectrum-estimator-confirmation-v1",
    ):
        if not base.exists():
            continue
        for path in base.glob("authorization.ordinal*.json"):
            if path.is_file():
                found.append(str(path.relative_to(repository_root)))
    return sorted(found)


def build_report(
    *,
    contract: dict[str, Any],
    prereg: dict[str, Any],
    source_audit: dict[str, Any],
    pilot_seed_audit: dict[str, Any],
    branches: list[dict[str, Any]],
    runs: list[dict[str, Any]],
    artifacts: list[dict[str, Any]],
    repository_root: Path,
) -> dict[str, Any]:
    verify_contract(contract)
    require(prereg.get("preregistrationSha256") == contract["confirmationPreregistration"]["preregistrationSha256"], "confirmation preregistration identity drift")
    require((prereg.get("executionBoundary") or {}).get("authorizationOrdinalAllocated") is False, "preregistration already allocates ordinal")
    require((prereg.get("executionBoundary") or {}).get("scientificExecutionAuthorized") is False, "preregistration already authorizes science")

    cases = (prereg.get("caseDesign") or {}).get("cases")
    require(isinstance(cases, list), "confirmation cases missing")
    confirmation_seeds = seed_set(cases, "confirmation cases")
    expected_lo, expected_hi = contract["confirmationSeedRange"]
    expected_seeds = set(range(expected_lo, expected_hi + 1))
    require(len(cases) == contract["confirmationCaseCount"], "confirmation case count drift")
    require(len(confirmation_seeds) == contract["confirmationSeedCount"], "confirmation seeds not unique")
    require(confirmation_seeds == expected_seeds, "confirmation seed range drift")

    source_seeds = seed_set(source_audit.get("sourceCases"), "source seed audit")
    pilot_seeds = seed_set(pilot_seed_audit.get("candidateCases"), "pilot seed audit")
    require(not (confirmation_seeds & source_seeds), "confirmation seed collision with exact source ledger")
    require(not (confirmation_seeds & pilot_seeds), "confirmation seed collision with consumed pilot seeds")

    auth_prefix = contract["confirmationAuthorizationRefPrefix"]
    dispatch_prefix = contract["confirmationDispatchRefPrefix"]
    branch_names = [str(b.get("name") or "") for b in branches]
    conflicting_refs = sorted(name for name in branch_names if name.startswith(auth_prefix) or name.startswith(dispatch_prefix))
    require(not conflicting_refs, f"confirmation authorization/dispatch ref already exists: {conflicting_refs}")

    title_prefix = contract["confirmationScientificRunTitlePrefix"].lower()
    conflicting_runs: list[int] = []
    for run in runs:
        event = str(run.get("event") or "")
        head = str(run.get("head_branch") or "")
        name = str(run.get("name") or "")
        title = str(run.get("display_title") or "")
        path = str(run.get("path") or "")
        scientific = (
            head.startswith(dispatch_prefix)
            or title.lower().startswith(title_prefix)
            or name.lower().startswith(title_prefix)
            or ("full-spectrum-estimator-confirmation-v1" in path and "execution" in path.lower())
        )
        if event == "push" and scientific:
            conflicting_runs.append(int(run.get("id") or 0))
    require(not conflicting_runs, f"prior confirmation scientific push run exists: {conflicting_runs}")

    artifact_prefix = contract["confirmationCaseArtifactPrefix"]
    conflicting_artifacts: list[dict[str, Any]] = []
    for artifact in artifacts:
        name = str(artifact.get("name") or "")
        if name.startswith(artifact_prefix) or name.lower().startswith(title_prefix):
            conflicting_artifacts.append({"id": int(artifact.get("id") or 0), "name": name})
    require(not conflicting_artifacts, f"prior confirmation scientific artifact exists: {conflicting_artifacts}")

    auth_paths = scan_authorization_paths(repository_root)
    require(not auth_paths, f"confirmation authorization file already committed: {auth_paths}")

    ordinals = consumed_ordinals(branches, runs)
    require(ordinals, "no repository-global consumed scientific ordinal history found")
    latest = max(ordinals)
    require(latest >= int(contract["minimumKnownConsumedScientificOrdinal"]), "repository-global ordinal history incomplete or stale")
    next_available = latest + 1

    report: dict[str, Any] = {
        "schemaVersion": 1,
        "reportId": "public-tier1-full-spectrum-estimator-confirmation-v1-preauthorization-review-v1",
        "status": "PREAUTHORIZATION_SURFACE_CLEAN_NOT_ALLOCATED",
        "contractSha256": contract["contractSha256"],
        "confirmationCaseCount": len(cases),
        "confirmationSeedCount": len(confirmation_seeds),
        "confirmationSeedRange": [min(confirmation_seeds), max(confirmation_seeds)],
        "sourceSeedCount": len(source_seeds),
        "pilotSeedCount": len(pilot_seeds),
        "sourceSeedIntersection": [],
        "pilotSeedIntersection": [],
        "confirmationAuthorizationOrDispatchRefCount": 0,
        "confirmationScientificPushRunCount": 0,
        "confirmationScientificArtifactCount": 0,
        "committedConfirmationAuthorizationPathCount": 0,
        "latestConsumedScientificOrdinal": latest,
        "nextAvailableScientificOrdinalIfAllocatedLater": next_available,
        "authorizationOrdinalAllocated": False,
        "dispatchAuthorized": False,
        "scientificExecutionAuthorized": False,
        "repositoryGlobalBranchesInspected": True,
        "repositoryGlobalActionsRunsInspected": True,
        "repositoryGlobalActionsArtifactsInspected": True,
        "note": "The next ordinal is reported from fresh history only; this review does not allocate it.",
    }
    report["reportSha256"] = canonical_sha(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--source-seed-audit", type=Path, required=True)
    parser.add_argument("--pilot-seed-audit", type=Path, required=True)
    parser.add_argument("--branches-pages", type=Path, required=True)
    parser.add_argument("--runs-pages", type=Path, required=True)
    parser.add_argument("--artifacts-pages", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = build_report(
            contract=load_object(args.contract),
            prereg=load_object(args.preregistration),
            source_audit=load_object(args.source_seed_audit),
            pilot_seed_audit=load_object(args.pilot_seed_audit),
            branches=flatten_list_pages(args.branches_pages),
            runs=flatten_object_pages(args.runs_pages, "workflow_runs"),
            artifacts=flatten_object_pages(args.artifacts_pages, "artifacts"),
            repository_root=args.repository_root,
        )
    except Exception as exc:
        print(json.dumps({"status": "REFUSED", "reason": str(exc)}, sort_keys=True))
        return 2
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
