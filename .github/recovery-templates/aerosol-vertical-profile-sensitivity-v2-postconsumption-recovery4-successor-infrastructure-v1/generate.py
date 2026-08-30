from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_DIR = ROOT / ".github/recovery-templates/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery4-successor-infrastructure-v1"
SOURCE_WORKFLOW = ROOT / ".github/workflows/avps-v2-postconsumption-recovery3-science.yml"
SOURCE_ADAPTER = ROOT / "runtime-avps-v2-recovery3-ordinal44-v1/runtime_adapter.py"
SOURCE_EXECUTOR = ROOT / "runtime-avps-v2-recovery3-ordinal44-v1/executor.py"
SOURCE_AGGREGATOR = ROOT / "runtime-avps-v2-recovery3-ordinal44-v1/aggregator.py"
BASE_ADAPTER = ROOT / "review/aerosol-vertical-profile-sensitivity-v2-control-v1/adapter.py"

EXPECTED_BLOBS = {
    SOURCE_WORKFLOW: "ddc2bb954cf07c4c7f314c3d551a8aee44381c73",
    SOURCE_ADAPTER: "9fce4f704040d7849b59ed96577d02e5aeecd455",
    SOURCE_EXECUTOR: "643c0d5b499747a8529a2a58c659ee24a7fd2a60",
    SOURCE_AGGREGATOR: "abe8522d7e3562eef9f2c807911871916627fa96",
    BASE_ADAPTER: "c245eac2fe5b5d026e46ec4253bc377c5fde97ec",
}

STAGE = "aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery4"
AUTH_STATUS = "AUTHORIZED_POSTCONSUMPTION_RECOVERY4_PENDING_SEPARATE_ALLOCATION_AND_DISPATCH"
GUARD_STATUS = "EXACT_ONE_USE_AVPS_V2_POSTCONSUMPTION_RECOVERY4_DISPATCH_AUTHORIZED"
SEED_NAMESPACE = "synthetic-review-only|avps-v2-recovery4-routing-fixture|group-seed|sha256-v1"
MIN_SEED = 10_000_000
MAX_EXCLUSIVE = 2_147_483_647
SPAN = MAX_EXCLUSIVE - MIN_SEED
FOUR_ALIAS = "5e1814dd36cf861fd85477a97607299248f8272268df7bf428d31bbb6aa4354a"
PROFILE_SHA256 = {
    "opac-profile-continental-average": "ceed598f7681951cd0e6208b267beb5b41a52ab10311f37ce76f925700caff3d",
    "opac-profile-maritime-clean": "487b67bd7dbe89d12d032fdf2b33cab545e16a2e0697170648317f1a76362a67",
    "opac-profile-desert": "2b4d2e03c6ae3143d9bb05d2da49f57f75172dc1f24d34f7d4a4939bf9952fef",
    "opac-profile-arctic": "98f2fa5428c830764252fd0a2662b0f5c957fc027ffcb7bdc0a5e500dfd7d3d6",
    "opac-profile-antarctic": "ee063c6dca68cf9a31d8bb9d993f1fed5cb34c8bb056ac180c97171b5d6b4f19",
}

