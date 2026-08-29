from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXECUTOR = Path(__file__).with_name("executor.py")
AUTH = ROOT / "review/aerosol-vertical-profile-sensitivity-v2-authorization-control-v4/authorization.json"


def load_executor():
    spec = importlib.util.spec_from_file_location("avps_v2_executor_parity_review", EXECUTOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import executor")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def assert_refuses(fn, fragment: str):
    try:
        fn()
    except Exception as exc:
        assert fragment in str(exc), (fragment, type(exc).__name__, str(exc))
    else:
        raise AssertionError(f"expected refusal containing {fragment!r}")


def main() -> None:
    executor = load_executor()
    summary = executor.review_summary(ROOT)
    assert summary["status"] == "REVIEW_ONLY_V2_EXECUTOR_PARITY_PASS_NO_SOLVER"
    assert summary["scientificOrdinal"] == 41
    assert summary["caseCount"] == 360
    assert summary["groupCount"] == 72
    assert summary["statesPerGroup"] == 5
    assert summary["candidateSeedValuesSerialized"] is False
    assert summary["explicitFourSpeciesTransportRequired"] is True
    assert summary["solverExecutionPerformed"] is False
    assert summary["dispatchCreated"] is False
    assert summary["resultsOpened"] is False
    assert summary["productionAuthorized"] is False

    auth = json.loads(AUTH.read_text())
    executor.validate_authorization(auth)
    broken = dict(auth)
    broken["stageId"] = "aerosol-vertical-profile-sensitivity-v1"
    assert_refuses(lambda: executor.validate_authorization(broken), "stage/status drift")
    broken = dict(auth)
    broken["candidateSeedValuesIncluded"] = True
    assert_refuses(lambda: executor.validate_authorization(broken), "leaked")
    broken = dict(auth)
    broken["dispatchAuthorized"] = True
    assert_refuses(lambda: executor.validate_authorization(broken), "dispatchAuthorized")
    broken = dict(auth)
    broken["exactFourSpeciesProfileSha256"] = dict(auth["exactFourSpeciesProfileSha256"])
    broken["exactFourSpeciesProfileSha256"]["opac-profile-desert"] = "0" * 64
    assert_refuses(lambda: executor.validate_authorization(broken), "profile identity drift")

    valid_guard = {
        "status": "EXACT_ONE_USE_AVPS_V2_DISPATCH_AUTHORIZED",
        "scientificOrdinal": 41,
        "executionKey": "aerosol-vertical-profile-sensitivity-v2:numerical:41",
        "authorizationHead": "d5f5e4d9d19d7ede573fecae68565a92baabbec3",
        "authorizationPr": 604,
        "dispatchBranch": "dispatch/aerosol-vertical-profile-sensitivity-v2-ordinal-41",
        "dispatchBranchHeadSha": "d5f5e4d9d19d7ede573fecae68565a92baabbec3",
        "workflowRunAttempt": 1,
        "workflowRunId": 123456,
        "allocationMarkerCount": 1,
        "consumedMarkerCount": 1,
        "candidateSeedCanonicalSha256": "02f624d582e9b2caba6b920d65a5e8a8bc8fc1a2693623bc2f73abf5d3f706d2",
        "preSolverRepositoryGlobalSeedRecheckPassed": True,
        "fourAliasDataTreeSha256": "5e1814dd36cf861fd85477a97607299248f8272268df7bf428d31bbb6aa4354a",
        "solverExecutionPermittedNow": True,
        "githubRerun": False,
        "retryAllowed": False,
        "resumeAllowed": False,
    }
    executor.validate_guard(valid_guard)
    broken_guard = dict(valid_guard)
    broken_guard["consumedMarkerCount"] = 0
    assert_refuses(lambda: executor.validate_guard(broken_guard), "marker cardinality")
    broken_guard = dict(valid_guard)
    broken_guard["workflowRunAttempt"] = 2
    assert_refuses(lambda: executor.validate_guard(broken_guard), "exactly one")
    broken_guard = dict(valid_guard)
    broken_guard["preSolverRepositoryGlobalSeedRecheckPassed"] = False
    assert_refuses(lambda: executor.validate_guard(broken_guard), "seed recheck")

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        dummy = root / "dummy"
        dummy.write_text("not uvspec")
        assert_refuses(
            lambda: executor.execute_case(
                ROOT, AUTH, root / "guard.json", root / "runtime.json", root / "profiles",
                "avps-v2-does-not-matter", root / "data", root / "out", dummy,
                allow_execution=False,
            ),
            "allow_execution=True",
        )

    source = EXECUTOR.read_text()
    assert "aerosol_species_file profiles/" in source
    assert " INSO WASO SOOT SUSO" in source
    assert "legacy aerosol_file tau transport unexpectedly present" in source
    assert "profiles/{case['stateId']}.four-species.dat" in source
    assert "githubRerun" in source and "retryAllowed" in source and "resumeAllowed" in source
    print("AVPS_V2_EXECUTOR_PARITY_PASS")


if __name__ == "__main__":
    main()
