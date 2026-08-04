#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "twilight-surrogate-tier-1-ordinal2-recovery-v1"
EXECUTION_KEY = "twilight-surrogate-tier-1-v1:numerical:2"
AUTHORIZATION_ORDINAL = 2
EXPECTED_CASES = 96
EXPECTED_GEOMETRIES = 48
EXPECTED_PHOTONS = 6_960_000_000
FRESH_SEED_BASE = 9_200_000


class RecoveryError(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise RecoveryError(f"expected JSON object: {path}")
    return value


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def recover(manifest_path: Path, ordinal1_audit_path: Path, runtime_proof_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    source = load(manifest_path)
    failure_audit = load(ordinal1_audit_path)
    runtime_proof = load(runtime_proof_path)

    if len(source.get("geometries", [])) != EXPECTED_GEOMETRIES or len(source.get("cases", [])) != EXPECTED_CASES:
        raise RecoveryError("source Tier-1 counts changed")
    if sum(case.get("photonHistories", 0) for case in source["cases"]) != EXPECTED_PHOTONS:
        raise RecoveryError("source photon sum changed")
    if failure_audit.get("status") != "ORDINAL_1_UNIFORMLY_FAILED_BEFORE_SCIENTIFIC_RESULT":
        raise RecoveryError("ordinal-1 failure audit not accepted")
    if failure_audit.get("validScientificCaseResultCount") != 0 or failure_audit.get("authorizationConsumed") is not True:
        raise RecoveryError("ordinal-1 artifact boundary changed")
    if runtime_proof.get("status") != "FROZEN_RUNTIME_ACCEPTS_SITE_ALTITUDE_INPUT":
        raise RecoveryError("frozen runtime proof not accepted")
    if runtime_proof.get("syntaxCheckCount") != 1 or runtime_proof.get("solverExecutionCount") != 0:
        raise RecoveryError("runtime proof execution boundary changed")
    if runtime_proof.get("requiredInputLines") != ["altitude 0.357143", "zout 0.000000"]:
        raise RecoveryError("runtime proof input boundary changed")

    recovered = copy.deepcopy(source)
    source_seeds = [case.get("seed") for case in source["cases"]]
    fresh_seeds = []
    for expected_ordinal, case in enumerate(recovered["cases"], start=1):
        if case.get("ordinal") != expected_ordinal:
            raise RecoveryError("case ordinal sequence changed")
        new_seed = FRESH_SEED_BASE + expected_ordinal
        case["seed"] = new_seed
        fresh_seeds.append(new_seed)
    if len(set(source_seeds)) != EXPECTED_CASES or len(set(fresh_seeds)) != EXPECTED_CASES:
        raise RecoveryError("source or fresh seeds are not unique")
    if set(source_seeds) & set(fresh_seeds):
        raise RecoveryError("fresh seeds overlap ordinal-1 seeds")

    recovered["recovery"] = {
        "stageId": STAGE_ID,
        "sourceAuthorizationOrdinal": 1,
        "authorizationOrdinal": AUTHORIZATION_ORDINAL,
        "executionKey": EXECUTION_KEY,
        "freshSeedsForAllCases": True,
        "ordinal1AuditRawSha256": raw_sha256(ordinal1_audit_path),
        "runtimeProofRawSha256": raw_sha256(runtime_proof_path),
        "sourceManifestRawSha256": raw_sha256(manifest_path),
        "githubRerunPermitted": False,
        "firstAttemptOnly": True,
    }

    invariant_fields = (
        "caseId",
        "groupId",
        "method",
        "block",
        "photonHistories",
        "alisSpectralImportanceSamplingNm",
        "role",
        "executionTierId",
    )
    for before, after in zip(source["cases"], recovered["cases"]):
        changed = {field for field in set(before) | set(after) if before.get(field) != after.get(field)}
        if changed != {"seed"}:
            raise RecoveryError(f"case changed beyond seed: {before.get('caseId')}: {changed}")
        if any(before.get(field) != after.get(field) for field in invariant_fields):
            raise RecoveryError(f"scientific case invariant changed: {before.get('caseId')}")
    if source["geometries"] != recovered["geometries"]:
        raise RecoveryError("geometry set changed")
    for field in ("trainingGeometryIds", "internalHoldoutGeometryIds", "externalValidationAnchorIds", "limits", "frozenInputs"):
        if source.get(field) != recovered.get(field):
            raise RecoveryError(f"manifest invariant changed: {field}")

    report = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "ORDINAL_2_RECOVERY_FROZEN_PENDING_SEPARATE_AUTHORIZATION",
        "executionKey": EXECUTION_KEY,
        "authorizationOrdinal": AUTHORIZATION_ORDINAL,
        "geometryCount": EXPECTED_GEOMETRIES,
        "caseCount": EXPECTED_CASES,
        "configuredMcPhotonsSum": EXPECTED_PHOTONS,
        "freshSeedCount": len(fresh_seeds),
        "freshSeedMinimum": min(fresh_seeds),
        "freshSeedMaximum": max(fresh_seeds),
        "sourceSeedOverlapCount": 0,
        "scientificExecution": False,
        "executionAuthorized": False,
        "githubRerunPermitted": False,
        "surrogateTrainingAuthorized": False,
        "productionModelReady": False,
        "sourceManifestRawSha256": raw_sha256(manifest_path),
        "ordinal1AuditRawSha256": raw_sha256(ordinal1_audit_path),
        "runtimeProofRawSha256": raw_sha256(runtime_proof_path),
        "recoveredManifestRawSha256": hashlib.sha256(dump(recovered).encode()).hexdigest(),
        "boundary": "recovery package only; exactly seeds changed; no authorization, syntax check, solver, model fitting, Tier-2, or production use",
    }
    return recovered, report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--ordinal1-audit", type=Path, required=True)
    parser.add_argument("--runtime-proof", type=Path, required=True)
    parser.add_argument("--output-manifest", type=Path, required=True)
    parser.add_argument("--output-report", type=Path, required=True)
    args = parser.parse_args()
    try:
        recovered, report = recover(args.manifest, args.ordinal1_audit, args.runtime_proof)
        args.output_manifest.parent.mkdir(parents=True, exist_ok=True)
        args.output_report.parent.mkdir(parents=True, exist_ok=True)
        args.output_manifest.write_text(dump(recovered))
        args.output_report.write_text(dump(report))
        print(dump(report), end="")
        return 0
    except Exception as exc:
        print(dump({"schemaVersion": 1, "stageId": STAGE_ID, "status": "REFUSED", "reason": str(exc)}), file=sys.stderr, end="")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
