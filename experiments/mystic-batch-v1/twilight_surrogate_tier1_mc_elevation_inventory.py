#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "twilight-surrogate-tier-1-mc-elevation-inventory-v1"
TOKENS = ("mc_elevation_file", "elevation_file")
MAX_TEXT_BYTES = 5_000_000
MAX_MATCHES = 500


class InventoryError(RuntimeError):
    pass


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def raw_sha256(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def text_matches(prefix: Path) -> list[dict[str, Any]]:
    roots = [prefix / "share" / "libRadtran", prefix / "conda-meta"]
    matches: list[dict[str, Any]] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.stat().st_size > MAX_TEXT_BYTES:
                continue
            data = path.read_bytes()
            if b"\x00" in data[:4096]:
                continue
            text = data.decode("utf-8", errors="replace")
            for line_number, line in enumerate(text.splitlines(), start=1):
                if any(token in line for token in TOKENS):
                    matches.append({
                        "path": str(path.relative_to(prefix)),
                        "lineNumber": line_number,
                        "line": line[:2000],
                    })
                    if len(matches) >= MAX_MATCHES:
                        return matches
    return matches


def inventory(uvspec: Path, prefix: Path, output_dir: Path) -> dict[str, Any]:
    if not uvspec.is_file():
        raise InventoryError(f"uvspec missing: {uvspec}")
    if not prefix.is_dir():
        raise InventoryError(f"runtime prefix missing: {prefix}")
    output_dir.mkdir(parents=True, exist_ok=True)

    help_process = subprocess.run(
        [str(uvspec.resolve()), "-h"],
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )
    help_text = help_process.stdout + help_process.stderr
    (output_dir / "uvspec-help.txt").write_text(help_text)

    binary = uvspec.read_bytes()
    binary_tokens = {
        token: token.encode() in binary
        for token in TOKENS
    }
    matches = text_matches(prefix)
    (output_dir / "text-matches.json").write_text(dump(matches))

    metadata_files = sorted((prefix / "conda-meta").glob("rubin-libradtran-*.json"))
    metadata_hashes = {str(path.relative_to(prefix)): raw_sha256(path) for path in metadata_files}

    result = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "INVENTORY_CAPTURED_NO_SEMANTIC_VALIDATION",
        "scientificExecution": False,
        "scientificDatasetProduced": False,
        "syntaxCheckCount": 0,
        "solverExecutionCount": 0,
        "authorizationPermitted": False,
        "ordinal2ScientificDispatchPermitted": False,
        "uvspecSha256": raw_sha256(uvspec),
        "uvspecHelpExitCode": help_process.returncode,
        "uvspecHelpSha256": sha_bytes(help_text.encode()),
        "uvspecBinaryTokenPresence": binary_tokens,
        "installedTextMatchCount": len(matches),
        "installedTextMatches": matches,
        "packageMetadataRawSha256": metadata_hashes,
        "semanticConclusionPermitted": False,
        "requiredNextStep": "inspect primary runtime/package evidence, then design a separate constant-elevation mc_elevation_file probe without a Tier-1 dataset",
        "boundary": "installed-runtime option inventory only; no inferred file format, no terrain model, no scientific run, authorization, dispatch, training, or production use",
    }
    (output_dir / "inventory.json").write_text(dump(result))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--uvspec", type=Path, required=True)
    parser.add_argument("--prefix", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = inventory(args.uvspec, args.prefix, args.output_dir)
        print(dump(result), end="")
        return 0
    except Exception as exc:
        print(dump({"schemaVersion": 1, "stageId": STAGE_ID, "status": "REFUSED", "reason": str(exc)}), file=sys.stderr, end="")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
