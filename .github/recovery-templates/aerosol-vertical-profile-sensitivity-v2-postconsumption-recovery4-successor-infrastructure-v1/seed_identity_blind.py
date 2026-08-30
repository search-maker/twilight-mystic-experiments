from __future__ import annotations

"""Seed-identity-blind transport guard for the AVPS recovery4 successor generator.

This module is the mandatory entry point for any non-synthetic future recovery4
identity.  The underlying routing generator remains useful review substrate, but
its draft recovery4 seed namespace is explicitly refused here.  A real seed
namespace and its 72 deterministic counter-zero rows must first be produced by a
separately reviewed repository-global zero-collision seed-freshness gate.

No scientific ordinal, real seed namespace, authorization, dispatch, solver
execution, result opening, Level-B admission, protected holdout, Taylor/Jerusalem
fit, or production transition is selected by this module.
"""

import argparse
import copy
import hashlib
import importlib.util
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
BASE_GENERATOR = HERE / "generate.py"
OLD_RECOVERY3_NAMESPACE = "aerosol-vertical-profile-sensitivity-v2|postconsumption-recovery3|group-seed|sha256-v1"
PRESELECTED_DRAFT_RECOVERY4_NAMESPACE = "aerosol-vertical-profile-sensitivity-v2|postconsumption-recovery4|group-seed|sha256-v1"
OLD_RECOVERY3_SEED_CANONICAL = "d2817b1ea4f2bdc8cb1842e565b099b015e4e28c5874482629fadc450069d9bf"
SYNTHETIC_PREFIX = "synthetic-review-only|avps-recovery4|"
REAL_LEDGER_STATUS = "PASS_REVIEWED_REPOSITORY_GLOBAL_ZERO_COLLISION_NOT_ALLOCATED"
SYNTHETIC_LEDGER_STATUS = "SYNTHETIC_REVIEW_ONLY_NOT_FRESHNESS_EVIDENCE"


