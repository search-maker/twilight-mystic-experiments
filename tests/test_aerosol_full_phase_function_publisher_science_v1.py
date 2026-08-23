from __future__ import annotations

import importlib.util
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "experiments/aerosol-full-phase-function-sensitivity-v1"
EXECD = STAGE / "execution-candidate"
PUBLISHER = ROOT / ".github/workflows/afpf-v1-dispatch-publisher.yml"
SCIENCE = ROOT / ".github/workflows/afpf-v1-execution.yml"
SCIENCE_PLAN = EXECD / "science_plan.py"
DISPATCH_GUARD = EXECD / "dispatch_guard.py"
SCIENCE_GUARD = EXECD / "science_guard.py"
BUILD_LEVEL_B = EXECD / "build_level_b_input.py"
LEVEL_B_RUNNER = EXECD / "level_b_runner.mjs"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AerosolFullPhaseFunctionPublisherScienceV1Tests(unittest.TestCase):
    def test_publisher_uploads_zero_runtime_evidence_before_explicit_science_dispatch(self) -> None:
        text = PUBLISHER.read_text()
        upload = text.index("Persist immutable publisher evidence before science trigger")
        dispatch = text.index("Explicitly dispatch attempt-1 science on pushed ref")
        self.assertLess(upload, dispatch)
        self.assertIn("afpf-v1-dispatch-publisher-ordinal-", text)
        self.assertIn("DISPATCH_PUBLISHED_ZERO_RUNTIME", text)
        self.assertIn("ORDINAL${ORDINAL}_AFPF_V1_DISPATCH_CONSUMED", text)
        self.assertIn("actions/workflows/afpf-v1-execution.yml/dispatches", text)
        self.assertIn("GITHUB_RUN_ATTEMPT\" = 1", text)
        self.assertNotIn("github.event.workflow_run", text)

    def test_science_workflow_is_explicit_attempt1_and_exact_four_shards(self) -> None:
        text = SCIENCE.read_text()
        self.assertIn("workflow_dispatch:", text)
        self.assertNotIn("pull_request:", text)
        self.assertNotIn("schedule:", text)
        self.assertIn("test \"$GITHUB_RUN_ATTEMPT\" = 1", text)
        for depth in (2, 4, 6, 8):
            self.assertIn(f"cases-dep{depth}:", text)
            self.assertIn(f"needs.preflight.outputs.matrix{depth}", text)
        self.assertEqual(text.count("max-parallel: 2"), 4)
        self.assertIn("maximumGlobalCaseParallelism')!=8", text)
        self.assertIn("casesPerShard')!=90", text)
        self.assertNotIn("rerun-workflow", text)
        self.assertNotIn("re-run", text.lower())

    def test_science_waits_for_terminal_attempt1_publisher_and_exact_evidence(self) -> None:
        text = SCIENCE.read_text()
        self.assertIn("expected exactly one publisher run", text)
        self.assertIn("publisher rerun forbidden", text)
        self.assertIn('test "$PUBLISHER_STATUS" = completed', text)
        self.assertIn('test "$PUBLISHER_CONCLUSION" = success', text)
        self.assertIn("afpf-v1-dispatch-publisher-ordinal-", text)
        self.assertIn("publisher-artifact", text)
        self.assertIn("science_guard.evaluate", text)
        self.assertIn("EXACT_ONE_USE_AFPF_V1_DISPATCH_AUTHORIZED", text)

    def test_optprop_overlay_is_hash_verified_before_case_execution(self) -> None:
        text = SCIENCE.read_text()
        overlay = text.index("Reconstruct exact frozen OPAC overlay and capture runtime identity")
        execute = text.index("Execute exactly one preregistered AFPF case")
        self.assertLess(overlay, execute)
        self.assertIn("stage_frozen_overlay", text)
        self.assertIn("5d8bbf8e6b91ec3d405dee36f21a94afbb6e5ec6cd67da2dd5dd541738199d80", text)
        self.assertIn("optprop_v2.1.tar.gz", text)
        self.assertIn("libradtran-overlay/data", text)
        self.assertIn("allow_execution=True", text)

    def test_aggregate_refuses_partial_universe_and_level_b_follows_exact360(self) -> None:
        text = SCIENCE.read_text()
        enumerate_cases = text.index("Enumerate exact current-run case artifact metadata")
        download_cases = text.index("Download exact current-run cases only after complete enumeration")
        scalar = text.index("Run frozen exact-360 acquisition and scalar spectral analysis")
        level_b_input = text.index("Build Level-B input only after exact-360 aggregate success")
        level_b = text.index("Run frozen Level-B propagation only after exact-360 aggregate")
        final_upload = text.index("Persist complete preregistered AFPF analysis evidence")
        terminal = text.index("Publish terminal success checkpoint to Issue 60")
        self.assertLess(enumerate_cases, download_cases)
        self.assertLess(download_cases, scalar)
        self.assertLess(scalar, level_b_input)
        self.assertLess(level_b_input, level_b)
        self.assertLess(level_b, final_upload)
        self.assertLess(final_upload, terminal)
        self.assertIn("expected exactly 360 current-run case artifacts", text)
        self.assertIn("COMPLETED_PREREGISTERED_AFPF_V1_ANALYSIS", text)
        self.assertIn("COMPLETED_PREREGISTERED_AFPF_V1_SPECTRAL_ANALYSIS", text)
        self.assertIn("COMPLETED_PREREGISTERED_AFPF_V1_LEVEL_B", text)
        self.assertIn("contrastCountPerCell!==7", text)
        self.assertIn("desert_spheroids_vs_desert", text)
        self.assertIn("AFPF-V1-SCIENCE-COMPLETED", text)

    def test_afpf_transport_has_no_aops_ssa_g_control_fields(self) -> None:
        texts = "\n".join(path.read_text() for path in (
            PUBLISHER, SCIENCE, SCIENCE_PLAN, DISPATCH_GUARD, SCIENCE_GUARD,
            BUILD_LEVEL_B, LEVEL_B_RUNNER,
        ))
        self.assertNotIn("ssaSet", texts)
        self.assertNotIn("ggSet", texts)
        self.assertNotIn("aerosol_modify", SCIENCE.read_text())
        self.assertIn("opacMixture", BUILD_LEVEL_B.read_text())
        self.assertIn("desert_spheroids_vs_desert", LEVEL_B_RUNNER.read_text())

    def test_science_plan_is_exact_360_72_24_and_non_authorizing(self) -> None:
        source = SCIENCE_PLAN.read_text()
        self.assertIn("DEPTHS = (2.0, 4.0, 6.0, 8.0)", source)
        self.assertIn('"caseCount": 360', source)
        self.assertIn('"groupCount": 72', source)
        self.assertIn('"analysisCellCount": 24', source)
        self.assertIn('"casesPerShard": 90', source)
        self.assertIn('"maxParallelPerShard": 2', source)
        self.assertIn('"maximumGlobalCaseParallelism": 8', source)
        self.assertIn('"scientificExecutionAuthorizedByPlan": False', source)
        self.assertIn('"resultOpeningAuthorizedByPlan": False', source)

    def test_guard_sources_require_separate_dispatch_and_attempt1(self) -> None:
        dispatch = DISPATCH_GUARD.read_text()
        science = SCIENCE_GUARD.read_text()
        self.assertIn("DISPATCH_ELIGIBLE_NOT_CREATED", dispatch)
        self.assertIn("DISPATCH_TRANSITION_VALID", dispatch)
        self.assertIn("exactly one exact Issue #60 authorization allocation marker required", dispatch)
        self.assertIn("exactly one dispatch-consumed marker required after git push", dispatch)
        self.assertIn("workflow_dispatch", science)
        self.assertIn("science run attempt must be exactly 1", science)
        self.assertIn("publisher must be completed success attempt1", science)
        self.assertIn("resultOpeningAuthorizedBeforeExact360", science)
        self.assertIn("solverExecutionPermittedNow", science)

    def test_level_b_plumbing_is_exact_seven_contrasts_after_aggregate(self) -> None:
        build = BUILD_LEVEL_B.read_text()
        runner = LEVEL_B_RUNNER.read_text()
        self.assertIn("COMPLETE_EXACT_360_CASE_ARTIFACT_UNIVERSE", build)
        self.assertIn('"contrastCountPerCell": 7', build)
        self.assertIn("case-result content hash differs from aggregate acquisition", build)
        self.assertIn("COMPLETED_PREREGISTERED_AFPF_V1_LEVEL_B", runner)
        self.assertIn("EXPECTED_HUMAN_THRESHOLD_GIT_BLOB = 'bb4cd0ff02159ecffe276022cec9d292c7a434a3'", runner)
        self.assertIn("priorityShapeContrast: 'desert_spheroids_vs_desert'", runner)
        self.assertIn("pValuesPermitted: false", runner)
        self.assertIn("confidenceIntervalsPermitted: false", runner)
        self.assertIn("epsilonSubstitutionPermitted: false", runner)


if __name__ == "__main__":
    unittest.main()
