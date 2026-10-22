from __future__ import annotations

import io
import json
import tarfile
import tempfile
from pathlib import Path

import activation_support as s


def main() -> None:
    # Runtime provenance logic: only the reviewed alias may account for +1 file/+N bytes.
    alias = {"byteIdentical": True, "sourceSha256": "a", "aliasSha256": "a", "byteCount": 17}
    base = {"uvspecSha256": s.EXPECTED_UVSPEC_SHA256, "libRadtranDataTreeSha256": s.EXPECTED_BASE_DATA_SHA256}
    pre = {"libRadtranDataTreeSha256": s.EXPECTED_STAGED_DATA_SHA256, "libRadtranDataFileCount": 10, "libRadtranDataByteCount": 100}
    post = {"libRadtranDataTreeSha256": "post", "libRadtranDataFileCount": 11, "libRadtranDataByteCount": 117}
    r = s.validate_runtime_reports(base, pre, post, alias)
    assert r["status"] == "POST_ALIAS_RUNTIME_PROVENANCE_VALIDATED"
    bad = dict(post); bad["libRadtranDataFileCount"] = 12
    try:
        s.validate_runtime_reports(base, pre, bad, alias)
    except RuntimeError as exc:
        assert "file count" in str(exc)
    else:
        raise AssertionError("expected post-alias count refusal")

    # Report semantics remain capability-only and require both deterministic and MYSTIC nonidentity.
    with tempfile.TemporaryDirectory() as td:
        e = Path(td)
        (e / "disort-low.out").write_bytes(b"low")
        (e / "disort-high.out").write_bytes(b"high")
        (e / "mystic-low-mc.rad.spc").write_bytes(b"mlow")
        (e / "mystic-high-mc.rad.spc").write_bytes(b"mhigh")
        (e / "pre-alias-runtime-report.json").write_text(json.dumps(pre))
        (e / "post-alias-runtime-report.json").write_text(json.dumps(post))
        (e / "input-manifest.json").write_text(json.dumps({"resolverAlias": alias}))
        out = s.freeze_capability_report(e, 123)
        assert out["status"] == "PASS_CORRECTED_EXPLICIT_SPECIES_PROFILE_REACHES_DISORT_AND_MYSTIC"
        assert out["scientificOrdinalAllocated"] is False
        assert out["taylorOrJerusalemUsed"] is False
        assert out["productionAuthorized"] is False

    print("opac v3 activation support: PASS")


if __name__ == "__main__":
    main()
