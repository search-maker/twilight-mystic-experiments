from __future__ import annotations

import copy
import importlib.util
import json
import math
import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_PATH = ROOT / "experiments" / "tier1-precision-continuation-wave1-v2" / "package.py"
PREREG_PATH = ROOT / "evidence" / "tier1-precision-continuation-wave1-v2" / "preregistration.json"
AUTH_PATH = ROOT / "experiments" / "tier1-precision-continuation-wave1-v2" / "authorization.template.json"
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "tier1-precision-continuation-wave1-v2-contract.yml"


def load_module():
    spec = importlib.util.spec_from_file_location("tier1_precision_continuation_wave1_v2", PACKAGE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load wave-1 package")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


m = load_module()


def committed_preregistration():
    return json.loads(PREREG_PATH.read_text(encoding="utf-8"))


def fake_results(preregistration, value=1.0):
    base = m.base_module(ROOT)
    rows = []
    for case in preregistration["cases"]:
        case_value = value(case) if callable(value) else value
        node_value = case_value / (6.83002 * sum(base.CIE))
        nodes = [node_value] * len(base.CIE)
        case_value = base._photopic_value(nodes)
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
                "valueCdM2": case_value,
                "selectedNodeRadiance": nodes,
                "artifactSha256": "1" * 64,
                "inputSha256": "2" * 64,
                "radianceOutputSha256": "3" * 64,
                "stdOutputSha256": "4" * 64,
                "runtimeSha256": "5" * 64,
            }
        )
    return rows


