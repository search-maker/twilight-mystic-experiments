#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

STAGE_ID = "mystic-batch-v1"
TITLE_PREFIX = "MYSTIC batch v1 "


class DuplicateRefusal(RuntimeError):
    pass


def expected_title(execution_key: str, authorization_ref: str, ordinal: int) -> str:
    return f"{TITLE_PREFIX}| key={execution_key} | auth={authorization_ref} | ordinal={ordinal}"


def one_shot_marker(title: str) -> str:
    if not title.startswith(TITLE_PREFIX):
        raise DuplicateRefusal("internal expected title has wrong prefix")
    marker = title[len(TITLE_PREFIX):]
    if not marker.startswith("| key=") or " | auth=" not in marker or " | ordinal=" not in marker:
        raise DuplicateRefusal("internal one-shot marker is malformed")
    return marker


def display_title_matches(display_title: Any, marker: str) -> bool:
    return isinstance(display_title, str) and display_title.endswith(marker)


def evaluate(payload: dict[str, Any], current_run_id: int, title: str) -> dict[str, Any]:
    runs = payload.get("workflow_runs")
    total = payload.get("total_count")
    if not isinstance(runs, list) or not isinstance(total, int):
        raise DuplicateRefusal("malformed workflow-run response")
    if total > len(runs):
        raise DuplicateRefusal("workflow-run scan is incomplete; refusing rather than risk a duplicate")
    current = [run for run in runs if run.get("id") == current_run_id]
    if len(current) != 1:
        raise DuplicateRefusal("current workflow run was not found exactly once")
    run = current[0]
    marker = one_shot_marker(title)
    actual_title = run.get("display_title")
    if not display_title_matches(actual_title, marker):
        raise DuplicateRefusal("current workflow title does not match one-shot marker")
    if run.get("event") != "workflow_dispatch" or run.get("run_attempt") != 1:
        raise DuplicateRefusal("current run is not an exact first-attempt workflow_dispatch")
    duplicates = [
        {"id": item.get("id"), "status": item.get("status"), "conclusion": item.get("conclusion")}
        for item in runs
        if item.get("id") != current_run_id and display_title_matches(item.get("display_title"), marker)
    ]
    if duplicates:
        raise DuplicateRefusal(f"one-shot marker was already used: {duplicates}")
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "PASS",
        "currentRunId": current_run_id,
        "displayTitle": actual_title,
        "oneShotMarker": marker,
        "matchingPriorRunCount": 0,
        "boundary": "duplicate audit completed before syntax check or solver execution",
    }


def fetch_runs(repository: str, workflow: str, token: str) -> dict[str, Any]:
    encoded = urllib.parse.quote(workflow, safe="")
    url = f"https://api.github.com/repos/{repository}/actions/workflows/{encoded}/runs?event=workflow_dispatch&per_page=100"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "mystic-batch-v1-duplicate-audit",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--current-run-id", type=int, required=True)
    parser.add_argument("--execution-key", required=True)
    parser.add_argument("--authorization-ref", required=True)
    parser.add_argument("--authorization-ordinal", type=int, required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    title = expected_title(args.execution_key, args.authorization_ref, args.authorization_ordinal)
    try:
        result = evaluate(fetch_runs(args.repository, args.workflow, args.token), args.current_run_id, title)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        refusal = {
            "schemaVersion": 1,
            "stageId": STAGE_ID,
            "status": "REFUSED_BEFORE_SYNTAX_OR_SOLVER",
            "reason": str(exc),
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(refusal, indent=2, sort_keys=True) + "\n")
        print(json.dumps(refusal, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
