from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXECUTION_PATH = ROOT / "experiments/tier1-precision-continuation-wave1-v2/execution.py"
ADAPTER_PATH = ROOT / "experiments/tier1-precision-continuation-wave1-v2/execution_adapter.py"
EXECUTOR_PATH = ROOT / "experiments/tier1-precision-continuation-wave1-v2/case_executor.py"
PILOT_PATH = ROOT / "experiments/mystic-batch-v1/manifest.cross-geometry-pilot.proposal.json"


def load(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


e = load("wave1_execution", EXECUTION_PATH)
a = load("wave1_execution_adapter", ADAPTER_PATH)
x = load("wave1_case_executor", EXECUTOR_PATH)


def auth():
    return {
        "authorizationOrdinal": 8,
        "executionKey": e.EXECUTION_KEY,
        "enabled": True,
        "solverExecutionAuthorized": True,
        "runAttempt": 1,
        "status": "AUTHORIZED_PENDING_SEPARATE_DISPATCH",
        "caseCount": 40,
        "blocks": [3, 4],
        "automaticDispatch": False,
        "githubRerunAllowed": False,
        "dispatch": False,
        "workflowDispatchEnabled": False,
        "preregistrationSha256": e.EXPECTED_PREREGISTRATION_SHA256,
    }


def context():
    return {
        "eventName": "workflow_dispatch",
        "runAttempt": 1,
        "displayTitle": e.RUN_TITLE,
        "authorizationRef": e.AUTHORIZATION_REF,
        "authorizationOrdinal": 8,
        "executionKey": e.EXECUTION_KEY,
        "headBranch": "main",
        "headSha": "6cf159de79ba9730c5d8482c167c49acb7de5c41",
        "runId": 999001,
    }


def runtime():
    return {
        key: str(index) * 64
        for index, key in enumerate(
            (
                "uvspecSha256",
                "uvspecHelpSha256",
                "libRadtranDataTreeSha256",
                "atmosphereSha256",
                "runtimeLockRawSha256",
            ),
            1,
        )
    }


def manifest():
    return e.build_manifest(
        ROOT,
        auth(),
        context(),
        [
            {
                "id": 999001,
                "display_title": e.RUN_TITLE,
                "status": "in_progress",
                "conclusion": None,
            }
        ],
        runtime(),
    )


def materialize_libradtran_inputs(data_dir: pathlib.Path) -> pathlib.Path:
    pilot = json.loads(PILOT_PATH.read_text(encoding="utf-8"))
    atmosphere_path = None
    for name, spec in pilot["frozenInputs"]["dataPaths"].items():
        if spec["root"] != "libRadtranData":
            continue
        path = data_dir / spec["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        if name == "atmosphere":
            atmosphere_path = path
            path.write_text(
                "120 1\n80 1\n50 1\n30 1\n20 1\n10 1\n5 1\n2 1\n1 1\n0 1\n",
                encoding="utf-8",
            )
        else:
            path.write_text("contract fixture\n", encoding="utf-8")
    if atmosphere_path is None:
        raise AssertionError("pilot atmosphere path was not materialized")
    return atmosphere_path


class ExecutionInfrastructureTests(unittest.TestCase):
    def test_01_manifest_is_exact_and_deterministic(self):
        first = manifest()
        second = manifest()
        self.assertEqual(e.dump(first), e.dump(second))
        self.assertEqual(40, first["caseCount"])
        self.assertEqual(20, first["geometryCount"])
        self.assertEqual(
            5_100_000_000,
            sum(c["photonHistories"] for c in first["cases"]),
        )
        self.assertEqual({3, 4}, {c["block"] for c in first["cases"]})
        self.assertEqual(40, len({c["seed"] for c in first["cases"]}))
        self.assertEqual([], first["seedProof"]["historicalOverlap"])
        roles = {
            role: {
                c["groupId"]
                for c in first["cases"]
                if c["role"] == role
            }
            for role in ("surrogate-training", "internal-holdout")
        }
        self.assertEqual(
            (17, 3),
            (
                len(roles["surrogate-training"]),
                len(roles["internal-holdout"]),
            ),
        )

    def test_02_duplicate_refusal_is_conclusion_independent(self):
        for conclusion in (None, "success", "failure", "cancelled"):
            with self.assertRaises(e.Refusal):
                e.duplicate_run_audit(
                    [
                        {
                            "id": 123,
                            "display_title": e.RUN_TITLE,
                            "status": "completed",
                            "conclusion": conclusion,
                        }
                    ],
                    999001,
                )
        self.assertEqual(
            "NO_PRIOR_MATCHING_RUN",
            e.duplicate_run_audit(
                [{"id": 999001, "display_title": e.RUN_TITLE}],
                999001,
            )["status"],
        )
        with self.assertRaises(e.Refusal):
            e.duplicate_run_audit(["malformed"], 999001)

    def test_03_authorization_context_and_budget_drift_refused(self):
        prereg = e.load_json(ROOT / e.PREREGISTRATION_PATH)
        for key, value in (
            ("authorizationOrdinal", 9),
            ("executionKey", "reused"),
            ("enabled", False),
            ("githubRerunAllowed", True),
        ):
            candidate = auth()
            candidate[key] = value
            with self.assertRaises(e.Refusal):
                e.validate_authorization(candidate, prereg)
        for key, value in (
            ("runAttempt", 2),
            ("eventName", "push"),
            ("headBranch", "feature"),
        ):
            candidate = context()
            candidate[key] = value
            with self.assertRaises(e.Refusal):
                e.validate_context(candidate)

    def test_04_partial_malformed_hash_drift_and_nonfinite_refused(self):
        value = manifest()
        base = []
        for case in value["cases"]:
            result = {
                "status": "COMPLETED",
                "caseId": case["caseId"],
                "role": case["role"],
                "seed": case["seed"],
                "selectedNodeRadiance": [0.0] * 15,
                "syntaxCheckCount": 1,
                "solverExecutionCount": 1,
            }
            result["contentSha256"] = e.canonical_sha256(result)
            base.append(result)
        e.validate_result_set(value, base)
        for mutate in (
            lambda values: values[:-1],
            lambda values: [
                {**values[0], "selectedNodeRadiance": [float("inf")] * 15},
                *values[1:],
            ],
            lambda values: [
                {**values[0], "contentSha256": "0" * 64},
                *values[1:],
            ],
        ):
            with self.assertRaises(e.Refusal):
                e.validate_result_set(value, mutate(copy.deepcopy(base)))

    def test_05_zero_spectrum_is_preserved_and_nonfinite_refused(self):
        with tempfile.TemporaryDirectory() as td:
            path = pathlib.Path(td) / "mc.rad.spc"
            path.write_text(
                "\n".join(f"{node} 0" for node in x.NODES) + "\n"
            )
            self.assertEqual([0.0] * 15, x.parse_spectrum(path))
            path.write_text(
                "\n".join(
                    f"{node} {'nan' if node == 470 else 0}"
                    for node in x.NODES
                )
                + "\n"
            )
            with self.assertRaises(x.ExecutionRefusal):
                x.parse_spectrum(path)

    def test_06_workflows_are_manual_attempt1_and_closed(self):
        scientific = (
            ROOT
            / ".github/workflows/tier1-precision-continuation-wave1-ordinal8-execution.yml"
        ).read_text()
        contract = (
            ROOT
            / ".github/workflows/tier1-precision-continuation-wave1-ordinal8-execution-contract.yml"
        ).read_text()
        self.assertIn("workflow_dispatch:", scientific)
        self.assertNotIn("schedule:", scientific)
        self.assertNotIn("repository_dispatch:", scientific)
        self.assertIn("GITHUB_RUN_ATTEMPT", scientific)
        self.assertIn(e.AUTHORIZATION_REF, scientific)
        self.assertIn(
            "Duplicate search before any syntax or solver execution",
            scientific,
        )
        self.assertIn("fail-fast: false", scientific)
        self.assertIn("cancel-in-progress: false", scientific)
        self.assertNotIn("gh run rerun", scientific.lower())
        self.assertNotIn("workflow_dispatch:", contract)
        self.assertIn("execution-contract", contract)

    def test_07_real_wave1_case_uses_reviewed_atm_z_grid(self):
        value = manifest()
        case = next(
            case
            for case in value["cases"]
            if float(case["geometry"]["observerElevationM"]) > 0.0
        )
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            data_dir = root / "data"
            materialize_libradtran_inputs(data_dir)
            manifest_path = root / "execution-manifest.json"
            runtime_path = root / "runtime-report.json"
            manifest_path.write_text(e.dump(value), encoding="utf-8")
            runtime_path.write_text(e.dump(runtime()), encoding="utf-8")
            prepared = a.prepare_case(
                manifest_path,
                runtime_path,
                case["caseId"],
                data_dir,
                ROOT,
                root / "output",
            )
            resolved = pathlib.Path(prepared["inputPath"]).read_text(
                encoding="utf-8"
            )
            lines = [line.strip() for line in resolved.splitlines()]
            grid_lines = [
                line for line in lines if line.startswith("atm_z_grid ")
            ]
            self.assertEqual(1, len(grid_lines))
            self.assertEqual(1, lines.count("zout 0.000000"))
            self.assertFalse(
                any(
                    line.startswith("altitude ")
                    or line.startswith("mc_elevation_file ")
                    for line in lines
                )
            )
            grid = [float(value) for value in grid_lines[0].split()[1:]]
            self.assertAlmostEqual(
                float(case["geometry"]["observerElevationM"]) / 1000.0,
                grid[0],
                places=6,
            )
            self.assertTrue(
                all(grid[index] < grid[index + 1] for index in range(len(grid) - 1))
            )
            self.assertEqual("atm_z_grid", prepared["observerElevationMechanism"])
            self.assertEqual(0.0, prepared["zoutKmAboveLocalSurface"])
            self.assertEqual(len(grid), prepared["atmosphereGridLevelCount"])

    def test_08_elevation_input_refusals_are_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            atmosphere = root / "atmosphere.dat"
            atmosphere.write_text("10 1\n5 1\n0 1\n", encoding="utf-8")
            prefix = f"atmosphere_file {atmosphere.resolve()}\n"
            for rendered in (
                prefix,
                prefix + "zout 1.000000\nzout 1.000000\n",
                prefix + "altitude 1.000000\nzout 1.000000\n",
                prefix + "mc_elevation_file site.dat\nzout 1.000000\n",
            ):
                with self.assertRaises(a.AdapterRefusal):
                    a.apply_ground_site_atm_z_grid(rendered, 1000.0, ROOT)
            atmosphere.write_text("10 1\n5 1\n6 1\n0 1\n", encoding="utf-8")
            with self.assertRaises(a.AdapterRefusal):
                a.apply_ground_site_atm_z_grid(
                    prefix + "zout 1.000000\n",
                    1000.0,
                    ROOT,
                )
            atmosphere.write_text("10\n0 1\n", encoding="utf-8")
            with self.assertRaises(a.AdapterRefusal):
                a.apply_ground_site_atm_z_grid(
                    prefix + "zout 1.000000\n",
                    1000.0,
                    ROOT,
                )


def emit_contract(output: pathlib.Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    value = manifest()
    (output / "execution-manifest.json").write_text(
        e.dump(value),
        encoding="utf-8",
        newline="\n",
    )
    summary = {
        "schemaVersion": 1,
        "stageId": e.STAGE_ID,
        "caseCount": 40,
        "geometryCount": 20,
        "configuredPhotonHistories": sum(
            c["photonHistories"] for c in value["cases"]
        ),
        "manifestSha256": value["manifestSha256"],
        "seedProof": value["seedProof"],
        "scientificSolverExecuted": False,
    }
    (output / "contract-summary.json").write_text(
        e.dump(summary),
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--emit-contract", type=pathlib.Path)
    args, remaining = parser.parse_known_args()
    if args.emit_contract:
        emit_contract(args.emit_contract)
    else:
        unittest.main(argv=[__file__, *remaining])
