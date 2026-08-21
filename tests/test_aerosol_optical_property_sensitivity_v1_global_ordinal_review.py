from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "experiments/aerosol-optical-property-sensitivity-v1"
WRAPPER = STAGE / "execution-candidate/global_ordinal.py"
FREEZE = ROOT / "evidence/aerosol-optical-property-sensitivity-v1/review-freeze.json"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class AopsGlobalOrdinalReviewTests(unittest.TestCase):
    def test_bound_r8_global_ordinal_modules_load_exactly(self) -> None:
        mod = load("aops_global_ordinal_review_test", WRAPPER)
        r8_freshness, r8_ordinal = mod._bound_r8_modules()
        self.assertTrue(callable(r8_freshness.positive_candidate_claims))
        self.assertTrue(callable(r8_ordinal.derive_next_global_ordinal))
        self.assertTrue(callable(r8_ordinal.authoritative_global_ordinal_observations))

    def test_freeze_records_exact_global_ordinal_bindings(self) -> None:
        mod = load("aops_global_ordinal_review_test_2", WRAPPER)
        freeze = json.loads(FREEZE.read_text())
        self.assertEqual(freeze["globalOrdinalWrapperGitBlobSha1"], mod.git_blob_sha1(WRAPPER))
        self.assertEqual(freeze["boundR8GlobalOrdinalImplementationGitBlobSha1"], mod.R8_PREAUTH_ORDINAL_BLOB)
        self.assertEqual(freeze["boundR8FreshnessImplementationGitBlobSha1"], mod.R8_FRESHNESS_BLOB)
        self.assertTrue(freeze["globalOrdinalDerivationBoundToProvenR8Implementation"])
        self.assertFalse(freeze["scientificOrdinalAllocated"])


if __name__ == "__main__":
    unittest.main()
