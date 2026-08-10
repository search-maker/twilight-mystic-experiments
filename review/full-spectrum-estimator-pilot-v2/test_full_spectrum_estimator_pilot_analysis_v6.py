from __future__ import annotations

import hashlib
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ana = load_module("ana_v6", ROOT / "analyze_full_spectrum_estimator_pilot_v6.py")
ACQ = json.loads((ROOT / "full-spectrum-estimator-pilot-preregistration-v2.json").read_text())
AP = json.loads((ROOT / "full-spectrum-estimator-pilot-screening-analysis-preregistration-v4.json").read_text())
ADM = json.loads((ROOT / "full-spectrum-training-admission-complete-v1.json").read_text())
BASE = {g["geometryId"]: g for g in ADM["geometryReports"]}


def canon(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def synth_evidence(rsem_overrides=None, zero_overrides=None):
    rsem_overrides = rsem_overrides or {}
    zero_overrides = zero_overrides or set()
    rows = []
    for case in ACQ["cases"]:
        hist = BASE[case["geometryId"]]
        channels = {}
        sign = -1.0 if case["replicate"] == 1 else 1.0
        for name in ana.PRIMARY:
            values = [float(x) for x in hist["channels"][name]["values"]]
            mean = sum(values) / len(values)
            key = (case["geometryId"], case.get("importanceCenterNm"), name)
            d = float(rsem_overrides.get(key, 0.02))
            x = mean * (1.0 + sign * d)
            if (case["caseId"], name) in zero_overrides:
                x = 0.0
            channels[name] = x
        all_zero = all(channels[name] == 0.0 for name in ana.PRIMARY)
        rows.append(
            {
                "caseId": case["caseId"],
                "geometryId": case["geometryId"],
                "method": case["method"],
                "importanceCenterNm": case.get("importanceCenterNm"),
                "replicate": case["replicate"],
                "seed": case["seed"],
                "photonHistories": case["photonHistories"],
                "channels": channels,
                "zeroHit": all_zero,
            }
        )
    evidence = {
        "schemaVersion": 1,
        "evidenceId": "public-tier1-full-spectrum-estimator-pilot-normalized-evidence-v6",
        "status": "NORMALIZED",
        "protocolSha256": ana.ACQUISITION_PROTOCOL_SHA,
        "executionManifestSha256": ana.EXEC_SHA,
        "caseCount": 44,
        "cases": rows,
        "holdoutValuesRead": False,
    }
    evidence["evidenceSha256"] = canon(evidence)
    return evidence


def method_report(output, gid, center):
    geometry = next(row for row in output["geometryReports"] if row["geometryId"] == gid)
    return next(
        row
        for row in geometry["methodReports"]
        if row["method"] == "alis-alt-importance" and row["importanceCenterNm"] == center
    )


class T(unittest.TestCase):
    def test_analysis_protocol_hash_and_frozen_baseline_reproduces(self):
        self.assertEqual(AP["analysisProtocolSha256"], canon({k: v for k, v in AP.items() if k != "analysisProtocolSha256"}))
        frozen = ana.validate_analysis_protocol(AP, ACQ, ADM)
        self.assertEqual(set(frozen), set(ACQ["selectionBoundary"]["selectedGeometryIds"]))
        self.assertTrue(AP["historicalFirstTwoScreeningBaseline"]["fullAdaptiveHistoryMayBeReportedAsContextButNotUsedInVarianceGainThreshold"])
        self.assertTrue(AP["screeningRules"]["sameNVarianceGain"]["nonProblemChannelNonDegradationGuard"]["required"])
        self.assertFalse(AP["screeningRules"]["freshPrimaryChannelZeroPolicy"]["allChannelsZeroRequiredToTrigger"])

    def test_like_for_like_regression_train0041(self):
        overrides = {("train-0041", 550.0, name): 0.10 for name in ana.PRIMARY}
        output = ana.analyze(ACQ, AP, ADM, synth_evidence(overrides))
        report = method_report(output, "train-0041", 550.0)
        self.assertGreater(max(report["statistics"]["channels"][name]["descriptiveTwoBlockRsem"] for name in ana.PRIMARY), 0.08)
        old_full = max(next(g for g in output["geometryReports"] if g["geometryId"] == "train-0041")["historicalChannels"][name]["rsem"] for name in ana.PRIMARY)
        self.assertGreater(0.10, 0.5 * old_full)
        self.assertEqual(report["classification"], "SCREENING_VARIANCE_GAIN_ON_HISTORICAL_PROBLEM_CHANNELS")
        self.assertTrue(report["sameNVarianceGainScreen"]["passed"])
        self.assertTrue(output["nonProblemChannelVarianceNonDegradationGuardEnforced"])
        self.assertFalse(output["fullAdaptiveHistoricalRsemUsedForVarianceGainThreshold"])

    def test_first_two_and_full_history_are_distinct_contexts(self):
        frozen = ana.validate_analysis_protocol(AP, ACQ, ADM)["train-0041"]
        scotopic = frozen["channels"]["scotopicLuminanceScotCdM2"]
        self.assertGreater(scotopic["firstTwoDescriptiveRsem"], 0.40)
        self.assertLess(scotopic["fullHistoryRsem"], 0.09)

    def test_channel_specific_zero_refuses_candidate_even_if_case_not_all_zero(self):
        zero = {("train-0014-fs-alis-500-r1", "scotopicLuminanceScotCdM2")}
        output = ana.analyze(ACQ, AP, ADM, synth_evidence(zero_overrides=zero))
        report = method_report(output, "train-0014", 500.0)
        self.assertTrue(report["statistics"]["anyPrimaryChannelZeroHit"])
        self.assertEqual(report["statistics"]["allPrimaryChannelsZeroHitCaseCount"], 0)
        self.assertEqual(report["classification"], "NO_CLEAR_SCREENING_GAIN")
        self.assertTrue(output["freshPrimaryChannelZeroPolicyEnforced"])

    def test_nonproblem_channel_degradation_blocks_strong_gain(self):
        overrides = {
            ("train-0014", 500.0, "scotopicLuminanceScotCdM2"): 0.04,
            ("train-0014", 500.0, "photopicLuminanceCdM2"): 0.20,
            ("train-0014", 500.0, "johnsonVEffectiveRadiance_mW_m2_nm_sr"): 0.20,
        }
        output = ana.analyze(ACQ, AP, ADM, synth_evidence(overrides))
        report = method_report(output, "train-0014", 500.0)
        screen = report["sameNVarianceGainScreen"]
        self.assertTrue(screen["allProblemChannelsPass"])
        self.assertFalse(screen["allNonProblemChannelsPassNonDegradation"])
        self.assertFalse(screen["passed"])
        self.assertEqual(report["classification"], "NO_CLEAR_SCREENING_GAIN")

    def test_good_scotopic_gain_with_safe_other_channels_can_nominate(self):
        overrides = {
            ("train-0014", 500.0, "scotopicLuminanceScotCdM2"): 0.04,
            ("train-0014", 500.0, "photopicLuminanceCdM2"): 0.06,
            ("train-0014", 500.0, "johnsonVEffectiveRadiance_mW_m2_nm_sr"): 0.06,
        }
        output = ana.analyze(ACQ, AP, ADM, synth_evidence(overrides))
        report = method_report(output, "train-0014", 500.0)
        self.assertEqual(report["classification"], "LOW_TWO_BLOCK_RSEM_SCREENING_CANDIDATE")

    def test_tampered_analysis_protocol_refused(self):
        bad = json.loads(json.dumps(AP))
        bad["screeningRules"]["sameNVarianceGain"]["maximumVarianceProxyRatioOnEveryFiniteHistoricalProblemChannel"] = 0.9
        with self.assertRaisesRegex(ValueError, "analysis protocol identity"):
            ana.analyze(ACQ, bad, ADM, synth_evidence())


if __name__ == "__main__":
    unittest.main()
