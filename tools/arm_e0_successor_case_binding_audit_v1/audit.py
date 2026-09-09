#!/usr/bin/env python3
"""Result-blind audit of ARM E0 successor case/provenance binding surfaces.

This tool performs no network access, reads no credentials or ARM artifacts, and
never opens protected SWS/SASZE values.  It freezes the exact source surfaces
that must be rebound before a query-selected E0 successor can be executed or
consumed.  The legacy one-event lane remains immutable/spent; this audit does
not authorize changing it or running protected science.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

STATUS = "ARM_E0_SUCCESSOR_REBIND_SURFACE_FROZEN"
LEGACY_CASE = "2017-06-16_dusk"
LEGACY_AUTHORITY_COMMENT = "5575796491"
FROZEN_SOURCE_REF = "review/arm-ena-sws-v1-stage0"
FROZEN_SOURCE_HEAD = "b8671665a2bf8fe9972b8cb48492abcfa6765140"
FROZEN_UNIVERSE_SHA256 = "87933189ff56322ce2b5d2821a1c2ab8094d0a472ef6c690cfbd90cd0451fa41"
FROZEN_PROTOCOL = "ARM_ENA_SWS_V1_STAGE0_E0_RESULT_BLIND_V2"

# These are deliberately source-level requirements. A future successor may be
# implemented separately, but it must not silently reuse any of these old
# bindings for a different query-selected case or authorization identity.
SURFACES: dict[str, tuple[str, tuple[str, ...]]] = {
    "portable_wrapper": (
        "review/arm-ena-sws-v1-stage0/run_one_ena_sws_schema_probe_v3.py",
        (
            'PROBE_CASE_ID = "2017-06-16_dusk"',
            '"--start-case", PROBE_CASE_ID',
        ),
    ),
    "content_verifier": (
        "tools/arm_ena_sws_e0_postartifact_v1/verify_oneevent_e0_artifact_v1.py",
        ('PROBE_CASE_ID = "2017-06-16_dusk"',),
    ),
    "strict_content_verifier": (
        "tools/arm_ena_sws_e0_postartifact_v1/verify_oneevent_e0_artifact_strict_v1.py",
        ("base.PROBE_CASE_ID",),
    ),
    "authorized_run_envelope": (
        "tools/arm_ena_sws_e0_postartifact_v1/verify_authorized_run_envelope_v1.py",
        (
            "AUTHORITY_COMMENT = 5575796491",
            'FROZEN_BRANCH = "review/arm-ena-sws-v1-stage0"',
            'FROZEN_HEAD = "b8671665a2bf8fe9972b8cb48492abcfa6765140"',
        ),
    ),
    "downloaded_zip_digest_gate": (
        "tools/arm_ena_sws_e0_postartifact_v1/verify_downloaded_artifact_zip_v1.py",
        (
            "AUTHORITY_COMMENT = 5575796491",
            'FROZEN_BRANCH = "review/arm-ena-sws-v1-stage0"',
            'FROZEN_HEAD = "b8671665a2bf8fe9972b8cb48492abcfa6765140"',
        ),
    ),
    "safe_extraction_gate": (
        "tools/arm_ena_sws_e0_postartifact_v1/extract_sanitized_artifact_zip_v1.py",
        (
            "AUTHORITY_COMMENT = 5575796491",
            'FROZEN_BRANCH = "review/arm-ena-sws-v1-stage0"',
            'FROZEN_HEAD = "b8671665a2bf8fe9972b8cb48492abcfa6765140"',
        ),
    ),
    "sanitized_ingest_pipeline": (
        "tools/arm_ena_sws_e0_postartifact_v1/run_sanitized_ingest_pipeline_v1.py",
        ("content_gate.base.PROBE_CASE_ID",),
    ),
}

RUNNER_PATH = "review/arm-ena-sws-v1-stage0/run_ena_sws_e0_frozen_v3.py"
RUNNER_REQUIRED_TOKENS = (
    "known, remaining = pre.parse_known_args()",
    'sys.argv = [sys.argv[0]] + ["--e0-script", str(e0_path)] + remaining',
)
RUNNER_FORBIDDEN_TOKENS = (
    'PROBE_CASE_ID = "2017-06-16_dusk"',
)


class AuditRefusal(RuntimeError):
    """Fail-closed source/preparation drift."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_source(root: Path, rel: str) -> tuple[str, str]:
    path = root / rel
    if path.is_symlink() or not path.is_file():
        raise AuditRefusal(f"required source path missing/not regular: {rel}")
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise AuditRefusal(f"required source is not UTF-8 text: {rel}") from None
    return text, sha256_bytes(raw)


