from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "tier2", ROOT / "experiments/tier2-disabled-readiness-v1/package.py"
)
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def design():
    geometries = []
    cases = []
    training = []
    holdout = []
    tier_summaries = []
    for index in range(1, 97):
        gid = f"train-{index:04d}"
        tier = "tier-1-provisional" if index <= 48 else "tier-2-completion"
        role = "internal-holdout" if index % 5 == 0 else "surrogate-training"
        (holdout if role == "internal-holdout" else training).append(gid)
        value_index = index
        inverse = 0.0
        factor = 0.5
        while value_index:
            value_index, digit = divmod(value_index, 2)
            inverse += digit * factor
            factor *= 0.5
        sun = round(2.0 + 16.0 * inverse, 6)
        photons = (
            20_000_000
            if sun <= 8.0
            else 50_000_000
            if sun <= 12.0
            else 100_000_000
            if sun <= 15.0
            else 200_000_000
        )
        importance = (500.0, 550.0, 600.0)[index % 3]
        geometries.append(
            {
                "geometryId": gid,
                "executionTierId": tier,
                "sunDepressionDeg": sun,
                "photonHistoriesPerBlock": photons,
                "alisSpectralImportanceSamplingNm": importance,
            }
        )
        for block in (1, 2):
            ordinal = len(cases) + 1
            cases.append(
                {
                    "ordinal": ordinal,
                    "caseId": f"{gid}-alis-b{block}",
                    "groupId": gid,
                    "method": "alis",
                    "block": block,
                    "seed": 910_000 + ordinal,
                    "photonHistories": photons,
                    "alisSpectralImportanceSamplingNm": importance,
                    "role": role,
                    "executionTierId": tier,
                }
            )
    tier1_cases = [
        case for case in cases if case["executionTierId"] == "tier-1-provisional"
    ]
    tier2_cases = [
        case for case in cases if case["executionTierId"] == "tier-2-completion"
    ]
    assert sum(case["photonHistories"] for case in tier2_cases) == 7_320_000_000
    tier_summaries.append(
        {
            "tierId": "tier-1-provisional",
            "geometryCount": 48,
            "caseCount": 96,
            "configuredMcPhotonsSum": sum(
                case["photonHistories"] for case in tier1_cases
            ),
            "scientificExecution": False,
            "purpose": "early-surrogate-and-holdout-error-map",
            "geometryIds": [g["geometryId"] for g in geometries[:48]],
            "caseIds": [c["caseId"] for c in tier1_cases],
        }
    )
    tier_summaries.append(
        {
            "tierId": "tier-2-completion",
            "geometryCount": 48,
            "caseCount": 96,
            "configuredMcPhotonsSum": 7_320_000_000,
            "scientificExecution": False,
            "purpose": "complete-predeclared-space-filling-design",
            "geometryIds": [g["geometryId"] for g in geometries[48:]],
            "caseIds": [c["caseId"] for c in tier2_cases],
        }
    )
    return {
        "schemaVersion": 1,
        "stageId": "twilight-surrogate-training-design-v1",
        "proposalOnly": True,
        "scientificExecution": False,
        "successDoesNotAuthorizeProduction": True,
        "observationValidationRequired": True,
        "geometryCount": 96,
        "caseCount": 192,
        "blocksPerGeometry": 2,
        "sourceSpecBinding": "a" * 64,
        "parameterRanges": {"sunDepressionDeg": [2.0, 18.0]},
        "photonSchedule": [],
        "importanceSamplingPolicy": {"purpose": "variance reduction only"},
        "executionTiers": tier_summaries,
        "trainingGeometryIds": training,
        "internalHoldoutGeometryIds": holdout,
        "geometries": geometries,
        "cases": cases,
    }


def runtime():
    return {
        "schemaVersion": 1,
        "stageId": "mystic-runtime-lock-v1",
        "solver": "uvspec",
        "libRadtranVersion": "2.0.6",
        "scientificSolverExecuted": False,
        "syntaxCheckExecuted": False,
        "hashes": {
            "uvspecSha256": "1" * 64,
            "uvspecHelpSha256": "2" * 64,
            "libRadtranDataTreeSha256": "3" * 64,
            "atmosphereSha256": "4" * 64,
            "runtimeLockRawSha256": "5" * 64,
        },
    }


