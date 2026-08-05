from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "tier1_precision_continuation_v2",
    ROOT / "experiments/tier1-precision-continuation-v2/package.py",
)
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


ACCEPTED_IDS = {"train-0005", "train-0014", "train-0037"}


def _legacy_synthetic_source_fixture():
    schedule = {gid: photons for photons, gids in m.GEOMETRIES_BY_PHOTONS.items() for gid in gids}
    records = []
    for index in range(1, 49):
        gid = f"train-{index:04d}"
        continuation = gid in m.CONTINUATION_GEOMETRY_IDS
        zero = gid == m.ZERO_HIT_SOURCE_ID
        if zero:
            values = [0.0, 1.0]
            classification = "ADAPTIVE_CONTINUATION_REQUIRED"
            rsem = None
            rsem_status = "NOT_COMPUTED_ZERO_HIT_PRESENT"
            zero_ids = [f"{gid}-alis-b1"]
        elif continuation:
            values = [0.8, 1.2]
            classification = "ADAPTIVE_CONTINUATION_REQUIRED"
            rsem = m.classify_values(values)["relativeStandardErrorOfMean"]
            rsem_status = "COMPUTED"
            zero_ids = []
        elif gid in ACCEPTED_IDS:
            values = [0.94, 1.06]
            classification = "PRECISION_ACCEPTED"
            rsem = m.classify_values(values)["relativeStandardErrorOfMean"]
            rsem_status = "COMPUTED"
            zero_ids = []
        else:
            values = [0.99, 1.01]
            classification = "PRECISION_TARGET_MET"
            rsem = m.classify_values(values)["relativeStandardErrorOfMean"]
            rsem_status = "COMPUTED"
            zero_ids = []
        role = "internal-holdout" if gid in m.INTERNAL_HOLDOUT_IDS else "surrogate-training"
        geometry = {
            "geometryId": gid,
            "photonHistoriesPerBlock": schedule.get(gid, 20_000_000),
            "alisSpectralImportanceSamplingNm": (500.0, 550.0, 600.0)[index % 3],
            "sunDepressionDeg": 2.0 + index / 4,
        }
        records.append(
            {
                "geometryId": gid,
                "geometry": geometry,
                "role": role,
                "caseIds": [f"{gid}-alis-b1", f"{gid}-alis-b2"],
                "classification": classification,
                "numericalStatus": "NUMERICAL_ZERO_HIT_UNDERCONVERGED" if zero else "NUMERIC_ESTIMATES_AVAILABLE",
                "executionComplete": True,
                "scientificallyEligible": not continuation,
                "eligibleForProvisionalFit": not continuation and role == "surrogate-training",
                "eligibleForInternalHoldout": not continuation and role == "internal-holdout",
                "zeroHitCaseIds": zero_ids,
                "statistics": {
                    "blockCount": 2,
                    "valuesCdM2": values,
                    "nonzeroBlockValuesCdM2": [value for value in values if value],
                    "zeroHitBlockCount": sum(value == 0.0 for value in values),
                    "zeroHitBlockFraction": sum(value == 0.0 for value in values) / 2,
                    "relativeStandardErrorOfMean": rsem,
                    "relativeStandardErrorStatus": rsem_status,
                },
            }
        )
    dataset = {
        "schemaVersion": 2,
        "stageId": "twilight-surrogate-tier-1-analysis-v2",
        "status": "TIER_1_NUMERICAL_DATASET_PARTIAL_PRECISION",
        "executionComplete": True,
        "scientificallyEligible": False,
        "records": records,
        "adaptiveContinuationRequiredGeometryIds": list(m.CONTINUATION_GEOMETRY_IDS),
        "zeroHitGeometryIds": [m.ZERO_HIT_SOURCE_ID],
    }
    aggregate = {
        "schemaVersion": 2,
        "stageId": "mystic-batch-v1",
        "status": "COMPLETED",
        "classification": "SCIENTIFICALLY_INELIGIBLE",
        "executionComplete": True,
        "scientificallyEligible": False,
        "caseCountPlanned": 96,
        "caseCountCompleted": 96,
        "caseCountFailed": 0,
        "syntaxCheckCount": 96,
        "solverExecutionCount": 96,
        "configuredMcPhotonsSum": 6_960_000_000,
        "completedConfiguredMcPhotonsSum": 6_960_000_000,
        "zeroHitCaseCount": 1,
        "continuationRequiredGeometryIds": [m.ZERO_HIT_SOURCE_ID],
    }
    audit = {
        "schemaVersion": 2,
        "stageId": "mystic-batch-v1",
        "status": "PASSED",
        "batchClassification": "SCIENTIFICALLY_INELIGIBLE",
        "executionComplete": True,
        "scientificallyEligible": False,
        "caseResultCount": 96,
        "incompleteGeometryEnteredTrainingEligibility": False,
        "unaffectedGeometryStatisticsVerified": True,
        "zeroHitDiagnostics": {
            "caseId": "train-0047-alis-b1",
            "geometryId": m.ZERO_HIT_SOURCE_ID,
            "block": 1,
            "classification": "NUMERICAL_ZERO_HIT_UNDERCONVERGED",
            "derivedFromRawOutputs": True,
        },
    }
    source_seeds = list(range(1, 97))
    provenance = {
        "runId": m.SOURCE_RUN_ID,
        "runAttempt": 1,
        "headSha": m.SOURCE_HEAD_SHA,
        "authorizationRef": m.SOURCE_AUTHORIZATION_REF,
        "executionKey": m.SOURCE_EXECUTION_KEY,
        "authorizationOrdinal": m.SOURCE_AUTHORIZATION_ORDINAL,
        "event": "workflow_dispatch",
        "planRawSha256": m.SOURCE_PLAN_RAW_SHA256,
        "artifactManifestRawSha256": m.SOURCE_ARTIFACT_MANIFEST_RAW_SHA256,
        "historicalReproductionRawSha256": m.SOURCE_HISTORICAL_REPRODUCTION_RAW_SHA256,
        "artifactDigests": m.SOURCE_ARTIFACT_DIGESTS,
        "historicalTerminalConclusion": "failure",
        "historicalEvidenceImmutable": True,
        "correctedInterpretationOnly": True,
        "sourceSeeds": source_seeds,
        "sourceSeedsSha256": m.canonical_sha256(source_seeds),
        "bindings": {
            "datasetSha256": m.canonical_sha256(dataset),
            "aggregateSha256": m.canonical_sha256(aggregate),
            "auditSha256": m.canonical_sha256(audit),
        },
    }
    return dataset, aggregate, audit, provenance


