from __future__ import annotations

import hashlib
import shutil
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any

EXPECTED_ARCHIVE_SHA256 = "11daa1f1f4be0fd4ddf7e881ec2005498049674a1540d37b4b1e8f5e16052c7e"
EXPECTED_ARCHIVE_SIZE = 743_391_266
EXPECTED_BASE_DATA_TREE_SHA256 = "ad30b49177e9c84e46497d69faf0c75e466996b0d0003f1de210289ae9f847d7"
EXPECTED_AUGMENTED_DATA_TREE_SHA256 = "5d8bbf8e6b91ec3d405dee36f21a94afbb6e5ec6cd67da2dd5dd541738199d80"
EXPECTED_ARCHIVE_MEMBER_COUNT = 28


class OverlayRefusal(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_sha256(root: Path) -> tuple[str, int, int]:
    if not root.is_dir():
        raise OverlayRefusal(f"data directory not found: {root}")
    digest = hashlib.sha256()
    file_count = 0
    byte_count = 0
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        content_hash = sha256_file(path).encode("ascii")
        size = path.stat().st_size
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(size.to_bytes(8, "big"))
        digest.update(content_hash)
        file_count += 1
        byte_count += size
    if file_count == 0:
        raise OverlayRefusal("data directory contains no files")
    return digest.hexdigest(), file_count, byte_count


def validate_archive_members(archive: Path) -> list[tarfile.TarInfo]:
    if not archive.is_file():
        raise OverlayRefusal("optprop archive missing")
    if archive.stat().st_size != EXPECTED_ARCHIVE_SIZE:
        raise OverlayRefusal("official optprop archive size drift")
    if sha256_file(archive) != EXPECTED_ARCHIVE_SHA256:
        raise OverlayRefusal("official optprop archive SHA-256 drift")
    with tarfile.open(archive, "r:gz") as tf:
        members = tf.getmembers()
    if len(members) != EXPECTED_ARCHIVE_MEMBER_COUNT:
        raise OverlayRefusal(f"archive member-count drift: {len(members)}")
    for member in members:
        path = PurePosixPath(member.name)
        if not member.isfile():
            raise OverlayRefusal(f"non-regular archive member forbidden: {member.name}")
        if path.is_absolute() or ".." in path.parts or not path.parts or path.parts[0] != "data":
            raise OverlayRefusal(f"unsafe/out-of-root archive path: {member.name}")
    return members


def _copy_base(base_data_dir: Path, output_libradtran_root: Path) -> Path:
    base_hash, _, _ = tree_sha256(base_data_dir)
    if base_hash != EXPECTED_BASE_DATA_TREE_SHA256:
        raise OverlayRefusal("base libRadtran data-tree SHA-256 drift")
    if output_libradtran_root.exists():
        raise OverlayRefusal("overlay destination already exists; silent overwrite forbidden")
    output_libradtran_root.mkdir(parents=True, exist_ok=False)
    output_data_dir = output_libradtran_root / "data"
    shutil.copytree(base_data_dir, output_data_dir, copy_function=shutil.copy2)
    staged_hash, staged_count, staged_bytes = tree_sha256(output_data_dir)
    if staged_hash != EXPECTED_BASE_DATA_TREE_SHA256:
        raise OverlayRefusal("staged base data-tree differs from frozen base")
    return output_data_dir


def stage_frozen_overlay(base_data_dir: Path, archive: Path, output_libradtran_root: Path) -> dict[str, Any]:
    members = validate_archive_members(archive)
    output_data_dir = _copy_base(base_data_dir, output_libradtran_root)
    added: list[dict[str, Any]] = []
    with tarfile.open(archive, "r:gz") as tf:
        by_name = {member.name: member for member in tf.getmembers()}
        for member in members:
            path = PurePosixPath(member.name)
            destination = output_libradtran_root.joinpath(*path.parts)
            if destination.exists():
                raise OverlayRefusal(f"overlay collision forbidden: {member.name}")
            source = tf.extractfile(by_name[member.name])
            if source is None:
                raise OverlayRefusal(f"cannot stream archive member: {member.name}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha256()
            total = 0
            with destination.open("xb") as out:
                while True:
                    block = source.read(1024 * 1024)
                    if not block:
                        break
                    digest.update(block)
                    out.write(block)
                    total += len(block)
            if total != member.size:
                raise OverlayRefusal(f"extracted size mismatch: {member.name}")
            observed = sha256_file(destination)
            if observed != digest.hexdigest():
                raise OverlayRefusal(f"post-write hash mismatch: {member.name}")
            added.append({"path": member.name, "size": member.size, "sha256": observed})
    final_hash, final_count, final_bytes = tree_sha256(output_data_dir)
    if final_hash != EXPECTED_AUGMENTED_DATA_TREE_SHA256:
        raise OverlayRefusal("augmented libRadtran data-tree SHA-256 drift")
    return {
        "schemaVersion": 1,
        "status": "FROZEN_OPAC_RUNTIME_OVERLAY_STAGED",
        "archiveSha256": EXPECTED_ARCHIVE_SHA256,
        "archiveSizeBytes": EXPECTED_ARCHIVE_SIZE,
        "baseDataTreeSha256": EXPECTED_BASE_DATA_TREE_SHA256,
        "augmentedDataTreeSha256": final_hash,
        "addedMemberCount": len(added),
        "addedMembers": added,
        "finalDataFileCount": final_count,
        "finalDataByteCount": final_bytes,
        "scientificSolverExecuted": False,
        "syntaxCheckExecuted": False,
    }
