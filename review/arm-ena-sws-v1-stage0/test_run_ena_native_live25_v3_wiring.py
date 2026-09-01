#!/usr/bin/env python3
"""Static wiring proof: live25 v3 must bind the prospective v3 gate core."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
text = (HERE / "run_ena_native_live25_v3.py").read_text(encoding="utf-8")
assert "import ena_native_gate_core_v3 as gate_core_v3" in text
assert "_historical.G = gate_core_v3" in text
assert "ena_native_gate_core_v2 as gate_core_v3" not in text
assert "ena_native_gate_core_v1 as gate_core_v3" not in text
assert "sasze" not in text.lower()
print("PASS ENA native live25 v3 wiring")