class SeedIdentityRefusal(RuntimeError):
    pass


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SeedIdentityRefusal(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def canonical(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _generator():
    return load_module("avps_recovery4_seed_blind_base_generator", BASE_GENERATOR)


def derive_counter_zero_rows(namespace: str) -> list[dict[str, Any]]:
    if not isinstance(namespace, str) or not namespace.strip():
        raise SeedIdentityRefusal("seed namespace missing")
    generator = _generator()
    base = generator.load_module("avps_recovery4_seed_blind_base_adapter", generator.BASE_ADAPTER)
    skeleton = base._skeleton()
    groups = skeleton.get("groups")
    if not isinstance(groups, list) or len(groups) != 72:
        raise SeedIdentityRefusal("72-group skeleton drift")
    rows: list[dict[str, Any]] = []
    used: set[int] = set()
    for group in groups:
        gid = str(group["groupId"])
        material = f"{namespace}|groupId={gid}|counter=0"
        digest = hashlib.sha256(material.encode()).hexdigest()
        seed = (int(digest[:16], 16) % generator.SPAN) + generator.MIN_SEED
        if seed in used:
            raise SeedIdentityRefusal("intra-ledger seed collision")
        used.add(seed)
        rows.append({"groupId": gid, "collisionCounter": 0, "derivationMaterialSha256": digest, "seed": seed})
    if len(rows) != 72 or len({int(row["seed"]) for row in rows}) != 72:
        raise SeedIdentityRefusal("seed-row cardinality drift")
    return rows


def _validate_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise SeedIdentityRefusal(f"invalid SHA-256: {label}")
    return value


def validate_seed_ledger(identity: dict[str, Any], ledger: dict[str, Any]) -> list[dict[str, Any]]:
    ordinal = identity.get("scientificOrdinal")
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal <= 0:
        raise SeedIdentityRefusal("scientific ordinal must be positive")
    if ordinal == 44:
        raise SeedIdentityRefusal("consumed ordinal44 is permanently refused")

    namespace = identity.get("seedNamespace")
    if not isinstance(namespace, str) or not namespace:
        raise SeedIdentityRefusal("future seedNamespace missing")
    if namespace == OLD_RECOVERY3_NAMESPACE:
        raise SeedIdentityRefusal("consumed recovery3 seed namespace refused")
    if namespace == PRESELECTED_DRAFT_RECOVERY4_NAMESPACE:
        raise SeedIdentityRefusal("preselected draft recovery4 namespace refused; choose only after fresh global review")

    synthetic = identity.get("syntheticReviewOnly") is True
    expected_status = SYNTHETIC_LEDGER_STATUS if synthetic else REAL_LEDGER_STATUS
    if ledger.get("status") != expected_status:
        raise SeedIdentityRefusal("seed-ledger review status drift")
    if ledger.get("seedNamespace") != namespace:
        raise SeedIdentityRefusal("seed-ledger namespace mismatch")
    if ledger.get("candidateSeedCount") != 72:
        raise SeedIdentityRefusal("seed-ledger count drift")
    if ledger.get("repositoryGlobalCollisionCount") != 0:
        raise SeedIdentityRefusal("repository-global seed collision not zero")
    if ledger.get("scientificOrdinalAllocated") is not False:
        raise SeedIdentityRefusal("seed ledger must precede ordinal allocation")
    if ledger.get("dispatchCreated") is not False or ledger.get("scientificRuntime") is not False:
        raise SeedIdentityRefusal("seed ledger crossed execution boundary")

    if synthetic:
        if not namespace.startswith(SYNTHETIC_PREFIX):
            raise SeedIdentityRefusal("synthetic fixture namespace drift")
    elif namespace.startswith(SYNTHETIC_PREFIX):
        raise SeedIdentityRefusal("synthetic namespace forbidden for real identity")

    rows = ledger.get("rows")
    if not isinstance(rows, list) or len(rows) != 72:
        raise SeedIdentityRefusal("seed-ledger rows missing")
    derived = derive_counter_zero_rows(namespace)
    if rows != derived:
        raise SeedIdentityRefusal("seed-ledger rows are not exact counter-zero derivation for reviewed namespace")
    seeds = [int(row["seed"]) for row in rows]
    seed_hash = canonical(seeds)
    rows_hash = canonical(rows)
    _validate_sha256(identity.get("candidateSeedCanonicalSha256"), "identity candidate seeds")
    _validate_sha256(identity.get("candidateRowsCanonicalSha256"), "identity candidate rows")
    if identity["candidateSeedCanonicalSha256"] != seed_hash or identity["candidateRowsCanonicalSha256"] != rows_hash:
        raise SeedIdentityRefusal("identity candidate hashes do not bind reviewed seed ledger")
    if ledger.get("candidateSeedCanonicalSha256") != seed_hash or ledger.get("candidateRowsCanonicalSha256") != rows_hash:
        raise SeedIdentityRefusal("seed-ledger canonical hash drift")
    if seed_hash == OLD_RECOVERY3_SEED_CANONICAL:
        raise SeedIdentityRefusal("consumed recovery3 seed identity refused")
    return copy.deepcopy(rows)


def generate(identity_path: Path, seed_ledger_path: Path, output_root: Path) -> dict[str, Any]:
    identity = json.loads(identity_path.read_text())
    ledger = json.loads(seed_ledger_path.read_text())
    rows = validate_seed_ledger(identity, ledger)
    namespace = str(identity["seedNamespace"])

    generator = _generator()
    generator.SEED_NAMESPACE = namespace

    def reviewed_rows(requested_namespace: str = namespace) -> list[dict[str, Any]]:
        if requested_namespace != namespace:
            raise SystemExit("seed namespace drift from separately reviewed identity")
        return copy.deepcopy(rows)

    generator.derive_seed_rows = reviewed_rows
    manifest = generator.generate(identity_path, output_root)
    if manifest.get("scientificRuntime") is not False or manifest.get("solverExecution") is not False:
        raise SeedIdentityRefusal("seed-blind generator crossed scientific runtime boundary")
    if manifest.get("resultsOpened") is not False or manifest.get("newMappingAuthorized") is not False:
        raise SeedIdentityRefusal("seed-blind generator crossed result/mapping boundary")
    manifest["seedIdentitySource"] = "SEPARATELY_REVIEWED_LEDGER"
    manifest["seedNamespaceSelectedByInfrastructureGate"] = False
    manifest["seedLedgerStatus"] = ledger["status"]
    (output_root / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def _identity_for_synthetic(namespace: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    generator = _generator()
    ordinal = 1_900_000_001
    seeds = [int(row["seed"]) for row in rows]
    return {
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
        "authorizationSeedLedgerPath": "review/synthetic-avps-recovery4-seed-freshness/seed-ledger.json",
        "authorizationSeedLedgerBlob": "5" * 40,
        "seedNamespace": namespace,
        "candidateSeedCount": 72,
        "candidateSeedCanonicalSha256": canonical(seeds),
        "candidateRowsCanonicalSha256": canonical(rows),
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


def _ledger_for_synthetic(namespace: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    seeds = [int(row["seed"]) for row in rows]
    return {
        "schemaVersion": 1,
        "status": SYNTHETIC_LEDGER_STATUS,
        "seedNamespace": namespace,
        "candidateSeedCount": 72,
        "candidateSeedCanonicalSha256": canonical(seeds),
        "candidateRowsCanonicalSha256": canonical(rows),
        "repositoryGlobalCollisionCount": 0,
        "scientificOrdinalAllocated": False,
        "dispatchCreated": False,
        "scientificRuntime": False,
        "rows": rows,
    }


def expect_refusal(fn, label: str) -> None:
    try:
        fn()
    except Exception:
        return
    raise SystemExit(f"expected refusal did not occur: {label}")


def self_test() -> dict[str, Any]:
    namespace = SYNTHETIC_PREFIX + "fixture-v1"
    rows = derive_counter_zero_rows(namespace)
    identity = _identity_for_synthetic(namespace, rows)
    ledger = _ledger_for_synthetic(namespace, rows)

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        identity_path = root / "identity.json"
        ledger_path = root / "seed-ledger.json"
        output = root / "generated"
        identity_path.write_text(json.dumps(identity, indent=2, sort_keys=True) + "\n")
        ledger_path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n")
        output.mkdir()
        manifest = generate(identity_path, ledger_path, output)
        runtime = output / manifest["runtimeDir"]
        adapter = load_module("avps_recovery4_seed_blind_generated_adapter", runtime / "runtime_adapter.py")
        receipt = adapter.seed_receipt()
        if receipt.get("seedCount") != 72:
            raise SystemExit("generated adapter seed count drift")
        if receipt.get("seedCanonicalSha256") != identity["candidateSeedCanonicalSha256"]:
            raise SystemExit("generated adapter seed hash drift")
        if receipt.get("rowsCanonicalSha256") != identity["candidateRowsCanonicalSha256"]:
            raise SystemExit("generated adapter row hash drift")
        workflow = (output / manifest["workflow"]).read_text()
        runtime_dir = manifest["runtimeDir"]
        for token in (
            f"RUNTIME_ADAPTER_PATH: {runtime_dir}/runtime_adapter.py",
            f"EXECUTOR_PATH: {runtime_dir}/executor.py",
            f"AGGREGATOR_PATH: {runtime_dir}/aggregator.py",
            "Path('preflight/authorization.json')",
        ):
            if token not in workflow:
                raise SystemExit(f"generated wrapper route missing: {token}")

    bad = copy.deepcopy(identity)
    bad["scientificOrdinal"] = 44
    expect_refusal(lambda: validate_seed_ledger(bad, ledger), "consumed ordinal44")
    bad = copy.deepcopy(identity)
    bad["seedNamespace"] = OLD_RECOVERY3_NAMESPACE
    bad_ledger = copy.deepcopy(ledger); bad_ledger["seedNamespace"] = OLD_RECOVERY3_NAMESPACE
    expect_refusal(lambda: validate_seed_ledger(bad, bad_ledger), "consumed recovery3 namespace")
    bad = copy.deepcopy(identity)
    bad["seedNamespace"] = PRESELECTED_DRAFT_RECOVERY4_NAMESPACE
    bad_ledger = copy.deepcopy(ledger); bad_ledger["seedNamespace"] = PRESELECTED_DRAFT_RECOVERY4_NAMESPACE
    expect_refusal(lambda: validate_seed_ledger(bad, bad_ledger), "prematurely preselected draft recovery4 namespace")
    bad = copy.deepcopy(identity)
    bad["candidateSeedCanonicalSha256"] = OLD_RECOVERY3_SEED_CANONICAL
    expect_refusal(lambda: validate_seed_ledger(bad, ledger), "consumed recovery3 seed hash")
    bad_ledger = copy.deepcopy(ledger); bad_ledger["repositoryGlobalCollisionCount"] = 1
    expect_refusal(lambda: validate_seed_ledger(identity, bad_ledger), "nonzero repository-global collision")

    result = {
        "schemaVersion": 1,
        "status": "PASS_AVPS_V2_RECOVERY4_SEED_IDENTITY_BLIND_CORRECTION_ZERO_RUNTIME_REVIEW",
        "realSeedNamespaceSelected": False,
        "scientificOrdinalSelected": False,
        "syntheticFixtureOnly": True,
        "wrapperRoutesPreserved": True,
        "consumedOrdinal44Accepted": False,
        "consumedRecovery3NamespaceAccepted": False,
        "preselectedDraftRecovery4NamespaceAccepted": False,
        "consumedRecovery3SeedHashAccepted": False,
        "nonzeroGlobalCollisionAccepted": False,
        "caseCount": 360,
        "groupCount": 72,
        "statesPerGroup": 5,
        "photonHistoriesPerCase": 20_000_000,
        "scientificRuntime": False,
        "solverExecution": False,
        "resultsOpened": False,
        "newMappingAuthorized": False,
        "levelBOpeningAuthorized": False,
        "protectedHoldoutOpeningAuthorized": False,
        "productionAuthorized": False,
        "taylorOrJerusalemUsed": False,
    }
    Path("avps-recovery4-seed-identity-blind-correction-review-receipt.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--identity", type=Path)
    parser.add_argument("--seed-ledger", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.identity is None or args.seed_ledger is None or args.output is None:
        raise SystemExit("--identity, --seed-ledger and --output are required outside --self-test")
    if args.output.exists():
        raise SystemExit("output path already exists")
    args.output.mkdir(parents=True)
    manifest = generate(args.identity, args.seed_ledger, args.output)
    print(json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    main()
