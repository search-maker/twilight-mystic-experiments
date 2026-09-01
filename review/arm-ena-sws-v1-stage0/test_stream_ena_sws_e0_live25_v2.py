#!/usr/bin/env python3
"""Result-blind contract tests for the live25 E0-v2 hard-pin wrapper."""
from __future__ import annotations

import sys
from pathlib import Path

import stream_ena_sws_e0_live25_v2 as WRAP


def _run_with(argv: list[str]) -> tuple[int, list[str]]:
    old_argv = sys.argv[:]
    seen: list[str] = []
    old_main = WRAP.BASE.main

    def fake_main() -> int:
        seen.extend(sys.argv[1:])
        return 0

    try:
        WRAP.BASE.main = fake_main
        sys.argv = ["stream_ena_sws_e0_live25_v2.py", *argv]
        rc = WRAP.main()
    finally:
        WRAP.BASE.main = old_main
        sys.argv = old_argv
    return rc, seen


def _expect_override_rejected(argv: list[str]) -> None:
    old_argv = sys.argv[:]
    try:
        sys.argv = ["stream_ena_sws_e0_live25_v2.py", *argv]
        try:
            WRAP.main()
        except SystemExit as exc:
            msg = str(exc)
            assert "hard-pins audit_ena_sws_e0_v2.py" in msg, msg
        else:
            raise AssertionError("explicit --e0-script override was not rejected")
    finally:
        sys.argv = old_argv


def main() -> int:
    assert WRAP.E0_V2.name == "audit_ena_sws_e0_v2.py"
    assert WRAP.E0_V2 == (Path(WRAP.__file__).resolve().parent / "audit_ena_sws_e0_v2.py").resolve()
    assert WRAP.E0_V2.is_file()

    rc, args = _run_with(["--event-id", "2018-10-31_dusk"])
    assert rc == 0
    assert args[:2] == ["--e0-script", str(WRAP.E0_V2)], args
    assert args[2:] == ["--event-id", "2018-10-31_dusk"], args

    _expect_override_rejected(["--e0-script", "audit_ena_sws_e0.py"])
    _expect_override_rejected(["--e0-script=audit_ena_sws_e0.py"])

    src = Path(WRAP.__file__).read_text(encoding="utf-8")
    assert "audit_ena_sws_e0_v2.py" in src
    assert "protected" not in src.lower() or "photometric" in src.lower()
    print("PASS ENA SWS E0 live25 v2 hard-pin contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
