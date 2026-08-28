from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

STAGE = "aerosol-vertical-profile-sensitivity-v1"
AUTHORIZATION_PARENT = "99ade7798627e67921139697ba1a004fa8a304bb"
AUTHORIZATION_HEAD = "338ee82c8e088e929f45782b1f7ac1c3aaaaa533"
SCIENTIFIC_ORDINAL = 40
RECOVERY_RUN_ID = 33139545997
RECOVERY_RUN_HEAD = "6d0e0e0f1dd1deabaf8bb155ee7e323c5ba8673d"
FAILED_RUN_ID = 33137514692
GATE0_METADATA_ARTIFACT_ID = 9676069031
GATE0_METADATA_ARTIFACT_DIGEST = "sha256:70dedcd16209dea74a9ed67a1dc7377c123f1a62fd18741b1e15692702011fc8"
GATE0_METADATA_INNER_SHA256 = "323f458b43a031c50f2c2f74971594801608a5cdf437839c8760b42c19bdb92e"
RECOVERY_EXECUTOR_GIT_BLOB_SHA1 = "3580f7eff61ab06d0b4a7041f7907d871d961b5b"
ORIGINAL_EXECUTOR_GIT_BLOB_SHA1 = "68eb7f6916bae204e60f6a378eae25f9c2bff184"
AGGREGATOR_GIT_BLOB_SHA1 = "1f36fc95347b84623db9b77005907929389dc7e8"
PROTOCOL_REVIEW_PR = 579
PROTOCOL_REVIEW_HEAD = "5e191b1afbdb637e6534c856548af1d79138d6f1"
CASE_PREFIX = "avps-v1-case-"
EMPTY_ALLOWED_DIAGNOSTIC_MEMBERS = {
    "syntax-stdout.txt",
    "syntax-stderr.txt",
    "solver-stdout.txt",
    "solver-stderr.txt",
}


