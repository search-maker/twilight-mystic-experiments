#!/usr/bin/env python3
from pathlib import Path
p = Path(__file__).resolve().parents[2] / ".github/workflows/artifact-pipeline-replay-v1-review.yml"
t = p.read_text(encoding="utf-8"); low = t.lower()
assert "pull_request:" in t
assert "github.head_ref == 'review/artifact-pipeline-replay-v1'" in t
assert "workflow_" + "dispatch" not in low
assert "\npush:" not in low
for token in ("uv" + "spec", "librad" + "tran", "mc_" + "vroom", "mc_" + "spectral_is", "--allow-" + "execution", "executor_" + "v1.py"):
    assert token not in low, token
assert "actions: read" in t
assert "upload-artifact@v4" in t
assert "artifact-pipeline-replay-v1-candidate" in t
print("PASS: PR-only mechanical replay workflow; actions-read + candidate upload only; no solver/dispatch surface")