OLD = {
    "stage": "aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3",
    "auth_status": "AUTHORIZED_POSTCONSUMPTION_RECOVERY3_PENDING_SEPARATE_ALLOCATION_AND_DISPATCH",
    "guard_status": "EXACT_ONE_USE_AVPS_V2_POSTCONSUMPTION_RECOVERY3_DISPATCH_AUTHORIZED",
    "ordinal": 44,
    "execution_key": "aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3:numerical:44",
    "auth_head": "dd3a4c692af505389e9feb1e5f5480fa389110a3",
    "auth_parent": "d8cd4af807e7a8f11ed39fdc579ed92adf866aab",
    "auth_pr": 718,
    "auth_branch": "authorization/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3-ordinal-44",
    "dispatch_branch": "dispatch/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3-ordinal-44",
    "seed": "d2817b1ea4f2bdc8cb1842e565b099b015e4e28c5874482629fadc450069d9bf",
    "rows": "b6a519eadacdb99ea53c52d483c8acfeba05829643cb988de21682a53fc47896",
    "namespace": "aerosol-vertical-profile-sensitivity-v2|postconsumption-recovery3|group-seed|sha256-v1",
    "review_run": 33319037610,
    "review_artifact": 9734515864,
    "review_digest": "sha256:bfef625ebb0a45f8a59e38cb46b64ded9e7d9f3fcbb895355144a3af5044eed7",
    "auth_path": "review/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3-authorization-control-v1/authorization.json",
    "auth_blob": "927956c0c01d02d3b025b141bb1c8b72d873dfc7",
    "seed_ledger_path": "review/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3-seed-freshness-v1/seed_ledger.py",
    "seed_ledger_blob": "a4fc0b95c3627a310c0c17a1ae8b89701511b3b8",
}


