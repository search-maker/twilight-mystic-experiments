from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = ROOT / "experiments/mystic-batch-v1"


def module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


package = module("confirmation_package", PACKAGE_DIR / "cross_geometry_confirmation_package.py")
plan_module = module("confirmation_plan", PACKAGE_DIR / "cross_geometry_confirmation_execution_plan.py")
analysis_module = module("confirmation_analysis", PACKAGE_DIR / "cross_geometry_confirmation_analysis_driver.py")


def dump(value):
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def method_stats(mean: float, rsem: float = 0.05):
    return {
        "blockCount": 6,
        "valuesCdM2": [mean] * 6,
        "meanCdM2": mean,
        "sampleStandardDeviationCdM2": mean * rsem,
        "coefficientOfVariation": rsem,
        "relativeStandardErrorOfMean": rsem,
        "reportedNodeStdAvailable": False,
        "photopicWeightedReportedRelativeStd": None,
        "nodeMeanRadiance": [mean] * 15,
    }


def fixture():
    cases = []
    for block in range(1, 5):
        cases.append({
            "caseId": f"cgc-g01-alis-r{block}",
            "groupId": "g01-reference-bridge",
            "method": "alis",
            "ordinal": block,
            "seed": 80550 + block,
            "block": block,
            "photonHistories": 20_000_000,
            "purpose": "selected-reference-confirmation",
            "alisSpectralImportanceSamplingNm": 550.0,
        })
    source_result = {
        "groupId": "g01-reference-bridge",
        "classification": "REFERENCE_SELECTED_NEEDS_CONFIRMATION",
        "vroomStatistics": method_stats(1.0),
        "candidateAlisReferences": [
            {"referenceNm": 550.0, "alisStatistics": method_stats(1.0)}
        ],
        "selectedAlisReferenceNm": 550.0,
    }
    analysis = {
        "schemaVersion": 1,
        "stageId": "cross-geometry-final-convergence-v1",
        "status": "FINAL_CONVERGENCE_ANALYZED",
        "screeningOnly": True,
        "successDoesNotAuthorizeProduction": True,
        "heldOutConfirmationRequired": True,
        "heldOutConfirmationCaseCount": 4,
        "heldOutConfirmationConfiguredMcPhotonsSum": 80_000_000,
        "technicalDiagnosisRequiredGeometryIds": [],
        "geometryResults": [source_result],
    }
    proposal = {
        "schemaVersion": 1,
        "stageId": "cross-geometry-selected-reference-confirmation-v1",
        "mode": "scientific-proposal",
        "proposalOnly": True,
        "scientificExecution": False,
        "successDoesNotAuthorizeProduction": True,
        "adapterId": "mystic-cross-geometry-v1",
        "sourceFinalConvergenceStageId": "cross-geometry-final-convergence-v1",
        "selectedGeometryIds": ["g01-reference-bridge"],
        "geometries": [{"geometryId": "g01-reference-bridge", "sunDepressionDeg": 12.0, "targetAltitudeDeg": 10.0, "relativeAzimuthDeg": 120.0, "observerElevationM": 0.0, "aod550": 0.15}],
        "frozenInputs": {
            "albedo": 0.15,
            "alisSpectralImportanceSamplingNm": 405.0,
            "dataPaths": {
                "atmosphere": {"path": "atmmod/afglus.dat", "root": "libRadtranData"},
                "solarFlux": {"path": "solar_flux/atlas_plus_modtran", "root": "libRadtranData"},
                "wavelengthGrid": {"path": "experiments/reference-vroom-v1/wavelength-grid.dat", "root": "repository"},
            },
            "diagnosticNodesNm": [470,480,490,500,510,520,530,540,560,580,590,600,610,640,660],
            "mcSpherical": "1D",
            "molecularAbsorption": "crs",
            "wavelengthDomainNm": [380,780],
        },
        "runtime": {
            "uvspecSha256": "a" * 64,
            "uvspecHelpSha256": "b" * 64,
            "libRadtranDataTreeSha256": "c" * 64,
            "atmosphereSha256": "d" * 64,
            "runtimeLockRawSha256": "e" * 64,
        },
        "cases": cases,
        "limits": {"maximumCases": 4, "maximumConfiguredMcPhotonsSum": 80_000_000, "maximumParallel": 16, "perCaseTimeoutSeconds": 1800},
        "analysisPlan": {
            "selectionDataExcludedFromConfirmationDecision": True,
            "confirmationBlocksPerRequestedMethod": 4,
            "targetRelativeStandardErrorOfMean": 0.08,
            "maximumPhotonHistoriesPerBlock": 400_000_000,
            "noOpenEndedAdditionalBlocks": True,
        },
    }
    readiness = {
        "schemaVersion": 1,
        "status": "COMPUTATIONAL_REFERENCE_SCREENING_IN_PROGRESS",
        "productionModelReady": False,
        "observationValidationRequired": True,
    }
    run = {
        "id": 30869495039,
        "event": "workflow_dispatch",
        "run_attempt": 1,
        "status": "completed",
        "conclusion": "success",
        "display_title": "Cross geometry final convergence v1 | key=cross-geometry-final-convergence-v1:screening:4 | auth=7e630b8f46259ddf6a0cfdf5e381872c0182d0ba | ordinal=4",
    }
    pilot = {"schemaVersion": 1, "stageId": "cross-geometry-pilot-v1", "proposalOnly": True, "geometries": proposal["geometries"]}
    return analysis, proposal, readiness, run, pilot


