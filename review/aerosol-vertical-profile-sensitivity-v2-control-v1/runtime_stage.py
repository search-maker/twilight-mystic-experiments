from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
DEPENDENCY_PATH = HERE / "rh_audit_dependency.py"
EXPECTED_DEPENDENCY_BLOB = "095ff86f12a79dc312a51f734b0a03bd318f2337"
EXPECTED_ARCHIVE_SHA256 = "11daa1f1f4be0fd4ddf7e881ec2005498049674a1540d37b4b1e8f5e16052c7e"
EXPECTED_ARCHIVE_SIZE = 743_391_266
EXPECTED_BASE_DATA_TREE_SHA256 = "ad30b49177e9c84e46497d69faf0c75e466996b0d0003f1de210289ae9f847d7"
EXPECTED_ARCHIVE_STAGED_TREE_SHA256 = "5d8bbf8e6b91ec3d405dee36f21a94afbb6e5ec6cd67da2dd5dd541738199d80"
EXPECTED_FOUR_ALIAS_TREE_SHA256 = "5e1814dd36cf861fd85477a97607299248f8272268df7bf428d31bbb6aa4354a"
EXPECTED_UVSPEC_SHA256 = "2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3"
EXPECTED_AFGL_SHA256 = "dab26290ed81c762ed0c607e5dc2d53393c1462a0c3a528bc5e3f5935191cfb5"
EXPECTED_SPECIES = ("INSO", "WASO", "SOOT", "SUSO")


class RuntimeStageRefusal(RuntimeError):
    pass


def git_blob_sha1(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _dependency():
    if git_blob_sha1(DEPENDENCY_PATH) != EXPECTED_DEPENDENCY_BLOB:
        raise RuntimeStageRefusal("bound OPAC staging helper byte drift")
    spec = importlib.util.spec_from_file_location("avps_v2_control_rh_dependency", DEPENDENCY_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeStageRefusal("cannot load bound OPAC staging helper")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def stage_frozen_opac(archive: Path, runtime_root: Path) -> dict[str, Any]:
    if not archive.is_file() or archive.stat().st_size != EXPECTED_ARCHIVE_SIZE:
        raise RuntimeStageRefusal("official OPAC archive size drift")
    if sha256_file(archive) != EXPECTED_ARCHIVE_SHA256:
        raise RuntimeStageRefusal("official OPAC archive SHA drift")
    dep = _dependency()
    archive_meta = dep.extract_frozen_archive(archive, runtime_root / "share" / "libRadtran")
    data_dir = runtime_root / "share" / "libRadtran" / "data"
    aliases = dep.prepare_no_extension_aliases(data_dir)
    if aliases.get("status") != "FOUR_NO_EXTENSION_ALIASES_READY":
        raise RuntimeStageRefusal("four no-extension aliases were not created")
    rows = aliases.get("aliases") or []
    if tuple(row.get("species") for row in rows) != EXPECTED_SPECIES:
        raise RuntimeStageRefusal("four-alias species order/set drift")
    if sha256_file(data_dir / "atmmod" / "afglus.dat") != EXPECTED_AFGL_SHA256:
        raise RuntimeStageRefusal("AFGL-US identity drift after staging")
    return {
        "schemaVersion": 1,
        "status": "FROZEN_OPAC_ARCHIVE_AND_FOUR_NO_EXTENSION_ALIASES_STAGED",
        "archive": archive_meta,
        "aliases": aliases,
        "dataDir": str(data_dir.resolve()),
        "expectedArchiveStagedTreeSha256": EXPECTED_ARCHIVE_STAGED_TREE_SHA256,
        "expectedFourAliasTreeSha256": EXPECTED_FOUR_ALIAS_TREE_SHA256,
        "scientificSolverExecuted": False,
        "scientificOrdinalAllocated": False,
    }


def validate_runtime_reports(base: dict[str, Any], pre_alias: dict[str, Any], post_alias: dict[str, Any]) -> dict[str, Any]:
    if base.get("uvspecSha256") != EXPECTED_UVSPEC_SHA256:
        raise RuntimeStageRefusal("locked uvspec SHA drift")
    if base.get("libRadtranDataTreeSha256") != EXPECTED_BASE_DATA_TREE_SHA256:
        raise RuntimeStageRefusal("locked base libRadtran data-tree drift")
    if pre_alias.get("libRadtranDataTreeSha256") != EXPECTED_ARCHIVE_STAGED_TREE_SHA256:
        raise RuntimeStageRefusal("staged official OPAC archive tree drift")
    if post_alias.get("libRadtranDataTreeSha256") != EXPECTED_FOUR_ALIAS_TREE_SHA256:
        raise RuntimeStageRefusal("four-alias data-tree drift")
    for report in (base, pre_alias, post_alias):
        if report.get("scientificSolverExecuted") is not False:
            raise RuntimeStageRefusal("runtime identity report crossed solver boundary")
    return {
        "schemaVersion": 1,
        "status": "PASS_FROZEN_BASE_ARCHIVE_AND_FOUR_ALIAS_RUNTIME_IDENTITIES",
        "uvspecSha256": EXPECTED_UVSPEC_SHA256,
        "baseDataTreeSha256": EXPECTED_BASE_DATA_TREE_SHA256,
        "archiveStagedDataTreeSha256": EXPECTED_ARCHIVE_STAGED_TREE_SHA256,
        "fourAliasDataTreeSha256": EXPECTED_FOUR_ALIAS_TREE_SHA256,
        "afglSha256": EXPECTED_AFGL_SHA256,
        "scientificSolverExecuted": False,
    }


def review_summary() -> dict[str, Any]:
    _dependency()
    return {
        "status": "REVIEW_ONLY_RUNTIME_STAGING_BOUND_NO_ARCHIVE_DOWNLOAD_NO_SOLVER",
        "dependencyGitBlobSha1": EXPECTED_DEPENDENCY_BLOB,
        "archiveSha256": EXPECTED_ARCHIVE_SHA256,
        "archiveSize": EXPECTED_ARCHIVE_SIZE,
        "baseDataTreeSha256": EXPECTED_BASE_DATA_TREE_SHA256,
        "archiveStagedDataTreeSha256": EXPECTED_ARCHIVE_STAGED_TREE_SHA256,
        "fourAliasDataTreeSha256": EXPECTED_FOUR_ALIAS_TREE_SHA256,
        "uvspecSha256": EXPECTED_UVSPEC_SHA256,
        "afglSha256": EXPECTED_AFGL_SHA256,
        "scientificOrdinalAllocated": False,
        "solverExecutionAuthorized": False,
    }


if __name__ == "__main__":
    print(json.dumps(review_summary(), indent=2, sort_keys=True))
