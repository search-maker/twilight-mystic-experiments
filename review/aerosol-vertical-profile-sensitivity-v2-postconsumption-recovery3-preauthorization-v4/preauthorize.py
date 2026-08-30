from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

V3_HEAD = "ec8af2af3e4eff1c9afd51d2d42a2b93698ab51a"
V3_PATH = "review/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3-preauthorization-v3/preauthorize.py"
V3_BLOB = "286b489911ce83f4eb6d6f0817f3c6271731a036"
V4_BRANCH = "review/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3-preauthorization-v4"


def _load_v3():
    base = os.environ.get("AVPS_V4_BASE_MAIN")
    if not base or len(base) != 40:
        raise SystemExit("AVPS_V4_BASE_MAIN must be the exact live main SHA bound by the review workflow")
    got = subprocess.check_output(["git", "rev-parse", f"{V3_HEAD}:{V3_PATH}"], text=True).strip()
    if got != V3_BLOB:
        raise SystemExit(f"v3 preauthorization source blob drift: {got} != {V3_BLOB}")
    source = subprocess.check_output(["git", "show", f"{V3_HEAD}:{V3_PATH}"], text=True)
    temp_root = Path(os.environ.get("RUNNER_TEMP") or ".")
    temp_path = temp_root / "avps-v2-recovery3-preauthorization-v3-bound-source.py"
    temp_path.write_text(source)
    spec = importlib.util.spec_from_file_location("avps_v2_recovery3_preauth_v4_bound_v3", temp_path)
    if spec is None or spec.loader is None:
        raise SystemExit("cannot load exact v3 preauthorization source")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    root = Path(__file__).resolve().parents[2]
    module.ROOT = root
    module.GENERIC_SCANNER = root / "experiments/aerosol-family-challenge-v2/repository_global_seed_scan.py"
    module.R8_DIR = root / "experiments/aerosol-family-challenge-v2-r8/execution-candidate"
    module.RECOVERY_LEDGER = root / "review/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3-seed-freshness-v1/seed_ledger.py"
    module.PREAUTH_BRANCH = V4_BRANCH
    module.BASE_MAIN = base

    original_build_report = module.build_report

    def build_report(payload: dict[str, Any], seed_global_report: dict[str, Any], expected_head: str, current_run_id: int | None):
        report, observations = original_build_report(payload, seed_global_report, expected_head, current_run_id)
        report["stageId"] = f"{module.STAGE}-preauthorization-v4"
        report.pop("contentSha256", None)
        report["contentSha256"] = module.canonical_sha256(report)
        return report, observations

    module.build_report = build_report
    return module


def main() -> int:
    module = _load_v3()
    return int(module.main())


if __name__ == "__main__":
    raise SystemExit(main())
