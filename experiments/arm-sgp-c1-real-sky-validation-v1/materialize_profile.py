#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import json
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAYLOAD = HERE / "fex-profile-shapes.csv.zlib.b64"
OUTPUT = HERE / "fex-profile-shapes.csv"
EXPECTED_BYTES = 93646
EXPECTED_SHA256 = "6c2db68e7ecf15f65860338c946cc0f5456f012b3a46eb8b111809b2184ffdd2"


def main() -> int:
    compressed = base64.b64decode(b"".join(PAYLOAD.read_bytes().split()), validate=True)
    raw = zlib.decompress(compressed)
    digest = hashlib.sha256(raw).hexdigest()
    if len(raw) != EXPECTED_BYTES:
        raise SystemExit(f"profile byte-count mismatch: {len(raw)} != {EXPECTED_BYTES}")
    if digest != EXPECTED_SHA256:
        raise SystemExit(f"profile sha256 mismatch: {digest} != {EXPECTED_SHA256}")
    if OUTPUT.exists() and OUTPUT.read_bytes() != raw:
        raise SystemExit("refusing to overwrite a noncanonical fex-profile-shapes.csv")
    OUTPUT.write_bytes(raw)
    print(json.dumps({
        "status": "MATERIALIZED_CANONICAL_FEX_PROFILE",
        "path": OUTPUT.name,
        "bytes": len(raw),
        "sha256": digest,
        "scientificSolverExecuted": False,
        "saszeRadianceOpened": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"status": "REFUSED", "reason": str(exc)}, sort_keys=True), file=sys.stderr)
        raise
