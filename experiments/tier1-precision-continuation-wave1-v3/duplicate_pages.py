#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


class Refusal(RuntimeError):
    pass


REQUIRED_RUN_FIELDS = {
    "id",
    "display_title",
    "status",
    "conclusion",
    "event",
    "run_attempt",
    "head_sha",
    "head_branch",
}


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def flatten_pages(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise Refusal("paginated run evidence must be a nonempty page array")
    rows: list[dict[str, Any]] = []
    seen: set[int] = set()
    for page_index, page in enumerate(value):
        if not isinstance(page, dict):
            raise Refusal(f"run page {page_index} is not an object")
        page_runs = page.get("workflow_runs")
        if not isinstance(page_runs, list):
            raise Refusal(f"run page {page_index} lacks workflow_runs array")
        for row_index, row in enumerate(page_runs):
            if not isinstance(row, dict):
                raise Refusal(f"run page {page_index} row {row_index} is malformed")
            missing = sorted(REQUIRED_RUN_FIELDS - set(row))
            if missing:
                raise Refusal(f"run metadata missing fields: {missing}")
            run_id = row["id"]
            if not isinstance(run_id, int) or isinstance(run_id, bool) or run_id <= 0:
                raise Refusal("run id must be a positive integer")
            if run_id in seen:
                raise Refusal(f"duplicate run id across pages: {run_id}")
            if not isinstance(row["display_title"], str) or not row["display_title"]:
                raise Refusal("run display title missing")
            if row["run_attempt"] != 1:
                raise Refusal("run history contains a forbidden retry attempt")
            seen.add(run_id)
            rows.append({key: row[key] for key in sorted(REQUIRED_RUN_FIELDS)})
    return sorted(rows, key=lambda item: item["id"], reverse=True)


def duplicate_audit(
    rows: list[dict[str, Any]],
    *,
    current_run_id: int,
    candidate_title: str,
) -> dict[str, Any]:
    if not isinstance(current_run_id, int) or current_run_id <= 0:
        raise Refusal("current run id missing")
    if not isinstance(candidate_title, str) or not candidate_title:
        raise Refusal("candidate title missing")
    matches = [
        {
            "id": row["id"],
            "status": row["status"],
            "conclusion": row["conclusion"],
        }
        for row in rows
        if row["id"] != current_run_id and row["display_title"] == candidate_title
    ]
    if matches:
        raise Refusal(f"prior matching execution title exists: {matches}")
    current = [row for row in rows if row["id"] == current_run_id]
    if len(current) != 1 or current[0]["display_title"] != candidate_title:
        raise Refusal("current run is absent or has a different title")
    return {
        "schemaVersion": 1,
        "status": "NO_PRIOR_MATCHING_RUN",
        "candidateTitle": candidate_title,
        "currentRunId": current_run_id,
        "inspectedRunCount": len(rows),
        "matchingRuns": [],
        "searchCompletedBeforeRuntimeOrSolver": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = json.loads(args.pages.read_text(encoding="utf-8"))
    args.output.write_text(dump(flatten_pages(value)), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
