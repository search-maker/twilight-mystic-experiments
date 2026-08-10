#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def canon(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def verify(root: Path) -> dict[str, Any]:
    protocol = load(root / "full-spectrum-estimator-pilot-preregistration-v2.json")
    manifest = load(root / "full-spectrum-estimator-pilot-execution-manifest-v4.json")
    expected_hash = manifest.get("manifestSha256")
    if expected_hash != canon({k: v for k, v in manifest.items() if k != "manifestSha256"}):
        raise ValueError("execution manifest canonical self-hash mismatch")
    if manifest.get("protocolId") != protocol.get("protocolId") or manifest.get("protocolSha256") != protocol.get("protocolSha256"):
        raise ValueError("execution manifest protocol binding drift")
    if manifest.get("caseCount") != 44 or len(manifest.get("cases", [])) != 44:
        raise ValueError("execution manifest case count drift")
    if manifest.get("configuredPhotonHistoriesSum") != 5_600_000_000:
        raise ValueError("execution manifest photon budget drift")
    cases = manifest["cases"]
    if len({row.get("caseId") for row in cases}) != 44:
        raise ValueError("execution manifest duplicate case id")
    if len({row.get("seed") for row in cases}) != 44:
        raise ValueError("execution manifest duplicate seed")
    protocol_cases = {row["caseId"]: row for row in protocol.get("cases", [])}
    if set(protocol_cases) != {row["caseId"] for row in cases}:
        raise ValueError("execution manifest case universe drift")
    for row in cases:
        source = protocol_cases[row["caseId"]]
        for key in ("geometryId", "method", "replicate", "seed", "photonHistories"):
            if row.get(key) != source.get(key):
                raise ValueError(f"execution manifest acquisition binding drift: {row['caseId']}.{key}")
        if source.get("importanceCenterNm") != row.get("numericalMethod", {}).get("mc_spectral_is_nm"):
            raise ValueError(f"execution manifest importance center drift: {row['caseId']}")
    boundary = manifest.get("executionBoundary", {})
    for key in ("authorizationEnabled", "dispatchPerformed", "fittingAuthorized", "holdoutOpeningAuthorized", "productionAuthorization", "scientificExecutionPerformed"):
        if boundary.get(key) is not False:
            raise ValueError(f"execution boundary unexpectedly open: {key}")
    contract = manifest.get("artifactContract", {})
    method_members = contract.get("requiredMembersByMethod", {})
    if set(method_members) != {"alis-alt-importance", "reference-vroom-1nm"}:
        raise ValueError("method-specific artifact contract drift")
    if "wavelength-grid-1nm.dat" not in method_members["reference-vroom-1nm"]:
        raise ValueError("VROOM grid artifact member missing")
    expected_names = [f"full-spectrum-estimator-pilot-v2-case-{row['caseId']}" for row in cases]
    if contract.get("expectedArtifactNames") != expected_names or contract.get("expectedArtifactNamesSha256") != canon(expected_names):
        raise ValueError("expected artifact-name universe drift")
    return {"status": "PASSED", "manifestSha256": expected_hash, "caseCount": 44, "configuredPhotonHistoriesSum": 5_600_000_000}


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
