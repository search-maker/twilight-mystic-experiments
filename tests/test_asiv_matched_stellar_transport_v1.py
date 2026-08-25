from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "review/asiv-matched-stellar-transport-v1/execution_candidate.py"
PRECONTRACT = ROOT / "review/asiv-matched-stellar-transport-v1/PRECONTRACT.review.json"


def load_candidate():
    spec = importlib.util.spec_from_file_location("asiv_matched_stellar_candidate", CANDIDATE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AsivMatchedStellarTransportV1Tests(unittest.TestCase):
    def test_candidate_is_render_only_and_case_counts_are_frozen(self):
        mod = load_candidate()
        payload = mod.build_prefrozen_manifest()
        self.assertEqual(payload["status"], "PREFROZEN_RENDER_ONLY_NO_SOLVER_EXECUTION")
        self.assertEqual(payload["training"]["caseCount"], 2700)
        self.assertEqual(payload["training"]["casesPerFamily"], 675)
        self.assertEqual(payload["validation"]["atmosphericCaseCount"], 768)
        self.assertEqual(payload["validation"]["atmosphericCasesPerFamily"], 192)
        self.assertEqual(payload["validation"]["johnsonVComparisonCount"], 2304)
        self.assertEqual(payload["validation"]["johnsonVComparisonsPerFamily"], 576)
        self.assertEqual(payload["nativeComparator"], {
            "stateId": "native-rural-ss",
            "representation": "MYSTIC-STATE-0081 stellar-transport-v2",
            "rebuildAuthorized": False,
            "renderPathPresent": False,
        })
        self.assertEqual(payload["authorization"], {
            "solverExecutionAuthorized": False,
            "scientificExecutionAuthorized": False,
            "resultOpeningAuthorized": False,
            "pandoraHoldoutAccessAllowed": False,
            "starsvisibilityMutationAuthorized": False,
            "productionActivationAuthorized": False,
        })
        self.assertEqual(
            {row["family"] for row in payload["training"]["cases"]},
            set(mod.NON_NATIVE_FAMILIES),
        )
        self.assertEqual(
            {row["family"] for row in payload["validation"]["cases"]},
            set(mod.NON_NATIVE_FAMILIES),
        )
        self.assertTrue(all(row["solverExecutionAuthorized"] is False for row in payload["training"]["cases"]))
        self.assertTrue(all(row["solverExecutionAuthorized"] is False for row in payload["validation"]["cases"]))

    def test_validation_grid_is_fresh_relative_to_0081_v2_acceptance_axes(self):
        mod = load_candidate()
        old_alt = {
            5.333333, 7.333333, 9.333333, 12.333333, 14.333333, 18.333333,
            23.333333, 28.333333, 36.666667, 46.666667, 56.666667, 71.666667,
        }
        old_elev = {166.666667, 750, 1500, 2166.666667}
        old_aod = {0.066666667, 0.133333333, 0.233333333, 0.333333333}
        self.assertTrue(old_alt.isdisjoint(set(mod.VALIDATION_ALTITUDE_DEG)))
        self.assertTrue(old_elev.isdisjoint(set(mod.VALIDATION_ELEVATION_M)))
        self.assertTrue(old_aod.isdisjoint(set(mod.VALIDATION_AOD550)))
        self.assertTrue(set(mod.VALIDATION_ALTITUDE_DEG).isdisjoint(set(mod.ALTITUDE_KNOTS)))
        self.assertTrue(set(mod.VALIDATION_ELEVATION_M).isdisjoint(set(mod.ELEVATION_KNOTS_M)))
        self.assertTrue(set(mod.VALIDATION_AOD550).isdisjoint(set(mod.AOD_KNOTS)))

    def test_exact_asiv_opac_directive_surface(self):
        mod = load_candidate()
        expected = {
            "opac-continental-average": "continental_average",
            "opac-maritime-clean": "maritime_clean",
            "opac-desert": "desert",
            "opac-desert-spheroids": "desert_spheroids",
        }
        for family, species in expected.items():
            self.assertEqual(mod.aerosol_block(family, 0.2), [
                "aerosol_default",
                "aerosol_species_library OPAC",
                f"aerosol_species_file {species}",
                "aerosol_set_tau_at_wvl 550 0.20000000",
            ])
        with self.assertRaises(mod.CandidateRefusal):
            mod.aerosol_block("native-rural-ss", 0.2)

    def test_precontract_marks_native_directives_provenance_only(self):
        pre = json.loads(PRECONTRACT.read_text(encoding="utf-8"))
        directives = pre["exactAerosolDirectiveContract"]
        self.assertEqual(
            directives["nativeDirectiveStatus"],
            "PROVENANCE_ONLY_NOT_RENDERABLE_BY_THIS_EXTENSION",
        )
        self.assertIn("four OPAC family directives", directives["rule"])
        self.assertIn("must not be rendered or rebuilt", directives["rule"])
        self.assertEqual(
            pre["runtimeRepresentation"]["nativeStatePolicy"],
            "Do not rebuild, alter, or replace the accepted MYSTIC-STATE-0081 native LUT as part of the non-native extension. Native remains the frozen comparator unless a separately preregistered reason requires a new state."
        )
        self.assertFalse(pre["sequencing"]["scientificExecutionAuthorizedByThisFile"])
        self.assertFalse(pre["sequencing"]["solverExecutionAuthorized"])

    def test_exact_asiv_runtime_identity_is_frozen_in_candidate_and_precontract(self):
        mod = load_candidate()
        payload = mod.build_prefrozen_manifest()
        pre = json.loads(PRECONTRACT.read_text(encoding="utf-8"))
        expected = {
            "runtimeLockPath": "experiments/mystic-batch-v1/runtime-lock.micromamba.json",
            "runtimeLockGitBlobSha1": "8573f62829371a0eb866976a5062ea61dc0767b1",
            "runtimeLockRawSha256": "3b5fbec964642b04c73a6423b3355dbcc4ba5e84f9614f6d74420491bacc20c5",
            "exactPackageSpec": "rubin-libradtran=2.0.6=py312pl5321he9373c2_1",
            "uvspecSha256": "2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3",
            "uvspecHelpSha256": "868aea5af762d968f6f62c4e1472916d25232ed9cab5be112d753b0823d20548",
            "baseDataTreeSha256": "ad30b49177e9c84e46497d69faf0c75e466996b0d0003f1de210289ae9f847d7",
            "augmentedDataTreeSha256": "5d8bbf8e6b91ec3d405dee36f21a94afbb6e5ec6cd67da2dd5dd541738199d80",
            "officialOptpropArchiveSha256": "11daa1f1f4be0fd4ddf7e881ec2005498049674a1540d37b4b1e8f5e16052c7e",
            "atmosphereSha256": "dab26290ed81c762ed0c607e5dc2d53393c1462a0c3a528bc5e3f5935191cfb5",
        }
        for key, value in expected.items():
            self.assertEqual(payload["runtimeIdentity"][key], value)
            self.assertEqual(pre["runtimeIdentity"][key], value)
        self.assertTrue(payload["runtimeIdentity"]["verificationRequiredBeforeAnyFutureSolverExecution"])
        self.assertTrue(pre["runtimeIdentity"]["verificationRequiredBeforeAnyFutureSolverExecution"])
        self.assertFalse(pre["runtimeIdentity"]["approximatelyEquivalentRuntimeAllowed"])
        self.assertTrue(pre["runtimeIdentity"]["inheritExactlyFromAsivExecutionContract"])
        self.assertEqual(
            payload["sourceBindings"]["asivExecutionContractGitBlobSha1"],
            "a2c4ebac5be8daf096ca3b543fd2f994ec4146a1",
        )
        self.assertEqual(
            pre["sourceBindings"]["exactAsivExecutionContract"],
            {
                "path": "experiments/aerosol-scenario-interpolation-validation-v1/execution-contract.review.json",
                "gitBlobSha1": "a2c4ebac5be8daf096ca3b543fd2f994ec4146a1",
            },
        )

    def test_rendered_non_native_input_matches_direct_transport_contract(self):
        mod = load_candidate()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            atmosphere = tmp_path / "afglus.dat"
            atmosphere.write_text(
                "120 1\n100 1\n80 1\n60 1\n40 1\n20 1\n10 1\n5 1\n2 1\n1 1\n0 1\n",
                encoding="utf-8",
            )
            grid = tmp_path / "wavelength-1nm.dat"
            grid.write_text("\n".join(str(w) for w in range(380, 781)) + "\n", encoding="ascii")
            text = mod.render_uvspec_input(
                family="opac-maritime-clean",
                data_dir=tmp_path,
                atmosphere_file=atmosphere,
                wavelength_grid_file=grid,
                target_altitude_deg=12.666667,
                observer_elevation_m=875,
                aod550=0.166666667,
            )
        self.assertIn("wavelength 380 780", text)
        self.assertIn("mol_abs_param crs", text)
        self.assertIn("zout 0.000000", text)
        self.assertIn("albedo 0.15000000", text)
        self.assertIn("aerosol_species_library OPAC", text)
        self.assertIn("aerosol_species_file maritime_clean", text)
        self.assertIn("aerosol_set_tau_at_wvl 550 0.16666667", text)
        self.assertIn("rte_solver sdisort", text)
        self.assertIn("sdisort nscat 1", text)
        self.assertIn("output_quantity transmittance", text)
        self.assertIn("output_user lambda edir", text)
        self.assertNotIn("rte_solver mystic", text.lower())
        self.assertNotIn("mc_", text.lower())
        self.assertNotIn("angstrom", text.lower())

    def test_native_rebuild_and_render_are_unconditionally_refused(self):
        mod = load_candidate()
        with self.assertRaises(mod.CandidateRefusal):
            mod.validate_case(
                family="native-rural-ss",
                target_altitude_deg=20,
                observer_elevation_m=0,
                aod550=0.1,
            )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            atmosphere = tmp_path / "afglus.dat"
            atmosphere.write_text("120 1\n0 1\n", encoding="utf-8")
            grid = tmp_path / "wavelength-1nm.dat"
            grid.write_text("380\n780\n", encoding="ascii")
            with self.assertRaises(mod.CandidateRefusal):
                mod.render_uvspec_input(
                    family="native-rural-ss",
                    data_dir=tmp_path,
                    atmosphere_file=atmosphere,
                    wavelength_grid_file=grid,
                    target_altitude_deg=20,
                    observer_elevation_m=0,
                    aod550=0.1,
                )

    def test_source_contains_no_solver_invocation_or_native_override_surface(self):
        source = CANDIDATE.read_text(encoding="utf-8")
        self.assertNotIn("import subprocess", source)
        self.assertNotIn("subprocess.", source)
        self.assertNotIn("find_uvspec", source)
        self.assertNotIn("run_reference(", source)
        self.assertNotIn("UVSPEC", source)
        self.assertNotIn("allow_native_render", source)
        self.assertNotIn("--allow-native-render", source)


if __name__ == "__main__":
    unittest.main()
