from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Callable

STAGE = "aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3"
EXPECTED_GUARD_STATUS = "EXACT_ONE_USE_AVPS_V2_POSTCONSUMPTION_RECOVERY3_DISPATCH_AUTHORIZED"
EXPECTED_AUTH_HEAD = "dd3a4c692af505389e9feb1e5f5480fa389110a3"
EXPECTED_AUTH_PR = 718
EXPECTED_ORDINAL = 44
EXPECTED_EXECUTION_KEY = "aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3:numerical:44"
EXPECTED_AUTH_BRANCH = "authorization/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3-ordinal-44"
EXPECTED_DISPATCH_BRANCH = "dispatch/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3-ordinal-44"
EXPECTED_SEED_CANONICAL = "d2817b1ea4f2bdc8cb1842e565b099b015e4e28c5874482629fadc450069d9bf"
EXPECTED_FOUR_ALIAS_TREE = "5e1814dd36cf861fd85477a97607299248f8272268df7bf428d31bbb6aa4354a"
EXPECTED_UVSPEC = "2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3"
EXPECTED_AFGL = "dab26290ed81c762ed0c607e5dc2d53393c1462a0c3a528bc5e3f5935191cfb5"

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE_EXECUTOR_PATH = ROOT / "review/aerosol-vertical-profile-sensitivity-v2-executor-parity-v1/executor.py"
BASE_ADAPTER_PATH = ROOT / "review/aerosol-vertical-profile-sensitivity-v2-control-v1/adapter.py"
ADAPTER_PATH = Path("review/avps-v2-recovery3-ordinal44-runtime-identity-bridge-v1/adapter_bridge.py")
CONTRACT_PATH = Path("review/avps-v2-recovery3-ordinal44-runtime-identity-bridge-v1/execution-contract.review.json")
RUNTIME_STAGE_PATH = Path("review/aerosol-vertical-profile-sensitivity-v2-control-v1/runtime_stage.py")
PROCESS_RUNNER_PATH = Path("experiments/aerosol-family-challenge-v2-r8-timeout-recovery-v1/execution-candidate/process_runner.py")
DERIVED_CHANNELS_PATH = Path("experiments/aerosol-family-challenge-v2-r8/derived_channels.py")
WAVELENGTH_GRID_PATH = Path("experiments/aerosol-family-challenge-v2-r8/wavelength-grid-1nm.dat")

EXPECTED_STABLE_BLOBS = {
    BASE_EXECUTOR_PATH.relative_to(ROOT): "bb1e4276d6383127a6b7e820fc2568d87d5de4b0",
    BASE_ADAPTER_PATH.relative_to(ROOT): "c245eac2fe5b5d026e46ec4253bc377c5fde97ec",
    RUNTIME_STAGE_PATH: "0d3ac10f3ef7d22f0205854233a6c37cbba03f7c",
    PROCESS_RUNNER_PATH: "e23d724e99c1cf9b0b862f8ab48356bd3d9bc56c",
    DERIVED_CHANNELS_PATH: "ccfd04d4c21188966351f4257e92893d7ce340c7",
    WAVELENGTH_GRID_PATH: "3bb3db96580d555ef758f57cabd6cac55b61cebb",
}


class BridgeRefusal(RuntimeError):
    pass


