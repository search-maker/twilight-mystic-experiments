#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "jerusalem-tishrei-elevated-site-smoke-v2-recovery1"
BATCH_ID = "jerusalem-tishrei-elevated-site-smoke-v2-recovery1"
EXECUTION_KEY = "jerusalem-tishrei-elevated-site-smoke-v2:infrastructure:2"
SMOKE_ORDINAL = 2
CONSUMED_V2_MAIN_SHA = "3885f7c390653181aa86a428779867469c5b278c"
FAILED_V2_RUN_ID = 33007847279
PACKAGE = Path("experiments/jerusalem-tishrei-elevated-site-smoke-v2-recovery1")
PATHS = {
    "gate": PACKAGE / "gate.smoke-recovery1.json",
    "guard": PACKAGE / "execution_guard.py",
    "workflow": Path(".github/workflows/jerusalem-tishrei-elevated-site-smoke-v2-recovery1.yml"),
    "sourceManifest": Path("experiments/jerusalem-tishrei-elevated-site-smoke-v2/manifest.smoke.json"),
    "sourceAdapter": Path("experiments/jerusalem-tishrei-elevated-site-smoke-v2/adapter.py"),
    "sourceExecutor": Path("experiments/jerusalem-tishrei-elevated-site-smoke-v2/smoke_executor.py"),
    "sourceConsumedV2Gate": Path("experiments/jerusalem-tishrei-elevated-site-smoke-v2/authorization.smoke.json"),
    "duplicateRunAudit": Path("experiments/mystic-batch-v1/duplicate_run_audit.py"),
    "runtimeLock": Path("experiments/mystic-batch-v1/runtime-lock.micromamba.json"),
    "runtimeProbe": Path("experiments/mystic-batch-v1/runtime_probe.py"),
}
EXPECTED_RUN_NAME = "run-name: MYSTIC batch v1 | key=${{ inputs.execution_key }} | auth=${{ inputs.gate_ref }} | ordinal=${{ inputs.smoke_ordinal }}"


