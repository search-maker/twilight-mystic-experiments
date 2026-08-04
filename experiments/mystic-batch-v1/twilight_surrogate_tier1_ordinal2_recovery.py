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
MAX_SEED = 2_147_483_646


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


def derive_seed(source_manifest_sha: str, case_id: str, used: set[int]) -> int:
    counter = 0
    while True:
        token = f"{STAGE_ID}|{EXECUTION_KEY}|{source_manifest_sha}|{case_id}|{counter}".encode()
        seed = 1 + int.from_bytes(hashlib.sha256(token).digest()[:8], "big") % MAX_SEED
        if seed not in used:
            return seed
        counter += 1


def recover(manifest_path: Path, ordinal1_audit_path: Path, runtime_proof_path: Path, solver_probe_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    source = load(manifest_path)
    failure_audit = load(ordinal1_audit_path)
    runtime_proof = load(runtime_proof_path)
    solver_probe = load(solver_probe_path)

    geometries = source.get("geometries", [])
    cases = source.get("cases", [])
    if len(geometries) != EXPECTED_GEOMETRIES or len(cases) != EXPECTED_CASES:
        raise RecoveryError("source Tier-1 counts changed")
    if sum(case.get("photonHistories", 0) for case in cases) != EXPECTED_PHOTONS:
        raise RecoveryError("source photon sum changed")
    if failure_audit.get("status") != "ORDINAL_1_UNIFORMLY_FAILED_BEFORE_SCIENTIFIC_RESULT":
        raise RecoveryError("ordinal-1 failure audit not accepted")
    if failure_audit.get("validScientificCaseResultCount") != 0 or failure_audit.get("authorizationConsumed") is not True:
        raise RecoveryError("ordinal-1 artifact boundary changed")
    if failure_audit.get("sourceAuthorizationOrdinal") != 1 or failure_audit.get("githubRerunPermitted") is not False:
        raise RecoveryError("ordinal-1 governance boundary changed")
    if runtime_proof.get("status") != "FROZEN_RUNTIME_ACCEPTS_SITE_ALTITUDE_INPUT":
        raise RecoveryError("frozen runtime syntax proof not accepted")
    if runtime_proof.get("syntaxCheckCount") != 1 or runtime_proof.get("solverExecutionCount") != 0:
        raise RecoveryError("runtime syntax proof boundary changed")
    if solver_probe.get("status") != "FROZEN_RUNTIME_SOLVER_ACCEPTS_SITE_ALTITUDE_INPUT":
        raise RecoveryError("frozen runtime solver probe not accepted")
    if solver_probe.get("solverExecutionCount") != 1 or solver_probe.get("mcPhotons") != 1:
        raise RecoveryError("solver probe execution boundary changed")
    if solver_probe.get("generatedOutputFilesPreserved") is not False or solver_probe.get("scientificDatasetProduced") is not False:
        raise RecoveryError("solver probe artifact boundary changed")
    required = ["altitude 0.357143", "zout 0.000000"]
    if runtime_proof.get("requiredInputLines") != required or solver_probe.get("requiredInputLines") != required:
        raise RecoveryError("runtime proof input boundary changed")

    geometry_ids = [row.get("geometryId") for row in geometries]
    if len(set(geometry_ids)) != EXPECTED_GEOMETRIES or any(not isinstance(value, str) for value in geometry_ids):
        raise RecoveryError("geometry IDs invalid")
    training_ids = source.get("trainingGeometryIds", [])
    holdout_ids = source.get("internalHoldoutGeometryIds", [])
    if len(training_ids) != 39 or len(holdout_ids) != 9 or set(training_ids) & set(holdout_ids):
        raise RecoveryError("frozen 39/9 role split changed")
    if set(training_ids) | set(holdout_ids) != set(geometry_ids):
        raise RecoveryError("frozen role split does not cover geometries")

    recovered = copy.deepcopy(source)
    source_seeds = [case.get("seed") for case in cases]
    if len(set(source_seeds)) != EXPECTED_CASES or any(not isinstance(seed, int) for seed in source_seeds):
        raise RecoveryError("source seeds are not unique integers")
    used = set(source_seeds)
    fresh_seeds: list[int] = []
    source_sha = raw_sha256(manifest_path)
    for expected_ordinal, case in enumerate(recovered["cases"], start=1):
        if case.get("ordinal") != expected_ordinal:
            raise RecoveryError("case ordinal sequence changed")
        case_id = case.get("caseId")
        if not isinstance(case_id, str):
            raise RecoveryError("case ID invalid")
        new_seed = derive_seed(source_sha, case_id, used)
        used.add(new_seed)
        case["seed"] = new_seed
        fresh_seeds.append(new_seed)
    if len(set(fresh_seeds)) != EXPECTED_CASES or set(source_seeds) & set(fresh_seeds):
        raise RecoveryError("fresh seed governance failed")

    invariant_fields = ("caseId", "groupId", "method", "block", "photonHistories", "alisSpectralImportanceSamplingNm", "role", "executionTierId", "ordinal")
    for before, after in zip(source["cases"], recovered["cases"]):
        changed = {field for field in set(before) | set(after) if before.get(field) != after.get(field)}
        if changed != {"seed"}:
            raise RecoveryError(f"case changed beyond seed: {before.get('caseId')}: {changed}")
        if any(before.get(field) != after.get(field) for field in invariant_fields):
            raise RecoveryError(f"scientific case invariant changed: {before.get('caseId')}")
    if source["geometries"] != recovered["geometries"]:
        raise RecoveryError("geometry set changed")
    for field in ("trainingGeometryIds", "internalHoldoutGeometryIds", "externalValidationAnchorIds", "limits", "frozenInputs", "bindings", "runtime"):
        if source.get(field) != recovered.get(field):
            raise RecoveryError(f"manifest invariant changed: {field}")
    if {case.get("alisSpectralImportanceSamplingNm") for case in cases} != {500.0, 550.0, 600.0}:
        raise RecoveryError("ALIS importance wavelength set changed")

    recovered["recovery"] = {
        "stageId": STAGE_ID,
        "sourceAuthorizationOrdinal": 1,
        "authorizationOrdinal": AUTHORIZATION_ORDINAL,
        "executionKey": EXECUTION_KEY,
        "freshSeedsForAllCases": True,
        "ordinal1AuditRawSha256": raw_sha256(ordinal1_audit_path),
        "runtimeSyntaxProofRawSha256": raw_sha256(runtime_proof_path),
        "runtimeSolverProbeRawSha256": raw_sha256(solver_probe_path),
        "sourceManifestRawSha256": source_sha,
        "githubRerunPermitted": False,
        "firstAttemptOnly": True,
    }

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
        "sourceManifestRawSha256": source_sha,
        "ordinal1AuditRawSha256": raw_sha256(ordinal1_audit_path),
        "runtimeSyntaxProofRawSha256": raw_sha256(runtime_proof_path),
        "runtimeSolverProbeRawSha256": raw_sha256(solver_probe_path),
        "recoveredManifestRawSha256": hashlib.sha256(dump(recovered).encode()).hexdigest(),
        "boundary": "recovery package only; exactly seeds changed; no authorization, scientific dataset, model fitting, Tier-2, or production use",
    }
    return recovered, report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--ordinal1-audit", type=Path, required=True)
    parser.add_argument("--runtime-proof", type=Path, required=True)
    parser.add_argument("--solver-probe", type=Path, required=True)
    parser.add_argument("--output-manifest", type=Path, required=True)
    parser.add_argument("--output-report", type=Path, required=True)
    args = parser.parse_args()
    try:
        recovered, report = recover(args.manifest, args.ordinal1_audit, args.runtime_proof, args.solver_probe)
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
