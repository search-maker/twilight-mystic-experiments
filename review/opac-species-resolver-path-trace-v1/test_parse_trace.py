from __future__ import annotations

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("resolver_trace", HERE / "parse_trace.py")
m = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(m)


def main() -> None:
    trace = "\n".join(
        [
            '123 openat(AT_FDCWD, "/tmp/capability-inputs/profiles/synthetic-low-inso.dat", O_RDONLY) = 3',
            '123 newfstatat(AT_FDCWD, "OPAC/INSO.nc", 0x7fff, 0) = -1 ENOENT (No such file or directory)',
            '123 openat(AT_FDCWD, "/data/aerosol/OPAC/INSO.cdf", O_RDONLY) = -1 ENOENT (No such file or directory)',
            '123 openat(AT_FDCWD, "/data/solar_flux/atlas_plus_modtran", O_RDONLY) = 4',
        ]
    )
    out = m.parse_trace(trace, "Error, found neither netcdf nor ASCII optical property files.\n", 255)
    assert out["status"] == "TRACE_IDENTIFIED_CANDIDATE_OPTICAL_PROPERTY_LOOKUPS"
    assert out["candidateMissingPaths"] == ["/data/aerosol/OPAC/INSO.cdf", "OPAC/INSO.nc"]
    assert "/tmp/capability-inputs/profiles/synthetic-low-inso.dat" not in out["candidateMissingPaths"]
    assert out["scientificOrdinalAllocated"] is False
    assert out["mysticExecuted"] is False
    assert out["highProfileSolverExecuted"] is False

    no_error = m.parse_trace(trace, "different stderr", 255)
    assert no_error["status"] == "TRACE_DID_NOT_IDENTIFY_REQUIRED_LOOKUPS"

    no_candidate = m.parse_trace('openat(AT_FDCWD, "/tmp/foo", O_RDONLY) = -1 ENOENT', m.EXPECTED_SOLVER_ERROR, 255)
    assert no_candidate["candidateCount"] == 0
    assert no_candidate["status"] == "TRACE_DID_NOT_IDENTIFY_REQUIRED_LOOKUPS"

    print("opac species resolver path trace parser: PASS")


if __name__ == "__main__":
    main()
