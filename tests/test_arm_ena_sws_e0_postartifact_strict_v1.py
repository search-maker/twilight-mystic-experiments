"""Refusal tests for the closed sanitized one-event E0 artifact universe."""
from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools" / "arm_ena_sws_e0_postartifact_v1"

base_spec = importlib.util.spec_from_file_location(
    "arm_e0_fixture_tests", TOOLS / "test_verify_oneevent_e0_artifact_v1.py"
)
assert base_spec is not None and base_spec.loader is not None
fixture_module = importlib.util.module_from_spec(base_spec)
base_spec.loader.exec_module(fixture_module)

strict_spec = importlib.util.spec_from_file_location(
    "arm_e0_strict", TOOLS / "verify_oneevent_e0_artifact_strict_v1.py"
)
assert strict_spec is not None and strict_spec.loader is not None
strict = importlib.util.module_from_spec(strict_spec)
strict_spec.loader.exec_module(strict)


def test_strict_clean_fixture_passes(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        fx = fixture_module.ArtifactFixture(root)
        monkeypatch.setattr(strict.base, "FROZEN_UNIVERSE_SHA256", fx.fixture_universe_sha)
        fx.refresh_receipt()
        result = strict.verify_strict(root)
        assert result["status"] == "SAFE_E0_ONEEVENT_SANITIZED_ARTIFACT_VERIFIED"
        assert result["stage_b_authorized"] is False
        assert result["heldout_radiance_opening_authorized"] is False


def test_strict_refuses_unexpected_text_file(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        fx = fixture_module.ArtifactFixture(root)
        monkeypatch.setattr(strict.base, "FROZEN_UNIVERSE_SHA256", fx.fixture_universe_sha)
        fx.refresh_receipt()
        (root / "unexpected-notes.txt").write_text("unexpected payload\n", encoding="utf-8")
        try:
            strict.verify_strict(root)
        except strict.StrictVerificationError as exc:
            assert "unexpected=['unexpected-notes.txt']" in str(exc)
        else:
            raise AssertionError("strict verifier accepted an unexpected artifact file")
