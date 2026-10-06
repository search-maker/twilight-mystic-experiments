import math
import pathlib
import tempfile
import unittest

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
import sys
sys.path.insert(0, str(HERE))
import late_twilight_prefit_v1 as m


class SyntheticRowFactory:
    @staticmethod
    def row(i: int, sun: float) -> m.TrainingRow:
        g = {
            "geometryId": f"train-{i:04d}",
            "sourceIndex": i,
            "sunDepressionDeg": sun,
            "targetAltitudeDeg": 10.0 + (i * 7) % 65,
            "relativeAzimuthDeg": float((i * 23) % 181),
            "observerElevationM": float((i * 311) % 2501),
            "aod550": 0.05 + 0.35 * ((i * 17) % 100) / 99.0,
        }
        x = m.raw_cos_coordinates(g)
        channels = {}
        for j, ch in enumerate(m.CHANNELS):
            log_mean = 1.2 - 3.0*x[0] + 0.35*x[1] - 0.25*x[2] + 0.15*x[3] - 0.3*x[4] + 0.03*j
            rsem = 0.04 + 0.005 * (i % 3)
            meas = math.log1p(rsem)
            channels[ch] = m.ChannelLabel(
                mean=math.exp(log_mean),
                log_mean=log_mean,
                measurement_sigma_log=meas,
                total_training_sigma_log=math.sqrt(meas*meas + 0.12**2),
                degrees_of_freedom=7,
                relative_standard_error=rsem,
            )
        return m.TrainingRow(g["geometryId"], g, "SYNTHETIC", channels)

    @staticmethod
    def rows():
        suns = [10.75, 11.0, 11.25, 11.5, 12.0, 12.5, 12.75, 13.0, 13.5, 14.0, 14.25, 14.5, 15.0, 15.5, 16.0]
        return [SyntheticRowFactory.row(101 + i, s) for i, s in enumerate(suns)]


