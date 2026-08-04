from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "experiments" / "mystic-batch-v1"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


AUDIT = load_module(
    "tier1_ordinal1_audit", BASE / "twilight_surrogate_tier1_ordinal1_audit.py"
)
RECOVERY = load_module(
    "tier1_ordinal2_recovery", BASE / "twilight_surrogate_tier1_ordinal2_recovery.py"
)
PROBE = load_module(
    "tier1_solver_probe", BASE / "twilight_surrogate_tier1_runtime_solver_probe.py"
)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def manifest_fixture() -> dict:
    geometries = [
        {
            "geometryId": f"train-{i:04d}",
            "observerElevationM": 357.143 if i == 1 else 0.0,
        }
        for i in range(1, 49)
    ]
    training = [row["geometryId"] for row in geometries[:39]]
    holdout = [row["geometryId"] for row in geometries[39:]]
    photons = [70_000_000] * 95 + [310_000_000]
    cases = []
    wavelengths = [500.0, 550.0, 600.0]
    ordinal = 0
    for geometry in geometries:
        for block in (1, 2):
            ordinal += 1
            gid = geometry["geometryId"]
            cases.append(
                {
                    "caseId": f"{gid}-alis-b{block}",
                    "groupId": gid,
                    "method": "alis",
                    "block": block,
                    "ordinal": ordinal,
                    "photonHistories": photons[ordinal - 1],
                    "alisSpectralImportanceSamplingNm": wavelengths[
                        (ordinal - 1) % 3
                    ],
                    "role": (
                        "surrogate-training" if gid in training else "internal-holdout"
                    ),
                    "executionTierId": "tier-1-provisional",
                    "seed": 910_000 + ordinal,
                }
            )
    return {
        "schemaVersion": 1,
        "stageId": "twilight-surrogate-tier-1-execution-v1",
        "geometries": geometries,
        "cases": cases,
        "trainingGeometryIds": training,
        "internalHoldoutGeometryIds": holdout,
        "externalValidationAnchorIds": [f"a{i}" for i in range(1, 7)],
        "limits": {"maximumParallel": 8},
        "frozenInputs": {"wavelengthDomainNm": [380, 780]},
        "bindings": {"source": "abc"},
        "runtime": {
            "uvspecSha256": "a" * 64,
            "runtimeLockRawSha256": "b" * 64,
            "atmosphereSha256": "c" * 64,
        },
    }


def combined_proof_fixture(manifest: dict) -> dict:
    return {
        "schemaVersion": 1,
        "stageId": RECOVERY.COMBINED_PROOF_STAGE_ID,
        "status": RECOVERY.COMBINED_PROOF_STATUS,
        "proofPassed": True,
        "profileEquivalenceDecision": True,
        "opticalPropertyEquivalenceDecision": True,
        "deterministicControlDecision": True,
        "threeHeightStructuralProfileDecision": True,
        "mysticProbeDecision": True,
        "scientificExecution": False,
        "scientificDatasetProduced": False,
        "surrogateTrainingUsePermitted": False,
        "authorizationPermitted": False,
        "ordinal2ScientificDispatchPermitted": False,
        "githubRerunPermitted": False,
        "frozenTier1InvariantsChanged": False,
        "maximumPermittedMysticSolverExecutionCount": 1,
        "deterministicSolverExecutionCount": 6,
        "mysticSolverExecutionCount": 1,
        "candidateRepresentation": {
            "atmosphereFileRemainsProfileSource": True,
            "atmZGridBottomIsSiteAltitude": True,
            "originalAtmosphereLevelsAboveSitePreservedExactly": True,
            "explicitAltitudeForbidden": True,
            "mcElevationFileForbidden": True,
            "localSurfaceZoutKm": 0.0,
        },
        "mysticProbe": {
            "status": RECOVERY.MYSTIC_PROBE_STATUS,
            "passed": True,
            "siteAltitudeKm": 0.357143,
            "localSurfaceZoutKm": 0.0,
            "atmosphereStartsAtSiteAltitude": True,
            "surfaceMarkerObserved": True,
            "layersBelowSiteAltitudePresent": False,
            "explicitAltitudePresent": False,
            "mcElevationFilePresent": False,
            "altitudeRejectionObserved": False,
            "generatedFilesPreserved": False,
            "scientificDatasetProduced": False,
            "solverExecutionCount": 1,
            "mcPhotons": 1,
            "generatedFiles": [
                {"filename": "mc.rad.spc", "rawSha256": "d" * 64, "sizeBytes": 1}
            ],
            "spectralConfiguration": {
                "wavelengthDomainNm": [380.0, 780.0],
                "alisImportanceWavelengthNm": 550.0,
                "alisReferenceStrictlyInsideDomain": True,
                "matchesFrozenTier1Domain": True,
                "singleWavelengthEndpointCrashConfigurationUsed": False,
                "alisMarkerObserved": True,
            },
        },
        "runtime": {
            "uvspecSha256": manifest["runtime"]["uvspecSha256"],
            "runtimeLockRawSha256": manifest["runtime"]["runtimeLockRawSha256"],
            "atmosphereSha256": manifest["runtime"]["atmosphereSha256"],
        },
    }


