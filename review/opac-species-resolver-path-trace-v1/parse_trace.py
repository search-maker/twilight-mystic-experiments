from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

EXPECTED_SOLVER_ERROR = "found neither netcdf nor ASCII optical property files"
PATH_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')


def _decode_trace_string(value: str) -> str:
    try:
        return bytes(value, "utf-8").decode("unicode_escape")
    except UnicodeDecodeError:
        return value


def _looks_like_property_lookup(path: str) -> bool:
    p = path.lower()
    name = Path(path).name.lower()
    if "synthetic-low-inso.dat" in p:
        return False
    if "inso" in name:
        return True
    if "opac" in p and name.endswith((".nc", ".cdf", ".dat", ".mie", ".ascii")):
        return True
    return False


def parse_trace(trace_text: str, stderr_text: str, exit_code: int) -> dict:
    failed_paths: list[str] = []
    all_relevant: list[str] = []
    for raw in trace_text.splitlines():
        paths = [_decode_trace_string(x) for x in PATH_RE.findall(raw)]
        relevant = [p for p in paths if _looks_like_property_lookup(p)]
        if relevant:
            all_relevant.extend(relevant)
        if "ENOENT" in raw and relevant:
            failed_paths.extend(relevant)

    candidates = sorted(set(failed_paths))
    relevant = sorted(set(all_relevant))
    error_present = EXPECTED_SOLVER_ERROR in stderr_text
    status = (
        "TRACE_IDENTIFIED_CANDIDATE_OPTICAL_PROPERTY_LOOKUPS"
        if candidates and error_present
        else "TRACE_DID_NOT_IDENTIFY_REQUIRED_LOOKUPS"
    )
    out = {
        "schemaVersion": 1,
        "stageId": "opac-species-resolver-path-trace-v1",
        "status": status,
        "uvspecExitCode": int(exit_code),
        "expectedResolverErrorPresent": error_present,
        "candidateMissingPaths": candidates,
        "allRelevantObservedPaths": relevant,
        "candidateCount": len(candidates),
        "scientificOrdinalAllocated": False,
        "mysticExecuted": False,
        "highProfileSolverExecuted": False,
        "taylorOrJerusalemUsed": False,
        "productionAuthorized": False,
        "levelBInferenceAuthorized": False,
    }
    canonical = json.dumps(out, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    out["contentSha256"] = hashlib.sha256(canonical).hexdigest()
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trace", type=Path, required=True)
    ap.add_argument("--stderr", type=Path, required=True)
    ap.add_argument("--exit-code-file", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    exit_code = int(args.exit_code_file.read_text().strip())
    out = parse_trace(args.trace.read_text(errors="replace"), args.stderr.read_text(errors="replace"), exit_code)
    args.output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps(out, sort_keys=True))


if __name__ == "__main__":
    main()
