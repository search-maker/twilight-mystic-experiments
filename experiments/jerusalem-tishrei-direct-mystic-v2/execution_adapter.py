#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

BATCH_ID = "jerusalem-tishrei-three-star-direct-mystic-v2"
FORMAL_SMOKE_RUN_ID = 33011713466
AOD550_BINDING_LITERAL = "aerosol_set_tau_at_wvl 550"
V1_REPAIRED_ADAPTER = Path(__file__).parents[1] / "jerusalem-tishrei-direct-mystic-v1" / "execution_adapter.py"


class TishreiV2AdapterRefusal(RuntimeError):
    pass


def _load_v1_adapter():
    spec = importlib.util.spec_from_file_location("tishrei_v1_repaired_execution_adapter", V1_REPAIRED_ADAPTER)
    if spec is None or spec.loader is None:
        raise TishreiV2AdapterRefusal(f"cannot load reviewed v1 repaired adapter: {V1_REPAIRED_ADAPTER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.BATCH_ID = BATCH_ID
    return module


def prepare_case(
    proposal_path: Path,
    runtime_report_path: Path,
    case_id: str,
    data_dir: Path,
    repository_root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    v1 = _load_v1_adapter()
    prepared = v1.prepare_case(
        proposal_path,
        runtime_report_path,
        case_id,
        data_dir,
        repository_root,
        output_dir,
    )
    if prepared.get("batchId") != BATCH_ID:
        raise TishreiV2AdapterRefusal(f"wrong scientific-v2 batchId: {prepared.get('batchId')}")
    inputs = prepared.get("inputs") or {}
    if float(inputs.get("observerElevationM", -1)) != 800.0 or float(inputs.get("aod550", -1)) != 0.22:
        raise TishreiV2AdapterRefusal("frozen elevation/AOD changed")
    if prepared.get("observerElevationMechanism") != "atm_z_grid":
        raise TishreiV2AdapterRefusal("reviewed atm_z_grid mechanism missing")
    if float(prepared.get("siteAltitudeKm", -1)) != 0.8 or float(prepared.get("zoutKmAboveLocalSurface", -1)) != 0.0:
        raise TishreiV2AdapterRefusal("frozen elevated-site semantics changed")
    prepared.update(
        {
            "scientificV2ExecutionAdapter": True,
            "sourceRepairedV1AdapterPath": V1_REPAIRED_ADAPTER.as_posix(),
            "formalInfrastructureSmokeRunId": FORMAL_SMOKE_RUN_ID,
            "scientificV2Boundary": (
                "scientific-v2 changes batch identity/governance only; exact v1 repaired atm_z_grid rendering is reused; "
                "Tishrei geometry, AOD550, elevation, seeds, photon histories, RT inputs and analysis semantics remain frozen"
            ),
        }
    )
    input_path = Path(prepared["inputPath"])
    if AOD550_BINDING_LITERAL not in input_path.read_text(encoding="utf-8"):
        raise TishreiV2AdapterRefusal("rendered AOD550 is no longer explicitly bound at 550 nm")
    (input_path.parent / "cross-geometry-prepared.json").write_text(
        json.dumps(prepared, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return prepared