class Tier1RecoveryTests(unittest.TestCase):
    def test_ordinal1_audit_accepts_exact_uniform_failure_and_rejects_science(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            preflight = root / "preflight"
            cases_root = root / "cases"
            preflight.mkdir()
            write_json(
                preflight / "plan.json",
                {
                    "caseCount": 96,
                    "configuredMcPhotonsSum": 6_960_000_000,
                    "authorizationOrdinal": 1,
                    "executionKey": "twilight-surrogate-tier-1-v1:numerical:1",
                },
            )
            write_json(preflight / "authorization-guard.json", {"status": "AUTHORIZED"})
            write_json(preflight / "duplicate-run-audit.json", {"status": "PASS"})
            photons = [70_000_000] * 95 + [310_000_000]
            for index in range(96):
                write_json(
                    cases_root / f"case-{index + 1:04d}" / "case-result.json",
                    {
                        "caseId": f"case-{index + 1:04d}",
                        "seed": 910_001 + index,
                        "photonHistories": photons[index],
                        "status": "FAILED",
                        "syntaxCheckCount": 1,
                        "solverExecutionCount": 1,
                        "syntax": {"exitCode": 0, "timedOut": False},
                        "solver": {"exitCode": 255, "timedOut": False},
                        "failure": {
                            "detail": {
                                "stdout": "",
                                "stderr": (
                                    "FATAL error: altitude grid does not contain level "
                                    f"{0.05102 * (index + 1):.6f}\n"
                                    "which has been specified as output altitude\n"
                                    "setup_sample_grid failed\n"
                                ),
                            }
                        },
                        "radianceOutputSha256": None,
                        "stdOutputSha256": None,
                        "selectedNodeRadiance": [],
                        "selectedPhotopicContributionCdM2": None,
                    },
                )
            aggregate = root / "aggregate.json"
            write_json(
                aggregate,
                {
                    "caseCountPlanned": 96,
                    "caseCountCompleted": 0,
                    "caseCountFailed": 96,
                    "configuredMcPhotonsSum": 6_960_000_000,
                    "completedConfiguredMcPhotonsSum": 0,
                    "syntaxCheckCount": 96,
                    "solverExecutionCount": 96,
                    "classification": "STRUCTURAL_OR_EXECUTION_FAILURE",
                    "status": "FAILED",
                },
            )
            prior = root / "audit.json"
            write_json(
                prior,
                {
                    "status": "FAILED",
                    "batchClassification": "STRUCTURAL_OR_EXECUTION_FAILURE",
                },
            )
            report = AUDIT.audit(preflight, cases_root, aggregate, prior)
            self.assertEqual(report["validScientificCaseResultCount"], 0)
            self.assertFalse(report["githubRerunPermitted"])
            bad_path = cases_root / "case-0001" / "case-result.json"
            bad = json.loads(bad_path.read_text())
            bad["radianceOutputSha256"] = "0" * 64
            write_json(bad_path, bad)
            with self.assertRaises(AUDIT.AuditError):
                AUDIT.audit(preflight, cases_root, aggregate, prior)

    def test_recovery_changes_only_all_seeds_and_binds_combined_proof(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = root / "manifest.json"
            ordinal1 = root / "ordinal1.json"
            combined = root / "combined.json"
            source = manifest_fixture()
            write_json(manifest, source)
            write_json(
                ordinal1,
                {
                    "status": "ORDINAL_1_UNIFORMLY_FAILED_BEFORE_SCIENTIFIC_RESULT",
                    "validScientificCaseResultCount": 0,
                    "authorizationConsumed": True,
                    "sourceAuthorizationOrdinal": 1,
                    "githubRerunPermitted": False,
                },
            )
            write_json(combined, combined_proof_fixture(source))
            recovered, report = RECOVERY.recover(manifest, ordinal1, combined)
            before = json.loads(manifest.read_text())
            self.assertEqual(
                report["executionKey"], "twilight-surrogate-tier-1-v1:numerical:2"
            )
            self.assertEqual(report["authorizationOrdinal"], 2)
            self.assertEqual(report["freshSeedCount"], 96)
            self.assertEqual(report["observerElevationRepresentation"], "atm_z_grid")
            self.assertFalse(report["authorizationPermitted"])
            self.assertFalse(report["ordinal2ScientificDispatchPermitted"])
            self.assertEqual(
                {c["seed"] for c in before["cases"]}
                & {c["seed"] for c in recovered["cases"]},
                set(),
            )
            self.assertEqual(len({c["seed"] for c in recovered["cases"]}), 96)
            for old, new in zip(before["cases"], recovered["cases"]):
                self.assertEqual(
                    {k for k in set(old) | set(new) if old.get(k) != new.get(k)},
                    {"seed"},
                )
            self.assertEqual(before["geometries"], recovered["geometries"])
            self.assertIn("combinedProofRawSha256", report)
            self.assertEqual(
                recovered["recovery"]["combinedAtmZGridProof"]["representation"],
                "atm_z_grid",
            )

            rejected = combined_proof_fixture(source)
            rejected["mysticProbe"]["explicitAltitudePresent"] = True
            write_json(combined, rejected)
            with self.assertRaises(RECOVERY.RecoveryError):
                RECOVERY.recover(manifest, ordinal1, combined)

            rejected = combined_proof_fixture(source)
            rejected["runtime"]["uvspecSha256"] = "e" * 64
            write_json(combined, rejected)
            with self.assertRaises(RECOVERY.RecoveryError):
                RECOVERY.recover(manifest, ordinal1, combined)

    def test_solver_probe_runs_one_fake_solver_and_deletes_numeric_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            data = root / "data"
            data.mkdir()
            atmosphere = data / "afglus.dat"
            solar = data / "atlas_plus_modtran"
            runtime_lock = root / "runtime-lock.json"
            atmosphere.write_text("atmosphere")
            solar.write_text("solar")
            runtime_lock.write_text("{}\n")
            fake = root / "uvspec"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "import pathlib,sys\n"
                "text=sys.stdin.read()\n"
                "base=[line.split(' ',1)[1] for line in text.splitlines() "
                "if line.startswith('mc_basename ')][0]\n"
                "pathlib.Path(base + '.rad.spc').write_text('not-scientific\\n')\n"
                "pathlib.Path(base + '.std.spc').write_text('not-scientific-std\\n')\n"
            )
            fake.chmod(0o755)
            out = root / "out"
            report = PROBE.probe(fake, data, atmosphere, solar, runtime_lock, out)
            self.assertTrue(report["accepted"])
            self.assertEqual(report["solverExecutionCount"], 1)
            self.assertEqual(report["mcPhotons"], 1)
            self.assertEqual(report["generatedOutputFileCount"], 2)
            self.assertFalse(report["generatedOutputFilesPreserved"])
            self.assertEqual(list(out.glob("mc*")), [])
            text = (out / "input-resolved.txt").read_text()
            self.assertEqual(text.count("altitude 0.357143"), 1)
            self.assertEqual(text.count("zout 0.000000"), 1)
            self.assertNotIn("zout 0.357143", text)


if __name__ == "__main__":
    unittest.main()
