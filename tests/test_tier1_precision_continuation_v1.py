from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "continuation", ROOT / "experiments/tier1-precision-continuation-v1/package.py"
)
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def fixture(high_geometry: str = "train-0048"):
    geometries = []
    cases = []
    records = []
    photon_total = 0
    for index in range(1, 49):
        gid = f"train-{index:04d}"
        photons = (
            20_000_000
            if index <= 19
            else 50_000_000
            if index <= 31
            else 100_000_000
            if index <= 40
            else 200_000_000
        )
        role = "internal-holdout" if index % 5 == 0 else "surrogate-training"
        importance = (500.0, 550.0, 600.0)[index % 3]
        geometry = {"geometryId": gid, "sunDepressionDeg": 2 + index / 4, "role": role}
        geometries.append(geometry)
        values = [0.8, 1.2] if gid == high_geometry else [1.0, 1.01]
        case_ids = []
        for block in (1, 2):
            ordinal = len(cases) + 1
            cid = f"{gid}-alis-b{block}"
            case_ids.append(cid)
            cases.append(
                {
                    "ordinal": ordinal,
                    "caseId": cid,
                    "groupId": gid,
                    "block": block,
                    "seed": 910_000 + ordinal,
                    "role": role,
                    "photonHistories": photons,
                    "alisSpectralImportanceSamplingNm": importance,
                    "geometrySha256": m.canonical_sha256(geometry),
                }
            )
            photon_total += photons
        measured = m.rsem(values)
        records.append(
            {
                "geometryId": gid,
                "role": role,
                "photonHistoriesPerBlock": photons,
                "alisSpectralImportanceSamplingNm": importance,
                "caseIds": case_ids,
                "classification": m.classify_rsem(measured),
                "statistics": {
                    "blockCount": 2,
                    "blockValuesCdM2": values,
                    "relativeStandardErrorOfMean": measured,
                },
            }
        )
    assert photon_total == 6_960_000_000
    dataset = {
        "schemaVersion": 1,
        "stageId": "twilight-surrogate-tier-1-analysis-v1",
        "status": "TIER_1_NUMERICAL_DATASET_COMPLETE",
        "geometryCount": 48,
        "caseCount": 96,
        "configuredMcPhotonsSum": photon_total,
        "blocksPerGeometry": 2,
        "allCasesFirstAttempt": True,
        "aggregatePassed": True,
        "independentAuditPassed": True,
        "sourceProvenanceValidated": True,
        "hashValidationPassed": True,
        "seedValidationPassed": True,
        "photonAccountingPassed": True,
        "precisionThresholds": {"targetMaximum": 0.05, "acceptedMaximum": 0.08},
        "geometries": geometries,
        "cases": cases,
        "records": records,
    }
    aggregate = {
        "classification": "BATCH_NUMERICALLY_COMPLETE",
        "caseCountPlanned": 96,
        "caseCountCompleted": 96,
        "caseCountFailed": 0,
        "syntaxCheckCount": 96,
        "solverExecutionCount": 96,
        "configuredMcPhotonsSum": photon_total,
        "completedConfiguredMcPhotonsSum": photon_total,
    }
    audit = {
        "status": "PASSED",
        "caseResultCount": 96,
        "planValidationPassed": True,
        "seedValidationPassed": True,
        "hashValidationPassed": True,
        "photonAccountingPassed": True,
        "firstAttemptValidationPassed": True,
    }
    provenance = {
        "runId": 12345,
        "runAttempt": 1,
        "event": "workflow_dispatch",
        "headSha": "a" * 40,
        "artifactsComplete": True,
        "sourceProvenanceValid": True,
        "hashesValid": True,
        "seedsValid": True,
        "photonAccountingValid": True,
        "firstAttemptAuditPassed": True,
        "bindings": {
            "datasetSha256": m.canonical_sha256(dataset),
            "aggregateSha256": m.canonical_sha256(aggregate),
            "auditSha256": m.canonical_sha256(audit),
        },
        "artifacts": [
            {"name": name, "runId": 12345, "expired": False, "digest": "sha256:" + char * 64}
            for name, char in zip(
                [
                    "twilight-surrogate-tier-1-execution-preflight",
                    "twilight-surrogate-tier-1-aggregate",
                    "twilight-surrogate-tier-1-audit",
                    "twilight-surrogate-tier-1-analysis",
                ],
                "bcde",
            )
        ],
    }
    return dataset, aggregate, audit, provenance