def git_blob_sha1(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def validate_bound_sources(repository_root: Path) -> None:
    for relative, expected in EXPECTED_STABLE_BLOBS.items():
        path = repository_root / relative
        if not path.is_file() or git_blob_sha1(path) != expected:
            raise BridgeRefusal(f"stable AVPS source byte drift: {relative}")
    for relative in (ADAPTER_PATH, CONTRACT_PATH):
        if not (repository_root / relative).is_file():
            raise BridgeRefusal(f"recovery3 bridge source missing: {relative}")


def load_contract(repository_root: Path) -> dict[str, Any]:
    contract = json.loads((repository_root / CONTRACT_PATH).read_text())
    if contract.get("status") != "REVIEW_ONLY_RECOVERY3_RUNTIME_IDENTITY_BRIDGE_FROZEN_ZERO_RUNTIME":
        raise BridgeRefusal("recovery3 bridge contract status drift")
    identity = contract.get("scientificIdentity") or {}
    if identity.get("stageId") != STAGE or identity.get("scientificOrdinal") != EXPECTED_ORDINAL or identity.get("executionKey") != EXPECTED_EXECUTION_KEY:
        raise BridgeRefusal("recovery3 bridge contract identity drift")
    if identity.get("authorizationHead") != EXPECTED_AUTH_HEAD or identity.get("authorizationPr") != EXPECTED_AUTH_PR:
        raise BridgeRefusal("recovery3 bridge contract authorization drift")
    design = contract.get("caseDesign") or {}
    if (design.get("expectedCaseCount"), design.get("expectedGroupCount"), design.get("expectedStatesPerGroup"), design.get("photonHistoriesPerCase")) != (360, 72, 5, 20_000_000):
        raise BridgeRefusal("recovery3 bridge case design drift")
    if design.get("attemptRequired") != 1 or design.get("retryPermitted") is not False or design.get("resumePermitted") is not False or design.get("githubRerunPermitted") is not False:
        raise BridgeRefusal("recovery3 bridge one-shot boundary drift")
    boundaries = contract.get("boundaries") or {}
    if boundaries.get("scientificDesignChanged") is not False or boundaries.get("seedIdentityChanged") is not False or boundaries.get("authorizationChanged") is not False:
        raise BridgeRefusal("recovery3 bridge changed frozen science/identity")
    if boundaries.get("snapshotFenceReleaseBarrierStillRequired") is not True:
        raise BridgeRefusal("recovery3 bridge dropped snapshot release barrier requirement")
    return contract


def validate_authorization(auth: dict[str, Any]) -> None:
    if auth.get("stageId") != STAGE or auth.get("status") != "AUTHORIZED_POSTCONSUMPTION_RECOVERY3_PENDING_SEPARATE_ALLOCATION_AND_DISPATCH":
        raise BridgeRefusal("recovery3 authorization stage/status drift")
    if auth.get("scientificOrdinal") != EXPECTED_ORDINAL or auth.get("executionKey") != EXPECTED_EXECUTION_KEY:
        raise BridgeRefusal("recovery3 authorization identity drift")
    if auth.get("authorizationBranch") != EXPECTED_AUTH_BRANCH or auth.get("dispatchBranch") != EXPECTED_DISPATCH_BRANCH:
        raise BridgeRefusal("recovery3 authorization branch drift")
    if auth.get("candidateSeedCanonicalSha256") != EXPECTED_SEED_CANONICAL or auth.get("candidateSeedCount") != 72:
        raise BridgeRefusal("recovery3 authorization seed identity drift")
    if auth.get("caseCount") != 360 or auth.get("commonRandomNumberGroupCount") != 72 or auth.get("statesPerGroup") != 5 or auth.get("photonHistoriesPerCase") != 20_000_000:
        raise BridgeRefusal("recovery3 authorization frozen case design drift")
    if auth.get("scientificExecutionAuthorized") is not True or auth.get("solverExecutionAuthorized") is not True or auth.get("snapshotFenceReleaseBarrierRequired") is not True:
        raise BridgeRefusal("recovery3 one-shot execution/barrier authorization drift")
    for key in ("dispatchAuthorized", "automaticDispatch", "resultOpeningAuthorized", "levelBOpeningAuthorized", "productionAuthorized", "protectedHoldoutOpeningAuthorized", "taylorOrJerusalemFitAuthorized"):
        if auth.get(key) is not False:
            raise BridgeRefusal(f"recovery3 authorization crossed closed boundary: {key}")
    for key in ("githubRerunAllowed", "retryAllowed", "resumeAllowed"):
        if auth.get(key) is not False:
            raise BridgeRefusal(f"recovery3 one-shot boundary weakened: {key}")


def validate_guard(guard: dict[str, Any]) -> None:
    if guard.get("status") != EXPECTED_GUARD_STATUS:
        raise BridgeRefusal("recovery3 one-use guard status drift")
    if guard.get("scientificOrdinal") != EXPECTED_ORDINAL or guard.get("executionKey") != EXPECTED_EXECUTION_KEY:
        raise BridgeRefusal("recovery3 guard identity drift")
    if guard.get("authorizationHead") != EXPECTED_AUTH_HEAD or guard.get("authorizationPr") != EXPECTED_AUTH_PR:
        raise BridgeRefusal("recovery3 guard authorization drift")
    if guard.get("dispatchBranch") != EXPECTED_DISPATCH_BRANCH or guard.get("dispatchBranchHeadSha") != EXPECTED_AUTH_HEAD:
        raise BridgeRefusal("recovery3 guard dispatch drift")
    run_id = guard.get("workflowRunId")
    if isinstance(run_id, bool) or not isinstance(run_id, int) or run_id <= 0 or guard.get("workflowRunAttempt") != 1:
        raise BridgeRefusal("recovery3 guard workflow identity drift")
    if guard.get("allocationMarkerCount") != 1 or guard.get("consumedMarkerCount") != 1:
        raise BridgeRefusal("recovery3 guard marker cardinality drift")
    if guard.get("candidateSeedCanonicalSha256") != EXPECTED_SEED_CANONICAL or guard.get("preSolverRepositoryGlobalSeedRecheckPassed") is not True:
        raise BridgeRefusal("recovery3 guard seed recheck drift")
    if guard.get("fourAliasDataTreeSha256") != EXPECTED_FOUR_ALIAS_TREE or guard.get("solverExecutionPermittedNow") is not True:
        raise BridgeRefusal("recovery3 guard runtime permission drift")
    if guard.get("githubRerun") is not False or guard.get("retryAllowed") is not False or guard.get("resumeAllowed") is not False:
        raise BridgeRefusal("recovery3 guard one-shot boundary weakened")


def _load_base():
    if not BASE_EXECUTOR_PATH.is_file() or git_blob_sha1(BASE_EXECUTOR_PATH) != "bb1e4276d6383127a6b7e820fc2568d87d5de4b0":
        raise BridgeRefusal("base executor byte drift")
    spec = importlib.util.spec_from_file_location("avps_v2_recovery3_bridge_base_executor", BASE_EXECUTOR_PATH)
    if spec is None or spec.loader is None:
        raise BridgeRefusal("cannot load base executor")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.STAGE = STAGE
    module.EXPECTED_GUARD_STATUS = EXPECTED_GUARD_STATUS
    module.EXPECTED_AUTH_HEAD = EXPECTED_AUTH_HEAD
    module.EXPECTED_AUTH_PR = EXPECTED_AUTH_PR
    module.EXPECTED_ORDINAL = EXPECTED_ORDINAL
    module.EXPECTED_EXECUTION_KEY = EXPECTED_EXECUTION_KEY
    module.EXPECTED_SEED_CANONICAL = EXPECTED_SEED_CANONICAL
    module.CONTRACT_PATH = CONTRACT_PATH
    module.ADAPTER_PATH = ADAPTER_PATH
    module.validate_bound_sources = validate_bound_sources
    module.load_contract = load_contract
    module.validate_authorization = validate_authorization
    module.validate_guard = validate_guard
    return module


def execute_case(repository_root: Path, authorization_path: Path, guard_report_path: Path, runtime_report_path: Path, profile_dir: Path, case_id: str, data_dir: Path, output_root: Path, uvspec: Path, *, allow_execution: bool = False, runner: Callable[..., dict[str, Any]] | None = None) -> dict[str, Any]:
    return _load_base().execute_case(repository_root, authorization_path, guard_report_path, runtime_report_path, profile_dir, case_id, data_dir, output_root, uvspec, allow_execution=allow_execution, runner=runner)


def review_summary(repository_root: Path, auth: dict[str, Any], guard: dict[str, Any]) -> dict[str, Any]:
    validate_bound_sources(repository_root)
    load_contract(repository_root)
    validate_authorization(auth)
    validate_guard(guard)
    return {
        "status": "PASS_RECOVERY3_ORDINAL44_EXECUTOR_IDENTITY_BRIDGE_ZERO_RUNTIME",
        "scientificOrdinal": EXPECTED_ORDINAL,
        "executionKey": EXPECTED_EXECUTION_KEY,
        "authorizationHead": EXPECTED_AUTH_HEAD,
        "authorizationPr": EXPECTED_AUTH_PR,
        "scientificRuntime": False,
        "solverExecution": False,
        "resultOpening": False,
    }