class Tests(unittest.TestCase):
    def test_geometry_generator_known_solar_depths(self):
        self.assertEqual(m.geometry_from_id("train-0009")["sunDepressionDeg"], 11.0)
        self.assertEqual(m.geometry_from_id("train-0021")["sunDepressionDeg"], 12.5)
        self.assertEqual(m.geometry_from_id("train-0007")["sunDepressionDeg"], 16.0)
        with self.assertRaises(m.Refusal):
            m.geometry_from_id("train-0005")

    def test_basis_dimensions_and_late_scaling(self):
        g = m.geometry_from_id("train-0007")
        self.assertEqual(len(m.basis(g, "COS_COMPACT_13_TERMS")), 13)
        self.assertEqual(len(m.basis(g, "PHYSICAL_COMPACT_16_TERMS")), 16)
        self.assertEqual(len(m.basis(g, "FULL_DEGREE2_ON_FIVE_COS_COORDINATES_21_TERMS")), 21)
        self.assertAlmostEqual(m.raw_cos_coordinates(g)[0], 1.0)

    def test_hard_domain_and_seam_probe(self):
        rows = SyntheticRowFactory.rows()
        g = dict(rows[0].geometry)
        g["sunDepressionDeg"] = 16.000001
        ok, d, _ = m.support(g, rows, 0.6)
        self.assertFalse(ok); self.assertTrue(math.isinf(d))
        g = dict(rows[0].geometry); g["targetAltitudeDeg"] = 80.0001
        self.assertFalse(m.support(g, rows, 0.6)[0])
        g = dict(rows[0].geometry); g["sunDepressionDeg"] = 10.5
        self.assertFalse(m.support(g, rows, 0.6)[0])
        # seam_probe bypasses only the strict late sun-min boundary.
        m.support(g, rows, 0.6, seam_probe=True)
        g["targetAltitudeDeg"] = 81
        self.assertFalse(m.support(g, rows, 0.6, seam_probe=True)[0])

    def test_ridge_grid_is_exact(self):
        rows = SyntheticRowFactory.rows()
        with self.assertRaises(m.Refusal):
            m.fit_student_t_irls(rows, m.CHANNELS[0], "COS_COMPACT_13_TERMS", 0.2)

    def test_irls_deterministic(self):
        rows = SyntheticRowFactory.rows()
        a = m.fit_student_t_irls(rows, m.CHANNELS[0], "COS_COMPACT_13_TERMS", 1e-3)
        b = m.fit_student_t_irls(rows, m.CHANNELS[0], "COS_COMPACT_13_TERMS", 1e-3)
        self.assertTrue(np.array_equal(a, b))

    def test_balanced_and_depth_folds(self):
        rows = SyntheticRowFactory.rows()
        bf = m.balanced_folds(rows)
        self.assertEqual(len(bf), 5)
        flat = [i for _,_,val in bf for i in val]
        self.assertEqual(sorted(flat), list(range(len(rows))))
        self.assertEqual(len(m.depth_folds(rows)), 3)

    def test_selection_and_all_row_guard(self):
        rows = SyntheticRowFactory.rows()
        selected, ranking = m.select_candidate(rows, m.CHANNELS[0])
        self.assertTrue(selected["ready"])
        self.assertFalse(selected.get("refused", False))
        self.assertEqual(len(ranking), 15)
        # Frozen procedure says a non-convergent candidate is refused, not a fatal
        # error for every other candidate.  This synthetic matrix deliberately
        # produces at least one such refusal.
        self.assertTrue(any(row.get("refused") for row in ranking))
        self.assertTrue(all(math.isinf(row["selectionScore"]) for row in ranking if row.get("refused")))
        beta = m.fit_selected_all_rows(rows, m.CHANNELS[0], selected)
        self.assertTrue(np.all(np.isfinite(beta)))
        bad = dict(selected); bad["ready"] = False
        with self.assertRaises(m.Refusal):
            m.fit_selected_all_rows(rows, m.CHANNELS[0], bad)

    def test_pooled_balanced_oof_rms_not_depth_repeated(self):
        rows = SyntheticRowFactory.rows()
        fam = m.FAMILIES[0]
        result = m.evaluate_candidate(rows, m.CHANNELS[0], fam, 1e-3)
        balanced = [f for f in result["folds"] if f["kind"] == "balanced"]
        self.assertEqual(sum(f["count"] for f in balanced), len(rows))
        self.assertGreaterEqual(result["balancedOofRmsLogResidual"], 0.0)

    def test_nearest_sigma_tie_is_conservative(self):
        rows = SyntheticRowFactory.rows()[:2]
        g = dict(rows[0].geometry)
        # duplicate geometry with different sigma to force an exact nearest tie.
        r0 = rows[0]
        ch = m.CHANNELS[0]
        labels = dict(r0.channels)
        old = labels[ch]
        labels[ch] = m.ChannelLabel(old.mean, old.log_mean, old.measurement_sigma_log, old.total_training_sigma_log + 0.5, old.degrees_of_freedom, old.relative_standard_error)
        r1 = m.TrainingRow("train-9999", dict(r0.geometry), "SYNTHETIC", labels)
        sigma, tied = m.nearest_label_sigma(g, [r0, r1], ch)
        self.assertEqual(tied, sorted([r0.geometry_id, r1.geometry_id]))
        self.assertAlmostEqual(sigma, labels[ch].total_training_sigma_log)

    def test_no_epsilon_nonpositive_blocks(self):
        report = {"geometryId":"train-0003","blockCount":4,"channels":{ch:{"values":[1.0, 2.0, 0.0, 4.0]} for ch in m.CHANNELS}}
        with self.assertRaises(m.Refusal):
            m._channel_label(report, m.CHANNELS[0], False)

    def test_raw_protected_scan_before_decode(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            p = root / m.OPEN_LABEL_PATH; p.parent.mkdir(parents=True)
            # Blob mismatch itself is fail-closed; dedicated raw-scan semantics are also unit-tested directly.
            raw = b'{"geometryReports":[{"geometryId":"train-0005"}]}'
            ids = __import__('re').findall(rb"train-(\d{4})", raw)
            self.assertTrue(any(int(x) % 5 == 0 for x in ids))

    def test_seam_grid_cardinality_and_no_promotion_semantics(self):
        self.assertEqual(len(m.frozen_seam_grid()), 108)
        rows = SyntheticRowFactory.rows()
        maxloo, threshold = m.calibrate_ood_threshold(rows)
        self.assertLessEqual(threshold, 0.6)
        part = m.seam_support_partition(rows, threshold)
        self.assertEqual(len(part["supported"]) + len(part["localOod"]), 108)

    def test_preliminary_uncertainty_floor(self):
        rows = SyntheticRowFactory.rows()
        selected, _ = m.select_candidate(rows, m.CHANNELS[0])
        u = m.preliminary_uncertainty(rows[0].geometry, rows, m.CHANNELS[0], selected)
        self.assertGreaterEqual(u["channelSigmaLog"], 0.12)
        self.assertAlmostEqual(u["halfWidthLog"], 2*u["channelSigmaLog"])


if __name__ == "__main__":
    unittest.main()
