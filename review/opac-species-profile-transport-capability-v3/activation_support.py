from __future__ import annotations

import hashlib
import json
import os
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any

EXPECTED_ARCHIVE_SHA256 = "11daa1f1f4be0fd4ddf7e881ec2005498049674a1540d37b4b1e8f5e16052c7e"
EXPECTED_ARCHIVE_SIZE = 743_391_266
EXPECTED_ARCHIVE_MEMBERS = 28
EXPECTED_BASE_DATA_SHA256 = "ad30b49177e9c84e46497d69faf0c75e466996b0d0003f1de210289ae9f847d7"
EXPECTED_STAGED_DATA_SHA256 = "5d8bbf8e6b91ec3d405dee36f21a94afbb6e5ec6cd67da2dd5dd541738199d80"
EXPECTED_UVSPEC_SHA256 = "2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def extract_frozen_opac_archive(archive: Path, libradtran_root: Path) -> dict[str, Any]:
    raw = archive.read_bytes()
    if len(raw) != EXPECTED_ARCHIVE_SIZE:
        raise RuntimeError(f"OPAC archive size drift: {len(raw)}")
    if sha256_bytes(raw) != EXPECTED_ARCHIVE_SHA256:
        raise RuntimeError("OPAC archive SHA drift")
    with tarfile.open(archive, "r:gz") as tf:
        members = tf.getmembers()
        if len(members) != EXPECTED_ARCHIVE_MEMBERS:
            raise RuntimeError(f"OPAC member-count drift: {len(members)}")
        plan: list[tuple[tarfile.TarInfo, Path]] = []
        for member in members:
            rel = PurePosixPath(member.name)
            dest = libradtran_root.joinpath(*rel.parts)
            if (
                not member.isfile()
                or rel.is_absolute()
                or ".." in rel.parts
                or not rel.parts
                or rel.parts[0] != "data"
                or dest.exists()
            ):
                raise RuntimeError(f"unsafe/colliding OPAC member: {member.name}")
            plan.append((member, dest))
        for member, dest in plan:
            src = tf.extractfile(member)
            if src is None:
                raise RuntimeError(f"cannot stream OPAC member: {member.name}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("xb") as out:
                while True:
                    block = src.read(1024 * 1024)
                    if not block:
                        break
                    out.write(block)
    return {
        "schemaVersion": 1,
        "status": "FROZEN_OPAC_ARCHIVE_EXTRACTED",
        "archiveSha256": EXPECTED_ARCHIVE_SHA256,
        "archiveSize": EXPECTED_ARCHIVE_SIZE,
        "memberCount": EXPECTED_ARCHIVE_MEMBERS,
    }


def validate_runtime_reports(base: dict[str, Any], pre: dict[str, Any], post: dict[str, Any], alias: dict[str, Any]) -> dict[str, Any]:
    if base.get("uvspecSha256") != EXPECTED_UVSPEC_SHA256:
        raise RuntimeError("uvspec SHA drift")
    if base.get("libRadtranDataTreeSha256") != EXPECTED_BASE_DATA_SHA256:
        raise RuntimeError("base data-tree SHA drift")
    if pre.get("libRadtranDataTreeSha256") != EXPECTED_STAGED_DATA_SHA256:
        raise RuntimeError("pre-alias staged tree SHA drift")
    if not alias.get("byteIdentical"):
        raise RuntimeError("resolver alias is not byte-identical")
    if alias.get("sourceSha256") != alias.get("aliasSha256") or int(alias.get("byteCount") or 0) <= 0:
        raise RuntimeError("resolver alias provenance drift")
    if post.get("libRadtranDataTreeSha256") == pre.get("libRadtranDataTreeSha256"):
        raise RuntimeError("post-alias data tree unexpectedly unchanged")
    if int(post.get("libRadtranDataFileCount") or 0) != int(pre.get("libRadtranDataFileCount") or 0) + 1:
        raise RuntimeError("post-alias data-file count drift")
    if int(post.get("libRadtranDataByteCount") or 0) != int(pre.get("libRadtranDataByteCount") or 0) + int(alias["byteCount"]):
        raise RuntimeError("post-alias data-byte count drift")
    return {
        "schemaVersion": 1,
        "status": "POST_ALIAS_RUNTIME_PROVENANCE_VALIDATED",
        "preAliasDataTreeSha256": pre["libRadtranDataTreeSha256"],
        "postAliasDataTreeSha256": post["libRadtranDataTreeSha256"],
        "resolverAlias": alias,
    }


def _file_sha(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def freeze_capability_report(evidence: Path, run_id: int) -> dict[str, Any]:
    disort_low = _file_sha(evidence / "disort-low.out")
    disort_high = _file_sha(evidence / "disort-high.out")
    mystic_low = _file_sha(evidence / "mystic-low-mc.rad.spc")
    mystic_high = _file_sha(evidence / "mystic-high-mc.rad.spc")
    pre = json.loads((evidence / "pre-alias-runtime-report.json").read_text()) if (evidence / "pre-alias-runtime-report.json").is_file() else {}
    post = json.loads((evidence / "post-alias-runtime-report.json").read_text()) if (evidence / "post-alias-runtime-report.json").is_file() else {}
    manifest = json.loads((evidence / "input-manifest.json").read_text()) if (evidence / "input-manifest.json").is_file() else {}
    disort_diff = bool(disort_low and disort_high and disort_low != disort_high)
    mystic_diff = bool(mystic_low and mystic_high and mystic_low != mystic_high)
    out = {
        "schemaVersion": 1,
        "stageId": "opac-species-profile-transport-capability-v3",
        "status": "PASS_CORRECTED_EXPLICIT_SPECIES_PROFILE_REACHES_DISORT_AND_MYSTIC" if disort_diff and mystic_diff else "FAILED_BEFORE_REQUIRED_COMPARISONS",
        "workflowRunId": int(run_id),
        "workflowRunAttempt": 1,
        "preAliasDataTreeSha256": pre.get("libRadtranDataTreeSha256"),
        "postAliasDataTreeSha256": post.get("libRadtranDataTreeSha256"),
        "resolverAlias": manifest.get("resolverAlias"),
        "disortOutputsDiffer": disort_diff,
        "mysticRadianceOutputsDiffer": mystic_diff,
        "scientificOrdinalAllocated": False,
        "taylorOrJerusalemUsed": False,
        "productionAuthorized": False,
        "levelBInferenceAuthorized": False,
        "scientificMaterialityThresholdCreated": False,
    }
    raw = json.dumps(out, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    out["contentSha256"] = hashlib.sha256(raw).hexdigest()
    (evidence / "capability-report.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    return out