def audit_source_tree(root: Path) -> dict[str, Any]:
    root = root.resolve()
    if not root.is_dir():
        raise AuditRefusal("repository root is not a directory")

    observed: dict[str, Any] = {}
    for role, (rel, tokens) in SURFACES.items():
        text, digest = read_source(root, rel)
        missing = [token for token in tokens if token not in text]
        if missing:
            raise AuditRefusal(f"{role} source binding drift; missing tokens={missing!r}")
        observed[role] = {
            "path": rel,
            "sha256": digest,
            "legacy_binding_tokens_present": list(tokens),
        }

    runner_text, runner_digest = read_source(root, RUNNER_PATH)
    missing_runner = [token for token in RUNNER_REQUIRED_TOKENS if token not in runner_text]
    if missing_runner:
        raise AuditRefusal(f"lower frozen runner forwarding contract drift; missing={missing_runner!r}")
    forbidden_runner = [token for token in RUNNER_FORBIDDEN_TOKENS if token in runner_text]
    if forbidden_runner:
        raise AuditRefusal(f"lower frozen runner unexpectedly acquired legacy case hard-pin={forbidden_runner!r}")

    return {
        "schema": 1,
        "status": STATUS,
        "purpose": "result-blind preregistration of all known E0 successor case/provenance rebind surfaces",
        "legacy_case_id": LEGACY_CASE,
        "legacy_authority_comment": LEGACY_AUTHORITY_COMMENT,
        "frozen_e0_source_ref": FROZEN_SOURCE_REF,
        "frozen_e0_source_head": FROZEN_SOURCE_HEAD,
        "frozen_e0_event_universe_sha256": FROZEN_UNIVERSE_SHA256,
        "frozen_e0_protocol": FROZEN_PROTOCOL,
        "legacy_rebind_surfaces": observed,
        "lower_frozen_runner": {
            "path": RUNNER_PATH,
            "sha256": runner_digest,
            "selected_case_passthrough_capable": True,
            "legacy_case_hardpin_present": False,
        },
        "successor_requirements": [
            "bind the query-selected case mechanically from an accepted freeze receipt before execution",
            "bind the exact future E0 authorization/run envelope separately from legacy authority 5575796491",
            "make artifact-digest and safe-extraction receipts use that same future run envelope",
            "make strict postartifact verification use that same selected case without legacy-case fallback",
            "make sanitized ingest cross-bind the same selected case and future run envelope",
            "preserve frozen E0 science source/head/universe/protocol unless separately authorized",
            "preserve result-blind firewall: no protected SWS/SASZE values, Stage B, MYSTIC science, or production authority",
        ],
        "arm_network_access_performed": False,
        "arm_credentials_read": False,
        "native_file_download_performed": False,
        "native_file_open_performed": False,
        "protected_sws_sasze_values_read": False,
        "heldout_radiance_opening_authorized": False,
        "stage_b_authorized": False,
        "mystic_science_authorized": False,
        "production_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        result = audit_source_tree(args.repo_root)
    except AuditRefusal as exc:
        print(json.dumps({"status": "REFUSED", "reason": str(exc)}, indent=2, sort_keys=True))
        return 2
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
