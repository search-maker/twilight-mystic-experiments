from __future__ import annotations

import copy
import importlib.util
import json
import math
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BATCH_PATH = ROOT / "review/asiv-matched-stellar-transport-v1/batch_orchestration_review.py"
BATCH_CONTRACT = ROOT / "review/asiv-matched-stellar-transport-v1/BATCH_ORCHESTRATION_CONTRACT.review.json"
EXECUTION_CONTRACT = ROOT / "review/asiv-matched-stellar-transport-v1/EXECUTION_TRANSPORT_CONTRACT.review.json"


def load_batch():
    spec = importlib.util.spec_from_file_location("asiv_matched_stellar_batch_orchestration", BATCH_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def strict_authorization(mod):
    gate = mod.load_strict_gate()
    contract = json.loads(EXECUTION_CONTRACT.read_text(encoding="utf-8"))
    transport = gate.load_bound_transport()
    authorization = {
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
        "sourceBindings": gate.current_authorization_binding(),
        "runtimeIdentity": copy.deepcopy(contract["runtimeIdentity"]),
        "photometricValidationAssets": copy.deepcopy(contract["photometricValidationAssets"]),
        "validationAcceptance": copy.deepcopy(contract["acceptance"]),
        "caseUniverse": copy.deepcopy(contract["caseUniverse"]),
    }
    return authorization


def batch_authorization(mod):
    authorization = strict_authorization(mod)
    authorization.update({
        "batchExecutionAuthorized": True,
        "partialShardInterpretationPermitted": False,
        "partialUniverseValidationPermitted": False,
        "batchBindings": mod.current_batch_binding(),
    })
    return authorization


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


class AsivMatchedStellarBatchOrchestrationV1Tests(unittest.TestCase):
    def test_exact_99_shard_manifest_and_canonical_hash(self):
        mod = load_batch()
        manifest = mod.build_batch_manifest()
        self.assertEqual(manifest["totalCaseCount"], 3468)
        self.assertEqual(manifest["shardCount"], 99)
        self.assertEqual(manifest["roles"]["training"], {"caseCount": 2700, "shardCount": 75, "casesPerShard": 36})
        self.assertEqual(manifest["roles"]["validation"], {"caseCount": 768, "shardCount": 24, "casesPerShard": 32})
        self.assertEqual(mod.canonical_sha256(manifest), mod.EXPECTED_BATCH_MANIFEST_CANONICAL_SHA256)
        self.assertEqual(mod.EXPECTED_BATCH_MANIFEST_CANONICAL_SHA256, "1756c756e1e865c729a3d93a1084c6081a5eefa6a05f4e874bdaed84e8359663")
        self.assertEqual(manifest["shards"][0]["shardId"], "training-000")
        self.assertEqual(manifest["shards"][74]["shardId"], "training-074")
        self.assertEqual(manifest["shards"][75]["shardId"], "validation-000")
        self.assertEqual(manifest["shards"][-1]["shardId"], "validation-023")
        flat = [case for shard in manifest["shards"] for case in shard["caseIds"]]
        self.assertEqual(len(flat), 3468)
        self.assertEqual(len(set(flat)), 3468)
        self.assertTrue(all(shard["caseCount"] == 36 for shard in manifest["shards"][:75]))
        self.assertTrue(all(shard["caseCount"] == 32 for shard in manifest["shards"][75:]))
        self.assertTrue(all(shard["role"] == "training" for shard in manifest["shards"][:75]))
        self.assertTrue(all(shard["role"] == "validation" for shard in manifest["shards"][75:]))

    def test_contract_binds_current_orchestrator_and_forbids_authorization(self):
        mod = load_batch()
        contract = json.loads(BATCH_CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(contract["sourceBindings"]["batchOrchestrationGitBlobSha1"], mod.git_blob_sha1(BATCH_PATH))
        self.assertEqual(contract["batchManifest"]["canonicalSha256"], mod.EXPECTED_BATCH_MANIFEST_CANONICAL_SHA256)
        for key in (
            "scientificExecutionAuthorized", "solverExecutionAuthorized", "workflowDispatchAuthorized",
            "resultOpeningAuthorized", "productionActivationAuthorized", "pandoraHoldoutAccessAllowed",
            "starsvisibilityMutationAuthorized", "nativeRebuildAuthorized", "retryPermitted",
            "resumePermitted", "githubRerunPermitted", "partialShardInterpretationPermitted",
            "partialUniverseValidationPermitted",
        ):
            self.assertFalse(contract[key], key)

    def test_strict_authorization_alone_is_insufficient_for_batch(self):
        mod = load_batch()
        authorization = strict_authorization(mod)
        with self.assertRaises(mod.BatchOrchestrationRefusal):
            mod.validate_batch_authorization(authorization)

    def test_batch_binding_drift_is_refused(self):
        mod = load_batch()
        authorization = batch_authorization(mod)
        authorization["batchBindings"]["batchManifestCanonicalSha256"] = "0" * 64
        with self.assertRaises(mod.BatchOrchestrationRefusal):
            mod.validate_batch_authorization(authorization)

    def test_allow_execution_false_refuses_before_fake_runner(self):
        mod = load_batch()
        gate = mod.load_strict_gate()
        transport = gate.load_bound_transport()
        calls = []
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            report = synthetic_runtime_report(transport, tmp)
            with self.assertRaises(mod.BatchOrchestrationRefusal):
                mod.execute_shard_strict(
                    shard_id="validation-000",
                    authorization=batch_authorization(mod),
                    runtime_report=report,
                    output_root=tmp / "out",
                    process_runner=lambda *args, **kwargs: calls.append((args, kwargs)),
                    allow_execution=False,
                )
        self.assertEqual(calls, [])

    def test_valid_fake_validation_shard_executes_exactly_32_fake_cases(self):
        mod = load_batch()
        gate = mod.load_strict_gate()
        transport = gate.load_bound_transport()
        calls = []

        def fake_runner(command, text, cwd, timeout):
            altitude = None
            for line in text.splitlines():
                if line.startswith("sza "):
                    altitude = 90.0 - float(line.split()[1])
                    break
            assert altitude is not None
            mu0 = math.sin(math.radians(altitude))
            stdout = "\n".join(f"{w} {mu0 * 0.75:.17g}" for w in range(380, 781)) + "\n"
            calls.append((command, timeout, text))
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
            report = synthetic_runtime_report(transport, tmp)
            output = tmp / "validation-000"
            result = mod.execute_shard_strict(
                shard_id="validation-000",
                authorization=batch_authorization(mod),
                runtime_report=report,
                output_root=output,
                process_runner=fake_runner,
                allow_execution=True,
            )
            self.assertTrue(output.is_dir())
            self.assertFalse((tmp / "validation-000.partial").exists())
            self.assertEqual(result["status"], "COMPLETE_SHARD_EXECUTED_ONCE")
            self.assertEqual(result["role"], "validation")
            self.assertEqual(result["caseCount"], 32)
            self.assertEqual(len(list(output.glob("validation__*.json"))), 32)
            summary = json.loads((output / "shard-result.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["caseIds"], mod.build_batch_manifest()["shards"][75]["caseIds"])
        self.assertEqual(len(calls), 32)
        self.assertTrue(all(timeout == 180 for _, timeout, _ in calls))

    def test_partial_shard_universe_is_refused_before_case_payload_opening(self):
        mod = load_batch()
        manifest = mod.build_batch_manifest()
        first = manifest["shards"][0]
        with tempfile.TemporaryDirectory() as tmp_name:
            root = Path(tmp_name) / first["shardId"]
            root.mkdir()
            (root / "shard-result.json").write_text(json.dumps({
                "schemaVersion": 1,
                "stageId": "asiv-matched-stellar-transport-v1-complete-shard",
                "status": "COMPLETE_SHARD_EXECUTED_ONCE",
                "shardId": first["shardId"],
                "role": first["role"],
                "caseCount": first["caseCount"],
                "caseIds": first["caseIds"],
                "batchManifestCanonicalSha256": mod.EXPECTED_BATCH_MANIFEST_CANONICAL_SHA256,
                "retryPermitted": False,
                "resumePermitted": False,
                "githubRerunPermitted": False,
                "partialShardInterpretationPermitted": False,
            }, sort_keys=True) + "\n", encoding="utf-8")
            with self.assertRaises(mod.BatchOrchestrationRefusal) as ctx:
                mod.collect_complete_case_payloads([root])
            self.assertIn("partial shard universe forbidden", str(ctx.exception))

    def test_review_module_has_no_execution_cli_or_subprocess_surface(self):
        source = BATCH_PATH.read_text(encoding="utf-8")
        self.assertNotIn("import subprocess", source)
        self.assertNotIn("subprocess.", source)
        self.assertNotIn("Popen(", source)
        self.assertNotIn("add_parser(\"execute\")", source)
        self.assertIn("REVIEW_ONLY_BATCH_ORCHESTRATION_NO_EXECUTION_CLI", source)


if __name__ == "__main__":
    unittest.main()
