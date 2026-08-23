from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "experiments/aerosol-full-phase-function-sensitivity-v1"
TRANSPORT_PATH = STAGE / "execution_transport.py"
ADAPTER_PATH = STAGE / "adapter.py"
EXECUTOR_PATH = STAGE / "execution-candidate/executor.py"
AGGREGATE_PATH = STAGE / "execution-candidate/aggregate_results.py"
OVERLAY_PATH = STAGE / "execution-candidate/runtime_overlay.py"
CONTRACT_PATH = STAGE / "execution-contract.review.json"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def review_seed_map(group_ids: list[str]) -> dict[str, int]:
    """Deterministic test-only values, not a persisted candidate-seed ledger."""
    used: set[int] = set()
    out: dict[str, int] = {}
    modulus = 2_147_483_646
    for group_id in sorted(group_ids):
        raw = int.from_bytes(hashlib.sha256(("transport-review-fixture|" + group_id).encode()).digest()[:8], "big")
        value = raw % modulus + 1
        while value in used:
            value = value % modulus + 1
        used.add(value)
        out[group_id] = value
    return out


class AerosolFullPhaseFunctionExecutionTransportV1Tests(unittest.TestCase):
    def test_seedless_transport_design_is_exact_and_nonrenderable(self) -> None:
        transport = load_module("afpf_transport_test", TRANSPORT_PATH)
        design = transport.build_seedless_transport_design()
        self.assertEqual(design["status"], "REVIEW_ONLY_EXECUTION_TRANSPORT_NON_RENDERABLE_NO_SEEDS")
        self.assertEqual(design["analysisCellCount"], 24)
        self.assertEqual(design["groupCount"], 72)
        self.assertEqual(design["caseCount"], 360)
        self.assertEqual(design["statesPerGroup"], 5)
        self.assertEqual(design["configuredPhotonHistories"], 7_200_000_000)
        self.assertIs(design["candidateSeedsAllocated"], False)
        self.assertIs(design["candidateSeedFreshnessProven"], False)
        self.assertTrue(all(row["seed"] is None for row in design["groups"]))
        self.assertTrue(all(row["seed"] is None for row in design["cases"]))
        self.assertTrue(all(row["renderable"] is False for row in design["cases"]))
        self.assertTrue(all(row["executionAuthorized"] is False for row in design["cases"]))
        state_ids = {
            "native-rural-ss",
            "opac-continental-average",
            "opac-maritime-clean",
            "opac-desert",
            "opac-desert-spheroids",
        }
        by_group: dict[str, list[dict]] = {}
        for row in design["cases"]:
            by_group.setdefault(row["groupId"], []).append(row)
        self.assertEqual(len(by_group), 72)
        for members in by_group.values():
            self.assertEqual(len(members), 5)
            self.assertEqual({row["stateId"] for row in members}, state_ids)
            self.assertEqual({row["augmentedDataTreeSha256"] for row in members}, {
                "5d8bbf8e6b91ec3d405dee36f21a94afbb6e5ec6cd67da2dd5dd541738199d80"
            })

    def test_future_seed_binding_does_not_claim_freshness_or_authorization(self) -> None:
        transport = load_module("afpf_transport_seed_test", TRANSPORT_PATH)
        seedless = transport.build_seedless_transport_design()
        seed_map = review_seed_map([row["groupId"] for row in seedless["groups"]])
        bound = transport.bind_unproven_candidate_seed_map(seed_map)
        self.assertEqual(bound["status"], "REVIEW_ONLY_CANDIDATE_SEEDS_BOUND_FRESHNESS_NOT_PROVEN_NON_RENDERABLE")
        self.assertIs(bound["candidateSeedsAllocated"], True)
        self.assertIs(bound["candidateSeedFreshnessProven"], False)
        self.assertIs(bound["scientificExecutionAuthorized"], False)
        self.assertEqual(len({row["seed"] for row in bound["groups"]}), 72)
        by_group: dict[str, list[dict]] = {}
        for row in bound["cases"]:
            by_group.setdefault(row["groupId"], []).append(row)
            self.assertIs(row["renderable"], False)
            self.assertIs(row["executionAuthorized"], False)
            self.assertEqual(row["seedStatus"], "CANDIDATE_BOUND_FRESHNESS_NOT_YET_PROVEN")
        for members in by_group.values():
            self.assertEqual(len({row["seed"] for row in members}), 1)

    def test_future_fresh_design_validator_requires_proof_state_and_canonical_hash(self) -> None:
        transport = load_module("afpf_transport_future_test", TRANSPORT_PATH)
        seedless = transport.build_seedless_transport_design()
        seed_map = review_seed_map([row["groupId"] for row in seedless["groups"]])
        future = transport.bind_unproven_candidate_seed_map(seed_map)
        future["status"] = "CANDIDATE_SEEDED_DESIGN_FRESHNESS_PROVEN_REVIEW_ONLY"
        future["candidateSeedFreshnessProven"] = True
        future["authorizationTimeSeedRecheckRequired"] = True
        for row in future["groups"]:
            row["seedStatus"] = "CANDIDATE_FRESHNESS_PROVEN_REVIEW_ONLY"
        for row in future["cases"]:
            row["seedStatus"] = "CANDIDATE_FRESHNESS_PROVEN_REVIEW_ONLY"
        future.pop("canonicalDesignSha256", None)
        future["canonicalDesignSha256"] = transport.canonical_sha256(future)
        transport.validate_future_fresh_seeded_design(future)
        tampered = copy.deepcopy(future)
        # The design is ordered in five-state blocks per CRN group; index 5 is the next group.
        tampered["cases"][0]["seed"] = tampered["cases"][5]["seed"]
        tampered.pop("canonicalDesignSha256", None)
        tampered["canonicalDesignSha256"] = transport.canonical_sha256(tampered)
        with self.assertRaises(transport.TransportRefusal):
            transport.validate_future_fresh_seeded_design(tampered)

    def test_seed_map_must_cover_all_groups_and_be_unique(self) -> None:
        transport = load_module("afpf_transport_bad_seed_test", TRANSPORT_PATH)
        seedless = transport.build_seedless_transport_design()
        seed_map = review_seed_map([row["groupId"] for row in seedless["groups"]])
        missing = dict(seed_map)
        missing.pop(next(iter(missing)))
        with self.assertRaisesRegex(transport.TransportRefusal, "exact 72-group"):
            transport.bind_unproven_candidate_seed_map(missing)
        duplicated = dict(seed_map)
        keys = list(duplicated)
        duplicated[keys[1]] = duplicated[keys[0]]
        with self.assertRaisesRegex(transport.TransportRefusal, "must be unique"):
            transport.bind_unproven_candidate_seed_map(duplicated)

    def test_adapter_renders_exact_five_state_surfaces_only_after_local_test_activation(self) -> None:
        transport = load_module("afpf_transport_render_test", TRANSPORT_PATH)
        adapter = load_module("afpf_adapter_transport_test", ADAPTER_PATH)
        design = transport.build_seedless_transport_design()
        first_group = design["groups"][0]["groupId"]
        cases = [row for row in design["cases"] if row["groupId"] == first_group]
        self.assertEqual(len(cases), 5)
        seed_map = review_seed_map([first_group])
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            for row in cases:
                active = {
                    **row,
                    "seed": seed_map[first_group],
                    "seedStatus": "TEST_ONLY_NOT_PERSISTED_CANDIDATE",
                    "renderable": True,
                    "executionAuthorized": True,
                }
                rendered = adapter.render_case_input(active, output / "data", ROOT, output / "out")
                adapter.assert_exact_aerosol_surface(rendered, active["stateId"], active["aod550"])
                self.assertNotIn("aerosol_modify", rendered)
                if active["stateId"] == "native-rural-ss":
                    self.assertNotIn("aerosol_species_library OPAC", rendered)
                else:
                    self.assertIn("aerosol_species_library OPAC", rendered)
                    self.assertIn(f"aerosol_species_file {active['opacMixture']}", rendered)

    def test_executor_refuses_before_touching_runtime_without_explicit_allow(self) -> None:
        executor = load_module("afpf_executor_refusal_test", EXECUTOR_PATH)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(executor.ExecutionRefusal, "allow_execution"):
                executor.execute_case(
                    ROOT,
                    root / "missing-design.json",
                    root / "missing-guard.json",
                    root / "missing-runtime.json",
                    "not-a-case",
                    root / "missing-data",
                    root / "out",
                    root / "missing-uvspec",
                    allow_execution=False,
                )

    def test_executor_and_aggregate_use_opac_metadata_not_aops_ssa_g_controls(self) -> None:
        executor_text = EXECUTOR_PATH.read_text()
        aggregate_text = AGGREGATE_PATH.read_text()
        for forbidden in ("ssaSet", "ggSet"):
            self.assertNotIn(forbidden, executor_text)
            self.assertNotIn(forbidden, aggregate_text)
        for required in ("aerosolKind", "opacMixture", "augmentedDataTreeSha256"):
            self.assertIn(required, executor_text)
            self.assertIn(required, aggregate_text)
        self.assertIn("COMPLETED_PREREGISTERED_AFPF_V1_ANALYSIS", aggregate_text)
        self.assertIn("COMPLETED_PREREGISTERED_AFPF_V1_SPECTRAL_ANALYSIS", aggregate_text)
        self.assertIn("contrastCountPerPrimaryChannelPerCell\": 7", aggregate_text)
        self.assertIn("desert_spheroids_vs_desert", aggregate_text)

    def test_contract_binds_exact_transport_sources_and_remains_no_seed_no_execution(self) -> None:
        contract = json.loads(CONTRACT_PATH.read_text())
        self.assertEqual(contract["status"], "FROZEN_REVIEW_ONLY_EXECUTION_TRANSPORT_NOT_AUTHORIZED")
        self.assertIs(contract["candidateSeedsAllocated"], False)
        self.assertIs(contract["scientificExecutionAuthorized"], False)
        self.assertIs(contract["solverExecutionAuthorized"], False)
        self.assertIs(contract["resultOpeningAuthorized"], False)
        self.assertEqual(contract["expectedCaseCount"], 360)
        self.assertEqual(contract["expectedGroupCount"], 72)
        self.assertEqual(contract["expectedAnalysisCellCount"], 24)
        self.assertEqual(contract["expectedStatesPerGroup"], 5)
        self.assertEqual(contract["expectedContrastCount"], 7)
        self.assertIs(contract["reviewBoundary"]["activeWorkflowAdded"], False)
        self.assertIs(contract["reviewBoundary"]["candidateSeedLedgerPresent"], False)
        bindings = contract["sourceBindings"]
        for path_key, blob_key in (
            ("protocolPath", "protocolGitBlobSha1"),
            ("analysisContractPath", "analysisContractGitBlobSha1"),
            ("reviewCorePath", "reviewCoreGitBlobSha1"),
            ("adapterPath", "adapterGitBlobSha1"),
            ("analysisPath", "analysisGitBlobSha1"),
            ("levelBAnalysisPath", "levelBAnalysisGitBlobSha1"),
            ("executionTransportPath", "executionTransportGitBlobSha1"),
            ("runtimeOverlayPath", "runtimeOverlayGitBlobSha1"),
            ("executorPath", "executorGitBlobSha1"),
            ("aggregatorPath", "aggregatorGitBlobSha1"),
            ("processGroupRunnerPath", "processGroupRunnerGitBlobSha1"),
            ("r8DerivedChannelsPath", "r8DerivedChannelsGitBlobSha1"),
            ("wavelengthGridPath", "wavelengthGridGitBlobSha1"),
        ):
            self.assertEqual(git_blob_sha1(ROOT / bindings[path_key]), bindings[blob_key], path_key)

    def test_overlay_transport_constants_match_contract_and_reject_nonfrozen_archive(self) -> None:
        overlay = load_module("afpf_overlay_transport_test", OVERLAY_PATH)
        contract = json.loads(CONTRACT_PATH.read_text())
        runtime = contract["runtimeIdentity"]
        self.assertEqual(overlay.EXPECTED_ARCHIVE_SHA256, runtime["officialOptpropArchiveSha256"])
        self.assertEqual(overlay.EXPECTED_ARCHIVE_SIZE, runtime["officialOptpropArchiveSizeBytes"])
        self.assertEqual(overlay.EXPECTED_BASE_DATA_TREE_SHA256, runtime["baseDataTreeSha256"])
        self.assertEqual(overlay.EXPECTED_AUGMENTED_DATA_TREE_SHA256, runtime["augmentedDataTreeSha256"])
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "not-frozen.tar.gz"
            bad.write_bytes(b"not the official optprop archive")
            with self.assertRaisesRegex(overlay.OverlayRefusal, "size drift"):
                overlay.validate_archive_members(bad)


if __name__ == "__main__":
    unittest.main()
