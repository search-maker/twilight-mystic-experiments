from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / ".github/workflows/native-stellar-zenith-v32-one-shot.yml"
RECOVERY = ROOT / ".github/workflows/native-stellar-zenith-v32-presolver-recovery1.yml"


def extract_science_invocation(text: str) -> str:
    start_marker = 'python "$STAGE_DIR/run_native_stellar_zenith_v32.py"'
    end_marker = '--output-dir execution-output'
    start = text.index(start_marker)
    end = text.index(end_marker, start) + len(end_marker)
    return text[start:end]


class NativeStellarZenithV32PresolverRecovery1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = ORIGINAL.read_text(encoding="utf-8")
        cls.recovery = RECOVERY.read_text(encoding="utf-8")

    def test_recovery_is_bound_to_immutable_presolver_failure(self):
        self.assertIn("PRIOR_RUN_ID: '33044161800'", self.recovery)
        self.assertIn("PRIOR_DISPATCH_SHA: c599e38f20e873fd85a8a6aca945482d40d66adb", self.recovery)
        self.assertIn("'recoveryOfRunId':33044161800", self.recovery)
        self.assertIn("'recoveryOfDispatchSha':'c599e38f20e873fd85a8a6aca945482d40d66adb'", self.recovery)
        self.assertIn("'priorFailureClass':'PRE_SOLVER_MICROMAMBA_JSON_PACKAGE_IDENTITY_PARSER_FAILURE'", self.recovery)
        self.assertIn("'priorSolverInvocationCount':0", self.recovery)
        self.assertIn("'priorProtectedHoldoutOpened':False", self.recovery)
        self.assertIn("'soleRecoveryChange':'PLAIN_TEXT_MICROMAMBA_PACKAGE_IDENTITY_PARSE'", self.recovery)
        self.assertIn("'scientificInputsChanged':False", self.recovery)
        self.assertIn("'acceptanceThresholdsChanged':False", self.recovery)

    def test_recovery_has_distinct_one_file_direct_child_dispatch(self):
        self.assertIn("dispatch/native-stellar-zenith-v32-presolver-recovery1", self.recovery)
        self.assertIn("review/native-stellar-zenith-v3/v32-presolver-recovery1-dispatch.json", self.recovery)
        self.assertIn('test "${#PARENTS[@]}" = 1', self.recovery)
        self.assertIn('test "$PARENT" = "$(git rev-parse origin/main)"', self.recovery)
        self.assertIn('test "${#CHANGED[@]}" = 1', self.recovery)
        self.assertIn('test "${CHANGED[0]}" = "$DISPATCH_PATH"', self.recovery)
        self.assertIn('test "$GITHUB_RUN_ATTEMPT" = 1', self.recovery)

    def test_only_package_identity_parser_strategy_is_recovered(self):
        self.assertIn("['micromamba','list','--json']", self.original)
        self.assertNotIn("['micromamba','list','--json']", self.recovery)
        self.assertIn("['micromamba','list','rubin-libradtran']", self.recovery)
        self.assertIn("if len(p)>=3 and p[0]=='rubin-libradtran'", self.recovery)
        self.assertIn("if len(rows)!=1:", self.recovery)
        self.assertIn("print('='.join(rows[0]))", self.recovery)
        self.assertIn("test \"$PACKAGE_SPEC\" = 'rubin-libradtran=2.0.6=py312pl5321he9373c2_1'", self.recovery)

    def test_scientific_invocation_is_identical_to_original(self):
        self.assertEqual(extract_science_invocation(self.original), extract_science_invocation(self.recovery))

    def test_frozen_science_counts_and_gates_are_unchanged(self):
        frozen_fragments = (
            "'trainingSpectrumCount':100",
            "'exactVerticalTrainingSpectrumCount':25",
            "'belowZenithSdisortTrainingSpectrumCount':75",
            "'protectedHoldoutSpectrumCount':64",
            "'totalSolverInvocationCount':164",
            "'freshJohnsonVComparisonCount':192",
            "'maxAbsDeltaAvMagLimit':0.025",
            "'rmsDeltaAvMagLimit':0.010",
            "'positiveEpsilonSubstitutionAuthorized':False",
            "'githubRerunPermitted':False",
            "'solverRetryPermitted':False",
            "'solverResumePermitted':False",
            "'postResultThresholdRelaxationAuthorized':False",
            "'postResultRetuningAuthorized':False",
            "'productionAuthorized':False",
        )
        for fragment in frozen_fragments:
            self.assertIn(fragment, self.original)
            self.assertIn(fragment, self.recovery)

    def test_final_scientific_gate_is_preserved(self):
        critical = (
            "if v.get('status')!='COMPUTATIONAL_REFERENCE_VALIDATION_PASS'",
            "if v.get('newTrainingSolverSpectrumCount')!=100",
            "if v.get('exactVerticalTrainingSpectrumCount')!=25",
            "if v.get('belowZenithSdisortTrainingSpectrumCount')!=75",
            "if v.get('freshValidationAtmosphericSpectrumCount')!=64 or v.get('protectedHoldoutSdisortSpectrumCount')!=64",
            "if v.get('johnsonVComparisonCount')!=192",
            "if v.get('scientificSolverExecuted') is not True or v.get('solverInvocationCount')!=164",
            "if v.get('overall',{}).get('maxAbsDeltaAvMagLimit')!=0.025",
            "if v.get('overall',{}).get('rmsDeltaAvMagLimit')!=0.010",
            "if v.get('overall',{}).get('passed') is not True",
            "if not all(row.get('passed') is True for row in v.get('byValidationAltitudeDeg',{}).values())",
            "if runtime.get('directOpticalDepth',[])[:675] != json.loads(Path('execution-inputs/stellar-transport-v2-lut.json').read_text())['directOpticalDepth']",
            "if prov.get('productionAuthorized') is not False",
        )
        for fragment in critical:
            self.assertIn(fragment, self.original)
            self.assertIn(fragment, self.recovery)

    def test_fail_evidence_is_uploaded_before_final_gate(self):
        upload_index = self.recovery.index("Preserve complete recovery execution evidence before final gate")
        gate_index = self.recovery.index("Require frozen protected-holdout PASS without relaxation")
        self.assertLess(upload_index, gate_index)
        self.assertIn("if: always()", self.recovery[upload_index:gate_index])


if __name__ == "__main__":
    unittest.main()
