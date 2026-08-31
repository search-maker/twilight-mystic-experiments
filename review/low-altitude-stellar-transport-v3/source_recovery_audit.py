#!/usr/bin/env python3
"""LOWALT-STELLAR-STATE-0003 solver-free pinned-source recovery audit.

This module performs provenance checks only. It never invokes uvspec or any
radiative-transfer solver and never reads protected LOWALT results.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

EXPECTED_FEEDSTOCK_COMMIT = "d6f1997b2f486541136f514188c650fdd370f8e2"
EXPECTED_RECIPE_URL = "http://www.libradtran.org/download/libRadtran-2.0.6.tar.gz"
EXPECTED_SOURCE_SHA256 = "999e47f4af4b5df6f85a6887fc105fc8f6e1a7cee89a3124f69ac8d8912c8e85"
EXPECTED_PACKAGE_FILENAME = "rubin-libradtran-2.0.6-py312pl5321he9373c2_1.conda"
EXPECTED_UVSPEC_SHA256 = "2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3"
EXPECTED_BUILD_STRING = "py312pl5321he9373c2_1"
GOVERNING_SOURCE_SUFFIXES = (
    "doc/radiative_transfer_theory.tex",
    "doc/radiative_transfer.tex",
    "libsrc_c/cdisort.c",
    "libsrc_c/cdisort.h",
    "src/solve_rte.c",
    "src/uvspec_lex.l",
)


class RecoveryRefusal(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_recipe(text: str) -> dict[str, Any]:
    url_match = re.search(r"^\s*url:\s*(.*?)\s*$", text, re.M)
    sha_match = re.search(r"^\s*sha256:\s*([0-9a-fA-F]{64})\s*$", text, re.M)
    build_match = re.search(r"^\s*number:\s*(\d+)\s*$", text, re.M)
    if not (url_match and sha_match and build_match):
        raise RecoveryRefusal("recipe URL/SHA/build fields not found")
    raw_url = url_match.group(1)
    rendered_url = raw_url.replace("{{ version }}", "2.0.6").replace("{{version}}", "2.0.6")
    return {
        "rawUrl": raw_url,
        "renderedUrl": rendered_url,
        "sourceSha256": sha_match.group(1).lower(),
        "buildNumber": int(build_match.group(1)),
    }


def parse_repodata(path: Path) -> dict[str, Any]:
    x = json.loads(path.read_text(encoding="utf-8"))
    record = None
    section = None
    for key in ("packages.conda", "packages"):
        candidates = x.get(key) or {}
        if EXPECTED_PACKAGE_FILENAME in candidates:
            record = candidates[EXPECTED_PACKAGE_FILENAME]
            section = key
            break
    if not isinstance(record, dict):
        raise RecoveryRefusal("exact package filename missing from repodata")
    if str(record.get("build")) != EXPECTED_BUILD_STRING:
        raise RecoveryRefusal("repodata build string drift")
    sha = record.get("sha256")
    size = record.get("size")
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", sha):
        raise RecoveryRefusal("repodata package SHA-256 missing")
    if not isinstance(size, int) or size <= 0:
        raise RecoveryRefusal("repodata package size missing")
    return {"section": section, "sha256": sha.lower(), "size": size, "record": record}


def bounded_text_evidence(info_dir: Path) -> dict[str, Any]:
    evidence: dict[str, Any] = {}
    if not info_dir.exists():
        return evidence
    needles = ("libradtran", "999e47", "64930c", "source:", "url:", "sha256:", "build:")
    for path in sorted(p for p in info_dir.rglob("*") if p.is_file()):
        rel = path.relative_to(info_dir).as_posix()
        if path.stat().st_size > 2_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        hits = []
        for lineno, line in enumerate(text.splitlines(), 1):
            low = line.lower()
            if any(n in low for n in needles):
                hits.append({"line": lineno, "text": line[:500]})
            if len(hits) >= 40:
                break
        if hits:
            evidence[rel] = {"sha256": sha256_file(path), "bytes": path.stat().st_size, "hits": hits}
    return evidence


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--recipe", type=Path, required=True)
    ap.add_argument("--http-archive", type=Path, required=True)
    ap.add_argument("--http-headers", type=Path, required=True)
    ap.add_argument("--http-effective-url", type=Path, required=True)
    ap.add_argument("--http-curl-status", type=Path, required=True)
    ap.add_argument("--repodata", type=Path, required=True)
    ap.add_argument("--conda-package", type=Path, required=True)
    ap.add_argument("--package-info-dir", type=Path, required=True)
    ap.add_argument("--package-members", type=Path, required=True)
    ap.add_argument("--uvspec", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "schemaVersion": 1,
        "state": "LOWALT-STELLAR-STATE-0003",
        "stage": "source-recovery-audit-v1",
        "postV1Nonblocking": True,
        "resultBlind": True,
        "scientificSolverExecuted": False,
        "uvspecExecuted": False,
        "mysticExecuted": False,
        "protectedResultsRead": False,
        "supportBelow5DegPromoted": False,
        "sourceEquivalenceResolved": False,
        "nonprotectedSolverMatrixFrozen": False,
        "expected": {
            "feedstockCommit": EXPECTED_FEEDSTOCK_COMMIT,
            "recipeSourceUrl": EXPECTED_RECIPE_URL,
            "sourceSha256": EXPECTED_SOURCE_SHA256,
            "packageFilename": EXPECTED_PACKAGE_FILENAME,
            "uvspecSha256": EXPECTED_UVSPEC_SHA256,
        },
    }

    try:
        recipe_text = args.recipe.read_text(encoding="utf-8")
        recipe = parse_recipe(recipe_text)
        report["recipe"] = recipe
        if recipe["renderedUrl"] != EXPECTED_RECIPE_URL:
            raise RecoveryRefusal(f"literal recipe URL drift: {recipe['renderedUrl']!r}")
        if recipe["sourceSha256"] != EXPECTED_SOURCE_SHA256 or recipe["buildNumber"] != 1:
            raise RecoveryRefusal("recipe source hash/build drift")

        curl_status_text = args.http_curl_status.read_text(encoding="utf-8").strip()
        if not re.fullmatch(r"[0-9]+", curl_status_text):
            raise RecoveryRefusal("literal HTTP curl status record malformed")
        curl_status = int(curl_status_text)
        effective_lines = [x.strip() for x in args.http_effective_url.read_text(encoding="utf-8").splitlines() if x.strip()]
        headers_sha = sha256_file(args.http_headers) if args.http_headers.is_file() else None
        http_present = args.http_archive.is_file() and args.http_archive.stat().st_size > 0
        http_sha = sha256_file(args.http_archive) if http_present else None
        http_bytes = args.http_archive.stat().st_size if http_present else 0
        report["literalHttpFetch"] = {
            "curlExitCode": curl_status,
            "archivePresent": http_present,
            "archiveSha256": http_sha,
            "archiveBytes": http_bytes,
            "headersSha256": headers_sha,
            "effectiveUrlRecord": effective_lines,
            "expectedSourceRecovered": curl_status == 0 and http_sha == EXPECTED_SOURCE_SHA256,
        }

        repodata = parse_repodata(args.repodata)
        pkg_sha = sha256_file(args.conda_package)
        pkg_size = args.conda_package.stat().st_size
        if args.conda_package.name != EXPECTED_PACKAGE_FILENAME:
            raise RecoveryRefusal("package filename drift")
        if pkg_sha != repodata["sha256"] or pkg_size != repodata["size"]:
            raise RecoveryRefusal("downloaded package does not match repodata SHA/size")
        uvspec_sha = sha256_file(args.uvspec)
        if uvspec_sha != EXPECTED_UVSPEC_SHA256:
            raise RecoveryRefusal("inherited uvspec binary SHA-256 mismatch")
        report["package"] = {
            "filename": args.conda_package.name,
            "sha256": pkg_sha,
            "bytes": pkg_size,
            "repodataSection": repodata["section"],
            "repodataSha256": repodata["sha256"],
            "uvspecSha256": uvspec_sha,
            "identityBound": True,
        }

        members = [x.strip() for x in args.package_members.read_text(encoding="utf-8").splitlines() if x.strip()]
        source_members = [m for m in members if any(m.endswith(s) for s in GOVERNING_SOURCE_SUFFIXES)]
        archive_members = [m for m in members if "libradtran" in m.lower() and (m.endswith(".tar.gz") or m.endswith(".tgz"))]
        report["packageInventory"] = {
            "memberCount": len(members),
            "governingSourceMembers": source_members,
            "embeddedLibRadtranArchives": archive_members,
        }
        report["packageInfoEvidence"] = bounded_text_evidence(args.package_info_dir)

        if curl_status == 0 and http_sha == EXPECTED_SOURCE_SHA256:
            report["status"] = "PASS_LITERAL_RECIPE_SOURCE_RECOVERED"
            report["sourceRecoveryReadyForExactCapture"] = True
        else:
            report["status"] = "FAIL_PINNED_SOURCE_NOT_RECOVERED"
            report["sourceRecoveryReadyForExactCapture"] = False
        report["sourceEquivalenceResolved"] = False
        rc = 0 if report["status"] == "PASS_LITERAL_RECIPE_SOURCE_RECOVERED" else 3
    except (OSError, ValueError, json.JSONDecodeError, RecoveryRefusal) as exc:
        report["status"] = "FAIL_RECOVERY_IDENTITY_OR_MECHANICS"
        report["error"] = str(exc)
        rc = 4

    (args.output / "source-recovery-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(report["status"])
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
