#!/usr/bin/env python3
"""Assemble the LOWALT-STELLAR-STATE-0001 lower-altitude candidate runtime.

This module consumes only an eligible fresh 275-spectrum training payload plus
the already-authoritative v3.2 runtime. It copies the exact 5-degree seam from
v3.2 and never executes a solver or opens/evaluates protected validation data.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
PHASE_B_PATH = HERE / "low_altitude_phase_b.py"
SPEC = importlib.util.spec_from_file_location("low_altitude_phase_b_for_assembly", PHASE_B_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load reviewed Phase-B contract")
phase_b = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(phase_b)

ASSEMBLY_ID = "low-altitude-stellar-phase-b-training-candidate-v1"
TRAINING_EXECUTION_ID = "low-altitude-stellar-phase-b-training-v1-exec001"


class AssemblyRefusal(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def require_training_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if payload.get("executionId") != TRAINING_EXECUTION_ID:
        raise AssemblyRefusal("unexpected training execution identity")
    if payload.get("scientificState") != phase_b.SCIENTIFIC_STATE:
        raise AssemblyRefusal("training scientific-state mismatch")
    if payload.get("phaseBFreezeIssue60CommentId") != phase_b.PHASE_B_FREEZE_COMMENT_ID:
        raise AssemblyRefusal("training Phase-B freeze binding mismatch")
    if payload.get("executionComplete") is not True:
        raise AssemblyRefusal("training execution is incomplete")
    if payload.get("trainingScientificallyEligible") is not True:
        raise AssemblyRefusal("training is not scientifically eligible")
    if payload.get("solverInvocationCount") != phase_b.EXPECTED_TRAINING_SPECTRA:
        raise AssemblyRefusal("training invocation count drift")
    if payload.get("passingTrainingSpectrumCount") != phase_b.EXPECTED_TRAINING_SPECTRA:
        raise AssemblyRefusal("training PASS count drift")
    if payload.get("numericallyUnresolvedTrainingSpectrumCount") != 0:
        raise AssemblyRefusal("training contains numerically unresolved spectra")
    if payload.get("trainingOnly") is not True:
        raise AssemblyRefusal("training-only claim missing")
    if payload.get("fiveDegreeSeamRegenerated") is not False:
        raise AssemblyRefusal("training attempted to regenerate protected seam")
    if payload.get("protectedValidationOpened") is not False:
        raise AssemblyRefusal("protected validation was opened during training")
    if payload.get("protectedSolverInvocationCount") != 0:
        raise AssemblyRefusal("protected solver invocation count is not zero")
    if payload.get("positiveEpsilonSubstitutionUsed") is not False:
        raise AssemblyRefusal("epsilon substitution detected")
    if payload.get("productionAuthorized") is not False or payload.get("applicationSupportChanged") is not False:
        raise AssemblyRefusal("training payload crossed claim boundary")
    if payload.get("solver") != "sdisort" or payload.get("solverGeometry") != "pseudo-spherical":
        raise AssemblyRefusal("training solver geometry drift")
    cases = payload.get("cases")
    if not isinstance(cases, list) or len(cases) != phase_b.EXPECTED_TRAINING_SPECTRA:
        raise AssemblyRefusal("training case universe incomplete")
    if any(row.get("status") != "PASS" for row in cases):
        raise AssemblyRefusal("non-PASS training case present")
    phase_b.validate_training_results(cases)
    return cases


def assemble_candidate(*, training_payload: dict[str, Any], source_v32_runtime: dict[str, Any],
                       source_v32_sha256: str, source_run_id: int,
                       source_artifact_id: int, source_artifact_digest: str,
                       source_dispatch_sha: str) -> tuple[dict[str, Any], dict[str, Any]]:
    phase_b.validate_frozen_universe()
    if source_v32_sha256 != phase_b.SOURCE_V32_RUNTIME_SHA256:
        raise AssemblyRefusal("authoritative v3.2 runtime SHA-256 mismatch")
    cases = require_training_payload(training_payload)
    runtime = phase_b.assemble_lower_runtime(cases, source_v32_runtime)
    if runtime["routing"]["lowerProviderMinInclusiveDeg"] != 0.25:
        raise AssemblyRefusal("candidate lower routing floor drift")
    if runtime["routing"]["lowerProviderMaxExclusiveDeg"] != 5.0:
        raise AssemblyRefusal("candidate seam routing drift")
    if runtime["routing"]["exactFiveAndAboveProvider"] != "authoritative-v3.2":
        raise AssemblyRefusal("authoritative exact-5 routing lost")
    if runtime["routing"]["exactHorizonSupported"] is not False:
        raise AssemblyRefusal("candidate falsely claims exact horizon support")
    runtime["provenance"].update({
        "assemblyId": ASSEMBLY_ID,
        "trainingExecutionId": TRAINING_EXECUTION_ID,
        "trainingSourceRunId": int(source_run_id),
        "trainingSourceArtifactId": int(source_artifact_id),
        "trainingSourceArtifactDigest": str(source_artifact_digest),
        "trainingSourceDispatchSha": str(source_dispatch_sha),
        "trainingSolver": "sdisort",
        "trainingSolverGeometry": "pseudo-spherical",
        "trainingTargetAltitudeBasis": "topocentric-vacuum-geometric",
        "refractionAppliedInRadiativeTransfer": False,
        "protectedValidationOpened": False,
        "protectedSolverInvocationCount": 0,
        "scientificallyValidatedBelow5Deg": False,
        "applicationSupportChanged": False,
    })
    phase_b.validate_lower_runtime(runtime, source_v32_runtime)
    canonical = (json.dumps(runtime, indent=2, sort_keys=True) + "\n").encode("utf-8")
    runtime_sha = sha256_bytes(canonical)
    receipt = {
        "schemaVersion": 1,
        "assemblyId": ASSEMBLY_ID,
        "scientificState": phase_b.SCIENTIFIC_STATE,
        "trainingExecutionId": TRAINING_EXECUTION_ID,
        "trainingSourceRunId": int(source_run_id),
        "trainingSourceArtifactId": int(source_artifact_id),
        "trainingSourceArtifactDigest": str(source_artifact_digest),
        "trainingSourceDispatchSha": str(source_dispatch_sha),
        "sourceV32RuntimeSha256": source_v32_sha256,
        "candidateRuntimeSha256": runtime_sha,
        "freshTrainingSpectrumCount": phase_b.EXPECTED_TRAINING_SPECTRA,
        "inheritedFiveDegreeSeamSpectrumCount": phase_b.EXPECTED_SEAM_SPECTRA,
        "protectedSpectrumCountOpened": 0,
        "protectedJohnsonVComparisonCountOpened": 0,
        "exactFiveDegreeSeamContentIdentical": True,
        "targetAltitudeRepresentation": "linear-direct-optical-depth-vs-geometric-altitude",
        "cscExtrapolationBelow5Deg": False,
        "refractionAppliedInRadiativeTransfer": False,
        "minimumCandidateGeometricAltitudeDeg": 0.25,
        "minimumScientificallySupportedGeometricAltitudeDeg": None,
        "exactHorizonSupported": False,
        "scientificallyValidatedBelow5Deg": False,
        "productionAuthorized": False,
        "applicationSupportChanged": False,
        "protectedValidationAuthorized": False,
    }
    return runtime, receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training-result", type=Path, required=True)
    parser.add_argument("--source-v32-runtime", type=Path, required=True)
    parser.add_argument("--source-run-id", type=int, required=True)
    parser.add_argument("--source-artifact-id", type=int, required=True)
    parser.add_argument("--source-artifact-digest", required=True)
    parser.add_argument("--source-dispatch-sha", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise AssemblyRefusal("output directory already exists; overwrite/reassembly is forbidden")
    training = json.loads(args.training_result.read_text(encoding="utf-8"))
    source_bytes = args.source_v32_runtime.read_bytes()
    source_sha = sha256_bytes(source_bytes)
    source_runtime = json.loads(source_bytes.decode("utf-8"))
    runtime, receipt = assemble_candidate(
        training_payload=training,
        source_v32_runtime=source_runtime,
        source_v32_sha256=source_sha,
        source_run_id=args.source_run_id,
        source_artifact_id=args.source_artifact_id,
        source_artifact_digest=args.source_artifact_digest,
        source_dispatch_sha=args.source_dispatch_sha,
    )
    args.output_dir.mkdir(parents=True)
    runtime_path = args.output_dir / "stellar-transport-low-altitude-training-candidate-v1.json"
    runtime_path.write_text(json.dumps(runtime, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if sha256_file(runtime_path) != receipt["candidateRuntimeSha256"]:
        raise AssemblyRefusal("candidate runtime serialization hash drift")
    (args.output_dir / "assembly-receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
