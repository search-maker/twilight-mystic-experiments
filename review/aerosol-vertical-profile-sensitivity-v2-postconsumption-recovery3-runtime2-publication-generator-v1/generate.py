from __future__ import annotations

import hashlib
import json
import runpy
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "generated-avps-v2-recovery3-ordinal44-runtime2-publication"
RUNTIME_IDENTITY_GENERATOR = ROOT / "review/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3-runtime-identity-v1/generate.py"
RUNTIME_IDENTITY_OUT = ROOT / "generated-avps-v2-recovery3-ordinal44-runtime-identity"
SOURCE_SCIENCE = ROOT / ".github/workflows/avps-v2-postconsumption-recovery3-science.yml"
SOURCE_PUBLISHER = ROOT / ".github/workflows/avps-v2-postconsumption-recovery3-dispatch-publisher.yml"
SOURCE_TRIGGER = ROOT / ".github/workflows/avps-v2-postconsumption-recovery3-publisher-trigger-bridge.yml"

SOURCE_BLOBS = {
    RUNTIME_IDENTITY_GENERATOR: "83313122917bb5da2bbb94107dfaf0e11ca18458",
    ROOT / "review/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3-runtime-identity-v1/test_generated.py": "ac27392f8ef979490701d1dcb610520f0e99cda3",
    SOURCE_SCIENCE: "ddc2bb954cf07c4c7f314c3d551a8aee44381c73",
    SOURCE_PUBLISHER: "10099ff88e169b6b820469d6d19ce5003c6f46bb",
    SOURCE_TRIGGER: "63a897d49cf7832f882fe16227ff3023a73c46ec",
}

RUNTIME_DIR = "runtime-avps-v2-recovery3-ordinal44-v1"
SCIENCE_NAME = "avps-v2-postconsumption-recovery3-runtime2-science.yml"
PUBLISHER_NAME = "avps-v2-postconsumption-recovery3-runtime2-dispatch-publisher.yml"
TRIGGER_NAME = "avps-v2-postconsumption-recovery3-runtime2-publisher-trigger-bridge.yml"
PUBLICATION_REVIEW_WORKFLOW = "avps-v2-recovery3-ordinal44-runtime2-publication-review.yml"
PUBLICATION_REVIEW_ARTIFACT = "avps-v2-recovery3-ordinal44-runtime2-publication-review"
ADMISSIBLE_PREFIX = "AVPS_V2_RECOVERY3_ORDINAL44_RUNTIME2_EXECUTION_PACKAGE_CORRECTED_ADMISSIBLE"
CONTROLLING_DEFECT = 5470658421

EXPECTED_RUNTIME = {
    "runtime_adapter.py": {
        "sha256": "1d9eb949c284b5194990c3fd23d2e54fdab83527b937b2cfcff937353da7921f",
        "blob": "9fce4f704040d7849b59ed96577d02e5aeecd455",
    },
    "executor.py": {
        "sha256": "85b411892bfea7699c232c0acd7a13132337b56f5f3df2cbf39688f03f0a7105",
        "blob": "643c0d5b499747a8529a2a58c659ee24a7fd2a60",
    },
    "aggregator.py": {
        "sha256": "631d6cc1fd070841bc5c0c071bac9df790c96a6f7093211759680ccaf4cad8c2",
        "blob": "abe8522d7e3562eef9f2c807911871916627fa96",
    },
}


