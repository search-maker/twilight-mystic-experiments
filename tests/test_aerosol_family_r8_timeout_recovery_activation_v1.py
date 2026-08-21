from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
STAGE = "aerosol-family-challenge-v2-r8-timeout-recovery-v1"
PKG = ROOT / "experiments" / STAGE
EVIDENCE = ROOT / "evidence" / STAGE
PRE = ROOT / ".github/workflows/aerosol-family-v2-r8-timeout-recovery-v1-preauthorization.yml"
AUTH_REVIEW = ROOT / ".github/workflows/aerosol-family-v2-r8-timeout-recovery-v1-authorization-review.yml"
EXEC = ROOT / ".github/workflows/aerosol-family-v2-r8-timeout-recovery-v1-execution.yml"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ActivationTests(unittest.TestCase):
    def test_manifest_is_exact_targeted_replacement(self):
        m=json.loads((EVIDENCE/'manifest.frozen.json').read_text())
        self.assertEqual(STAGE,m['stageId']); self.assertEqual(8,m['caseCount']); self.assertEqual(1,m['groupCount'])
        self.assertEqual(568,m['retainedSourceCaseCountForFutureCombinedAnalysis']); self.assertEqual(576,m['effectiveCombinedCaseCount'])
        self.assertEqual({371960104},{r['seed'] for r in m['cases']}); self.assertEqual({798398324},{r['sourceOrdinal34Seed'] for r in m['cases']})
        self.assertEqual({'afc2-d04-g06-late-opposite-high-aerosol-aod10-r2'},{r['groupId'] for r in m['cases']})
        self.assertEqual({20_000_000},{r['photonHistories'] for r in m['cases']})
        self.assertEqual({4.0},{r['sunDepressionDeg'] for r in m['cases']}); self.assertEqual({45.0},{r['targetAltitudeDeg'] for r in m['cases']})
        self.assertEqual({180.0},{r['relativeAzimuthDeg'] for r in m['cases']}); self.assertEqual({0.0},{r['observerElevationM'] for r in m['cases']})
        self.assertEqual({0.1},{r['aod550'] for r in m['cases']}); self.assertEqual({0.15},{r['albedo'] for r in m['cases']})
        self.assertEqual(7200,m['solverTimeoutSeconds']); self.assertEqual(150,m['githubJobTimeoutMinutes'])
        self.assertFalse(m['boundary']['scientificExecutionAuthorized']); self.assertFalse(m['boundary']['solverExecutionAuthorized'])

    def test_deterministic_freeze_verifies_against_source_manifest_when_present(self):
        source=ROOT/'evidence/aerosol-family-challenge-v2-r8/manifest.frozen.json'
        if not source.is_file():
            self.skipTest('source R8 manifest absent in isolated fixture checkout')
        freeze=load('afc2_recovery_activation_freeze',PKG/'freeze.py')
        self.assertEqual((EVIDENCE/'manifest.frozen.json').read_bytes(),freeze.expected_bytes(ROOT))

    def test_authorization_document_binds_exact_activation_transport(self):
        if not (ROOT/'experiments/aerosol-family-challenge-v2-r8/core.py').is_file():
            self.skipTest('source R8 byte-bound package absent in isolated fixture checkout')
        auth=load('afc2_recovery_activation_auth',PKG/'execution-candidate/authorization.py')
        row=auth.make(ROOT,35,'1'*40)
        auth.validate(ROOT,row,expected_parent='1'*40)
        self.assertEqual(f'{STAGE}:numerical:35',row['executionKey'])
        self.assertFalse(row['githubRerunAllowed']); self.assertFalse(row['retryAllowed']); self.assertFalse(row['resumeAllowed'])
        self.assertFalse(row['sourceOrdinal34Reusable']); self.assertFalse(row['sourceOrdinal34AffectedGroupArtifactsReusable'])
        self.assertIn('executionWorkflowRawSha256',row); self.assertIn('seedAuditRawSha256',row)
        self.assertEqual('04e93e1054ba2957383749ca4f4735b231993733',row['sourceR8CoreGitBlobSha1'])
        self.assertEqual('108af0a95274ee88fccf9d51d32f88ef0186bfaf',row['sourceR8AdapterGitBlobSha1'])
        self.assertEqual('ccfd04d4c21188966351f4257e92893d7ce340c7',row['sourceR8DerivedChannelsGitBlobSha1'])

    def test_zero_runtime_gates_and_scientific_execution_shape(self):
        pre=PRE.read_text(); review=AUTH_REVIEW.read_text(); exe=EXEC.read_text()
        for text in (pre,review):
            self.assertNotIn('setup-micromamba@',text); self.assertNotIn('--allow-execution',text)
        self.assertIn('workflow_dispatch:',exe)
        self.assertNotIn('push:\n    branches:',exe)
        self.assertIn('max-parallel: 2',exe); self.assertIn('timeout-minutes: 150',exe)
        self.assertIn('rubin-libradtran=2.0.6=py312pl5321he9373c2_1',exe)
        self.assertIn('Execute exactly one fresh recovery case',exe)
        self.assertIn('allow_execution=True',exe)
        self.assertIn('afc2-r8-timeout-recovery-v1-case-${{ matrix.caseId }}',exe)
        self.assertIn('COMPLETE_EXACT_8_FRESH_REPLACEMENT_CASE_ARTIFACT_UNIVERSE',exe)
        self.assertNotIn('rerun_workflow',exe.lower()); self.assertNotIn('gh run rerun',exe.lower())

    def test_process_group_timeout_is_bound_and_source_science_adapter_is_reused(self):
        runner=(PKG/'execution-candidate/process_runner.py').read_text(); executor=(PKG/'execution-candidate/executor.py').read_text()
        self.assertIn('start_new_session=True',runner); self.assertIn('os.killpg(proc.pid, signal.SIGTERM)',runner); self.assertIn('os.killpg(proc.pid, signal.SIGKILL)',runner)
        self.assertIn('experiments/aerosol-family-challenge-v2-r8',executor)
        self.assertIn('source / "adapter.py"',executor); self.assertIn('source / "derived_channels.py"',executor)
        self.assertIn('int(manifest["solverTimeoutSeconds"])',executor)

    def test_seed_audit_has_strict_preregistration_self_exception_only(self):
        text=(PKG/'execution-candidate/seed_audit.py').read_text()
        self.assertIn('PREREGISTRATION_PR_NUMBER = 286',text)
        self.assertIn('PREREGISTRATION_PR_HEAD = "002b671089c5a7f27f7d65781ce78e4cb9981150"',text)
        self.assertIn('PASS_STABLE_DOUBLE_ENUMERATION_NO_EXTERNAL_SEED_COLLISION',text)
        self.assertIn('tracked_collisions',text); self.assertIn('metadata_collisions',text)


if __name__=='__main__': unittest.main()