class GateProposalError(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise GateProposalError(f"expected JSON object: {path}")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def require_ancestor(root: Path, ancestor: str) -> None:
    result = subprocess.run(["git", "merge-base", "--is-ancestor", ancestor, "HEAD"], cwd=root, check=False)
    if result.returncode != 0:
        raise GateProposalError(f"HEAD does not contain required consumed-v2 checkpoint {ancestor}")


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
        raise GateProposalError(f"recovery gate is not pristine disabled: {stale}")


def validate_consumed_v2(path: Path) -> None:
    a = load(path)
    required = {
        "stageId": "jerusalem-tishrei-elevated-site-smoke-v2",
        "authorized": False,
        "infrastructureExecution": False,
        "scientificExecution": False,
        "scientificDiagnostic": False,
        "scientificUseProhibited": True,
        "consumed": True,
        "executionKey": "jerusalem-tishrei-elevated-site-smoke-v2:infrastructure:1",
        "smokeAuthorizationOrdinal": 1,
        "exactAuthorizationCommit": "3ec2a7bdacb4f00e49f5756ba339338b1e86769c",
    }
    stale = {k: (a.get(k), v) for k, v in required.items() if a.get(k) != v}
    if stale:
        raise GateProposalError(f"source smoke-v2 archive changed: {stale}")
    note = str(a.get("note", ""))
    if str(FAILED_V2_RUN_ID) not in note or "zero" in note.lower() and "solver" not in note.lower():
        raise GateProposalError("source smoke-v2 archive no longer records failed pre-solver run")
    if "display title" not in note and "one-shot" not in note and "duplicate_run_audit" not in note:
        raise GateProposalError("source smoke-v2 archive no longer records run-name/duplicate-audit cause")


def validate_source_smoke(manifest_path: Path) -> None:
    m = load(manifest_path)
    required = {
        "stageId": "jerusalem-tishrei-elevated-site-smoke-v2",
        "infrastructureOnly": True,
        "scientificExecution": False,
        "scientificDiagnostic": False,
        "scientificUseProhibited": True,
        "successDoesNotAuthorizeScientificExecution": True,
    }
    stale = {k: (m.get(k), v) for k, v in required.items() if m.get(k) != v}
    if stale:
        raise GateProposalError(f"source smoke manifest boundary changed: {stale}")
    cases = m.get("cases") or []
    if len(cases) != 2 or sum(int(c.get("photonHistories", 0)) for c in cases) != 20_000:
        raise GateProposalError("source smoke case/photon accounting changed")
    if {c.get("method") for c in cases} != {"reference-vroom", "alis"}:
        raise GateProposalError("source smoke method set changed")


def build(root: Path) -> dict[str, Any]:
    root = root.resolve()
    absolute = {k: root / p for k, p in PATHS.items()}
    for key, path in absolute.items():
        if not path.is_file():
            raise GateProposalError(f"missing {key}: {path}")
    require_ancestor(root, CONSUMED_V2_MAIN_SHA)
    gate = load(absolute["gate"])
    validate_disabled_gate(gate)
    validate_consumed_v2(absolute["sourceConsumedV2Gate"])
    validate_source_smoke(absolute["sourceManifest"])
    workflow_text = absolute["workflow"].read_text(encoding="utf-8")
    if EXPECTED_RUN_NAME not in workflow_text:
        raise GateProposalError("recovery workflow run-name is not the exact duplicate-audit marker template")
    audit_text = absolute["duplicateRunAudit"].read_text(encoding="utf-8")
    if 'TITLE_PREFIX = "MYSTIC batch v1 "' not in audit_text or 'return f"{TITLE_PREFIX}| key={execution_key} | auth={authorization_ref} | ordinal={ordinal}"' not in audit_text:
        raise GateProposalError("duplicate-run audit title contract changed")
    head = git(root, "rev-parse", "HEAD")
    proposed = {
        **gate,
        "enabled": True,
        "infrastructureExecution": True,
        "executionKey": EXECUTION_KEY,
        "batchId": BATCH_ID,
        "sourceSmokeManifestRawSha256": sha256(absolute["sourceManifest"]),
        "sourceSmokeAdapterRawSha256": sha256(absolute["sourceAdapter"]),
        "sourceSmokeExecutorRawSha256": sha256(absolute["sourceExecutor"]),
        "sourceConsumedSmokeV2GateRawSha256": sha256(absolute["sourceConsumedV2Gate"]),
        "duplicateRunAuditRawSha256": sha256(absolute["duplicateRunAudit"]),
        "executionGuardRawSha256": sha256(absolute["guard"]),
        "executionWorkflowRawSha256": sha256(absolute["workflow"]),
        "runtimeLockRawSha256": sha256(absolute["runtimeLock"]),
        "runtimeProbeRawSha256": sha256(absolute["runtimeProbe"]),
        "exactGateParentCommit": head,
        "exactGateCommit": None,
        "smokeOrdinal": SMOKE_ORDINAL,
        "consumed": False,
        "note": "Infrastructure-only recovery gate. Source smoke-v2 ordinal 1 was consumed by run 33007847279 before uvspec because of a run-name/duplicate-audit mismatch. This recovery changes execution governance only: exact same two source smoke inputs, new key/ordinal, exact duplicate-audit run-name. A separate one-purpose gate commit and separate first-attempt workflow_dispatch are still required; smoke output remains scientifically unusable.",
    }
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "PROPOSAL_ONLY_GATE_DISABLED_IN_REPOSITORY",
        "executionEnabledByProposal": False,
        "sourceCommit": head,
        "failedSourceSmokeRunId": FAILED_V2_RUN_ID,
        "proposedGate": proposed,
        "boundary": "proposal only; no uvspec, MYSTIC, scientific execution, scientific use, or production permission",
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
        report = {"schemaVersion": 1, "stageId": STAGE_ID, "status": "REFUSED", "reason": str(exc)}
        print(json.dumps(report, indent=2, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