def git_blob_sha1_bytes(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def git_blob_sha1(path: Path) -> str:
    return git_blob_sha1_bytes(path.read_bytes())


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def check_source_bytes() -> None:
    for path, expected in SOURCE_BLOBS.items():
        if not path.is_file() or git_blob_sha1(path) != expected:
            raise SystemExit(f"bound source byte drift: {path}")


def replace_required(text: str, old: str, new: str, label: str, *, minimum: int = 1) -> str:
    count = text.count(old)
    if count < minimum:
        raise SystemExit(f"required replacement missing ({label}): {old!r}; count={count}")
    return text.replace(old, new)


def generate_runtime() -> dict[str, bytes]:
    if RUNTIME_IDENTITY_OUT.exists():
        shutil.rmtree(RUNTIME_IDENTITY_OUT)
    runpy.run_path(str(RUNTIME_IDENTITY_GENERATOR), run_name="__main__")
    outputs: dict[str, bytes] = {}
    for name, expected in EXPECTED_RUNTIME.items():
        path = RUNTIME_IDENTITY_OUT / name
        raw = path.read_bytes()
        if sha256(raw) != expected["sha256"] or git_blob_sha1_bytes(raw) != expected["blob"]:
            raise SystemExit(f"reviewed runtime byte drift: {name}")
        outputs[name] = raw
    return outputs


def transform_science(source: str) -> str:
    text = source
    text = replace_required(text, "name: AVPS v2 scientific execution", "name: AVPS v2 recovery3 ordinal44 runtime2 scientific execution", "science name")
    text = replace_required(text, "run-name: AVPS v2 postconsumption recovery3 ordinal 44 |", "run-name: AVPS v2 postconsumption recovery3 runtime2 ordinal 44 |", "science run-name")
    text = replace_required(text, "avps-v2-postconsumption-recovery3-science.yml", SCIENCE_NAME, "science filename self references")
    text = replace_required(text, "review/aerosol-vertical-profile-sensitivity-v2-executor-parity-v1/executor.py", f"{RUNTIME_DIR}/executor.py", "executor route")
    text = replace_required(text, "review/aerosol-vertical-profile-sensitivity-v2-aggregator-parity-v1/aggregator.py", f"{RUNTIME_DIR}/aggregator.py", "aggregator route")
    text = text.replace("avps-v2-postconsumption-recovery3-ordinal-44-science", "avps-v2-postconsumption-recovery3-runtime2-ordinal-44-science")
    if "review/aerosol-vertical-profile-sensitivity-v2-executor-parity-v1/executor.py" in text:
        raise SystemExit("old executor runtime route survived")
    if "review/aerosol-vertical-profile-sensitivity-v2-aggregator-parity-v1/aggregator.py" in text:
        raise SystemExit("old aggregator runtime route survived")
    return text


def transform_publisher(source: str) -> str:
    text = source
    text = replace_required(text, "name: AVPS v2 recovery3 ordinal44 dispatch publisher", "name: AVPS v2 recovery3 ordinal44 runtime2 dispatch publisher", "publisher name")
    text = replace_required(text, "run-name: AVPS v2 postconsumption recovery3 ordinal 44 zero-runtime dispatch publisher", "run-name: AVPS v2 postconsumption recovery3 runtime2 ordinal 44 zero-runtime dispatch publisher", "publisher run-name")
    text = text.replace("avps-v2-postconsumption-recovery3-ordinal-44-dispatch-publisher", "avps-v2-postconsumption-recovery3-runtime2-ordinal-44-dispatch-publisher")
    text = replace_required(text, "avps-v2-postconsumption-recovery3-science.yml", SCIENCE_NAME, "publisher science filename")
    text = replace_required(text, "avps-v2-postconsumption-recovery3-dispatch-publisher.yml", PUBLISHER_NAME, "publisher filename self references")
    text = replace_required(text, "avps-v2-postconsumption-recovery3-publisher-trigger-bridge.yml", TRIGGER_NAME, "publisher trigger filename")
    text = replace_required(text, "PACKAGE_REVIEW_WORKFLOW: avps-v2-recovery3-ordinal44-snapshot-choreography-correction-review.yml", f"PACKAGE_REVIEW_WORKFLOW: {PUBLICATION_REVIEW_WORKFLOW}", "package review workflow")
    text = replace_required(text, "PACKAGE_REVIEW_ARTIFACT: avps-v2-recovery3-ordinal44-snapshot-choreography-correction-review", f"PACKAGE_REVIEW_ARTIFACT: {PUBLICATION_REVIEW_ARTIFACT}", "package review artifact")
    text = replace_required(text, "not_admissible=5470357989", f"not_admissible={CONTROLLING_DEFECT}", "controlling defect")
    text = replace_required(text, "prefix='AVPS_V2_RECOVERY3_ORDINAL44_EXECUTION_PACKAGE_CORRECTED_ADMISSIBLE'", f"prefix='{ADMISSIBLE_PREFIX}'", "fresh admissibility prefix")
    text = replace_required(text, "PASS_AVPS_V2_RECOVERY3_ORDINAL44_SNAPSHOT_CHOREOGRAPHY_CORRECTION_REVIEW_ZERO_RUNTIME", "PASS_AVPS_V2_RECOVERY3_ORDINAL44_RUNTIME2_PUBLICATION_REVIEW_ZERO_RUNTIME", "publication review status")
    text = text.replace("avps-v2-postconsumption-recovery3-dispatch-publisher-ordinal-44", "avps-v2-postconsumption-recovery3-runtime2-dispatch-publisher-ordinal-44")
    if "not_admissible=5470357989" in text or "AVPS_V2_RECOVERY3_ORDINAL44_EXECUTION_PACKAGE_CORRECTED_ADMISSIBLE" in text:
        raise SystemExit("stale publisher admissibility binding survived")
    return text


def transform_trigger(source: str, publisher_blob: str) -> str:
    text = source
    text = replace_required(text, "name: AVPS v2 publisher postconsumption-recovery3-ordinal44 trigger bridge", "name: AVPS v2 publisher postconsumption-recovery3-runtime2-ordinal44 trigger bridge", "trigger name")
    text = replace_required(text, "run-name: AVPS v2 postconsumption recovery3 ordinal 44 publisher postconsumption-recovery3-ordinal44 trigger bridge", "run-name: AVPS v2 postconsumption recovery3 runtime2 ordinal 44 publisher trigger bridge", "trigger run-name")
    text = replace_required(text, "dispatch-trigger/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3-ordinal-44-publisher", "dispatch-trigger/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3-runtime2-ordinal-44-publisher", "activation branch")
    text = replace_required(text, "dispatch-triggers/avps-v2-postconsumption-recovery3-ordinal44-publisher.txt", "dispatch-triggers/avps-v2-postconsumption-recovery3-runtime2-ordinal44-publisher.txt", "activation marker")
    text = replace_required(text, "avps-v2-postconsumption-recovery3-dispatch-publisher.yml", PUBLISHER_NAME, "trigger publisher filename")
    text = replace_required(text, "PUBLISHER_BLOB: 10099ff88e169b6b820469d6d19ce5003c6f46bb", f"PUBLISHER_BLOB: {publisher_blob}", "trigger publisher blob")
    text = replace_required(text, "AVPS_V2_POSTCONSUMPTION_RECOVERY3_ORDINAL44_PUBLISHER_TRIGGER_V1", "AVPS_V2_POSTCONSUMPTION_RECOVERY3_RUNTIME2_ORDINAL44_PUBLISHER_TRIGGER_V1", "activation schema")
    text = text.replace("avps-v2-postconsumption-recovery3-ordinal-44-publisher-trigger-bridge", "avps-v2-postconsumption-recovery3-runtime2-ordinal-44-publisher-trigger-bridge")
    text = text.replace("postconsumption-recovery3-ordinal44-publisher", "postconsumption-recovery3-runtime2-ordinal44-publisher")
    return text


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    check_source_bytes()
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    runtime = generate_runtime()
    for name, raw in runtime.items():
        dest = OUT / RUNTIME_DIR / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)

    science = transform_science(SOURCE_SCIENCE.read_text(encoding="utf-8"))
    publisher = transform_publisher(SOURCE_PUBLISHER.read_text(encoding="utf-8"))
    publisher_blob = git_blob_sha1_bytes(publisher.encode())
    trigger = transform_trigger(SOURCE_TRIGGER.read_text(encoding="utf-8"), publisher_blob)

    write_text(OUT / ".github/workflows" / SCIENCE_NAME, science)
    write_text(OUT / ".github/workflows" / PUBLISHER_NAME, publisher)
    write_text(OUT / ".github/workflows" / TRIGGER_NAME, trigger)

    files = {}
    for path in sorted(p for p in OUT.rglob("*") if p.is_file()):
        rel = path.relative_to(OUT).as_posix()
        raw = path.read_bytes()
        files[rel] = {"sha256": sha256(raw), "gitBlobSha1": git_blob_sha1_bytes(raw), "size": len(raw)}

    expected_paths = sorted([
        f"{RUNTIME_DIR}/runtime_adapter.py",
        f"{RUNTIME_DIR}/executor.py",
        f"{RUNTIME_DIR}/aggregator.py",
        f".github/workflows/{SCIENCE_NAME}",
        f".github/workflows/{PUBLISHER_NAME}",
        f".github/workflows/{TRIGGER_NAME}",
    ])
    if sorted(files) != expected_paths:
        raise SystemExit(f"generated publication file set drift: {sorted(files)}")

    manifest = {
        "schemaVersion": 1,
        "status": "GENERATED_AVPS_V2_RECOVERY3_ORDINAL44_RUNTIME2_PUBLICATION_ZERO_RUNTIME",
        "sourceMain": "8e7498f58b219467ee3a17f9503a5b68b7d105eb",
        "controllingDefectComment": CONTROLLING_DEFECT,
        "runtimeIdentityGateMerge": "8e7498f58b219467ee3a17f9503a5b68b7d105eb",
        "scientificOrdinal": 44,
        "authorizationHead": "dd3a4c692af505389e9feb1e5f5480fa389110a3",
        "authorizationPr": 718,
        "candidateSeedCanonicalSha256": "d2817b1ea4f2bdc8cb1842e565b099b015e4e28c5874482629fadc450069d9bf",
        "candidateRowsCanonicalSha256": "b6a519eadacdb99ea53c52d483c8acfeba05829643cb988de21682a53fc47896",
        "caseCount": 360,
        "groupCount": 72,
        "statesPerGroup": 5,
        "photonHistoriesPerCase": 20_000_000,
        "admissibilityMarkerPrefix": ADMISSIBLE_PREFIX,
        "publisherBlob": publisher_blob,
        "frozenScienceChanged": False,
        "dispatchCreated": False,
        "scientificRuntime": False,
        "solverExecution": False,
        "resultsOpened": False,
        "levelB": False,
        "holdout": False,
        "taylorOrJerusalemUsed": False,
        "lowAltitudeEvidenceUsed": False,
        "newMappingAuthorized": False,
        "files": files,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    main()
