import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = (
    Path(__file__).parents[1]
    / "experiments"
    / "tier1-precision-continuation-wave1-v2"
    / "ordinal8_review.py"
)
spec = importlib.util.spec_from_file_location("ordinal8_review", MODULE_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def write(path: Path, value: dict) -> str:
    path.write_text(json.dumps(value, sort_keys=True) + "\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def preregistration() -> dict:
    cases = []
    for index in range(20):
        role = "internal-holdout" if index >= 17 else "surrogate-training"
        for block in (3, 4):
            cases.append(
                {
                    "caseId": f"g{index}-b{block}",
                    "groupId": f"g{index}",
                    "block": block,
                    "seed": 1000 + len(cases),
                    "role": role,
                    "photonHistories": 100_000_000,
                    "proposalOnly": True,
                }
            )
    cases[-1]["photonHistories"] = 1_200_000_000
    return {
        "authorizationEnabled": False,
        "authorizationOrdinal": None,
        "authorizationRef": None,
        "executionKey": None,
        "dispatchEnabled": False,
        "workflowDispatchEnabled": False,
        "scientificExecution": False,
        "proposalOnly": True,
        "blocks": [3, 4],
        "caseCount": 40,
        "geometryCount": 20,
        "maximumConfiguredPhotonHistories": 5_100_000_000,
        "roleCounts": {
            "internalHoldoutCases": 6,
            "internalHoldoutGeometries": 3,
            "surrogateTrainingCases": 34,
            "surrogateTrainingGeometries": 17,
        },
        "preservation": {
            key: True
            for key in (
                "evidenceBindingsUnchanged",
                "geometryInputsUnchanged",
                "historicalArtifactsImmutable",
                "originalBlocksB1B2Preserved",
                "photonScheduleUnchanged",
                "rolesUnchanged",
                "thresholdsUnchanged",
                "zeroHitHandlingUnchanged",
            )
        },
        "seedProof": {
            "allWave1SeedsUnique": True,
            "historicalOverlap": [],
            "historicalSeedCount": 196,
            "wave1SeedCount": 40,
        },
        "cases": cases,
    }


def authorization_template() -> dict:
    return {
        "enabled": False,
        "dispatch": False,
        "automaticDispatch": False,
        "workflowDispatchEnabled": False,
        "solverExecutionAuthorized": False,
        "githubRerunAllowed": False,
        "authorizationOrdinal": None,
        "authorizationRef": None,
        "authorizationCommit": None,
        "executionKey": None,
    }


def snapshot() -> dict:
    return {
        "status": "REVIEW_ONLY_SNAPSHOT",
        "ordinalScope": "REPOSITORY_GLOBAL_SINGLE_USE",
        "candidateSearchComplete": True,
        "candidateIdentity": module.CANDIDATE,
        "checkedDimensions": sorted(module.DIMS),
        "consumedIdentityInventory": module.CONSUMED_IDENTITIES,
        "findings": {
            "candidateOrdinalCollisions": [],
            "candidateExecutionKeyCollisions": [],
            "authorizationRefCollisions": [],
            "runTitleCollisions": [],
            "branchPathCollisions": [],
            "authorizationFilePathCollisions": [],
            "wave1SeedCollisions": [],
        },
        "sources": [],
    }


class CandidateOrdinal8ReviewTests(unittest.TestCase):
    def run_build(self, prereg_mutator=None, template_mutator=None, snapshot_mutator=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prereg = preregistration()
            template = authorization_template()
            review_snapshot = snapshot()
            if prereg_mutator:
                prereg_mutator(prereg)
            if template_mutator:
                template_mutator(template)
            if snapshot_mutator:
                snapshot_mutator(review_snapshot)
            prereg_path = root / "preregistration.json"
            template_path = root / "template.json"
            snapshot_path = root / "snapshot.json"
            prereg_sha = write(prereg_path, prereg)
            template_sha = write(template_path, template)
            write(snapshot_path, review_snapshot)
            return module.build(
                prereg_path,
                template_path,
                snapshot_path,
                prereg_sha,
                template_sha,
            )

    def test_candidate_packet_remains_unallocated(self):
        packet = self.run_build()
        self.assertEqual(packet["status"], "CANDIDATE_NO_COLLISION_FOUND_REVIEW_ONLY")
        self.assertEqual(packet["candidateIdentity"]["authorizationOrdinal"], 8)
        self.assertEqual(packet["candidateIdentity"]["status"], "UNALLOCATED_REVIEW_ONLY")
        self.assertFalse(packet["candidateDecision"]["allocated"])
        self.assertFalse(packet["candidateDecision"]["reserved"])
        self.assertEqual(
            [item["authorizationOrdinal"] for item in packet["consumedIdentityInventory"]],
            list(range(1, 8)),
        )
        self.assertIsNone(packet["authoritativeIdentity"]["authorizationOrdinal"])
        self.assertIsNone(packet["authoritativeIdentity"]["executionKey"])
        self.assertIsNone(packet["authoritativeIdentity"]["authorizationRef"])

    def test_candidate_collision_refuses(self):
        with self.assertRaisesRegex(module.Refusal, "candidate ordinal collision"):
            self.run_build(
                snapshot_mutator=lambda value: value["findings"].update(
                    candidateOrdinalCollisions=[{"authorizationOrdinal": 8, "runId": 1}]
                )
            )

    def test_incomplete_consumed_inventory_refuses(self):
        with self.assertRaisesRegex(module.Refusal, "consumed identity inventory"):
            self.run_build(
                snapshot_mutator=lambda value: value.update(
                    consumedIdentityInventory=value["consumedIdentityInventory"][:-1]
                )
            )

    def test_duplicate_seed_refuses(self):
        with self.assertRaisesRegex(module.Refusal, "case/seed universe"):
            self.run_build(
                prereg_mutator=lambda value: value["cases"][1].update(
                    seed=value["cases"][0]["seed"]
                )
            )

    def test_open_template_refuses(self):
        with self.assertRaisesRegex(module.Refusal, "boundary opened"):
            self.run_build(template_mutator=lambda value: value.update(enabled=True))

    def test_search_incomplete_refuses(self):
        with self.assertRaisesRegex(module.Refusal, "candidate search not complete"):
            self.run_build(snapshot_mutator=lambda value: value.update(candidateSearchComplete=False))


if __name__ == "__main__":
    unittest.main()
