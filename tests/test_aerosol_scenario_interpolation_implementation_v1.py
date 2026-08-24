import importlib.util
import json
import math
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MOD_PATH = ROOT / 'review/aerosol-scenario-interpolation-implementation-v1/select_model_v1.py'
PROTO_PATH = ROOT / 'review/aerosol-scenario-interpolation-validation-v1/protocol.review.json'
spec = importlib.util.spec_from_file_location('asiv', MOD_PATH)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
PROTO = json.loads(PROTO_PATH.read_text())


class AerosolScenarioInterpolationImplementationV1Tests(unittest.TestCase):
    def synthetic_index(self):
        cells = []
        for s in [2.0, 4.0, 6.0, 8.0]:
            for alt, az, gid in [(10.0, 30.0, 'g02'), (30.0, 90.0, 'g04'), (45.0, 180.0, 'g06')]:
                for aod in [0.1, 0.3]:
                    primary = {}
                    for ci, ch in enumerate(m.CHANNELS):
                        primary[ch] = {}
                        base = 0.02 * s + 0.001 * alt + 0.03 * math.cos(math.radians(az)) + 0.4 * aod + 0.01 * ci
                        for ki, contrast in enumerate(m.CONTRASTS):
                            value = base + 0.025 * ki
                            primary[ch][contrast] = {
                                'status': 'FINITE_THREE_REPLICATES',
                                'mean': value,
                                'replicateValues': [value, value, value],
                            }
                    cells.append({
                        'analysisCellId': f's{s}-{gid}-a{aod}',
                        'sunDepressionDeg': s,
                        'targetAltitudeDeg': alt,
                        'relativeAzimuthDeg': az,
                        'aod550': aod,
                        'primary': primary,
                    })
        return {'scientificOrdinal': 38, 'analysisCellCount': 24, 'cells': cells}

    def test_no_external_numerical_dependency(self):
        text = MOD_PATH.read_text()
        self.assertNotIn('import numpy', text)
        self.assertNotIn('from numpy', text)

    def test_candidate_count_and_determinism(self):
        specs = m.candidate_specs(PROTO)
        self.assertEqual(len(specs), 17)
        self.assertEqual(len({x['candidateId'] for x in specs}), 17)

    def test_geometry_excludes_elevation(self):
        g = {'sunDepressionDeg': 4, 'targetAltitudeDeg': 30, 'relativeAzimuthDeg': 90, 'aod550': 0.2, 'observerElevationM': 999}
        self.assertEqual(len(m.coordinate(g)), 4)

    def test_training_matrix_exact_shape(self):
        records, x, y = m.extract_training(self.synthetic_index())
        self.assertEqual(len(records), 24)
        self.assertEqual((len(x), len(x[0])), (24, 4))
        self.assertEqual((len(y), len(y[0])), (24, 12))

    def test_selection_is_training_only_and_materializes(self):
        out = m.materialize(self.synthetic_index(), PROTO, 'abc', 'def')
        self.assertFalse(out['holdoutValuesRead'])
        self.assertFalse(out['scientificExecutionPerformed'])
        self.assertFalse(out['solverExecutionPerformed'])
        self.assertFalse(out['ordinal39Allocated'])
        self.assertTrue(out['selectedCandidate']['eligible'])
        self.assertEqual(len(out['candidateTable']), 17)
        self.assertEqual(len(out['targetNamesInOrder']), 12)
        self.assertTrue(out['selfSha256'])

    def test_quantile_ridge_and_cholesky_semantics(self):
        self.assertAlmostEqual(m.percentile_linear([0.0, 10.0, 20.0, 30.0], 0.9), 27.0)
        self.assertEqual(len(m.quadratic_design_row([0.0, 0.0, 0.0, 0.0])), 15)
        A = [[4.0, 2.0], [2.0, 3.0]]
        B = [[1.0], [1.0]]
        L = m.cholesky(A)
        sol = m.solve_cholesky_multi(L, B)
        self.assertAlmostEqual(sol[0][0], 0.125)
        self.assertAlmostEqual(sol[1][0], 0.25)


if __name__ == '__main__':
    unittest.main()