def source_fixture():
    evidence = ROOT / "evidence" / "ordinal2-corrected-v2"
    dataset = json.loads((evidence / "tier1-numerical-dataset.json").read_text())
    aggregate = json.loads((evidence / "batch-summary.json").read_text())
    audit = json.loads((evidence / "audit-report.json").read_text())
    plan = json.loads((evidence / "plan.json").read_text())
    source_seeds = [case["seed"] for case in plan["cases"]]
    provenance = {
        "runId": m.SOURCE_RUN_ID,
        "runAttempt": 1,
        "headSha": m.SOURCE_HEAD_SHA,
        "authorizationRef": m.SOURCE_AUTHORIZATION_REF,
        "executionKey": m.SOURCE_EXECUTION_KEY,
        "authorizationOrdinal": m.SOURCE_AUTHORIZATION_ORDINAL,
        "event": "workflow_dispatch",
        "planRawSha256": m.SOURCE_PLAN_RAW_SHA256,
        "artifactManifestRawSha256": m.SOURCE_ARTIFACT_MANIFEST_RAW_SHA256,
        "historicalReproductionRawSha256": m.SOURCE_HISTORICAL_REPRODUCTION_RAW_SHA256,
        "artifactDigests": m.SOURCE_ARTIFACT_DIGESTS,
        "historicalTerminalConclusion": "failure",
        "historicalEvidenceImmutable": True,
        "correctedInterpretationOnly": True,
        "sourceSeeds": source_seeds,
        "sourceSeedsSha256": m.SOURCE_SEEDS_SHA256,
        "bindings": {
            "datasetSha256": m.SOURCE_DATASET_CANONICAL_SHA256,
            "aggregateSha256": m.SOURCE_AGGREGATE_CANONICAL_SHA256,
            "auditSha256": m.SOURCE_AUDIT_CANONICAL_SHA256,
        },
    }
    return dataset, aggregate, audit, provenance


