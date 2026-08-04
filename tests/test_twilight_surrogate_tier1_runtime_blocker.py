from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "experiments" / "mystic-batch-v1"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PROBE = load_module(
    "tier1_solver_probe_blocker",
    BASE / "twilight_surrogate_tier1_runtime_solver_probe.py",
)
RECOVERY = load_module(
    "tier1_recovery_blocker",
    BASE / "twilight_surrogate_tier1_ordinal2_recovery.py",
)


class Tier1RuntimeBlockerTests(unittest.TestCase):
    def test_exact_frozen_runtime_altitude_rejection_is_a_hard_blocker(self) -> None:
        status, accepted, blocked = PROBE.classify(
            255,
            "",
            PROBE.MYSTIC_ALTITUDE_REJECTION,
            0,
        )
        self.assertEqual(
            status,
            "BLOCKED_MYSTIC_ALTITUDE_REQUIRES_VALIDATED_MC_ELEVATION_FILE",
        )
        self.assertFalse(accepted)
        self.assertTrue(blocked)

    def test_near_match_is_not_silently_classified(self) -> None:
        status, accepted, blocked = PROBE.classify(
            255,
            "",
            PROBE.MYSTIC_ALTITUDE_REJECTION + "extra\n",
            0,
        )
        self.assertEqual(status, "UNEXPECTED_FROZEN_RUNTIME_SOLVER_RESULT")
        self.assertFalse(accepted)
        self.assertFalse(blocked)

    def test_recovery_refuses_structural_blocker_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = root / "manifest.json"
            audit = root / "audit.json"
            syntax = root / "syntax.json"
            blocker = root / "blocker.json"
            manifest.write_text(json.dumps({"geometries": [], "cases": []}) + "\n")
            audit.write_text(json.dumps({}) + "\n")
            syntax.write_text(json.dumps({}) + "\n")
            blocker.write_text(json.dumps({
                "status": "BLOCKED_MYSTIC_ALTITUDE_REQUIRES_VALIDATED_MC_ELEVATION_FILE",
                "accepted": False,
                "recognizedStructuralBlocker": True,
                "authorizationPermitted": False,
                "ordinal2ScientificDispatchPermitted": False,
            }) + "\n")
            with self.assertRaises(RECOVERY.RecoveryError):
                RECOVERY.recover(manifest, audit, syntax, blocker)


if __name__ == "__main__":
    unittest.main()
