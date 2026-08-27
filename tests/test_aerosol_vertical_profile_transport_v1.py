from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "review" / "aerosol-vertical-profile-transport-v1" / "profile_transport.py"
spec = importlib.util.spec_from_file_location("profile_transport", MODULE)
pt = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = pt
spec.loader.exec_module(pt)


class VerticalProfileTransportTests(unittest.TestCase):
    def test_constant_profile_maps_to_exact_layer_fractions(self):
        out = pt.remap_normalized_vertical_shape(
            [0, 1000, 2000], [1, 1, 1], [0, 500, 1500, 2000],
            outside_below_policy="reject", outside_above_policy="reject",
            source_identity={"kind": "synthetic"},
        )
        self.assertEqual(out.layer_tau_fractions, (0.25, 0.5, 0.25))
        self.assertAlmostEqual(math.fsum(out.layer_tau_fractions), 1.0, places=15)

    def test_observer_clipping_renormalizes_only_remaining_column(self):
        out = pt.remap_normalized_vertical_shape(
            [0, 1000, 2000], [1, 1, 0], [1000, 1500, 2000],
            outside_below_policy="reject", outside_above_policy="reject",
        )
        self.assertAlmostEqual(out.layer_tau_fractions[0], 0.75, places=15)
        self.assertAlmostEqual(out.layer_tau_fractions[1], 0.25, places=15)
        self.assertAlmostEqual(out.transported_integral, 500.0, places=12)

    def test_explicit_zero_above_support_is_not_hidden_extrapolation(self):
        out = pt.remap_normalized_vertical_shape(
            [0, 1000], [1, 1], [0, 1000, 2000],
            outside_below_policy="reject", outside_above_policy="zero",
        )
        self.assertEqual(out.layer_tau_fractions, (1.0, 0.0))

    def test_reject_outside_support_refuses_implicit_extension(self):
        with self.assertRaises(pt.ProfileTransportError):
            pt.remap_normalized_vertical_shape(
                [0, 1000], [1, 1], [0, 1000, 2000],
                outside_below_policy="reject", outside_above_policy="reject",
            )

    def test_bad_profiles_fail_closed(self):
        bad = [
            ([0, 1000, 900], [1, 1, 1]),
            ([0, 1000, 2000], [1, -0.1, 0]),
            ([0, 1000, 2000], [0, 0, 0]),
        ]
        for z, y in bad:
            with self.subTest(z=z, y=y), self.assertRaises(pt.ProfileTransportError):
                pt.remap_normalized_vertical_shape(
                    z, y, [0, 1000, 2000],
                    outside_below_policy="reject", outside_above_policy="reject",
                )

    def test_render_uses_lower_boundary_tau_and_zero_top(self):
        out = pt.remap_normalized_vertical_shape(
            [262, 1000, 2000], [1, 1, 1], [262, 1000, 2000],
            outside_below_policy="reject", outside_above_policy="reject",
        )
        text = pt.render_libradtran_aerosol_tau(out, header="test")
        rows = [line for line in text.splitlines() if line and not line.startswith("#")]
        self.assertEqual(rows[0].split()[0], "2.000000000")
        self.assertEqual(float(rows[0].split()[1]), 0.0)
        self.assertEqual(rows[-1].split()[0], "0.262000000")
        rendered_sum = math.fsum(float(row.split()[1]) for row in rows)
        self.assertAlmostEqual(rendered_sum, 1.0, places=15)

    def test_fingerprint_is_stable_and_source_sensitive(self):
        a = pt.remap_normalized_vertical_shape(
            [0, 1], [1, 2], [0, 1], outside_below_policy="reject", outside_above_policy="reject",
            source_identity={"b": 2, "a": 1},
        )
        b = pt.remap_normalized_vertical_shape(
            [0, 1], [1, 2], [0, 1], outside_below_policy="reject", outside_above_policy="reject",
            source_identity={"a": 1, "b": 2},
        )
        c = pt.remap_normalized_vertical_shape(
            [0, 1], [1, 2], [0, 1], outside_below_policy="reject", outside_above_policy="reject",
            source_identity={"a": 1, "b": 3},
        )
        self.assertEqual(a.source_fingerprint_sha256, b.source_fingerprint_sha256)
        self.assertNotEqual(a.source_fingerprint_sha256, c.source_fingerprint_sha256)


if __name__ == "__main__":
    unittest.main()
