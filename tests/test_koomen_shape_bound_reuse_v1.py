from __future__ import annotations

import importlib.util
import math
import unittest
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "review/published-twilight-radiance-benchmark-v1/certify_koomen_shape_continuous_aod_v1.py"


def load_candidate():
    spec = importlib.util.spec_from_file_location("koomen_shape_certifier", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeExtrema:
    @staticmethod
    def _down(value: float) -> float:
        return math.nextafter(value, -math.inf) if math.isfinite(value) else value

    @staticmethod
    def _up(value: float) -> float:
        return math.nextafter(value, math.inf) if math.isfinite(value) else value

    @dataclass(frozen=True)
    class Interval:
        lo: float
        hi: float

        def add(self, other: "FakeExtrema.Interval") -> "FakeExtrema.Interval":
            return FakeExtrema.Interval(FakeExtrema._down(self.lo + other.lo), FakeExtrema._up(self.hi + other.hi))

        def mul_const(self, value: float) -> "FakeExtrema.Interval":
            a, b = self.lo * value, self.hi * value
            return FakeExtrema.Interval(FakeExtrema._down(min(a, b)), FakeExtrema._up(max(a, b)))

        def div_pos(self, other: "FakeExtrema.Interval") -> "FakeExtrema.Interval":
            if other.lo <= 0:
                raise ValueError("positive denominator required")
            values = (
                self.lo / other.lo,
                self.lo / other.hi,
                self.hi / other.lo,
                self.hi / other.hi,
            )
            return FakeExtrema.Interval(FakeExtrema._down(min(values)), FakeExtrema._up(max(values)))

    @staticmethod
    def _q_range(constant: float, center: float, lo: float, hi: float):
        nearest_x = min(max(center, lo), hi)
        qlo = constant + (nearest_x - center) ** 2
        qhi = constant + max((lo - center) ** 2, (hi - center) ** 2)
        return FakeExtrema._down(qlo), FakeExtrema._up(qhi)

    @staticmethod
    def _weight_interval(constant: float, center: float, lo: float, hi: float, power: int):
        qlo, qhi = FakeExtrema._q_range(constant, center, lo, hi)
        if qlo <= 0:
            return None
        if power == 1:
            return FakeExtrema.Interval(FakeExtrema._down(1.0 / math.sqrt(qhi)), FakeExtrema._up(1.0 / math.sqrt(qlo)))
        if power == 2:
            return FakeExtrema.Interval(FakeExtrema._down(1.0 / qhi), FakeExtrema._up(1.0 / qlo))
        raise ValueError("unsupported IDW power")


def scalar_idw_bound(extrema, rows, coord_key, target_key, fixed, x_index,
                     selected, lo, hi, power, target_index):
    params = []
    singular = []
    for index in selected:
        row = rows[index]
        coord = row[coord_key]
        constant = sum((fixed[j] - coord[j]) ** 2 for j in range(len(fixed)))
        center = coord[x_index]
        target = float(row[target_key][target_index])
        params.append((index, constant, center, target))
        if constant == 0.0 and lo <= center <= hi:
            singular.append((index, constant, center, target))

    if len(singular) > 1:
        raise ArithmeticError("multiple exact-hit IDW singularities in selected set")

    if singular:
        singular_index, _, singular_center, singular_target = singular[0]
        u_max = max(abs(lo - singular_center), abs(hi - singular_center))
        numerator = extrema.Interval(singular_target, singular_target)
        denominator = extrema.Interval(1.0, 1.0)
        for index, constant, center, target in params:
            if index == singular_index:
                continue
            qlo, _ = extrema._q_range(constant, center, lo, hi)
            if qlo <= 0:
                raise ArithmeticError("secondary singularity")
            if power == 1:
                ratio_hi = u_max / math.sqrt(qlo)
            else:
                ratio_hi = (u_max * u_max) / qlo
            ratio = extrema.Interval(0.0, extrema._up(ratio_hi))
            numerator = numerator.add(ratio.mul_const(target))
            denominator = denominator.add(ratio)
        return numerator.div_pos(denominator)

    numerator = extrema.Interval(0.0, 0.0)
    denominator = extrema.Interval(0.0, 0.0)
    for _, constant, center, target in params:
        weight = extrema._weight_interval(constant, center, lo, hi, power)
        if weight is None:
            raise ArithmeticError("unhandled singularity")
        numerator = numerator.add(weight.mul_const(target))
        denominator = denominator.add(weight)
    return numerator.div_pos(denominator)


def targets(seed: float):
    return [seed + (index - 5) * 0.137 for index in range(12)]


class KoomenShapeBoundReuseV1Tests(unittest.TestCase):
    def assert_scalar_parity(self, rows, fixed, lo, hi):
        mod = load_candidate()
        selected = tuple(range(len(rows)))
        target_indices = (0, 3, 6, 9)
        actual = mod._idw_bounds_multi(
            FakeExtrema, rows, "coord", "target", fixed, 3,
            selected, lo, hi, 2, target_indices,
        )
        for target_index in target_indices:
            expected = scalar_idw_bound(
                FakeExtrema, rows, "coord", "target", fixed, 3,
                selected, lo, hi, 2, target_index,
            )
            self.assertEqual(actual[target_index], expected)

    def test_non_singular_multi_target_bounds_are_bitwise_identical_to_scalar_algorithm(self):
        rows = [
            {"coord": (0.10, 0.30, 0.50, 0.12), "target": targets(-0.4)},
            {"coord": (0.22, 0.38, 0.58, 0.28), "target": targets(0.2)},
            {"coord": (0.33, 0.44, 0.63, 0.46), "target": targets(0.7)},
            {"coord": (0.48, 0.57, 0.71, 0.68), "target": targets(-0.1)},
        ]
        self.assert_scalar_parity(rows, (0.15, 0.35, 0.55), 0.10, 0.40)

    def test_exact_hit_endpoint_multi_target_bounds_are_bitwise_identical_to_scalar_algorithm(self):
        rows = [
            {"coord": (0.10, 0.20, 0.30, 0.25), "target": targets(-0.8)},
            {"coord": (0.17, 0.26, 0.36, 0.38), "target": targets(0.1)},
            {"coord": (0.31, 0.42, 0.54, 0.62), "target": targets(0.9)},
        ]
        self.assert_scalar_parity(rows, (0.10, 0.20, 0.30), 0.25, 0.50)

    def test_scientific_contract_is_unchanged(self):
        mod = load_candidate()
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertEqual(mod.DEFAULT_LOG_TOLERANCE, 1e-4)
        self.assertEqual(mod.SCENARIOS, ("native", "continental", "maritime", "desert", "desert_spheroids"))
        self.assertEqual(mod.CONTRASTS, ("continental", "maritime", "desert", "desert_spheroids"))
        self.assertEqual(source.count("extrema._idw_bound("), 1)
        self.assertIn('"algorithmId": "CERTIFIED_SAME_AOD_SAME_SCENARIO_SHAPE_INTERVAL_BNB_V1"', source)
        self.assertIn('parser.add_argument("--max-depth", type=int, default=50)', source)
        self.assertIn('parser.add_argument("--max-nodes", type=int, default=500000)', source)


if __name__ == "__main__":
    unittest.main()