class Wave1PreparationTests(unittest.TestCase):
    def test_base_source_binding_is_line_ending_independent(self):
        source = (ROOT / m.BASE_PACKAGE_RELATIVE_PATH).read_bytes().replace(b"\r\n", b"\n")
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp) / "base.py"
            temp_path.write_bytes(source)
            lf_hash = m.canonical_source_sha256(temp_path)
            temp_path.write_bytes(source.replace(b"\n", b"\r\n"))
            crlf_hash = m.canonical_source_sha256(temp_path)
        self.assertEqual(lf_hash, m.BASE_PACKAGE_RAW_SHA256)
        self.assertEqual(crlf_hash, m.BASE_PACKAGE_RAW_SHA256)
    def test_committed_generation_is_byte_identical(self):
        first = m.build_preregistration(ROOT)
        second = m.build_preregistration(ROOT)
        self.assertEqual(m.dump_json(first), m.dump_json(second))
        self.assertEqual(PREREG_PATH.read_text(encoding="utf-8"), m.dump_json(first))
        template = m.authorization_template(first, ROOT)
        self.assertEqual(AUTH_PATH.read_text(encoding="utf-8"), m.dump_json(template))
        self.assertEqual(m.canonical_sha256({k: v for k, v in first.items() if k != "preregistrationSha256"}), first["preregistrationSha256"])

    def test_exact_wave1_case_geometry_role_and_budget_accounting(self):
        prereg = committed_preregistration()
        m.validate_preregistration(prereg, ROOT)
        self.assertEqual(prereg["baseCommitSha"], m.BASE_COMMIT_SHA)
        self.assertEqual(prereg["blocks"], [3, 4])
        self.assertEqual(prereg["geometryCount"], 20)
        self.assertEqual(prereg["caseCount"], 40)
        self.assertEqual(len({row["caseId"] for row in prereg["cases"]}), 40)
        self.assertEqual({row["block"] for row in prereg["cases"]}, {3, 4})
        self.assertEqual(sum(row["photonHistories"] for row in prereg["cases"]), 5_100_000_000)
        self.assertEqual(prereg["roleCounts"], {
            "surrogateTrainingGeometries": 17,
            "internalHoldoutGeometries": 3,
            "surrogateTrainingCases": 34,
            "internalHoldoutCases": 6,
        })
        self.assertEqual(prereg["internalHoldoutGeometryIds"], ["train-0015", "train-0035", "train-0045"])

    def test_wave1_uses_only_frozen_b3_b4_seed_subset(self):
        prereg = committed_preregistration()
        base = m.base_module(ROOT)
        expected = [
            base.PRECOMPUTED_SEEDS[gid][block - 3]
            for gid in base.CONTINUATION_GEOMETRY_IDS
            for block in (3, 4)
        ]
        observed = [row["seed"] for row in prereg["cases"]]
        self.assertEqual(observed, expected)
        self.assertEqual(len(observed), len(set(observed)))
        self.assertEqual(prereg["seedProof"]["historicalOverlap"], [])
        self.assertEqual(prereg["seedProof"]["historicalSeedCount"], 196)

    def test_seed_overlap_with_any_consumed_source_is_refused(self):
        base = m.base_module(ROOT)
        _, _, _, _, ordinal2 = m._base_inputs(ROOT, base)
        clean = [base.PRECOMPUTED_SEEDS[gid][0] for gid in base.CONTINUATION_GEOMETRY_IDS for _ in (0, 1)]
        clean = list(range(1, 41))
        m._historical_seed_proof(base, ordinal2, clean)
        for consumed in (m.ORDINAL1_SEEDS[0], ordinal2[0], m.CONSUMED_PROBE_SEEDS[0]):
            changed = list(clean)
            changed[0] = consumed
            with self.subTest(consumed=consumed), self.assertRaisesRegex(m.Refusal, "overlaps consumed"):
                m._historical_seed_proof(base, ordinal2, changed)

    def test_original_b1_b2_physical_inputs_and_bindings_are_preserved(self):
        prereg = committed_preregistration()
        base = m.base_module(ROOT)
        proposal, _ = m._build_base_proposal(ROOT, base)
        source = {row["geometryId"]: row for row in proposal["sourceRecords"]}
        for case in prereg["cases"]:
            row = source[case["groupId"]]
            self.assertEqual(case["preservedSourceCaseIds"], row["caseIds"])
            self.assertEqual(case["preservedSourceValuesCdM2"], row["valuesCdM2"])
            self.assertEqual(case["preservedZeroHitCaseIds"], row["zeroHitCaseIds"])
            self.assertEqual(case["geometry"], row["geometry"])
            self.assertEqual(case["geometrySha256"], base.canonical_sha256(row["geometry"]))
        self.assertTrue(prereg["preservation"]["originalBlocksB1B2Preserved"])
        self.assertTrue(prereg["preservation"]["evidenceBindingsUnchanged"])

    def test_preregistration_refuses_scope_threshold_role_photon_or_hash_drift(self):
        prereg = committed_preregistration()
        mutations = []
        for field, value in (("geometryCount", 19), ("caseCount", 39), ("maximumConfiguredPhotonHistories", 5_100_000_001)):
            row = copy.deepcopy(prereg)
            row[field] = value
            mutations.append(row)
        row = copy.deepcopy(prereg)
        row["thresholds"]["targetMaximum"] = 0.051
        mutations.append(row)
        row = copy.deepcopy(prereg)
        row["cases"][0]["role"] = "internal-holdout"
        mutations.append(row)
        row = copy.deepcopy(prereg)
        row["cases"][0]["photonHistories"] += 1
        mutations.append(row)
        row = copy.deepcopy(prereg)
        row["sourceBindings"]["basePackageRawSha256"] = "0" * 64
        mutations.append(row)
        for index, changed in enumerate(mutations):
            with self.subTest(index=index), self.assertRaises(m.Refusal):
                m.validate_preregistration(changed, ROOT)

    def test_bound_source_evidence_missing_malformed_or_hash_drift_is_refused(self):
        with tempfile.TemporaryDirectory() as raw:
            temp_root = Path(raw)
            base_target = temp_root / m.BASE_PACKAGE_RELATIVE_PATH
            base_target.parent.mkdir(parents=True)
            shutil.copy2(ROOT / m.BASE_PACKAGE_RELATIVE_PATH, base_target)
            for relative in m.EVIDENCE_RAW_SHA256:
                target = temp_root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / relative, target)
            m.build_preregistration(temp_root)
            plan = temp_root / "evidence/ordinal2-corrected-v2/plan.json"
            plan.write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(m.Refusal, "bound evidence hash changed"):
                m.build_preregistration(temp_root)
            plan.unlink()
            with self.assertRaises((m.Refusal, FileNotFoundError)):
                m.build_preregistration(temp_root)

    def test_authorization_template_is_disabled_and_allocates_nothing(self):
        prereg = committed_preregistration()
        template = json.loads(AUTH_PATH.read_text(encoding="utf-8"))
        self.assertEqual(template, m.authorization_template(prereg, ROOT))
        for field in ("authorizationOrdinal", "authorizationRef", "authorizationCommit", "executionKey", "runAttempt"):
            self.assertIsNone(template[field])
        for field in ("enabled", "dispatch", "workflowDispatchEnabled", "automaticDispatch", "githubRerunAllowed", "solverExecutionAuthorized"):
            self.assertFalse(template[field])

    def test_case_contracts_are_one_shot_attempt1_only(self):
        prereg = committed_preregistration()
        contracts = m.case_contracts(prereg, ROOT)
        self.assertEqual(len(contracts), 40)
        self.assertTrue(all(row["syntaxCheckCountExactly"] == 1 for row in contracts))
        self.assertTrue(all(row["solverExecutionCountExactly"] == 1 for row in contracts))
        self.assertTrue(all(row["attemptMustEqual"] == 1 for row in contracts))
        self.assertTrue(all(row["retryAllowed"] is False for row in contracts))

    def test_duplicate_search_and_attempt1_run_context(self):
        prereg = committed_preregistration()
        title = "future-wave1-title-with-no-allocated-identity"
        passed = m.duplicate_run_audit(prereg, title, [{"id": 1, "display_title": "different"}], ROOT)
        self.assertEqual(passed["status"], "PASSED_NO_DUPLICATE")
        m.validate_run_context({"event": "workflow_dispatch", "run_attempt": 1}, passed)
        refused = m.duplicate_run_audit(prereg, title, [{"id": 2, "display_title": title}], ROOT)
        self.assertEqual(refused["status"], "REFUSED_DUPLICATE")
        with self.assertRaisesRegex(m.Refusal, "duplicate-run refusal"):
            m.validate_run_context({"event": "workflow_dispatch", "run_attempt": 1}, refused)
        for run in ({"event": "workflow_dispatch", "run_attempt": 2}, {"event": "push", "run_attempt": 1}):
            with self.subTest(run=run), self.assertRaisesRegex(m.Refusal, "attempt 1"):
                m.validate_run_context(run, passed)

    def test_duplicate_metadata_malformed_and_audit_hash_drift_are_refused(self):
        prereg = committed_preregistration()
        with self.assertRaisesRegex(m.Refusal, "metadata malformed"):
            m.duplicate_run_audit(prereg, "future", [{"id": 1}], ROOT)
        passed = m.duplicate_run_audit(prereg, "future", [], ROOT)
        passed["searchedRunCount"] = 1
        with self.assertRaisesRegex(m.Refusal, "audit hash changed"):
            m.validate_run_context({"event": "workflow_dispatch", "run_attempt": 1}, passed)

    def test_complete_wave_aggregate_audit_and_analysis_are_bound(self):
        prereg = committed_preregistration()
        results = fake_results(prereg)
        aggregate = m.aggregate_wave1(prereg, results, ROOT)
        self.assertEqual(aggregate["aggregate"]["status"], "COMPLETED")
        self.assertEqual(aggregate["aggregate"]["caseCountObserved"], 40)
        audit = m.audit_wave1(prereg, results, aggregate, ROOT)
        self.assertEqual(audit["audit"]["status"], "PASSED")
        self.assertTrue(audit["independentlyRecomputedFromRawSelectedNodeRadiance"])
        analysis = m.analyze_wave1(prereg, aggregate, audit, ROOT)
        self.assertEqual(analysis["analysis"]["status"], "CONTINUATION_ANALYZED")
        self.assertFalse(analysis["additionalExecutionAutomaticallyAuthorized"])
        zero = next(row for row in analysis["analysis"]["points"] if row["geometryId"] == "train-0047")
        self.assertEqual(zero["classification"], "ADAPTIVE_CONTINUATION_REQUIRED")
        self.assertIsNone(zero["relativeStandardErrorOfMean"])
        self.assertFalse(zero["scientificallyEligible"])

    def test_valid_new_zero_hit_is_preserved_and_raw_recomputed(self):
        prereg = committed_preregistration()
        results = fake_results(
            prereg,
            lambda case: 0.0 if case["groupId"] == "train-0047" and case["block"] == 3 else 1.0,
        )
        aggregate = m.aggregate_wave1(prereg, results, ROOT)
        self.assertEqual(len(aggregate["aggregate"]["zeroHitDiagnostics"]), 1)
        audit = m.audit_wave1(prereg, results, aggregate, ROOT)
        self.assertEqual(audit["audit"]["status"], "PASSED")
        self.assertEqual(len(audit["audit"]["zeroHitDiagnostics"]), 1)
        analysis = m.analyze_wave1(prereg, aggregate, audit, ROOT)
        zero = next(row for row in analysis["analysis"]["points"] if row["geometryId"] == "train-0047")
        self.assertEqual(zero["relativeStandardErrorStatus"], "NOT_COMPUTED_ZERO_HIT_PRESENT")

    def test_partial_duplicate_hash_drift_and_nonfinite_results_fail_closed(self):
        prereg = committed_preregistration()
        clean = fake_results(prereg)
        variants = []
        variants.append(clean[:-1])
        duplicate = copy.deepcopy(clean)
        duplicate.append(copy.deepcopy(duplicate[0]))
        variants.append(duplicate)
        bad_hash = copy.deepcopy(clean)
        bad_hash[0]["artifactSha256"] = "bad"
        variants.append(bad_hash)
        nonfinite = copy.deepcopy(clean)
        nonfinite[0]["selectedNodeRadiance"][0] = math.inf
        variants.append(nonfinite)
        wrong_count = copy.deepcopy(clean)
        wrong_count[0]["solverExecutionCount"] = 2
        variants.append(wrong_count)
        for index, rows in enumerate(variants):
            with self.subTest(index=index):
                aggregate = m.aggregate_wave1(prereg, rows, ROOT)
                self.assertEqual(aggregate["aggregate"]["status"], "FAILED")
                self.assertEqual(aggregate["aggregate"]["classification"], "STRUCTURAL_OR_EXECUTION_FAILURE")

    def test_audit_refuses_reported_value_or_wrapper_hash_drift(self):
        prereg = committed_preregistration()
        clean = fake_results(prereg)
        aggregate = m.aggregate_wave1(prereg, clean, ROOT)
        changed = copy.deepcopy(aggregate)
        changed["aggregate"]["caseCountObserved"] = 39
        with self.assertRaisesRegex(m.Refusal, "wrapper hash changed"):
            m.audit_wave1(prereg, clean, changed, ROOT)
        reported = copy.deepcopy(clean)
        reported[0]["valueCdM2"] *= 2.0
        aggregate = m.aggregate_wave1(prereg, reported, ROOT)
        audit = m.audit_wave1(prereg, reported, aggregate, ROOT)
        self.assertEqual(audit["audit"]["status"], "FAILED")
        self.assertIn("reported-estimator-differs-from-raw-spectrum", {row["code"] for row in audit["audit"]["failures"]})

    def test_workflow_has_no_dispatch_or_scientific_execution_surface(self):
        text = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("pull_request:", text)
        self.assertNotIn("workflow_dispatch:", text)
        self.assertNotIn("repository_dispatch:", text)
        self.assertNotIn("scientific_case_executor.py", text)
        self.assertNotIn("uvspec", text)


if __name__ == "__main__":
    unittest.main()
