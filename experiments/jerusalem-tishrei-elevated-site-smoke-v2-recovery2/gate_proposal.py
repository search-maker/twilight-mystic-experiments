#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "jerusalem-tishrei-elevated-site-smoke-v2-recovery2"
BATCH_ID = STAGE_ID
EXECUTION_KEY = "jerusalem-tishrei-elevated-site-smoke-v2:infrastructure:3"
SMOKE_ORDINAL = 3
CONSUMED_RECOVERY1_MAIN_SHA = "7f007e37ba33aba8fafa450418a10ef35eb3f72d"
RECOVERY1_RUN_ID = 33009947410
PACKAGE = Path("experiments/jerusalem-tishrei-elevated-site-smoke-v2-recovery2")
PATHS = {
    "gate": PACKAGE / "gate.smoke-recovery2.json",
    "guard": PACKAGE / "execution_guard.py",
    "workflow": Path(".github/workflows/jerusalem-tishrei-elevated-site-smoke-v2-recovery2.yml"),
    "sourceManifest": Path("experiments/jerusalem-tishrei-elevated-site-smoke-v2/manifest.smoke.json"),
    "sourceAdapter": Path("experiments/jerusalem-tishrei-elevated-site-smoke-v2/adapter.py"),
    "recovery2Executor": PACKAGE / "smoke_executor.py",
    "consumedRecovery1Gate": Path("experiments/jerusalem-tishrei-elevated-site-smoke-v2-recovery1/gate.smoke-recovery1.json"),
    "referenceVroomRunner": Path("experiments/reference-vroom-v1/runner.py"),
    "referenceVroomGrid": Path("experiments/reference-vroom-v1/wavelength-grid.dat"),
    "duplicateRunAudit": Path("experiments/mystic-batch-v1/duplicate_run_audit.py"),
    "runtimeLock": Path("experiments/mystic-batch-v1/runtime-lock.micromamba.json"),
    "runtimeProbe": Path("experiments/mystic-batch-v1/runtime_probe.py"),
}
EXPECTED_RUN_NAME = "run-name: MYSTIC batch v1 | key=${{ inputs.execution_key }} | auth=${{ inputs.gate_ref }} | ordinal=${{ inputs.smoke_ordinal }}"
EXPECTED_CASES = [
    {"ordinal": 1, "caseId": "jtm-smoke-gamcyg-vroom-v2", "method": "reference-vroom", "seed": 89301, "photonHistories": 10000},
    {"ordinal": 2, "caseId": "jtm-smoke-gamcyg-alis-v2", "method": "alis", "seed": 89302, "photonHistories": 10000},
]


class ProposalError(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ProposalError(f"expected JSON object: {path}")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def require_ancestor(root: Path, ancestor: str) -> None:
    if subprocess.run(["git", "merge-base", "--is-ancestor", ancestor, "HEAD"], cwd=root, check=False).returncode != 0:
        raise ProposalError(f"HEAD does not contain required consumed recovery1 checkpoint {ancestor}")


def validate_disabled_gate(gate: dict[str, Any]) -> None:
    required = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "enabled": False,
        "infrastructureExecution": False,
        "scientificExecution": False,
        "scientificDiagnostic": False,
        "scientificUseProhibited": True,
        "successDoesNotAuthorizeScientificExecution": True,
        "successDoesNotAuthorizeProduction": True,
        "executionKey": None,
        "batchId": None,
        "exactGateParentCommit": None,
        "exactGateCommit": None,
        "smokeOrdinal": 0,
        "consumed": False,
    }
    stale = {k: (gate.get(k), v) for k, v in required.items() if gate.get(k) != v}
    if stale:
        raise ProposalError(f"recovery2 gate is not pristine disabled: {stale}")


def validate_source_manifest(path: Path) -> None:
    m = load(path)
    required = {
        "stageId": "jerusalem-tishrei-elevated-site-smoke-v2",
        "infrastructureOnly": True,
        "scientificExecution": False,
        "scientificDiagnostic": False,
        "scientificUseProhibited": True,
    }
    stale = {k: (m.get(k), v) for k, v in required.items() if m.get(k) != v}
    if stale or m.get("cases") != EXPECTED_CASES:
        raise ProposalError(f"source smoke inputs changed: boundary={stale}, cases={m.get('cases')}")
    g = m.get("frozenGeometry") or {}
    frozen = {
        "sunDepressionDeg": 5.2416836635666755,
        "targetAltitudeDeg": 65.34228371339654,
        "relativeAzimuthDeg": 148.9564384037443,
        "observerElevationM": 800,
        "aod550": 0.22,
        "surfaceAlbedo": 0.15,
        "atmosphere": "AFGLUS",
        "mcSpherical": "1D",
        "molecularAbsorption": "crs",
    }
    stale_g = {k: (g.get(k), v) for k, v in frozen.items() if g.get(k) != v}
    if stale_g:
        raise ProposalError(f"frozen smoke geometry/physics changed: {stale_g}")


