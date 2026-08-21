from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


class TransportAuthorizationRefusal(RuntimeError):
    pass


def raw_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise TransportAuthorizationRefusal(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def validate_transport_contract(repository_root: Path, authorization: dict[str, Any]) -> dict[str, Any]:
    stage = repository_root / "experiments/aerosol-optical-property-sensitivity-v1"
    contract_path = stage / "transport-contract.v1.json"
    contract = json.loads(contract_path.read_text())
    if contract.get("stageId") != "aerosol-optical-property-sensitivity-v1-transport-contract":
        raise TransportAuthorizationRefusal("transport contract stage drift")
    if contract.get("status") != "FROZEN_TRANSPORT_REVIEW_NOT_AUTHORIZATION":
        raise TransportAuthorizationRefusal("transport contract status drift")
    if authorization.get("transportContractRawSha256") != raw_sha(contract_path):
        raise TransportAuthorizationRefusal("authorization transport-contract raw hash drift")
    if contract.get("reviewPackageMainSha") != authorization.get("reviewPackageMainSha"):
        raise TransportAuthorizationRefusal("transport/review-package main binding drift")
    if any(contract.get(key) is not False for key in (
        "scientificOrdinalAllocated", "authorizationCreated", "dispatchCreated",
        "scientificExecutionAuthorized", "solverExecutionAuthorized", "resultOpeningAuthorized",
    )):
        raise TransportAuthorizationRefusal("transport review contract crossed execution boundary")
    bindings = contract.get("gitBlobBindings")
    if not isinstance(bindings, dict) or not bindings:
        raise TransportAuthorizationRefusal("transport contract missing Git blob bindings")
    for rel, expected in sorted(bindings.items()):
        path = repository_root / rel
        if not path.is_file():
            raise TransportAuthorizationRefusal(f"transport-bound path missing: {rel}")
        if git_blob_sha1(path) != expected:
            raise TransportAuthorizationRefusal(f"transport-bound path drift: {rel}")
    return contract


def validate_enabled_document(
    repository_root: Path,
    authorization: dict[str, Any],
    live_main: str,
    paths: dict[str, Path],
    seed_proof: dict[str, Any],
) -> dict[str, Any]:
    contract = validate_transport_contract(repository_root, authorization)
    frozen_guard = load("aops_frozen_authorization_guard_for_transport", paths["authorizationGuard"])
    frozen_guard.validate_enabled_document(authorization, live_main, paths, seed_proof)
    if authorization.get("transportContractRawSha256") != raw_sha(repository_root / "experiments/aerosol-optical-property-sensitivity-v1/transport-contract.v1.json"):
        raise TransportAuthorizationRefusal("transport contract binding drift")
    return contract
