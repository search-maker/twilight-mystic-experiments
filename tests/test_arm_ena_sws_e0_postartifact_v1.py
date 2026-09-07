"""Expose the ARM one-event sanitized-ingest refusal suite to generic CI."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools" / "arm_ena_sws_e0_postartifact_v1" / "test_verify_oneevent_e0_artifact_v1.py"
SPEC = importlib.util.spec_from_file_location("arm_e0_postartifact_tests", SOURCE)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

VerifyOneEventArtifactTests = MODULE.VerifyOneEventArtifactTests
