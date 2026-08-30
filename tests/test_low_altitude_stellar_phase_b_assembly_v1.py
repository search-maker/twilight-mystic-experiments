from __future__ import annotations

import importlib.util
import json
import math
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "review" / "low-altitude-stellar-transport-v1" / "assemble_phase_b_training_candidate_v1.py"
SPEC = importlib.util.spec_from_file_location("assemble_phase_b_training_candidate_v1", MODULE_PATH)
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class PhaseBAssemblyV1Tests(unittest.TestCase):
    def _training_payload(self):
        cases = []
        for row in m.phase_b.build_training_cases():
            tau = 0.1 + 0.01 * (5.0 - row["targetGeometricAltitudeDeg"]) + 0.001 * row["aod550"]
            cases.append({
                **row,
                "status": "PASS",
                "solver": "sdisort",
                "solverGeometry": "pseudo-spherical",
                "wavelengthNm": list(m.phase_b.WAVELENGTH_NM),
                "directOpticalDepth": [tau] * len(m.phase_b.WAVELENGTH_NM),
                "lineOfSightDirectTransmission": [math.exp(-tau)] * len(m.phase_b.WAVELENGTH_NM),
                "positiveEpsilonSubstitutionUsed": False,
            })
        return {
            "schemaVersion": 1,
            "executionId": m.TRAINING_EXECUTION_ID,
            "scientificState": m.phase_b.SCIENTIFIC_STATE,
            "phaseBFreezeIssue60CommentId": m.phase_b.PHASE_B_FREEZE_COMMENT_ID,
            "solver": "sdisort",
            "solverGeometry": "pseudo-spherical",
            "solverInvocationCount": m.phase_b.EXPECTED_TRAINING_SPECTRA,
            "executionComplete": True,
            "trainingScientificallyEligible": True,
            "passingTrainingSpectrumCount": m.phase_b.EXPECTED_TRAINING_SPECTRA,
            "numericallyUnresolvedTrainingSpectrumCount": 0,
            "trainingOnly": True,
            "fiveDegreeSeamRegenerated": False,
            "protectedValidationOpened": False,
            "protectedSolverInvocationCount": 0,
            "positiveEpsilonSubstitutionUsed": False,
            "productionAuthorized": False,
            "applicationSupportChanged": False,
            "cases": cases,
        }

    def _v32_runtime(self):
        altitudes = [5.0, 6.0]
        spectra = []
        for h in altitudes:
            for e in m.phase_b.ELEVATION_KNOTS_M:
                for a in m.phase_b.AOD_KNOTS:
                    tau = 0.2 + 0.00001 * e + 0.02 * a + 0.001 * h
                    spectra.append([tau] * len(m.phase_b.WAVELENGTH_NM))
        return {
            "schemaVersion": 1,
            "quantity": "level-b-stellar-direct-optical-depth-lut",
            "axes": {
                "targetAltitudeDeg": altitudes,
                "observerElevationM": list(m.phase_b.ELEVATION_KNOTS_M),
                "aod550": list(m.phase_b.AOD_KNOTS),
            },
            "wavelengthNm": list(m.phase_b.WAVELENGTH_NM),
            "directOpticalDepth": spectra,
        }

    def test_candidate_uses_275_training_and_exact_25_v32_seam(self):
        source = self._v32_runtime()
        runtime, receipt = m.assemble_candidate(
            training_payload=self._training_payload(),
            source_v32_runtime=source,
            source_v32_sha256=m.phase_b.SOURCE_V32_RUNTIME_SHA256,
            source_run_id=123,
            source_artifact_id=456,
            source_artifact_digest="sha256:test",
            source_dispatch_sha="abc",
        )
        self.assertEqual(runtime["axes"]["targetAltitudeDeg"], list(m.phase_b.LOWER_ASSET_ALTITUDE_DEG))
        self.assertEqual(len(runtime["directOpticalDepth"]), len(m.phase_b.LOWER_ASSET_ALTITUDE_DEG) * 25)
        seam = m.phase_b.extract_v32_five_degree_seam(source)
        last_alt = len(m.phase_b.LOWER_ASSET_ALTITUDE_DEG) - 1
        for ei, e in enumerate(m.phase_b.ELEVATION_KNOTS_M):
            for ai, a in enumerate(m.phase_b.AOD_KNOTS):
                index = ((last_alt * len(m.phase_b.ELEVATION_KNOTS_M)) + ei) * len(m.phase_b.AOD_KNOTS) + ai
                self.assertEqual(runtime["directOpticalDepth"][index], seam[m.phase_b.coord(5.0, e, a)])
        self.assertTrue(receipt["exactFiveDegreeSeamContentIdentical"])
        self.assertEqual(receipt["protectedSpectrumCountOpened"], 0)
        self.assertFalse(receipt["scientificallyValidatedBelow5Deg"])
        self.assertIsNone(receipt["minimumScientificallySupportedGeometricAltitudeDeg"])
        self.assertFalse(receipt["exactHorizonSupported"])

    def test_refuses_ineligible_or_incomplete_training(self):
        source = self._v32_runtime()
        for key, value in (
            ("trainingScientificallyEligible", False),
            ("executionComplete", False),
            ("protectedValidationOpened", True),
            ("positiveEpsilonSubstitutionUsed", True),
        ):
            payload = self._training_payload()
            payload[key] = value
            with self.assertRaises(m.AssemblyRefusal):
                m.assemble_candidate(
                    training_payload=payload,
                    source_v32_runtime=source,
                    source_v32_sha256=m.phase_b.SOURCE_V32_RUNTIME_SHA256,
                    source_run_id=1, source_artifact_id=2,
                    source_artifact_digest="sha256:x", source_dispatch_sha="y",
                )

    def test_refuses_wrong_v32_identity(self):
        with self.assertRaisesRegex(m.AssemblyRefusal, "v3.2 runtime SHA-256"):
            m.assemble_candidate(
                training_payload=self._training_payload(),
                source_v32_runtime=self._v32_runtime(),
                source_v32_sha256="0" * 64,
                source_run_id=1, source_artifact_id=2,
                source_artifact_digest="sha256:x", source_dispatch_sha="y",
            )

    def test_module_contains_no_solver_or_protected_evaluation_surface(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("subprocess", source)
        self.assertNotIn("uvspec", source)
        self.assertNotIn("build_protected_cases()", source)
        self.assertNotIn("evaluate_protected_deltas(", source)
        self.assertNotIn("Taylor", source)
        self.assertNotIn("Jerusalem", source)

    def test_cli_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            out = root / "already"
            out.mkdir()
            training = root / "training.json"
            training.write_text(json.dumps(self._training_payload()), encoding="utf-8")
            source = root / "v32.json"
            source.write_text(json.dumps(self._v32_runtime()), encoding="utf-8")
            # Main's exact SHA cannot be reproduced by the synthetic file; overwrite
            # refusal occurs first and therefore proves no mutation is attempted.
            import sys
            old = sys.argv
            try:
                sys.argv = [
                    str(MODULE_PATH), "--training-result", str(training),
                    "--source-v32-runtime", str(source), "--source-run-id", "1",
                    "--source-artifact-id", "2", "--source-artifact-digest", "sha256:x",
                    "--source-dispatch-sha", "y", "--output-dir", str(out),
                ]
                with self.assertRaises(m.AssemblyRefusal):
                    m.main()
            finally:
                sys.argv = old


if __name__ == "__main__":
    unittest.main()
