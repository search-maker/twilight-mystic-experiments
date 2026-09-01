#!/usr/bin/env python3
"""Prospective result-blind E0 correction for ARM ENA/SWS V1.

Issue #60 comment 5487647692 froze, before any SWS value opening, that EACH
-6/-7/-8 anchor must have >=1 native timestamp within +/-5 s and >=10 within
+/-30 s, and that the native channel nearest 550 nm has usable structural
validity/fill/QC state for the REQUIRED samples.  Historical v1 correctly kept
protected photometric arrays sealed, but then required only five safe-QC-good
samples inside +/-30 s and did not require a safe-QC-good sample inside +/-5 s.
That implementation threshold was never part of the preregistration.

This module preserves every v1 firewall/schema/time/wavelength primitive and
changes only the prospective disposition rule: the frozen 1/10 anchor counts
must themselves be satisfied by structurally usable non-photometric-QC samples.
Duplicate native timestamps retain the preregistered validity OR.  No radiance,
signal, count, intensity, brightness, spectrum or other protected value is read.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import netCDF4
import numpy as np

import audit_ena_sws_e0 as V1
from audit_ena_sws_e0 import *  # re-export frozen event/firewall helpers

PROTOCOL = "ARM_ENA_SWS_V1_STAGE0_E0_RESULT_BLIND_V2"
CONTROL_COMMENT = "5487647692"


def audit(event: Event, root: Path, index: dict[str, list[Path]]) -> dict[str, Any]:
    centers = {
        "minus8": parse_utc(event.t_minus8_utc),
        "minus7": parse_utc(event.t_minus7_utc),
        "minus6": parse_utc(event.t_minus6_utc),
    }
    paths: list[Path] = []
    for d in needed_dates(event):
        paths.extend(index.get(d, []))
    paths = sorted(set(paths))

    row: dict[str, Any] = {
        **event.__dict__,
        "source_file_count": len(paths),
        "source_files": ";".join(str(p.relative_to(root)) for p in paths),
        "source_sha256": ";".join(f"{p.name}|{sha256_file(p)}" for p in paths),
        "target_wavelength_nm_requested": TARGET_WAVELENGTH_NM,
        "target_pixel_map": "",
        "qc_variables_used": "",
        "timing_pass": False,
        "validity_resolved_without_photometric_values": False,
        "validity_pass": False,
        "primary_holdout_eligible_after_e0": False,
        "disposition": "",
        "read_errors": "",
        "e0_semantics": "FROZEN_REQUIRED_COUNTS_ARE_STRUCTURALLY_USABLE_SAMPLES",
    }
    for a in centers:
        row[f"nearest_{a}_s"] = ""
        row[f"samples_within_5s_{a}"] = 0
        row[f"samples_within_30s_{a}"] = 0
        row[f"safe_qc_valid_samples_within_5s_{a}"] = ""
        row[f"safe_qc_valid_samples_within_30s_{a}"] = ""

    if not paths:
        row["disposition"] = "SOURCE_FILE_MISSING"
        return row

    # Structural native-row timing only.  This is safe: decode_times never reads
    # protected photometric arrays.
    arrays: list[np.ndarray] = []
    try:
        for path in paths:
            with netCDF4.Dataset(path, "r") as ds:
                t = decode_times(ds)
            if not t.size or not np.isfinite(t).any():
                raise ValueError(f"{path.name}:NO_DECODABLE_NATIVE_TIMESTAMPS")
            arrays.append(t[np.isfinite(t)])
    except Exception as exc:
        row["read_errors"] = f"{type(exc).__name__}:{exc}"
        row["disposition"] = "UNREADABLE_OR_UNDECODABLE"
        return row

    all_times = np.unique(np.concatenate(arrays))
    timing_ok = True
    for a, center in centers.items():
        nearest, c5 = nearest_count(all_times, center, 5.0)
        _, c30 = nearest_count(all_times, center, 30.0)
        row[f"nearest_{a}_s"] = "" if nearest is None else f"{nearest:.6f}"
        row[f"samples_within_5s_{a}"] = c5
        row[f"samples_within_30s_{a}"] = c30
        timing_ok &= c5 >= 1 and c30 >= 10
    row["timing_pass"] = bool(timing_ok)
    if not timing_ok:
        row["disposition"] = "E0_TIMING_FAIL"
        return row

    # Structural channel validity is derived ONLY from wavelength coordinates
    # and explicitly safe integer QC fields.  file_validity() is inherited from
    # v1 and never accesses protected photometric values.
    validity: dict[str, dict[float, bool]] = {k: {} for k in centers}
    pixels: list[str] = []
    qc_names: set[str] = set()
    resolved = True
    try:
        for path in paths:
            partial, meta = file_validity(path, centers)
            merge(validity, partial)
            if meta["pixel"] is not None:
                pixels.append(
                    f"{path.name}|{meta['pixel']}|{float(meta['wavelength_nm']):.9f}"
                )
            qc_names.update(meta["qc"])
            with netCDF4.Dataset(path, "r") as ds:
                t = decode_times(ds)
            contributes = any(
                np.count_nonzero(
                    np.isfinite(t) & (np.abs(t - c) <= 30.0 + 1e-9)
                )
                for c in centers.values()
            )
            if contributes and not meta["resolved"]:
                resolved = False
    except Exception as exc:
        row["read_errors"] = f"{type(exc).__name__}:{exc}"
        row["disposition"] = "E0_VALIDITY_UNREADABLE"
        return row

    row["target_pixel_map"] = ";".join(pixels)
    row["qc_variables_used"] = ";".join(sorted(qc_names))
    row["validity_resolved_without_photometric_values"] = resolved
    if not resolved:
        row["disposition"] = "E0_VALIDITY_UNRESOLVED_NO_SAFE_QC"
        return row

    validity_ok = True
    for a, center in centers.items():
        good_times = np.asarray(
            [stamp for stamp, ok in validity[a].items() if bool(ok)], dtype=float
        )
        if good_times.size:
            delta = np.abs(good_times - center)
            c5_good = int(np.count_nonzero(delta <= 5.0 + 1e-9))
            c30_good = int(np.count_nonzero(delta <= 30.0 + 1e-9))
        else:
            c5_good = 0
            c30_good = 0
        row[f"safe_qc_valid_samples_within_5s_{a}"] = c5_good
        row[f"safe_qc_valid_samples_within_30s_{a}"] = c30_good
        validity_ok &= c5_good >= 1 and c30_good >= 10

    row["validity_pass"] = bool(validity_ok)
    if not validity_ok:
        row["disposition"] = "E0_SAFE_QC_VALIDITY_FAIL"
        return row

    row["primary_holdout_eligible_after_e0"] = True
    row["disposition"] = "E0_PASS_BLIND_CANDIDATE"
    return row


def main() -> int:
    # Preserve v1 CLI/output mechanics but ensure its module-global audit and
    # protocol identifiers are the prospective v2 definitions.
    V1.audit = audit
    V1.PROTOCOL = PROTOCOL
    V1.CONTROL_COMMENT = CONTROL_COMMENT
    return V1.main()


if __name__ == "__main__":
    raise SystemExit(main())