def git_blob_sha1_bytes(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def git_blob_sha1(path: Path) -> str:
    return git_blob_sha1_bytes(path.read_bytes())


def canonical(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def check_sources() -> None:
    if not SEED_NAMESPACE.startswith("synthetic-review-only|"):
        raise SystemExit("infrastructure review seed namespace must remain explicitly synthetic")
    if "postconsumption-recovery4|group-seed" in SEED_NAMESPACE:
        raise SystemExit("infrastructure review must not preselect a real recovery4 seed namespace")
    for path, expected in EXPECTED_BLOBS.items():
        if not path.is_file():
            raise SystemExit(f"bound source missing: {path}")
        got = git_blob_sha1(path)
        if got != expected:
            raise SystemExit(f"bound source byte drift: {path}: {got} != {expected}")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def derive_seed_rows(namespace: str = SEED_NAMESPACE) -> list[dict[str, Any]]:
    if namespace != SEED_NAMESPACE:
        raise SystemExit("only the explicit synthetic review seed namespace may be derived in this infrastructure gate")
    base = load_module("avps_recovery4_generator_base_adapter", BASE_ADAPTER)
    skeleton = base._skeleton()
    groups = skeleton.get("groups")
    if not isinstance(groups, list) or len(groups) != 72:
        raise SystemExit("72-group skeleton drift")
    rows: list[dict[str, Any]] = []
    used: set[int] = set()
    for group in groups:
        gid = str(group["groupId"])
        counter = 0
        material = f"{namespace}|groupId={gid}|counter={counter}"
        digest = hashlib.sha256(material.encode()).hexdigest()
        seed = (int(digest[:16], 16) % SPAN) + MIN_SEED
        if seed in used:
            raise SystemExit("unexpected synthetic review seed collision")
        used.add(seed)
        rows.append({"groupId": gid, "collisionCounter": counter, "derivationMaterialSha256": digest, "seed": seed})
    if len(rows) != 72 or len({int(row["seed"]) for row in rows}) != 72:
        raise SystemExit("synthetic review seed row cardinality drift")
    return rows


def _is_sha1(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value) is not None


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def validate_identity(identity: dict[str, Any]) -> dict[str, Any]:
    ordinal = identity.get("scientificOrdinal")
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal <= 0:
        raise SystemExit("future scientificOrdinal must be a positive separately-reviewed integer")
    if ordinal == OLD["ordinal"]:
        raise SystemExit("consumed recovery3 ordinal44 cannot be reused")
    exact = {
        "stageId": STAGE,
        "authorizationStatus": AUTH_STATUS,
        "executionKey": f"{STAGE}:numerical:{ordinal}",
        "authorizationBranch": f"authorization/{STAGE}-ordinal-{ordinal}",
        "dispatchBranch": f"dispatch/{STAGE}-ordinal-{ordinal}",
        "candidateSeedCount": 72,
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
    for key, value in exact.items():
        if identity.get(key) != value:
            raise SystemExit(f"future identity drift: {key}")
    for key in ("authorizationHead", "authorizationParent", "authorizationBlob", "authorizationSeedLedgerBlob"):
        if not _is_sha1(identity.get(key)):
            raise SystemExit(f"future identity invalid SHA-1: {key}")
    for key in ("candidateSeedCanonicalSha256", "candidateRowsCanonicalSha256"):
        if not _is_sha256(identity.get(key)):
            raise SystemExit(f"future identity invalid SHA-256: {key}")
    if identity.get("candidateSeedCanonicalSha256") == OLD["seed"]:
        raise SystemExit("consumed recovery3 candidate seed identity cannot be reused")
    if identity.get("candidateRowsCanonicalSha256") == OLD["rows"]:
        raise SystemExit("consumed recovery3 candidate row identity cannot be reused")
    if not isinstance(identity.get("authorizationPr"), int) or identity["authorizationPr"] <= 0:
        raise SystemExit("future authorizationPr invalid")
    if not isinstance(identity.get("authorizationReviewRun"), int) or identity["authorizationReviewRun"] <= 0:
        raise SystemExit("future authorizationReviewRun invalid")
    if not isinstance(identity.get("authorizationReviewArtifact"), int) or identity["authorizationReviewArtifact"] <= 0:
        raise SystemExit("future authorizationReviewArtifact invalid")
    digest = identity.get("authorizationReviewDigest")
    if not isinstance(digest, str) or re.fullmatch(r"sha256:[0-9a-f]{64}", digest) is None:
        raise SystemExit("future authorizationReviewDigest invalid")
    for key in ("authorizationPath", "authorizationSeedLedgerPath"):
        value = identity.get(key)
        if not isinstance(value, str) or not value or value.startswith("/") or ".." in Path(value).parts:
            raise SystemExit(f"future path invalid: {key}")
    namespace = identity.get("seedNamespace")
    if not isinstance(namespace, str) or not namespace or len(namespace) > 256 or re.fullmatch(r"[A-Za-z0-9._:/=|+-]+", namespace) is None:
        raise SystemExit("future seedNamespace invalid")
    if namespace == OLD["namespace"]:
        raise SystemExit("consumed recovery3 seed namespace cannot be reused")
    synthetic = identity.get("syntheticReviewOnly")
    if synthetic is True:
        if namespace != SEED_NAMESPACE:
            raise SystemExit("synthetic review identity must use the explicit synthetic namespace")
        rows = derive_seed_rows(SEED_NAMESPACE)
        seeds = [int(row["seed"]) for row in rows]
        if canonical(seeds) != identity["candidateSeedCanonicalSha256"]:
            raise SystemExit("synthetic candidateSeedCanonicalSha256 drift")
        if canonical(rows) != identity["candidateRowsCanonicalSha256"]:
            raise SystemExit("synthetic candidateRowsCanonicalSha256 drift")
    elif synthetic is False:
        if namespace == SEED_NAMESPACE or namespace.startswith("synthetic-review-only|"):
            raise SystemExit("future scientific identity cannot reuse the synthetic review namespace")
    else:
        raise SystemExit("syntheticReviewOnly must be explicit boolean")
    return identity


def replace_exact(text: str, old: str, new: str, *, count: int | None = None, label: str) -> str:
    seen = text.count(old)
    if count is not None and seen != count:
        raise SystemExit(f"{label}: expected {count} occurrences, got {seen}")
    if seen == 0:
        raise SystemExit(f"{label}: source token absent")
    return text.replace(old, new)


def transform_adapter(identity: dict[str, Any]) -> str:
    text = SOURCE_ADAPTER.read_text()
    replacements = [
        (f'STAGE = "{OLD["stage"]}"', f'STAGE = "{STAGE}"'),
        (f'AUTH_STATUS = "{OLD["auth_status"]}"', f'AUTH_STATUS = "{AUTH_STATUS}"'),
        (f"ORDINAL = {OLD['ordinal']}", f"ORDINAL = {identity['scientificOrdinal']}"),
        (f'EXECUTION_KEY = "{OLD["execution_key"]}"', f'EXECUTION_KEY = "{identity["executionKey"]}"'),
        (f'AUTH_HEAD = "{OLD["auth_head"]}"', f'AUTH_HEAD = "{identity["authorizationHead"]}"'),
        (f"AUTH_PR = {OLD['auth_pr']}", f"AUTH_PR = {identity['authorizationPr']}"),
        (f'AUTH_BRANCH = "{OLD["auth_branch"]}"', f'AUTH_BRANCH = "{identity["authorizationBranch"]}"'),
        (f'DISPATCH_BRANCH = "{OLD["dispatch_branch"]}"', f'DISPATCH_BRANCH = "{identity["dispatchBranch"]}"'),
        (f'SEED_CANONICAL = "{OLD["seed"]}"', f'SEED_CANONICAL = "{identity["candidateSeedCanonicalSha256"]}"'),
        (f'ROWS_CANONICAL = "{OLD["rows"]}"', f'ROWS_CANONICAL = "{identity["candidateRowsCanonicalSha256"]}"'),
        (f'NAMESPACE = "{OLD["namespace"]}"', f'NAMESPACE = "{identity["seedNamespace"]}"'),
    ]
    for old, new in replacements:
        text = replace_exact(text, old, new, count=1, label="adapter identity")
    text = text.replace("recovery3", "recovery4")
    return text


def transform_executor(identity: dict[str, Any]) -> str:
    text = SOURCE_EXECUTOR.read_text()
    text = replace_exact(
        text,
        'CONTRACT_PATH=ROOT/"review/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3-runtime-identity-v1/identity-contract.review.json"',
        'CONTRACT_PATH=Path(__file__).with_name("runtime_contract.json")',
        count=1,
        label="executor contract path",
    )
    text = replace_exact(
        text,
        'c=json.loads((repository_root/CONTRACT_PATH.relative_to(ROOT)).read_text())',
        'c=json.loads(CONTRACT_PATH.read_text())',
        count=1,
        label="executor contract read",
    )
    replacements = [
        (f'STAGE="{OLD["stage"]}"', f'STAGE="{STAGE}"'),
        (f'GUARD_STATUS="{OLD["guard_status"]}"', f'GUARD_STATUS="{GUARD_STATUS}"'),
        (f"ORDINAL={OLD['ordinal']}", f"ORDINAL={identity['scientificOrdinal']}"),
        (f'EXECUTION_KEY="{OLD["execution_key"]}"', f'EXECUTION_KEY="{identity["executionKey"]}"'),
        (f'AUTH_HEAD="{OLD["auth_head"]}"', f'AUTH_HEAD="{identity["authorizationHead"]}"'),
        (f"AUTH_PR={OLD['auth_pr']}", f"AUTH_PR={identity['authorizationPr']}"),
        (f'DISPATCH_BRANCH="{OLD["dispatch_branch"]}"', f'DISPATCH_BRANCH="{identity["dispatchBranch"]}"'),
        (f'SEED_CANONICAL="{OLD["seed"]}"', f'SEED_CANONICAL="{identity["candidateSeedCanonicalSha256"]}"'),
    ]
    for old, new in replacements:
        text = replace_exact(text, old, new, count=1, label="executor identity")
    text = text.replace("recovery3", "recovery4")
    return text


def transform_aggregator(identity: dict[str, Any]) -> str:
    text = SOURCE_AGGREGATOR.read_text()
    text = replace_exact(
        text,
        'CONTRACT_PATH=ROOT/"review/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3-runtime-identity-v1/identity-contract.review.json"',
        'CONTRACT_PATH=Path(__file__).with_name("runtime_contract.json")',
        count=1,
        label="aggregator contract path",
    )
    text = replace_exact(
        text,
        'c=json.loads((root/CONTRACT_PATH.relative_to(ROOT)).read_text())',
        'c=json.loads(CONTRACT_PATH.read_text())',
        count=1,
        label="aggregator contract read",
    )
    replacements = [
        (f'STAGE="{OLD["stage"]}"', f'STAGE="{STAGE}"'),
        (f"ORDINAL={OLD['ordinal']}", f"ORDINAL={identity['scientificOrdinal']}"),
        (f'EXECUTION_KEY="{OLD["execution_key"]}"', f'EXECUTION_KEY="{identity["executionKey"]}"'),
        (f'AUTH_HEAD="{OLD["auth_head"]}"', f'AUTH_HEAD="{identity["authorizationHead"]}"'),
        (f'SEED_CANONICAL="{OLD["seed"]}"', f'SEED_CANONICAL="{identity["candidateSeedCanonicalSha256"]}"'),
    ]
    for old, new in replacements:
        text = replace_exact(text, old, new, count=1, label="aggregator identity")
    text = text.replace("recovery3", "recovery4")
    return text


def runtime_contract(identity: dict[str, Any]) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "stageId": STAGE,
        "status": "REVIEW_ONLY_EXECUTION_CONTROL_FROZEN_DISPATCH_NOT_AUTHORIZED",
        "scientificOrdinal": identity["scientificOrdinal"],
        "executionKey": identity["executionKey"],
        "authorizationHead": identity["authorizationHead"],
        "authorizationPr": identity["authorizationPr"],
        "candidateSeedCanonicalSha256": identity["candidateSeedCanonicalSha256"],
        "candidateRowsCanonicalSha256": identity["candidateRowsCanonicalSha256"],
        "sourceBindings": {
            "baseAdapterBlobSha1": EXPECTED_BLOBS[BASE_ADAPTER],
            "baseExecutorBlobSha1": "bb1e4276d6383127a6b7e820fc2568d87d5de4b0",
            "baseAggregatorBlobSha1": "ef24a0d30af3dfb46a6b764f3e426465da870fbe",
            "recovery3SourceWorkflowBlobSha1": EXPECTED_BLOBS[SOURCE_WORKFLOW],
            "recovery3SourceAdapterBlobSha1": EXPECTED_BLOBS[SOURCE_ADAPTER],
            "recovery3SourceExecutorBlobSha1": EXPECTED_BLOBS[SOURCE_EXECUTOR],
            "recovery3SourceAggregatorBlobSha1": EXPECTED_BLOBS[SOURCE_AGGREGATOR],
            "fourAliasDataTreeSha256": FOUR_ALIAS,
            "exactFourSpeciesProfileSha256": PROFILE_SHA256,
        },
        "caseDesign": {
            "expectedCaseCount": 360,
            "expectedGroupCount": 72,
            "expectedAnalysisCellCount": 24,
            "expectedStatesPerGroup": 5,
            "photonHistoriesPerCase": 20_000_000,
        },
        "resultOpeningAuthorized": False,
        "levelBOpeningAuthorized": False,
        "protectedHoldoutOpeningAuthorized": False,
        "productionAuthorized": False,
        "taylorOrJerusalemFitAuthorized": False,
        "newMappingAuthorized": False,
    }


def transform_workflow(identity: dict[str, Any], runtime_dir: str, executor_blob: str, aggregator_blob: str) -> str:
    text = SOURCE_WORKFLOW.read_text()
    ordinal = identity["scientificOrdinal"]
    tokens = [
        (OLD["auth_branch"], identity["authorizationBranch"]),
        (OLD["dispatch_branch"], identity["dispatchBranch"]),
        (OLD["execution_key"], identity["executionKey"]),
        (OLD["auth_head"], identity["authorizationHead"]),
        (OLD["auth_parent"], identity["authorizationParent"]),
        (str(OLD["review_run"]), str(identity["authorizationReviewRun"])),
        (str(OLD["review_artifact"]), str(identity["authorizationReviewArtifact"])),
        (OLD["review_digest"], identity["authorizationReviewDigest"]),
        (OLD["seed"], identity["candidateSeedCanonicalSha256"]),
        (OLD["rows"], identity["candidateRowsCanonicalSha256"]),
        (OLD["seed_ledger_path"], identity["authorizationSeedLedgerPath"]),
        (OLD["seed_ledger_blob"], identity["authorizationSeedLedgerBlob"]),
        (OLD["auth_path"], identity["authorizationPath"]),
        (OLD["auth_blob"], identity["authorizationBlob"]),
    ]
    for old, new in tokens:
        if old not in text:
            raise SystemExit(f"workflow identity source token absent: {old}")
        text = text.replace(old, new)
    text = text.replace("recovery3", "recovery4")
    text = text.replace("RECOVERY3", "RECOVERY4")
    text = text.replace("ordinal-44", f"ordinal-{ordinal}")
    text = text.replace("ORDINAL44", f"ORDINAL{ordinal}")
    text = text.replace("ordinal44", f"ordinal{ordinal}")
    text = text.replace("ordinal 44", f"ordinal {ordinal}")
    text = text.replace("'scientificOrdinal':44", f"'scientificOrdinal':{ordinal}")
    text = replace_exact(text, "  AUTH_PR: '718'", f"  AUTH_PR: '{identity['authorizationPr']}'", count=1, label="workflow auth PR env")
    text = text.replace(" pr=718", f" pr={identity['authorizationPr']}")
    text = text.replace("!=718", f"!={identity['authorizationPr']}")
    text = text.replace("'authorizationPr':718", f"'authorizationPr':{identity['authorizationPr']}")

    text = replace_exact(
        text,
        "  EXECUTOR_PATH: review/aerosol-vertical-profile-sensitivity-v2-executor-parity-v1/executor.py\n  AGGREGATOR_PATH: review/aerosol-vertical-profile-sensitivity-v2-aggregator-parity-v1/aggregator.py",
        f"  RUNTIME_DIR: {runtime_dir}\n  RUNTIME_ADAPTER_PATH: {runtime_dir}/runtime_adapter.py\n  EXECUTOR_PATH: {runtime_dir}/executor.py\n  AGGREGATOR_PATH: {runtime_dir}/aggregator.py",
        count=1,
        label="workflow runtime path env",
    )
    text = replace_exact(
        text,
        "p=Path('review/aerosol-vertical-profile-sensitivity-v2-control-v1/adapter.py')",
        "p=Path(os.environ['RUNTIME_ADAPTER_PATH'])",
        count=1,
        label="matrix adapter route",
    )
    text = replace_exact(
        text,
        'test "$(git rev-parse HEAD:$EXECUTOR_PATH)" = bb1e4276d6383127a6b7e820fc2568d87d5de4b0',
        f'test "$(git rev-parse HEAD:$EXECUTOR_PATH)" = {executor_blob}',
        count=1,
        label="executor blob route",
    )
    text = replace_exact(
        text,
        "PYTHONPATH=review/aerosol-vertical-profile-sensitivity-v2-executor-parity-v1 python - <<'PY'",
        "PYTHONPATH=\"$RUNTIME_DIR\" python - <<'PY'",
        count=1,
        label="case executor import route",
    )
    text = replace_exact(
        text,
        'test "$(git rev-parse HEAD:$AGGREGATOR_PATH)" = ef24a0d30af3dfb46a6b764f3e426465da870fbe',
        f'test "$(git rev-parse HEAD:$AGGREGATOR_PATH)" = {aggregator_blob}',
        count=1,
        label="aggregator blob route",
    )
    text = replace_exact(
        text,
        "PYTHONPATH=review/aerosol-vertical-profile-sensitivity-v2-aggregator-parity-v1 python - <<'PY'",
        "PYTHONPATH=\"$RUNTIME_DIR\" python - <<'PY'",
        count=1,
        label="closed aggregate import route",
    )
    download_cases = """      - uses: actions/download-artifact@v4
        with:
          pattern: avps-v2-case-*
          path: case-artifacts
"""
    download_preflight = f"""      - uses: actions/download-artifact@v4
        with:
          pattern: avps-v2-case-*
          path: case-artifacts
      - uses: actions/download-artifact@v4
        with:
          name: avps-v2-postconsumption-recovery4-preflight-ordinal-{ordinal}
          path: preflight
"""
    text = replace_exact(text, download_cases, download_preflight, count=1, label="closed aggregate preflight authorization download")
    text = replace_exact(
        text,
        "acquisition,verified=aggregator.aggregate(Path('.'),Path('case-artifacts'),Path('case-artifact-metadata.json'),workflow_run_id=int(os.environ['GITHUB_RUN_ID']))",
        "acquisition,verified=aggregator.aggregate(Path('.'),Path('case-artifacts'),Path('case-artifact-metadata.json'),Path('preflight/authorization.json'),workflow_run_id=int(os.environ['GITHUB_RUN_ID']))",
        count=1,
        label="closed aggregate authorization route",
    )
    return text


def generate(identity_path: Path, output_root: Path) -> dict[str, Any]:
    check_sources()
    identity = validate_identity(json.loads(identity_path.read_text()))
    runtime_dir = f"runtime-avps-v2-recovery4-ordinal{identity['scientificOrdinal']}-v1"
    out = output_root / runtime_dir
    out.mkdir(parents=True, exist_ok=False)

    adapter_text = transform_adapter(identity)
    executor_text = transform_executor(identity)
    aggregator_text = transform_aggregator(identity)
    contract = runtime_contract(identity)
    (out / "runtime_adapter.py").write_text(adapter_text, newline="\n")
    (out / "executor.py").write_text(executor_text, newline="\n")
    (out / "aggregator.py").write_text(aggregator_text, newline="\n")
    (out / "runtime_contract.json").write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", newline="\n")

    executor_blob = git_blob_sha1(out / "executor.py")
    aggregator_blob = git_blob_sha1(out / "aggregator.py")
    workflow = transform_workflow(identity, runtime_dir, executor_blob, aggregator_blob)
    workflow_name = "avps-v2-postconsumption-recovery4-science.yml"
    (output_root / workflow_name).write_text(workflow, newline="\n")

    outputs = {}
    for path in sorted([*out.iterdir(), output_root / workflow_name]):
        raw = path.read_bytes()
        outputs[str(path.relative_to(output_root))] = {
            "gitBlobSha1": git_blob_sha1_bytes(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "size": len(raw),
        }
    manifest = {
        "schemaVersion": 1,
        "status": "GENERATED_AVPS_V2_RECOVERY4_SUCCESSOR_INFRASTRUCTURE_ZERO_RUNTIME_RESULTS_CLOSED",
        "scientificOrdinal": identity["scientificOrdinal"],
        "syntheticReviewOnly": bool(identity.get("syntheticReviewOnly", False)),
        "stageId": STAGE,
        "authorizationStatus": AUTH_STATUS,
        "guardStatus": GUARD_STATUS,
        "runtimeDir": runtime_dir,
        "workflow": workflow_name,
        "candidateSeedCanonicalSha256": identity["candidateSeedCanonicalSha256"],
        "candidateRowsCanonicalSha256": identity["candidateRowsCanonicalSha256"],
        "seedNamespaceSelectedByInfrastructure": False,
        "realCandidateRowsDerivedByInfrastructure": False,
        "caseCount": 360,
        "groupCount": 72,
        "statesPerGroup": 5,
        "photonHistoriesPerCase": 20_000_000,
        "matrixUsesGeneratedRecoveryAdapter": True,
        "caseUsesGeneratedRecoveryExecutor": True,
        "closedAggregateUsesGeneratedRecoveryAggregator": True,
        "frozenScienceChanged": False,
        "dispatchCreated": False,
        "scientificRuntime": False,
        "solverExecution": False,
        "resultsOpened": False,
        "levelBOpeningAuthorized": False,
        "protectedHoldoutOpeningAuthorized": False,
        "productionAuthorized": False,
        "taylorOrJerusalemUsed": False,
        "newMappingAuthorized": False,
        "outputs": outputs,
    }
    (output_root / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", newline="\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--identity", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("output path already exists")
    args.output.mkdir(parents=True)
    manifest = generate(args.identity, args.output)
    print(json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    main()
