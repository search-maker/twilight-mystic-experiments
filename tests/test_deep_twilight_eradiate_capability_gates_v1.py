import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path("review/deep-twilight-eradiate-capability-gates-v1/gates.py")
spec = importlib.util.spec_from_file_location("deep_twilight_gates_v1", MODULE_PATH)
gates = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(gates)


class DeepTwilightParityGateTests(unittest.TestCase):
    @staticmethod
    def source_snapshot():
        return {
            "wavelength_nm": [500.0, 550.0],
            "extinction_per_km": [0.01, 0.009],
            "ssa": [0.9, 0.91],
            "phase": [
                {"components": {"11": {"mu": [-1.0, 0.0, 1.0], "value": [0.5, 1.0, 1.5]}}},
                {"components": {"11": {"mu": [-1.0, 0.0, 1.0], "value": [0.6, 1.0, 1.4]}}},
            ],
            "pmom_p11": [[1.0, 0.1], [1.0, 0.2]],
            "vertical_profile": {
                "altitude_km": [0.0, 1.0, 2.0],
                "extinction_per_km_by_wavelength": [[0.02, 0.01, 0.0], [0.018, 0.009, 0.0]],
                "scattering_per_km_by_wavelength": [[0.018, 0.009, 0.0], [0.01638, 0.00819, 0.0]],
            },
        }

    @classmethod
    def converted_snapshot(cls):
        source = cls.source_snapshot()
        converted = json.loads(json.dumps(source))
        converted["phase"] = [
            {"mu": [-1.0, 0.0, 1.0], "components": {"11": [0.5, 1.0, 1.5]}},
            {"mu": [-1.0, 0.0, 1.0], "components": {"11": [0.6, 1.0, 1.4]}},
        ]
        converted["translation_metadata"] = {
            "nearest_neighbor_dimension_selected": False,
            "phase_normalized_during_conversion": False,
        }
        return converted

    def test_exact_translation_passes(self):
        result = gates.evaluate_parity(self.source_snapshot(), self.converted_snapshot())
        self.assertEqual(result["status"], "PASS")

    def test_vertical_extinction_change_fails_closed(self):
        converted = self.converted_snapshot()
        converted["vertical_profile"]["extinction_per_km_by_wavelength"][0][1] *= 1.01
        self.assertEqual(gates.evaluate_parity(self.source_snapshot(), converted)["status"], "FAIL_CLOSED")

    def test_vertical_scattering_change_fails_closed(self):
        converted = self.converted_snapshot()
        converted["vertical_profile"]["scattering_per_km_by_wavelength"][0][1] *= 1.01
        self.assertEqual(gates.evaluate_parity(self.source_snapshot(), converted)["status"], "FAIL_CLOSED")

    def test_phase_change_fails_closed(self):
        converted = self.converted_snapshot()
        converted["phase"][0]["components"]["11"][1] *= 1.01
        self.assertEqual(gates.evaluate_parity(self.source_snapshot(), converted)["status"], "FAIL_CLOSED")


class DeepTwilightKorkinGateTests(unittest.TestCase):
    @staticmethod
    def write_inputs(root: str, offset: float = 0.0, scatter: float = 0.0002):
        reference = Path(root) / "reference.csv"
        batches = Path(root) / "batches.csv"
        with reference.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["relative_azimuth_deg", "mu_view", "mystic_I", "mcssa_I"])
            writer.writeheader()
            for az, mu in sorted(gates.FROZEN_KORKIN_KEYS):
                writer.writerow({"relative_azimuth_deg": az, "mu_view": mu, "mystic_I": 1.0, "mcssa_I": 1.0})
        with batches.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["relative_azimuth_deg", "mu_view", "batch_id", "eradiate_I"])
            writer.writeheader()
            for az, mu in sorted(gates.FROZEN_KORKIN_KEYS):
                for batch_id, value in enumerate([1.0 + offset - scatter, 1.0 + offset + scatter]):
                    writer.writerow({"relative_azimuth_deg": az, "mu_view": mu, "batch_id": batch_id, "eradiate_I": value})
        return reference, batches

    def test_precise_consistent_batches_pass(self):
        with tempfile.TemporaryDirectory() as root:
            reference, batches = self.write_inputs(root)
            self.assertEqual(gates.evaluate_korkin(reference, batches)["status"], "PASS")

    def test_reference_disagreement_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            reference, batches = self.write_inputs(root, offset=0.01)
            self.assertEqual(gates.evaluate_korkin(reference, batches)["status"], "FAIL_CLOSED")

    def test_insufficient_precision_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            reference, batches = self.write_inputs(root, scatter=0.01)
            result = gates.evaluate_korkin(reference, batches)
            self.assertEqual(result["status"], "FAIL_CLOSED")
            self.assertTrue(any(point["status"] == "CAPABILITY_UNRESOLVED" for point in result["points"]))


if __name__ == "__main__":
    unittest.main()
