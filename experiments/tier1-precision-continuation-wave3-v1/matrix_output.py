#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


class Refusal(RuntimeError):
    pass


def matrix_value(manifest: dict[str, Any]) -> str:
    cases = manifest.get("cases")
    case_count = manifest.get("caseCount")
    geometry_count = manifest.get("geometryCount")
    if (
        not isinstance(cases, list)
        or not isinstance(case_count, int)
        or not isinstance(geometry_count, int)
        or geometry_count <= 0
        or case_count != 2 * geometry_count
        or len(cases) != case_count
    ):
        raise Refusal("dynamic execution manifest case cardinality changed")
    include = []
    seen = set()
    for row in cases:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("caseId"), str)
            or not row["caseId"]
            or row.get("block") not in (7, 8)
        ):
            raise Refusal("matrix case identity missing or outside b7-b8")
        case_id = row["caseId"]
        if case_id in seen:
            raise Refusal("duplicate matrix case identity")
        seen.add(case_id)
        include.append({"caseId": case_id, "timeoutSeconds": 2400})
    return json.dumps(
        {"include": include}, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def append_github_output(manifest_path: Path, output_path: Path) -> None:
    value = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Refusal("manifest root must be an object")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(f"matrix={matrix_value(value)}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--github-output", type=Path, required=True)
    args = parser.parse_args()
    append_github_output(args.manifest, args.github_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
