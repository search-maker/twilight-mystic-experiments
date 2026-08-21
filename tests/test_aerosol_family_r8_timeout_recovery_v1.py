from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "experiments/aerosol-family-challenge-v2-r8-timeout-recovery-v1"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


core = load("afc2_timeout_recovery_core", PKG / "core.py")
runner = load("afc2_timeout_recovery_runner", PKG / "execution-candidate/process_runner.py")


class RecoveryProtocolTests(unittest.TestCase):
    def setUp(self):
        self.protocol = json.loads((PKG / "protocol.review.json").read_text())

    def test_review_protocol_is_frozen_and_fail_closed(self):
        core.validate_protocol(self.protocol)
        self.assertFalse(self.protocol["scientificExecutionAuthorized"])
        self.assertFalse(self.protocol["solverExecutionAuthorized"])
        self.assertFalse(self.protocol["dispatchAuthorized"])
        self.assertFalse(self.protocol["resultsOpened"])
        self.assertEqual(568, self.protocol["retentionAndReplacement"]["retainedSourceCaseCount"])
        self.assertEqual(8, self.protocol["retentionAndReplacement"]["freshReplacementCaseCount"])
        self.assertEqual(576, self.protocol["retentionAndReplacement"]["effectiveCombinedCaseCount"])
        self.assertEqual(core.SOURCE_TIMEOUT_ANNOTATION, self.protocol["sourceEvidenceBindings"]["githubTimeoutAnnotationMessage"])
        self.assertEqual(core.SOURCE_ANALYSIS_CONTRACT_RAW_SHA256, self.protocol["sourceAnalysisBindings"]["analysisContractRawSha256"])
        ledger_path = PKG / "candidate-seed-ledger.v1.json"
        self.assertEqual(core.RECOVERY_SEED_LEDGER_RAW_SHA256, core.raw_sha256(ledger_path))
        self.assertEqual(core.RECOVERY_SEED_LEDGER_RAW_SHA256, self.protocol["recoveryGroup"]["candidateSeedLedgerRawSha256"])

    def test_seed_derivation_is_exact_and_fresh_relative_to_failed_group(self):
        seed, material, material_sha = core.derive_recovery_seed()
        self.assertEqual(371960104, seed)
        self.assertNotEqual(core.SOURCE_GROUP_SEED, seed)
        self.assertEqual(self.protocol["recoveryGroup"]["seedDerivationMaterial"], material)
        self.assertEqual(self.protocol["recoveryGroup"]["seedDerivationMaterialSha256"], material_sha)

    def test_manifest_replaces_entire_crn_group_and_nothing_physical(self):
        template = {
            "stageId": core.SOURCE_STAGE_ID,
            "caseCount": 576,
            "sourceBindings": {"runtimeLock": {"rawSha256": "a" * 64}},
            "cases": [],
        }
        for i in range(568):
            template["cases"].append({"caseId": f"keep-{i}", "groupId": f"other-{i}", "seed": 1000 + i})
        for family in core.FAMILIES:
            for season in core.SEASONS:
                template["cases"].append({
                    "caseId": f"{core.FAILED_GROUP_ID}-{family}-{season}",
                    "groupId": core.FAILED_GROUP_ID,
                    "analysisCellId": "afc2-d04-g06-late-opposite-high-aerosol-aod10",
                    "replicate": 2,
                    "seed": core.SOURCE_GROUP_SEED,
                    "photonHistories": core.EXPECTED_PHOTON_HISTORIES_PER_CASE,
                    "aerosolFamily": family,
                    "aerosolSeason": season,
                    "sunDepressionDeg": 4.0,
                    "targetAltitudeDeg": 45.0,
                    "relativeAzimuthDeg": 180.0,
                    "observerElevationM": 0.0,
                    "aod550": 0.1,
                    "albedo": 0.15,
                })
        manifest = core.build_recovery_manifest(self.protocol, template)
        self.assertEqual(8, manifest["caseCount"])
        self.assertEqual({core.RECOVERY_SEED}, {row["seed"] for row in manifest["cases"]})
        self.assertEqual({core.SOURCE_GROUP_SEED}, {row["sourceOrdinal34Seed"] for row in manifest["cases"]})
        self.assertEqual({core.FAILED_GROUP_ID}, {row["groupId"] for row in manifest["cases"]})
        self.assertEqual({20_000_000}, {row["photonHistories"] for row in manifest["cases"]})
        self.assertEqual({4.0}, {row["sunDepressionDeg"] for row in manifest["cases"]})
        self.assertEqual({45.0}, {row["targetAltitudeDeg"] for row in manifest["cases"]})
        self.assertEqual({180.0}, {row["relativeAzimuthDeg"] for row in manifest["cases"]})
        self.assertEqual({0.1}, {row["aod550"] for row in manifest["cases"]})


class ProcessGroupTimeoutTests(unittest.TestCase):
    def test_timeout_terminates_descendant_process_group(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            child_pid_path = root / "child.pid"
            script = root / "spawn.py"
            script.write_text(
                "import pathlib, subprocess, sys, time\n"
                "p=subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
                "pathlib.Path('child.pid').write_text(str(p.pid))\n"
                "print('spawned', p.pid, flush=True)\n"
                "time.sleep(60)\n"
            )
            started = time.monotonic()
            result = runner.run_process_group([os.sys.executable, str(script)], "", root, 1, sigterm_grace_seconds=1)
            elapsed = time.monotonic() - started
            self.assertTrue(result["timedOut"])
            self.assertTrue(result["processGroupIsolated"])
            self.assertTrue(result["processGroupTerminationAttempted"])
            self.assertLess(elapsed, 8.0)
            child_pid = int(child_pid_path.read_text())
            time.sleep(0.1)
            proc_stat = Path(f"/proc/{child_pid}/stat")
            if proc_stat.exists():
                state = proc_stat.read_text().split()[2]
                self.assertEqual("Z", state, f"descendant remained live in state {state}")


if __name__ == "__main__":
    unittest.main()
