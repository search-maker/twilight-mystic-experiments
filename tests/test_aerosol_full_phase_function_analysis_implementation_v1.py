from __future__ import annotations

import importlib.util
import json
import math
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "experiments/aerosol-full-phase-function-sensitivity-v1"
ANALYSIS_PATH = STAGE / "analysis.py"


def load_analysis():
    spec = importlib.util.spec_from_file_location("afpf_analysis_review", ANALYSIS_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load AFPF analysis review module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def records(values: dict[str, float]) -> dict[str, dict[str, float]]:
    return {
        state: {
            "photopicLuminanceCdM2": value,
            "scotopicLuminanceScotCdM2": value,
            "johnsonVEffectiveRadiance_mW_m2_nm_sr": value,
        }
        for state, value in values.items()
    }


def canonical_values() -> dict[str, float]:
    return {
        "native-rural-ss": 1.0,
        "opac-continental-average": 2.0,
        "opac-maritime-clean": 4.0,
        "opac-desert": 8.0,
        "opac-desert-spheroids": 16.0,
    }


class AerosolFullPhaseFunctionAnalysisImplementationV1Tests(unittest.TestCase):
    def test_analysis_binds_frozen_preregistration_and_contract(self) -> None:
        m = load_analysis()
        summary = m.review_summary()
        self.assertEqual(summary["status"], "PASS_AFPF_ANALYSIS_IMPLEMENTATION_BINDINGS")
        self.assertEqual(summary["stateCount"], 5)
        self.assertEqual(summary["contrastCount"], 7)
        self.assertEqual(summary["rawSpectrumNodeCount"], 8001)
        self.assertIs(summary["r8PrimaryChannelsMatch"], True)
        self.assertIs(summary["pValuesPermitted"], False)
        self.assertIs(summary["confidenceIntervalsPermitted"], False)
        self.assertIs(summary["epsilonSubstitutionPermitted"], False)
        self.assertIs(summary["scientificExecutionAuthorized"], False)
        self.assertIs(summary["resultOpeningAuthorized"], False)

    def test_scalar_contrasts_are_exact_preregistered_log_ratios(self) -> None:
        m = load_analysis()
        got = m.scalar_replicate_contrasts(records(canonical_values()), "photopicLuminanceCdM2")
        expected = {
            "continental_vs_native": math.log(2.0),
            "maritime_vs_native": math.log(4.0),
            "desert_vs_native": math.log(8.0),
            "desert_spheroids_vs_native": math.log(16.0),
            "maritime_vs_continental": math.log(2.0),
            "desert_vs_continental": math.log(4.0),
            "desert_spheroids_vs_desert": math.log(2.0),
        }
        self.assertEqual(tuple(got), m.CONTRAST_IDS)
        for key, value in expected.items():
            self.assertAlmostEqual(got[key], value, places=12)

    def test_nonpositive_required_response_is_unresolved_without_epsilon(self) -> None:
        m = load_analysis()
        values = canonical_values()
        values["opac-desert"] = 0.0
        got = m.scalar_replicate_contrasts(records(values), "photopicLuminanceCdM2")
        self.assertIsNone(got["desert_vs_native"])
        self.assertIsNone(got["desert_vs_continental"])
        self.assertIsNone(got["desert_spheroids_vs_desert"])
        self.assertTrue(math.isfinite(got["desert_spheroids_vs_native"]))
        summary = m.summarize_three([got["desert_vs_native"]] * 3)
        self.assertEqual(summary["status"], "NUMERICALLY_UNRESOLVED")
        self.assertIsNone(summary["mean"])
        self.assertIsNone(summary["sampleStd"])
        self.assertIsNone(summary["standardError"])

    def test_exact_five_state_universe_is_required(self) -> None:
        m = load_analysis()
        bad = records(canonical_values())
        bad.pop("opac-maritime-clean")
        with self.assertRaisesRegex(m.AnalysisRefusal, "exact five-state"):
            m.scalar_replicate_contrasts(bad, "photopicLuminanceCdM2")

    def test_spectral_contrasts_and_three_replicate_summary_keep_8001_nodes(self) -> None:
        m = load_analysis()
        values = canonical_values()
        spectra = {state: [value] * 8001 for state, value in values.items()}
        one = m.spectral_replicate_contrasts(spectra)
        self.assertEqual(tuple(one), m.CONTRAST_IDS)
        self.assertTrue(all(len(nodes) == 8001 for nodes in one.values()))
        self.assertAlmostEqual(one["desert_spheroids_vs_desert"][0], math.log(2.0), places=12)
        summary = m.summarize_spectral_three([one, one, one])
        shape = summary["desert_spheroids_vs_desert"]
        self.assertAlmostEqual(shape["meanLogRatio"][0], math.log(2.0), places=12)
        self.assertAlmostEqual(shape["sampleStdLogRatio"][0], 0.0, places=12)
        self.assertAlmostEqual(shape["standardErrorLogRatio"][0], 0.0, places=12)
        self.assertEqual(shape["unresolvedNodeIndices"], [])
        self.assertEqual(shape["wavelengthGrid"]["nodeCount"], 8001)
        self.assertIs(shape["inferentialPValueOrConfidenceIntervalPermitted"], False)
        self.assertIs(shape["epsilonSubstitutionPermitted"], False)

    def test_three_replicate_scalar_summary_retains_all_values(self) -> None:
        m = load_analysis()
        base = records(canonical_values())
        reps = []
        for multiplier in (1.0, 1.0, 1.0):
            by_channel = {}
            for channel in m.PRIMARY_CHANNELS:
                scaled = {
                    state: {**row, channel: row[channel] * multiplier}
                    for state, row in base.items()
                }
                by_channel[channel] = m.scalar_replicate_contrasts(scaled, channel)
            reps.append(by_channel)
        out = m.aggregate_three_replicates(reps)
        shape = out["photopicLuminanceCdM2"]["desert_spheroids_vs_desert"]
        self.assertEqual(shape["status"], "FINITE_THREE_REPLICATES")
        for actual in shape["replicateValues"]:
            self.assertAlmostEqual(actual, math.log(2.0), places=12)
        self.assertAlmostEqual(shape["sampleStd"], 0.0, places=12)
        self.assertAlmostEqual(shape["standardError"], 0.0, places=12)

    def test_level_b_uses_exact_seven_deltas_and_no_time_conversion(self) -> None:
        script = r'''
import {
  AFPF_LEVEL_B_CONTRASTS,
  replicateLevelBContrasts,
  summarizeLevelBThreeReplicates,
} from './experiments/aerosol-full-phase-function-sensitivity-v1/level_b_analysis.mjs';

const records = {
  'native-rural-ss': { photopicLuminanceCdM2: 1 },
  'opac-continental-average': { photopicLuminanceCdM2: 10 },
  'opac-maritime-clean': { photopicLuminanceCdM2: 100 },
  'opac-desert': { photopicLuminanceCdM2: 1000 },
  'opac-desert-spheroids': { photopicLuminanceCdM2: 10000 },
};
const limiter = ({backgroundLuminanceCdM2}) => -2.5 * Math.log10(backgroundLuminanceCdM2);
const one = replicateLevelBContrasts(records, limiter);
const summary = summarizeLevelBThreeReplicates([one, one, one]);
const zero = structuredClone(records);
zero['opac-desert'].photopicLuminanceCdM2 = 0;
const unresolved = replicateLevelBContrasts(zero, limiter);
console.log(JSON.stringify({
  contrasts: AFPF_LEVEL_B_CONTRASTS,
  one,
  summary,
  unresolved: unresolved.pairedLimitingMagnitudeDelta,
}));
'''
        proc = subprocess.run(
            ["node", "--input-type=module", "-e", script],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(
            [row["contrastId"] for row in payload["contrasts"]],
            [
                "continental_vs_native",
                "maritime_vs_native",
                "desert_vs_native",
                "desert_spheroids_vs_native",
                "maritime_vs_continental",
                "desert_vs_continental",
                "desert_spheroids_vs_desert",
            ],
        )
        deltas = payload["one"]["pairedLimitingMagnitudeDelta"]
        expected = {
            "continental_vs_native": -2.5,
            "maritime_vs_native": -5.0,
            "desert_vs_native": -7.5,
            "desert_spheroids_vs_native": -10.0,
            "maritime_vs_continental": -2.5,
            "desert_vs_continental": -5.0,
            "desert_spheroids_vs_desert": -2.5,
        }
        for key, value in expected.items():
            self.assertAlmostEqual(deltas[key], value, places=12)
        summary = payload["summary"]
        self.assertEqual(summary["status"], "COMPLETED_PREREGISTERED_AFPF_LEVEL_B_SUMMARY")
        self.assertEqual(summary["contrastCount"], 7)
        self.assertEqual(summary["priorityShapeContrast"], "desert_spheroids_vs_desert")
        self.assertEqual(summary["contrasts"]["desert_spheroids_vs_desert"]["replicateValues"], [-2.5, -2.5, -2.5])
        self.assertAlmostEqual(summary["contrasts"]["desert_spheroids_vs_desert"]["sampleStd"], 0.0, places=12)
        self.assertIs(summary["pValuesPermitted"], False)
        self.assertIs(summary["confidenceIntervalsPermitted"], False)
        self.assertIs(summary["epsilonSubstitutionPermitted"], False)
        self.assertIs(summary["universalSunDepressionToMinutesConversionPermitted"], False)
        self.assertIsNone(payload["unresolved"]["desert_spheroids_vs_desert"])


if __name__ == "__main__":
    unittest.main()
