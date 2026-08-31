#!/usr/bin/env python3
"""Capture small DQR/DQPR/quality-document excerpts from the preserved ARM order.

This is intentionally conservative: only files whose relative paths clearly look
like quality/readme/manifest documentation are considered, binary-looking files
are skipped, and at most a bounded prefix is exported. Source hashes come from
archive_inventory.csv so no second whole-archive hash pass is required.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Sequence

QUALITY_PATH_RE = re.compile(r"(?:dqr|dqpr|data[_ -]?quality|quality|readme|manifest|release[_ -]?notes)", re.I)
TEXT_SUFFIXES = {".txt", ".csv", ".json", ".xml", ".html", ".htm", ".md", ".log", ".yaml", ".yml"}
MAX_SOURCE_BYTES = 10 * 1024 * 1024
MAX_EXCERPT_BYTES = 64 * 1024


def looks_textual(data: bytes) -> bool:
    if not data:
        return True
    if b"\x00" in data:
        return False
    printable = sum(1 for byte in data if byte in b"\t\n\r" or 32 <= byte <= 126 or byte >= 128)
    return printable / len(data) >= 0.90


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-root", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    archive_root = args.archive_root.resolve()
    rows = []
    with args.inventory.open("r", encoding="utf-8-sig", newline="") as fh:
        inventory = list(csv.DictReader(fh))

    for record in inventory:
        relative = record.get("relative_path", "")
        if not relative or not QUALITY_PATH_RE.search(relative):
            continue
        source = archive_root / Path(relative)
        if source.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            size = int(record.get("size_bytes") or source.stat().st_size)
        except Exception:
            continue
        if size > MAX_SOURCE_BYTES:
            rows.append({
                "relative_path": relative,
                "source_sha256": record.get("sha256", ""),
                "size_bytes": size,
                "excerpt_bytes": 0,
                "truncated": True,
                "disposition": "SKIPPED_TOO_LARGE",
                "text": "",
            })
            continue
        try:
            with source.open("rb") as fh:
                data = fh.read(MAX_EXCERPT_BYTES + 1)
            truncated = len(data) > MAX_EXCERPT_BYTES or size > MAX_EXCERPT_BYTES
            data = data[:MAX_EXCERPT_BYTES]
            if not looks_textual(data):
                disposition = "SKIPPED_BINARY_LOOKING"
                text = ""
            else:
                disposition = "EXCERPTED"
                text = data.decode("utf-8-sig", errors="replace")
            rows.append({
                "relative_path": relative,
                "source_sha256": record.get("sha256", ""),
                "size_bytes": size,
                "excerpt_bytes": len(data) if text else 0,
                "truncated": bool(truncated),
                "disposition": disposition,
                "text": text,
            })
        except Exception as exc:
            rows.append({
                "relative_path": relative,
                "source_sha256": record.get("sha256", ""),
                "size_bytes": size,
                "excerpt_bytes": 0,
                "truncated": False,
                "disposition": f"READ_ERROR:{type(exc).__name__}:{exc}",
                "text": "",
            })

    with args.output.open("w", encoding="utf-8", newline="\n") as fh:
        for row in sorted(rows, key=lambda item: item["relative_path"]):
            fh.write(json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"quality-document candidates: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