class ConfirmationTests(unittest.TestCase):
    def write_fixture(self, root: Path):
        analysis, proposal, readiness, run, pilot = fixture()
        paths = {}
        for name, value in (("analysis", analysis), ("proposal", proposal), ("readiness", readiness), ("run", run), ("pilot", pilot)):
            path = root / f"{name}.json"
            path.write_text(dump(value))
            paths[name] = path
        return paths

    def test_promote_exact_dynamic_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_fixture(Path(tmp))
            promoted = package.promote(paths["analysis"], paths["proposal"], paths["readiness"], paths["run"], 30869495039)
            self.assertEqual(promoted["batchId"], package.BATCH_ID)
            self.assertEqual(len(promoted["cases"]), 4)
            self.assertTrue(promoted["scientificDiagnostic"])
            self.assertEqual(promoted["sourceRunId"], 30869495039)

    def test_promote_rejects_missing_held_out_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_fixture(Path(tmp))
            proposal = json.loads(paths["proposal"].read_text())
            proposal["cases"].pop()
            proposal["limits"]["maximumCases"] = 3
            proposal["limits"]["maximumConfiguredMcPhotonsSum"] = 60_000_000
            paths["proposal"].write_text(dump(proposal))
            with self.assertRaises(package.ConfirmationPackageError):
                package.promote(paths["analysis"], paths["proposal"], paths["readiness"], paths["run"], 30869495039)

    def test_dynamic_plan_uses_promoted_hash_and_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self.write_fixture(root)
            promoted = package.promote(paths["analysis"], paths["proposal"], paths["readiness"], paths["run"], 30869495039)
            manifest = root / "manifest.json"
            manifest.write_text(package.dump(promoted))
            guard = root / "guard.json"
            guard.write_text(dump({
                "status": "AUTHORIZED",
                "stageId": package.STAGE_ID,
                "batchId": package.BATCH_ID,
                "promotedManifestRawSha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
                "executionAdapterRawSha256": "a" * 64,
                "runtimeLockRawSha256": "b" * 64,
                "executionWorkflowRawSha256": "c" * 64,
                "authorizationRef": "d" * 40,
                "authorizationOrdinal": 5,
                "executionKey": "cross-geometry-selected-reference-confirmation-v1:screening:5",
                "sourceRunId": 30869495039,
                "sourceFinalAnalysisRawSha256": promoted["sourceFinalAnalysisRawSha256"],
                "sourceProposalRawSha256": promoted["sourceProposalRawSha256"],
                "sourceReadinessRawSha256": promoted["sourceReadinessRawSha256"],
            }))
            plan = plan_module.build_plan(manifest, guard)
            self.assertEqual(plan["caseCount"], 4)
            self.assertEqual(plan["configuredMcPhotonsSum"], 80_000_000)
            self.assertEqual(plan["maximumParallel"], 16)

    def test_held_out_analysis_passes_without_using_selected_alis_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self.write_fixture(root)
            promoted = package.promote(paths["analysis"], paths["proposal"], paths["readiness"], paths["run"], 30869495039)
            manifest = root / "manifest.json"
            manifest.write_text(package.dump(promoted))
            cases_root = root / "cases"
            cases_root.mkdir()
            adapter_hash = "f" * 64
            for case in promoted["cases"]:
                case_dir = cases_root / case["caseId"]
                case_dir.mkdir()
                record = {
                    "schemaVersion": 1,
                    "stageId": "mystic-batch-v1",
                    "status": "COMPLETED",
                    "scientificDiagnostic": True,
                    "successDoesNotAuthorizeProduction": True,
                    "batchId": promoted["batchId"],
                    "caseId": case["caseId"],
                    "ordinal": case["ordinal"],
                    "seed": case["seed"],
                    "photonHistories": case["photonHistories"],
                    "manifestRawSha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
                    "adapterRawSha256": adapter_hash,
                    "syntaxCheckCount": 1,
                    "solverExecutionCount": 1,
                    "syntax": {"exitCode": 0, "timedOut": False, "elapsedSeconds": 1.0},
                    "solver": {"exitCode": 0, "timedOut": False, "elapsedSeconds": 2.0},
                    "selectedNodeRadiance": [1.0] * 15,
                    "selectedPhotopicContributionCdM2": 1.0,
                }
                (case_dir / "case-result.json").write_text(dump(record))
            summary = root / "summary.json"
            summary.write_text(dump({
                "stageId": "mystic-batch-v1",
                "classification": "BATCH_NUMERICALLY_COMPLETE",
                "caseCountCompleted": 4,
                "caseCountFailed": 0,
                "configuredMcPhotonsSum": 80_000_000,
                "completedConfiguredMcPhotonsSum": 80_000_000,
                "scientificAdapterRawSha256": adapter_hash,
            }))
            audit = root / "audit.json"
            audit.write_text(dump({"stageId": "mystic-batch-v1", "status": "PASSED", "caseResultCount": 4}))
            output = root / "out"
            result = analysis_module.analyze(
                manifest,
                paths["analysis"],
                paths["pilot"],
                cases_root,
                summary,
                audit,
                PACKAGE_DIR / "cross_geometry_convergence_v2.py",
                output,
            )
            self.assertTrue(result["computationalReferenceScreeningComplete"])
            self.assertEqual(result["geometryResults"][0]["classification"], "HELD_OUT_CONFIRMATION_PASSED")
            self.assertEqual(result["geometryResults"][0]["methodOrigins"]["alis"], "held-out-confirmation")
            dataset = json.loads((output / "audited-reference-dataset.json").read_text())
            self.assertEqual(len(dataset["records"]), 1)

    def test_authorization_is_disabled_by_default(self):
        active = json.loads((PACKAGE_DIR / "authorization.cross-geometry-confirmation.json").read_text())
        template = json.loads((PACKAGE_DIR / "authorization.cross-geometry-confirmation-execution-template.json").read_text())
        self.assertEqual(active, template)
        self.assertFalse(active["authorized"])
        self.assertEqual(active["authorizationOrdinal"], 0)


if __name__ == "__main__":
    unittest.main()