def fake_results(cases, value=1.0):
    results = []
    for case in cases:
        case_value = value(case) if callable(value) else value
        node_value = case_value / (6.83002 * sum(m.CIE))
        nodes = [node_value] * 15
        case_value = m._photopic_value(nodes)
        results.append(
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
                "valueCdM2": case_value,
                "selectedNodeRadiance": nodes,
                "artifactSha256": "1" * 64,
                "inputSha256": "2" * 64,
                "radianceOutputSha256": "3" * 64,
                "stdOutputSha256": "4" * 64,
                "runtimeSha256": "5" * 64,
            }
        )
    return results


def completed_audited_wave(proposal, wave, active_geometry_ids, value=None):
    if value is None:
        source_means = {
            row["geometryId"]: sum(row["valuesCdM2"]) / len(row["valuesCdM2"])
            for row in proposal["sourceRecords"]
        }
        value = lambda case: source_means[case["groupId"]]
    cases = m.wave_cases(proposal, wave, active_geometry_ids)
    results = fake_results(cases, value)
    aggregate = m.aggregate_wave(proposal, wave, active_geometry_ids, results)
    audit = m.audit_wave(proposal, wave, active_geometry_ids, results, aggregate)
    if audit["status"] != "PASSED":
        raise AssertionError(audit["failures"])
    return aggregate, audit


