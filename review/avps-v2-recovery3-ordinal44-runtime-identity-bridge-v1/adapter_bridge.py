from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

STAGE = "aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3"
EXPECTED_ORDINAL = 44
EXPECTED_EXECUTION_KEY = "aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3:numerical:44"
EXPECTED_AUTH_BRANCH = "authorization/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3-ordinal-44"
EXPECTED_DISPATCH_BRANCH = "dispatch/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3-ordinal-44"
EXPECTED_SEED_CANONICAL = "d2817b1ea4f2bdc8cb1842e565b099b015e4e28c5874482629fadc450069d9bf"
EXPECTED_ROWS_CANONICAL = "b6a519eadacdb99ea53c52d483c8acfeba05829643cb988de21682a53fc47896"
EXPECTED_FOUR_ALIAS_TREE = "5e1814dd36cf861fd85477a97607299248f8272268df7bf428d31bbb6aa4354a"
EXPECTED_UVSPEC = "2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3"
EXPECTED_PROFILE_SHA256 = {
    "opac-profile-continental-average": "ceed598f7681951cd0e6208b267beb5b41a52ab10311f37ce76f925700caff3d",
    "opac-profile-maritime-clean": "487b67bd7dbe89d12d032fdf2b33cab545e16a2e0697170648317f1a76362a67",
    "opac-profile-desert": "2b4d2e03c6ae3143d9bb05d2da49f57f75172dc1f24d34f7d4a4939bf9952fef",
    "opac-profile-arctic": "98f2fa5428c830764252fd0a2662b0f5c957fc027ffcb7bdc0a5e500dfd7d3d6",
    "opac-profile-antarctic": "ee063c6dca68cf9a31d8bb9d993f1fed5cb34c8bb056ac180c97171b5d6b4f19",
}

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE_ADAPTER_PATH = ROOT / "review/aerosol-vertical-profile-sensitivity-v2-control-v1/adapter.py"
EXPECTED_BASE_ADAPTER_BLOB = "c245eac2fe5b5d026e46ec4253bc377c5fde97ec"
SEED_LEDGER_ENV = "AVPS_RECOVERY3_CANDIDATE_SEED_LEDGER"


class BridgeRefusal(RuntimeError):
    pass


