from __future__ import annotations

import importlib.util
import math
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "experiments" / "mystic-batch-v1" / "twilight_surrogate_tier1_edited_atmosphere_proof.py"


def load_module():
    spec = importlib.util.spec_from_file_location("tier1_edited_atmosphere_proof", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PROOF = load_module()


class EditedAtmosphereProofTests(unittest.TestCase):
    def test_descending_profile_is_cut_at_interpolated_site_level(self) -> None:
        rows = [
            [2.0, 20.0, 200.0],
            [1.0, 10.0, 100.0],
            [0.0, 0.0, 0.0],
        ]
        transformed, mode = PROOF.transformed_rows(rows, 0.25)
        self.assertEqual(mode, "linear-interpolation")
        self.assertEqual([row[0] for row in transformed], [2.0, 1.0, 0.25])
        self.assertTrue(math.isclose(transformed[-1][1], 2.5))
        self.assertTrue(math.isclose(transformed[-1][2], 25.0))

    def test_ascending_profile_preserves_existing_site_level(self) -> None:
        rows = [
            [0.0, 0.0, 0.0],
            [0.25, 2.5, 25.0],
            [1.0, 10.0, 100.0],
        ]
        transformed, mode = PROOF.transformed_rows(rows, 0.25)
        self.assertEqual(mode, "existing-level")
        self.assertEqual([row[0] for row in transformed], [0.25, 1.0])

    def test_mystic_candidate_uses_edited_profile_without_altitude_option(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            text = PROOF.render_mystic(root, root / "site.dat", root / "solar.dat", root)
        self.assertNotIn("\naltitude ", text)
        self.assertEqual(text.count("zout 0.000000"), 1)
        self.assertIn("atmosphere_file", text)
        self.assertIn("mc_spherical 1D", text)
        self.assertIn("mc_photons 1", text)

    def test_deterministic_pair_differs_only_by_representation_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            reference = PROOF.render_deterministic(root, root / "source.dat", root / "solar.dat", altitude_option=True)
            candidate = PROOF.render_deterministic(root, root / "site.dat", root / "solar.dat", altitude_option=False)
        self.assertIn("altitude 0.357143", reference)
        self.assertNotIn("\naltitude ", candidate)
        self.assertIn("zout 0.000000", reference)
        self.assertIn("zout 0.000000", candidate)

    def test_vector_comparison_refuses_length_change(self) -> None:
        with self.assertRaises(PROOF.ProofError):
            PROOF.compare_vectors([1.0], [1.0, 2.0])


if __name__ == "__main__":
    unittest.main()
