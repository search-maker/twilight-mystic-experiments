#!/usr/bin/env python3
"""Fail-closed control-plane verifier for the authorized ARM E0 workflow run.

This module never contacts ARM Live and never reads artifact contents. It binds a
future sanitized E0 artifact to the exact GitHub Actions execution authorized by
Issue #60 comment 5575796491 before the existing post-artifact verifier is used.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

AUTHORITY_COMMENT = 5575796491
FROZEN_BRANCH = "review/arm-ena-sws-v1-stage0"
FROZEN_HEAD = "b8671665a2bf8fe9972b8cb48492abcfa6765140"
WORKFLOW_PATH = ".github/workflows/arm-ena-sws-e0-oneevent-auth-runtime-v1.yml"
ARTIFACT_NAME = "arm-ena-sws-e0-oneevent-auth-v1"
DIGEST_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")


class EnvelopeVerificationError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise EnvelopeVerificationError(message)


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"invalid JSON in {path}: {type(exc).__name__}")


def _require_object(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"{where} must be a JSON object")
    return value


def _positive_int(value: Any, where: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        fail(f"{where} must be a positive integer")
    return value


def verify_run(run_payload: Any) -> dict[str, Any]:
    run = _require_object(run_payload, "run payload")
    run_id = _positive_int(run.get("id"), "run id")
    exact = {
        "event": "workflow_dispatch",
        "run_attempt": 1,
        "head_branch": FROZEN_BRANCH,
        "head_sha": FROZEN_HEAD,
        "path": WORKFLOW_PATH,
        "status": "completed",
        "conclusion": "success",
    }
    for key, expected in exact.items():
        if run.get(key) != expected:
            fail(f"run {key} mismatch: expected {expected!r}, got {run.get(key)!r}")
    if run.get("previous_attempt_url") is not None:
        fail("run has previous_attempt_url; attempt1 must not be a rerun/retry")
    return run


def verify_dispatch_inventory(inventory_payload: Any, run_id: int) -> None:
    payload = _require_object(inventory_payload, "dispatch inventory")
    runs = payload.get("workflow_runs")
    if not isinstance(runs, list):
        fail("dispatch inventory workflow_runs must be a list")
    total_count = payload.get("total_count")
    if not isinstance(total_count, int) or isinstance(total_count, bool) or total_count < 0:
        fail("dispatch inventory total_count must be a nonnegative integer")
    if total_count != len(runs):
        fail("dispatch inventory is not complete in the supplied JSON page set")

    exact_surface: list[dict[str, Any]] = []
    for index, item in enumerate(runs, 1):
        row = _require_object(item, f"dispatch inventory row {index}")
        if row.get("event") == "workflow_dispatch" and row.get("path") == WORKFLOW_PATH and row.get("head_branch") == FROZEN_BRANCH:
            exact_surface.append(row)

    if len(exact_surface) != 1:
        fail(f"expected exactly one E0 workflow_dispatch on the frozen branch, found {len(exact_surface)}")
    only = exact_surface[0]
    if only.get("id") != run_id:
        fail("dispatch inventory run id does not match selected run")
    if only.get("head_sha") != FROZEN_HEAD:
        fail("dispatch inventory E0 run is not bound to the frozen head")
    if only.get("run_attempt") != 1:
        fail("dispatch inventory E0 run is not attempt1")


def verify_artifacts(artifacts_payload: Any, run: dict[str, Any]) -> dict[str, Any]:
    payload = _require_object(artifacts_payload, "artifact payload")
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list):
        fail("artifact payload artifacts must be a list")
    total_count = payload.get("total_count")
    if total_count != len(artifacts):
        fail("artifact payload total_count does not match supplied artifacts")
    if len(artifacts) != 1:
        fail(f"expected exactly one artifact from frozen E0 workflow, found {len(artifacts)}")

    artifact = _require_object(artifacts[0], "artifact row")
    _positive_int(artifact.get("id"), "artifact id")
    if artifact.get("name") != ARTIFACT_NAME:
        fail(f"artifact name mismatch: {artifact.get('name')!r}")
    if artifact.get("expired") is not False:
        fail("artifact is expired or expiration state is not false")
    digest = artifact.get("digest")
    if not isinstance(digest, str) or DIGEST_RE.fullmatch(digest) is None:
        fail("artifact lacks a canonical GitHub SHA-256 digest")

    wr = _require_object(artifact.get("workflow_run"), "artifact workflow_run binding")
    if wr.get("id") != run.get("id"):
        fail("artifact workflow_run id does not match selected run")
    if wr.get("head_branch") != FROZEN_BRANCH:
        fail("artifact workflow_run branch does not match frozen branch")
    if wr.get("head_sha") != FROZEN_HEAD:
        fail("artifact workflow_run head does not match frozen head")
    return artifact


def verify_envelope(run_payload: Any, artifacts_payload: Any, inventory_payload: Any) -> dict[str, Any]:
    run = verify_run(run_payload)
    run_id = int(run["id"])
    verify_dispatch_inventory(inventory_payload, run_id)
    artifact = verify_artifacts(artifacts_payload, run)
    return {
        "schema": 1,
        "status": "ARM_E0_AUTHORIZED_RUN_ENVELOPE_VERIFIED",
        "authority_comment": AUTHORITY_COMMENT,
        "run_id": run_id,
        "run_attempt": 1,
        "event": "workflow_dispatch",
        "execution_branch": FROZEN_BRANCH,
        "execution_head": FROZEN_HEAD,
        "workflow_path": WORKFLOW_PATH,
        "artifact_id": artifact["id"],
        "artifact_name": ARTIFACT_NAME,
        "artifact_digest": artifact["digest"],
        "duplicate_e0_dispatches": 0,
        "protected_results_opened": False,
        "stage_b_authorized": False,
        "heldout_radiance_opening_authorized": False,
        "science_execution_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-json", type=Path, required=True)
    parser.add_argument("--artifacts-json", type=Path, required=True)
    parser.add_argument("--dispatch-inventory-json", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify_envelope(
        read_json(args.run_json),
        read_json(args.artifacts_json),
        read_json(args.dispatch_inventory_json),
    )
    rendered = json.dumps(result, sort_keys=True, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
