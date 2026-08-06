#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


class EnvelopeCompatibilityRefusal(RuntimeError):
    pass


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def require_sha256(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise EnvelopeCompatibilityRefusal(f"{label} must be lowercase raw SHA-256")
    return value


def normalize_envelope(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EnvelopeCompatibilityRefusal("envelope root must be an object")
    if value.get("stageId") != "twilight-surrogate-tier-1-dataset-envelope-v1":
        raise EnvelopeCompatibilityRefusal("unexpected envelope stage")
    bindings = value.get("bindings")
    if not isinstance(bindings, dict):
        raise EnvelopeCompatibilityRefusal("envelope bindings missing")
    audit_sha = require_sha256(bindings.get("auditRawSha256"), "auditRawSha256")
    existing = bindings.get("independentAuditRawSha256")
    if existing not in (None, audit_sha):
        raise EnvelopeCompatibilityRefusal(
            "independent-audit compatibility binding conflicts with audit binding"
        )
    bindings["independentAuditRawSha256"] = audit_sha
    value["bindings"] = bindings
    return value


def normalize_file(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EnvelopeCompatibilityRefusal(f"invalid envelope JSON: {path}") from exc
    normalized = normalize_envelope(value)
    path.write_text(dump(normalized), encoding="utf-8", newline="\n")
    return normalized


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--envelope", type=Path, required=True)
    args = parser.parse_args()
    normalized = normalize_file(args.envelope)
    print(
        dump(
            {
                "status": "CONTINUATION_ENVELOPE_ADAPTER_COMPATIBLE",
                "independentAuditRawSha256": normalized["bindings"][
                    "independentAuditRawSha256"
                ],
            }
        ),
        end="",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
