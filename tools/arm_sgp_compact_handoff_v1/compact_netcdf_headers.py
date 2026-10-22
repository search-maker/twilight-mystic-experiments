#!/usr/bin/env python3
"""Compact broad per-file ARM NetCDF header rows into structural schema groups."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def normalize_header(header: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return structural header and observed-size metadata.

    Time/record counts vary between otherwise identical daily files, so raw
    dimension sizes and variable shape lengths are observations, not schema
    identity. Variable dtype/dimension names/attributes and nonvolatile global
    attributes remain part of the structural signature.
    """
    sizes = {
        "dimensions": {name: data.get("size") for name, data in header.get("dimensions", {}).items()},
        "variable_shapes": {name: data.get("shape", []) for name, data in header.get("variables", {}).items()},
    }
    structural = {
        "dimensions": {
            name: {"unlimited": bool(data.get("unlimited", False))}
            for name, data in header.get("dimensions", {}).items()
        },
        "global_attr_names": header.get("global_attr_names", []),
        "global_attrs_nonvolatile": header.get("global_attrs_nonvolatile", {}),
        "variables": {
            name: {
                "dtype": data.get("dtype"),
                "dimensions": data.get("dimensions", []),
                "attrs": data.get("attrs", {}),
            }
            for name, data in header.get("variables", {}).items()
        },
    }
    return structural, sizes


def merge_range(current: dict[str, list[int]], name: str, value: Any) -> None:
    if value is None:
        return
    try:
        ivalue = int(value)
    except Exception:
        return
    if name not in current:
        current[name] = [ivalue, ivalue]
    else:
        current[name][0] = min(current[name][0], ivalue)
        current[name][1] = max(current[name][1], ivalue)


def compact(path: Path) -> None:
    groups: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            structural, sizes = normalize_header(row["header"])
            key_payload = {"datastream": row.get("datastream", ""), "header": structural}
            signature = hashlib.sha256(canonical(key_payload)).hexdigest()
            group = groups.setdefault(signature, {
                "structural_schema_signature": signature,
                "datastream": row.get("datastream", ""),
                "example_file": row.get("example_file", ""),
                "source_schema_signatures": [],
                "observed_file_count": 0,
                "observed_dimension_size_ranges": {},
                "header": structural,
            })
            group["observed_file_count"] += 1
            source_signature = row.get("schema_signature")
            if source_signature and source_signature not in group["source_schema_signatures"]:
                group["source_schema_signatures"].append(source_signature)
            for name, value in sizes.get("dimensions", {}).items():
                merge_range(group["observed_dimension_size_ranges"], name, value)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for signature in sorted(groups):
            row = groups[signature]
            row["source_schema_signatures"] = sorted(row["source_schema_signatures"])
            fh.write(json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--headers", type=Path, required=True)
    args = parser.parse_args(argv)
    compact(args.headers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
