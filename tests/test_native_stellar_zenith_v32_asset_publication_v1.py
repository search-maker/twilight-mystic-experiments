import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/native-stellar-zenith-v32-asset-publication-v1.yml"


class NativeStellarZenithV32AssetPublicationV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_source_identity_is_frozen(self):
        for token in (
            "SOURCE_RUN_ID: '33044767268'",
            "SOURCE_ARTIFACT_ID: '9635340184'",
            "sha256:bb08c75c916db36408cdad86a392a450ca09bcc29060d1003c0b1eb551a6e0a0",
            "9e33f2f76bbb34ce651b496cfd910265fbf77b01",
            "0b96bd5868dc0c72d5cd77b504098d35086feaf573d92556c4f8311a163e3ce2",
            "235e7252f9d8c926aeda54899d106451a71a85d23dd859d349a1b46c1f7c72be",
            "21eeb51fcc5287ab3bb8cb59cfe0bb0073f34e9ca1b6cc6df988c6eb5043631f",
        ):
            self.assertIn(token, self.text)

    def test_workflow_is_publication_only(self):
        self.assertIn("test -z \"$(command -v uvspec || true)\"", self.text)
        self.assertNotIn("micromamba", self.text)
        self.assertNotIn("mc_photons", self.text)
        self.assertNotIn("rte_solver", self.text)
        self.assertNotIn("allow-execution", self.text)
        self.assertNotIn("workflow_dispatch", self.text)

    def test_one_shot_and_isolated_result_branch_are_required(self):
        self.assertIn('test "$GITHUB_RUN_ATTEMPT" = "1"', self.text)
        self.assertIn("review/native-stellar-zenith-v32-publication-v1/dispatch.json", self.text)
        self.assertIn("publication/native-stellar-zenith-v32-assets-v1", self.text)
        self.assertIn("Result branch already exists; refusing overwrite/re-publication", self.text)

    def test_validated_claim_boundary_is_preserved(self):
        for assertion in (
            "validation['status']=='COMPUTATIONAL_REFERENCE_VALIDATION_PASS'",
            "validation['overall']['comparisonCount']==192",
            "runtime['provenance']['oldDomainValuesUnchanged'] is True",
            "runtime['provenance']['newTrainingSolverSpectrumCount']==100",
            "runtime['provenance']['belowZenithSdisortTrainingSpectrumCount']==75",
            "runtime['provenance']['exactVerticalOpticalColumnTrainingSpectrumCount']==25",
            "runtime['provenance']['postResultRetuningPerformed'] is False",
            "runtime['provenance']['empiricalRealSkyValidated'] is False",
            "runtime['provenance']['humanFirstSeeingValidated'] is False",
            "runtime['provenance']['productionAuthorized'] is False",
        ):
            self.assertIn(assertion, self.text)

    def test_exact_runtime_bytes_are_copied_not_reconstructed(self):
        self.assertIn("cp \"$SOURCE/stellar-transport-v32-zenith-lut.json\"", self.text)
        self.assertIn("cp \"$SOURCE/native-stellar-zenith-v32-validation.json\"", self.text)
        self.assertIn("sha256sum generated/level-b-stellar-v32/stellar-transport-v32-zenith-lut.json", self.text)
        self.assertIn("sha256sum generated/level-b-stellar-v32/native-stellar-zenith-v32-validation.json", self.text)


if __name__ == "__main__":
    unittest.main()
