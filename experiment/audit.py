#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path, PurePosixPath
import sys
from typing import Any
import zipfile

HERE = Path(__file__).resolve().parent
RUNNER_PATH = HERE / "runner.py"
STAGE_ID = "corrected-weak-twilight-alis-spectral-convergence-v1"
ALLOWED_COMPLETE_CLASSIFICATIONS = {
    "BOTH_CONVERGE_AND_AGREE",
    "PERSISTENT_METHOD_DISCREPANCY",
    "REFERENCE_UNDERCONVERGED",
    "ALIS_UNDERCONVERGED",
    "INCONCLUSIVE",
}


class AuditFailure(RuntimeError):
    pass


def load_runner():
    spec = importlib.util.spec_from_file_location("corrected_convergence_runner", RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise AuditFailure("could not load frozen runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json_bytes(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(payload.decode("utf-8"))
    except Exception as exc:
        raise AuditFailure(f"invalid {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise AuditFailure(f"{label} is not an object")
    return value


def unique_member(archive: zipfile.ZipFile, basename: str) -> str:
    matches = [name for name in archive.namelist() if not name.endswith("/") and PurePosixPath(name).name == basename]
    if len(matches) != 1:
        raise AuditFailure(f"expected exactly one {basename}, found {len(matches)}")
    return matches[0]


def assert_close_tree(actual: Any, expected: Any, path: str = "analysis") -> None:
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise AuditFailure(f"{path} keys differ")
        for key in expected:
            assert_close_tree(actual[key], expected[key], f"{path}.{key}")
        return
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise AuditFailure(f"{path} list length differs")
        for index, (actual_item, expected_item) in enumerate(zip(actual, expected)):
            assert_close_tree(actual_item, expected_item, f"{path}[{index}]")
        return
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        if not isinstance(actual, (int, float)) or isinstance(actual, bool):
            raise AuditFailure(f"{path} is not numeric")
        if not math.isfinite(float(actual)) or not math.isclose(float(actual), float(expected), rel_tol=1e-12, abs_tol=1e-15):
            raise AuditFailure(f"{path} differs: {actual!r} != {expected!r}")
        return
    if actual != expected:
        raise AuditFailure(f"{path} differs: {actual!r} != {expected!r}")


def validate_case_records(cases: Any, runner: Any, *, require_all: bool) -> None:
    if not isinstance(cases, list):
        raise AuditFailure("cases is not a list")
    expected = {(case["method"], case["seed"]): case["photonHistories"] for case in runner.cases_from_manifest(runner.load_json(runner.MANIFEST_PATH))}
    seen: set[tuple[str, int]] = set()
    for case in cases:
        if not isinstance(case, dict):
            raise AuditFailure("case record is not an object")
        key = (case.get("method"), case.get("seed"))
        if key not in expected or key in seen:
            raise AuditFailure(f"unexpected or duplicate case {key}")
        if case.get("photonHistories") != expected[key]:
            raise AuditFailure(f"photon count changed for {key}")
        values = case.get("selectedNodeRadiance")
        if not isinstance(values, list) or len(values) != len(runner.SELECTED_NODES):
            raise AuditFailure(f"selected-node vector invalid for {key}")
        if any(not isinstance(value, (int, float)) or not math.isfinite(float(value)) or value < 0 for value in values):
            raise AuditFailure(f"selected-node radiance invalid for {key}")
        if not any(value > 0 for value in values):
            raise AuditFailure(f"selected-node radiance all zero for {key}")
        seen.add(key)
    if require_all and seen != set(expected):
        raise AuditFailure("complete result does not contain the exact 12-case set")


def audit(zip_path: Path, metadata_path: Path, expected_run_id: int, expected_head_sha: str) -> dict[str, Any]:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    run = metadata.get("run", {})
    artifact = metadata.get("artifact", {})
    if run.get("id") != expected_run_id or run.get("head_sha") != expected_head_sha:
        raise AuditFailure("workflow run identity mismatch")
    if run.get("status") != "completed" or run.get("run_attempt") != 1:
        raise AuditFailure("workflow run was not completed attempt 1")
    if run.get("event") != "push" or run.get("head_branch") != "authorization/corrected-spectral-convergence-v1":
        raise AuditFailure("workflow run event or branch mismatch")
    digest = artifact.get("digest")
    if not isinstance(digest, str) or not digest.startswith("sha256:"):
        raise AuditFailure("artifact digest is missing or malformed")
    actual_digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    if actual_digest != digest.split(":", 1)[1]:
        raise AuditFailure("artifact ZIP digest mismatch")

    with zipfile.ZipFile(zip_path) as archive:
        analysis_name = unique_member(archive, "analysis-result.json")
        manifest_name = unique_member(archive, "run-manifest.json")
        analysis_bytes = archive.read(analysis_name)
        manifest_bytes = archive.read(manifest_name)
    result = load_json_bytes(analysis_bytes, "analysis-result.json")
    run_manifest = load_json_bytes(manifest_bytes, "run-manifest.json")
    runner = load_runner()
    runner.load_frozen()

    if result.get("stageId") != STAGE_ID or run_manifest.get("stageId") != STAGE_ID:
        raise AuditFailure("stage identity mismatch")
    if result.get("successDoesNotAuthorizeProduction") is not True or result.get("authorizationConsumed") is not True:
        raise AuditFailure("scientific or authorization boundary missing")
    if run_manifest.get("authorizationCommit") != expected_head_sha:
        raise AuditFailure("authorization commit mismatch")
    if run_manifest.get("resultSha256") != hashlib.sha256(analysis_bytes).hexdigest():
        raise AuditFailure("analysis-result hash differs from run manifest")
    for key in ("solverExecutionCount", "syntaxCheckCount", "attemptedConfiguredMcPhotonsSum", "completedConfiguredMcPhotonsSum", "classification"):
        if run_manifest.get(key) != result.get(key):
            raise AuditFailure(f"run manifest differs for {key}")

    classification = result.get("classification")
    if classification == "STRUCTURAL_OR_EXECUTION_FAILURE":
        if result.get("status") != "FAILED" or not isinstance(result.get("structuralFailure"), dict):
            raise AuditFailure("structural classification lacks failure record")
        if result.get("analysis") is not None:
            raise AuditFailure("structural failure must not contain scientific analysis")
        if len(result.get("cases", [])) >= 12:
            raise AuditFailure("structural failure unexpectedly contains 12 complete cases")
        validate_case_records(result.get("cases"), runner, require_all=False)
        if run.get("conclusion") not in ("failure", "cancelled", "timed_out"):
            raise AuditFailure("structural result has incompatible workflow conclusion")
        verified_scientific = False
    else:
        if classification not in ALLOWED_COMPLETE_CLASSIFICATIONS:
            raise AuditFailure("unknown complete classification")
        if result.get("status") != "COMPLETED" or result.get("structuralFailure") is not None:
            raise AuditFailure("complete classification has inconsistent status")
        if result.get("solverExecutionCount") != 12 or result.get("syntaxCheckCount") != 12:
            raise AuditFailure("complete result has wrong execution counts")
        if result.get("attemptedConfiguredMcPhotonsSum") != 1_200_000_000 or result.get("completedConfiguredMcPhotonsSum") != 1_200_000_000:
            raise AuditFailure("complete result has wrong photon accounting")
        if run.get("conclusion") != "success":
            raise AuditFailure("complete result requires successful workflow conclusion")
        cases = result.get("cases")
        validate_case_records(cases, runner, require_all=True)
        baseline = runner.load_json(runner.BASELINE_PATH)
        contract = runner.load_json(runner.CONTRACT_PATH)
        recomputed = runner.analyze(cases, baseline, contract)
        assert_close_tree(result.get("analysis"), recomputed)
        if recomputed.get("classification") != classification:
            raise AuditFailure("recomputed classification differs")
        verified_scientific = True

    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "verified": True,
        "scientificClassificationAvailable": verified_scientific,
        "classification": classification,
        "completeCaseCount": len(result.get("cases", [])),
        "solverExecutionCount": result.get("solverExecutionCount"),
        "syntaxCheckCount": result.get("syntaxCheckCount"),
        "workflowRun": run,
        "artifact": {
            "id": artifact.get("id"),
            "name": artifact.get("name"),
            "sizeInBytes": artifact.get("size_in_bytes"),
            "sha256": actual_digest,
        },
        "boundary": "read-only post-run audit; no dispatch, rerun, resume, or solver authorization",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", required=True)
    parser.add_argument("--metadata", required=True)
    parser.add_argument("--expected-run-id", required=True, type=int)
    parser.add_argument("--expected-head-sha", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        summary = audit(Path(args.zip), Path(args.metadata), args.expected_run_id, args.expected_head_sha)
    except (AuditFailure, OSError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        print(json.dumps({"verified": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    Path(args.output).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