class ContinuationV2Tests(unittest.TestCase):
    def test_accepts_execution_complete_scientifically_ineligible_schema_v2_source(self):
        proposal = m.build(*source_fixture())
        self.assertEqual(proposal["source"]["runId"], 30_952_457_327)
        self.assertEqual(proposal["continuationGeometryIds"], list(m.CONTINUATION_GEOMETRY_IDS))
        self.assertEqual(proposal["continuationGeometryCount"], 20)
        self.assertFalse(proposal["scientificExecution"])
        self.assertFalse(proposal["authorizationEnabled"])
        self.assertFalse(proposal["automaticContinuation"])
        self.assertFalse(proposal["githubRerunAllowed"])

    def test_exact_photon_groups_wave_and_global_caps(self):
        proposal = m.build(*source_fixture())
        for wave in (1, 2, 3):
            cases = m.wave_cases(proposal, wave, m.CONTINUATION_GEOMETRY_IDS)
            self.assertEqual(len(cases), 40)
            self.assertEqual(sum(case["photonHistories"] for case in cases), 5_100_000_000)
        self.assertEqual(len(proposal["potentialCases"]), 120)
        self.assertEqual(sum(case["photonHistories"] for case in proposal["potentialCases"]), 15_300_000_000)
        self.assertEqual(
            {case["role"] for case in proposal["potentialCases"] if case["groupId"] in m.INTERNAL_HOLDOUT_IDS},
            {"internal-holdout"},
        )

    def test_frozen_seed_table_is_unique_bound_and_source_fresh(self):
        proposal = m.build(*source_fixture())
        seeds = [case["seed"] for case in proposal["potentialCases"]]
        self.assertEqual(len(seeds), len(set(seeds)))
        self.assertEqual(proposal["seedProof"]["sourceContinuationOverlap"], [])
        dataset, aggregate, audit, provenance = source_fixture()
        provenance["sourceSeeds"][0] = seeds[0]
        provenance["sourceSeedsSha256"] = m.canonical_sha256(sorted(provenance["sourceSeeds"]))
        with self.assertRaises(m.Refusal):
            m.build(dataset, aggregate, audit, provenance)

        proposal = m.build(*source_fixture())
        proposal["potentialCases"][0]["seed"] = proposal["seedProof"]["sourceSeedCount"]
        unhashed = dict(proposal)
        unhashed.pop("proposalSha256")
        proposal["proposalSha256"] = m.canonical_sha256(unhashed)
        with self.assertRaisesRegex(m.Refusal, "case universe"):
            m.wave_cases(proposal, 1, m.CONTINUATION_GEOMETRY_IDS)

    def test_immutable_ordinal2_identity_and_hash_binding_refused_on_drift(self):
        dataset, aggregate, audit, provenance = source_fixture()
        provenance["runAttempt"] = 2
        with self.assertRaises(m.Refusal):
            m.build(dataset, aggregate, audit, provenance)
        dataset, aggregate, audit, provenance = source_fixture()
        aggregate["classification"] = "BATCH_NUMERICALLY_COMPLETE"
        provenance["bindings"]["aggregateSha256"] = m.canonical_sha256(aggregate)
        with self.assertRaises(m.Refusal):
            m.build(dataset, aggregate, audit, provenance)

    def test_source_geometry_selection_role_and_zero_rsem_are_immutable(self):
        dataset, aggregate, audit, provenance = source_fixture()
        dataset["adaptiveContinuationRequiredGeometryIds"].pop()
        provenance["bindings"]["datasetSha256"] = m.canonical_sha256(dataset)
        with self.assertRaises(m.Refusal):
            m.build(dataset, aggregate, audit, provenance)
        dataset, aggregate, audit, provenance = source_fixture()
        changed = next(record for record in dataset["records"] if record["geometryId"] == "train-0003")
        changed["geometry"]["sunDepressionDeg"] += 1.0
        changed["geometry"]["alisSpectralImportanceSamplingNm"] = 500.0
        provenance["bindings"]["datasetSha256"] = m.canonical_sha256(dataset)
        with self.assertRaisesRegex(m.Refusal, "reviewed ordinal-2 evidence"):
            m.build(dataset, aggregate, audit, provenance)
        dataset, aggregate, audit, provenance = source_fixture()
        zero = next(record for record in dataset["records"] if record["geometryId"] == "train-0047")
        zero["statistics"]["relativeStandardErrorOfMean"] = 1.0
        provenance["bindings"]["datasetSha256"] = m.canonical_sha256(dataset)
        with self.assertRaises(m.Refusal):
            m.build(dataset, aggregate, audit, provenance)

    def test_threshold_boundaries_and_exhaustion(self):
        self.assertEqual(m.classify_values([0.95, 1.05])["classification"], "PRECISION_TARGET_MET")
        self.assertEqual(m.classify_values([0.92, 1.08])["classification"], "PRECISION_ACCEPTED")
        self.assertEqual(m.classify_values([0.9, 1.1])["classification"], "ADAPTIVE_CONTINUATION_REQUIRED")
        exhausted = m.classify_values([0.1, 1.9] * 4)
        self.assertEqual(exhausted["classification"], "PRECISION_CONTINUATION_EXHAUSTED")
        self.assertFalse(exhausted["scientificallyEligible"])

    def test_zero_is_preserved_with_null_rsem_and_exhausts_separately(self):
        interim = m.classify_values([0.0, 1.0, 1.0, 1.0])
        self.assertEqual(interim["classification"], "ADAPTIVE_CONTINUATION_REQUIRED")
        self.assertIsNone(interim["relativeStandardErrorOfMean"])
        self.assertEqual(interim["relativeStandardErrorStatus"], "NOT_COMPUTED_ZERO_HIT_PRESENT")
        exhausted = m.classify_values([0.0] + [1.0] * 7)
        self.assertEqual(exhausted["classification"], "PRECISION_CONTINUATION_EXHAUSTED_ZERO_HIT")
        self.assertEqual(exhausted["zeroHitBlockCount"], 1)

    def test_wave_aggregate_separates_execution_failure_from_valid_zero(self):
        proposal = m.build(*source_fixture())
        cases = m.wave_cases(proposal, 1, m.CONTINUATION_GEOMETRY_IDS)
        results = fake_results(cases, lambda case: 0.0 if case["groupId"] == "train-0047" and case["block"] == 3 else 1.0)
        aggregate = m.aggregate_wave(proposal, 1, m.CONTINUATION_GEOMETRY_IDS, results)
        self.assertEqual(aggregate["status"], "COMPLETED")
        self.assertEqual(len(aggregate["zeroHitDiagnostics"]), 1)
        audit = m.audit_wave(proposal, 1, m.CONTINUATION_GEOMETRY_IDS, results, aggregate)
        self.assertEqual(audit["status"], "PASSED")
        self.assertTrue(audit["independentlyRecomputedFromRawSelectedNodeRadiance"])
        failed = copy.deepcopy(results)
        failed[0]["solver"]["timedOut"] = True
        aggregate = m.aggregate_wave(proposal, 1, m.CONTINUATION_GEOMETRY_IDS, failed)
        self.assertEqual(aggregate["classification"], "STRUCTURAL_OR_EXECUTION_FAILURE")
        self.assertTrue(aggregate["executionFailures"])

    def test_inconsistent_zero_spectrum_is_structural_failure(self):
        proposal = m.build(*source_fixture())
        cases = m.wave_cases(proposal, 1, m.CONTINUATION_GEOMETRY_IDS)
        results = fake_results(cases)
        results[0]["valueCdM2"] = 0.0
        aggregate = m.aggregate_wave(proposal, 1, m.CONTINUATION_GEOMETRY_IDS, results)
        self.assertEqual(aggregate["classification"], "STRUCTURAL_OR_EXECUTION_FAILURE")
        self.assertIn("zero-estimator-inconsistent", {failure["code"] for failure in aggregate["structuralFailures"]})

    def test_two_block_stopping_is_additive_and_zero_reaches_cap(self):
        proposal = m.build(*source_fixture())
        wave1, audit1 = completed_audited_wave(proposal, 1, m.CONTINUATION_GEOMETRY_IDS)
        analysis1 = m.analyze_waves(proposal, [wave1], [audit1])
        self.assertEqual(len(analysis1["nextWaveGeometryIds"]), 15)
        self.assertIn("train-0047", analysis1["nextWaveGeometryIds"])

        wave2, audit2 = completed_audited_wave(proposal, 2, analysis1["nextWaveGeometryIds"])
        analysis2 = m.analyze_waves(proposal, [wave1, wave2], [audit1, audit2])
        self.assertEqual(len(analysis2["nextWaveGeometryIds"]), 13)
        accepted = [point for point in analysis2["points"] if point["geometryId"] == "train-0019"][0]
        self.assertEqual(accepted["blockCount"], 6)
        self.assertEqual(accepted["classification"], "PRECISION_ACCEPTED")

        wave3, audit3 = completed_audited_wave(proposal, 3, analysis2["nextWaveGeometryIds"])
        analysis3 = m.analyze_waves(proposal, [wave1, wave2, wave3], [audit1, audit2, audit3])
        self.assertEqual(analysis3["nextWaveGeometryIds"], [])
        self.assertEqual(len(analysis3["exhaustedGeometryIds"]), 6)
        self.assertIn("train-0047", analysis3["exhaustedGeometryIds"])
        zero = [point for point in analysis3["points"] if point["geometryId"] == "train-0047"][0]
        self.assertEqual(zero["blockCount"], 8)
        self.assertEqual(zero["classification"], "PRECISION_CONTINUATION_EXHAUSTED_ZERO_HIT")
        self.assertIsNone(zero["relativeStandardErrorOfMean"])

    def test_stopped_geometry_cannot_be_selectively_reintroduced(self):
        proposal = m.build(*source_fixture())
        wave1, audit1 = completed_audited_wave(proposal, 1, m.CONTINUATION_GEOMETRY_IDS)
        wave2, audit2 = completed_audited_wave(proposal, 2, m.CONTINUATION_GEOMETRY_IDS)
        wrong_wave3, wrong_audit3 = completed_audited_wave(proposal, 3, m.CONTINUATION_GEOMETRY_IDS)
        with self.assertRaises(m.Refusal):
            m.analyze_waves(proposal, [wave1, wave2, wrong_wave3], [audit1, audit2, wrong_audit3])

    def test_analysis_requires_matching_independent_raw_wave_audit(self):
        proposal = m.build(*source_fixture())
        wave1, audit1 = completed_audited_wave(proposal, 1, m.CONTINUATION_GEOMETRY_IDS)
        fabricated = copy.deepcopy(wave1)
        fabricated["valuesByGeometry"]["train-0003"].extend(
            [
                {"caseId": "forged-b5", "block": 5, "valueCdM2": 1.0, "zeroHit": False},
                {"caseId": "forged-b6", "block": 6, "valueCdM2": 1.0, "zeroHit": False},
            ]
        )
        with self.assertRaisesRegex(m.Refusal, "independent audit invalid"):
            m.analyze_waves(proposal, [fabricated], [audit1])
        forged_raw = copy.deepcopy(audit1)
        forged_raw["rawValuesByGeometry"]["train-0003"][0]["valueCdM2"] = 1_000_000.0
        unhashed = dict(forged_raw)
        unhashed.pop("auditPayloadSha256")
        forged_raw["auditPayloadSha256"] = m.canonical_sha256(unhashed)
        with self.assertRaisesRegex(m.Refusal, "audited geometry universe"):
            m.analyze_waves(proposal, [wave1], [forged_raw])

    def test_authorization_template_allocates_nothing(self):
        proposal = m.build(*source_fixture())
        template = m.authorization_template(proposal, 1)
        self.assertFalse(template["enabled"])
        self.assertIsNone(template["authorizationOrdinal"])
        self.assertIsNone(template["executionKey"])
        self.assertFalse(template["automaticDispatch"])
        self.assertFalse(template["githubRerunAllowed"])


if __name__ == "__main__":
    unittest.main()
