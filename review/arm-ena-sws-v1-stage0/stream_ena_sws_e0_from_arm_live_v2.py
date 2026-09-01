#!/usr/bin/env python3
"""Holdout-safe ARM Live transport shim for ENA/SWS E0.

Prospective/result-blind hardening before any authenticated ENA native E0 run.
The historical transport remains unchanged for provenance. This shim delegates
all frozen structural/schema logic to it while ensuring that network exceptions
cannot persist a URL containing ``user=ARM_ID:ACCESS_TOKEN``. It also refuses
explicit credential CLI arguments: credentials may be inherited only through
``ARM_USER_ID`` and ``ARM_ACCESS_TOKEN``.
"""
from __future__ import annotations

import sys

import stream_ena_sws_e0_from_arm_live as BASE

BASE_URL = BASE.BASE
DATASTREAM = BASE.DATASTREAM
AUX_DATASTREAM = BASE.AUX_DATASTREAM
FILE_RE = BASE.FILE_RE
AUX_RE = BASE.AUX_RE
sha256_file = BASE.sha256_file
safe_schema_snapshot = BASE.safe_schema_snapshot
row_without_raw_paths = BASE.row_without_raw_paths
json_filenames = BASE.json_filenames
iso_day = BASE.iso_day
plus_one_day = BASE.plus_one_day

# Capture immutable references BEFORE main() replaces the historical module's
# transport symbols with the sanitized wrappers. Calling BASE.query_day after
# that replacement would recurse into this shim.
_BASE_QUERY_DAY = BASE.query_day
_BASE_DOWNLOAD_NATIVE = BASE.download_native


class ARMTransportError(RuntimeError):
    """Sanitized transport failure whose text contains no request URL/secret."""


def _safe_failure(exc: BaseException) -> ARMTransportError:
    return ARMTransportError(type(exc).__name__)


def query_day(userpair: str, ds: str, yyyymmdd: str, pattern):
    try:
        return _BASE_QUERY_DAY(userpair, ds, yyyymmdd, pattern)
    except Exception as exc:
        raise _safe_failure(exc) from None


def download_native(userpair: str, filename: str, destination):
    try:
        return _BASE_DOWNLOAD_NATIVE(userpair, filename, destination)
    except Exception as exc:
        raise _safe_failure(exc) from None


def _reject_explicit_credentials(argv: list[str]) -> None:
    forbidden = ("--user-id", "--access-token")
    for arg in argv:
        if any(arg == key or arg.startswith(key + "=") for key in forbidden):
            raise SystemExit(
                "E0 transport v2 accepts ARM credentials from inherited environment only"
            )


def main() -> int:
    _reject_explicit_credentials(sys.argv[1:])
    # The historical collector resolves these names from its own module globals;
    # replace only transport calls with sanitized wrappers before delegating.
    BASE.query_day = query_day
    BASE.download_native = download_native
    return int(BASE.main() or 0)


if __name__ == "__main__":
    raise SystemExit(main())
