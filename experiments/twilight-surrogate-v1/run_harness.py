#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from harness import LogRidgeSurrogate, allocate_two_stage, dump_json, evaluate, load_jsonl, select_adaptive_cases


def run(data_dir: Path, output_dir: Path) -> dict:
    train = load_jsonl(data_dir / "train.jsonl")
    validation = load_jsonl(data_dir / "validation.jsonl")
    withheld = load_jsonl(data_dir / "withheld.jsonl")
    candidates = load_jsonl(data_dir / "candidates.jsonl")
    model = LogRidgeSurrogate(train, ridge=1e-8, ood_distance=0.62)
    validation_report = evaluate(model, validation)
    withheld_report = evaluate(model, withheld)
    selected = select_adaptive_cases(model, candidates, limit=24)
    synthetic_stage_one = [
        {"caseId": row["id"], "value": model.predict(row).value, "sigma": model.predict(row).value * ratio}
        for row, ratio in zip(selected[:9], (0.02, 0.04, 0.10, 0.025, 0.07, 0.12, 0.03, 0.055, 0.09), strict=True)
    ]
    allocation = allocate_two_stage(synthetic_stage_one)
    output_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "schemaVersion": 1,
        "stageId": "twilight-surrogate-v1",
        "status": "PASSED_SYNTHETIC_HARNESS",
        "syntheticOnly": True,
        "model": {
            "type": "log-space engineered ridge surrogate",
            "basisCount": 16,
            "ridge": 1e-8,
            "oodDistance": 0.62,
        },
        "validation": validation_report,
        "withheld": withheld_report,
        "selectedAdaptiveCases": selected,
        "twoStageAllocation": allocation,
        "gates": {
            "maximumWithheldMeanAbsoluteLogError": 0.09,
            "minimumWithheldTwoSigmaCoverage": 0.75,
            "actualWithheldMeanAbsoluteLogError": withheld_report["meanAbsoluteLogError"],
            "actualWithheldTwoSigmaCoverage": withheld_report["twoSigmaCoverage"],
            "passed": withheld_report["meanAbsoluteLogError"] <= 0.09 and withheld_report["twoSigmaCoverage"] >= 0.75,
        },
        "boundary": "synthetic software harness only; no MYSTIC validity, observational validity, LUT readiness, or production authorization",
    }
    if not report["gates"]["passed"]:
        raise RuntimeError(f"synthetic withheld gates failed: {report['gates']}")
    (output_dir / "harness-report.json").write_text(dump_json(report))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(dump_json(run(args.data_dir, args.output_dir)), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
