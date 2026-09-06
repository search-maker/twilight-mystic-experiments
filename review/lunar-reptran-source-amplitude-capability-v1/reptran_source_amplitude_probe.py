#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path

PASS_STATUS = "PASS_CUSTOM_SOURCE_WITH_REPTRAN_CONSUMED_EXACT_RUNTIME"
FAIL_STATUS = "FAIL_CUSTOM_SOURCE_WITH_REPTRAN_NOT_ADMITTED"
EXPECTED_RATIO = 7.0
MAX_ABS_RATIO_DEVIATION = 0.01


class ProbeFailure(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_source(path: Path, amplitude: float) -> None:
    if not math.isfinite(amplitude) or amplitude <= 0.0:
        raise ProbeFailure("synthetic source amplitude must be finite and positive")
    path.write_text(
        "".join(
            f"{w:.1f} {amplitude:.12g}\n"
            for w in (380.0, 550.0, 780.0)
        ),
        encoding="utf-8",
    )


def render_input(*, data_dir: Path, atmosphere: Path, source: Path) -> str:
    text = "\n".join(
        [
            f"data_files_path {data_dir.resolve()}",
            f"atmosphere_file {atmosphere.resolve()}",
            f"source solar {source.resolve()}",
            "mol_abs_param reptran",
            "wavelength 380 780",
            "sza 0",
            "albedo 0",
            "rte_solver disort",
            "number_of_streams 4",
            "zout TOA",
            "output_user lambda edir",
            "quiet",
        ]
    ) + "\n"
    lines = text.splitlines()
    source_line = f"source solar {source.resolve()}"
    if lines.count(source_line) != 1:
        raise ProbeFailure("exactly one arm-specific custom source directive is required")
    if lines.count("mol_abs_param reptran") != 1:
        raise ProbeFailure("exactly one mol_abs_param reptran directive is required")
    if any(line.startswith("mol_abs_param crs") for line in lines):
        raise ProbeFailure("historical CRS fallback is forbidden")
    if sum(line.startswith("mol_abs_param ") for line in lines) != 1:
        raise ProbeFailure("exactly one molecular-absorption directive is required")
    if "rte_solver mystic" in lines or any(line.startswith("mc_") for line in lines):
        raise ProbeFailure("MYSTIC/protected-science controls are forbidden in capability probe")
    return text


def run_arm(*, uvspec: Path, input_text: str, timeout_seconds: int = 180) -> dict:
    completed = subprocess.run(
        [str(uvspec.resolve())],
        input=input_text,
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
        check=False,
    )
    return {
        "exitCode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def parse_lambda_edir(stdout: str) -> tuple[list[float], list[float]]:
    wavelengths: list[float] = []
    edir: list[float] = []
    for raw in stdout.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            wavelength = float(parts[0])
            value = float(parts[1])
        except ValueError:
            continue
        wavelengths.append(wavelength)
        edir.append(value)
    if not wavelengths:
        raise ProbeFailure("uvspec output contains no parseable lambda/edir rows")
    if any(not math.isfinite(x) for x in wavelengths + edir):
        raise ProbeFailure("uvspec output contains non-finite lambda/edir values")
    return wavelengths, edir


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--uvspec", required=True, type=Path)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--atmosphere", required=True, type=Path)
    parser.add_argument("--runtime-report", required=True, type=Path)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    runtime = json.loads(args.runtime_report.read_text(encoding="utf-8"))

    if contract.get("status") != "PREREGISTERED_BEFORE_FRESH_EXACT_RUNTIME_PROBE":
        raise ProbeFailure("capability contract status drift")
    if contract["probe"]["requiredMolecularAbsorption"] != "reptran":
        raise ProbeFailure("contract does not require REPTRAN")
    if contract["probe"]["historicalCrsFallbackAllowed"] is not False:
        raise ProbeFailure("contract silently permits historical CRS fallback")
    if contract["freshIdentityRules"]["attemptMustEqual"] != 1:
        raise ProbeFailure("contract attempt rule drift")
    if contract["freshIdentityRules"]["rerunRetryResumeForbidden"] is not True:
        raise ProbeFailure("contract rerun prohibition drift")

    expected_runtime = contract["exactRuntime"]
    if runtime.get("scientificSolverExecuted") is not False:
        raise ProbeFailure("runtime binding unexpectedly executed scientific solver")
    if runtime.get("syntaxCheckExecuted") is not False:
        raise ProbeFailure("runtime binding unexpectedly executed syntax check")
    if runtime.get("uvspecSha256") != expected_runtime["uvspecSha256"]:
        raise ProbeFailure("uvspec SHA-256 does not match exact pinned runtime")
    if runtime.get("libRadtranDataTreeSha256") != expected_runtime["libRadtranDataTreeSha256"]:
        raise ProbeFailure("libRadtran data-tree SHA-256 does not match exact pinned runtime")

    source_a = out / "synthetic-source-amplitude-a.dat"
    source_b = out / "synthetic-source-amplitude-b.dat"
    write_source(source_a, 1.0)
    write_source(source_b, 7.0)
    input_a = render_input(data_dir=args.data_dir, atmosphere=args.atmosphere, source=source_a)
    input_b = render_input(data_dir=args.data_dir, atmosphere=args.atmosphere, source=source_b)
    (out / "arm-a.inp").write_text(input_a, encoding="utf-8")
    (out / "arm-b.inp").write_text(input_b, encoding="utf-8")

    arm_a = run_arm(uvspec=args.uvspec, input_text=input_a)
    arm_b = run_arm(uvspec=args.uvspec, input_text=input_b)
    (out / "arm-a.stdout.txt").write_text(arm_a["stdout"], encoding="utf-8")
    (out / "arm-b.stdout.txt").write_text(arm_b["stdout"], encoding="utf-8")
    (out / "arm-a.stderr.txt").write_text(arm_a["stderr"], encoding="utf-8")
    (out / "arm-b.stderr.txt").write_text(arm_b["stderr"], encoding="utf-8")

    report = {
        "schemaVersion": 1,
        "contractId": contract["contractId"],
        "status": FAIL_STATUS,
        "classification": contract["probe"]["classification"],
        "runtime": {
            "uvspecSha256": runtime["uvspecSha256"],
            "libRadtranDataTreeSha256": runtime["libRadtranDataTreeSha256"],
            "runtimeReportSha256": sha256_file(args.runtime_report),
        },
        "input": {
            "molecularAbsorption": "reptran",
            "crsFallbackAllowed": False,
            "sourceWavelengthNm": [380.0, 550.0, 780.0],
            "armASourceFlux": [1.0, 1.0, 1.0],
            "armBSourceFlux": [7.0, 7.0, 7.0],
            "sourceFluxUnit": "mW m-2 nm-1",
            "armAInputSha256": hashlib.sha256(input_a.encode()).hexdigest(),
            "armBInputSha256": hashlib.sha256(input_b.encode()).hexdigest(),
        },
        "observed": {
            "armAExitCode": arm_a["exitCode"],
            "armBExitCode": arm_b["exitCode"],
            "armAStderrSha256": hashlib.sha256(arm_a["stderr"].encode()).hexdigest(),
            "armBStderrSha256": hashlib.sha256(arm_b["stderr"].encode()).hexdigest(),
        },
        "decisionRule": {
            "expectedArmBToArmARatio": EXPECTED_RATIO,
            "maximumAbsoluteRatioDeviationAllowed": MAX_ABS_RATIO_DEVIATION,
        },
        "boundaries": {
            "mysticExecuted": False,
            "protectedLunarGeometryUsed": False,
            "protectedLunarResultOpened": False,
            "taylorOrJerusalemResidualUsed": False,
            "scientificSeedAllocated": False,
            "exec004Authorized": False,
            "writeQuietEntered": False,
            "dispatchCreated": False,
            "productionAuthorized": False,
        },
    }

    failure_reasons: list[str] = []
    if arm_a["exitCode"] != 0:
        failure_reasons.append(f"arm A exit code {arm_a['exitCode']}")
    if arm_b["exitCode"] != 0:
        failure_reasons.append(f"arm B exit code {arm_b['exitCode']}")

    if not failure_reasons:
        try:
            wavelengths_a, edir_a = parse_lambda_edir(arm_a["stdout"])
            wavelengths_b, edir_b = parse_lambda_edir(arm_b["stdout"])
            if wavelengths_a != wavelengths_b:
                failure_reasons.append("arm wavelength vectors differ")
            elif len(edir_a) != len(edir_b):
                failure_reasons.append("arm output vector lengths differ")
            elif any(x <= 0.0 for x in edir_a):
                failure_reasons.append("arm A direct irradiance contains non-positive value")
            else:
                ratios = [b / a for a, b in zip(edir_a, edir_b)]
                deviations = [abs(r - EXPECTED_RATIO) for r in ratios]
                max_dev = max(deviations)
                report["observed"].update(
                    {
                        "wavelengthNm": wavelengths_a,
                        "armAEdirect": edir_a,
                        "armBEdirect": edir_b,
                        "armBToArmARatio": ratios,
                        "maximumAbsoluteRatioDeviationObserved": max_dev,
                    }
                )
                if any(not math.isfinite(r) for r in ratios):
                    failure_reasons.append("non-finite B/A ratio")
                elif max_dev > MAX_ABS_RATIO_DEVIATION:
                    failure_reasons.append(
                        f"maximum absolute ratio deviation {max_dev:.12g} exceeds {MAX_ABS_RATIO_DEVIATION}"
                    )
        except ProbeFailure as exc:
            failure_reasons.append(str(exc))

    report["failureReasons"] = failure_reasons
    if not failure_reasons:
        report["status"] = PASS_STATUS

    report_path = out / "reptran-source-amplitude-capability-report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == PASS_STATUS else 2


if __name__ == "__main__":
    raise SystemExit(main())
