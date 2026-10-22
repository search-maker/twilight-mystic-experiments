from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ContinuationSourceGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.guard = load(
            cls.root / "modeling/surrogate-training-v2/continuation_source_guard.py",
            "surrogate_training_v2_continuation_source_guard_test",
        )

    def values(self):
        g = self.guard
        run = {
            "id": g.SOURCE_RUN_ID,
            "status": "completed",
            "conclusion": "success",
            "event": "push",
            "run_attempt": 1,
            "display_title": g.SOURCE_TITLE,
            "head_branch": g.SOURCE_BRANCH,
            "head_sha": g.SOURCE_AUTHORIZATION_REF,
        }
        names = ["tier1-wave2-ordinal12-execution-manifest"]
        names += [f"tier1-wave2-ordinal12-case-case-{index:02d}" for index in range(32)]
        names += [
            "tier1-wave2-ordinal12-aggregate",
            "tier1-wave2-ordinal12-audit",
            "tier1-wave2-ordinal12-analysis",
        ]
        artifacts = {
            "artifacts": [
                {
                    "id": 1000 + index,
                    "name": name,
                    "expired": False,
                    "digest": "sha256:" + f"{index + 1:064x}"[-64:],
                }
                for index, name in enumerate(names)
            ]
        }
        cases = [
            {
                "caseId": f"case-{index:02d}",
                "seed": 2000 + index,
                "block": 5 if index < 16 else 6,
            }
            for index in range(32)
        ]
        manifest = {
            "schemaVersion": 1,
            "stageId": "tier1-precision-continuation-wave2-ordinal12-execution-v1",
            "status": "AUTHORIZED_FOR_ONE_ATTEMPT1_EXECUTION",
            "displayTitle": g.SOURCE_TITLE,
            "authorizationRef": g.SOURCE_AUTHORIZATION_REF,
            "authorizationOrdinal": g.SOURCE_AUTHORIZATION_ORDINAL,
            "executionKey": g.SOURCE_EXECUTION_KEY,
            "runId": g.SOURCE_RUN_ID,
            "runAttempt": 1,
            "eventName": "push",
            "triggerBranch": g.SOURCE_BRANCH,
            "headBranch": "main",
            "headSha": g.SOURCE_MAIN_SHA,
            "blocks": [5, 6],
            "wave": 2,
            "geometryCount": 16,
            "caseCount": 32,
            "maximumConfiguredPhotonHistories": 4_600_000_000,
            "githubRerunAllowed": False,
            "retryAllowed": False,
            "resumeAllowed": False,
            "automaticNextWave": False,
            "surrogateTrainingAuthorized": False,
            "internalHoldoutOpeningAuthorized": False,
            "tier2Authorized": False,
            "productionPromotionAuthorized": False,
            "sourceBindings": {"preregistrationSha256": g.SOURCE_PREREGISTRATION_SHA256},
            "seedProof": {"wave2SeedsSha256": g.SOURCE_SEEDS_SHA256},
            "duplicateRunAudit": {"status": "NO_PRIOR_MATCHING_RUN", "matchingRuns": []},
            "cases": cases,
        }
        manifest["manifestSha256"] = g.canonical_sha256(manifest)
        aggregate_inner = {
            "status": "COMPLETED",
            "classification": "CONTINUATION_WAVE_EXECUTION_COMPLETE",
            "executionComplete": True,
            "caseCountPlanned": 32,
            "caseCountObserved": 32,
            "configuredPhotonHistories": 4_600_000_000,
            "executionFailures": [],
            "structuralFailures": [],
            "additionalExecutionAutomaticallyAuthorized": False,
        }
        aggregate = {
            "schemaVersion": 1,
            "stageId": "tier1-precision-continuation-wave2-aggregate-v1",
            "aggregate": aggregate_inner,
            "aggregateSha256": g.canonical_sha256(aggregate_inner),
        }
        aggregate["payloadSha256"] = g.canonical_sha256(aggregate)
        audit_inner = {
            "status": "PASSED",
            "caseResultCount": 32,
            "failures": [],
            "independentlyRecomputedFromRawSelectedNodeRadiance": True,
            "additionalExecutionAutomaticallyAuthorized": False,
        }
        audit = {
            "schemaVersion": 1,
            "stageId": "tier1-precision-continuation-wave2-independent-audit-v1",
            "aggregateSha256": aggregate["aggregateSha256"],
            "audit": audit_inner,
            "auditSha256": g.canonical_sha256(audit_inner),
        }
        audit["payloadSha256"] = g.canonical_sha256(audit)
        points = [
            {
                "geometryId": f"train-{index:04d}",
                "blockCount": 6,
                "classification": "PRECISION_TARGET_MET",
                "scientificallyEligible": True,
            }
            for index in range(1, 21)
        ]
        analysis = {
            "schemaVersion": 1,
            "stageId": "tier1-precision-continuation-wave2-analysis-v1",
            "wave2AggregateSha256": aggregate["aggregateSha256"],
            "wave2AuditSha256": audit["auditSha256"],
            "analysis": {
                "status": "CONTINUATION_ANALYZED",
                "points": points,
                "nextWaveGeometryIds": [],
                "exhaustedGeometryIds": [],
                "scientificallyEligible": True,
            },
            "additionalExecutionAutomaticallyAuthorized": False,
            "surrogateFitAuthorized": False,
            "internalHoldoutOpened": False,
            "tier2Authorized": False,
            "productionPromotionAuthorized": False,
        }
        analysis["analysisSha256"] = g.canonical_sha256(analysis)
        return run, artifacts, manifest, aggregate, audit, analysis

    def test_accepts_exact_terminal_source_without_authorizing_training(self):
        result = self.guard.validate(
            run=self.values()[0], artifacts=self.values()[1], manifest=self.values()[2],
            aggregate=self.values()[3], audit=self.values()[4], analysis=self.values()[5]
        )
        self.assertEqual(result["sourceArtifactCount"], 36)
        self.assertEqual(result["sourceCaseArtifactCount"], 32)
        self.assertEqual(result["nextWaveGeometryIds"], [])
        self.assertTrue(result["scientificallyEligible"])
        self.assertFalse(result["surrogateTrainingAuthorized"])
        self.assertFalse(result["internalHoldoutOpeningAuthorized"])

    def test_refuses_nonterminal_run(self):
        run, artifacts, manifest, aggregate, audit, analysis = self.values()
        run["status"] = "in_progress"
        with self.assertRaisesRegex(Exception, "source run boundary changed"):
            self.guard.validate(run=run, artifacts=artifacts, manifest=manifest, aggregate=aggregate, audit=audit, analysis=analysis)

    def test_refuses_missing_case_artifact(self):
        run, artifacts, manifest, aggregate, audit, analysis = self.values()
        artifacts["artifacts"].pop()
        with self.assertRaisesRegex(Exception, "exactly 36"):
            self.guard.validate(run=run, artifacts=artifacts, manifest=manifest, aggregate=aggregate, audit=audit, analysis=analysis)

    def test_refuses_manifest_tamper(self):
        run, artifacts, manifest, aggregate, audit, analysis = self.values()
        manifest["caseCount"] = 31
        with self.assertRaisesRegex(Exception, "self-hash changed"):
            self.guard.validate(run=run, artifacts=artifacts, manifest=manifest, aggregate=aggregate, audit=audit, analysis=analysis)

    def test_refuses_analysis_hash_or_audit_binding_tamper(self):
        run, artifacts, manifest, aggregate, audit, analysis = self.values()
        analysis["wave2AuditSha256"] = "f" * 64
        analysis["analysisSha256"] = self.guard.canonical_sha256(
            {key: value for key, value in analysis.items() if key != "analysisSha256"}
        )
        with self.assertRaisesRegex(Exception, "two-wave analysis boundary changed"):
            self.guard.validate(run=run, artifacts=artifacts, manifest=manifest, aggregate=aggregate, audit=audit, analysis=analysis)


if __name__ == "__main__":
    unittest.main()
