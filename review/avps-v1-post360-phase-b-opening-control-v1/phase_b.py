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
PHASE_A_RUN_ID = 33170006532
PHASE_A_RUN_HEAD = "17537a2a5d60d7836eb9a1e01169a5bab5c70ea2"
PHASE_A_ARTIFACT_ID = 9685308839
PHASE_A_ARTIFACT_DIGEST = "sha256:68216d6a4982618d8cf9238948f0cbeb651bc9cde7ce53e688b5b1b11d204148"
PHASE_A_RECEIPT_CONTENT_SHA256 = "c14ef76e6280bdd34172202c63e8a319b4044cdb647e348926c02d03160198e4"
PHASE_A_ANALYSIS_INPUT_CONTENT_SHA256 = "c58907c2f838396417edcfe87d306c130b92374b649790ff25537f3ac049bdc8"
PHASE_A_ANALYSIS_INPUT_RAW_SHA256 = "b1c2d82e53c91606854c6ae0fea4d6e08d959dd3ee26ac080d0ee62ad4a4096b"
PHASE_A_ACQUISITION_CONTENT_SHA256 = "b3d4ac428ced54e217721507c36e349511ef0b4478f5815af7fe557fed005541"
OPEN_RESULTS_GIT_BLOB_SHA1 = "4a6842e83cbd1525bf603c5e09e92317a63b6af9"
ANALYSIS_GIT_BLOB_SHA1 = "dd2b7fb9cd4cc660338f1694841a0be5b4bf4a4d"
EXECUTION_CONTRACT_GIT_BLOB_SHA1 = "230874923004115ff21f218bb0ce4d2e038d3a98"
PROTOCOL_REVIEW_PR = 579
PROTOCOL_REVIEW_HEAD = "5e191b1afbdb637e6534c856548af1d79138d6f1"
PHASE_A_REVIEW_PR = 584
PHASE_A_REVIEW_HEAD = "b93c284c8a24296dff9d8aedc265f7a3bdec465a"
PHASE_A_REVIEW_RUN_ID = 33169583131


