#!/usr/bin/env python3
"""Strict review-only authorization gate for ASIV matched stellar transport.

This module does not authorize scientific execution and exposes no execution CLI.
It exists to make a future separately reviewed one-file authorization bind all
scientifically material bytes and contracts before delegating to the already
reviewed one-case deterministic transport.

The future authorization must bind, at minimum:
- this gate and the exact transport bytes;
- the prefrozen render candidate bytes;
- the exact complete-set validation assembler bytes;
- the execution contract bytes;
- the frozen runtime identity;
- the frozen Pickles/Johnson-V photometric assets;
- the per-family acceptance gates and exact case universe.

Pandora remains closed, native MYSTIC-STATE-0081 remains non-renderable, and
production activation remains forbidden.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any, Callable

HERE = Path(__file__).resolve().parent
TRANSPORT_PATH = HERE / "execution_transport_review.py"
VALIDATOR_PATH = HERE / "assemble_validate_matched_stellar_v1.py"
CONTRACT_PATH = HERE / "EXECUTION_TRANSPORT_CONTRACT.review.json"
CANDIDATE_PATH = HERE / "execution_candidate.py"

EXPECTED_TRANSPORT_GIT_BLOB_SHA1 = "2bfb94758e048868aa0a6009a654e0805af35f0a"
EXPECTED_VALIDATOR_GIT_BLOB_SHA1 = "9492ca0297136654bdacc81bf0fa2c90d63108b9"
EXPECTED_CANDIDATE_GIT_BLOB_SHA1 = "ec433aa3a594311738a6f6aa2b339a7e33d43447"


class AuthorizationGateRefusal(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AuthorizationGateRefusal(f"cannot load bound module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_bound_transport():
    if git_blob_sha1(TRANSPORT_PATH) != EXPECTED_TRANSPORT_GIT_BLOB_SHA1:
        raise AuthorizationGateRefusal("execution transport Git blob drift")
    return _load_module(TRANSPORT_PATH, "asiv_matched_stellar_bound_execution_transport")


def validate_bound_scientific_sources() -> None:
    if git_blob_sha1(VALIDATOR_PATH) != EXPECTED_VALIDATOR_GIT_BLOB_SHA1:
        raise AuthorizationGateRefusal("complete-set validation assembler Git blob drift")
    if git_blob_sha1(CANDIDATE_PATH) != EXPECTED_CANDIDATE_GIT_BLOB_SHA1:
        raise AuthorizationGateRefusal("prefrozen render candidate Git blob drift")
    load_bound_transport()


def current_authorization_binding() -> dict[str, str]:
    validate_bound_scientific_sources()
    transport = load_bound_transport()
    transport_binding = transport.current_transport_binding()
    return {
        "executionAuthorizationGateSha256": sha256_file(Path(__file__).resolve()),
        "executionAuthorizationGateGitBlobSha1": git_blob_sha1(Path(__file__).resolve()),
        "executionTransportSha256": transport_binding["executionTransportSha256"],
        "executionTransportGitBlobSha1": transport_binding["executionTransportGitBlobSha1"],
        "executionCandidateSha256": transport_binding["executionCandidateSha256"],
        "executionCandidateGitBlobSha1": transport_binding["executionCandidateGitBlobSha1"],
        "executionContractSha256": transport_binding["executionContractSha256"],
        "executionContractGitBlobSha1": transport_binding["executionContractGitBlobSha1"],
        "validationAssemblerSha256": sha256_file(VALIDATOR_PATH),
        "validationAssemblerGitBlobSha1": git_blob_sha1(VALIDATOR_PATH),
    }


def _load_contract() -> dict[str, Any]:
    payload = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if payload.get("schemaVersion") != 1:
        raise AuthorizationGateRefusal("execution contract schema drift")
    if payload.get("stageId") != "asiv-matched-stellar-transport-v1-execution-transport":
        raise AuthorizationGateRefusal("execution contract stage drift")
    if payload.get("status") != "FROZEN_REVIEW_ONLY_EXECUTION_TRANSPORT_NO_AUTHORIZATION":
        raise AuthorizationGateRefusal("review execution contract unexpectedly changed authorization state")
    return payload


def validate_strict_authorization(document: dict[str, Any]) -> None:
    if not isinstance(document, dict):
        raise AuthorizationGateRefusal("authorization must be an object")
    transport = load_bound_transport()
    validate_bound_scientific_sources()
    contract = _load_contract()

    expected_flags = {
        "scientificExecutionAuthorized": True,
        "solverExecutionAuthorized": True,
        "resultOpeningAuthorized": False,
        "productionActivationAuthorized": False,
        "pandoraHoldoutAccessAllowed": False,
        "starsvisibilityMutationAuthorized": False,
        "nativeRebuildAuthorized": False,
        "retryPermitted": False,
        "resumePermitted": False,
        "githubRerunPermitted": False,
    }
    if document.get("schemaVersion") != 1:
        raise AuthorizationGateRefusal("authorization schema drift")
    if document.get("stageId") != "asiv-matched-stellar-transport-v1-execution-authorization":
        raise AuthorizationGateRefusal("authorization stage drift")
    if document.get("status") != "AUTHORIZED_ONE_SHOT_SCIENTIFIC_EXECUTION":
        raise AuthorizationGateRefusal("positive one-shot authorization is absent")
    for key, expected in expected_flags.items():
        if document.get(key) is not expected:
            raise AuthorizationGateRefusal(f"authorization flag mismatch: {key}")

    if tuple(document.get("families", ())) != tuple(transport.NON_NATIVE_FAMILIES):
        raise AuthorizationGateRefusal("authorization aerosol-family universe drift")
    if document.get("nativeState") != transport.NATIVE_STATE or document.get("nativeRenderable") is not False:
        raise AuthorizationGateRefusal("authorization must keep native comparator non-renderable")

    if document.get("sourceBindings") != current_authorization_binding():
        raise AuthorizationGateRefusal("authorization does not bind exact gate/transport/validator bytes")
    if document.get("runtimeIdentity") != contract.get("runtimeIdentity"):
        raise AuthorizationGateRefusal("authorization runtime identity drift")
    if document.get("photometricValidationAssets") != contract.get("photometricValidationAssets"):
        raise AuthorizationGateRefusal("authorization photometric-validation asset contract drift")
    if document.get("validationAcceptance") != contract.get("acceptance"):
        raise AuthorizationGateRefusal("authorization per-family acceptance gates drift")
    if document.get("caseUniverse") != contract.get("caseUniverse"):
        raise AuthorizationGateRefusal("authorization case universe drift")


def execute_one_case_strict(*, authorization: dict[str, Any], runtime_report: dict[str, Any],
                            family: str, target_altitude_deg: float, observer_elevation_m: float,
                            aod550: float,
                            process_runner: Callable[..., dict[str, Any]] | None = None) -> dict[str, Any]:
    """Delegate one case only after strict external authorization validation.

    This is intentionally not reachable from this module's CLI. A future workflow
    must be separately reviewed and must load a one-file authorization whose exact
    bytes satisfy validate_strict_authorization().
    """
    validate_strict_authorization(authorization)
    transport = load_bound_transport()
    delegated = dict(authorization)
    delegated["sourceBindings"] = transport.current_transport_binding()
    return transport.execute_one_case(
        authorization=delegated,
        runtime_report=runtime_report,
        family=family,
        target_altitude_deg=target_altitude_deg,
        observer_elevation_m=observer_elevation_m,
        aod550=aod550,
        process_runner=process_runner,
    )


def main() -> int:
    print(json.dumps({
        "status": "REVIEW_ONLY_STRICT_AUTHORIZATION_GATE_NO_EXECUTION_CLI",
        "scientificExecutionAuthorized": False,
        "solverExecutionAuthorized": False,
        "resultOpeningAuthorized": False,
        "productionActivationAuthorized": False,
        "pandoraHoldoutAccessAllowed": False,
        "nativeRebuildAuthorized": False,
        "currentAuthorizationBinding": current_authorization_binding(),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
