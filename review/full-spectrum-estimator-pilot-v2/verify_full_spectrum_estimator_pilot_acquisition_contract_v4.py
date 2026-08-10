#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def canon(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def raw(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def verify(root: Path) -> dict[str, Any]:
    execution_path = root / "full-spectrum-estimator-pilot-execution-manifest-v4.json"
    renderer_path = root / "rendered-review-v5" / "renderer-review-report.json"
    contract_path = root / "full-spectrum-estimator-pilot-acquisition-contract-v4.json"
    execution = load(execution_path)
    renderer = load(renderer_path)
    contract = load(contract_path)
    if contract.get("contractSha256") != canon({k: v for k, v in contract.items() if k != "contractSha256"}):
        raise ValueError("acquisition contract canonical self-hash mismatch")
    if contract.get("executionManifestSha256") != execution.get("manifestSha256") or contract.get("executionManifestRawSha256") != raw(execution_path):
        raise ValueError("acquisition contract execution-manifest binding drift")
    if contract.get("rendererReportSelfHash") != renderer.get("reportSha256") or contract.get("rendererReportRawSha256") != raw(renderer_path):
        raise ValueError("acquisition contract renderer binding drift")
    expected = contract.get("expectedArtifacts")
    if not isinstance(expected, list) or len(expected) != 44 or contract.get("expectedArtifactCount") != 44:
        raise ValueError("acquisition artifact count drift")
    if contract.get("expectedArtifactsCanonicalSha256") != canon(expected):
        raise ValueError("acquisition expected-artifact canonical hash drift")
    by_case = {row["caseId"]: row for row in renderer.get("cases", [])}
    exec_by_case = {row["caseId"]: row for row in execution.get("cases", [])}
    if set(by_case) != set(exec_by_case) or len(by_case) != 44:
        raise ValueError("renderer/execution case universe drift")
    for row in expected:
        cid = row.get("caseId")
        if cid not in by_case or cid not in exec_by_case:
            raise ValueError(f"unknown acquisition case: {cid}")
        rendered = by_case[cid]
        case = exec_by_case[cid]
        if row.get("artifactName") != f"full-spectrum-estimator-pilot-v2-case-{cid}":
            raise ValueError(f"artifact name drift: {cid}")
        if row.get("reviewedInputResolvedSha256") != rendered.get("inputResolvedReviewSha256") or row.get("reviewedInputTemplateSha256") != rendered.get("inputTemplateSha256"):
            raise ValueError(f"reviewed input hash drift: {cid}")
        if row.get("historicalPhysicalFingerprintSha256") != rendered.get("physicalFingerprintSha256"):
            raise ValueError(f"physical fingerprint drift: {cid}")
        members = execution["artifactContract"]["requiredMembersByMethod"][case["method"]]
        if row.get("requiredMemberBasenames") != members or row.get("requiredMemberBasenamesSha256") != canon(members):
            raise ValueError(f"artifact member contract drift: {cid}")
    for key in ("authorizationPermitted", "scientificExecutionAuthorized", "solverExecutionPerformed"):
        if contract.get(key) is not False:
            raise ValueError(f"acquisition boundary unexpectedly open: {key}")
    opening = contract.get("resultOpeningBoundary", {})
    if any(opening.get(key) is not False for key in ("pilotResultsOpened", "artifactBytesOpened", "modelFittingAuthorized", "holdoutOpeningAuthorized", "tier2Authorized", "productionAuthorization")):
        raise ValueError("result-opening boundary unexpectedly open")
    return {"status": "PASSED", "contractSha256": contract["contractSha256"], "artifactCount": 44}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.root.resolve()), indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "REFUSED", "reason": str(exc)}, indent=2, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