class PhaseBRefusal(RuntimeError):
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
        raise PhaseBRefusal(f"cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def validate_phase_a_receipt(receipt: dict[str, Any]) -> None:
    exact = {
        "schemaVersion": 1,
        "stageId": f"{STAGE}-post360-phase-a",
        "status": "PHASE_A_EXACT360_AGGREGATE_VERIFIED_RESULTS_STILL_CLOSED",
        "authorizationParent": AUTHORIZATION_PARENT,
        "authorizationHead": AUTHORIZATION_HEAD,
        "scientificOrdinal": SCIENTIFIC_ORDINAL,
        "sourceWorkflowRunId": 33139545997,
        "sourceWorkflowHead": "6d0e0e0f1dd1deabaf8bb155ee7e323c5ba8673d",
        "gate0MetadataArtifactId": 9676069031,
        "gate0MetadataArtifactDigest": "sha256:70dedcd16209dea74a9ed67a1dc7377c123f1a62fd18741b1e15692702011fc8",
        "gate0MetadataInnerSha256": "323f458b43a031c50f2c2f74971594801608a5cdf437839c8760b42c19bdb92e",
        "protocolReviewPr": PROTOCOL_REVIEW_PR,
        "protocolReviewHead": PROTOCOL_REVIEW_HEAD,
        "caseArtifactCount": 360,
        "sourceAcquisitionContentSha256": PHASE_A_ACQUISITION_CONTENT_SHA256,
        "analysisInputContentSha256": PHASE_A_ANALYSIS_INPUT_CONTENT_SHA256,
        "analysisInputRawSha256": PHASE_A_ANALYSIS_INPUT_RAW_SHA256,
        "caseContentsDownloadedForVerification": True,
        "aggregateResultsCalled": True,
        "openResultsCalled": False,
        "scientificInterpretationPerformed": False,
        "resultOpeningAuthorized": False,
        "contentSha256": PHASE_A_RECEIPT_CONTENT_SHA256,
    }
    for key, value in exact.items():
        if receipt.get(key) != value:
            raise PhaseBRefusal(f"Phase-A receipt drift: {key}")
    check = dict(receipt)
    stored = check.pop("contentSha256", None)
    if stored != canonical_sha256(check):
        raise PhaseBRefusal("Phase-A receipt self-hash drift")


def validate_phase_a_payloads(phase_a_dir: Path) -> tuple[Path, Path, Path]:
    names = sorted(p.name for p in phase_a_dir.iterdir() if p.is_file())
    if names != ["acquisition-audit.json", "analysis-input.json", "phase-a-receipt.json"]:
        raise PhaseBRefusal(f"Phase-A artifact file universe drift: {names}")
    acquisition = phase_a_dir / "acquisition-audit.json"
    analysis_input = phase_a_dir / "analysis-input.json"
    receipt_path = phase_a_dir / "phase-a-receipt.json"
    receipt = json.loads(receipt_path.read_text())
    validate_phase_a_receipt(receipt)
    if sha256_file(analysis_input) != PHASE_A_ANALYSIS_INPUT_RAW_SHA256:
        raise PhaseBRefusal("Phase-A analysis-input raw SHA-256 drift")
    payload = json.loads(analysis_input.read_text())
    stored = payload.get("contentSha256")
    check = dict(payload)
    check.pop("contentSha256", None)
    if stored != PHASE_A_ANALYSIS_INPUT_CONTENT_SHA256 or stored != canonical_sha256(check):
        raise PhaseBRefusal("Phase-A analysis-input self-hash/content binding drift")
    acquisition_payload = json.loads(acquisition.read_text())
    acq_stored = acquisition_payload.get("contentSha256")
    acq_check = dict(acquisition_payload)
    acq_check.pop("contentSha256", None)
    if acq_stored != PHASE_A_ACQUISITION_CONTENT_SHA256 or acq_stored != canonical_sha256(acq_check):
        raise PhaseBRefusal("Phase-A acquisition self-hash/content binding drift")
    return acquisition, analysis_input, receipt_path


def run_phase_b(repository_root: Path, phase_a_dir: Path, output_dir: Path) -> dict[str, Any]:
    stage_dir = repository_root / "experiments" / STAGE
    open_path = stage_dir / "open_results.py"
    analysis_path = stage_dir / "analysis.py"
    contract_path = stage_dir / "execution-contract.review.json"
    if git_blob_sha1(open_path) != OPEN_RESULTS_GIT_BLOB_SHA1:
        raise PhaseBRefusal("frozen open-results byte drift")
    if git_blob_sha1(analysis_path) != ANALYSIS_GIT_BLOB_SHA1:
        raise PhaseBRefusal("frozen analysis byte drift")
    if git_blob_sha1(contract_path) != EXECUTION_CONTRACT_GIT_BLOB_SHA1:
        raise PhaseBRefusal("frozen execution-contract byte drift")

    _, analysis_input, _ = validate_phase_a_payloads(phase_a_dir)
    opener = load_module("avps_frozen_open_results_for_phase_b", open_path)
    primary = opener.open_results(repository_root, analysis_input)
    exact = {
        "schemaVersion": 1,
        "stageId": f"{STAGE}-primary-analysis",
        "status": "COMPLETED_PREREGISTERED_AVPS_V1_PRIMARY_ANALYSIS_AFTER_EXACT_360_GATE",
        "workflowRunId": 33139545997,
        "scientificOrdinal": SCIENTIFIC_ORDINAL,
        "caseCount": 360,
        "groupCount": 72,
        "analysisCellCount": 24,
        "statesPerGroup": 5,
        "primaryContrastCountPerCell": 4,
        "sourceAnalysisInputContentSha256": PHASE_A_ANALYSIS_INPUT_CONTENT_SHA256,
        "analysisGitBlobSha1": ANALYSIS_GIT_BLOB_SHA1,
        "pValuesPermitted": False,
        "confidenceIntervalsPermitted": False,
        "epsilonSubstitutionPermitted": False,
        "universalSunDepressionToMinutesConversionPermitted": False,
        "productionMaterialityThresholdCreated": False,
        "taylorOrJerusalemScoringPerformed": False,
    }
    for key, value in exact.items():
        if primary.get(key) != value:
            raise PhaseBRefusal(f"frozen primary opening contract drift: {key}")
    if not isinstance(primary.get("cells"), list) or len(primary["cells"]) != 24:
        raise PhaseBRefusal("primary result exact 24-cell universe required")
    stored = primary.get("contentSha256")
    check = dict(primary)
    check.pop("contentSha256", None)
    if stored != canonical_sha256(check):
        raise PhaseBRefusal("primary result self-hash drift")

    output_dir.mkdir(parents=True, exist_ok=False)
    primary_path = output_dir / "primary-results.json"
    primary_path.write_text(json.dumps(primary, indent=2, sort_keys=True) + "\n")
    receipt = {
        "schemaVersion": 1,
        "stageId": f"{STAGE}-post360-phase-b",
        "status": "PHASE_B_PREREGISTERED_PRIMARY_RESULTS_OPENED_NO_TAYLOR_OR_JERUSALEM_SCORING",
        "authorizationParent": AUTHORIZATION_PARENT,
        "authorizationHead": AUTHORIZATION_HEAD,
        "scientificOrdinal": SCIENTIFIC_ORDINAL,
        "phaseARunId": PHASE_A_RUN_ID,
        "phaseARunHead": PHASE_A_RUN_HEAD,
        "phaseAArtifactId": PHASE_A_ARTIFACT_ID,
        "phaseAArtifactDigest": PHASE_A_ARTIFACT_DIGEST,
        "phaseAReceiptContentSha256": PHASE_A_RECEIPT_CONTENT_SHA256,
        "sourceAnalysisInputContentSha256": PHASE_A_ANALYSIS_INPUT_CONTENT_SHA256,
        "sourceAnalysisInputRawSha256": PHASE_A_ANALYSIS_INPUT_RAW_SHA256,
        "openResultsGitBlobSha1": OPEN_RESULTS_GIT_BLOB_SHA1,
        "analysisGitBlobSha1": ANALYSIS_GIT_BLOB_SHA1,
        "primaryResultsContentSha256": primary["contentSha256"],
        "primaryResultsRawSha256": sha256_file(primary_path),
        "resultOpeningPerformed": True,
        "scientificInterpretationPerformed": False,
        "taylorOrJerusalemScoringPerformed": False,
        "levelBMappingPerformed": False,
        "productionRoutingChanged": False,
    }
    receipt["contentSha256"] = canonical_sha256(receipt)
    (output_dir / "phase-b-receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    )
    return receipt
