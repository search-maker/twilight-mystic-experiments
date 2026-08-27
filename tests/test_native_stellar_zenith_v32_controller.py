from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "review/native-stellar-zenith-v3/run_native_stellar_zenith_v32.py"


def load_module():
    spec = importlib.util.spec_from_file_location("native_stellar_zenith_v32_controller_tested", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load v3.2 controller")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


r = load_module()


class NativeStellarZenithV32ControllerTests(unittest.TestCase):
    def _base_failure(self):
        return {
            "schemaVersion": 1,
            "stageId": "native-stellar-zenith-v3",
            "status": "COMPUTATIONAL_REFERENCE_VALIDATION_FAIL",
            "interpolation": "v3-old",
            "freshValidationAtmosphericSpectrumCount": 64,
            "johnsonVComparisonCount": 192,
            "overall": {
                "comparisonCount": 192,
                "maxAbsDeltaAvMag": 0.026,
                "rmsDeltaAvMag": 0.009,
                "maxAbsDeltaAvMagLimit": 0.025,
                "rmsDeltaAvMagLimit": 0.010,
                "passed": False,
            },
            "byValidationAltitudeDeg": {str(h): {"passed": h != 88.4375} for h in r.v32.VALIDATION_ALTITUDE_DEG},
            "claimBoundary": {"productionAuthorized": False},
        }

    def test_extract_validation_failure_decorates_v32_without_relaxing_gate(self):
        original = self._base_failure()
        exc = r.v32.ZenithV32Refusal(json.dumps({"validationFailed": original}, sort_keys=True))
        result = r.extract_validation_failure(exc)
        self.assertIsNotNone(result)
        self.assertEqual(result["stageId"], r.v32.STAGE_ID)
        self.assertEqual(result["methodVersion"], r.v32.METHOD_VERSION)
        self.assertEqual(result["overall"]["maxAbsDeltaAvMagLimit"], 0.025)
        self.assertEqual(result["overall"]["rmsDeltaAvMagLimit"], 0.010)
        self.assertFalse(result["overall"]["passed"])
        self.assertEqual(result["exactVerticalTrainingSpectrumCount"], 25)
        self.assertEqual(result["protectedHoldoutSdisortSpectrumCount"], 64)
        self.assertTrue(result["exactVerticalEndpointProof"]["passed"])
        self.assertFalse(result["claimBoundary"]["productionAuthorized"])

    def test_extract_validation_failure_refuses_non_json_or_unrelated_json(self):
        self.assertIsNone(r.extract_validation_failure(RuntimeError("plain failure")))
        self.assertIsNone(r.extract_validation_failure(RuntimeError(json.dumps({"other": {}}))))

    def test_preserve_validation_failure_never_overwrites(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "output"
            result = r.decorate_validation_result(self._base_failure())
            path = r.preserve_validation_failure(out, result)
            self.assertTrue(path.is_file())
            loaded = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(loaded["status"], "COMPUTATIONAL_REFERENCE_VALIDATION_FAIL")
            with self.assertRaises(RuntimeError):
                r.preserve_validation_failure(out, result)

    def test_execute_from_args_preserves_structured_holdout_fail_then_raises(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "execution-output"
            args = argparse.Namespace(
                root=ROOT,
                source_runtime=Path("source"),
                uvspec=Path("uvspec"),
                data_dir=Path("data"),
                atmosphere_file=Path("atm"),
                wavelength_grid_file=Path("grid"),
                sed_bundle=Path("sed"),
                johnson_v=Path("v"),
                output_dir=out,
            )
            failure = self._base_failure()
            exc = r.v32.ZenithV32Refusal(json.dumps({"validationFailed": failure}, sort_keys=True))
            with mock.patch.object(r.v32, "execute_campaign", side_effect=exc):
                with self.assertRaises(r.v32.ZenithV32Refusal):
                    r.execute_from_args(args)
            saved = json.loads((out / "native-stellar-zenith-v32-validation.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["stageId"], r.v32.STAGE_ID)
            self.assertEqual(saved["status"], "COMPUTATIONAL_REFERENCE_VALIDATION_FAIL")
            self.assertFalse(saved["overall"]["passed"])

    def test_execute_from_args_does_not_mask_nonvalidation_failure(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "execution-output"
            args = argparse.Namespace(
                root=ROOT,
                source_runtime=Path("source"), uvspec=Path("uvspec"), data_dir=Path("data"),
                atmosphere_file=Path("atm"), wavelength_grid_file=Path("grid"), sed_bundle=Path("sed"),
                johnson_v=Path("v"), output_dir=out,
            )
            exc = r.v32.ZenithV32Refusal("parser failed before holdout scoring")
            with mock.patch.object(r.v32, "execute_campaign", side_effect=exc):
                with self.assertRaises(r.v32.ZenithV32Refusal):
                    r.execute_from_args(args)
            self.assertFalse((out / "native-stellar-zenith-v32-validation.json").exists())


if __name__ == "__main__":
    unittest.main()
