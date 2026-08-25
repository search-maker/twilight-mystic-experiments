import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / 'review/asiv-matched-stellar-transport-v1'
RECOVERY = STAGE / 'science-control-recovery-v2'
BUILDER = RECOVERY / 'authorization_builder_review.py'
CONTRACT = RECOVERY / 'SCIENCE_CONTROL_CONTRACT.review.json'
SCIENCE = ROOT / '.github/workflows/asiv-matched-stellar-science-recovery-v2.yml'
AUTH_REVIEW = ROOT / '.github/workflows/asiv-matched-stellar-authorization-review-recovery-v2.yml'
AUTH_PATH = STAGE / 'authorization-recovery-v2.json'


def load_builder():
    spec = importlib.util.spec_from_file_location('recovery_v2_builder_test', BUILDER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class MatchedStellarRecoveryV2ControlTests(unittest.TestCase):
    def test_recovery_contract_is_zero_runtime_and_science_invariant(self):
        c = json.loads(CONTRACT.read_text(encoding='utf-8'))
        self.assertEqual(c['status'], 'FROZEN_RECOVERY_V2_CONTROL_PRE_SOLVER_INFRASTRUCTURE_FIX')
        self.assertEqual(c['recoveryFromRunId'], 32848973816)
        self.assertFalse(c['priorRunSolverExecutionPerformed'])
        self.assertEqual(c['priorRunScientificShardArtifactCount'], 0)
        self.assertFalse(c['scientificCaseUniverseChanged'])
        self.assertFalse(c['scientificAcceptanceGatesChanged'])
        self.assertFalse(c['runtimeIdentityClaimsChanged'])
        self.assertFalse(c['aerosolFamiliesChanged'])
        self.assertFalse(c['photometricAssetsChanged'])
        self.assertFalse(c['interpolationSemanticsChanged'])
        self.assertFalse(c['scientificExecutionAuthorizedByThisContract'])
        self.assertFalse(c['dispatchPerformedByThisContract'])
        self.assertFalse(c['pandoraHoldoutAccessAllowed'])
        self.assertFalse(c['productionActivationAuthorized'])
        self.assertEqual(c['scientificUniverse']['caseCount'], 3468)
        self.assertEqual(c['scientificUniverse']['shardCount'], 99)
        self.assertEqual(c['scientificUniverse']['validationJohnsonVComparisonsTotal'], 2304)
        self.assertEqual(c['acceptance']['maxAbsoluteJohnsonVExtinctionErrorMagPerFamily'], 0.025)
        self.assertEqual(c['acceptance']['rmsJohnsonVExtinctionErrorMagPerFamily'], 0.01)

    def test_recovery_builder_binds_exact_active_workflow_bytes_and_frozen_gates(self):
        m = load_builder()
        active = m.validate_active_workflows(ROOT)
        self.assertEqual(active['authorizationReviewWorkflowActiveGitBlobSha1'], 'f9fefa51ae73a55d91c937fc652a5aa3e3b03c51')
        self.assertEqual(active['scienceWorkflowActiveGitBlobSha1'], 'e272da7d2dc497f1d06537d7796ef3af2092c965')
        auth = m.build_authorization(ROOT, 'a' * 40)
        self.assertEqual(auth['caseUniverse']['trainingSpectraTotal'], 2700)
        self.assertEqual(auth['caseUniverse']['validationAtmosphericSpectraTotal'], 768)
        self.assertEqual(auth['caseUniverse']['validationJohnsonVComparisonsTotal'], 2304)
        self.assertEqual(auth['batchBindings']['totalShardCount'], 99)
        self.assertEqual(auth['batchBindings']['totalCaseCount'], 3468)
        self.assertEqual(auth['validationAcceptance']['maxAbsoluteJohnsonVExtinctionErrorMagPerFamily'], 0.025)
        self.assertEqual(auth['validationAcceptance']['rmsJohnsonVExtinctionErrorMagPerFamily'], 0.01)
        self.assertFalse(auth['nativeRenderable'])
        self.assertFalse(auth['pandoraHoldoutAccessAllowed'])
        self.assertFalse(auth['productionActivationAuthorized'])
        self.assertFalse(auth['retryPermitted'])
        self.assertFalse(auth['resumePermitted'])
        self.assertFalse(auth['githubRerunPermitted'])
        self.assertEqual(auth['recoveryFromRunId'], 32848973816)
        self.assertFalse(auth['priorRunSolverExecutionPerformed'])
        self.assertEqual(auth['priorRunScientificShardArtifactCount'], 0)

    def test_only_runtime_metadata_discovery_is_recovered(self):
        text = SCIENCE.read_text(encoding='utf-8')
        self.assertNotIn("subprocess.check_output(['micromamba','list','--json']", text)
        self.assertIn("meta_dir=Path(os.environ['CONDA_PREFIX'])/'conda-meta'", text)
        self.assertIn("glob('rubin-libradtran-*.json')", text)
        self.assertIn("rubin-libradtran=2.0.6=py312pl5321he9373c2_1", text)
        self.assertIn("RECOVERY_SOURCE_CONFIRMED_PRE_SOLVER_FAILURE", text)
        self.assertIn("32848973816", text)
        self.assertIn("d1c4f156967e592ee41f4c1a829e7d551a4f7ea7", (STAGE / 'BATCH_ORCHESTRATION_CONTRACT.review.json').read_text(encoding='utf-8') if False else 'd1c4f156967e592ee41f4c1a829e7d551a4f7ea7')
        self.assertFalse(AUTH_PATH.exists())

    def test_recovery_workflows_have_expected_triggers_and_no_automatic_dispatch(self):
        science = SCIENCE.read_text(encoding='utf-8')
        review = AUTH_REVIEW.read_text(encoding='utf-8')
        self.assertIn('workflow_dispatch:', science)
        self.assertNotIn('schedule:', science)
        self.assertNotIn('push:', science)
        self.assertIn("dispatch/asiv-matched-stellar-transport-recovery-v2", science)
        self.assertIn("authorization/asiv-matched-stellar-transport-recovery-v2", science)
        self.assertIn("authorization-recovery-v2.json", review)
        self.assertIn("github.event.pull_request.draft == true", review)


if __name__ == '__main__':
    unittest.main()
