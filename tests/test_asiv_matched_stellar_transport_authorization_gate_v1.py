from __future__ import annotations

import copy
import importlib.util
import json
import math
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "review/asiv-matched-stellar-transport-v1/execution_authorization_gate_review.py"
CONTRACT = ROOT / "review/asiv-matched-stellar-transport-v1/EXECUTION_TRANSPORT_CONTRACT.review.json"


def load_gate():
    spec = importlib.util.spec_from_file_location("asiv_matched_stellar_authorization_gate", GATE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def positive_strict_authorization(mod):
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    transport = mod.load_bound_transport()
    return {
        "schemaVersion": 1,
        "stageId": "asiv-matched-stellar-transport-v1-execution-authorization",
        "status": "AUTHORIZED_ONE_SHOT_SCIENTIFIC_EXECUTION",
        "scientificExecutionAuthorized": True,
        "solverExecutionAuthorized": True,
        "resultOpeningAuthorized": False,
        "productionActivationAuthorized": False,
        "pandoraHoldoutAccessAllowed": False,
        "starsvisibilityMutationAuthorized": False,
        "nativeRebuildAuthorized": False,
        "retryPermitted": False,
        "resumePermitted": False,
        "githubRerunPermitted": False,
        "families": list(transport.NON_NATIVE_FAMILIES),
        "nativeState": transport.NATIVE_STATE,
        "nativeRenderable": False,
        "sourceBindings": mod.current_authorization_binding(),
        "runtimeIdentity": copy.deepcopy(contract["runtimeIdentity"]),
        "photometricValidationAssets": copy.deepcopy(contract["photometricValidationAssets"]),
        "validationAcceptance": copy.deepcopy(contract["acceptance"]),
        "caseUniverse": copy.deepcopy(contract["caseUniverse"]),
    }


def synthetic_runtime_report(transport, tmp: Path):
    uvspec = tmp / "uvspec"
    uvspec.write_text("synthetic-not-executed\n", encoding="utf-8")
    data_dir = tmp / "data"
    data_dir.mkdir()
    atmosphere = tmp / "afglus.dat"
    atmosphere.write_text("120 1\n0 1\n", encoding="utf-8")
    return {
        "schemaVersion": 1,
        "status": "MATCHED_STELLAR_RUNTIME_IDENTITY_VERIFIED",
        "runtimeLockRawSha256": transport.EXPECTED_RUNTIME_LOCK_RAW_SHA256,
        "exactPackageSpec": transport.EXPECTED_PACKAGE_SPEC,
        "uvspecPath": str(uvspec),
        "uvspecSha256": transport.EXPECTED_UVSPEC_SHA256,
        "uvspecHelpSha256": transport.EXPECTED_UVSPEC_HELP_SHA256,
        "augmentedDataDir": str(data_dir),
        "augmentedDataTreeSha256": transport.EXPECTED_AUGMENTED_DATA_TREE_SHA256,
        "atmospherePath": str(atmosphere),
        "atmosphereSha256": transport.EXPECTED_ATMOSPHERE_SHA256,
        "wavelengthGridGitBlobSha1": transport.EXPECTED_WAVELENGTH_GRID_GIT_BLOB_SHA1,
        "scientificSolverExecuted": False,
    }


class AsivMatchedStellarAuthorizationGateV1Tests(unittest.TestCase):
    def test_contract_binds_current_gate_and_validator(self):
        mod = load_gate()
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(
            mod.git_blob_sha1(mod.VALIDATOR_PATH),
            contract["sourceBindings"]["validationAssemblerGitBlobSha1"],
        )
        gate_blob = mod.git_blob_sha1(Path(mod.__file__).resolve())
        self.assertEqual(gate_blob, contract["sourceBindings"]["strictAuthorizationGateGitBlobSha1"])
        self.assertEqual(gate_blob, contract["authorizationGate"]["gitBlobSha1"])
        self.assertTrue(contract["authorizationGate"]["requiredForFutureExecution"])
        self.assertFalse(contract["authorizationGate"]["reviewCliExecutesSolver"])
        req = contract["futureAuthorizationRequirements"]
        self.assertTrue(req["authorizationMustUseStrictGate"])
        self.assertTrue(req["authorizationMustBindExactGateBytes"])
        self.assertTrue(req["authorizationMustBindExactValidatorBytes"])
        self.assertTrue(req["authorizationMustBindExactPhotometricAssets"])
        self.assertTrue(req["authorizationMustBindExactAcceptanceGates"])
        self.assertTrue(req["authorizationMustBindExactCaseUniverse"])

    def test_positive_strict_authorization_is_structurally_accepted(self):
        mod = load_gate()
        authorization = positive_strict_authorization(mod)
        mod.validate_strict_authorization(authorization)

    def test_validator_binding_drift_is_refused(self):
        mod = load_gate()
        authorization = positive_strict_authorization(mod)
        authorization["sourceBindings"]["validationAssemblerGitBlobSha1"] = "0" * 40
        with self.assertRaises(mod.AuthorizationGateRefusal):
            mod.validate_strict_authorization(authorization)

    def test_photometric_asset_drift_is_refused(self):
        mod = load_gate()
        authorization = positive_strict_authorization(mod)
        authorization["photometricValidationAssets"]["picklesSedBundleSha256"] = "0" * 64
        with self.assertRaises(mod.AuthorizationGateRefusal):
            mod.validate_strict_authorization(authorization)

    def test_acceptance_gate_drift_is_refused(self):
        mod = load_gate()
        authorization = positive_strict_authorization(mod)
        authorization["validationAcceptance"]["maxAbsoluteJohnsonVExtinctionErrorMagPerFamily"] = 0.026
        with self.assertRaises(mod.AuthorizationGateRefusal):
            mod.validate_strict_authorization(authorization)

    def test_case_universe_drift_is_refused(self):
        mod = load_gate()
        authorization = positive_strict_authorization(mod)
        authorization["caseUniverse"]["validationJohnsonVComparisonsTotal"] = 2303
        with self.assertRaises(mod.AuthorizationGateRefusal):
            mod.validate_strict_authorization(authorization)

    def test_strict_refusal_happens_before_fake_process_runner(self):
        mod = load_gate()
        transport = mod.load_bound_transport()
        calls = []
        with tempfile.TemporaryDirectory() as tmp_name:
            report = synthetic_runtime_report(transport, Path(tmp_name))
            authorization = positive_strict_authorization(mod)
            authorization["photometricValidationAssets"]["johnsonVRawAssetSha256"] = "0" * 64
            with self.assertRaises(mod.AuthorizationGateRefusal):
                mod.execute_one_case_strict(
                    authorization=authorization,
                    runtime_report=report,
                    family="opac-maritime-clean",
                    target_altitude_deg=20,
                    observer_elevation_m=500,
                    aod550=0.2,
                    process_runner=lambda *args, **kwargs: calls.append((args, kwargs)),
                )
        self.assertEqual(calls, [])

    def test_valid_strict_authorization_delegates_exactly_one_fake_case(self):
        mod = load_gate()
        transport = mod.load_bound_transport()
        calls = []
        altitude = 20.0
        mu0 = math.sin(math.radians(altitude))
        stdout = "\n".join(f"{w} {mu0 * 0.75:.17g}" for w in range(380, 781)) + "\n"

        def fake_runner(command, text, cwd, timeout):
            calls.append({"command": command, "text": text, "cwd": cwd, "timeout": timeout})
            return {
                "exitCode": 0,
                "timedOut": False,
                "stdout": stdout,
                "stderr": "",
                "processGroupIsolated": True,
                "processGroupTerminationAttempted": False,
                "sigkillFallbackUsed": False,
            }

        with tempfile.TemporaryDirectory() as tmp_name:
            report = synthetic_runtime_report(transport, Path(tmp_name))
            authorization = positive_strict_authorization(mod)
            result = mod.execute_one_case_strict(
                authorization=authorization,
                runtime_report=report,
                family="opac-maritime-clean",
                target_altitude_deg=altitude,
                observer_elevation_m=500,
                aod550=0.2,
                process_runner=fake_runner,
            )
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["timeout"], 180)
        self.assertIn("aerosol_species_file maritime_clean", calls[0]["text"])
        self.assertEqual(result["status"], "MATCHED_STELLAR_CASE_EXECUTED_ONCE")
        self.assertEqual(result["solverExecutionCount"], 1)
        self.assertFalse(result["retryPermitted"])

    def test_gate_review_cli_has_no_execute_subcommand(self):
        source = GATE.read_text(encoding="utf-8")
        self.assertIn("REVIEW_ONLY_STRICT_AUTHORIZATION_GATE_NO_EXECUTION_CLI", source)
        self.assertNotIn("add_parser(\"execute\")", source)
        self.assertNotIn("add_parser('execute')", source)


if __name__ == "__main__":
    unittest.main()
