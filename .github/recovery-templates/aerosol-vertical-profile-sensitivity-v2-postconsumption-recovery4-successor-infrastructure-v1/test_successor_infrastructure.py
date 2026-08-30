from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
GENERATOR = HERE / "generate.py"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def expect_refusal(fn, label: str) -> None:
    try:
        fn()
    except Exception:
        return
    raise SystemExit(f"expected refusal did not occur: {label}")


def main() -> None:
    generator = load("avps_recovery4_successor_generator", GENERATOR)
    generator.check_sources()
    rows = generator.derive_seed_rows()
    seeds = [int(row["seed"]) for row in rows]
    ordinal = 1_900_000_001  # synthetic review sentinel; never a candidate/allocated scientific ordinal
    identity = {
        "schemaVersion": 1,
        "syntheticReviewOnly": True,
        "stageId": generator.STAGE,
        "authorizationStatus": generator.AUTH_STATUS,
        "scientificOrdinal": ordinal,
        "executionKey": f"{generator.STAGE}:numerical:{ordinal}",
        "authorizationHead": "1" * 40,
        "authorizationParent": "2" * 40,
        "authorizationPr": 1_900_001,
        "authorizationReviewRun": 1_900_002,
        "authorizationReviewArtifact": 1_900_003,
        "authorizationReviewDigest": "sha256:" + "3" * 64,
        "authorizationBranch": f"authorization/{generator.STAGE}-ordinal-{ordinal}",
        "dispatchBranch": f"dispatch/{generator.STAGE}-ordinal-{ordinal}",
        "authorizationPath": "review/synthetic-avps-recovery4-authorization/authorization.json",
        "authorizationBlob": "4" * 40,
        "authorizationSeedLedgerPath": "review/synthetic-avps-recovery4-seed-freshness/seed_ledger.py",
        "authorizationSeedLedgerBlob": "5" * 40,
        "seedNamespace": generator.SEED_NAMESPACE,
        "candidateSeedCount": 72,
        "candidateSeedCanonicalSha256": generator.canonical(seeds),
        "candidateRowsCanonicalSha256": generator.canonical(rows),
        "caseCount": 360,
        "commonRandomNumberGroupCount": 72,
        "statesPerGroup": 5,
        "photonHistoriesPerCase": 20_000_000,
        "newMappingAuthorized": False,
        "resultOpeningAuthorized": False,
        "levelBOpeningAuthorized": False,
        "protectedHoldoutOpeningAuthorized": False,
        "productionAuthorized": False,
        "taylorOrJerusalemFitAuthorized": False,
    }

    auth = {
        "stageId": generator.STAGE,
        "status": generator.AUTH_STATUS,
        "scientificOrdinal": ordinal,
        "executionKey": identity["executionKey"],
        "authorizationBranch": identity["authorizationBranch"],
        "dispatchBranch": identity["dispatchBranch"],
        "candidateSeedCanonicalSha256": identity["candidateSeedCanonicalSha256"],
        "candidateRowsCanonicalSha256": identity["candidateRowsCanonicalSha256"],
        "candidateSeedCount": 72,
        "caseCount": 360,
        "commonRandomNumberGroupCount": 72,
        "statesPerGroup": 5,
        "photonHistoriesPerCase": 20_000_000,
        "scientificExecutionAuthorized": True,
        "solverExecutionAuthorized": True,
        "dispatchAuthorized": False,
        "automaticDispatch": False,
        "resultOpeningAuthorized": False,
        "levelBOpeningAuthorized": False,
        "protectedHoldoutOpeningAuthorized": False,
        "productionAuthorized": False,
        "taylorOrJerusalemFitAuthorized": False,
        "githubRerunAllowed": False,
        "retryAllowed": False,
        "resumeAllowed": False,
    }

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        identity_path = root / "identity.json"
        identity_path.write_text(json.dumps(identity, indent=2, sort_keys=True) + "\n")
        output = root / "generated"
        output.mkdir()
        manifest = generator.generate(identity_path, output)

        mirror = {
            generator.BASE_ADAPTER: output / "review/aerosol-vertical-profile-sensitivity-v2-control-v1/adapter.py",
            ROOT / "review/aerosol-vertical-profile-sensitivity-v2-executor-parity-v1/executor.py": output / "review/aerosol-vertical-profile-sensitivity-v2-executor-parity-v1/executor.py",
            ROOT / "review/aerosol-vertical-profile-sensitivity-v2-aggregator-parity-v1/aggregator.py": output / "review/aerosol-vertical-profile-sensitivity-v2-aggregator-parity-v1/aggregator.py",
        }
        for src, dst in mirror.items():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)

        runtime = output / manifest["runtimeDir"]
        adapter = load("avps_recovery4_fixture_adapter", runtime / "runtime_adapter.py")
        executor = load("avps_recovery4_fixture_executor", runtime / "executor.py")
        aggregator = load("avps_recovery4_fixture_aggregator", runtime / "aggregator.py")

        auth_path = root / "authorization.json"
        auth_path.write_text(json.dumps(auth, indent=2, sort_keys=True) + "\n")
        adapter.validate_authorization(auth)
        cases = adapter.authorized_case_universe(auth)
        if len(cases) != 360 or len({str(row["groupId"]) for row in cases}) != 72:
            raise SystemExit("future wrapper case/group cardinality drift")
        groups: dict[str, list[dict]] = {}
        matrices = {2: [], 4: [], 6: [], 8: []}
        for row in cases:
            groups.setdefault(str(row["groupId"]), []).append(row)
            dep = int(round(float(row["sunDepressionDeg"])))
            if dep not in matrices:
                raise SystemExit(f"unexpected solar depression {dep}")
            matrices[dep].append(row["caseId"])
        if any(len(rows_) != 5 or len({r["stateId"] for r in rows_}) != 5 or len({r["seed"] for r in rows_}) != 1 for rows_ in groups.values()):
            raise SystemExit("future wrapper CRN five-state structure drift")
        if {k: len(v) for k, v in matrices.items()} != {2: 90, 4: 90, 6: 90, 8: 90}:
            raise SystemExit("future wrapper 4x90 matrix drift")

        executor.validate_authorization(auth)
        guard = {
            "status": generator.GUARD_STATUS,
            "scientificOrdinal": ordinal,
            "executionKey": identity["executionKey"],
            "authorizationHead": identity["authorizationHead"],
            "authorizationPr": identity["authorizationPr"],
            "dispatchBranch": identity["dispatchBranch"],
            "dispatchBranchHeadSha": identity["authorizationHead"],
            "workflowRunId": 1_900_004,
            "workflowRunAttempt": 1,
            "allocationMarkerCount": 1,
            "consumedMarkerCount": 1,
            "candidateSeedCanonicalSha256": identity["candidateSeedCanonicalSha256"],
            "preSolverRepositoryGlobalSeedRecheckPassed": True,
            "fourAliasDataTreeSha256": generator.FOUR_ALIAS,
            "solverExecutionPermittedNow": True,
            "githubRerun": False,
            "retryAllowed": False,
            "resumeAllowed": False,
        }
        executor.validate_guard(guard)

        bad = dict(auth); bad["stageId"] = generator.OLD["stage"]
        expect_refusal(lambda: adapter.validate_authorization(bad), "old recovery3 stage")
        bad = dict(auth); bad["status"] = generator.OLD["auth_status"]
        expect_refusal(lambda: adapter.validate_authorization(bad), "old recovery3 status")
        bad = dict(auth); bad["scientificOrdinal"] = generator.OLD["ordinal"]
        expect_refusal(lambda: adapter.validate_authorization(bad), "consumed ordinal44")
        bad = dict(auth); bad["candidateSeedCanonicalSha256"] = generator.OLD["seed"]
        expect_refusal(lambda: adapter.validate_authorization(bad), "consumed recovery3 seed identity")
        old_guard = dict(guard); old_guard["scientificOrdinal"] = generator.OLD["ordinal"]
        expect_refusal(lambda: executor.validate_guard(old_guard), "consumed ordinal44 guard")

        expect_refusal(
            lambda: executor.execute_case(Path("."), Path("none"), Path("none"), Path("none"), Path("none"), "none", Path("none"), Path("none"), Path("none"), allow_execution=False),
            "review-mode executor cannot execute solver",
        )
        closed = aggregator.structural_closed_aggregate_fixture(ROOT, auth_path)
        if closed != {
            "exact360ClosedAggregateCompatible": True,
            "missingCaseRefused": True,
            "caseCount": 360,
            "groupCount": 72,
            "analysisCellCount": 24,
            "statesPerGroup": 5,
            "resultOpeningAuthorized": False,
        }:
            raise SystemExit("closed aggregate fixture drift")

        workflow = (output / manifest["workflow"]).read_text()
        runtime_dir = manifest["runtimeDir"]
        required_routes = (
            f"RUNTIME_ADAPTER_PATH: {runtime_dir}/runtime_adapter.py",
            "p=Path(os.environ['RUNTIME_ADAPTER_PATH'])",
            f"EXECUTOR_PATH: {runtime_dir}/executor.py",
            'PYTHONPATH="$RUNTIME_DIR" python - <<\'PY\'\n          import os\n          from pathlib import Path\n          import executor',
            f"AGGREGATOR_PATH: {runtime_dir}/aggregator.py",
            'PYTHONPATH="$RUNTIME_DIR" python - <<\'PY\'\n          import json,os\n          from pathlib import Path\n          import aggregator',
            "Path('preflight/authorization.json')",
        )
        for token in required_routes:
            if token not in workflow:
                raise SystemExit(f"generated workflow missing wrapper route: {token}")
        forbidden_routes = (
            "p=Path('review/aerosol-vertical-profile-sensitivity-v2-control-v1/adapter.py')",
            "PYTHONPATH=review/aerosol-vertical-profile-sensitivity-v2-executor-parity-v1 python - <<'PY'",
            "PYTHONPATH=review/aerosol-vertical-profile-sensitivity-v2-aggregator-parity-v1 python - <<'PY'",
        )
        for token in forbidden_routes:
            if token in workflow:
                raise SystemExit(f"generated workflow retained old direct route: {token}")
        if generator.OLD["auth_head"] in workflow or generator.OLD["dispatch_branch"] in workflow or generator.OLD["seed"] in workflow:
            raise SystemExit("generated workflow retained consumed recovery3 identity")
        if manifest.get("solverExecution") is not False or manifest.get("resultsOpened") is not False or manifest.get("newMappingAuthorized") is not False:
            raise SystemExit("review manifest crossed a closed boundary")

        receipt = {
            "schemaVersion": 1,
            "status": "PASS_AVPS_V2_RECOVERY4_SUCCESSOR_INFRASTRUCTURE_ZERO_RUNTIME_REVIEW",
            "syntheticReviewOrdinalOnly": ordinal,
            "futureAuthorizationAcceptedByGeneratedAdapter": True,
            "matrixAssemblyUsesGeneratedRecoveryAdapter": True,
            "matrixShardCounts": {str(k): len(v) for k, v in matrices.items()},
            "caseExecutionUsesGeneratedRecoveryExecutor": True,
            "closedAggregationUsesGeneratedRecoveryAggregator": True,
            "oldRecovery3StageAccepted": False,
            "oldRecovery3StatusAccepted": False,
            "consumedOrdinal44Accepted": False,
            "consumedRecovery3SeedIdentityAccepted": False,
            "caseCount": 360,
            "groupCount": 72,
            "statesPerGroup": 5,
            "photonHistoriesPerCase": 20_000_000,
            "closedAggregate": closed,
            "scientificRuntime": False,
            "solverExecution": False,
            "resultsOpened": False,
            "levelBOpeningAuthorized": False,
            "protectedHoldoutOpeningAuthorized": False,
            "productionAuthorized": False,
            "taylorOrJerusalemUsed": False,
            "newMappingAuthorized": False,
        }
        Path("avps-recovery4-successor-infrastructure-review-receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
        print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