def git_blob_sha1(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _load_base():
    if not BASE_ADAPTER_PATH.is_file() or git_blob_sha1(BASE_ADAPTER_PATH) != EXPECTED_BASE_ADAPTER_BLOB:
        raise BridgeRefusal("base AVPS v2 adapter byte drift")
    spec = importlib.util.spec_from_file_location("avps_v2_recovery3_bridge_base_adapter", BASE_ADAPTER_PATH)
    if spec is None or spec.loader is None:
        raise BridgeRefusal("cannot load base AVPS v2 adapter")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.STAGE = STAGE
    module.EXPECTED_SEED_CANONICAL = EXPECTED_SEED_CANONICAL
    module.EXPECTED_ROWS_CANONICAL = EXPECTED_ROWS_CANONICAL
    module.validate_authorization = validate_authorization
    module._seed_map = _seed_map
    return module


def validate_authorization(auth: dict[str, Any]) -> None:
    if auth.get("stageId") != STAGE or auth.get("status") != "AUTHORIZED_POSTCONSUMPTION_RECOVERY3_PENDING_SEPARATE_ALLOCATION_AND_DISPATCH":
        raise BridgeRefusal("recovery3 authorization stage/status drift")
    if auth.get("scientificOrdinal") != EXPECTED_ORDINAL or auth.get("executionKey") != EXPECTED_EXECUTION_KEY:
        raise BridgeRefusal("recovery3 authorization identity drift")
    if auth.get("authorizationBranch") != EXPECTED_AUTH_BRANCH or auth.get("dispatchBranch") != EXPECTED_DISPATCH_BRANCH:
        raise BridgeRefusal("recovery3 authorization branch drift")
    if auth.get("candidateSeedCount") != 72 or auth.get("candidateSeedCanonicalSha256") != EXPECTED_SEED_CANONICAL or auth.get("candidateRowsCanonicalSha256") != EXPECTED_ROWS_CANONICAL:
        raise BridgeRefusal("recovery3 candidate-seed identity drift")
    if auth.get("candidateSeedValuesIncluded") is not False or auth.get("candidateSeedsAppliedToTrackedCases") is not False:
        raise BridgeRefusal("candidate seeds leaked into tracked authorization state")
    if auth.get("caseCount") != 360 or auth.get("commonRandomNumberGroupCount") != 72 or auth.get("statesPerGroup") != 5:
        raise BridgeRefusal("recovery3 authorization cardinality drift")
    if auth.get("photonHistoriesPerCase") != 20_000_000:
        raise BridgeRefusal("recovery3 photon budget drift")
    if auth.get("exactFourSpeciesProfileSha256") != EXPECTED_PROFILE_SHA256:
        raise BridgeRefusal("recovery3 profile identity drift")
    if auth.get("fourAliasDataTreeSha256") != EXPECTED_FOUR_ALIAS_TREE or auth.get("uvspecSha256") != EXPECTED_UVSPEC:
        raise BridgeRefusal("recovery3 runtime identity drift")
    if auth.get("scientificExecutionAuthorized") is not True or auth.get("solverExecutionAuthorized") is not True:
        raise BridgeRefusal("recovery3 authorization does not preserve one-shot science authorization")
    if auth.get("snapshotFenceReleaseBarrierRequired") is not True:
        raise BridgeRefusal("recovery3 snapshot-fence-release requirement missing")
    for key in ("dispatchAuthorized", "automaticDispatch", "resultOpeningAuthorized", "levelBOpeningAuthorized", "productionAuthorized", "protectedHoldoutOpeningAuthorized", "taylorOrJerusalemFitAuthorized"):
        if auth.get(key) is not False:
            raise BridgeRefusal(f"recovery3 authorization crossed closed boundary: {key}")
    for key in ("githubRerunAllowed", "retryAllowed", "resumeAllowed"):
        if auth.get(key) is not False:
            raise BridgeRefusal(f"recovery3 one-shot boundary weakened: {key}")


def _seed_map() -> dict[str, int]:
    raw = os.environ.get(SEED_LEDGER_ENV, "").strip()
    if not raw:
        raise BridgeRefusal(f"{SEED_LEDGER_ENV} is required")
    path = Path(raw).resolve()
    if not path.is_file():
        raise BridgeRefusal("recovery3 candidate-seed ledger missing")
    ledger = json.loads(path.read_text())
    seeds = ledger.get("candidateSeeds")
    rows = ledger.get("candidateRows")
    if ledger.get("candidateSeedCount") != 72 or not isinstance(seeds, list) or len(seeds) != 72 or not isinstance(rows, list) or len(rows) != 72:
        raise BridgeRefusal("recovery3 candidate-seed ledger cardinality drift")
    if ledger.get("candidateSeedCanonicalSha256") != EXPECTED_SEED_CANONICAL or canonical_sha256([int(x) for x in seeds]) != EXPECTED_SEED_CANONICAL:
        raise BridgeRefusal("recovery3 candidate-seed canonical drift")
    if ledger.get("candidateRowsCanonicalSha256") != EXPECTED_ROWS_CANONICAL or canonical_sha256(rows) != EXPECTED_ROWS_CANONICAL:
        raise BridgeRefusal("recovery3 candidate-row canonical drift")
    out = {str(row.get("groupId")): int(row.get("seed")) for row in rows}
    if len(out) != 72 or len(set(out.values())) != 72 or set(out.values()) != {int(x) for x in seeds}:
        raise BridgeRefusal("recovery3 group-seed mapping drift")
    if any(not 0 < seed < 2_147_483_647 for seed in out.values()):
        raise BridgeRefusal("recovery3 seed outside signed-32-bit domain")
    return out


def authorized_case_universe(auth: dict[str, Any]) -> list[dict[str, Any]]:
    validate_authorization(auth)
    return _load_base().authorized_case_universe(auth)


def render_case_input(case: dict[str, Any], data_dir: Path, repository_root: Path, case_dir: Path) -> str:
    return _load_base().render_case_input(case, data_dir, repository_root, case_dir)


def prepare_case_files(case: dict[str, Any], auth: dict[str, Any], data_dir: Path, repository_root: Path, profile_dir: Path, output_root: Path) -> dict[str, Any]:
    validate_authorization(auth)
    return _load_base().prepare_case_files(case, auth, data_dir, repository_root, profile_dir, output_root)


def review_summary(auth: dict[str, Any]) -> dict[str, Any]:
    cases = authorized_case_universe(auth)
    groups = {str(row["groupId"]) for row in cases}
    return {
        "status": "PASS_RECOVERY3_ORDINAL44_ADAPTER_IDENTITY_BRIDGE_ZERO_RUNTIME",
        "scientificOrdinal": EXPECTED_ORDINAL,
        "executionKey": EXPECTED_EXECUTION_KEY,
        "caseCount": len(cases),
        "groupCount": len(groups),
        "candidateSeedCanonicalSha256": EXPECTED_SEED_CANONICAL,
        "candidateRowsCanonicalSha256": EXPECTED_ROWS_CANONICAL,
        "scientificRuntime": False,
        "solverExecution": False,
        "resultOpening": False,
    }
