#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

STAGE = "reference-vroom-v2"
WORKFLOW = "reference-vroom-v2-execution.yml"


class Refusal(RuntimeError):
    pass


def expected_title(execution_key: str, authorization_ref: str, authorization_ordinal: int) -> str:
    return f"Reference VROOM v2 | key={execution_key} | auth={authorization_ref} | ordinal={authorization_ordinal}"


def evaluate(payload: dict[str, Any], current_run_id: int, title: str) -> dict[str, Any]:
    runs = payload.get("workflow_runs")
    total = payload.get("total_count")
    if not isinstance(runs, list) or not isinstance(total, int):
        raise Refusal("malformed workflow-run response")
    if total > len(runs):
        raise Refusal("workflow-run scan is incomplete")

    current = [run for run in runs if run.get("id") == current_run_id]
    if len(current) != 1:
        raise Refusal("current workflow run was not found exactly once")
    current_run = current[0]
    if current_run.get("display_title") != title:
        raise Refusal("current workflow title does not match the frozen marker")
    if current_run.get("event") != "workflow_dispatch":
        raise Refusal("current workflow event is not workflow_dispatch")
    if current_run.get("run_attempt") != 1:
        raise Refusal("current workflow run attempt is not one")

    duplicates = [
        {
            "id": run.get("id"),
            "status": run.get("status"),
            "conclusion": run.get("conclusion"),
            "run_attempt": run.get("run_attempt"),
        }
        for run in runs
        if run.get("id") != current_run_id and run.get("display_title") == title
    ]
    if duplicates:
        raise Refusal(f"prior workflow run already used this one-shot marker: {duplicates}")

    return {
        "schemaVersion": 1,
        "stageId": STAGE,
        "status": "PASS",
        "currentRunId": current_run_id,
        "displayTitle": title,
        "matchingPriorRunCount": 0,
        "boundary": "duplicate audit completed before syntax check or solver execution",
    }


def fetch_runs(repository: str, workflow: str, token: str) -> dict[str, Any]:
    encoded_workflow = urllib.parse.quote(workflow, safe="")
    url = f"https://api.github.com/repos/{repository}/actions/workflows/{encoded_workflow}/runs?event=workflow_dispatch&per_page=100"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "reference-vroom-v2-duplicate-audit",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def self_test() -> dict[str, Any]:
    title = expected_title(STAGE, "a" * 40, 1)
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
    except Refusal:
        pass
    else:
        raise AssertionError("duplicate self-test did not refuse")
    return {"schemaVersion": 1, "stageId": STAGE, "status": "PASS", "result": result}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository")
    parser.add_argument("--workflow", default=WORKFLOW)
    parser.add_argument("--current-run-id", type=int)
    parser.add_argument("--execution-key")
    parser.add_argument("--authorization-ref")
    parser.add_argument("--authorization-ordinal", type=int)
    parser.add_argument("--token")
    parser.add_argument("--output")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    try:
        if args.self_test:
            print(json.dumps(self_test(), indent=2, sort_keys=True))
            return 0
        required = (
            args.repository,
            args.current_run_id,
            args.execution_key,
            args.authorization_ref,
            args.authorization_ordinal,
            args.token,
            args.output,
        )
        if not all(required):
            raise Refusal("runtime arguments missing")
        title = expected_title(args.execution_key, args.authorization_ref, args.authorization_ordinal)
        result = evaluate(fetch_runs(args.repository, args.workflow, args.token), args.current_run_id, title)
        Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        refusal = {
            "schemaVersion": 1,
            "stageId": STAGE,
            "status": "REFUSED_BEFORE_SYNTAX_OR_SOLVER",
            "reason": str(exc),
        }
        if args.output:
            Path(args.output).write_text(json.dumps(refusal, indent=2, sort_keys=True) + "\n")
        print(json.dumps(refusal, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
