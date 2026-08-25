from __future__ import annotations

import importlib.util
import json
import math
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRANSPORT = ROOT / "review/asiv-matched-stellar-transport-v1/execution_transport_review.py"
CONTRACT = ROOT / "review/asiv-matched-stellar-transport-v1/EXECUTION_TRANSPORT_CONTRACT.review.json"


def load_transport():
    spec = importlib.util.spec_from_file_location("asiv_matched_stellar_execution_transport", TRANSPORT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def positive_test_authorization(mod):
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
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
        "families": list(mod.NON_NATIVE_FAMILIES),
        "nativeState": mod.NATIVE_STATE,
        "nativeRenderable": False,
        "sourceBindings": mod.current_transport_binding(),
        "runtimeIdentity": contract["runtimeIdentity"],
    }


def synthetic_runtime_report(mod, tmp: Path):
    uvspec = tmp / "uvspec"
    uvspec.write_text("synthetic-not-executed\n", encoding="utf-8")
    data_dir = tmp / "data"
    data_dir.mkdir()
    atmosphere = tmp / "afglus.dat"
    atmosphere.write_text(
        "120 1\n100 1\n80 1\n60 1\n40 1\n20 1\n10 1\n5 1\n2 1\n1 1\n0 1\n",
        encoding="utf-8",
    )
    return {
        "schemaVersion": 1,
        "status": "MATCHED_STELLAR_RUNTIME_IDENTITY_VERIFIED",
        "runtimeLockRawSha256": mod.EXPECTED_RUNTIME_LOCK_RAW_SHA256,
        "exactPackageSpec": mod.EXPECTED_PACKAGE_SPEC,
        "uvspecPath": str(uvspec),
        "uvspecSha256": mod.EXPECTED_UVSPEC_SHA256,
        "uvspecHelpSha256": mod.EXPECTED_UVSPEC_HELP_SHA256,
        "augmentedDataDir": str(data_dir),
        "augmentedDataTreeSha256": mod.EXPECTED_AUGMENTED_DATA_TREE_SHA256,
        "atmospherePath": str(atmosphere),
        "atmosphereSha256": mod.EXPECTED_ATMOSPHERE_SHA256,
        "wavelengthGridGitBlobSha1": mod.EXPECTED_WAVELENGTH_GRID_GIT_BLOB_SHA1,
        "scientificSolverExecuted": False,
    }