def validate_consumed_recovery1(path: Path) -> None:
    g = load(path)
    required = {
        "stageId": "jerusalem-tishrei-elevated-site-smoke-v2-recovery1",
        "enabled": False,
        "infrastructureExecution": False,
        "scientificExecution": False,
        "scientificDiagnostic": False,
        "scientificUseProhibited": True,
        "consumed": True,
        "executionKey": "jerusalem-tishrei-elevated-site-smoke-v2:infrastructure:2",
        "smokeOrdinal": 2,
    }
    stale = {k: (g.get(k), v) for k, v in required.items() if g.get(k) != v}
    if stale:
        raise ProposalError(f"consumed recovery1 gate changed: {stale}")
    note = str(g.get("note", ""))
    for token in (str(RECOVERY1_RUN_ID), "8001", "VROOM", "solver"):
        if token.lower() not in note.lower():
            raise ProposalError(f"consumed recovery1 provenance missing token {token!r}")


def validate_vroom_correction(executor: Path, reference_runner: Path, grid: Path) -> None:
    text = executor.read_text(encoding="utf-8")
    for token in ("8001", "full-vroom-output-8001-node", "TRANSPORT_GRID_NM", "COMPARISON_NODES_NM", "scientificRole"):
        if token not in text:
            raise ProposalError(f"recovery2 executor missing VROOM structural token {token}")
    if "derive_channels" in text or "evaluatePointSourceVisibility" in text:
        raise ProposalError("recovery2 executor acquired forbidden scientific analysis")
    ref = reference_runner.read_text(encoding="utf-8")
    if "def parse_spectrum(path):" not in ref or "for line in path.read_text" not in ref or "for n in NODES" not in ref:
        raise ProposalError("reference-vroom full-spectrum diagnostic-node parser changed")
    expected_grid = [380,470,480,490,500,510,520,530,540,560,580,590,600,610,640,660,780]
    actual = [int(x) for x in grid.read_text(encoding="utf-8").split()]
    if actual != expected_grid:
        raise ProposalError(f"reference-vroom transport grid changed: {actual}")


def build(root: Path) -> dict[str, Any]:
    root = root.resolve()
    require_ancestor(root, CONSUMED_RECOVERY1_MAIN_SHA)
    paths = {k: root / p for k, p in PATHS.items()}
    for key, path in paths.items():
        if not path.is_file():
            raise ProposalError(f"missing {key}: {path}")
    gate = load(paths["gate"])
    validate_disabled_gate(gate)
    validate_source_manifest(paths["sourceManifest"])
    validate_consumed_recovery1(paths["consumedRecovery1Gate"])
    validate_vroom_correction(paths["recovery2Executor"], paths["referenceVroomRunner"], paths["referenceVroomGrid"])
    if EXPECTED_RUN_NAME not in paths["workflow"].read_text(encoding="utf-8"):
        raise ProposalError("recovery2 workflow run-name is not exact duplicate-audit marker")
    audit_text = paths["duplicateRunAudit"].read_text(encoding="utf-8")
    if 'TITLE_PREFIX = "MYSTIC batch v1 "' not in audit_text:
        raise ProposalError("duplicate-run audit title contract changed")
    head = git(root, "rev-parse", "HEAD")
    proposed = {
        **gate,
        "enabled": True,
        "infrastructureExecution": True,
        "executionKey": EXECUTION_KEY,
        "batchId": BATCH_ID,
        "sourceSmokeManifestRawSha256": sha256(paths["sourceManifest"]),
        "sourceSmokeAdapterRawSha256": sha256(paths["sourceAdapter"]),
        "recovery2SmokeExecutorRawSha256": sha256(paths["recovery2Executor"]),
        "consumedRecovery1GateRawSha256": sha256(paths["consumedRecovery1Gate"]),
        "referenceVroomRunnerRawSha256": sha256(paths["referenceVroomRunner"]),
        "referenceVroomGridRawSha256": sha256(paths["referenceVroomGrid"]),
        "duplicateRunAuditRawSha256": sha256(paths["duplicateRunAudit"]),
        "executionGuardRawSha256": sha256(paths["guard"]),
        "executionWorkflowRawSha256": sha256(paths["workflow"]),
        "runtimeLockRawSha256": sha256(paths["runtimeLock"]),
        "runtimeProbeRawSha256": sha256(paths["runtimeProbe"]),
        "exactGateParentCommit": head,
        "exactGateCommit": None,
        "smokeOrdinal": SMOKE_ORDINAL,
        "consumed": False,
        "note": "Infrastructure-only recovery2 gate proposal after run 33009947410 proved both MYSTIC solvers exit 0 but exposed a false 17-row VROOM structural assertion. Recovery2 keeps the exact same two source smoke cases and corrects only VROOM output interpretation to a full 8001-row spectrum containing the frozen transport/comparison nodes. Scientific use remains prohibited.",
    }
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "PROPOSAL_ONLY_GATE_DISABLED_IN_REPOSITORY",
        "executionEnabledByProposal": False,
        "sourceCommit": head,
        "recovery1RunId": RECOVERY1_RUN_ID,
        "proposedGate": proposed,
        "boundary": "proposal only; no uvspec, MYSTIC, scientific analysis, scientific use, or production permission",
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repository-root", type=Path, default=Path("."))
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    try:
        result = build(args.repository_root)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"schemaVersion": 1, "stageId": STAGE_ID, "status": "REFUSED", "reason": str(exc)}, indent=2, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
