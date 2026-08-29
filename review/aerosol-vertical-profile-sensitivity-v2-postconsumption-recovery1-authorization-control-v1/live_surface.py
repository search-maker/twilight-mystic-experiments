from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
GENERIC_SCANNER = ROOT / "experiments/aerosol-family-challenge-v2/repository_global_seed_scan.py"
GENERIC_SCANNER_BLOB = "4c6d704fa24228284780bcb1dd7c52537b4c5b0d"
R8_DIR = ROOT / "experiments/aerosol-family-challenge-v2-r8/execution-candidate"
R8_FRESHNESS_BLOB = "732f803b5261e7986582dd7e0d69a66f70432b1e"
R8_ORDINAL_BLOB = "7ca8efd17ae9e7ec2baa32fe935e5173ca6d173f"
STAGE = "aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery1"
CONSUMED_ORDINAL = 41
ORDINAL = 42
AUTH_BRANCH = f"authorization/{STAGE}-ordinal-{ORDINAL}"
DISPATCH_BRANCH = f"dispatch/{STAGE}-ordinal-{ORDINAL}"
SHA40 = re.compile(r"^[0-9a-f]{40}$")


class Refusal(RuntimeError):
    pass


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise Refusal(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def bound_modules():
    if git_blob_sha1(GENERIC_SCANNER) != GENERIC_SCANNER_BLOB:
        raise Refusal("repository-global scanner byte drift")
    freshness_path = R8_DIR / "freshness.py"
    ordinal_path = R8_DIR / "preauthorization_ordinal.py"
    if git_blob_sha1(freshness_path) != R8_FRESHNESS_BLOB:
        raise Refusal("R8 freshness parser byte drift")
    if git_blob_sha1(ordinal_path) != R8_ORDINAL_BLOB:
        raise Refusal("R8 ordinal parser byte drift")
    scanner = load_module("avps_v2_recovery1_auth_surface_scanner", GENERIC_SCANNER)
    freshness = load_module("avps_v2_recovery1_auth_surface_freshness", freshness_path)
    old = sys.modules.get("freshness")
    sys.modules["freshness"] = freshness
    try:
        ordinal = load_module("avps_v2_recovery1_auth_surface_ordinal", ordinal_path)
    finally:
        if old is None:
            sys.modules.pop("freshness", None)
        else:
            sys.modules["freshness"] = old
    return scanner, ordinal


def exact_markers(payload: dict[str, Any], ordinal: int) -> tuple[bool, bool]:
    alloc_prefix = f"ORDINAL{ordinal}_"
    allocation = False
    consumed = False
    for row in payload.get("issue60Comments", []):
        body = str(row.get("body") or "").strip().upper()
        if body.startswith(alloc_prefix) and "_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED" in body:
            allocation = True
        if body == f"ORDINAL{ordinal}_AVPS_V2_POSTCONSUMPTION_RECOVERY1_DISPATCH_CONSUMED" or (
            body.startswith(alloc_prefix) and body.endswith("_DISPATCH_CONSUMED")
        ):
            consumed = True
    return allocation, consumed


def control_surface(payload: dict[str, Any], ordinal_module, current_run_id: int | None) -> dict[str, Any]:
    observations = ordinal_module.authoritative_global_ordinal_observations(payload, current_run_id=current_run_id)
    if not observations:
        raise Refusal("no authoritative global ordinal observations")
    occupied = sorted({int(row["ordinal"]) for row in observations})
    consumed = sorted({int(row["ordinal"]) for row in observations if row.get("reason") == "exact-consumed-marker"})
    if CONSUMED_ORDINAL not in consumed:
        raise Refusal("ordinal 41 exact consumed marker missing")
    if max(occupied) != CONSUMED_ORDINAL:
        raise Refusal(f"global ordinal max changed: {max(occupied)}")
    branches = {str(row.get("name") or "") for row in payload.get("branches", [])}
    allocation, consumed_marker = exact_markers(payload, ORDINAL)
    if AUTH_BRANCH in branches or DISPATCH_BRANCH in branches or allocation or consumed_marker:
        raise Refusal("proposed ordinal-42 recovery identity is no longer free")
    report = {
        "schemaVersion": 1,
        "status": "PASS_RECOVERY1_AUTHORIZATION_CONTROL_LIVE_SURFACE_NOT_ALLOCATED",
        "consumedOrdinal": CONSUMED_ORDINAL,
        "consumedOrdinalsObserved": consumed,
        "occupiedScientificOrdinalsObserved": occupied,
        "occupiedMaxScientificOrdinal": max(occupied),
        "nextAvailableScientificOrdinal": ORDINAL,
        "authorizationBranch": AUTH_BRANCH,
        "dispatchBranch": DISPATCH_BRANCH,
        "authorizationBranchExists": False,
        "dispatchBranchExists": False,
        "allocationMarkerExists": False,
        "consumedMarkerExists": False,
        "scientificOrdinalAllocated": False,
        "ordinalObservationCount": len(observations),
        "ordinalObservationsCanonicalSha256": canonical_sha256(observations),
    }
    return report


def _self_observation(row: dict[str, Any], payload: dict[str, Any], head: str, pr_number: int, current_run_id: int) -> bool:
    surface = row.get("surface")
    identity = str(row.get("id") or "")
    if surface == "branch" and identity == AUTH_BRANCH:
        return True
    if surface == "pull-request" and identity == str(pr_number):
        return True
    if surface == "workflow-run":
        try:
            run_id = int(identity)
        except ValueError:
            return False
        if run_id == current_run_id:
            return True
        for run in payload.get("runs", []):
            if int(run.get("id") or 0) != run_id:
                continue
            return str(run.get("head_branch") or "") == AUTH_BRANCH and str(run.get("head_sha") or "").lower() == head
    return False


def authorization_surface(payload: dict[str, Any], ordinal_module, head: str, pr_number: int, current_run_id: int) -> dict[str, Any]:
    if SHA40.fullmatch(head or "") is None:
        raise Refusal("authorization head malformed")
    observations = ordinal_module.authoritative_global_ordinal_observations(payload, current_run_id=current_run_id)
    branches = [row for row in payload.get("branches", []) if str(row.get("name") or "") == AUTH_BRANCH]
    if len(branches) != 1 or str(((branches[0].get("commit") or {}).get("sha") or "")).lower() != head:
        raise Refusal("authorization branch/head evidence drift")
    if any(str(row.get("name") or "") == DISPATCH_BRANCH for row in payload.get("branches", [])):
        raise Refusal("dispatch branch exists before allocation review")
    allocation, consumed_marker = exact_markers(payload, ORDINAL)
    if allocation or consumed_marker:
        raise Refusal("ordinal-42 allocation/consumption marker already exists")

    nonself = []
    for row in observations:
        value = int(row["ordinal"])
        if value == ORDINAL and _self_observation(row, payload, head, pr_number, current_run_id):
            continue
        nonself.append(row)
    occupied_nonself = sorted({int(row["ordinal"]) for row in nonself})
    if not occupied_nonself or max(occupied_nonself) != CONSUMED_ORDINAL:
        raise Refusal(f"non-self global ordinal max is not 41: {max(occupied_nonself) if occupied_nonself else None}")
    conflicts = [row for row in nonself if int(row["ordinal"]) >= ORDINAL]
    if conflicts:
        raise Refusal(f"non-self ordinal-42+ conflict: {conflicts[:3]}")
    return {
        "schemaVersion": 1,
        "status": "PASS_RECOVERY1_AUTHORIZATION_REVIEW_LIVE_SURFACE_SELF_ONLY_NOT_ALLOCATED",
        "authorizationHead": head,
        "authorizationPrNumber": pr_number,
        "consumedOrdinal": CONSUMED_ORDINAL,
        "nonSelfOccupiedMaxScientificOrdinal": max(occupied_nonself),
        "scientificOrdinal": ORDINAL,
        "authorizationBranch": AUTH_BRANCH,
        "dispatchBranch": DISPATCH_BRANCH,
        "authorizationBranchExistsAtExactHead": True,
        "dispatchBranchExists": False,
        "allocationMarkerExists": False,
        "consumedMarkerExists": False,
        "scientificOrdinalAllocated": False,
        "nonSelfOrdinalObservationCount": len(nonself),
        "nonSelfOrdinalObservationsCanonicalSha256": canonical_sha256(nonself),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--mode", choices=("control", "authorization"), required=True)
    parser.add_argument("--current-run-id", type=int, required=True)
    parser.add_argument("--head")
    parser.add_argument("--pr-number", type=int)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN required")
    scanner, ordinal = bound_modules()
    payload = scanner.collect(args.repository, 60, token)
    if args.mode == "control":
        report = control_surface(payload, ordinal, args.current_run_id)
    else:
        if not args.head or not args.pr_number:
            raise SystemExit("authorization mode requires --head and --pr-number")
        report = authorization_surface(payload, ordinal, args.head, args.pr_number, args.current_run_id)
    report["repositoryGlobalStableContextSha256"] = canonical_sha256({
        "branches": payload.get("branches", []),
        "runs": payload.get("runs", []),
        "pulls": payload.get("pulls", []),
        "artifacts": payload.get("artifacts", []),
        "issue60Comments": payload.get("issue60Comments", []),
    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