class AsivMatchedStellarTransportExecutionV1Tests(unittest.TestCase):
    def test_contract_is_hard_disabled_and_exact_case_universe(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(contract["status"], "FROZEN_REVIEW_ONLY_EXECUTION_TRANSPORT_NO_AUTHORIZATION")
        for key in (
            "scientificExecutionAuthorized",
            "solverExecutionAuthorized",
            "resultOpeningAuthorized",
            "productionActivationAuthorized",
            "pandoraHoldoutAccessAllowed",
            "starsvisibilityMutationAuthorized",
            "nativeRebuildAuthorized",
            "retryPermitted",
            "resumePermitted",
            "githubRerunPermitted",
        ):
            self.assertFalse(contract[key], key)
        self.assertEqual(contract["caseUniverse"]["trainingSpectraTotal"], 2700)
        self.assertEqual(contract["caseUniverse"]["validationAtmosphericSpectraTotal"], 768)
        self.assertEqual(contract["caseUniverse"]["validationJohnsonVComparisonsTotal"], 2304)
        self.assertEqual(contract["acceptance"]["maxAbsoluteJohnsonVExtinctionErrorMagPerFamily"], 0.025)
        self.assertEqual(contract["acceptance"]["rmsJohnsonVExtinctionErrorMagPerFamily"], 0.010)
        self.assertTrue(contract["acceptance"]["everyFamilyMustPass"])
        self.assertFalse(contract["acceptance"]["postResidualRetuningPermitted"])

    def test_bound_sources_and_shared_wavelength_grid_are_exact(self):
        mod = load_transport()
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        bindings = contract["sourceBindings"]
        self.assertEqual(mod.git_blob_sha1(mod.CANDIDATE_PATH), bindings["prefrozenRenderCandidateGitBlobSha1"])
        self.assertEqual(mod.git_blob_sha1(mod.OVERLAY_PATH), bindings["opacRuntimeOverlayGitBlobSha1"])
        self.assertEqual(mod.git_blob_sha1(mod.PROCESS_RUNNER_PATH), bindings["processGroupRunnerGitBlobSha1"])
        self.assertEqual(mod.git_blob_sha1(mod.WAVELENGTH_GRID_PATH), bindings["wavelengthGridGitBlobSha1"])
        mod.validate_wavelength_grid_binding()

    def test_parser_is_exact_0081_edir_over_mu0_and_tau(self):
        mod = load_transport()
        altitude = 30.0
        mu0 = math.sin(math.radians(altitude))
        transmission = 0.8
        stdout = "\n".join(f"{w} {mu0 * transmission:.17g}" for w in range(380, 781)) + "\n"
        parsed = mod.parse_direct_transmission(stdout, target_altitude_deg=altitude)
        self.assertEqual(parsed["wavelengthNm"], list(range(380, 781)))
        self.assertEqual(len(parsed["directOpticalDepth"]), 401)
        for value in parsed["lineOfSightDirectTransmission"]:
            self.assertAlmostEqual(value, transmission, places=14)
        for tau in parsed["directOpticalDepth"]:
            self.assertAlmostEqual(tau, -math.log(transmission), places=14)

    def test_missing_positive_authorization_refuses_before_process(self):
        mod = load_transport()
        calls = []
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            report = synthetic_runtime_report(mod, tmp)
            authorization = positive_test_authorization(mod)
            authorization["status"] = "REVIEW_ONLY_NO_AUTHORIZATION"
            with self.assertRaises(mod.ExecutionTransportRefusal):
                mod.execute_one_case(
                    authorization=authorization,
                    runtime_report=report,
                    family="opac-maritime-clean",
                    target_altitude_deg=20,
                    observer_elevation_m=500,
                    aod550=0.2,
                    process_runner=lambda *args, **kwargs: calls.append((args, kwargs)),
                )
        self.assertEqual(calls, [])

    def test_native_is_unconditionally_refused_before_process(self):
        mod = load_transport()
        calls = []
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            report = synthetic_runtime_report(mod, tmp)
            authorization = positive_test_authorization(mod)
            with self.assertRaises(mod.ExecutionTransportRefusal):
                mod.execute_one_case(
                    authorization=authorization,
                    runtime_report=report,
                    family="native-rural-ss",
                    target_altitude_deg=20,
                    observer_elevation_m=500,
                    aod550=0.2,
                    process_runner=lambda *args, **kwargs: calls.append((args, kwargs)),
                )
        self.assertEqual(calls, [])

    def test_fake_authorized_non_native_case_runs_exactly_once(self):
        mod = load_transport()
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
            tmp = Path(tmp_name)
            report = synthetic_runtime_report(mod, tmp)
            authorization = positive_test_authorization(mod)
            result = mod.execute_one_case(
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
        self.assertIn("aerosol_species_library OPAC", calls[0]["text"])
        self.assertIn("aerosol_species_file maritime_clean", calls[0]["text"])
        self.assertIn("aerosol_set_tau_at_wvl 550 0.20000000", calls[0]["text"])
        self.assertIn("rte_solver sdisort", calls[0]["text"])
        self.assertIn("sdisort nscat 1", calls[0]["text"])
        self.assertNotIn("rte_solver mystic", calls[0]["text"].lower())
        self.assertEqual(result["solverExecutionCount"], 1)
        self.assertFalse(result["retryPermitted"])
        self.assertEqual(result["family"], "opac-maritime-clean")
        self.assertEqual(len(result["spectrum"]["directOpticalDepth"]), 401)
        for tau in result["spectrum"]["directOpticalDepth"]:
            self.assertAlmostEqual(tau, -math.log(0.75), places=14)

    def test_runtime_report_drift_refuses(self):
        mod = load_transport()
        with tempfile.TemporaryDirectory() as tmp_name:
            report = synthetic_runtime_report(mod, Path(tmp_name))
            report["uvspecSha256"] = "0" * 64
            with self.assertRaises(mod.ExecutionTransportRefusal):
                mod.validate_runtime_report(report)

    def test_review_cli_has_no_execute_subcommand(self):
        source = TRANSPORT.read_text(encoding="utf-8")
        self.assertIn("REVIEW_ONLY_NO_EXECUTION_CLI", source)
        self.assertNotIn("add_parser(\"execute\")", source)
        self.assertNotIn("add_parser('execute')", source)


if __name__ == "__main__":
    unittest.main()
