from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
STAGE = "aerosol-optical-property-sensitivity-v1"
STAGE_DIR = ROOT / "experiments" / STAGE
EVIDENCE_DIR = ROOT / "evidence" / STAGE
EXECUTION_DESIGN = STAGE_DIR / "execution_design.py"
ANALYSIS = STAGE_DIR / "analysis.py"
ANALYSIS_CONTRACT = STAGE_DIR / "analysis-contract.v1.json"
ADAPTER = STAGE_DIR / "adapter.py"
FREEZE = EVIDENCE_DIR / "review-freeze.json"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git_blob_sha1(path: Path) -> str:
    import hashlib
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


class AerosolOpticalPropertySensitivityV1ExecutionAnalysisReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.execution_design = load_module("aops_v1_execution_design_test", EXECUTION_DESIGN)
        cls.analysis = load_module("aops_v1_analysis_test", ANALYSIS)
        cls.adapter = load_module("aops_v1_adapter_execution_test", ADAPTER)

    def test_seeded_review_design_is_exact_and_still_non_renderable(self):
        d = self.execution_design.build_review_execution_design()
        self.assertEqual("REVIEW_ONLY_SEEDED_DESIGN_NON_RENDERABLE_NOT_AUTHORIZED", d["status"])
        self.assertEqual(24, d["analysisCellCount"])
        self.assertEqual(72, d["groupCount"])
        self.assertEqual(360, d["caseCount"])
        self.assertEqual(5, d["statesPerGroup"])
        self.assertTrue(d["authorizationTimeSeedRecheckRequired"])
        self.assertFalse(d["scientificOrdinalAllocated"])
        self.assertFalse(d["authorizationCreated"])
        self.assertFalse(d["dispatchCreated"])
        self.assertFalse(d["scientificExecutionAuthorized"])
        self.assertFalse(d["solverExecutionAuthorized"])
        self.assertFalse(d["resultOpeningAuthorized"])
        self.assertEqual(72, len({g["groupId"] for g in d["groups"]}))
        self.assertEqual(360, len({c["caseId"] for c in d["cases"]}))
        by_group = {}
        for c in d["cases"]:
            by_group.setdefault(c["groupId"], []).append(c)
        self.assertEqual(72, len(by_group))
        for members in by_group.values():
            self.assertEqual(5, len(members))
            self.assertEqual(1, len({m["seed"] for m in members}))
            self.assertEqual({"native-rural-ss", "ssa085-g060", "ssa085-g080", "ssa098-g060", "ssa098-g080"}, {m["stateId"] for m in members})
            self.assertTrue(all(m["renderable"] is False for m in members))
            self.assertTrue(all(m["executionAuthorized"] is False for m in members))

    def test_seeded_review_design_cannot_render(self):
        d = self.execution_design.build_review_execution_design()
        case = dict(d["cases"][0])
        self.assertIsInstance(case["seed"], int)
        self.assertFalse(case["renderable"])
        self.assertFalse(case["executionAuthorized"])
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(self.adapter.Refusal):
                self.adapter.render_case_input(case, Path(td) / "data", ROOT, Path(td) / "out")

    def test_analysis_contract_is_exact_and_noninferential(self):
        c = json.loads(ANALYSIS_CONTRACT.read_text())
        self.assertEqual("FROZEN_REVIEW_ONLY_ANALYSIS_CONTRACT_RESULTS_NOT_OPENED", c["status"])
        self.assertFalse(c["scientificExecutionAuthorized"])
        self.assertFalse(c["resultOpeningAuthorized"])
        u = c["caseUniverse"]
        self.assertEqual((24, 72, 3, 5, 360), (u["analysisCellCount"], u["commonRandomNumberGroupCount"], u["replicateCountPerCell"], u["statesPerGroup"], u["caseCount"]))
        self.assertTrue(u["commonSeedRequiredAcrossFiveStatesWithinGroup"])
        self.assertEqual(9, len(c["scalarContrastsPerCellReplicate"]))
        self.assertEqual(8001, c["spectralContrasts"]["rawWavelengthNodeCount"])
        r = c["replicateSummary"]
        self.assertEqual(3, r["replicateCount"])
        self.assertFalse(r["independentErrorQuadraturePermitted"])
        self.assertFalse(r["pValuesPermitted"])
        self.assertFalse(r["confidenceIntervalsPermitted"])
        self.assertFalse(c["numericRules"]["epsilonSubstitutionPermitted"])
        self.assertFalse(c["numericRules"]["dropUnresolvedReplicateAndUseRemainingReplicatesPermitted"])
        lb = c["secondaryLevelB"]
        self.assertEqual(2.4, lb["fieldFactor"])
        self.assertFalse(lb["universalSunDepressionToMinutesConversionPermitted"])
        self.assertTrue(lb["timeConversionRequiresActualDateLocationSolarDepressionRate"])

    def _scalar_records(self, channel: str):
        return {
            "native-rural-ss": {channel: 1.0},
            "ssa085-g060": {channel: 2.0},
            "ssa085-g080": {channel: 4.0},
            "ssa098-g060": {channel: 8.0},
            "ssa098-g080": {channel: 32.0},
        }

    def test_scalar_factorial_contrasts_and_interaction_are_exact(self):
        for channel in self.analysis.PRIMARY_CHANNELS:
            x = self.analysis.scalar_replicate_contrasts(self._scalar_records(channel), channel)
            self.assertAlmostEqual(math.log(2.0), x["native_vs_ssa085_g060"])
            self.assertAlmostEqual(math.log(4.0), x["native_vs_ssa085_g080"])
            self.assertAlmostEqual(math.log(8.0), x["native_vs_ssa098_g060"])
            self.assertAlmostEqual(math.log(32.0), x["native_vs_ssa098_g080"])
            self.assertAlmostEqual(math.log(4.0), x["ssa_high_vs_low_at_g060"])
            self.assertAlmostEqual(math.log(8.0), x["ssa_high_vs_low_at_g080"])
            self.assertAlmostEqual(math.log(2.0), x["g_high_vs_low_at_ssa085"])
            self.assertAlmostEqual(math.log(4.0), x["g_high_vs_low_at_ssa098"])
            self.assertAlmostEqual(math.log(2.0), x["ssa_x_g_interaction"])

    def test_nonpositive_values_are_unresolved_without_epsilon(self):
        channel = self.analysis.PRIMARY_CHANNELS[0]
        rows = self._scalar_records(channel)
        rows["native-rural-ss"][channel] = 0.0
        x = self.analysis.scalar_replicate_contrasts(rows, channel)
        self.assertIsNone(x["native_vs_ssa085_g060"])
        self.assertIsNone(x["native_vs_ssa098_g080"])
        s = self.analysis.summarize_three([None, 0.1, 0.2])
        self.assertEqual("NUMERICALLY_UNRESOLVED", s["status"])
        self.assertIsNone(s["mean"])
        self.assertIsNone(s["sampleStd"])
        self.assertIsNone(s["standardError"])

    def test_three_replicate_summary_uses_sample_sd_and_se(self):
        values = [1.0, 2.0, 3.0]
        s = self.analysis.summarize_three(values)
        self.assertEqual("FINITE_THREE_REPLICATES", s["status"])
        self.assertAlmostEqual(2.0, s["mean"])
        self.assertAlmostEqual(1.0, s["sampleStd"])
        self.assertAlmostEqual(1.0 / math.sqrt(3.0), s["standardError"])
        self.assertEqual(values, s["replicateValues"])

    def test_spectral_contrasts_require_8001_nodes_and_use_same_interaction(self):
        spectra = {
            "native-rural-ss": [1.0] * 8001,
            "ssa085-g060": [2.0] * 8001,
            "ssa085-g080": [4.0] * 8001,
            "ssa098-g060": [8.0] * 8001,
            "ssa098-g080": [32.0] * 8001,
        }
        x = self.analysis.spectral_replicate_contrasts(spectra)
        self.assertEqual(9, len(x))
        self.assertTrue(all(len(v) == 8001 for v in x.values()))
        self.assertAlmostEqual(math.log(2.0), x["ssa_x_g_interaction"][0])
        self.assertAlmostEqual(math.log(2.0), x["ssa_x_g_interaction"][-1])
        bad = dict(spectra)
        bad["ssa098-g080"] = [32.0] * 8000
        with self.assertRaises(self.analysis.AnalysisRefusal):
            self.analysis.spectral_replicate_contrasts(bad)

    def test_spectral_three_replicate_summary_is_noninferential(self):
        one = {"ssa_x_g_interaction": [math.log(2.0)] * 8001}
        two = {"ssa_x_g_interaction": [math.log(2.2)] * 8001}
        three = {"ssa_x_g_interaction": [math.log(1.8)] * 8001}
        out = self.analysis.summarize_spectral_three([one, two, three])
        row = out["ssa_x_g_interaction"]
        self.assertEqual(8001, len(row["meanLogRatio"]))
        self.assertEqual([], row["unresolvedNodeIndices"])
        self.assertFalse(row["inferentialPValueOrConfidenceIntervalPermitted"])
        self.assertEqual(8001, row["wavelengthGrid"]["nodeCount"])

    def test_freeze_binds_execution_design_analysis_and_contract(self):
        f = json.loads(FREEZE.read_text())
        self.assertEqual(git_blob_sha1(EXECUTION_DESIGN), f["executionDesignGitBlobSha1"])
        self.assertEqual(git_blob_sha1(ANALYSIS), f["analysisImplementationGitBlobSha1"])
        self.assertEqual(git_blob_sha1(ANALYSIS_CONTRACT), f["analysisContractGitBlobSha1"])
        self.assertEqual("50b64b5c8a7a9d28a1c7174c1a1fda8d7380799d", f["sourceR8AnalysisGitBlobSha1"])
        self.assertEqual("ccfd04d4c21188966351f4257e92893d7ce340c7", f["sourceR8DerivedChannelsGitBlobSha1"])
        self.assertFalse(f["candidateSeedAuthorizationRecheckPassed"])
        self.assertFalse(f["scientificOrdinalAllocated"])
        self.assertFalse(f["authorizationCreated"])
        self.assertFalse(f["dispatchCreated"])
        self.assertFalse(f["scientificExecutionAuthorized"])
        self.assertFalse(f["solverExecutionAuthorized"])
        self.assertFalse(f["resultOpeningAuthorized"])


if __name__ == "__main__":
    unittest.main()
