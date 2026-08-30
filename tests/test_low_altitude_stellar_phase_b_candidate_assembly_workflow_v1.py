from __future__ import annotations

import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github/workflows/low-altitude-stellar-phase-b-candidate-assembly-v1-one-shot.yml'


class CandidateAssemblyWorkflowV1Tests(unittest.TestCase):
    def test_workflow_is_solver_free_single_use_and_training_bound(self):
        text = WORKFLOW.read_text(encoding='utf-8')
        self.assertIn('dispatch/low-altitude-stellar-phase-b-candidate-assembly-v1', text)
        self.assertIn("SOURCE_RUN_ID: '33310723749'", text)
        self.assertIn("SOURCE_JOB_ID: '99255161427'", text)
        self.assertIn("SOURCE_DISPATCH_SHA: '5ddb68e9a46fe9cc0bbb225dbe9614b47e4b24c2'", text)
        self.assertIn("SOURCE_V32_RUNTIME_SHA256: '0b96bd5868dc0c72d5cd77b504098d35086feaf573d92556c4f8311a163e3ce2'", text)
        self.assertIn('test "$GITHUB_RUN_ATTEMPT" = 1', text)
        self.assertIn('test "${#CHANGED[@]}" = 1', text)
        self.assertIn('test -z "$(command -v uvspec || true)"', text)
        self.assertIn('protectedValidationAuthorized', text)
        self.assertIn('scientificSolverExecutionAuthorized', text)
        self.assertIn('minimumScientificallySupportedGeometricAltitudeDeg', text)
        self.assertIn('exactFiveDegreeSeamContentIdentical', text)
        self.assertNotIn('rte_solver', text)
        self.assertNotIn('micromamba', text)
        self.assertNotIn('Taylor', text)
        self.assertNotIn('Jerusalem', text)
        self.assertNotIn('workflow_dispatch:', text)

    def test_artifact_identity_is_verified_before_download(self):
        text = WORKFLOW.read_text(encoding='utf-8')
        metadata = text.index('Verify immutable training artifact metadata')
        download = text.index('Download exact immutable training artifact')
        eligibility = text.index('Verify terminal eligible training evidence before assembly')
        assembly = text.index('Assemble immutable protected-closed candidate once')
        self.assertLess(metadata, download)
        self.assertLess(download, eligibility)
        self.assertLess(eligibility, assembly)
        self.assertIn("p['digest']==artifact_digest", text)
        self.assertIn("p['workflow_run']['head_sha']==os.environ['SOURCE_DISPATCH_SHA']", text)
        self.assertIn("r['trainingScientificallyEligible'] is True", text)
        self.assertIn("r['numericallyUnresolvedTrainingSpectrumCount']==0", text)


if __name__ == '__main__':
    unittest.main()
