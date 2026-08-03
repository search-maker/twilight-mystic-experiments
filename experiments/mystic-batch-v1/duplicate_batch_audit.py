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
WORKFLOW = "mystic-batch-v1-execution.yml"


class DuplicateRefusal(RuntimeError):
    pass


def expected_title(batch_id: str, manifest_sha256: str, authorization_ref: str, authorization_ordinal: int) -> str:
    return (
        f"MYSTIC batch v1 | batch={batch_id} | manifest={manifest_sha256} | "
        f"auth={authorization_ref} | ordinal={authorization_ordinal}"
    )


def evaluate(payload: dict[str, Any], current_run_id: int, title: str) -> dict[str, Any]:
    runs = payload.get("workflow_runs")
    total = payload.get("total_count")
    if not isinstance(runs, list) or not isinstance(total, int):
        raise DuplicateRefusal("malformed workflow-run response")
    if total > len(runs):
        raise DuplicateRefusal("workflow-run scan is incomplete")
    current = [run for run in runs if run.get("id") == current_run_id]
    if len(current) != 1:
        raise DuplicateRefusal("current workflow run was not found exactly once")
    run = current[0]
    if run.get("display_title") != title:
        raise DuplicateRefusal("current workflow title does not match the frozen marker")
    if run.get("event") != "workflow_dispatch" or run.get("run_attempt") != 1:
        raise DuplicateRefusal("current workflow is not the exact first workflow_dispatch attempt")
    duplicates = [
        {
            "id": candidate.get("id"),
            "status": candidate.get("status"),
            "conclusion": candidate.get("conclusion"),
            "run_attempt": candidate.get("run_attempt"),
        }
        for candidate in runs
        if candidate.get("id") != current_run_id and candidate.get("display_title") == title
    ]
    if duplicates:
        raise DuplicateRefusal(f"prior workflow run already used this exact batch authorization: {duplicates}")
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "PASS",
        "currentRunId": current_run_id,
        "displayTitle": title,
        "matchingPriorRunCount": 0,
        "boundary": "duplicate audit completed before runtime installation, syntax check, or solver execution",
    }


def fetch_runs(repository: str, workflow: str, token: str) -> dict[str, Any]:
    encoded_workflow = urllib.parse.quote(workflow, safe="")
    url = (
        f"https://api.github.com/repos/{repository}/actions/workflows/{encoded_workflow}/runs"
        "?event=workflow_dispatch&per_page=100"
    )
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


def self_test() -> dict[str, Any]:
    title = expected_title("batch-a", "b" * 64, "c" * 40, 1)
    current = {
        "id": 20,
        "display_title": title,
        "event": "workflow_dispatch",
        "run_attempt": 1,
        "status": "in_progress",
        "conclusion": None,
    }
    result = evaluate({"total_count": 1, "workflow_runs": [current]}, 20, title)
    duplicate = {**current, "id": 10, "status": "completed", "conclusion": "failure"}
    try:
        evaluate({"total_count": 2, "workflow_runs": [current, duplicate]}, 20, title)
    except DuplicateRefusal:
        pass
    else:
        raise AssertionError("duplicate self-test did not refuse")
    return {"schemaVersion": 1, "stageId": STAGE_ID, "status": "PASS", "result": result}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository")
    parser.add_argument("--workflow", default=WORKFLOW)
    parser.add_argument("--current-run-id", type=int)
    parser.add_argument("--batch-id")
    parser.add_argument("--manifest-sha256")
    parser.add_argument("--authorization-ref")
    parser.add_argument("--authorization-ordinal", type=int)
    parser.add_argument("--token")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            print(json.dumps(self_test(), indent=2, sort_keys=True))
            return 0
        required = (
            args.repository,
            args.current_run_id,
            args.batch_id,
            args.manifest_sha256,
            args.authorization_ref,
            args.authorization_ordinal,
            args.token,
            args.output,
        )
        if not all(required):
            raise DuplicateRefusal("runtime arguments missing")
        title = expected_title(
            args.batch_id,
            args.manifest_sha256,
            args.authorization_ref,
            args.authorization_ordinal,
        )
        result = evaluate(fetch_runs(args.repository, args.workflow, args.token), args.current_run_id, title)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        refusal = {
            "schemaVersion": 1,
            "stageId": STAGE_ID,
            "status": "REFUSED_BEFORE_RUNTIME_OR_SOLVER",
            "reason": str(exc),
        }
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(refusal, indent=2, sort_keys=True) + "\n")
        print(json.dumps(refusal, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
