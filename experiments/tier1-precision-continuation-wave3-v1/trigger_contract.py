#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

DIRECTORY = "experiments/tier1-precision-continuation-wave3-v1"
SCIENTIFIC_WORKFLOW = ".github/workflows/tier1-precision-continuation-wave3-ordinal13-execution.yml"
AUTHORIZATION_PATH = "experiments/tier1-precision-continuation-wave3-v1/authorization.ordinal13.json"
TITLE = "Tier-1 precision continuation wave 3 ordinal 13"
KEY = "twilight-surrogate-tier-1-v1:numerical:13"
TRIGGER_BRANCH = "dispatch/tier1-precision-continuation-wave3-ordinal13-v1"


class Refusal(RuntimeError):
    pass


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise Refusal(f"module unavailable: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_rows(path: Path) -> list[dict[str, Any]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Refusal(f"invalid scientific run history: {path}") from exc
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise Refusal("scientific run history must be an array of objects")
    return value


def validate_workflow(root: Path) -> None:
    path = root / SCIENTIFIC_WORKFLOW
    text = path.read_text(encoding="utf-8")
    required = (
        "run-name: " + TITLE,
        "push:",
        TRIGGER_BRANCH,
        "terminal_trigger_execution.py manifest",
        "trigger_case_executor.py",
        "--allow-" + "execution",
        "githubRerunAllowed",
        "GITHUB_RUN_ATTEMPT",
        "authorization.ordinal13.json",
    )
    missing = [token for token in required if token not in text]
    if missing:
        raise Refusal(f"scientific push transport incomplete: {missing}")
    forbidden = (
        "workflow_" + "dispatch:",
        "pull_request:",
        "schedule:",
        "repository_dispatch:",
    )
    found = [token for token in forbidden if token in text]
    if found:
        raise Refusal(f"scientific workflow exposed an alternate trigger: {found}")
    if (root / AUTHORIZATION_PATH).exists():
        raise Refusal("ordinal-13 authorization already exists in review package")


def dry_contract(
    root: Path,
    source_analysis: Path,
    scientific_runs: Path,
    output_dir: Path,
) -> dict[str, Any]:
    root = root.resolve()
    validate_workflow(root)
    directory = root / DIRECTORY
    guard = load(directory / "terminal_trigger_execution.py", "wave3_trigger_contract_guard")
    package = load(directory / "package.py", "wave3_trigger_contract_package")
    binding = load(directory / "terminal_binding.py", "wave3_trigger_contract_binding")
    binding_report = binding.validate_path(source_analysis)
    source_value = package.load_json(source_analysis)
    prereg = package.build_preregistration(source_value, source_analysis, root)
    expected_ids = list(binding.ACTIVE_GEOMETRY_IDS)
    if (
        prereg.get("geometryIds") != expected_ids
        or prereg.get("geometryCount") != 15
        or prereg.get("caseCount") != 30
        or prereg.get("blocks") != [7, 8]
        or len(prereg.get("cases", [])) != 30
    ):
        raise Refusal("real terminal source did not generate exact 30-case scope")
    if (
        len({case.get("caseId") for case in prereg["cases"]}) != 30
        or len({case.get("seed") for case in prereg["cases"]}) != 30
        or prereg.get("seedProof", {}).get("consumedOverlap") != []
    ):
        raise Refusal("real terminal source seed or case proof changed")

    rows = load_rows(scientific_runs)
    duplicates = [row for row in rows if row.get("display_title") == TITLE]
    if duplicates:
        raise Refusal(
            f"ordinal-13 title already allocated: {[row.get('id') for row in duplicates]}"
        )

    head = "1" * 40
    authorization_ref = "2" * 40
    context = {
        "eventName": "push",
        "triggerBranch": TRIGGER_BRANCH,
        "runAttempt": 1,
        "displayTitle": TITLE,
        "authorizationOrdinal": 13,
        "executionKey": KEY,
        "headBranch": "main",
        "headSha": head,
        "authorizationRef": authorization_ref,
        "runId": 717171,
    }
    authorization = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave3-authorization-v1",
        "status": "AUTHORIZED_PENDING_SEPARATE_DISPATCH",
        "authorizationOrdinal": 13,
        "executionKey": KEY,
        "runTitle": TITLE,
        "runAttempt": 1,
        "wave": 3,
        "blocks": [7, 8],
        "geometryCount": 15,
        "caseCount": 30,
        "enabled": True,
        "solverExecutionAuthorized": True,
        "automaticDispatch": False,
        "dispatch": False,
        "workflowDispatchEnabled": False,
        "triggerBranch": TRIGGER_BRANCH,
        "triggerEvent": "push",
        "githubRerunAllowed": False,
        "surrogateTrainingAuthorized": False,
        "internalHoldoutOpeningAuthorized": False,
        "tier2Authorized": False,
        "productionPromotionAuthorized": False,
        "sourceRunId": binding.SOURCE_RUN_ID,
        "sourceRunAttempt": binding.SOURCE_RUN_ATTEMPT,
        "sourceMainSha": "0ef7e011e00a4c4badcafb2f6ca06256026b1746",
        "sourceAuthorizationRef": binding.SOURCE_HEAD_SHA,
        "sourceExecutionKey": "twilight-surrogate-tier-1-v1:numerical:12",
        "sourceArtifactId": binding.SOURCE_ARTIFACT_ID,
        "sourceArtifactDigest": binding.SOURCE_ARTIFACT_DIGEST,
        "preregistrationSha256": prereg["preregistrationSha256"],
        "sourceAnalysisRawSha256": prereg["sourceAnalysisRawSha256"],
        "sourceAnalysisSha256": prereg["sourceAnalysisSha256"],
        "executionSourceHeadSha": head,
    }
    metadata = {
        "authorizationCommit": authorization_ref,
        "authorizationParent": head,
        "changedFiles": [AUTHORIZATION_PATH],
        "parentCount": 1,
    }
    runtime = {
        "uvspecSha256": "3" * 64,
        "uvspecHelpSha256": "4" * 64,
        "libRadtranDataTreeSha256": "5" * 64,
        "atmosphereSha256": "6" * 64,
        "runtimeLockRawSha256": "7" * 64,
    }
    rows.append(
        {
            "id": context["runId"],
            "display_title": TITLE,
            "status": "in_progress",
            "conclusion": None,
            "event": "push",
            "run_attempt": 1,
            "head_sha": authorization_ref,
            "head_branch": TRIGGER_BRANCH,
        }
    )
    manifest = guard.build_manifest(
        root, authorization, context, rows, runtime, metadata, source_analysis
    )
    guard.validate_terminal_manifest(manifest, binding_report, root)
    if manifest.get("geometryIds") != expected_ids or manifest.get("caseCount") != 30:
        raise Refusal("dry manifest terminal scope changed")

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "terminal-source-binding.json").write_text(
        json.dumps(binding_report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "dry-authorization.json").write_text(
        json.dumps(authorization, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "dry-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave3-trigger-v1-contract-review",
        "status": "EXACT_TERMINAL_BOUND_ORDINAL13_PUSH_TRANSPORT_CONTRACT_PASSED",
        "sourceArtifactId": binding.SOURCE_ARTIFACT_ID,
        "sourceArtifactDigest": binding.SOURCE_ARTIFACT_DIGEST,
        "sourceAnalysisRawSha256": binding.SOURCE_ANALYSIS_RAW_SHA256,
        "sourceAnalysisSha256": binding.SOURCE_ANALYSIS_SHA256,
        "geometryIds": expected_ids,
        "geometryCount": 15,
        "caseCount": 30,
        "blocks": [7, 8],
        "wave3SeedsSha256": manifest["seedProof"]["wave3SeedsSha256"],
        "candidateOrdinal": 13,
        "candidateExecutionKey": KEY,
        "candidateRunTitle": TITLE,
        "candidateTriggerBranch": TRIGGER_BRANCH,
        "authorizationAllocated": False,
        "dispatchBranchCreated": False,
        "scientificSolverExecutions": 0,
        "githubRerunAllowed": False,
        "surrogateTrainingAuthorized": False,
        "internalHoldoutOpened": False,
        "tier2Authorized": False,
        "productionPromotionAuthorized": False,
    }
    base = guard._modules(root)[1]._base(root)
    report["reportSha256"] = base.canonical_sha256(report)
    (output_dir / "contract-review.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--source-analysis", type=Path, required=True)
    parser.add_argument("--scientific-runs", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = dry_contract(
            args.root, args.source_analysis, args.scientific_runs, args.output_dir
        )
    except Exception as exc:
        print(json.dumps({"status": "REFUSED", "reason": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
