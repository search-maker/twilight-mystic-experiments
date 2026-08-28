from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE / "phase_a.py"
spec = importlib.util.spec_from_file_location("avps_post360_phase_a", MODULE_PATH)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)


def expect_refusal(fn, needle: str) -> None:
    try:
        fn()
    except m.PhaseARefusal as exc:
        if needle not in str(exc):
            raise AssertionError(f"wrong refusal: {exc}")
    else:
        raise AssertionError("expected PhaseARefusal")


def gate0_fixture() -> dict:
    artifacts = [
        {
            "id": 100000 + i,
            "name": f"avps-v1-case-case-{i:03d}",
            "digest": "sha256:" + f"{i:064x}"[-64:],
            "sizeInBytes": 2000000 + i,
        }
        for i in range(360)
    ]
    return {
        "schemaVersion": 1,
        "status": "EXACT360_RAW_RECOVERY_ARTIFACT_METADATA_FROZEN_RESULTS_UNOPENED",
        "workflowRunId": 33139545997,
        "recoveryOfWorkflowRunId": 33137514692,
        "caseArtifactCount": 360,
        "caseContentsDownloaded": False,
        "aggregateResultsCalled": False,
        "openResultsCalled": False,
        "scientificInterpretationPerformed": False,
        "artifacts": artifacts,
    }


def live_fixture(gate0: dict) -> list[dict]:
    return [{
        "artifacts": [
            {
                "id": row["id"],
                "name": row["name"],
                "digest": row["digest"],
                "size_in_bytes": row["sizeInBytes"],
                "expired": False,
                "workflow_run": {"id": 33139545997},
            }
            for row in gate0["artifacts"]
        ]
    }]


def recovery_result_fixture() -> dict:
    return {
        "transportRecovery": True,
        "recoveryOfWorkflowRunId": 33137514692,
        "recoveryReason": "EMPTY_DIAGNOSTIC_STREAM_ARTIFACT_CONTRACT_ONLY",
        "authorizedOriginalExecutorGitBlobSha1": "68eb7f6916bae204e60f6a378eae25f9c2bff184",
        "recoveryExecutorGitBlobSha1": "3580f7eff61ab06d0b4a7041f7907d871d961b5b",
        "scientificInputsChangedByRecovery": False,
        "seedAllocationChangedByRecovery": False,
        "caseUniverseChangedByRecovery": False,
        "runtimeIdentityChangedByRecovery": False,
        "resultOpeningAuthorizedByRecovery": False,
        "retryPerformed": False,
        "resumePerformed": False,
        "githubRerun": False,
        "workflowRunAttempt": 1,
        "workflowRunId": 33139545997,
        "scientificOrdinal": 40,
        "emptyDiagnosticStreamsPermittedByRecovery": [
            "solver-stderr.txt",
            "solver-stdout.txt",
            "syntax-stderr.txt",
            "syntax-stdout.txt",
        ],
    }


def main() -> None:
    assert m.AUTHORIZATION_PARENT == "99ade7798627e67921139697ba1a004fa8a304bb"
    assert m.AUTHORIZATION_HEAD == "338ee82c8e088e929f45782b1f7ac1c3aaaaa533"
    assert m.SCIENTIFIC_ORDINAL == 40
    assert m.RECOVERY_RUN_ID == 33139545997
    assert m.FAILED_RUN_ID == 33137514692
    assert m.GATE0_METADATA_ARTIFACT_ID == 9676069031
    assert m.GATE0_METADATA_ARTIFACT_DIGEST == "sha256:70dedcd16209dea74a9ed67a1dc7377c123f1a62fd18741b1e15692702011fc8"
    assert m.GATE0_METADATA_INNER_SHA256 == "323f458b43a031c50f2c2f74971594801608a5cdf437839c8760b42c19bdb92e"
    assert m.AGGREGATOR_GIT_BLOB_SHA1 == "1f36fc95347b84623db9b77005907929389dc7e8"
    assert m.RECOVERY_EXECUTOR_GIT_BLOB_SHA1 == "3580f7eff61ab06d0b4a7041f7907d871d961b5b"

    g = gate0_fixture()
    frozen = m.validate_gate0_metadata(g)
    assert len(frozen) == 360
    m.validate_live_artifact_surface(frozen, live_fixture(g))

    bad = json.loads(json.dumps(g))
    bad["openResultsCalled"] = True
    expect_refusal(lambda: m.validate_gate0_metadata(bad), "openResultsCalled")

    bad_live = live_fixture(g)
    bad_live[0]["artifacts"][0]["digest"] = "sha256:" + "f" * 64
    expect_refusal(lambda: m.validate_live_artifact_surface(frozen, bad_live), "digest drift")

    result = recovery_result_fixture()
    m.validate_recovery_case_result(result, "case")
    for key in (
        "transportRecovery",
        "recoveryOfWorkflowRunId",
        "scientificInputsChangedByRecovery",
        "resultOpeningAuthorizedByRecovery",
        "workflowRunId",
    ):
        bad_result = dict(result)
        bad_result[key] = None
        expect_refusal(lambda r=bad_result: m.validate_recovery_case_result(r, "case"), key)

    bad_diag = dict(result)
    bad_diag["emptyDiagnosticStreamsPermittedByRecovery"] = ["syntax-stdout.txt"]
    expect_refusal(lambda: m.validate_recovery_case_result(bad_diag, "case"), "diagnostic-member")

    source = MODULE_PATH.read_text()
    assert "open_results.py" not in source
    assert "open_results(" not in source
    assert '"openResultsCalled": False' in source
    assert '"scientificInterpretationPerformed": False' in source
    assert '"resultOpeningAuthorized": False' in source
    assert "aggregate.aggregate(" in source
    print("AVPS post360 Phase A wrapper tests: PASS")


if __name__ == "__main__":
    main()