def fake_results(proposal):
    rows = []
    for case in proposal["cases"]:
        rows.append(
            {
                "caseId": case["caseId"],
                "seed": case["seed"],
                "role": case["role"],
                "photonHistories": case["photonHistories"],
                "alisSpectralImportanceSamplingNm": case["alisSpectralImportanceSamplingNm"],
                "geometrySha256": case["geometrySha256"],
                "status": "COMPLETED",
                "syntaxCheckCount": 1,
                "solverExecutionCount": 1,
                "syntax": {"exitCode": 0, "timedOut": False},
                "solver": {"exitCode": 0, "timedOut": False},
                "valueCdM2": 1.0,
                "artifactSha256": "1" * 64,
                "inputSha256": "2" * 64,
                "outputSha256": "3" * 64,
                "runtimeSha256": "4" * 64,
            }
        )
    return rows


class ContinuationTests(unittest.TestCase):
    def test_frozen_threshold_boundaries(self):
        self.assertEqual(m.classify_rsem(0.05), "PRECISION_TARGET_MET")
        self.assertEqual(m.classify_rsem(0.0500001), "PRECISION_ACCEPTED")
        self.assertEqual(m.classify_rsem(0.08), "PRECISION_ACCEPTED")
        self.assertEqual(m.classify_rsem(0.0800001), "ADAPTIVE_CONTINUATION_REQUIRED")

    def test_build_is_bounded_fresh_and_proposal_only(self):
        proposal = m.build(*fixture())
        self.assertEqual(proposal["continuationGeometryCount"], 1)
        point = [row for row in proposal["points"] if row["geometryId"] == "train-0048"][0]
        self.assertEqual(point["requiredTotalBlockCount"], 8)
        self.assertEqual(point["additionalBlockCount"], 6)
        self.assertEqual(proposal["caseCount"], 6)
        self.assertEqual(len({case["seed"] for case in proposal["cases"]}), 6)
        self.assertTrue(all(case["seed"] > 910_096 for case in proposal["cases"]))
        self.assertFalse(proposal["automaticDispatch"])
        self.assertFalse(proposal["authorizationEnabled"])
        self.assertFalse(proposal["tier2AutomaticallyAuthorized"])

    def test_source_refuses_retry_and_hash_or_role_change(self):
        dataset, aggregate, audit, provenance = fixture()
        provenance["runAttempt"] = 2
        with self.assertRaises(m.Refusal):
            m.build(dataset, aggregate, audit, provenance)
        dataset, aggregate, audit, provenance = fixture()
        dataset["records"][0]["role"] = "internal-holdout"
        provenance["bindings"]["datasetSha256"] = m.canonical_sha256(dataset)
        with self.assertRaises(m.Refusal):
            m.build(dataset, aggregate, audit, provenance)

    def test_source_refuses_deleted_block_and_threshold_change(self):
        dataset, aggregate, audit, provenance = fixture()
        dataset["records"][0]["caseIds"].pop()
        provenance["bindings"]["datasetSha256"] = m.canonical_sha256(dataset)
        with self.assertRaises(m.Refusal):
            m.build(dataset, aggregate, audit, provenance)
        dataset, aggregate, audit, provenance = fixture()
        dataset["precisionThresholds"]["acceptedMaximum"] = 0.081
        provenance["bindings"]["datasetSha256"] = m.canonical_sha256(dataset)
        with self.assertRaises(m.Refusal):
            m.build(dataset, aggregate, audit, provenance)

    def test_fake_results_aggregate_audit_and_final_classification(self):
        proposal = m.build(*fixture())
        results = fake_results(proposal)
        aggregate = m.aggregate_results(proposal, results)
        audit = m.independent_audit(proposal, aggregate, results)
        final = m.final_analysis(proposal, aggregate, audit)
        row = [item for item in final["points"] if item["geometryId"] == "train-0048"][0]
        self.assertEqual(row["blockCount"], 8)
        self.assertIn(
            row["classification"],
            {"PRECISION_TARGET_MET", "PRECISION_ACCEPTED", "ADAPTIVE_CONTINUATION_REQUIRED"},
        )
        self.assertTrue(final["noFourthClassification"])
        self.assertFalse(final["additionalExecutionAutomaticallyAuthorized"])

    def test_duplicate_and_tampered_result_refused(self):
        proposal = m.build(*fixture())
        with self.assertRaises(m.Refusal):
            m.refuse_duplicate_execution(proposal, [{"proposalSha256": proposal["proposalSha256"]}])
        results = fake_results(proposal)
        results[0]["seed"] += 1
        with self.assertRaises(m.Refusal):
            m.aggregate_results(proposal, results)

    def test_disabled_authorization_template_allocates_nothing(self):
        proposal = m.build(*fixture())
        template = m.authorization_template(proposal)
        self.assertFalse(template["enabled"])
        self.assertIsNone(template["authorizationOrdinal"])
        self.assertFalse(template["automaticDispatch"])
        self.assertFalse(template["githubRerunAllowed"])


if __name__ == "__main__":
    unittest.main()