class PhaseARefusal(RuntimeError):
    pass


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise PhaseARefusal(f"cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def find_one(root: Path, basename: str) -> Path:
    rows = [p for p in root.rglob(basename) if p.is_file()]
    if len(rows) != 1:
        raise PhaseARefusal(f"{root}: expected exactly one {basename}, got {len(rows)}")
    return rows[0]


def _flatten_artifact_pages(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        rows = payload.get("artifacts")
        if not isinstance(rows, list):
            raise PhaseARefusal("live artifact payload missing artifacts list")
        return rows
    if isinstance(payload, list):
        out: list[dict[str, Any]] = []
        for page in payload:
            if not isinstance(page, dict) or not isinstance(page.get("artifacts"), list):
                raise PhaseARefusal("live artifact page shape drift")
            out.extend(page["artifacts"])
        return out
    raise PhaseARefusal("live artifact payload shape drift")


def validate_gate0_metadata(metadata: dict[str, Any]) -> dict[str, dict[str, Any]]:
    exact = {
        "schemaVersion": 1,
        "status": "EXACT360_RAW_RECOVERY_ARTIFACT_METADATA_FROZEN_RESULTS_UNOPENED",
        "workflowRunId": RECOVERY_RUN_ID,
        "recoveryOfWorkflowRunId": FAILED_RUN_ID,
        "caseArtifactCount": 360,
        "caseContentsDownloaded": False,
        "aggregateResultsCalled": False,
        "openResultsCalled": False,
        "scientificInterpretationPerformed": False,
    }
    for key, value in exact.items():
        if metadata.get(key) != value:
            raise PhaseARefusal(f"Gate-0 metadata drift: {key}")
    rows = metadata.get("artifacts")
    if not isinstance(rows, list) or len(rows) != 360:
        raise PhaseARefusal("Gate-0 exact 360 artifact rows required")
    by_name: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise PhaseARefusal("Gate-0 artifact row shape drift")
        name = str(row.get("name") or "")
        aid = row.get("id")
        digest = str(row.get("digest") or "")
        size = row.get("sizeInBytes")
        if not name.startswith(CASE_PREFIX) or name in by_name:
            raise PhaseARefusal(f"Gate-0 case artifact name drift: {name}")
        if isinstance(aid, bool) or not isinstance(aid, int) or aid <= 0:
            raise PhaseARefusal(f"{name}: invalid Gate-0 artifact ID")
        if not digest.startswith("sha256:") or len(digest) != 71:
            raise PhaseARefusal(f"{name}: invalid Gate-0 artifact digest")
        if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
            raise PhaseARefusal(f"{name}: invalid Gate-0 artifact size")
        by_name[name] = row
    if len(by_name) != 360:
        raise PhaseARefusal("Gate-0 artifact names not unique")
    return by_name


def validate_live_artifact_surface(
    gate0_by_name: dict[str, dict[str, Any]], live_payload: Any
) -> None:
    rows = _flatten_artifact_pages(live_payload)
    cases = [r for r in rows if str(r.get("name") or "").startswith(CASE_PREFIX)]
    if len(cases) != 360:
        raise PhaseARefusal(f"live exact 360 case artifacts required, got {len(cases)}")
    by_name = {str(r.get("name") or ""): r for r in cases}
    if len(by_name) != 360 or set(by_name) != set(gate0_by_name):
        raise PhaseARefusal("live/Gate-0 case artifact universe drift")
    for name, frozen in gate0_by_name.items():
        live = by_name[name]
        if live.get("expired") is True:
            raise PhaseARefusal(f"{name}: live artifact expired")
        if int(live.get("id") or 0) != frozen["id"]:
            raise PhaseARefusal(f"{name}: artifact ID drift")
        if live.get("digest") != frozen["digest"]:
            raise PhaseARefusal(f"{name}: artifact digest drift")
        if int(live.get("size_in_bytes") or 0) != frozen["sizeInBytes"]:
            raise PhaseARefusal(f"{name}: artifact size drift")
        wf = live.get("workflow_run") or {}
        if wf and int(wf.get("id") or 0) != RECOVERY_RUN_ID:
            raise PhaseARefusal(f"{name}: source workflow drift")


def validate_recovery_case_result(result: dict[str, Any], case_name: str) -> None:
    exact = {
        "transportRecovery": True,
        "recoveryOfWorkflowRunId": FAILED_RUN_ID,
        "recoveryReason": "EMPTY_DIAGNOSTIC_STREAM_ARTIFACT_CONTRACT_ONLY",
        "authorizedOriginalExecutorGitBlobSha1": ORIGINAL_EXECUTOR_GIT_BLOB_SHA1,
        "recoveryExecutorGitBlobSha1": RECOVERY_EXECUTOR_GIT_BLOB_SHA1,
        "scientificInputsChangedByRecovery": False,
        "seedAllocationChangedByRecovery": False,
        "caseUniverseChangedByRecovery": False,
        "runtimeIdentityChangedByRecovery": False,
        "resultOpeningAuthorizedByRecovery": False,
        "retryPerformed": False,
        "resumePerformed": False,
        "githubRerun": False,
        "workflowRunAttempt": 1,
        "workflowRunId": RECOVERY_RUN_ID,
        "scientificOrdinal": SCIENTIFIC_ORDINAL,
    }
    for key, value in exact.items():
        if result.get(key) != value:
            raise PhaseARefusal(f"{case_name}: recovery provenance drift: {key}")
    allowed = result.get("emptyDiagnosticStreamsPermittedByRecovery")
    if not isinstance(allowed, list) or set(allowed) != EMPTY_ALLOWED_DIAGNOSTIC_MEMBERS:
        raise PhaseARefusal(f"{case_name}: recovery diagnostic-member policy drift")


def run_phase_a(
    repository_root: Path,
    authorization_path: Path,
    artifact_root: Path,
    gate0_metadata_path: Path,
    live_artifact_pages_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    stage_dir = repository_root / "experiments" / STAGE
    aggregator_path = stage_dir / "aggregate_results.py"
    if git_blob_sha1(aggregator_path) != AGGREGATOR_GIT_BLOB_SHA1:
        raise PhaseARefusal("frozen aggregator byte drift")
    if git_blob_sha1(authorization_path) != "91c2fcfe0536f7289b9da3c597428c546523571a":
        raise PhaseARefusal("authorization document byte drift")

    metadata = json.loads(gate0_metadata_path.read_text())
    gate0_by_name = validate_gate0_metadata(metadata)
    live = json.loads(live_artifact_pages_path.read_text())
    validate_live_artifact_surface(gate0_by_name, live)

    for name in sorted(gate0_by_name):
        root = artifact_root / name
        if not root.is_dir():
            raise PhaseARefusal(f"downloaded artifact missing: {name}")
        result = json.loads(find_one(root, "case-result.json").read_text())
        validate_recovery_case_result(result, name)

    aggregate = load_module("avps_frozen_aggregate_for_phase_a", aggregator_path)
    acquisition, analysis_input = aggregate.aggregate(
        repository_root,
        authorization_path,
        artifact_root,
        gate0_metadata_path,
        expected_workflow_run_id=RECOVERY_RUN_ID,
        expected_scientific_ordinal=SCIENTIFIC_ORDINAL,
    )
    if acquisition.get("status") != "COMPLETE_EXACT_360_CASE_ARTIFACT_UNIVERSE_RESULTS_STILL_CLOSED":
        raise PhaseARefusal("frozen aggregate acquisition status drift")
    if acquisition.get("resultOpeningAuthorized") is not False:
        raise PhaseARefusal("Phase A must keep results closed")
    if analysis_input.get("status") != "COMPLETE_EXACT_360_ANALYSIS_INPUT_AFTER_AGGREGATE_VERIFICATION":
        raise PhaseARefusal("frozen analysis-input status drift")
    for payload, label in ((acquisition, "acquisition"), (analysis_input, "analysis-input")):
        stored = payload.get("contentSha256")
        check = dict(payload)
        check.pop("contentSha256", None)
        if stored != canonical_sha256(check):
            raise PhaseARefusal(f"{label} self-hash drift")

    output_dir.mkdir(parents=True, exist_ok=False)
    acquisition_path = output_dir / "acquisition-audit.json"
    analysis_path = output_dir / "analysis-input.json"
    acquisition_path.write_text(json.dumps(acquisition, indent=2, sort_keys=True) + "\n")
    analysis_path.write_text(json.dumps(analysis_input, indent=2, sort_keys=True) + "\n")
    receipt = {
        "schemaVersion": 1,
        "stageId": f"{STAGE}-post360-phase-a",
        "status": "PHASE_A_EXACT360_AGGREGATE_VERIFIED_RESULTS_STILL_CLOSED",
        "authorizationParent": AUTHORIZATION_PARENT,
        "authorizationHead": AUTHORIZATION_HEAD,
        "scientificOrdinal": SCIENTIFIC_ORDINAL,
        "sourceWorkflowRunId": RECOVERY_RUN_ID,
        "sourceWorkflowHead": RECOVERY_RUN_HEAD,
        "gate0MetadataArtifactId": GATE0_METADATA_ARTIFACT_ID,
        "gate0MetadataArtifactDigest": GATE0_METADATA_ARTIFACT_DIGEST,
        "gate0MetadataInnerSha256": GATE0_METADATA_INNER_SHA256,
        "protocolReviewPr": PROTOCOL_REVIEW_PR,
        "protocolReviewHead": PROTOCOL_REVIEW_HEAD,
        "caseArtifactCount": 360,
        "sourceAcquisitionContentSha256": acquisition["contentSha256"],
        "analysisInputContentSha256": analysis_input["contentSha256"],
        "analysisInputRawSha256": sha256_file(analysis_path),
        "caseContentsDownloadedForVerification": True,
        "aggregateResultsCalled": True,
        "openResultsCalled": False,
        "scientificInterpretationPerformed": False,
        "resultOpeningAuthorized": False,
    }
    receipt["contentSha256"] = canonical_sha256(receipt)
    (output_dir / "phase-a-receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    )
    return receipt
