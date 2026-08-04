#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "twilight-surrogate-tier-1-ordinal2-recovery-v2"
EXECUTION_KEY = "twilight-surrogate-tier-1-v1:numerical:2"
AUTHORIZATION_ORDINAL = 2
EXPECTED_CASES = 96
EXPECTED_GEOMETRIES = 48
EXPECTED_PHOTONS = 6_960_000_000
MAX_SEED = 2_147_483_646
COMBINED_PROOF_STAGE_ID = (
    "twilight-surrogate-tier-1-atm-z-grid-combined-spectral-proof-v3"
)
COMBINED_PROOF_STATUS = (
    "ATM_Z_GRID_ELEVATED_SITE_EQUIVALENCE_AND_MYSTIC_ACCEPTANCE_PROOF_PASSED"
)
MYSTIC_PROBE_STATUS = (
    "MYSTIC_ACCEPTS_EQUIVALENCE_VALIDATED_ATM_Z_GRID_WITH_TIER1_SPECTRAL_DOMAIN"
)
EXPECTED_PRIMARY_SITE_ALTITUDE_KM = 0.357143
EXPECTED_TIER1_DOMAIN_NM = [380.0, 780.0]
EXPECTED_IMPORTANCE_WAVELENGTH_NM = 550.0


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
        token = (
            f"{STAGE_ID}|{EXECUTION_KEY}|{source_manifest_sha}|{case_id}|{counter}"
        ).encode()
        seed = 1 + int.from_bytes(hashlib.sha256(token).digest()[:8], "big") % MAX_SEED
        if seed not in used:
            return seed
        counter += 1


def require_true_fields(value: dict[str, Any], fields: tuple[str, ...], label: str) -> None:
    stale = {field: value.get(field) for field in fields if value.get(field) is not True}
    if stale:
        raise RecoveryError(f"{label} true fields changed: {stale}")


def require_false_fields(value: dict[str, Any], fields: tuple[str, ...], label: str) -> None:
    stale = {field: value.get(field) for field in fields if value.get(field) is not False}
    if stale:
        raise RecoveryError(f"{label} false fields changed: {stale}")


def validate_combined_proof(
    source: dict[str, Any], combined_proof: dict[str, Any]
) -> dict[str, Any]:
    if combined_proof.get("schemaVersion") != 1:
        raise RecoveryError("combined proof schema changed")
    if combined_proof.get("stageId") != COMBINED_PROOF_STAGE_ID:
        raise RecoveryError("combined proof stage changed")
    if combined_proof.get("status") != COMBINED_PROOF_STATUS:
        raise RecoveryError("combined proof status not accepted")
    require_true_fields(
        combined_proof,
        (
            "proofPassed",
            "profileEquivalenceDecision",
            "opticalPropertyEquivalenceDecision",
            "deterministicControlDecision",
            "threeHeightStructuralProfileDecision",
            "mysticProbeDecision",
        ),
        "combined proof",
    )
    require_false_fields(
        combined_proof,
        (
            "scientificExecution",
            "scientificDatasetProduced",
            "surrogateTrainingUsePermitted",
            "authorizationPermitted",
            "ordinal2ScientificDispatchPermitted",
            "githubRerunPermitted",
            "frozenTier1InvariantsChanged",
        ),
        "combined proof",
    )
    if combined_proof.get("deterministicSolverExecutionCount") != 6:
        raise RecoveryError("deterministic proof execution boundary changed")
    if combined_proof.get("mysticSolverExecutionCount") != 1:
        raise RecoveryError("MYSTIC proof execution boundary changed")
    if combined_proof.get("maximumPermittedMysticSolverExecutionCount") != 1:
        raise RecoveryError("MYSTIC proof maximum changed")

    candidate = combined_proof.get("candidateRepresentation")
    if not isinstance(candidate, dict):
        raise RecoveryError("candidate representation missing")
    require_true_fields(
        candidate,
        (
            "atmosphereFileRemainsProfileSource",
            "atmZGridBottomIsSiteAltitude",
            "originalAtmosphereLevelsAboveSitePreservedExactly",
            "explicitAltitudeForbidden",
            "mcElevationFileForbidden",
        ),
        "candidate representation",
    )
    if candidate.get("localSurfaceZoutKm") != 0.0:
        raise RecoveryError("candidate local-surface zout changed")

    mystic = combined_proof.get("mysticProbe")
    if not isinstance(mystic, dict):
        raise RecoveryError("combined MYSTIC probe missing")
    if mystic.get("status") != MYSTIC_PROBE_STATUS or mystic.get("passed") is not True:
        raise RecoveryError("combined MYSTIC probe not accepted")
    if not math.isclose(
        float(mystic.get("siteAltitudeKm", math.nan)),
        EXPECTED_PRIMARY_SITE_ALTITUDE_KM,
        rel_tol=0.0,
        abs_tol=1.0e-9,
    ):
        raise RecoveryError("combined MYSTIC site altitude changed")
    if mystic.get("localSurfaceZoutKm") != 0.0:
        raise RecoveryError("combined MYSTIC local zout changed")
    require_true_fields(
        mystic,
        ("atmosphereStartsAtSiteAltitude", "surfaceMarkerObserved"),
        "combined MYSTIC probe",
    )
    require_false_fields(
        mystic,
        (
            "layersBelowSiteAltitudePresent",
            "explicitAltitudePresent",
            "mcElevationFilePresent",
            "altitudeRejectionObserved",
            "generatedFilesPreserved",
            "scientificDatasetProduced",
        ),
        "combined MYSTIC probe",
    )
    if mystic.get("solverExecutionCount") != 1 or mystic.get("mcPhotons") != 1:
        raise RecoveryError("combined MYSTIC probe boundary changed")
    generated = mystic.get("generatedFiles")
    if not isinstance(generated, list) or not generated:
        raise RecoveryError("combined MYSTIC proof produced no hashed numerical file")

    spectral = mystic.get("spectralConfiguration")
    if not isinstance(spectral, dict):
        raise RecoveryError("combined MYSTIC spectral configuration missing")
    if spectral.get("wavelengthDomainNm") != EXPECTED_TIER1_DOMAIN_NM:
        raise RecoveryError("combined MYSTIC spectral domain changed")
    if spectral.get("alisImportanceWavelengthNm") != EXPECTED_IMPORTANCE_WAVELENGTH_NM:
        raise RecoveryError("combined MYSTIC importance wavelength changed")
    require_true_fields(
        spectral,
        (
            "alisReferenceStrictlyInsideDomain",
            "matchesFrozenTier1Domain",
            "alisMarkerObserved",
        ),
        "combined MYSTIC spectral configuration",
    )
    if spectral.get("singleWavelengthEndpointCrashConfigurationUsed") is not False:
        raise RecoveryError("single-wavelength crash configuration returned")

    source_runtime = source.get("runtime")
    proof_runtime = combined_proof.get("runtime")
    if not isinstance(source_runtime, dict) or not isinstance(proof_runtime, dict):
        raise RecoveryError("runtime binding missing")
    runtime_fields = (
        "uvspecSha256",
        "runtimeLockRawSha256",
        "atmosphereSha256",
    )
    stale = {
        field: (proof_runtime.get(field), source_runtime.get(field))
        for field in runtime_fields
        if proof_runtime.get(field) != source_runtime.get(field)
    }
    if stale:
        raise RecoveryError(f"combined proof runtime differs from source manifest: {stale}")

    return {
        "stageId": combined_proof["stageId"],
        "status": combined_proof["status"],
        "rawSha256": None,
        "representation": "atm_z_grid",
        "siteAltitudeKm": EXPECTED_PRIMARY_SITE_ALTITUDE_KM,
        "localSurfaceZoutKm": 0.0,
        "wavelengthDomainNm": EXPECTED_TIER1_DOMAIN_NM,
        "mysticSolverExecutionCount": 1,
        "mcPhotons": 1,
        "proofPassed": True,
    }


