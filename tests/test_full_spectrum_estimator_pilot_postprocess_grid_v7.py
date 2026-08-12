from __future__ import annotations

import importlib.util
import json
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NORMALIZER = ROOT / 'review' / 'full-spectrum-estimator-pilot-v2' / 'normalize_full_spectrum_estimator_pilot_results_v7.py'
CONTRACT = ROOT / 'experiments' / 'full-spectrum-estimator-pilot-v2' / 'postprocess-contract.ordinal16.v7.json'
WORKFLOW = ROOT / '.github' / 'workflows' / 'full-spectrum-estimator-pilot-v2-ordinal16-postprocess-v7.yml'

spec = importlib.util.spec_from_file_location('normalizer_v7', NORMALIZER)
if spec is None or spec.loader is None:
    raise RuntimeError('cannot load v7 normalizer')
normalizer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(normalizer)


def serialized_grid(overrides: dict[int, float] | None = None) -> bytes:
    overrides = overrides or {}
    rows = []
    for index in range(8001):
        wavelength = 380.0 + index * 0.05
        if 0 < index < 8000:
            wavelength += (-2e-5 if index % 3 == 0 else 1e-5 if index % 3 == 1 else 0.0)
        wavelength = overrides.get(index, wavelength)
        rows.append(f'{wavelength:.5f} 0 0 0 1')
    return ('\n'.join(rows) + '\n').encode()


class PostprocessGridV7Tests(unittest.TestCase):
    def test_contract_self_hash_and_no_science_permissions(self) -> None:
        contract = json.loads(CONTRACT.read_text())
        normalizer.validate_postprocess_contract(contract)
        self.assertFalse(contract['solverExecutionAuthorized'])
        self.assertFalse(contract['syntaxCheckAuthorized'])
        self.assertFalse(contract['githubRerunOfScientificRunAllowed'])
        self.assertFalse(contract['newScientificOrdinalAuthorized'])
        self.assertFalse(contract['modelFittingAuthorized'])
        self.assertFalse(contract['holdoutValidationOpeningAuthorized'])

    def test_serialized_solar_output_grid_is_accepted_for_alis_and_vroom_callers(self) -> None:
        raw = serialized_grid()
        for caller in ((8001, 0.05), (401, 1.0)):
            wavelengths, values = normalizer.parse_spectrum_v7(raw, *caller)
            self.assertEqual(8001, len(wavelengths))
            self.assertEqual(8001, len(values))
            self.assertEqual(380.0, wavelengths[0])
            self.assertEqual(780.0, wavelengths[-1])

    def test_out_of_bound_grid_point_is_refused(self) -> None:
        raw = serialized_grid({100: 385.001})
        with self.assertRaisesRegex(ValueError, 'output grid point mismatch'):
            normalizer.parse_spectrum_v7(raw, 8001, 0.05)

    def test_wrong_node_count_and_unknown_caller_are_refused(self) -> None:
        raw = serialized_grid()
        with self.assertRaisesRegex(ValueError, 'unsupported v6 output-grid caller contract'):
            normalizer.parse_spectrum_v7(raw, 400, 1.0)
        with self.assertRaisesRegex(ValueError, 'output grid mismatch'):
            normalizer.parse_spectrum_v7(raw.rsplit(b'\n', 2)[0] + b'\n', 8001, 0.05)

    def test_negative_or_nonfinite_radiance_is_refused(self) -> None:
        lines = serialized_grid().decode().splitlines()
        lines[10] = lines[10].rsplit(' ', 1)[0] + ' -1'
        with self.assertRaisesRegex(ValueError, 'invalid number'):
            normalizer.parse_spectrum_v7(('\n'.join(lines) + '\n').encode(), 8001, 0.05)
        lines[10] = lines[10].rsplit(' ', 1)[0] + ' nan'
        with self.assertRaisesRegex(ValueError, 'invalid number'):
            normalizer.parse_spectrum_v7(('\n'.join(lines) + '\n').encode(), 8001, 0.05)

    def test_postprocess_workflow_is_exact_source_and_zero_solver(self) -> None:
        text = WORKFLOW.read_text()
        self.assertIn('postprocess/full-spectrum-estimator-pilot-v2-ordinal16-v7', text)
        self.assertIn('31546667072', text)
        self.assertIn('183188bdbe5a899f5dcd1bc4e423fa385d26e3af', text)
        self.assertIn('normalize_full_spectrum_estimator_pilot_results_v7.py', text)
        self.assertIn('analyze_full_spectrum_estimator_pilot_v6.py', text)
        for forbidden in ('setup-micromamba', 'rubin-libradtran', 'command -v uvspec', '--allow-execution', 'workflow_dispatch:', 'schedule:', 'repository_dispatch:'):
            self.assertNotIn(forbidden, text)


if __name__ == '__main__':
    unittest.main()
