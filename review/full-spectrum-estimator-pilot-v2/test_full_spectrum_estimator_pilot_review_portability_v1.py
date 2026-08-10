from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class T(unittest.TestCase):
    def test_active_dependencies_present(self):
        required = (
            'build_full_spectrum_training_handoff.py',
            'wavelength-grid-1nm.dat',
            'normalize_full_spectrum_estimator_pilot_results_v6.py',
            'analyze_full_spectrum_estimator_pilot_v6.py',
            'full-spectrum-estimator-pilot-preregistration-v2.json',
            'full-spectrum-estimator-pilot-screening-analysis-preregistration-v4.json',
            'full-spectrum-estimator-pilot-execution-manifest-v4.json',
            'rendered-review-v5/renderer-review-report.json',
            'build_full_spectrum_estimator_pilot_preauthorization_contract_v4.py',
            'full-spectrum-estimator-pilot-preauthorization-contract-v4.json',
            'full_spectrum_estimator_pilot_preauthorization_guard_v4.py',
            'run_review_checks.py',
            'verify_full_spectrum_estimator_pilot_execution_manifest_v4.py',
            'verify_full_spectrum_estimator_pilot_acquisition_contract_v4.py',
            'verify_full_spectrum_estimator_pilot_seed_collision_audit_v4.py',
            'verify_full_spectrum_estimator_pilot_identity_collision_audit_v4.py',
            'reference/full-spectrum-estimator-pilot-preregistration-v1.json',
            'reference/full-spectrum-estimator-pilot-execution-manifest-v1.json',
            'reference/historical-nonportable/README.md',
        )
        for rel in required:
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_grid_bytes(self):
        path = ROOT / 'wavelength-grid-1nm.dat'
        self.assertEqual(path.read_text(), ''.join(f'{i}\n' for i in range(380, 781)))
        self.assertEqual(
            hashlib.sha256(path.read_bytes()).hexdigest(),
            '488f6bd90c35a6f5aeffe1ef230186ae87002d42747af4fe94f07d82c5eef692',
        )

    def test_active_python_is_repository_relative(self):
        offenders = []
        forbidden = '/' + 'mnt' + '/' + 'data'
        for path in ROOT.rglob('*.py'):
            if 'reference' in path.parts:
                continue
            if forbidden in path.read_text():
                offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [])

    def test_superseded_or_nonportable_builders_not_active(self):
        forbidden_root = (
            'analyze_full_spectrum_estimator_pilot_v4.py',
            'analyze_full_spectrum_estimator_pilot_v5.py',
            'full-spectrum-estimator-pilot-screening-analysis-preregistration-v3.json',
            'build_full_spectrum_estimator_pilot_acquisition_contract_v4.py',
            'build_full_spectrum_estimator_pilot_execution_manifest_v4.py',
            'build_full_spectrum_estimator_pilot_identity_collision_audit_v4.py',
            'build_full_spectrum_estimator_pilot_seed_collision_audit_v4.py',
            'build_full_spectrum_estimator_pilot_preauthorization_contract_v2.py',
            'build_full_spectrum_estimator_pilot_preauthorization_contract_v3.py',
            'full-spectrum-estimator-pilot-preauthorization-contract-v2.json',
            'full-spectrum-estimator-pilot-preauthorization-contract-v3.json',
            'full_spectrum_estimator_pilot_preauthorization_guard_v2.py',
            'full_spectrum_estimator_pilot_preauthorization_guard_v3.py',
            'test_full_spectrum_estimator_pilot_preauthorization_guard_v2.py',
            'test_full_spectrum_estimator_pilot_preauthorization_guard_v3.py',
        )
        for rel in forbidden_root:
            self.assertFalse((ROOT / rel).exists(), rel)
        historical = ROOT / 'reference' / 'historical-nonportable'
        for rel in (
            'build_full_spectrum_estimator_pilot_acquisition_contract_v4.py',
            'build_full_spectrum_estimator_pilot_execution_manifest_v4.py',
            'build_full_spectrum_estimator_pilot_identity_collision_audit_v4.py',
            'build_full_spectrum_estimator_pilot_seed_collision_audit_v4.py',
        ):
            self.assertTrue((historical / rel).is_file(), rel)


if __name__ == '__main__':
    unittest.main()
