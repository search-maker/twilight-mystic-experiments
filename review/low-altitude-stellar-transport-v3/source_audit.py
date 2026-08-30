from __future__ import annotations

import argparse
import hashlib
import json
import re
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any

EXPECTED_SOURCE_SHA256 = "999e47f4af4b5df6f85a6887fc105fc8f6e1a7cee89a3124f69ac8d8912c8e85"
EXPECTED_FEEDSTOCK_COMMIT = "d6f1997b2f486541136f514188c650fdd370f8e2"
EXPECTED_VERSION = "2.0.6"
EXPECTED_BUILD_NUMBER = 1
GOVERNING_PATHS = (
    "doc/radiative_transfer_theory.tex",
    "doc/radiative_transfer.tex",
    "libsrc_c/cdisort.c",
    "libsrc_c/cdisort.h",
    "src/solve_rte.c",
    "src/uvspec_lex.l",
)
PATTERNS = {
    "earth_radius": r"earth[_ ]radius|EARTH_RADIUS|radius.*earth",
    "chapman": r"chapman|CH\s*\(|ichapman",
    "pseudospherical": r"pseudo[-_ ]?spherical|pseudospherical",
    "geometry_angle": r"mu0|umu0|sza|solar zenith",
    "model_vertical_grid": r"atm_z_grid|zout|altitude",
    "aerosol_tau": r"aerosol_set_tau_at_wvl|aerosol.*tau|set_tau",
    "solver_null": r"rte_solver|null",
    "solver_sdisort": r"sdisort|SDISORT",
    "direct_output": r"edir|direct.*flux|flux.*direct|uavgdir",
    "underflow_exp": r"exp\s*\(|underflow|DBL_MIN|FLT_MIN|HUGE_VAL",
}
CONTEXT_RADIUS = 5
MAX_CONTEXT_BLOCKS_PER_PATTERN_PER_FILE = 12


class AuditError(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def parse_recipe(text: str) -> dict[str, Any]:
    version_match = re.search(r'\{%\s*set\s+version\s*=\s*"([^"]+)"\s*%\}', text)
    sha_match = re.search(r"^\s*sha256:\s*([0-9a-f]{64})\s*$", text, re.MULTILINE)
    build_match = re.search(r"^build:\s*\n\s*number:\s*(\d+)\s*$", text, re.MULTILINE)
    return {
        "version": version_match.group(1) if version_match else None,
        "sourceSha256": sha_match.group(1) if sha_match else None,
        "buildNumber": int(build_match.group(1)) if build_match else None,
    }


def safe_member_name(name: str) -> PurePosixPath:
    p = PurePosixPath(name)
    if p.is_absolute() or ".." in p.parts or not p.parts:
        raise AuditError(f"unsafe tar member: {name}")
    return p


def find_member(tf: tarfile.TarFile, relative_path: str) -> tarfile.TarInfo:
    matches = []
    for member in tf.getmembers():
        p = safe_member_name(member.name)
        if member.isfile() and p.as_posix().endswith("/" + relative_path):
            matches.append(member)
    if len(matches) != 1:
        raise AuditError(f"expected exactly one {relative_path}, found {len(matches)}")
    return matches[0]


def context_blocks(text: str, regex: re.Pattern[str]) -> list[dict[str, Any]]:
    lines = text.splitlines()
    hit_lines = [i for i, line in enumerate(lines) if regex.search(line)]
    blocks: list[tuple[int, int]] = []
    for i in hit_lines:
        start = max(0, i - CONTEXT_RADIUS)
        stop = min(len(lines), i + CONTEXT_RADIUS + 1)
        if blocks and start <= blocks[-1][1]:
            blocks[-1] = (blocks[-1][0], max(blocks[-1][1], stop))
        else:
            blocks.append((start, stop))
    out = []
    for start, stop in blocks[:MAX_CONTEXT_BLOCKS_PER_PATTERN_PER_FILE]:
        out.append(
            {
                "startLine": start + 1,
                "endLine": stop,
                "lines": [f"{j + 1}: {lines[j]}" for j in range(start, stop)],
            }
        )
    return out


def write_report(output: Path, report: dict[str, Any]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    canonical = json.dumps(
        report,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode()
    report["contentSha256BeforeSelfField"] = sha256_bytes(canonical)
    (output / "source-audit-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", type=Path, required=True)
    ap.add_argument("--recipe", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    report: dict[str, Any] = {
        "schemaVersion": 1,
        "stateId": "LOWALT-STELLAR-STATE-0003",
        "stageId": "pinned-source-equivalence-audit-v1",
        "status": "STARTED",
        "postV1Nonblocking": True,
        "resultBlind": True,
        "scientificSolverExecuted": False,
        "uvspecExecuted": False,
        "mysticExecuted": False,
        "protectedResultsRead": False,
        "supportBelow5DegPromoted": False,
        "expectedFeedstockCommit": EXPECTED_FEEDSTOCK_COMMIT,
        "expectedVersion": EXPECTED_VERSION,
        "expectedSourceSha256": EXPECTED_SOURCE_SHA256,
        "expectedBuildNumber": EXPECTED_BUILD_NUMBER,
    }

    try:
        recipe_text = args.recipe.read_text(encoding="utf-8")
        recipe = parse_recipe(recipe_text)
        report["recipe"] = {
            **recipe,
            "sha256": sha256_file(args.recipe),
            "byteCount": args.recipe.stat().st_size,
        }
        if recipe != {
            "version": EXPECTED_VERSION,
            "sourceSha256": EXPECTED_SOURCE_SHA256,
            "buildNumber": EXPECTED_BUILD_NUMBER,
        }:
            report["status"] = "FAIL_PINNED_RECIPE_DRIFT"
            write_report(args.output, report)
            raise SystemExit(20)

        observed_archive_sha = sha256_file(args.archive)
        report["archive"] = {
            "sha256": observed_archive_sha,
            "byteCount": args.archive.stat().st_size,
        }
        if observed_archive_sha != EXPECTED_SOURCE_SHA256:
            report["status"] = "FAIL_PINNED_SOURCE_ARCHIVE_DRIFT"
            write_report(args.output, report)
            raise SystemExit(21)

        source_files: dict[str, Any] = {}
        source_context: dict[str, Any] = {}
        compiled = {
            key: re.compile(pattern, re.IGNORECASE)
            for key, pattern in PATTERNS.items()
        }
        with tarfile.open(args.archive, "r:gz") as tf:
            for relative in GOVERNING_PATHS:
                member = find_member(tf, relative)
                stream = tf.extractfile(member)
                if stream is None:
                    raise AuditError(f"cannot read {relative}")
                data = stream.read()
                text = data.decode("utf-8", errors="strict")
                source_files[relative] = {
                    "archiveMember": member.name,
                    "byteCount": len(data),
                    "sha256": sha256_bytes(data),
                    "lineCount": len(text.splitlines()),
                }
                source_context[relative] = {}
                for key, regex in compiled.items():
                    blocks = context_blocks(text, regex)
                    if blocks:
                        source_context[relative][key] = blocks

        report["governingFiles"] = source_files
        report["sourceContext"] = source_context
        report["capturePatterns"] = PATTERNS
        report["status"] = "PASS_PINNED_SOURCE_CAPTURED"
        write_report(args.output, report)
    except SystemExit:
        raise
    except Exception as exc:
        report["status"] = "FAIL_SOURCE_CAPTURE"
        report["errorType"] = type(exc).__name__
        report["error"] = str(exc)
        write_report(args.output, report)
        raise


if __name__ == "__main__":
    main()
