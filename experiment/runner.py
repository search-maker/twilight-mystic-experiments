#!/usr/bin/env python3
from pathlib import Path

_PARTS = Path(__file__).resolve().parent / "runner_parts"
_SOURCE = "".join((_PARTS / f"part{index:02d}.pyfrag").read_text(encoding="utf-8") for index in range(1, 7))
exec(compile(_SOURCE, str(Path(__file__).resolve()), "exec"), globals(), globals())