def fake_results(package):
    rows = []
    for case in package["cases"]:
        rows.append(
            {
                "caseId": case["caseId"],
                "seed": case["seed"],
                "role": case["role"],
                "photonHistories": case["photonHistories"],
                "alisSpectralImportanceSamplingNm": case[
                    "alisSpectralImportanceSamplingNm"
                ],
                "status": "COMPLETED",
                "syntaxCheckCount": 1,
                "solverExecutionCount": 1,
                "syntax": {"exitCode": 0, "timedOut": False},
                "solver": {"exitCode": 0, "timedOut": False},
                "valueCdM2": 1.0 if case["block"] == 1 else 1.01,
                "artifactSha256": "6" * 64,
                "inputSha256": "7" * 64,
                "outputSha256": "8" * 64,
                "runtimeSha256": "9" * 64,
            }
        )
    return rows


class Tier2Tests(unittest.TestCase):
    def test_exact_frozen_package_and_determinism(self):
        package = m.regenerate(design(), runtime())
        self.assertEqual(package["geometryCount"], 48)
        self.assertEqual(package["caseCount"], 96)
        self.assertEqual(package["configuredMcPhotonsSum"], 7_320_000_000)
        self.assertEqual(package, m.regenerate(design(), runtime()))
        self.assertFalse(package["automaticTrigger"])
        self.assertFalse(package["automaticTier2Decision"])
        self.assertFalse(package["authorizationEnabled"])

    def test_matrix_runtime_and_split_are_exact(self):
        package = m.build(design(), runtime())
        self.assertEqual(len(package["matrix"]), 96)
        self.assertEqual(
            {row["timeout_seconds"] for row in package["matrix"]},
            {900, 1200, 1800, 2400},
        )
        self.assertFalse(
            set(package["trainingGeometryIds"])
            & set(package["internalHoldoutGeometryIds"])
        )
        self.assertTrue(all(case["seed"] > 910_096 for case in package["cases"]))

    def test_refuses_photon_role_seed_and_runtime_changes(self):
        value = design()
        value["cases"][96]["photonHistories"] = 30_000_000
        with self.assertRaises(m.Refusal):
            m.build(value, runtime())
        value = design()
        value["cases"][96]["role"] = "internal-holdout"
        with self.assertRaises(m.Refusal):
            m.build(value, runtime())
        value = design()
        value["cases"][96]["seed"] = 910_001
        with self.assertRaises(m.Refusal):
            m.build(value, runtime())
        locked = runtime()
        locked["hashes"]["atmosphereSha256"] = "bad"
        with self.assertRaises(m.Refusal):
            m.build(design(), locked)

    def test_source_audit_and_disabled_authorization(self):
        full = design()
        locked = runtime()
        package = m.build(full, locked)
        audit = m.source_audit(full, locked, package)
        self.assertEqual(audit["status"], "PASSED")
        template = m.authorization_template(package)
        self.assertFalse(template["enabled"])
        self.assertIsNone(template["authorizationOrdinal"])
        self.assertFalse(template["githubRerunAllowed"])

    def test_authorization_proposal_requires_separate_complete_decision(self):
        package = m.build(design(), runtime())
        with self.assertRaises(m.Refusal):
            m.authorization_proposal(package, {})
        decision = {
            "status": "TIER_2_EXECUTION_SEPARATELY_APPROVED",
            "tier1DatasetComplete": True,
            "requiredContinuationComplete": True,
            "surrogateFitFrozen": True,
            "internalHoldoutReviewed": True,
            "hardAnchorReportReviewed": True,
            "independentScientificReviewComplete": True,
            "automaticDecision": False,
            "decisionDocumentSha256": "a" * 64,
        }
        proposal = m.authorization_proposal(package, decision)
        self.assertFalse(proposal["authorizationEnabled"])
        self.assertFalse(proposal["automaticDispatch"])

    def test_fake_solver_aggregate_audit_and_precision(self):
        package = m.build(design(), runtime())
        results = fake_results(package)
        aggregate = m.aggregate(package, results)
        audit = m.independent_audit(package, aggregate, results)
        analysis = m.precision_analysis(package, aggregate, audit)
        self.assertEqual(len(analysis["points"]), 48)
        self.assertTrue(
            all(
                row["classification"] == "PRECISION_TARGET_MET"
                for row in analysis["points"]
            )
        )
        self.assertFalse(analysis["automaticContinuation"])
        self.assertFalse(analysis["modelFittingAuthorized"])

    def test_duplicate_and_tampered_case_refused(self):
        package = m.build(design(), runtime())
        with self.assertRaises(m.Refusal):
            m.refuse_duplicate_execution(
                package, [{"packageSha256": package["packageSha256"]}]
            )
        results = fake_results(package)
        results[0]["artifactSha256"] = None
        with self.assertRaises(m.Refusal):
            m.aggregate(package, results)


if __name__ == "__main__":
    unittest.main()