def recover(
    manifest_path: Path,
    ordinal1_audit_path: Path,
    combined_proof_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    source = load(manifest_path)
    failure_audit = load(ordinal1_audit_path)
    combined_proof = load(combined_proof_path)

    geometries = source.get("geometries", [])
    cases = source.get("cases", [])
    if len(geometries) != EXPECTED_GEOMETRIES or len(cases) != EXPECTED_CASES:
        raise RecoveryError("source Tier-1 counts changed")
    if sum(case.get("photonHistories", 0) for case in cases) != EXPECTED_PHOTONS:
        raise RecoveryError("source photon sum changed")
    if failure_audit.get("status") != (
        "ORDINAL_1_UNIFORMLY_FAILED_BEFORE_SCIENTIFIC_RESULT"
    ):
        raise RecoveryError("ordinal-1 failure audit not accepted")
    if (
        failure_audit.get("validScientificCaseResultCount") != 0
        or failure_audit.get("authorizationConsumed") is not True
    ):
        raise RecoveryError("ordinal-1 artifact boundary changed")
    if (
        failure_audit.get("sourceAuthorizationOrdinal") != 1
        or failure_audit.get("githubRerunPermitted") is not False
    ):
        raise RecoveryError("ordinal-1 governance boundary changed")

    proof_binding = validate_combined_proof(source, combined_proof)
    proof_binding["rawSha256"] = raw_sha256(combined_proof_path)

    geometry_ids = [row.get("geometryId") for row in geometries]
    if len(set(geometry_ids)) != EXPECTED_GEOMETRIES or any(
        not isinstance(value, str) for value in geometry_ids
    ):
        raise RecoveryError("geometry IDs invalid")
    training_ids = source.get("trainingGeometryIds", [])
    holdout_ids = source.get("internalHoldoutGeometryIds", [])
    if (
        len(training_ids) != 39
        or len(holdout_ids) != 9
        or set(training_ids) & set(holdout_ids)
    ):
        raise RecoveryError("frozen 39/9 role split changed")
    if set(training_ids) | set(holdout_ids) != set(geometry_ids):
        raise RecoveryError("frozen role split does not cover geometries")

    recovered = copy.deepcopy(source)
    source_seeds = [case.get("seed") for case in cases]
    if len(set(source_seeds)) != EXPECTED_CASES or any(
        not isinstance(seed, int) for seed in source_seeds
    ):
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
    if len(set(fresh_seeds)) != EXPECTED_CASES or set(source_seeds) & set(
        fresh_seeds
    ):
        raise RecoveryError("fresh seed governance failed")

    invariant_fields = (
        "caseId",
        "groupId",
        "method",
        "block",
        "photonHistories",
        "alisSpectralImportanceSamplingNm",
        "role",
        "executionTierId",
        "ordinal",
    )
    for before, after in zip(source["cases"], recovered["cases"]):
        changed = {
            field
            for field in set(before) | set(after)
            if before.get(field) != after.get(field)
        }
        if changed != {"seed"}:
            raise RecoveryError(
                f"case changed beyond seed: {before.get('caseId')}: {changed}"
            )
        if any(before.get(field) != after.get(field) for field in invariant_fields):
            raise RecoveryError(
                f"scientific case invariant changed: {before.get('caseId')}"
            )
    if source["geometries"] != recovered["geometries"]:
        raise RecoveryError("geometry set changed")
    for field in (
        "trainingGeometryIds",
        "internalHoldoutGeometryIds",
        "externalValidationAnchorIds",
        "limits",
        "frozenInputs",
        "bindings",
        "runtime",
    ):
        if source.get(field) != recovered.get(field):
            raise RecoveryError(f"manifest invariant changed: {field}")
    if {
        case.get("alisSpectralImportanceSamplingNm") for case in cases
    } != {500.0, 550.0, 600.0}:
        raise RecoveryError("ALIS importance wavelength set changed")

    recovered["recovery"] = {
        "stageId": STAGE_ID,
        "sourceAuthorizationOrdinal": 1,
        "authorizationOrdinal": AUTHORIZATION_ORDINAL,
        "executionKey": EXECUTION_KEY,
        "freshSeedsForAllCases": True,
        "ordinal1AuditRawSha256": raw_sha256(ordinal1_audit_path),
        "combinedAtmZGridProof": proof_binding,
        "sourceManifestRawSha256": source_sha,
        "githubRerunPermitted": False,
        "firstAttemptOnly": True,
        "scientificExecution": False,
        "executionAuthorized": False,
    }

    report = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": (
            "ORDINAL_2_RECOVERY_FROZEN_WITH_ATM_Z_GRID_PENDING_SEPARATE_AUTHORIZATION"
        ),
        "executionKey": EXECUTION_KEY,
        "authorizationOrdinal": AUTHORIZATION_ORDINAL,
        "geometryCount": EXPECTED_GEOMETRIES,
        "caseCount": EXPECTED_CASES,
        "configuredMcPhotonsSum": EXPECTED_PHOTONS,
        "freshSeedCount": len(fresh_seeds),
        "freshSeedMinimum": min(fresh_seeds),
        "freshSeedMaximum": max(fresh_seeds),
        "sourceSeedOverlapCount": 0,
        "observerElevationRepresentation": "atm_z_grid",
        "localSurfaceZoutKm": 0.0,
        "combinedAtmZGridProof": proof_binding,
        "scientificExecution": False,
        "executionAuthorized": False,
        "authorizationPermitted": False,
        "ordinal2ScientificDispatchPermitted": False,
        "githubRerunPermitted": False,
        "surrogateTrainingAuthorized": False,
        "productionModelReady": False,
        "sourceManifestRawSha256": source_sha,
        "ordinal1AuditRawSha256": raw_sha256(ordinal1_audit_path),
        "combinedProofRawSha256": raw_sha256(combined_proof_path),
        "recoveredManifestRawSha256": hashlib.sha256(
            dump(recovered).encode()
        ).hexdigest(),
        "boundary": (
            "recovery package only; exactly seeds changed; observer elevation is "
            "rendered later by the execution adapter through the equivalence-proven "
            "atm_z_grid representation; no authorization, dispatch, scientific "
            "dataset, model fitting, Tier-2, or production use"
        ),
    }
    return recovered, report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--ordinal1-audit", type=Path, required=True)
    parser.add_argument("--combined-proof", type=Path, required=True)
    parser.add_argument("--output-manifest", type=Path, required=True)
    parser.add_argument("--output-report", type=Path, required=True)
    args = parser.parse_args()
    try:
        recovered, report = recover(
            args.manifest, args.ordinal1_audit, args.combined_proof
        )
        args.output_manifest.parent.mkdir(parents=True, exist_ok=True)
        args.output_report.parent.mkdir(parents=True, exist_ok=True)
        args.output_manifest.write_text(dump(recovered))
        args.output_report.write_text(dump(report))
        print(dump(report), end="")
        return 0
    except Exception as exc:
        print(
            dump(
                {
                    "schemaVersion": 1,
                    "stageId": STAGE_ID,
                    "status": "REFUSED",
                    "reason": str(exc),
                    "scientificExecution": False,
                    "authorizationPermitted": False,
                    "ordinal2ScientificDispatchPermitted": False,
                    "githubRerunPermitted": False,
                }
            ),
            file=sys.stderr,
            end="",
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
